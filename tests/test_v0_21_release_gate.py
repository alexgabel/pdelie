from __future__ import annotations

import importlib
import json
import re
import tomllib
from pathlib import Path

import pdelie
from pdelie.data import from_numpy, generate_heat_1d_field_batch
from pdelie.examples import run_external_data_readiness_example
from pdelie.reporting import summarize_field_batch_readiness
from pdelie.residuals import HeatResidualEvaluator, KdVResidualEvaluator


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def _heat_metadata(*, equation: str | None = "heat_1d") -> dict[str, object]:
    parameter_tags: dict[str, object] = {"nu": 0.1, "domain_length": float(2.0 * 3.141592653589793)}
    if equation is not None:
        parameter_tags["equation"] = equation
    return {
        "boundary_conditions": {"x": "periodic"},
        "coordinate_system": "cartesian",
        "grid_regularity": "uniform",
        "grid_type": "rectilinear",
        "parameter_tags": parameter_tags,
    }


def test_v0_21_release_gate_metadata_docs_and_ci_are_aligned() -> None:
    pyproject = tomllib.loads(_repo_text("pyproject.toml"))
    workflow = _repo_text(".github/workflows/ci.yml")
    readiness = _repo_text("docs/releases/V0_22_RELEASE_READINESS.md")
    readme = _repo_text("README.md")
    changelog = _repo_text("CHANGELOG.md")
    publishing = _repo_text("docs/releases/PUBLISHING.md")
    plan = _repo_text("docs/planning/PLAN.md")
    scope = _repo_text("docs/planning/V0_21_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    release_gate_jobs = re.findall(r"^  (v0_\d+-release-gate):", workflow, flags=re.MULTILINE)

    assert pyproject["project"]["version"] == "0.22.0"
    assert release_gate_jobs == ["v0_22-release-gate"]
    assert "python -m pytest tests/test_v0_22_release_gate.py" in workflow
    assert "v0_20-release-gate" not in workflow

    assert "## 0.22.0" in changelog
    assert "V0.22" in readme
    assert "summarize_field_batch_readiness" in readme
    assert "package version: `0.22.0`" in readiness
    assert "git tag: `v0.22.0`" in readiness
    assert "Do not publish to TestPyPI or PyPI for `v0.22.0`" in readiness
    assert "including `v0.22.0`" in publishing
    assert "Milestone 6: COMPLETE" in plan
    assert "Milestone 6: COMPLETE" in scope
    assert "`v0.21` - External data readiness reports" in roadmap
    assert "**Status:** Completed" in roadmap


def test_v0_21_release_gate_readiness_api_is_documented_and_submodule_only() -> None:
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    reporting_module = importlib.import_module("pdelie.reporting")
    examples_module = importlib.import_module("pdelie.examples")

    assert hasattr(reporting_module, "summarize_field_batch_readiness")
    assert hasattr(examples_module, "run_external_data_readiness_example")
    assert not hasattr(pdelie, "summarize_field_batch_readiness")
    assert not hasattr(pdelie, "run_external_data_readiness_example")
    assert "pdelie.reporting.summarize_field_batch_readiness" in api_stability
    assert "summary_type = \"field_batch_readiness\"" in api_stability
    assert "ready" in api_stability
    assert "needs_attention" in api_stability
    assert "not_ready" in api_stability
    assert "no root `pdelie` exports" in api_stability


def test_v0_21_release_gate_generated_and_imported_field_readiness_reports_are_json_safe() -> None:
    generated = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=32, seed=21021)
    generated_report = summarize_field_batch_readiness(
        generated,
        residual_evaluator=HeatResidualEvaluator(),
    )

    imported = from_numpy(
        generated.values,
        dims=generated.dims,
        coords=generated.coords,
        var_name="u",
        metadata=_heat_metadata(equation="heat_1d"),
        preprocess_log=[{"operation": "release_gate_import"}],
    )
    imported_report = summarize_field_batch_readiness(
        imported,
        residual_evaluator=HeatResidualEvaluator(),
        expected_equation="heat_1d",
    )
    mismatch_report = summarize_field_batch_readiness(
        imported,
        residual_evaluator=KdVResidualEvaluator(),
        expected_equation="kdv_normalized",
    )

    assert json.loads(json.dumps(generated_report)) == generated_report
    assert json.loads(json.dumps(imported_report)) == imported_report
    assert generated_report["summary_type"] == "field_batch_readiness"
    assert generated_report["readiness_label"] == "ready"
    assert generated_report["residual_preflight"]["residual"]["summary_type"] == "residual_batch"
    assert imported_report["readiness_label"] == "ready"
    assert imported_report["component_statuses"]["metadata"]["status"] == "passed"
    assert mismatch_report["readiness_label"] == "not_ready"
    assert mismatch_report["component_statuses"]["expected_equation"]["status"] == "failed"
    assert mismatch_report["component_statuses"]["residual_preflight"]["status"] == "failed"


def test_v0_21_release_gate_example_outputs_readiness_cases() -> None:
    result = run_external_data_readiness_example()

    assert json.loads(json.dumps(result)) == result
    assert result["summary_type"] == "external_data_readiness_example"
    assert result["extra_metrics"]["readiness_labels"] == ["ready", "not_ready", "not_ready"]
    cases = {case["case_name"]: case["readiness"] for case in result["cases"]}
    assert cases["from_numpy_heat_ready"]["summary_type"] == "field_batch_readiness"
    assert cases["from_numpy_heat_ready"]["readiness_label"] == "ready"
    assert cases["metadata_incomplete"]["readiness_label"] == "not_ready"
    assert cases["residual_evaluator_mismatch"]["readiness_label"] == "not_ready"
    assert cases["residual_evaluator_mismatch"]["component_statuses"]["expected_equation"]["status"] == "passed"
    assert cases["residual_evaluator_mismatch"]["component_statuses"]["residual_preflight"]["status"] == "failed"


def test_v0_21_release_gate_no_deferred_surface_leaked() -> None:
    root_forbidden = {
        "run_external_data_readiness_example",
        "summarize_field_batch_readiness",
    }
    deferred_forbidden = {
        "from_pdebench",
        "from_the_well",
        "from_xarray_dataset",
        "generate_ks_1d_field_batch",
        "generate_ks_feasibility_field_batch",
        "KSResidualEvaluator",
        "KuramotoSivashinskyResidualEvaluator",
        "load_field_batch",
        "load_pdebench",
        "load_the_well",
        "resample_nonuniform_grid",
        "split_orbit_train_heldout",
        "summarize_field_batch_readiness_score",
        "train_test_translation_orbit_split",
        "WeakAdvectionDiffusionResidualEvaluator",
        "WeakKSResidualEvaluator",
        "WeakReactionDiffusionResidualEvaluator",
    }

    for name in sorted(root_forbidden | deferred_forbidden):
        assert not hasattr(pdelie, name), f"pdelie.{name}"

    modules = [
        importlib.import_module("pdelie.data"),
        importlib.import_module("pdelie.invariants"),
        importlib.import_module("pdelie.residuals"),
        importlib.import_module("pdelie.reporting"),
        importlib.import_module("pdelie.examples"),
        importlib.import_module("pdelie.discovery"),
        importlib.import_module("pdelie.symmetry"),
    ]
    for module in modules:
        for name in sorted(deferred_forbidden):
            assert not hasattr(module, name), f"{module.__name__}.{name}"
