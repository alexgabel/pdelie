from __future__ import annotations

import importlib
import json

import numpy as np

import pdelie
from tests._helpers.kdv_scope_decision import (
    run_internal_kdv_scope_matrix,
    run_internal_weak_kdv_identity_checks,
)


def test_internal_kdv_scope_matrix_is_json_compatible_and_keeps_public_surface_frozen() -> None:
    report = run_internal_kdv_scope_matrix()
    data_module = importlib.import_module("pdelie.data")
    residuals_module = importlib.import_module("pdelie.residuals")

    assert json.loads(json.dumps(report, allow_nan=False)) == report
    assert report["summary_type"] == "kdv_scope_decision_matrix"
    assert report["visibility"] == "internal_diagnostic_only"
    assert report["conclusion"] == "keep_public_kdv_surface_frozen"

    cases = {case["case_name"]: case for case in report["cases"]}
    assert set(cases) == {"frozen_default", "larger_amplitude", "longer_horizon", "more_modes"}
    assert cases["frozen_default"]["evidence_category"] == "current_frozen_supported"
    assert cases["frozen_default"]["max_abs_residual"] < 1e-2
    assert cases["frozen_default"]["rms_residual"] < 2e-3
    for name in ("larger_amplitude", "longer_horizon", "more_modes"):
        assert cases[name]["evidence_category"] == "diagnostic_only"
        assert cases[name]["finite"] is True
        assert np.isfinite(float(cases[name]["max_abs_residual"]))

    assert not hasattr(pdelie, "generate_general_kdv_1d_field_batch")
    assert not hasattr(data_module, "generate_kdv_1d_field_batch_from_initial_condition")
    assert not hasattr(data_module, "generate_configurable_kdv_1d_field_batch")
    assert not hasattr(residuals_module, "ConfigurableKdVResidualEvaluator")


def test_internal_kdv_custom_initial_condition_and_coefficient_feasibility_are_diagnostic_only() -> None:
    report = run_internal_kdv_scope_matrix()

    custom = report["custom_initial_condition_feasibility"]
    coefficients = report["configurable_coefficient_feasibility"]

    assert custom["visibility"] == "internal_diagnostic_only"
    assert custom["evidence_category"] == "diagnostic_only"
    assert custom["finite"] is True
    assert custom["deterministic"] is True
    assert custom["public_api"]["custom_initial_condition_generator"] is False

    assert coefficients["visibility"] == "internal_diagnostic_only"
    assert coefficients["evidence_category"] == "diagnostic_only"
    assert coefficients["passed"] is True
    assert coefficients["alpha_scaling_abs_error"] <= coefficients["tolerance"]
    assert coefficients["beta_scaling_abs_error"] <= coefficients["tolerance"]
    assert coefficients["public_api"]["configurable_kdv_residual_evaluator"] is False


def test_internal_weak_kdv_identity_checks_are_identity_first_and_test_only() -> None:
    report = run_internal_weak_kdv_identity_checks()
    residuals_module = importlib.import_module("pdelie.residuals")

    assert json.loads(json.dumps(report, allow_nan=False)) == report
    assert report["summary_type"] == "weak_kdv_identity_feasibility"
    assert report["visibility"] == "internal_diagnostic_only"
    assert report["test_function_family"] == "sixth_order_boundary_regular_bump"
    assert report["passed"] is True
    assert report["boundary_abs"] == {"phi": 0.0, "phi_prime": 0.0, "phi_second": 0.0}
    assert report["third_order_integration_by_parts_abs_error"] <= report["tolerance"]
    assert not hasattr(pdelie, "evaluate_weak_kdv_residual")
    assert not hasattr(residuals_module, "evaluate_weak_kdv_residual")
    assert not hasattr(residuals_module, "WeakKdVResidualEvaluator")
    assert not hasattr(residuals_module, "compute_weak_derivatives")
