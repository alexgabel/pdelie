from __future__ import annotations

import importlib
import re
from pathlib import Path

import pdelie
from pdelie.examples import run_heat_vertical_slice_example, run_kdv_vertical_slice_example


_REPORTING_HELPERS = {
    "summarize_generator_family",
    "summarize_residual_batch",
    "summarize_verification_report",
    "summarize_vertical_slice",
    "summarize_weak_residual_report",
}
_DEFERRED_OR_FORBIDDEN_NAMES = {
    "KSResidualEvaluator",
    "KuramotoSivashinskyResidualEvaluator",
    "OperatorSymmetry",
    "WeakKdVResidualEvaluator",
    "compute_weak_derivatives",
    "evaluate_weak_kdv_residual",
    "from_pdebench",
    "from_the_well",
    "generate_ks_1d_field_batch",
    "generate_ks_feasibility_field_batch",
    "load_pdebench",
    "load_the_well",
    "sample_kdv_mode_coefficients",
}


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def _assert_vertical_slice_summary(summary: dict[str, object], *, expected_equation: str) -> None:
    assert summary["summary_schema_version"] == "0.1"
    assert summary["summary_type"] == "vertical_slice"
    assert summary["derivative_backend"] == "spectral_fd"
    assert summary["extra_metrics"]["equation"] == expected_equation
    assert summary["residual"]["summary_type"] == "residual_batch"
    assert summary["generator"]["summary_type"] == "generator_family"
    assert summary["verification"]["summary_type"] == "verification_report"

    assert "verification_classification" not in summary
    assert "max_abs_residual" not in summary


def test_v0_10_release_gate_reporting_surface_and_api_stability_are_aligned() -> None:
    reporting_module = importlib.import_module("pdelie.reporting")
    api_stability = _repo_text("docs/specs/API_STABILITY.md")

    for name in sorted(_REPORTING_HELPERS):
        assert hasattr(reporting_module, name)
        assert not hasattr(pdelie, name)
        assert f"pdelie.reporting.{name}" in api_stability

    assert "pdelie.residuals.evaluate_weak_heat_residual" in api_stability
    assert "pdelie.residuals.evaluate_weak_burgers_residual" in api_stability
    assert "pdelie.data.generate_kdv_1d_field_batch" in api_stability
    assert "pdelie.residuals.KdVResidualEvaluator" in api_stability
    assert "these APIs have no root `pdelie` exports" in api_stability
    assert "operator symmetry" in api_stability


def test_v0_10_release_gate_examples_emit_nested_reporting_summaries() -> None:
    heat = run_heat_vertical_slice_example()
    kdv = run_kdv_vertical_slice_example()

    _assert_vertical_slice_summary(heat, expected_equation="heat_1d")
    _assert_vertical_slice_summary(kdv, expected_equation="kdv_normalized")
    assert heat["verification"]["classification"] == "exact"
    assert kdv["verification"]["classification"] != "failed"
    assert kdv["residual"]["max_abs_residual"] < 1e-2


def test_v0_10_release_gate_no_new_numerical_or_deferred_public_surface() -> None:
    modules = [
        pdelie,
        importlib.import_module("pdelie.data"),
        importlib.import_module("pdelie.derivatives"),
        importlib.import_module("pdelie.residuals"),
        importlib.import_module("pdelie.reporting"),
    ]

    for module in modules:
        for name in sorted(_DEFERRED_OR_FORBIDDEN_NAMES):
            assert not hasattr(module, name), f"{module.__name__}.{name}"


def test_v0_10_release_gate_ci_uses_single_current_release_gate_job() -> None:
    workflow = _repo_text(".github/workflows/ci.yml")
    release_gate_jobs = re.findall(r"^  (v0_\d+-release-gate):", workflow, flags=re.MULTILINE)

    assert release_gate_jobs == ["v0_10-release-gate"]
    assert "python -m pytest tests/test_v0_10_release_gate.py" in workflow
    assert "run: python -m pytest\n" in workflow
    for historical_job in range(4, 10):
        assert f"v0_{historical_job}-release-gate:" not in workflow
