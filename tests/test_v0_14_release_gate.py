from __future__ import annotations

import importlib
import json
import re
import tomllib
from pathlib import Path

import numpy as np

import pdelie
from pdelie.data import generate_heat_1d_field_batch
from pdelie.invariants import summarize_uniform_translation_orbit
from pdelie.reporting import summarize_invariant_workflow
from pdelie.residuals import HeatResidualEvaluator


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def test_v0_14_release_gate_metadata_docs_and_ci_are_aligned() -> None:
    pyproject = tomllib.loads(_repo_text("pyproject.toml"))
    workflow = _repo_text(".github/workflows/ci.yml")
    readiness = _repo_text("docs/releases/V0_28_RELEASE_READINESS.md")
    readme = _repo_text("README.md")
    changelog = _repo_text("CHANGELOG.md")
    publishing = _repo_text("docs/releases/PUBLISHING.md")
    plan = _repo_text("docs/planning/PLAN.md")
    scope = _repo_text("docs/planning/V0_14_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    release_gate_jobs = re.findall(r"^  (v0_\d+-release-gate):", workflow, flags=re.MULTILINE)

    assert pyproject["project"]["version"] == "0.28.0"
    assert release_gate_jobs == ["v0_28-release-gate"]
    assert "python -m pytest tests/test_v0_28_release_gate.py" in workflow
    assert "v0_13-release-gate" not in workflow

    assert "## 0.14.0" in changelog
    assert "V0.27" in readme
    assert "summarize_invariant_workflow" in readme
    assert "summarize_uniform_translation_orbit" in readme
    assert "package version: `0.28.0`" in readiness
    assert "git tag: `v0.28.0`" in readiness
    assert "Do not publish to TestPyPI or PyPI for `v0.28.0`" in readiness
    assert "including `v0.28.0`" in publishing
    assert "Milestone 6: COMPLETE" in plan
    assert "Milestone 6: COMPLETE" in scope
    assert "`v0.14` - Invariant workflow summaries and read-only orbit reports" in roadmap
    assert "**Status:** Completed" in roadmap


def test_v0_14_release_gate_new_helpers_are_documented_and_submodule_only() -> None:
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    invariants_module = importlib.import_module("pdelie.invariants")
    reporting_module = importlib.import_module("pdelie.reporting")

    assert hasattr(invariants_module, "summarize_uniform_translation_orbit")
    assert hasattr(reporting_module, "summarize_invariant_workflow")
    assert not hasattr(pdelie, "summarize_uniform_translation_orbit")
    assert not hasattr(pdelie, "summarize_invariant_workflow")
    assert "pdelie.invariants.summarize_uniform_translation_orbit" in api_stability
    assert "pdelie.reporting.summarize_invariant_workflow" in api_stability
    assert "do not construct augmented datasets, orbit datasets, or transformed `FieldBatch` collections" in api_stability
    assert "time-translation diagnostics remain deferred" in api_stability


def test_v0_14_release_gate_representative_invariant_workflow_summary() -> None:
    domain_length = 2.0 * np.pi
    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=14014)
    orbit = summarize_uniform_translation_orbit(
        field,
        shifts=[0.0, domain_length / 16.0, domain_length],
        windows=[{"start": 0.0, "width": domain_length / 4.0}],
        residual_evaluator=HeatResidualEvaluator(),
        source_field_id="v0_14_release_gate_heat",
    )
    workflow = summarize_invariant_workflow(
        orbit=orbit,
        coverage=orbit["coverage"],
        consistency=orbit["consistency"],
        extra_metrics={"release_gate": "v0.14"},
    )

    assert json.loads(json.dumps(workflow)) == workflow
    assert orbit["summary_type"] == "uniform_translation_orbit"
    assert orbit["source_field_id"] == "v0_14_release_gate_heat"
    assert orbit["orbit_passed"] is True
    assert orbit["coverage"]["summary_type"] == "periodic_window_coverage"
    assert orbit["consistency"]["summary_type"] == "uniform_translation_consistency"
    assert len(orbit["orbit_reports"]) == 3
    assert [report["shift"] for report in orbit["orbit_reports"]] == [0.0, domain_length / 16.0, domain_length]
    for report in orbit["orbit_reports"]:
        assert report["transform_spec"]["construction_method"] == "uniform_translation"
        assert report["inverse_passed"] is True
        assert report["period_wrap_passed"] is True
        assert report["residual_stability_passed"] is True
        assert "FieldBatch" not in repr(report)

    assert workflow["summary_schema_version"] == "0.1"
    assert workflow["summary_type"] == "invariant_workflow"
    assert workflow["orbit"]["summary_type"] == "uniform_translation_orbit"
    assert workflow["coverage"]["summary_type"] == "periodic_window_coverage"
    assert workflow["consistency"]["summary_type"] == "uniform_translation_consistency"
    assert workflow["extra_metrics"] == {"release_gate": "v0.14"}


def test_v0_14_release_gate_no_deferred_surface_leaked() -> None:
    modules = [
        pdelie,
        importlib.import_module("pdelie.data"),
        importlib.import_module("pdelie.invariants"),
        importlib.import_module("pdelie.residuals"),
        importlib.import_module("pdelie.reporting"),
        importlib.import_module("pdelie.examples"),
        importlib.import_module("pdelie.discovery"),
    ]
    forbidden_names = {
        "augment_translation_orbit",
        "build_translation_orbit_dataset",
        "build_translation_orbit_views",
        "compute_coverage_diagnostics",
        "compute_weak_derivatives",
        "diagnose_time_translation_consistency",
        "evaluate_weak_ks_residual",
        "from_pdebench",
        "from_the_well",
        "generate_ks_1d_field_batch",
        "generate_ks_feasibility_field_batch",
        "KSResidualEvaluator",
        "KuramotoSivashinskyResidualEvaluator",
        "load_pdebench",
        "load_the_well",
        "run_ks_vertical_slice_example",
        "WeakKSResidualEvaluator",
    }

    for module in modules:
        for name in sorted(forbidden_names):
            assert not hasattr(module, name), f"{module.__name__}.{name}"
