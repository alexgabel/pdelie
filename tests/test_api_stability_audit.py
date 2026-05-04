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
    "run_kdv_scope_decision_example",
    "run_multi_generator_diagnostics_example",
    "run_formula_generator_validation_example",
    "run_generator_confidence_report_example",
    "run_downstream_discovery_contracts_example",
    "run_external_data_readiness_example",
    "run_split_leakage_provenance_example",
    "run_weak_form_supportability_example",
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
    "summarize_field_batch_readiness",
    "summarize_formula_generator_family",
    "summarize_generator_confidence",
    "summarize_downstream_discovery_workflow",
    "summarize_split_leakage_provenance",
    "summarize_discovery_bridge_output",
    "summarize_discovery_result",
    "summarize_generator_family",
    "summarize_invariant_workflow",
    "summarize_recovery_grid",
    "summarize_residual_batch",
    "summarize_verification_report",
    "summarize_vertical_slice",
    "summarize_weak_residual_report",
    "summarize_weak_form_supportability",
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
    "from_xarray_dataset",
    "from_the_well",
    "load_dataset",
    "load_field_batch",
    "generate_ks_1d_field_batch",
    "generate_configurable_kdv_1d_field_batch",
    "generate_general_kdv_1d_field_batch",
    "generate_kdv_1d_field_batch_from_initial_condition",
    "generate_ks_feasibility_field_batch",
    "generate_reaction_advection_diffusion_1d_field_batch",
    "generate_variable_coefficient_advection_diffusion_1d_field_batch",
    "load_pdebench",
    "load_the_well",
    "materialize_uniform_translation_orbit",
    "sample_kdv_mode_coefficients",
    "ConfigurableKdVResidualEvaluator",
    "split_orbit_train_heldout",
    "split_leakage_enforcer",
    "summarize_generator_confidence_score",
    "summarize_field_batch_readiness_score",
    "summarize_leakage_prevention",
    "summarize_orbit_coverage",
    "summarize_orbit_coverage_feasibility",
    "train_test_translation_orbit_split",
    "fit_multi_generator_family",
    "fit_generator_family_span",
    "MultiGeneratorInvariantChart",
    "build_multi_generator_orbit",
    "compose_bch",
    "integrate_generator_flow",
    "build_multi_parameter_orbit_chart",
}
_DEFERRED_API_STABILITY_NAMES = {
    "pdelie.data.augment_translation_orbit",
    "pdelie.data.build_translation_orbit_dataset",
    "pdelie.data.build_translation_orbit_views",
    "pdelie.data.compute_coverage_diagnostics",
    "pdelie.data.from_pdebench",
    "pdelie.data.from_xarray_dataset",
    "pdelie.data.from_the_well",
    "pdelie.data.load_dataset",
    "pdelie.data.load_field_batch",
    "pdelie.data.generate_configurable_kdv_1d_field_batch",
    "pdelie.data.generate_general_kdv_1d_field_batch",
    "pdelie.data.generate_kdv_1d_field_batch_from_initial_condition",
    "pdelie.data.generate_ks_1d_field_batch",
    "pdelie.data.generate_reaction_advection_diffusion_1d_field_batch",
    "pdelie.data.generate_variable_coefficient_advection_diffusion_1d_field_batch",
    "pdelie.data.load_pdebench",
    "pdelie.data.load_the_well",
    "pdelie.reporting.summarize_generator_confidence_score",
    "pdelie.reporting.summarize_field_batch_readiness_score",
    "pdelie.reporting.summarize_leakage_prevention",
    "pdelie.reporting.summarize_orbit_coverage",
    "pdelie.reporting.summarize_orbit_coverage_feasibility",
    "pdelie.residuals.KSResidualEvaluator",
    "pdelie.residuals.KuramotoSivashinskyResidualEvaluator",
    "pdelie.residuals.ConfigurableKdVResidualEvaluator",
    "pdelie.residuals.WeakKSResidualEvaluator",
    "pdelie.residuals.WeakReactionDiffusionResidualEvaluator",
    "pdelie.residuals.evaluate_weak_ks_residual",
    "pdelie.residuals.evaluate_weak_reaction_diffusion_residual",
    "pdelie.residuals.evaluate_weak_advection_diffusion_residual",
    "pdelie.residuals.WeakAdvectionDiffusionResidualEvaluator",
    "pdelie.symmetry.OperatorSymmetry",
    "pdelie.symmetry.CallableGeneratorFamily",
    "pdelie.symmetry.fit_multi_generator_family",
    "pdelie.symmetry.fit_generator_family_span",
    "pdelie.symmetry.MultiGeneratorInvariantChart",
    "pdelie.symmetry.build_multi_generator_orbit",
    "pdelie.symmetry.compose_bch",
    "pdelie.symmetry.integrate_generator_flow",
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
_V0_20_CONFIDENCE_REPORTING_APIS = {
    "pdelie.reporting.summarize_generator_confidence",
    "summary_type = \"generator_confidence\"",
    "confidence_label",
}
_V0_21_FIELD_READINESS_APIS = {
    "pdelie.reporting.summarize_field_batch_readiness",
    "summary_type = \"field_batch_readiness\"",
    "readiness_label",
    "pdelie.examples.run_external_data_readiness_example",
}
_V0_22_DOWNSTREAM_CONTRACT_APIS = {
    "pdelie.discovery.summarize_discovery_bridge_output",
    "pdelie.discovery.summarize_discovery_result",
    "pdelie.reporting.summarize_downstream_discovery_workflow",
    "pdelie.examples.run_downstream_discovery_contracts_example",
    "summary_type = \"discovery_bridge_output\"",
    "summary_type = \"discovery_result\"",
    "summary_type = \"downstream_discovery_workflow\"",
}
_V0_23_SPLIT_PROVENANCE_APIS = {
    "pdelie.reporting.summarize_split_leakage_provenance",
    "pdelie.examples.run_split_leakage_provenance_example",
    "summary_type = \"split_leakage_provenance\"",
    "risk_label",
    "traceable_overlap",
}
_V0_24_WEAK_SUPPORTABILITY_APIS = {
    "pdelie.reporting.summarize_weak_form_supportability",
    "pdelie.examples.run_weak_form_supportability_example",
    "summary_type = \"weak_form_supportability\"",
    "supportability_label",
    "supported_existing_slice",
    "diagnostic_only",
}
_V0_25_KDV_SCOPE_DECISION_APIS = {
    "pdelie.examples.run_kdv_scope_decision_example",
    "summary_type = \"kdv_scope_decision_example\"",
    "current_frozen_supported",
    "deferred_no_go",
}
_V0_27_MULTI_GENERATOR_DIAGNOSTICS_APIS = {
    "pdelie.examples.run_multi_generator_diagnostics_example",
    "summary_type = \"multi_generator_diagnostics_example\"",
    "family_rank_status = \"rank_deficient\"",
    "closure_required=True|False",
    "multi_generator_diagnostics_feasible_fitting_deferred",
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
        | _V0_20_CONFIDENCE_REPORTING_APIS
        | _V0_21_FIELD_READINESS_APIS
        | _V0_22_DOWNSTREAM_CONTRACT_APIS
        | _V0_23_SPLIT_PROVENANCE_APIS
        | _V0_24_WEAK_SUPPORTABILITY_APIS
        | _V0_25_KDV_SCOPE_DECISION_APIS
        | _V0_27_MULTI_GENERATOR_DIAGNOSTICS_APIS
    ):
        assert api_name in text

    assert "does not add a stable public Kuramoto-Sivashinsky data generator or residual evaluator" in text
    assert "these APIs have no root `pdelie` exports" in text
    assert "not canonical objects, artifact schemas, manuscript-table generators, or figure/rendering APIs" in text
    assert "do not construct augmented datasets, orbit datasets, or transformed `FieldBatch` collections" in text
    assert "time-translation diagnostics remain deferred" in text
    assert (
        "weak-form derivatives and weak-form methods beyond the frozen `v0.8` weak residual report slice "
        "and the `v0.24` weak supportability reporting layer"
    ) in text
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
            "summarize_discovery_bridge_output",
            "summarize_discovery_result",
            "summarize_recovery_grid",
            "to_pysindy_trajectories",
        },
        "pdelie.examples": {
            "run_formula_generator_validation_example",
            "run_generator_confidence_report_example",
            "run_downstream_discovery_contracts_example",
            "run_external_data_readiness_example",
            "run_split_leakage_provenance_example",
            "run_weak_form_supportability_example",
            "run_advection_diffusion_vertical_slice_example",
            "run_heat_vertical_slice_example",
            "run_invariant_workflow_summary_example",
            "run_kdv_scope_decision_example",
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
            "summarize_downstream_discovery_workflow",
            "summarize_formula_generator_family",
            "summarize_field_batch_readiness",
            "summarize_generator_confidence",
            "summarize_generator_fit_diagnostics",
            "summarize_generator_family",
            "summarize_invariant_workflow",
            "summarize_residual_batch",
            "summarize_split_leakage_provenance",
            "summarize_verification_report",
            "summarize_vertical_slice",
            "summarize_weak_residual_report",
            "summarize_weak_form_supportability",
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


def test_v0_22_planning_docs_record_downstream_discovery_contracts_and_non_goals() -> None:
    scope = _repo_text("docs/planning/V0_22_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")

    assert "Downstream Discovery Contracts" in scope
    assert "pdelie.discovery.summarize_discovery_bridge_output" in scope
    assert "pdelie.discovery.summarize_discovery_result" in scope
    assert "pdelie.reporting.summarize_downstream_discovery_workflow" in scope
    assert "pdelie.examples.run_downstream_discovery_contracts_example" in scope
    assert "feature-keyed" in scope
    assert "heldout-leakage detection" in scope
    assert "file loaders" in scope
    assert "train/test split policy" in scope
    assert "- Milestone 4: COMPLETE" in scope
    assert "- Milestone 5: COMPLETE" in scope
    assert "- Milestone 6: COMPLETE" in scope

    assert "`v0.22` is the completed downstream discovery contracts release" in roadmap
    assert "downstream discovery contracts" in roadmap
    assert "- no split management or heldout-leakage detection" in roadmap


def test_v0_23_planning_docs_record_split_provenance_and_non_goals() -> None:
    scope = _repo_text("docs/planning/V0_23_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")

    assert "Split / Leakage Provenance Diagnostics" in scope
    assert "pdelie.reporting.summarize_split_leakage_provenance" in scope
    assert "pdelie.examples.run_split_leakage_provenance_example" in scope
    assert "traceable_overlap" in scope
    assert "missing_provenance" in scope
    assert "no split creation" in scope
    assert "no leakage prevention" in scope
    assert "- Milestone 4: COMPLETE" in scope
    assert "- Milestone 5: COMPLETE" in scope
    assert "- Milestone 6: COMPLETE" in scope

    assert "`v0.23` is the completed split/leakage provenance diagnostics release" in roadmap
    assert "split/leakage provenance diagnostics" in roadmap
    assert "- no split management or leakage prevention" in roadmap


def test_v0_24_planning_docs_record_weak_supportability_and_non_goals() -> None:
    scope = _repo_text("docs/planning/V0_24_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")

    assert "Weak-Form Supportability Reset" in scope
    assert "pdelie.reporting.summarize_weak_form_supportability" in scope
    assert "pdelie.examples.run_weak_form_supportability_example" in scope
    assert "supported_existing_slice" in scope
    assert "diagnostic_only" in scope
    assert "does not implement WSINDy" in scope
    assert "weak derivative backend" in scope
    assert "- Milestone 4: COMPLETE" in scope
    assert "- Milestone 5: COMPLETE" in scope
    assert "- Milestone 6: COMPLETE" in scope

    assert "`v0.24` is the completed weak-form supportability reset" in roadmap
    assert "weak-form supportability reset" in roadmap
    assert "- no weak derivative backend" in roadmap


def test_v0_25_planning_docs_record_kdv_scope_decision_and_non_goals() -> None:
    scope = _repo_text("docs/planning/V0_25_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")

    assert "KdV Scope Decision" in scope
    assert "current_frozen_supported" in scope
    assert "deferred_no_go" in scope
    assert "custom KdV initial conditions remain deferred" in scope
    assert "weak KdV remains deferred" in scope
    assert "- Milestone 4: COMPLETE" in scope
    assert "- Milestone 5: COMPLETE" in scope
    assert "- Milestone 6: COMPLETE" in scope

    assert "`v0.25` is the completed KdV scope decision release" in roadmap
    assert "keep KdV public APIs frozen" in roadmap
    assert "- no weak KdV" in roadmap


def test_v0_26_planning_docs_record_ks_revisit_decision_and_non_goals() -> None:
    plan = _repo_text("docs/planning/PLAN.md")
    scope = _repo_text("docs/planning/V0_26_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    api_stability = _api_stability_text()

    assert "KS Revisit Decision" in scope
    assert "current_no_go_reference_fallback" in scope
    assert "direct_strong_candidate_for_v0_26b_promotion" in scope
    assert "Promotion evidence must come from the frozen primary fixture" in scope
    assert "no public KS residual evaluator" in scope
    assert "no residual-only KS API" in scope
    assert "no weak KS API" in scope
    assert "- Milestone 4: COMPLETE" in scope
    assert "- Milestone 5: COMPLETE" in scope
    assert "- Milestone 6: COMPLETE" in scope

    assert "`v0.26` is the completed Kuramoto-Sivashinsky revisit decision release" in roadmap
    assert "`v0.26b` - KS promotion" in roadmap
    assert "Decision-only note for the frozen `v0.26` KS revisit decision" in api_stability


def test_v0_27_planning_docs_record_multi_generator_diagnostics_decision_and_non_goals() -> None:
    plan = _repo_text("docs/planning/PLAN.md")
    scope = _repo_text("docs/planning/V0_27_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    api_stability = _api_stability_text()

    assert "**Status:** COMPLETE" in plan
    assert "multi-generator diagnostics decision" in plan
    assert "multi_generator_diagnostics_feasible_fitting_deferred" in plan
    assert "no public multi-generator fitting API" in plan
    assert "- Milestone 6: COMPLETE" in plan

    assert "Multi-Generator Diagnostics Decision" in scope
    assert "bracket convention" in scope
    assert "family_rank_status" in scope
    assert "rank_deficient" in scope
    assert "closure_required=True|False" in scope
    assert "no BCH composition" in scope
    assert "no exponential-map finite-flow integration" in scope
    assert "- Milestone 4: COMPLETE" in scope
    assert "- Milestone 5: COMPLETE" in scope
    assert "- Milestone 6: COMPLETE" in scope

    assert "`v0.27` - Multi-generator diagnostics decision" in roadmap
    assert "no public multi-generator fitting" in roadmap
    assert "Runtime public API and behavior updates for the frozen `v0.27`" in api_stability
    assert "pdelie.examples.run_multi_generator_diagnostics_example" in api_stability
    assert "multi_generator_diagnostics_feasible_fitting_deferred" in api_stability
