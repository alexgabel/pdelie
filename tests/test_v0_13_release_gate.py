from __future__ import annotations

import importlib
import json
import re
import tomllib
from pathlib import Path

import numpy as np

import pdelie
from pdelie.data import generate_heat_1d_field_batch
from pdelie.invariants import compute_periodic_window_coverage, diagnose_uniform_translation_consistency
from pdelie.residuals import HeatResidualEvaluator


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def test_v0_13_release_gate_metadata_docs_and_ci_are_aligned() -> None:
    pyproject = tomllib.loads(_repo_text("pyproject.toml"))
    workflow = _repo_text(".github/workflows/ci.yml")
    readiness = _repo_text("docs/releases/V0_18_RELEASE_READINESS.md")
    readme = _repo_text("README.md")
    changelog = _repo_text("CHANGELOG.md")
    publishing = _repo_text("docs/releases/PUBLISHING.md")
    plan = _repo_text("docs/planning/PLAN.md")
    scope = _repo_text("docs/planning/V0_13_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    release_gate_jobs = re.findall(r"^  (v0_\d+-release-gate):", workflow, flags=re.MULTILINE)

    assert pyproject["project"]["version"] == "0.18.0"
    assert release_gate_jobs == ["v0_18-release-gate"]
    assert "python -m pytest tests/test_v0_18_release_gate.py" in workflow
    assert "v0_13-release-gate" not in workflow

    assert "## 0.13.0" in changelog
    assert "V0.18" in readme
    assert "compute_periodic_window_coverage" in readme
    assert "diagnose_uniform_translation_consistency" in readme
    assert "package version: `0.18.0`" in readiness
    assert "git tag: `v0.18.0`" in readiness
    assert "Do not run TestPyPI or PyPI publishing for `v0.18`" in readiness
    assert "including `v0.18.0`" in publishing
    assert "V0.18 is complete" in plan
    assert "Milestone 6: COMPLETE" in scope
    assert "`v0.13` - Public orbit and coverage diagnostics" in roadmap
    assert "**Status:** Completed" in roadmap


def test_v0_13_release_gate_invariant_diagnostics_are_documented_and_submodule_only() -> None:
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    invariants_module = importlib.import_module("pdelie.invariants")

    assert hasattr(invariants_module, "compute_periodic_window_coverage")
    assert hasattr(invariants_module, "diagnose_uniform_translation_consistency")
    assert not hasattr(pdelie, "compute_periodic_window_coverage")
    assert not hasattr(pdelie, "diagnose_uniform_translation_consistency")
    assert "pdelie.invariants.compute_periodic_window_coverage" in api_stability
    assert "pdelie.invariants.diagnose_uniform_translation_consistency" in api_stability
    assert "do not construct augmented datasets" in api_stability


def test_v0_13_release_gate_representative_coverage_and_consistency_claims() -> None:
    domain_length = 2.0 * np.pi
    x = np.linspace(0.0, domain_length, 8, endpoint=False)
    coverage = compute_periodic_window_coverage(
        x=x,
        windows=[{"start": 0.0, "width": domain_length / 8.0}],
        shifts=[domain_length / 8.0],
    )

    assert json.loads(json.dumps(coverage)) == coverage
    assert coverage["summary_type"] == "periodic_window_coverage"
    assert coverage["coverage_convention"] == "preimage_of_fixed_window_under_translation"
    assert coverage["shift_convention"] == "field_shift_then_fixed_window"
    np.testing.assert_allclose(coverage["inferred_domain_length"], domain_length)
    assert coverage["coverage_counts"] == [0, 0, 0, 0, 0, 0, 0, 1]

    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=13013)
    consistency = diagnose_uniform_translation_consistency(
        field,
        shifts=[0.0, domain_length],
        residual_evaluator=HeatResidualEvaluator(),
    )

    assert json.loads(json.dumps(consistency)) == consistency
    assert consistency["summary_type"] == "uniform_translation_consistency"
    assert consistency["residual_evaluator"] == "HeatResidualEvaluator"
    for report in consistency["shift_reports"]:
        assert report["dims_preserved"] is True
        assert report["shape_preserved"] is True
        assert report["coords_preserved"] is True
        assert report["metadata_preserved"] is True
        assert report["var_names_preserved"] is True
        assert report["mask_preserved"] is True
        assert report["inverse_passed"] is True
        assert report["period_wrap_passed"] is True
        assert report["residual_stability_passed"] is True
        assert report["provenance_operation"] == "invariant_apply"
        assert report["provenance_construction_method"] == "uniform_translation"


def test_v0_13_release_gate_no_deferred_surface_leaked() -> None:
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
        "build_translation_orbit_views",
        "compute_coverage_diagnostics",
        "compute_weak_derivatives",
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
