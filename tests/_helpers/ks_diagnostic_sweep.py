from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
from typing import Any

import numpy as np

from pdelie.data import split_batch_train_heldout
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.reporting import summarize_generator_fit_diagnostics
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import verify_translation_generator
from tests._helpers.ks_feasibility import (
    KSFeasibilityResidualEvaluator,
    compute_l2_norm,
    compute_mass,
    generate_ks_feasibility_field_batch,
)


KS_SWEEP_EPSILONS = (1e-5, 3e-5, 1e-4, 3e-4, 1e-3)
KS_SWEEP_VARIANTS: tuple[dict[str, object], ...] = (
    {"variant_name": "default", "generator_kwargs": {}},
    {"variant_name": "lower_amplitude", "generator_kwargs": {"amplitude": 0.04}},
    {"variant_name": "shorter_time", "generator_kwargs": {"max_time": 0.1}},
)
KS_SWEEP_TRAIN_SIZE = 2
KS_SWEEP_SPLIT_SEED = 11102


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


def _summary(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"min": None, "median": None, "max": None}
    array = np.asarray(values, dtype=float)
    return {
        "min": float(np.min(array)),
        "median": float(np.median(array)),
        "max": float(np.max(array)),
    }


def _variant_conclusion(fits: list[dict[str, object]], *, fallback_reason_stable: bool) -> str:
    labels = [str(fit["evidence_label"]) for fit in fits]
    fallback_flags = [bool(fit["reference_fallback_used"]) for fit in fits]
    verification_passes = [str(fit["classification"]) != "failed" for fit in fits]

    if any(label == "direct_svd_in_tolerance" for label in labels):
        return "direct_svd_recovered"
    if all(fallback_flags) and fallback_reason_stable and all(verification_passes):
        return "fallback_stable_across_epsilons"
    if len(set(labels)) > 1 or len(set(fallback_flags)) > 1:
        return "epsilon_sensitive"
    return "inconclusive"


def _variant_aggregates(fits: list[dict[str, object]]) -> dict[str, object]:
    condition_numbers = [
        float(fit["condition_number"])
        for fit in fits
        if fit["condition_number"] is not None and np.isfinite(float(fit["condition_number"]))
    ]
    svd_span_distances = [
        float(fit["svd_span_distance"])
        for fit in fits
        if fit["svd_span_distance"] is not None and np.isfinite(float(fit["svd_span_distance"]))
    ]
    fallback_reasons = sorted(
        {
            str(fit["fallback_reason"])
            for fit in fits
            if isinstance(fit["fallback_reason"], str) and fit["fallback_reason"]
        }
    )
    fallback_reason_stable = bool(fallback_reasons) and len(fallback_reasons) == 1

    aggregates = {
        "condition_number_summary": _summary(condition_numbers),
        "svd_span_distance_summary": _summary(svd_span_distances),
        "any_direct_svd_in_tolerance": any(
            fit["evidence_label"] == "direct_svd_in_tolerance" for fit in fits
        ),
        "fallback_reason_stable": fallback_reason_stable,
        "fallback_reasons": fallback_reasons,
    }
    aggregates["conclusion"] = _variant_conclusion(fits, fallback_reason_stable=fallback_reason_stable)
    return aggregates


def _run_variant(*, variant_name: str, generator_kwargs: dict[str, object]) -> dict[str, object]:
    field = generate_ks_feasibility_field_batch(**generator_kwargs)
    training, heldout = split_batch_train_heldout(
        field,
        train_size=KS_SWEEP_TRAIN_SIZE,
        seed=KS_SWEEP_SPLIT_SEED,
    )

    derivatives = compute_spectral_fd_derivatives(training, max_spatial_order=4)
    residual_evaluator = KSFeasibilityResidualEvaluator()
    residual = residual_evaluator.evaluate(training, derivatives)
    mass = compute_mass(field)
    l2 = compute_l2_norm(field)
    fits: list[dict[str, object]] = []

    for epsilon in KS_SWEEP_EPSILONS:
        generator = fit_translation_generator(training, residual_evaluator, epsilon=epsilon)
        fit_diagnostics = summarize_generator_fit_diagnostics(generator)
        verification = verify_translation_generator(heldout, generator, residual_evaluator)
        fit = {
            "epsilon": float(epsilon),
            "fit_diagnostics": fit_diagnostics,
            "selected_span_distance": fit_diagnostics["selected_span_distance"],
            "svd_span_distance": fit_diagnostics["svd_span_distance"],
            "reference_fallback_used": fit_diagnostics["reference_fallback_used"],
            "fallback_reason": fit_diagnostics["fallback_reason"],
            "evidence_label": fit_diagnostics["evidence_label"],
            "first_verification_error": float(verification.error_curve[0]),
            "classification": verification.classification,
            "transform_mode": verification.diagnostics["transform_mode"],
            "singular_values": fit_diagnostics["singular_values"],
            "condition_number": fit_diagnostics["condition_number"],
        }
        fits.append(_json_safe(fit))

    aggregates = _variant_aggregates(fits)
    return _json_safe(
        {
            "variant_name": variant_name,
            "generator_kwargs": generator_kwargs,
            "residual_max_abs": float(residual.diagnostics["max_abs_residual"]),
            "residual_rms": float(residual.diagnostics["rms_residual"]),
            "mass_drift": float(np.max(np.abs(mass - mass[:, [0]]))),
            "relative_l2_drift": float(
                np.max(np.abs(l2 - l2[:, [0]]) / np.maximum(np.abs(l2[:, [0]]), 1e-12))
            ),
            **aggregates,
            "fits": fits,
        }
    )


def run_ks_fit_diagnostic_sweep() -> dict[str, object]:
    return _json_safe(
        {
            "summary_schema_version": "0.1",
            "summary_type": "ks_fit_diagnostic_sweep",
            "epsilons": [float(epsilon) for epsilon in KS_SWEEP_EPSILONS],
            "train_size": KS_SWEEP_TRAIN_SIZE,
            "split_seed": KS_SWEEP_SPLIT_SEED,
            "variants": [
                _run_variant(
                    variant_name=str(variant["variant_name"]),
                    generator_kwargs=dict(variant["generator_kwargs"]),
                )
                for variant in KS_SWEEP_VARIANTS
            ],
        }
    )


@lru_cache(maxsize=1)
def _cached_ks_fit_diagnostic_sweep() -> dict[str, object]:
    return run_ks_fit_diagnostic_sweep()


def cached_ks_fit_diagnostic_sweep() -> dict[str, object]:
    return deepcopy(_cached_ks_fit_diagnostic_sweep())
