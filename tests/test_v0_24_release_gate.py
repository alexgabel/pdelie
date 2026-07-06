from __future__ import annotations

import importlib
import json
from pathlib import Path

import pdelie
from pdelie.data import generate_heat_1d_field_batch
from pdelie.examples import run_weak_form_supportability_example
from pdelie.reporting import summarize_weak_form_supportability
from pdelie.residuals import evaluate_weak_heat_residual
from tests._helpers.weak_reaction_diffusion_feasibility import run_internal_fisher_kpp_weak_feasibility


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")
def test_v0_24_release_gate_weak_supportability_api_is_documented_and_submodule_only() -> None:
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    reporting_module = importlib.import_module("pdelie.reporting")
    examples_module = importlib.import_module("pdelie.examples")

    assert hasattr(reporting_module, "summarize_weak_form_supportability")
    assert hasattr(examples_module, "run_weak_form_supportability_example")
    assert not hasattr(pdelie, "summarize_weak_form_supportability")
    assert not hasattr(pdelie, "run_weak_form_supportability_example")
    assert "pdelie.reporting.summarize_weak_form_supportability" in api_stability
    assert "summary_type = \"weak_form_supportability\"" in api_stability
    assert "supported_existing_slice" in api_stability
    assert "diagnostic_only" in api_stability
    assert "weak design matrices" in api_stability
    assert "these APIs have no root `pdelie` exports" in api_stability


def test_v0_24_release_gate_weak_supportability_labels_and_json_contract() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=7, num_points=16, seed=24024)
    weak_report = evaluate_weak_heat_residual(field)
    supported = summarize_weak_form_supportability(
        weak_report=weak_report,
        thresholds={"finite_required": True, "min_weak_rows": 1},
    )
    diagnostic = summarize_weak_form_supportability(
        feasibility={
            "summary_schema_version": "0.1",
            "summary_type": "weak_reaction_diffusion_feasibility",
            "visibility": "internal_diagnostic_only",
            "quadrature_rule": "composite_simpson_tensor_product_v1",
            "conclusion": "diagnostic_only",
        },
    )
    failed = summarize_weak_form_supportability(
        weak_report=weak_report,
        thresholds={"weak_report_max_abs": 1e-12},
    )
    insufficient = summarize_weak_form_supportability()

    for report in (supported, diagnostic, failed, insufficient):
        assert json.loads(json.dumps(report, allow_nan=False)) == report
        assert report["summary_type"] == "weak_form_supportability"

    assert supported["supportability_label"] == "supported_existing_slice"
    assert supported["weak_contract"]["quadrature_rule"] == "composite_tensor_product_trapezoidal_native_window"
    assert diagnostic["supportability_label"] == "diagnostic_only"
    assert failed["supportability_label"] == "failed"
    assert insufficient["supportability_label"] == "insufficient_evidence"
    assert supported["policy"]["supports_wsindy"] is False
    assert supported["policy"]["supports_weak_derivative_backend"] is False


def test_v0_24_release_gate_internal_fisher_kpp_feasibility_stays_test_only() -> None:
    report = run_internal_fisher_kpp_weak_feasibility()
    residuals_module = importlib.import_module("pdelie.residuals")

    assert json.loads(json.dumps(report, allow_nan=False)) == report
    assert report["visibility"] == "internal_diagnostic_only"
    assert report["all_identity_tests_passed"] is True
    assert not hasattr(pdelie, "evaluate_weak_reaction_diffusion_residual")
    assert not hasattr(residuals_module, "evaluate_weak_reaction_diffusion_residual")
    assert not hasattr(residuals_module, "WeakReactionDiffusionResidualEvaluator")
    assert not hasattr(residuals_module, "compute_weak_derivatives")


def test_v0_24_release_gate_example_outputs_weak_supportability_summary() -> None:
    result = run_weak_form_supportability_example()

    assert json.loads(json.dumps(result, allow_nan=False)) == result
    assert result["summary_type"] == "weak_form_supportability_example"
    assert result["extra_metrics"]["supportability_labels"] == [
        "supported_existing_slice",
        "supported_existing_slice",
        "diagnostic_only",
    ]
    assert result["cases"][0]["supportability"]["summary_type"] == "weak_form_supportability"


def test_v0_24_release_gate_no_deferred_surface_leaked() -> None:
    forbidden = {
        "compute_weak_derivatives",
        "evaluate_weak_kdv_residual",
        "evaluate_weak_ks_residual",
        "evaluate_weak_reaction_diffusion_residual",
        "summarize_weak_sparse_recovery",
        "summarize_wsindy_design_matrix",
        "WeakKdVResidualEvaluator",
        "WeakKSResidualEvaluator",
        "WeakReactionDiffusionResidualEvaluator",
        "WSINDyDesignMatrix",
    }

    for name in sorted(forbidden | {"run_weak_form_supportability_example", "summarize_weak_form_supportability"}):
        assert not hasattr(pdelie, name), f"pdelie.{name}"

    modules = [
        importlib.import_module("pdelie.derivatives"),
        importlib.import_module("pdelie.reporting"),
        importlib.import_module("pdelie.residuals"),
        importlib.import_module("pdelie.symmetry"),
    ]
    for module in modules:
        for name in sorted(forbidden):
            assert not hasattr(module, name), f"{module.__name__}.{name}"
