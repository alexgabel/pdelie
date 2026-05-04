from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from typing import Any

import numpy as np

from pdelie.data import split_batch_train_heldout
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.reporting import (
    summarize_generator_confidence,
    summarize_generator_fit_diagnostics,
    summarize_residual_batch,
    summarize_verification_report,
)
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.symmetry.parameterization import translation_span_distance
from pdelie.verification import verify_translation_generator
from tests._helpers.ks_feasibility import (
    KS_FEASIBILITY_CONFIG,
    KSFeasibilityResidualEvaluator,
    compute_l2_norm,
    compute_mass,
    generate_ks_feasibility_field_batch,
)
from tests._helpers.ks_vertical_slice import classify_translation_evidence


KS_REVISIT_THRESHOLDS: dict[str, float] = {
    "residual_max_abs": 5e-2,
    "residual_rms": 1e-2,
    "verification_first_error": 5e-4,
}
KS_REVISIT_PRIMARY_EPSILON = 1e-4
KS_REVISIT_SEEDS = (11101, 11109, 11117)
KS_REVISIT_EPSILONS = (1e-5, 1e-4, 1e-3)
KS_REVISIT_RESOLUTION_VARIANT = {"variant_name": "resolution_96", "num_points": 96}


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _run_ks_case(
    *,
    case_name: str,
    generator_kwargs: dict[str, object] | None = None,
    epsilon: float = KS_REVISIT_PRIMARY_EPSILON,
    include_confidence: bool = False,
) -> dict[str, object]:
    field = generate_ks_feasibility_field_batch(**(generator_kwargs or {}))
    training, heldout = split_batch_train_heldout(field, train_size=2, seed=11102)
    residual_evaluator = KSFeasibilityResidualEvaluator()
    derivatives = compute_spectral_fd_derivatives(training, max_spatial_order=4)
    residual = residual_evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, residual_evaluator, epsilon=float(epsilon))
    verification = verify_translation_generator(heldout, generator, residual_evaluator)
    fit_summary = summarize_generator_fit_diagnostics(generator)
    residual_summary = summarize_residual_batch(residual)
    verification_summary = summarize_verification_report(verification)

    selected_span_distance = float(translation_span_distance(generator.coefficients))
    svd_span_distance = fit_summary["svd_span_distance"]
    evidence_label = classify_translation_evidence(
        reference_fallback_used=bool(fit_summary["reference_fallback_used"]),
        selected_span_distance=selected_span_distance,
        verification_failed=verification.classification == "failed",
        fallback_reason=fit_summary["fallback_reason"],
        svd_span_distance=svd_span_distance,
    )
    mass = compute_mass(field)
    l2 = compute_l2_norm(field)

    report: dict[str, object] = {
        "case_name": case_name,
        "generator_kwargs": generator_kwargs or {},
        "epsilon": float(epsilon),
        "derivative_keys": sorted(str(name) for name in derivatives.derivatives),
        "residual_max_abs": float(residual.diagnostics["max_abs_residual"]),
        "residual_rms": float(residual.diagnostics["rms_residual"]),
        "mass_drift": float(np.max(np.abs(mass - mass[:, [0]]))),
        "relative_l2_drift": float(
            np.max(np.abs(l2 - l2[:, [0]]) / np.maximum(np.abs(l2[:, [0]]), 1e-12))
        ),
        "selected_span_distance": selected_span_distance,
        "svd_span_distance": None if svd_span_distance is None else float(svd_span_distance),
        "fit_mode": fit_summary["fit_mode"],
        "reference_fallback_used": bool(fit_summary["reference_fallback_used"]),
        "fallback_reason": fit_summary["fallback_reason"],
        "evidence_label": evidence_label,
        "first_verification_error": float(verification.error_curve[0]),
        "classification": verification.classification,
        "transform_mode": verification.diagnostics["transform_mode"],
        "fit_diagnostics": fit_summary,
    }
    if include_confidence:
        report["confidence"] = summarize_generator_confidence(
            residual=residual_summary,
            generator=generator,
            fit_diagnostics=fit_summary,
            verification=verification_summary,
            thresholds=KS_REVISIT_THRESHOLDS,
            extra_metrics={
                "promotion_requires_direct_svd": True,
                "v0_26_public_ks_promotion_allowed": False,
            },
        )
    return _json_safe(report)


def _promotion_candidate(case: dict[str, object]) -> bool:
    return (
        float(case["residual_max_abs"]) < KS_REVISIT_THRESHOLDS["residual_max_abs"]
        and float(case["residual_rms"]) < KS_REVISIT_THRESHOLDS["residual_rms"]
        and float(case["first_verification_error"]) < KS_REVISIT_THRESHOLDS["verification_first_error"]
        and str(case["classification"]) != "failed"
        and case["evidence_label"] == "direct_svd_in_tolerance"
        and case["reference_fallback_used"] is False
    )


def _decision_label(primary: dict[str, object]) -> str:
    residual_feasible = (
        float(primary["residual_max_abs"]) < KS_REVISIT_THRESHOLDS["residual_max_abs"]
        and float(primary["residual_rms"]) < KS_REVISIT_THRESHOLDS["residual_rms"]
    )
    verification_feasible = (
        float(primary["first_verification_error"]) < KS_REVISIT_THRESHOLDS["verification_first_error"]
        and str(primary["classification"]) != "failed"
    )
    if _promotion_candidate(primary):
        return "direct_strong_candidate_for_v0_26b_promotion"
    if (
        residual_feasible
        and verification_feasible
        and primary["reference_fallback_used"] is True
        and primary["fallback_reason"] == "svd_translation_span_drift"
    ):
        return "current_no_go_reference_fallback"
    if residual_feasible and verification_feasible:
        return "residual_feasible_fit_not_promotable"
    return "deferred_no_go"


def run_ks_revisit_decision_report() -> dict[str, object]:
    primary = _run_ks_case(case_name="primary_frozen_fixture", include_confidence=True)
    seed_sweep = [
        _run_ks_case(
            case_name=f"seed_{seed}",
            generator_kwargs={"seed": seed},
        )
        for seed in KS_REVISIT_SEEDS
    ]
    epsilon_sweep = [
        _run_ks_case(
            case_name=f"epsilon_{epsilon:g}",
            epsilon=epsilon,
        )
        for epsilon in KS_REVISIT_EPSILONS
    ]
    resolution_variant = _run_ks_case(
        case_name=str(KS_REVISIT_RESOLUTION_VARIANT["variant_name"]),
        generator_kwargs={"num_points": KS_REVISIT_RESOLUTION_VARIANT["num_points"]},
    )
    diagnostic_cases = [*seed_sweep, *epsilon_sweep, resolution_variant]

    return _json_safe(
        {
            "summary_schema_version": "0.1",
            "summary_type": "ks_revisit_decision",
            "visibility": "internal_diagnostic_only",
            "equation": KS_FEASIBILITY_CONFIG["equation"],
            "decision_label": _decision_label(primary),
            "decision_labels": [
                "current_no_go_reference_fallback",
                "residual_feasible_fit_not_promotable",
                "direct_strong_candidate_for_v0_26b_promotion",
                "deferred_no_go",
            ],
            "promotion_policy": {
                "v0_26_promotes_public_ks_runtime": False,
                "v0_26b_reserved_for_actual_promotion": True,
                "separate_scope_freeze_required": True,
                "best_of_sweep_promotion_allowed": False,
                "residual_only_public_api_allowed": False,
                "weak_ks_allowed": False,
            },
            "thresholds": KS_REVISIT_THRESHOLDS,
            "primary_fixture": primary,
            "minimal_matrix": {
                "seed_sweep": seed_sweep,
                "epsilon_sweep": epsilon_sweep,
                "resolution_variant": resolution_variant,
                "all_cases_diagnostic_only": True,
                "any_variant_direct_svd_candidate": any(_promotion_candidate(case) for case in diagnostic_cases),
                "variant_count": len(diagnostic_cases),
            },
        }
    )


@lru_cache(maxsize=1)
def _cached_ks_revisit_decision_report() -> dict[str, object]:
    return run_ks_revisit_decision_report()


def cached_ks_revisit_decision_report() -> dict[str, object]:
    return deepcopy(_cached_ks_revisit_decision_report())
