from __future__ import annotations

import importlib
import json
import re
import tomllib
from pathlib import Path

import numpy as np

import pdelie
from pdelie import GeneratorFamily
from pdelie.examples import run_multi_generator_diagnostics_example
from pdelie.symmetry import compare_generator_spans, diagnose_generator_family_closure
from tests._helpers.multi_generator_diagnostics import run_internal_multi_generator_fit_probe


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def _x_basis_spec() -> dict[str, object]:
    return {
        "variables": ["x"],
        "component_names": ["xi"],
        "basis_terms": [
            {"label": "1", "powers": [0]},
            {"label": "x", "powers": [1]},
        ],
        "component_ordering": ["xi"],
        "term_ordering": ["1", "x"],
        "layout": "component_major",
    }


def _family(coefficients: list[list[float]]) -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="algebraic_fixture",
        coefficients=np.asarray(coefficients, dtype=float),
        basis_spec=_x_basis_spec(),
        normalization="runtime_fixture",
        diagnostics={},
    )


def test_v0_27_release_gate_metadata_docs_and_ci_are_aligned() -> None:
    pyproject = tomllib.loads(_repo_text("pyproject.toml"))
    workflow = _repo_text(".github/workflows/ci.yml")
    readiness = _repo_text("docs/releases/V0_28_RELEASE_READINESS.md")
    readme = _repo_text("README.md")
    changelog = _repo_text("CHANGELOG.md")
    publishing = _repo_text("docs/releases/PUBLISHING.md")
    plan = _repo_text("docs/planning/PLAN.md")
    scope = _repo_text("docs/planning/V0_27_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    release_gate_jobs = re.findall(r"^  (v0_\d+-release-gate):", workflow, flags=re.MULTILINE)

    assert pyproject["project"]["version"] == "0.28.0"
    assert release_gate_jobs == ["v0_28-release-gate"]
    assert "python -m pytest tests/test_v0_28_release_gate.py" in workflow
    assert "v0_26-release-gate" not in workflow

    assert "## 0.28.0" in changelog
    assert "V0.27" in readme
    assert "multi-generator diagnostics decision" in readme
    assert "package version: `0.28.0`" in readiness
    assert "git tag: `v0.28.0`" in readiness
    assert "Do not publish to TestPyPI or PyPI for `v0.28.0`" in readiness
    assert "including `v0.28.0`" in publishing
    assert "Milestone 6: COMPLETE" in plan
    assert "Milestone 6: COMPLETE" in scope
    assert "`v0.27` - Multi-generator diagnostics decision" in roadmap


def test_v0_27_release_gate_example_records_diagnostic_only_decision() -> None:
    result = run_multi_generator_diagnostics_example()

    assert json.loads(json.dumps(result, allow_nan=False)) == result
    assert result["summary_type"] == "multi_generator_diagnostics_example"
    assert result["decision"]["conclusion"] == "multi_generator_diagnostics_feasible_fitting_deferred"
    assert result["decision"]["public_promotion_decision"] == "no_public_multi_generator_fitting_or_invariant_action"
    assert (
        result["algebraic_diagnostics"]["closed_affine_x"]["structure_constants"]["structure_constant_error"]
        <= 1e-12
    )
    assert result["algebraic_diagnostics"]["rank_deficient_affine"]["family_rank_status"] == "rank_deficient"
    assert result["pde_context_diagnostics"]["closed_affine_x"]["conclusion"] == "partially_validated"
    assert result["fit_probe_diagnostics"]["label"] == "fit_probe_diagnostic_only"
    assert result["extra_metrics"]["no_bch_composition"] is True


def test_v0_27_release_gate_rank_deficient_families_are_diagnostic_not_exceptions() -> None:
    full = _family([[1.0, 0.0], [0.0, 1.0]])
    rank_deficient = _family([[1.0, 0.0], [2.0, 0.0]])

    closure = diagnose_generator_family_closure(rank_deficient)
    span = compare_generator_spans(full, rank_deficient)

    assert closure["family_rank_status"] == "rank_deficient"
    assert closure["structure_constants"]["status"] == "unavailable"
    assert span["comparison_status"] == "warning"
    assert span["candidate_rank_status"] == "rank_deficient"


def test_v0_27_release_gate_internal_fit_probe_stays_diagnostic_only() -> None:
    report = run_internal_multi_generator_fit_probe()

    assert json.loads(json.dumps(report, allow_nan=False)) == report
    assert report["summary_type"] == "multi_generator_fit_probe"
    assert report["visibility"] == "internal_test_only"
    assert report["label"] == "fit_probe_diagnostic_only"
    assert report["passed"] is True
    assert report["future_promotion_candidate"] is False
    assert report["public_api_promoted"] is False
    assert report["probe_policy"]["no_public_import_path"] is True
    assert report["probe_policy"]["no_runtime_example"] is True
    assert report["probe_policy"]["no_best_of_sweep_promotion"] is True
    for case in report["cases"]:
        assert case["span_report"]["comparison_status"] == "passed"
        assert case["span_report"]["projection_residual"]["summary"] <= 1e-12


def test_v0_27_release_gate_no_deferred_surface_leaked() -> None:
    forbidden = {
        "fit_multi_generator_family",
        "fit_generator_family_span",
        "MultiGeneratorInvariantChart",
        "build_multi_generator_orbit",
        "compose_bch",
        "integrate_generator_flow",
        "build_multi_parameter_orbit_chart",
        "run_multi_generator_feasibility_example",
    }

    modules = [
        importlib.import_module("pdelie.discovery"),
        importlib.import_module("pdelie.examples"),
        importlib.import_module("pdelie.invariants"),
        importlib.import_module("pdelie.reporting"),
        importlib.import_module("pdelie.symmetry"),
    ]
    for name in sorted(forbidden | {"run_multi_generator_diagnostics_example"}):
        assert not hasattr(pdelie, name), f"pdelie.{name}"
    for module in modules:
        for name in sorted(forbidden):
            assert not hasattr(module, name), f"{module.__name__}.{name}"

    examples_module = importlib.import_module("pdelie.examples")
    assert hasattr(examples_module, "run_multi_generator_diagnostics_example")
