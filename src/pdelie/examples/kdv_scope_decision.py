from __future__ import annotations

import json

import numpy as np

from pdelie.data import generate_kdv_1d_field_batch, split_batch_train_heldout
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.reporting import (
    summarize_field_batch_readiness,
    summarize_generator_confidence,
    summarize_generator_fit_diagnostics,
    summarize_residual_batch,
    summarize_verification_report,
)
from pdelie.residuals import KdVResidualEvaluator
from pdelie.symmetry import validate_symmetry_candidate
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.symmetry.parameterization import translation_span_distance
from pdelie.verification import verify_translation_generator


_SUMMARY_SCHEMA_VERSION = "0.1"


def _mass_and_l2_drift(values: np.ndarray, *, dx: float) -> dict[str, float]:
    scalar_values = np.asarray(values[..., 0], dtype=float)
    mass = dx * np.sum(scalar_values, axis=-1)
    l2 = np.sqrt(dx * np.sum(np.square(scalar_values), axis=-1))
    return {
        "mass_drift": float(np.max(np.abs(mass - mass[:, [0]]))),
        "relative_l2_drift": float(np.max(np.abs(l2 - l2[:, [0]]) / np.maximum(np.abs(l2[:, [0]]), 1e-12))),
    }


def _deferred_decisions() -> list[dict[str, object]]:
    return [
        {
            "decision": "custom_kdv_initial_conditions",
            "evidence_category": "deferred_no_go",
            "reason": "custom initial-condition rollout is still test-only feasibility evidence, not a public API.",
        },
        {
            "decision": "configurable_kdv_coefficients",
            "evidence_category": "deferred_no_go",
            "reason": "coefficient sign/scaling diagnostics remain internal and do not define a stable evaluator surface.",
        },
        {
            "decision": "general_kdv_regime",
            "evidence_category": "deferred_no_go",
            "reason": "longer horizons, larger amplitudes, and broader mode ranges need a separate promotion gate.",
        },
        {
            "decision": "weak_kdv",
            "evidence_category": "deferred_no_go",
            "reason": "third-order weak KdV needs stronger boundary-regular test functions and broader weak machinery.",
        },
    ]


def run_kdv_scope_decision_example() -> dict[str, object]:
    field = generate_kdv_1d_field_batch(batch_size=5, seed=25025)
    training, heldout = split_batch_train_heldout(field, train_size=2, seed=25026)
    evaluator = KdVResidualEvaluator()

    derivatives = compute_spectral_fd_derivatives(training, max_spatial_order=3)
    residual = evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, evaluator, epsilon=1e-4)
    verification = verify_translation_generator(heldout, generator, evaluator)
    candidate_validation = validate_symmetry_candidate(
        field,
        generator,
        residual_evaluator=evaluator,
        source_candidate_id="frozen_kdv_translation_fit",
    )
    readiness = summarize_field_batch_readiness(
        field,
        residual_evaluator=evaluator,
        expected_equation="kdv_normalized",
    )
    confidence = summarize_generator_confidence(
        residual=residual,
        generator=generator,
        fit_diagnostics=summarize_generator_fit_diagnostics(generator),
        verification=verification,
        candidate_validation=candidate_validation,
        thresholds={
            "residual_max_abs": 1e-2,
            "residual_rms": 2e-3,
            "verification_first_error": 1e-4,
        },
        extra_metrics={"case_name": "kdv_frozen_public_strong_path"},
    )
    dx = float(field.coords["x"][1] - field.coords["x"][0])
    conservation = _mass_and_l2_drift(field.values, dx=dx)

    return {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": "kdv_scope_decision_example",
        "decision": {
            "evidence_category": "current_frozen_supported",
            "public_scope": "normalized_scalar_1d_periodic_short_horizon_strong_kdv",
            "conclusion": "keep_public_kdv_surface_frozen",
            "equation": "u_t + 6*u*u_x + u_xxx = 0",
        },
        "current_frozen_path": {
            "readiness": readiness,
            "residual": summarize_residual_batch(residual),
            "fit_diagnostics": summarize_generator_fit_diagnostics(generator),
            "verification": summarize_verification_report(verification),
            "candidate_validation": candidate_validation,
            "confidence": confidence,
        },
        "deferred_decisions": _deferred_decisions(),
        "extra_metrics": {
            "example_name": "kdv_scope_decision",
            "generator_seed": 25025,
            "split_seed": 25026,
            "train_size": 2,
            "decision_categories": ["current_frozen_supported", "deferred_no_go"],
            "fit_evidence_label": generator.diagnostics.get("evidence_label"),
            "reference_fallback_used": bool(generator.diagnostics.get("reference_fallback_used")),
            "translation_span_distance": float(translation_span_distance(generator.coefficients)),
            "mass_drift": conservation["mass_drift"],
            "relative_l2_drift": conservation["relative_l2_drift"],
            "interpretation": "kdv_scope_decision_not_general_kdv_or_weak_kdv_promotion",
        },
    }


def main() -> None:
    print(json.dumps(run_kdv_scope_decision_example(), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
