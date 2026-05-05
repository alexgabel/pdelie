from __future__ import annotations

import importlib
import json
import re
import tomllib
from pathlib import Path

import pdelie
from tests._helpers.ks_revisit_decision import cached_ks_revisit_decision_report


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")
def test_v0_26_release_gate_records_decision_only_ks_revisit() -> None:
    report = cached_ks_revisit_decision_report()

    assert json.loads(json.dumps(report, allow_nan=False)) == report
    assert report["summary_type"] == "ks_revisit_decision"
    assert report["visibility"] == "internal_diagnostic_only"
    assert report["decision_label"] == "current_no_go_reference_fallback"
    assert "direct_strong_candidate_for_v0_26b_promotion" in report["decision_labels"]
    assert report["promotion_policy"]["v0_26_promotes_public_ks_runtime"] is False
    assert report["promotion_policy"]["v0_26b_reserved_for_actual_promotion"] is True
    assert report["promotion_policy"]["best_of_sweep_promotion_allowed"] is False
    assert report["primary_fixture"]["confidence"]["summary_type"] == "generator_confidence"
    assert report["primary_fixture"]["confidence"]["confidence_label"] == "qualified"
    assert report["primary_fixture"]["fit_diagnostics"]["reference_fallback_used"] is True
    assert report["primary_fixture"]["fit_diagnostics"]["evidence_label"] == "reference_fallback"


def test_v0_26_release_gate_api_stability_does_not_promote_ks_runtime_contracts() -> None:
    api_stability = _repo_text("docs/specs/API_STABILITY.md")

    assert "v0.26" in api_stability
    assert "KS revisit decision" in api_stability
    assert "direct_strong_candidate_for_v0_26b_promotion" in api_stability
    assert "does not add a stable public Kuramoto-Sivashinsky data generator or residual evaluator" in api_stability
    assert "pdelie.data.generate_ks_1d_field_batch" not in api_stability
    assert "pdelie.residuals.KSResidualEvaluator" not in api_stability
    assert "pdelie.residuals.KuramotoSivashinskyResidualEvaluator" not in api_stability


def test_v0_26_release_gate_no_ks_runtime_surface_leaked() -> None:
    forbidden = {
        "generate_ks_1d_field_batch",
        "generate_ks_feasibility_field_batch",
        "KSResidualEvaluator",
        "KuramotoSivashinskyResidualEvaluator",
        "WeakKSResidualEvaluator",
        "evaluate_weak_ks_residual",
        "run_ks_status_example",
        "run_ks_vertical_slice_example",
    }

    modules = [
        importlib.import_module("pdelie.data"),
        importlib.import_module("pdelie.examples"),
        importlib.import_module("pdelie.residuals"),
        importlib.import_module("pdelie.reporting"),
        importlib.import_module("pdelie.symmetry"),
    ]
    for name in sorted(forbidden):
        assert not hasattr(pdelie, name), f"pdelie.{name}"
    for module in modules:
        for name in sorted(forbidden):
            assert not hasattr(module, name), f"{module.__name__}.{name}"
