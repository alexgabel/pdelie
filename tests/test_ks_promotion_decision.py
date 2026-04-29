from __future__ import annotations

import importlib
from pathlib import Path

import pdelie
from tests._helpers.ks_vertical_slice import cached_ks_vertical_slice_summary


def test_m5_ks_promotion_decision_records_reference_fallback_no_go_evidence() -> None:
    summary = cached_ks_vertical_slice_summary()

    assert summary["evidence_label"] == "reference_fallback"
    assert summary["reference_fallback_used"] is True
    assert isinstance(summary["fallback_reason"], str)
    assert summary["fallback_reason"]
    assert summary["svd_span_distance"] is not None
    assert summary["svd_span_distance"] > 1e-1
    assert summary["selected_span_distance"] <= 1e-1
    assert summary["first_epsilon_error"] < 5e-4
    assert summary["classification"] != "failed"


def test_m5_no_public_ks_runtime_surface_or_api_stability_promotion() -> None:
    data_module = importlib.import_module("pdelie.data")
    residuals_module = importlib.import_module("pdelie.residuals")
    examples_module = importlib.import_module("pdelie.examples")
    api_stability_text = (
        Path(__file__).resolve().parents[1] / "docs/specs/API_STABILITY.md"
    ).read_text(encoding="utf-8")

    assert not hasattr(data_module, "generate_ks_1d_field_batch")
    assert not hasattr(residuals_module, "KSResidualEvaluator")
    assert not hasattr(residuals_module, "KuramotoSivashinskyResidualEvaluator")
    assert not hasattr(examples_module, "run_ks_vertical_slice_example")
    assert not hasattr(pdelie, "generate_ks_1d_field_batch")
    assert not hasattr(pdelie, "KSResidualEvaluator")
    assert not hasattr(pdelie, "KuramotoSivashinskyResidualEvaluator")
    assert not hasattr(pdelie, "run_ks_vertical_slice_example")

    assert "pdelie.data.generate_ks_1d_field_batch" not in api_stability_text
    assert "pdelie.residuals.KSResidualEvaluator" not in api_stability_text
    assert "pdelie.residuals.KuramotoSivashinskyResidualEvaluator" not in api_stability_text
    assert "does not add a stable public Kuramoto-Sivashinsky data generator or residual evaluator" in api_stability_text
