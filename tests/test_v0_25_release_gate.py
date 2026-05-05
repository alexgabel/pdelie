from __future__ import annotations

import importlib
import json
import re
import tomllib
from pathlib import Path

import pdelie
from pdelie.examples import run_kdv_scope_decision_example
from tests._helpers.kdv_scope_decision import run_internal_kdv_scope_matrix


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")
def test_v0_25_release_gate_kdv_scope_decision_api_is_documented_and_submodule_only() -> None:
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    examples_module = importlib.import_module("pdelie.examples")

    assert hasattr(examples_module, "run_kdv_scope_decision_example")
    assert not hasattr(pdelie, "run_kdv_scope_decision_example")
    assert "pdelie.examples.run_kdv_scope_decision_example" in api_stability
    assert "summary_type = \"kdv_scope_decision_example\"" in api_stability
    assert "current_frozen_supported" in api_stability
    assert "deferred_no_go" in api_stability
    assert "keep_public_kdv_surface_frozen" in api_stability
    assert "custom KdV initial conditions" in api_stability
    assert "weak KdV remain deferred" in api_stability
    assert "these APIs have no root `pdelie` exports" in api_stability


def test_v0_25_release_gate_example_outputs_kdv_decision_summary() -> None:
    result = run_kdv_scope_decision_example()

    assert json.loads(json.dumps(result, allow_nan=False)) == result
    assert result["summary_type"] == "kdv_scope_decision_example"
    assert result["decision"]["evidence_category"] == "current_frozen_supported"
    assert result["decision"]["conclusion"] == "keep_public_kdv_surface_frozen"
    assert result["current_frozen_path"]["readiness"]["readiness_label"] == "ready"
    assert result["current_frozen_path"]["residual"]["max_abs_residual"] < 1e-2
    assert result["current_frozen_path"]["residual"]["rms_residual"] < 2e-3
    assert result["current_frozen_path"]["fit_diagnostics"]["evidence_label"] == "direct_svd_in_tolerance"
    assert result["current_frozen_path"]["fit_diagnostics"]["reference_fallback_used"] is False
    assert result["current_frozen_path"]["verification"]["classification"] != "failed"
    assert result["current_frozen_path"]["confidence"]["confidence_label"] == "strong"
    assert result["extra_metrics"]["interpretation"] == "kdv_scope_decision_not_general_kdv_or_weak_kdv_promotion"
    assert {decision["evidence_category"] for decision in result["deferred_decisions"]} == {"deferred_no_go"}


def test_v0_25_release_gate_internal_kdv_scope_matrix_stays_test_only() -> None:
    report = run_internal_kdv_scope_matrix()
    data_module = importlib.import_module("pdelie.data")
    residuals_module = importlib.import_module("pdelie.residuals")

    assert json.loads(json.dumps(report, allow_nan=False)) == report
    assert report["visibility"] == "internal_diagnostic_only"
    assert report["conclusion"] == "keep_public_kdv_surface_frozen"
    assert report["custom_initial_condition_feasibility"]["deterministic"] is True
    assert report["configurable_coefficient_feasibility"]["passed"] is True
    assert report["weak_kdv_identity_feasibility"]["passed"] is True
    assert not hasattr(pdelie, "generate_kdv_1d_field_batch_from_initial_condition")
    assert not hasattr(data_module, "generate_kdv_1d_field_batch_from_initial_condition")
    assert not hasattr(data_module, "generate_configurable_kdv_1d_field_batch")
    assert not hasattr(data_module, "generate_general_kdv_1d_field_batch")
    assert not hasattr(residuals_module, "ConfigurableKdVResidualEvaluator")


def test_v0_25_release_gate_no_deferred_surface_leaked() -> None:
    forbidden = {
        "ConfigurableKdVResidualEvaluator",
        "WeakKdVResidualEvaluator",
        "compute_weak_derivatives",
        "evaluate_weak_kdv_residual",
        "generate_configurable_kdv_1d_field_batch",
        "generate_general_kdv_1d_field_batch",
        "generate_kdv_1d_field_batch_from_initial_condition",
        "sample_kdv_mode_coefficients",
    }

    for name in sorted(forbidden | {"run_kdv_scope_decision_example"}):
        assert not hasattr(pdelie, name), f"pdelie.{name}"

    modules = [
        importlib.import_module("pdelie.data"),
        importlib.import_module("pdelie.derivatives"),
        importlib.import_module("pdelie.residuals"),
    ]
    for module in modules:
        for name in sorted(forbidden):
            assert not hasattr(module, name), f"{module.__name__}.{name}"
