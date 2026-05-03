from __future__ import annotations

import importlib
from pathlib import Path

import pdelie


_ROOT_RUNTIME_NAMES = {
    "AdvectionDiffusionResidualEvaluator",
    "InvariantApplier",
    "add_gaussian_noise",
    "build_uniform_translation_orbit_batch",
    "build_translation_canonical_discovery_inputs",
    "coerce_generator_family",
    "compare_generator_spans",
    "compute_periodic_window_coverage",
    "compute_spectral_fd_derivatives",
    "diagnose_generator_family_closure",
    "diagnose_uniform_translation_consistency",
    "diagnose_time_translation_consistency",
    "evaluate_discovery_recovery",
    "evaluate_weak_burgers_residual",
    "evaluate_weak_advection_diffusion_residual",
    "evaluate_weak_heat_residual",
    "export_generator_family_manifest",
    "fit_pysindy_discovery",
    "fit_translation_generator",
    "FormulaGeneratorFamily",
    "from_numpy",
    "from_xarray",
    "generate_advection_diffusion_1d_field_batch",
    "generate_burgers_1d_field_batch",
    "generate_heat_1d_field_batch",
    "generate_kdv_1d_field_batch",
    "generate_reaction_diffusion_1d_field_batch",
    "import_generator_family_manifest",
    "plot_closure_diagnostics",
    "plot_generator_coefficients",
    "plot_generator_symbolic_summary",
    "plot_span_diagnostics",
    "plot_verification_curve",
    "render_generator_family",
    "run_heat_vertical_slice_example",
    "run_advection_diffusion_vertical_slice_example",
    "run_formula_generator_validation_example",
    "run_kdv_vertical_slice_example",
    "run_orbit_coverage_diagnostics_example",
    "run_reaction_diffusion_vertical_slice_example",
    "run_invariant_workflow_summary_example",
    "run_symmetry_candidate_validation_example",
    "run_translation_orbit_batch_example",
    "split_batch_train_heldout",
    "subsample_time",
    "subsample_x",
    "summarize_generator_fit_diagnostics",
    "summarize_formula_generator_family",
    "summarize_generator_family",
    "summarize_invariant_workflow",
    "summarize_recovery_grid",
    "summarize_residual_batch",
    "summarize_verification_report",
    "summarize_vertical_slice",
    "summarize_weak_residual_report",
    "summarize_uniform_translation_orbit",
    "to_pysindy_trajectories",
    "to_sympy_component_expressions",
    "validate_symmetry_candidate",
}
_DEFERRED_OR_PRIVATE_NAMES = {
    "CallableGeneratorFamily",
    "OperatorSymmetry",
    "KSResidualEvaluator",
    "KuramotoSivashinskyResidualEvaluator",
    "WeakKSResidualEvaluator",
    "WeakBurgersResidualEvaluator",
    "WeakHeatResidualEvaluator",
    "WeakKdVResidualEvaluator",
    "WeakReactionDiffusionResidualEvaluator",
    "WeakAdvectionDiffusionResidualEvaluator",
    "augment_translation_orbit",
    "build_translation_orbit_dataset",
    "build_translation_orbit_views",
    "compute_coverage_diagnostics",
    "compute_weak_derivatives",
    "evaluate_weak_advection_diffusion_residual",
    "evaluate_weak_kdv_residual",
    "evaluate_weak_ks_residual",
    "evaluate_weak_reaction_diffusion_residual",
    "from_pdebench",
    "from_the_well",
    "generate_ks_1d_field_batch",
    "generate_ks_feasibility_field_batch",
    "generate_reaction_advection_diffusion_1d_field_batch",
    "generate_variable_coefficient_advection_diffusion_1d_field_batch",
    "load_pdebench",
    "load_the_well",
    "materialize_uniform_translation_orbit",
    "sample_kdv_mode_coefficients",
    "split_orbit_train_heldout",
    "summarize_orbit_coverage",
    "summarize_orbit_coverage_feasibility",
    "train_test_translation_orbit_split",
}
_DEFERRED_API_STABILITY_NAMES = {
    "pdelie.data.augment_translation_orbit",
    "pdelie.data.build_translation_orbit_dataset",
    "pdelie.data.build_translation_orbit_views",
    "pdelie.data.compute_coverage_diagnostics",
    "pdelie.data.from_pdebench",
    "pdelie.data.from_the_well",
    "pdelie.data.generate_ks_1d_field_batch",
    "pdelie.data.generate_reaction_advection_diffusion_1d_field_batch",
    "pdelie.data.generate_variable_coefficient_advection_diffusion_1d_field_batch",
    "pdelie.data.load_pdebench",
    "pdelie.data.load_the_well",
    "pdelie.reporting.summarize_orbit_coverage",
    "pdelie.reporting.summarize_orbit_coverage_feasibility",
    "pdelie.residuals.KSResidualEvaluator",
    "pdelie.residuals.KuramotoSivashinskyResidualEvaluator",
    "pdelie.residuals.WeakKSResidualEvaluator",
    "pdelie.residuals.WeakReactionDiffusionResidualEvaluator",
    "pdelie.residuals.evaluate_weak_ks_residual",
    "pdelie.residuals.evaluate_weak_reaction_diffusion_residual",
    "pdelie.residuals.evaluate_weak_advection_diffusion_residual",
    "pdelie.residuals.WeakAdvectionDiffusionResidualEvaluator",
    "pdelie.symmetry.OperatorSymmetry",
    "pdelie.symmetry.CallableGeneratorFamily",
    "pdelie.symmetry.validate_generator_candidate",
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
_V0_14_INVARIANT_WORKFLOW_APIS = {
    "pdelie.invariants.summarize_uniform_translation_orbit",
    "pdelie.reporting.summarize_invariant_workflow",
}
_V0_15_ORBIT_BATCH_APIS = {
    "pdelie.invariants.build_uniform_translation_orbit_batch",
    "pdelie.invariants.OrbitBatchResult",
}
_V0_16_SYMMETRY_VALIDATION_APIS = {
    "pdelie.symmetry.validate_symmetry_candidate",
}
_V0_17_FORMULA_GENERATOR_APIS = {
    "pdelie.symmetry.FormulaGeneratorFamily",
    "pdelie.reporting.summarize_formula_generator_family",
    "candidate_kind = \"formula_generator_family\"",
}
_V0_18_REACTION_DIFFUSION_APIS = {
    "pdelie.data.generate_reaction_diffusion_1d_field_batch",
    "pdelie.residuals.ReactionDiffusionResidualEvaluator",
    "pdelie.examples.run_reaction_diffusion_vertical_slice_example",
    "reaction_diffusion_fisher_kpp",
}
_V0_19_ADVECTION_DIFFUSION_APIS = {
    "pdelie.data.generate_advection_diffusion_1d_field_batch",
    "pdelie.residuals.AdvectionDiffusionResidualEvaluator",
    "pdelie.examples.run_advection_diffusion_vertical_slice_example",
    "advection_diffusion_constant_coefficient",
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
        | _V0_14_INVARIANT_WORKFLOW_APIS
        | _V0_15_ORBIT_BATCH_APIS
        | _V0_16_SYMMETRY_VALIDATION_APIS
        | _V0_17_FORMULA_GENERATOR_APIS
        | _V0_18_REACTION_DIFFUSION_APIS
        | _V0_19_ADVECTION_DIFFUSION_APIS
    ):
        assert api_name in text

    assert "does not add a stable public Kuramoto-Sivashinsky data generator or residual evaluator" in text
    assert "these APIs have no root `pdelie` exports" in text
    assert "not canonical objects, artifact schemas, manuscript-table generators, or figure/rendering APIs" in text
    assert "do not construct augmented datasets, orbit datasets, or transformed `FieldBatch` collections" in text
    assert "time-translation diagnostics remain deferred" in text
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
    assert "build_translation_orbit_dataset" not in text
    assert "diagnose_time_translation_consistency" not in text
    assert "validate_generator_candidate" not in text
    assert "CallableGeneratorFamily" not in text


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
            "generate_advection_diffusion_1d_field_batch",
            "generate_kdv_1d_field_batch",
            "generate_reaction_diffusion_1d_field_batch",
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
            "run_formula_generator_validation_example",
            "run_advection_diffusion_vertical_slice_example",
            "run_heat_vertical_slice_example",
            "run_invariant_workflow_summary_example",
            "run_kdv_vertical_slice_example",
            "run_orbit_coverage_diagnostics_example",
            "run_reaction_diffusion_vertical_slice_example",
            "run_symmetry_candidate_validation_example",
            "run_translation_orbit_batch_example",
        },
        "pdelie.invariants": {
            "InvariantApplier",
            "OrbitBatchResult",
            "build_uniform_translation_orbit_batch",
            "compute_periodic_window_coverage",
            "diagnose_uniform_translation_consistency",
            "summarize_uniform_translation_orbit",
        },
        "pdelie.portability": {
            "coerce_generator_family",
            "export_generator_family_manifest",
            "import_generator_family_manifest",
        },
        "pdelie.reporting": {
            "summarize_formula_generator_family",
            "summarize_generator_fit_diagnostics",
            "summarize_generator_family",
            "summarize_invariant_workflow",
            "summarize_residual_batch",
            "summarize_verification_report",
            "summarize_vertical_slice",
            "summarize_weak_residual_report",
        },
        "pdelie.residuals": {
            "AdvectionDiffusionResidualEvaluator",
            "BurgersResidualEvaluator",
            "HeatResidualEvaluator",
            "KdVResidualEvaluator",
            "ReactionDiffusionResidualEvaluator",
            "ResidualEvaluator",
            "evaluate_weak_burgers_residual",
            "evaluate_weak_heat_residual",
        },
        "pdelie.symmetry": {
            "FormulaGeneratorFamily",
            "compare_generator_spans",
            "diagnose_generator_family_closure",
            "fit_translation_generator",
            "render_generator_family",
            "to_sympy_component_expressions",
            "validate_symmetry_candidate",
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


def test_v0_19_planning_docs_record_advection_diffusion_and_non_goals() -> None:
    plan = _repo_text("docs/planning/PLAN.md")
    scope = _repo_text("docs/planning/V0_19_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")

    assert "**Status:** COMPLETE" in plan
    assert "Milestone 2 - Synthetic Data Generator" in plan
    assert "Milestone 3 - Residual Evaluator" in plan
    assert "pdelie.data.generate_advection_diffusion_1d_field_batch" in plan
    assert "pdelie.residuals.AdvectionDiffusionResidualEvaluator" in plan
    assert "advection_diffusion_constant_coefficient" in plan
    assert "direct_svd_in_tolerance" in plan
    assert "No fallback-backed advection-diffusion claim landed" in plan
    assert "## Milestone 5 - API / Public-surface Audit" in plan
    assert "## Milestone 6 - Release Gate And Readiness" in plan
    assert "updated CI so the current explicit release gate is `v0_19-release-gate`" in plan
    assert "- Milestone 6: COMPLETE" in plan

    assert "Stable Advection-Diffusion Strong Path" in scope
    assert "pdelie.data.generate_advection_diffusion_1d_field_batch" in scope
    assert "pdelie.residuals.AdvectionDiffusionResidualEvaluator" in scope
    assert "pdelie.examples.run_advection_diffusion_vertical_slice_example" in scope
    assert "direct_svd_in_tolerance" in scope
    assert "weak advection-diffusion" in scope
    assert "neural or callable generator APIs" in scope
    assert "- Milestone 4: COMPLETE" in scope
    assert "- Milestone 5: COMPLETE" in scope
    assert "- Milestone 6: COMPLETE" in scope

    assert "`v0.19` is the completed narrow PDE-expansion release" in roadmap
    assert "stable scalar 1D periodic constant-coefficient advection-diffusion strong path" in roadmap
    assert "- no variable-coefficient advection-diffusion" in roadmap
