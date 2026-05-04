from __future__ import annotations

import importlib
import json

import pdelie

from tests._helpers.weak_reaction_diffusion_feasibility import run_internal_fisher_kpp_weak_feasibility


def test_internal_fisher_kpp_weak_feasibility_is_identity_first_and_json_only() -> None:
    report = run_internal_fisher_kpp_weak_feasibility()

    assert json.loads(json.dumps(report, allow_nan=False)) == report
    assert report["summary_schema_version"] == "0.1"
    assert report["summary_type"] == "weak_reaction_diffusion_feasibility"
    assert report["visibility"] == "internal_diagnostic_only"
    assert report["pde"] == "reaction_diffusion_fisher_kpp"
    assert report["quadrature_rule"] == "composite_simpson_tensor_product_v1"
    assert report["conclusion"] == "diagnostic_only"
    assert report["all_identity_tests_passed"] is True

    identity_tests = report["identity_tests"]
    assert set(identity_tests) == {
        "constant_field",
        "manufactured_fisher_kpp_smooth_field",
        "pure_space_fourier_integration_by_parts",
        "pure_time_sign",
    }
    for diagnostics in identity_tests.values():
        assert diagnostics["passed"] is True
        assert diagnostics["abs_error"] <= report["identity_tolerance"]


def test_internal_fisher_kpp_weak_feasibility_does_not_leak_public_surface() -> None:
    residuals_module = importlib.import_module("pdelie.residuals")
    reporting_module = importlib.import_module("pdelie.reporting")

    assert not hasattr(pdelie, "evaluate_weak_reaction_diffusion_residual")
    assert not hasattr(residuals_module, "evaluate_weak_reaction_diffusion_residual")
    assert not hasattr(residuals_module, "WeakReactionDiffusionResidualEvaluator")
    assert not hasattr(residuals_module, "compute_weak_derivatives")
    assert not hasattr(reporting_module, "summarize_wsindy_design_matrix")
    assert not hasattr(reporting_module, "summarize_weak_sparse_recovery")
