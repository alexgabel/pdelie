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
    "compute_periodic_window_coverage",
    "compute_spectral_fd_derivatives",
    "diagnose_generator_family_closure",
    "diagnose_uniform_translation_consistency",
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
    "run_orbit_coverage_diagnostics_example",
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
    "WeakKSResidualEvaluator",
    "WeakBurgersResidualEvaluator",
    "WeakHeatResidualEvaluator",
    "WeakKdVResidualEvaluator",
    "augment_translation_orbit",
    "build_translation_orbit_views",
    "compute_coverage_diagnostics",
    "compute_weak_derivatives",
    "evaluate_weak_kdv_residual",
    "evaluate_weak_ks_residual",
    "from_pdebench",
    "from_the_well",
    "generate_ks_1d_field_batch",
    "generate_ks_feasibility_field_batch",
    "load_pdebench",
    "load_the_well",
    "sample_kdv_mode_coefficients",
    "summarize_orbit_coverage",
    "summarize_orbit_coverage_feasibility",
}
_DEFERRED_API_STABILITY_NAMES = {
    "pdelie.data.augment_translation_orbit",
    "pdelie.data.build_translation_orbit_views",
    "pdelie.data.compute_coverage_diagnostics",
    "pdelie.data.from_pdebench",
    "pdelie.data.from_the_well",
    "pdelie.data.generate_ks_1d_field_batch",
    "pdelie.data.load_pdebench",
    "pdelie.data.load_the_well",
    "pdelie.reporting.summarize_orbit_coverage",
    "pdelie.reporting.summarize_orbit_coverage_feasibility",
    "pdelie.residuals.KSResidualEvaluator",
    "pdelie.residuals.KuramotoSivashinskyResidualEvaluator",
    "pdelie.residuals.WeakKSResidualEvaluator",
    "pdelie.residuals.evaluate_weak_ks_residual",
    "pdelie.symmetry.OperatorSymmetry",
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
_V0_13_INVARIANT_APIS = {
    "pdelie.invariants.compute_periodic_window_coverage",
    "pdelie.invariants.diagnose_uniform_translation_consistency",
}


def _api_stability_text() -> str:
    return (Path(__file__).resolve().parents[1] / "docs/specs/API_STABILITY.md").read_text(encoding="utf-8")


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def test_api_stability_doc_covers_current_stable_runtime_surface() -> None:
    text = _api_stability_text()

    for api_name in sorted(
        _V0_10_REPORTING_APIS
        | _V0_8_WEAK_APIS
        | _V0_9_KDV_APIS
        | _V0_11_DERIVATIVE_APIS
        | _V0_12_REPORTING_APIS
        | _V0_13_INVARIANT_APIS
    ):
        assert api_name in text

    assert "does not add a stable public Kuramoto-Sivashinsky data generator or residual evaluator" in text
    assert "these APIs have no root `pdelie` exports" in text
    assert "not canonical objects, artifact schemas, manuscript-table generators, or figure/rendering APIs" in text
    assert "do not construct augmented datasets, orbit views, training branches" in text
    assert "weak-form derivatives and weak-form methods beyond the frozen `v0.8` weak residual report slice" in text
    assert "operator symmetry" in text


def test_api_stability_doc_does_not_promote_deferred_v0_13_surfaces() -> None:
    text = _api_stability_text()

    for api_name in sorted(_DEFERRED_API_STABILITY_NAMES):
        assert api_name not in text

    assert "PDEBench" not in text
    assert "The Well" not in text
    assert "multidimensional grids" not in text
    assert "nonuniform grids" not in text
    assert "augment_translation_orbit" not in text
    assert "build_translation_orbit_views" not in text


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
        "pdelie.examples": {
            "run_heat_vertical_slice_example",
            "run_kdv_vertical_slice_example",
            "run_orbit_coverage_diagnostics_example",
        },
        "pdelie.invariants": {
            "InvariantApplier",
            "compute_periodic_window_coverage",
            "diagnose_uniform_translation_consistency",
        },
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
        importlib.import_module("pdelie.invariants"),
        importlib.import_module("pdelie.reporting"),
        importlib.import_module("pdelie.residuals"),
        importlib.import_module("pdelie.symmetry"),
    ]

    for module in modules:
        for name in sorted(_DEFERRED_OR_PRIVATE_NAMES):
            assert not hasattr(module, name), f"{module.__name__}.{name}"


def test_v0_13_planning_docs_record_public_diagnostics_and_no_augmentation_scope() -> None:
    plan = _repo_text("docs/planning/PLAN.md")
    scope = _repo_text("docs/planning/V0_13_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")

    assert "**Status:** COMPLETE" in plan
    assert "Milestone 2 - Periodic Coverage Diagnostic" in plan
    assert "pdelie.invariants.compute_periodic_window_coverage" in plan
    assert "Milestone 3 - Translation Consistency Diagnostic" in plan
    assert "pdelie.invariants.diagnose_uniform_translation_consistency" in plan
    assert "diagnostics support invariant/finite-transform workflows but do not construct augmented datasets" in plan
    assert "## Milestone 5 - API / Public-surface Audit" in plan
    assert "no public augmentation utilities landed" in plan
    assert "## Milestone 6 - Release Gate and Readiness" in plan
    assert "updated CI so the current explicit release gate is `v0_13-release-gate`" in plan
    assert "- Milestone 6: COMPLETE" in plan

    assert "diagnostics support invariant/finite-transform workflows but do not construct augmented datasets" in scope
    assert "stable public augmentation utilities" in scope
    assert "pdelie.invariants.compute_periodic_window_coverage" in scope
    assert "pdelie.invariants.diagnose_uniform_translation_consistency" in scope
    assert "- Milestone 4: COMPLETE" in scope
    assert "- Milestone 5: COMPLETE" in scope
    assert "- Milestone 6: COMPLETE" in scope

    assert "`v0.13` is the completed public orbit/coverage diagnostics release" in roadmap
    assert "do not construct augmented datasets" in roadmap
    assert "- no new PDE" in roadmap
