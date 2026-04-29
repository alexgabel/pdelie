from __future__ import annotations

import importlib

import numpy as np

import pdelie
from pdelie.data import split_batch_train_heldout
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.symmetry.parameterization import translation_span_distance
from pdelie.verification import verify_translation_generator
from tests._helpers.ks_feasibility import (
    KSFeasibilityResidualEvaluator,
    compute_l2_norm,
    compute_mass,
    generate_ks_feasibility_field_batch,
)


def _classify_translation_evidence(
    *,
    reference_fallback_used: bool,
    selected_span_distance: float,
    verification_failed: bool,
    fallback_reason: object,
    svd_span_distance: object,
) -> str:
    if not reference_fallback_used and selected_span_distance <= 1e-1:
        return "direct_svd_in_tolerance"
    if (
        reference_fallback_used
        and selected_span_distance <= 1e-1
        and not verification_failed
        and isinstance(fallback_reason, str)
        and fallback_reason
        and svd_span_distance is not None
    ):
        return "reference_fallback"
    return "mixed"


def _run_ks_vertical_slice_summary() -> dict[str, object]:
    field = generate_ks_feasibility_field_batch()
    training, heldout = split_batch_train_heldout(field, train_size=2, seed=11102)

    derivatives = compute_spectral_fd_derivatives(training, max_spatial_order=4)
    residual_evaluator = KSFeasibilityResidualEvaluator()
    residual = residual_evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, residual_evaluator, epsilon=1e-4)
    verification = verify_translation_generator(heldout, generator, residual_evaluator)

    mass = compute_mass(field)
    l2 = compute_l2_norm(field)
    mass_drift = float(np.max(np.abs(mass - mass[:, [0]])))
    relative_l2_drift = float(np.max(np.abs(l2 - l2[:, [0]]) / np.maximum(np.abs(l2[:, [0]]), 1e-12)))
    selected_span_distance = float(translation_span_distance(generator.coefficients))
    svd_span_distance = generator.diagnostics.get("svd_span_distance")
    fallback_reason = generator.diagnostics.get("fallback_reason")
    evidence_label = _classify_translation_evidence(
        reference_fallback_used=bool(generator.diagnostics["reference_fallback_used"]),
        selected_span_distance=selected_span_distance,
        verification_failed=verification.classification == "failed",
        fallback_reason=fallback_reason,
        svd_span_distance=svd_span_distance,
    )

    return {
        "derivative_keys": sorted(derivatives.derivatives),
        "residual_max_abs": float(residual.diagnostics["max_abs_residual"]),
        "residual_rms": float(residual.diagnostics["rms_residual"]),
        "mass_drift": mass_drift,
        "relative_l2_drift": relative_l2_drift,
        "selected_span_distance": selected_span_distance,
        "svd_span_distance": None if svd_span_distance is None else float(svd_span_distance),
        "fit_mode": generator.diagnostics["fit_mode"],
        "reference_fallback_used": bool(generator.diagnostics["reference_fallback_used"]),
        "fallback_reason": fallback_reason,
        "first_epsilon_error": float(verification.error_curve[0]),
        "classification": verification.classification,
        "transform_mode": verification.diagnostics["transform_mode"],
        "evidence_label": evidence_label,
    }


def test_ks_vertical_slice_frozen_fixture_passes_feasibility_thresholds() -> None:
    summary = _run_ks_vertical_slice_summary()

    assert summary["derivative_keys"] == ["u_t", "u_x", "u_xx", "u_xxx", "u_xxxx"]
    assert summary["residual_max_abs"] < 5e-2
    assert summary["residual_rms"] < 1e-2
    assert summary["mass_drift"] <= 1e-8
    assert summary["selected_span_distance"] <= 1e-1
    assert summary["first_epsilon_error"] < 5e-4
    assert summary["classification"] != "failed"
    assert summary["transform_mode"] == "uniform_translation"


def test_ks_vertical_slice_records_relative_l2_drift_as_diagnostic_only() -> None:
    summary = _run_ks_vertical_slice_summary()

    assert "relative_l2_drift" in summary
    assert summary["relative_l2_drift"] >= 0.0
    # KS M4 gates mass drift, not relative L2 drift.
    assert summary["mass_drift"] <= 1e-8


def test_ks_vertical_slice_evidence_label_records_fallback_context() -> None:
    summary = _run_ks_vertical_slice_summary()

    assert summary["evidence_label"] in {"direct_svd_in_tolerance", "reference_fallback", "mixed"}
    if summary["reference_fallback_used"]:
        assert summary["evidence_label"] == "reference_fallback"
        assert summary["selected_span_distance"] <= 1e-1
        assert summary["classification"] != "failed"
        assert isinstance(summary["fallback_reason"], str)
        assert summary["fallback_reason"]
        assert summary["svd_span_distance"] is not None


def test_ks_vertical_slice_summary_is_deterministic() -> None:
    first = _run_ks_vertical_slice_summary()
    second = _run_ks_vertical_slice_summary()
    numeric_keys = {
        "residual_max_abs",
        "residual_rms",
        "mass_drift",
        "relative_l2_drift",
        "selected_span_distance",
        "svd_span_distance",
        "first_epsilon_error",
    }

    for key in first:
        if key in numeric_keys:
            np.testing.assert_allclose(first[key], second[key], rtol=1e-9, atol=1e-12)
        else:
            assert first[key] == second[key]


def test_ks_vertical_slice_feasibility_adds_no_public_ks_surface() -> None:
    data_module = importlib.import_module("pdelie.data")
    residuals_module = importlib.import_module("pdelie.residuals")

    assert not hasattr(pdelie, "generate_ks_1d_field_batch")
    assert not hasattr(pdelie, "KSResidualEvaluator")
    assert not hasattr(data_module, "generate_ks_1d_field_batch")
    assert not hasattr(data_module, "generate_ks_feasibility_field_batch")
    assert not hasattr(residuals_module, "KSResidualEvaluator")
    assert not hasattr(residuals_module, "KuramotoSivashinskyResidualEvaluator")
