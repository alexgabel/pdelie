from __future__ import annotations

import importlib
import json
import re
import tomllib
from pathlib import Path

import numpy as np

import pdelie
from pdelie.contracts import GeneratorFamily, _translation_generator_basis_spec
from pdelie.reporting import summarize_generator_fit_diagnostics


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def _diagnostic_generator() -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.asarray([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={
            "fit_mode": "svd",
            "training_epsilon": 1e-4,
            "basis": ["1", "t", "x", "u"],
            "basis_delta_norms": {"1": 1.0, "t": 2.0, "x": 3.0, "u": 4.0},
            "design_column_norms": {"1": 1.0, "t": 2.0, "x": 3.0, "u": 4.0},
            "singular_values": [4.0, 2.0, 1.0],
            "condition_number": 4.0,
            "fit_residual": 1e-8,
            "min_delta_basis": "1",
            "selected_coefficients": [1.0, 0.0, 0.0, 0.0],
            "svd_coefficients": [1.0, 0.0, 0.0, 0.0],
            "selected_span_distance": 0.0,
            "svd_span_distance": 0.0,
            "reference_fallback_used": False,
            "fallback_reason": None,
            "evidence_label": "direct_svd_in_tolerance",
        },
    )


def test_v0_12_release_record_remains_intact() -> None:
    readiness = _repo_text("docs/releases/V0_12_RELEASE_READINESS.md")
    changelog = _repo_text("CHANGELOG.md")
    scope = _repo_text("docs/planning/V0_12_SCOPE.md")
    roadmap = _repo_text("docs/planning/archive/ROADMAP_HISTORY.md")

    assert "## 0.12.0" in changelog
    assert "package version: `0.12.0`" in readiness
    assert "git tag: `v0.12.0`" in readiness
    assert "Do not run TestPyPI or PyPI publishing for `v0.12`" in readiness
    assert "Milestone 6: COMPLETE" in scope
    assert "`v0.12` - Diagnostics and supportability hardening" in roadmap
    assert "**Status:** Completed" in roadmap


def test_v0_12_release_gate_fit_diagnostic_helper_is_documented_and_submodule_only() -> None:
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    reporting_module = importlib.import_module("pdelie.reporting")
    summary = summarize_generator_fit_diagnostics(_diagnostic_generator())

    assert hasattr(reporting_module, "summarize_generator_fit_diagnostics")
    assert not hasattr(pdelie, "summarize_generator_fit_diagnostics")
    assert "pdelie.reporting.summarize_generator_fit_diagnostics" in api_stability
    assert "Runtime public API for the frozen `v0.12` Milestone 2 slice" in api_stability

    assert json.loads(json.dumps(summary)) == summary
    assert summary["summary_type"] == "generator_fit_diagnostics"
    assert summary["singular_values"] == [4.0, 2.0, 1.0]
    assert summary["condition_number"] == 4.0
    assert summary["selected_span_distance"] == 0.0
    assert summary["svd_span_distance"] == 0.0
    assert summary["reference_fallback_used"] is False
    assert summary["fallback_reason"] is None
    assert summary["evidence_label"] == "direct_svd_in_tolerance"


def test_v0_12_release_gate_internal_diagnostics_remain_non_public() -> None:
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    modules = [
        pdelie,
        importlib.import_module("pdelie.data"),
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
        "summarize_orbit_coverage",
        "summarize_orbit_coverage_feasibility",
        "WeakKSResidualEvaluator",
    }

    for module in modules:
        for name in sorted(forbidden_names):
            assert not hasattr(module, name), f"{module.__name__}.{name}"

    for name in sorted(forbidden_names):
        assert f"pdelie.{name}" not in api_stability


def test_v0_12_release_gate_does_not_promote_ks_or_orbit_coverage_in_docs() -> None:
    readme = _repo_text("README.md")
    readiness = _repo_text("docs/releases/V0_12_RELEASE_READINESS.md")
    scope = _repo_text("docs/planning/V0_12_SCOPE.md")

    assert "internal KS diagnostic sweep" in readme
    assert "no stable KS runtime API is promoted" in readme
    assert "no stable KS runtime API is promoted" in readiness
    assert "no public orbit/coverage helper" in readiness
    assert "no public augmentation utility" in readiness
    assert "M3 internal KS diagnostics and M4 orbit/coverage diagnostics remain internal" in scope
