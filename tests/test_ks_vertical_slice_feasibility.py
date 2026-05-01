from __future__ import annotations

import importlib

import numpy as np

import pdelie
from tests._helpers.ks_vertical_slice import cached_ks_vertical_slice_summary, run_ks_vertical_slice_summary


def test_ks_vertical_slice_frozen_fixture_passes_feasibility_thresholds() -> None:
    summary = cached_ks_vertical_slice_summary()

    assert summary["derivative_keys"] == ["u_t", "u_x", "u_xx", "u_xxx", "u_xxxx"]
    assert summary["residual_max_abs"] < 5e-2
    assert summary["residual_rms"] < 1e-2
    assert summary["mass_drift"] <= 1e-8
    assert summary["selected_span_distance"] <= 1e-1
    assert summary["first_epsilon_error"] < 5e-4
    assert summary["classification"] != "failed"
    assert summary["transform_mode"] == "uniform_translation"


def test_ks_vertical_slice_records_relative_l2_drift_as_diagnostic_only() -> None:
    summary = cached_ks_vertical_slice_summary()

    assert "relative_l2_drift" in summary
    assert summary["relative_l2_drift"] >= 0.0
    # KS M4 gates mass drift, not relative L2 drift.
    assert summary["mass_drift"] <= 1e-8


def test_ks_vertical_slice_evidence_label_records_fallback_context() -> None:
    summary = cached_ks_vertical_slice_summary()

    assert summary["evidence_label"] in {"direct_svd_in_tolerance", "reference_fallback", "mixed"}
    if summary["reference_fallback_used"]:
        assert summary["evidence_label"] == "reference_fallback"
        assert summary["selected_span_distance"] <= 1e-1
        assert summary["classification"] != "failed"
        assert isinstance(summary["fallback_reason"], str)
        assert summary["fallback_reason"]
        assert summary["svd_span_distance"] is not None


def test_ks_vertical_slice_summary_is_deterministic() -> None:
    first = run_ks_vertical_slice_summary()
    second = run_ks_vertical_slice_summary()
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
            # The KS no-go fixture intentionally records fallback-backed SVD diagnostics.
            # Repeated LAPACK solves can differ at the final sub-nanounit digits without
            # changing the feasibility conclusion or the frozen threshold evidence.
            np.testing.assert_allclose(first[key], second[key], rtol=1e-8, atol=1e-12)
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
