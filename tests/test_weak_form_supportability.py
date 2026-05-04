from __future__ import annotations

import copy
import json

import numpy as np
import pytest

from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.errors import SchemaValidationError
from pdelie.reporting import (
    summarize_residual_batch,
    summarize_weak_form_supportability,
    summarize_weak_residual_report,
)
from pdelie.residuals import (
    BurgersResidualEvaluator,
    HeatResidualEvaluator,
    evaluate_weak_burgers_residual,
    evaluate_weak_heat_residual,
)


_WEAK_FORM_SUPPORTABILITY_KEYS = {
    "summary_schema_version",
    "summary_type",
    "supportability_label",
    "component_statuses",
    "weak_report",
    "weak_report_metrics",
    "weak_contract",
    "quadrature_rule",
    "strong_residual",
    "robustness",
    "imported_parity",
    "feasibility",
    "thresholds",
    "missing_evidence",
    "policy",
    "extra_metrics",
}


def _heat_weak_report() -> dict[str, object]:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=17, num_points=32, seed=2401)
    return evaluate_weak_heat_residual(field)


def _burgers_weak_report() -> dict[str, object]:
    field = generate_burgers_1d_field_batch(batch_size=1, num_times=17, num_points=32, seed=2402)
    return evaluate_weak_burgers_residual(field)


def test_summarize_weak_form_supportability_supports_heat_and_burgers_public_slice() -> None:
    for weak_report in (_heat_weak_report(), _burgers_weak_report()):
        summary = summarize_weak_form_supportability(
            weak_report=weak_report,
            thresholds={
                "finite_required": True,
                "min_weak_rows": 1,
                "max_skipped_fraction": 0.0,
            },
        )

        assert set(summary) == _WEAK_FORM_SUPPORTABILITY_KEYS
        assert json.loads(json.dumps(summary, allow_nan=False)) == summary
        assert summary["summary_schema_version"] == "0.1"
        assert summary["summary_type"] == "weak_form_supportability"
        assert summary["supportability_label"] == "supported_existing_slice"
        assert summary["weak_report"]["summary_type"] == "weak_residual_report"
        assert summary["weak_contract"]["quadrature_rule"] == "composite_tensor_product_trapezoidal_native_window"
        assert summary["quadrature_rule"] == "composite_tensor_product_trapezoidal_native_window"
        assert summary["component_statuses"]["weak_report"]["status"] == "passed"
        assert summary["component_statuses"]["weak_contract"]["status"] == "passed"
        assert summary["policy"]["supports_wsindy"] is False
        assert summary["policy"]["supports_weak_derivative_backend"] is False


def test_summarize_weak_form_supportability_accepts_precomputed_weak_and_strong_summaries() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=17, num_points=32, seed=2403)
    weak_summary = summarize_weak_residual_report(evaluate_weak_heat_residual(field))
    residual = HeatResidualEvaluator().evaluate(field, compute_spectral_fd_derivatives(field))
    strong_summary = summarize_residual_batch(residual)

    summary = summarize_weak_form_supportability(
        weak_report_summary=weak_summary,
        strong_residual_summary=strong_summary,
    )

    assert summary["supportability_label"] == "supported_existing_slice"
    assert summary["strong_residual"]["summary_type"] == "residual_batch"
    assert summary["component_statuses"]["strong_residual"]["status"] == "passed"


def test_summarize_weak_form_supportability_reports_diagnostic_only_for_internal_feasibility() -> None:
    feasibility = {
        "summary_schema_version": "0.1",
        "summary_type": "weak_reaction_diffusion_feasibility",
        "visibility": "internal_diagnostic_only",
        "pde": "reaction_diffusion_fisher_kpp",
        "quadrature_rule": "composite_simpson_tensor_product_v1",
        "conclusion": "diagnostic_only",
    }

    summary = summarize_weak_form_supportability(feasibility=feasibility)

    assert summary["supportability_label"] == "diagnostic_only"
    assert summary["quadrature_rule"] == "composite_simpson_tensor_product_v1"
    assert summary["component_statuses"]["feasibility"]["status"] == "warning"


def test_summarize_weak_form_supportability_fails_configured_weak_metric() -> None:
    summary = summarize_weak_form_supportability(
        weak_report=_heat_weak_report(),
        thresholds={"weak_report_max_abs": 1e-12},
    )

    assert summary["supportability_label"] == "failed"
    assert summary["component_statuses"]["weak_report"]["status"] == "failed"


def test_summarize_weak_form_supportability_enforces_contract_skipped_fraction() -> None:
    summary = summarize_weak_form_supportability(
        weak_contract={
            "schema_version": "0.1",
            "equation": "heat_1d",
            "equation_form": "nonconservative",
            "test_function_family": "separable_quartic_bump_beta",
            "test_function_order": 4,
            "operator_order_supported": 2,
            "integration_by_parts_depth": 2,
            "boundary_vanishing_order": 1,
            "patch_shape": [5, 9],
            "patch_stride": [1, 1],
            "quadrature_rule": "composite_tensor_product_trapezoidal_native_window",
            "normalization": "none",
            "valid_window_policy": "interior_time_periodic_x_wrapped",
            "row_count": 8,
            "skipped_patch_count": 2,
            "finite_value_policy": "finite_window_residuals_required",
        },
        thresholds={"max_skipped_fraction": 0.1},
    )

    assert summary["supportability_label"] == "failed"
    assert summary["component_statuses"]["weak_contract"]["status"] == "failed"


def test_summarize_weak_form_supportability_checks_robustness_and_imported_parity_thresholds() -> None:
    summary = summarize_weak_form_supportability(
        weak_report=_heat_weak_report(),
        robustness={"cases": [{"case_name": "clean"}, {"case_name": "coarse"}]},
        imported_parity={"max_abs_difference": 1e-8, "max_relative_difference": 2e-8},
        thresholds={
            "robustness_required_cases": ["clean", "coarse"],
            "imported_parity_abs_tol": 1e-6,
            "imported_parity_rel_tol": 1e-6,
        },
    )

    assert summary["supportability_label"] == "supported_existing_slice"
    assert summary["component_statuses"]["robustness"]["status"] == "passed"
    assert summary["component_statuses"]["imported_parity"]["status"] == "passed"


def test_summarize_weak_form_supportability_fails_missing_robustness_case() -> None:
    summary = summarize_weak_form_supportability(
        weak_report=_heat_weak_report(),
        robustness={"cases": [{"case_name": "clean"}]},
        thresholds={"robustness_required_cases": ["clean", "coarse"]},
    )

    assert summary["supportability_label"] == "failed"
    assert summary["component_statuses"]["robustness"]["status"] == "failed"


def test_summarize_weak_form_supportability_missing_weak_evidence_is_insufficient() -> None:
    field = generate_burgers_1d_field_batch(batch_size=1, num_times=17, num_points=32, seed=2404)
    residual = BurgersResidualEvaluator().evaluate(field, compute_spectral_fd_derivatives(field))

    summary = summarize_weak_form_supportability(strong_residual=residual)

    assert summary["supportability_label"] == "insufficient_evidence"
    assert summary["component_statuses"]["strong_residual"]["status"] == "passed"
    assert summary["component_statuses"]["weak_report"]["status"] == "unavailable"


def test_summarize_weak_form_supportability_does_not_mutate_inputs() -> None:
    weak_report = _heat_weak_report()
    original = copy.deepcopy(weak_report)

    summarize_weak_form_supportability(weak_report=weak_report)

    assert weak_report["equation"] == original["equation"]
    np.testing.assert_allclose(weak_report["window_residuals"], original["window_residuals"])
    assert weak_report["diagnostics"] == original["diagnostics"]


def test_summarize_weak_form_supportability_rejects_malformed_contracts_and_thresholds() -> None:
    with pytest.raises(SchemaValidationError, match="weak_contract"):
        summarize_weak_form_supportability(
            weak_contract={
                "quadrature_rule": float("nan"),
            }
        )

    with pytest.raises(SchemaValidationError, match="unsupported weak-form keys"):
        summarize_weak_form_supportability(thresholds={"weak_confidence_score": 0.5})

    with pytest.raises(SchemaValidationError, match="finite_required"):
        summarize_weak_form_supportability(thresholds={"finite_required": 1.0})


def test_summarize_weak_form_supportability_rejects_ambiguous_inputs() -> None:
    weak_report = _heat_weak_report()
    weak_summary = summarize_weak_residual_report(weak_report)

    with pytest.raises(SchemaValidationError, match="either weak_report or weak_report_summary"):
        summarize_weak_form_supportability(weak_report=weak_report, weak_report_summary=weak_summary)
