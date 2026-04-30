from __future__ import annotations

import importlib
from pathlib import Path

import pdelie


_ROOT_RUNTIME_NAMES = {
    "InvariantApplier",
    "add_gaussian_noise",
    "build_translation_canonical_discovery_inputs",
    "coerce_generator_family",
    "compare_generator_spans",
    "compute_spectral_fd_derivatives",
    "diagnose_generator_family_closure",
    "evaluate_discovery_recovery",
    "evaluate_weak_burgers_residual",
    "evaluate_weak_heat_residual",
    "export_generator_family_manifest",
    "fit_pysindy_discovery",
    "fit_translation_generator",
    "from_numpy",
    "from_xarray",
    "generate_burgers_1d_field_batch",
    "generate_heat_1d_field_batch",
    "generate_kdv_1d_field_batch",
    "import_generator_family_manifest",
    "plot_closure_diagnostics",
    "plot_generator_coefficients",
    "plot_generator_symbolic_summary",
    "plot_span_diagnostics",
    "plot_verification_curve",
    "render_generator_family",
    "run_heat_vertical_slice_example",
    "run_kdv_vertical_slice_example",
    "split_batch_train_heldout",
    "subsample_time",
    "subsample_x",
    "summarize_generator_fit_diagnostics",
    "summarize_generator_family",
    "summarize_recovery_grid",
    "summarize_residual_batch",
    "summarize_verification_report",
    "summarize_vertical_slice",
    "summarize_weak_residual_report",
    "to_pysindy_trajectories",
    "to_sympy_component_expressions",
}
_DEFERRED_OR_PRIVATE_NAMES = {
    "OperatorSymmetry",
    "KSResidualEvaluator",
    "KuramotoSivashinskyResidualEvaluator",
    "WeakBurgersResidualEvaluator",
    "WeakHeatResidualEvaluator",
    "WeakKdVResidualEvaluator",
    "compute_weak_derivatives",
    "evaluate_weak_kdv_residual",
    "from_pdebench",
    "from_the_well",
    "generate_ks_1d_field_batch",
    "generate_ks_feasibility_field_batch",
    "load_pdebench",
    "load_the_well",
    "sample_kdv_mode_coefficients",
}
_V0_10_REPORTING_APIS = {
    "pdelie.reporting.summarize_residual_batch",
    "pdelie.reporting.summarize_weak_residual_report",
    "pdelie.reporting.summarize_generator_family",
    "pdelie.reporting.summarize_verification_report",
    "pdelie.reporting.summarize_vertical_slice",
}
_V0_8_WEAK_APIS = {
    "pdelie.residuals.evaluate_weak_heat_residual",
    "pdelie.residuals.evaluate_weak_burgers_residual",
}
_V0_9_KDV_APIS = {
    "pdelie.derivatives.compute_spectral_fd_derivatives(field, *, max_spatial_order=2)",
    "pdelie.data.generate_kdv_1d_field_batch",
    "pdelie.residuals.KdVResidualEvaluator",
}
_V0_11_DERIVATIVE_APIS = {
    "pdelie.derivatives.compute_spectral_fd_derivatives(field, *, max_spatial_order=4)",
}
_V0_12_REPORTING_APIS = {
    "pdelie.reporting.summarize_generator_fit_diagnostics",
}


def _api_stability_text() -> str:
    return (Path(__file__).resolve().parents[1] / "docs/specs/API_STABILITY.md").read_text(encoding="utf-8")


def test_api_stability_doc_covers_current_stable_runtime_surface() -> None:
    text = _api_stability_text()

    for api_name in sorted(
        _V0_10_REPORTING_APIS
        | _V0_8_WEAK_APIS
        | _V0_9_KDV_APIS
        | _V0_11_DERIVATIVE_APIS
        | _V0_12_REPORTING_APIS
    ):
        assert api_name in text

    assert "does not add a stable public Kuramoto-Sivashinsky data generator or residual evaluator" in text
    assert "these APIs have no root `pdelie` exports" in text
    assert "not canonical objects, artifact schemas, manuscript-table generators, or figure/rendering APIs" in text
    assert "weak-form derivatives and weak-form methods beyond the frozen `v0.8` weak residual report slice" in text
    assert "operator symmetry" in text


def test_root_package_still_exposes_only_stable_canonical_surface() -> None:
    for name in sorted(_ROOT_RUNTIME_NAMES | _DEFERRED_OR_PRIVATE_NAMES):
        assert not hasattr(pdelie, name), name


def test_required_runtime_submodule_apis_remain_importable() -> None:
    required_by_module = {
        "pdelie.data": {
            "add_gaussian_noise",
            "from_numpy",
            "from_xarray",
            "generate_burgers_1d_field_batch",
            "generate_heat_1d_field_batch",
            "generate_kdv_1d_field_batch",
            "split_batch_train_heldout",
            "subsample_time",
            "subsample_x",
        },
        "pdelie.derivatives": {"compute_spectral_fd_derivatives"},
        "pdelie.discovery": {
            "build_translation_canonical_discovery_inputs",
            "evaluate_discovery_recovery",
            "fit_pysindy_discovery",
            "summarize_recovery_grid",
            "to_pysindy_trajectories",
        },
        "pdelie.examples": {"run_heat_vertical_slice_example", "run_kdv_vertical_slice_example"},
        "pdelie.invariants": {"InvariantApplier"},
        "pdelie.portability": {
            "coerce_generator_family",
            "export_generator_family_manifest",
            "import_generator_family_manifest",
        },
        "pdelie.reporting": {
            "summarize_generator_fit_diagnostics",
            "summarize_generator_family",
            "summarize_residual_batch",
            "summarize_verification_report",
            "summarize_vertical_slice",
            "summarize_weak_residual_report",
        },
        "pdelie.residuals": {
            "BurgersResidualEvaluator",
            "HeatResidualEvaluator",
            "KdVResidualEvaluator",
            "ResidualEvaluator",
            "evaluate_weak_burgers_residual",
            "evaluate_weak_heat_residual",
        },
        "pdelie.symmetry": {
            "compare_generator_spans",
            "diagnose_generator_family_closure",
            "fit_translation_generator",
            "render_generator_family",
            "to_sympy_component_expressions",
        },
        "pdelie.viz": {
            "plot_closure_diagnostics",
            "plot_generator_coefficients",
            "plot_generator_symbolic_summary",
            "plot_span_diagnostics",
            "plot_verification_curve",
        },
    }

    for module_name, names in required_by_module.items():
        module = importlib.import_module(module_name)
        for name in sorted(names):
            assert hasattr(module, name), f"{module_name}.{name}"


def test_deferred_and_private_names_are_not_public_submodule_exports() -> None:
    modules = [
        importlib.import_module("pdelie.data"),
        importlib.import_module("pdelie.derivatives"),
        importlib.import_module("pdelie.discovery"),
        importlib.import_module("pdelie.reporting"),
        importlib.import_module("pdelie.residuals"),
        importlib.import_module("pdelie.symmetry"),
    ]

    for module in modules:
        for name in sorted(_DEFERRED_OR_PRIVATE_NAMES):
            assert not hasattr(module, name), f"{module.__name__}.{name}"
