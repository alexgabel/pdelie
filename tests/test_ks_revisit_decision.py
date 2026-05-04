from __future__ import annotations

import importlib
import json

import pdelie
from tests._helpers.ks_revisit_decision import (
    KS_REVISIT_EPSILONS,
    KS_REVISIT_SEEDS,
    cached_ks_revisit_decision_report,
    run_ks_revisit_decision_report,
)


def test_ks_revisit_decision_report_is_strict_json_and_deterministic() -> None:
    first = cached_ks_revisit_decision_report()
    second = run_ks_revisit_decision_report()

    assert json.loads(json.dumps(first, allow_nan=False)) == first
    assert json.loads(json.dumps(second, allow_nan=False)) == second
    assert first["summary_schema_version"] == "0.1"
    assert first["summary_type"] == "ks_revisit_decision"
    assert first["visibility"] == "internal_diagnostic_only"
    assert first["decision_label"] == second["decision_label"]
    assert first["primary_fixture"]["evidence_label"] == second["primary_fixture"]["evidence_label"]
    assert first["primary_fixture"]["reference_fallback_used"] == second["primary_fixture"]["reference_fallback_used"]


def test_ks_revisit_primary_fixture_records_reference_fallback_no_go() -> None:
    report = cached_ks_revisit_decision_report()
    primary = report["primary_fixture"]
    assert isinstance(primary, dict)

    assert report["decision_label"] == "current_no_go_reference_fallback"
    assert primary["evidence_label"] == "reference_fallback"
    assert primary["reference_fallback_used"] is True
    assert primary["fallback_reason"] == "svd_translation_span_drift"
    assert primary["residual_max_abs"] < report["thresholds"]["residual_max_abs"]
    assert primary["residual_rms"] < report["thresholds"]["residual_rms"]
    assert primary["first_verification_error"] < report["thresholds"]["verification_first_error"]
    assert primary["classification"] != "failed"
    assert primary["confidence"]["summary_type"] == "generator_confidence"
    assert primary["confidence"]["confidence_label"] == "qualified"
    assert primary["confidence"]["fit_diagnostics"]["reference_fallback_used"] is True


def test_ks_revisit_minimal_matrix_is_diagnostic_only_and_not_best_of_sweep_promotion() -> None:
    report = cached_ks_revisit_decision_report()
    matrix = report["minimal_matrix"]
    assert isinstance(matrix, dict)

    seed_sweep = matrix["seed_sweep"]
    epsilon_sweep = matrix["epsilon_sweep"]
    resolution_variant = matrix["resolution_variant"]
    assert isinstance(seed_sweep, list)
    assert isinstance(epsilon_sweep, list)
    assert isinstance(resolution_variant, dict)
    assert len(seed_sweep) == len(KS_REVISIT_SEEDS)
    assert len(epsilon_sweep) == len(KS_REVISIT_EPSILONS)
    assert matrix["variant_count"] == len(seed_sweep) + len(epsilon_sweep) + 1
    assert matrix["all_cases_diagnostic_only"] is True
    assert report["promotion_policy"]["best_of_sweep_promotion_allowed"] is False
    assert report["promotion_policy"]["v0_26_promotes_public_ks_runtime"] is False
    assert report["promotion_policy"]["v0_26b_reserved_for_actual_promotion"] is True

    for case in [*seed_sweep, *epsilon_sweep, resolution_variant]:
        assert case["evidence_label"] in {
            "direct_svd_in_tolerance",
            "reference_fallback",
            "mixed",
        }
        assert case["classification"] != "failed"
        assert case["transform_mode"] == "uniform_translation"


def test_ks_revisit_decision_keeps_ks_runtime_surface_private() -> None:
    data_module = importlib.import_module("pdelie.data")
    residuals_module = importlib.import_module("pdelie.residuals")
    examples_module = importlib.import_module("pdelie.examples")

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
    for name in sorted(forbidden):
        assert not hasattr(pdelie, name), f"pdelie.{name}"
    for module in (data_module, residuals_module, examples_module):
        for name in sorted(forbidden):
            assert not hasattr(module, name), f"{module.__name__}.{name}"
