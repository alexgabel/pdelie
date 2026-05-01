from __future__ import annotations

import importlib
import sys

import numpy as np
import pytest

import pdelie
from pdelie import (
    DerivativeBatch,
    FieldBatch,
    GeneratorFamily,
    InvariantMapSpec,
    ResidualBatch,
    ResidualEvaluator,
    VerificationReport,
)


def test_stable_public_api_is_importable() -> None:
    assert FieldBatch is not None
    assert DerivativeBatch is not None
    assert ResidualBatch is not None
    assert ResidualEvaluator is not None
    assert GeneratorFamily is not None
    assert InvariantMapSpec is not None
    assert VerificationReport is not None


def test_runtime_package_api_is_importable() -> None:
    from pdelie.data import (
        add_gaussian_noise,
        from_numpy,
        from_xarray,
        generate_kdv_1d_field_batch,
        split_batch_train_heldout,
        subsample_time,
        subsample_x,
    )
    from pdelie.discovery import (
        build_translation_canonical_discovery_inputs,
        evaluate_discovery_recovery,
        fit_pysindy_discovery,
        summarize_recovery_grid,
        to_pysindy_trajectories,
    )
    from pdelie.invariants import (
        InvariantApplier,
        compute_periodic_window_coverage,
        diagnose_uniform_translation_consistency,
        summarize_uniform_translation_orbit,
    )
    from pdelie.portability import (
        coerce_generator_family,
        export_generator_family_manifest,
        import_generator_family_manifest,
    )
    from pdelie.residuals import KdVResidualEvaluator, evaluate_weak_burgers_residual, evaluate_weak_heat_residual
    from pdelie.reporting import (
        summarize_generator_fit_diagnostics,
        summarize_generator_family,
        summarize_invariant_workflow,
        summarize_residual_batch,
        summarize_verification_report,
        summarize_vertical_slice,
        summarize_weak_residual_report,
    )
    from pdelie.symmetry import (
        compare_generator_spans,
        diagnose_generator_family_closure,
        render_generator_family,
        to_sympy_component_expressions,
    )
    from pdelie.viz import (
        plot_closure_diagnostics,
        plot_generator_coefficients,
        plot_generator_symbolic_summary,
        plot_span_diagnostics,
        plot_verification_curve,
    )

    assert add_gaussian_noise is not None
    assert from_numpy is not None
    assert from_xarray is not None
    assert generate_kdv_1d_field_batch is not None
    assert split_batch_train_heldout is not None
    assert subsample_time is not None
    assert subsample_x is not None
    assert InvariantApplier is not None
    assert compute_periodic_window_coverage is not None
    assert diagnose_uniform_translation_consistency is not None
    assert summarize_uniform_translation_orbit is not None
    assert KdVResidualEvaluator is not None
    assert evaluate_weak_burgers_residual is not None
    assert evaluate_weak_heat_residual is not None
    assert summarize_generator_fit_diagnostics is not None
    assert summarize_generator_family is not None
    assert summarize_invariant_workflow is not None
    assert summarize_residual_batch is not None
    assert summarize_verification_report is not None
    assert summarize_vertical_slice is not None
    assert summarize_weak_residual_report is not None
    assert build_translation_canonical_discovery_inputs is not None
    assert evaluate_discovery_recovery is not None
    assert fit_pysindy_discovery is not None
    assert summarize_recovery_grid is not None
    assert to_pysindy_trajectories is not None
    assert coerce_generator_family is not None
    assert export_generator_family_manifest is not None
    assert import_generator_family_manifest is not None
    assert compare_generator_spans is not None
    assert diagnose_generator_family_closure is not None
    assert render_generator_family is not None
    assert to_sympy_component_expressions is not None
    assert plot_generator_coefficients is not None
    assert plot_generator_symbolic_summary is not None
    assert plot_verification_curve is not None
    assert plot_span_diagnostics is not None
    assert plot_closure_diagnostics is not None


def test_root_package_does_not_export_runtime_invariant_applier() -> None:
    assert not hasattr(pdelie, "InvariantApplier")
    assert not hasattr(pdelie, "add_gaussian_noise")
    assert not hasattr(pdelie, "build_translation_canonical_discovery_inputs")
    assert not hasattr(pdelie, "build_translation_orbit_dataset")
    assert not hasattr(pdelie, "build_translation_orbit_views")
    assert not hasattr(pdelie, "augment_translation_orbit")
    assert not hasattr(pdelie, "compute_periodic_window_coverage")
    assert not hasattr(pdelie, "compute_weak_derivatives")
    assert not hasattr(pdelie, "compute_coverage_diagnostics")
    assert not hasattr(pdelie, "diagnose_uniform_translation_consistency")
    assert not hasattr(pdelie, "diagnose_time_translation_consistency")
    assert not hasattr(pdelie, "summarize_uniform_translation_orbit")
    assert not hasattr(pdelie, "evaluate_weak_burgers_residual")
    assert not hasattr(pdelie, "evaluate_weak_heat_residual")
    assert not hasattr(pdelie, "evaluate_weak_ks_residual")
    assert not hasattr(pdelie, "evaluate_discovery_recovery")
    assert not hasattr(pdelie, "fit_pysindy_discovery")
    assert not hasattr(pdelie, "from_pdebench")
    assert not hasattr(pdelie, "from_numpy")
    assert not hasattr(pdelie, "from_the_well")
    assert not hasattr(pdelie, "from_xarray")
    assert not hasattr(pdelie, "split_batch_train_heldout")
    assert not hasattr(pdelie, "subsample_time")
    assert not hasattr(pdelie, "subsample_x")
    assert not hasattr(pdelie, "summarize_recovery_grid")
    assert not hasattr(pdelie, "summarize_generator_fit_diagnostics")
    assert not hasattr(pdelie, "summarize_generator_family")
    assert not hasattr(pdelie, "summarize_invariant_workflow")
    assert not hasattr(pdelie, "summarize_orbit_coverage")
    assert not hasattr(pdelie, "summarize_orbit_coverage_feasibility")
    assert not hasattr(pdelie, "summarize_residual_batch")
    assert not hasattr(pdelie, "summarize_verification_report")
    assert not hasattr(pdelie, "summarize_vertical_slice")
    assert not hasattr(pdelie, "summarize_weak_residual_report")
    assert not hasattr(pdelie, "to_pysindy_trajectories")
    assert not hasattr(pdelie, "coerce_generator_family")
    assert not hasattr(pdelie, "export_generator_family_manifest")
    assert not hasattr(pdelie, "import_generator_family_manifest")
    assert not hasattr(pdelie, "KdVResidualEvaluator")
    assert not hasattr(pdelie, "generate_kdv_1d_field_batch")
    assert not hasattr(pdelie, "generate_ks_1d_field_batch")
    assert not hasattr(pdelie, "generate_ks_feasibility_field_batch")
    assert not hasattr(pdelie, "KSResidualEvaluator")
    assert not hasattr(pdelie, "KuramotoSivashinskyResidualEvaluator")
    assert not hasattr(pdelie, "WeakKSResidualEvaluator")
    assert not hasattr(pdelie, "OperatorSymmetry")
    assert not hasattr(pdelie, "run_invariant_workflow_summary_example")
    assert not hasattr(pdelie, "run_kdv_vertical_slice_example")
    assert not hasattr(pdelie, "run_orbit_coverage_diagnostics_example")
    assert not hasattr(pdelie, "sample_kdv_mode_coefficients")
    assert not hasattr(pdelie, "compare_generator_spans")
    assert not hasattr(pdelie, "diagnose_generator_family_closure")
    assert not hasattr(pdelie, "render_generator_family")
    assert not hasattr(pdelie, "to_sympy_component_expressions")
    assert not hasattr(pdelie, "plot_generator_coefficients")
    assert not hasattr(pdelie, "plot_generator_symbolic_summary")
    assert not hasattr(pdelie, "plot_verification_curve")
    assert not hasattr(pdelie, "plot_span_diagnostics")
    assert not hasattr(pdelie, "plot_closure_diagnostics")


def test_invariants_package_runtime_api_matches_frozen_milestone_surface() -> None:
    invariants_module = importlib.import_module("pdelie.invariants")

    assert hasattr(invariants_module, "InvariantApplier")
    assert hasattr(invariants_module, "compute_periodic_window_coverage")
    assert hasattr(invariants_module, "diagnose_uniform_translation_consistency")
    assert hasattr(invariants_module, "summarize_uniform_translation_orbit")
    assert not hasattr(invariants_module, "augment_translation_orbit")
    assert not hasattr(invariants_module, "build_translation_orbit_dataset")
    assert not hasattr(invariants_module, "build_translation_orbit_views")
    assert not hasattr(invariants_module, "diagnose_time_translation_consistency")
    assert not hasattr(invariants_module, "InvariantMapSpec")


def test_data_package_runtime_api_matches_current_frozen_surface() -> None:
    data_module = importlib.import_module("pdelie.data")

    assert hasattr(data_module, "add_gaussian_noise")
    assert hasattr(data_module, "from_numpy")
    assert hasattr(data_module, "from_xarray")
    assert hasattr(data_module, "generate_kdv_1d_field_batch")
    assert hasattr(data_module, "subsample_time")
    assert hasattr(data_module, "subsample_x")
    assert hasattr(data_module, "split_batch_train_heldout")
    assert not hasattr(data_module, "augment_translation_orbit")
    assert not hasattr(data_module, "build_translation_orbit_views")
    assert not hasattr(data_module, "compute_coverage_diagnostics")
    assert not hasattr(data_module, "from_pdebench")
    assert not hasattr(data_module, "from_the_well")
    assert not hasattr(data_module, "generate_ks_1d_field_batch")
    assert not hasattr(data_module, "generate_ks_feasibility_field_batch")
    assert not hasattr(data_module, "load_pdebench")
    assert not hasattr(data_module, "load_the_well")
    assert not hasattr(data_module, "sample_kdv_mode_coefficients")


def test_residuals_package_runtime_api_matches_current_frozen_surface() -> None:
    residuals_module = importlib.import_module("pdelie.residuals")

    assert hasattr(residuals_module, "HeatResidualEvaluator")
    assert hasattr(residuals_module, "BurgersResidualEvaluator")
    assert hasattr(residuals_module, "KdVResidualEvaluator")
    assert hasattr(residuals_module, "ResidualEvaluator")
    assert hasattr(residuals_module, "evaluate_weak_heat_residual")
    assert hasattr(residuals_module, "evaluate_weak_burgers_residual")
    assert not hasattr(residuals_module, "compute_weak_derivatives")
    assert not hasattr(residuals_module, "evaluate_weak_kdv_residual")
    assert not hasattr(residuals_module, "evaluate_weak_ks_residual")
    assert not hasattr(residuals_module, "WeakHeatResidualEvaluator")
    assert not hasattr(residuals_module, "WeakBurgersResidualEvaluator")
    assert not hasattr(residuals_module, "WeakKdVResidualEvaluator")
    assert not hasattr(residuals_module, "WeakKSResidualEvaluator")
    assert not hasattr(residuals_module, "WeakKuramotoSivashinskyResidualEvaluator")
    assert not hasattr(residuals_module, "KSResidualEvaluator")
    assert not hasattr(residuals_module, "KuramotoSivashinskyResidualEvaluator")
    assert not hasattr(residuals_module, "KDVResidualEvaluator")
    assert not hasattr(residuals_module, "KdvResidualEvaluator")


def test_reporting_package_runtime_api_matches_frozen_m2_surface() -> None:
    reporting_module = importlib.import_module("pdelie.reporting")

    assert hasattr(reporting_module, "summarize_generator_fit_diagnostics")
    assert hasattr(reporting_module, "summarize_generator_family")
    assert hasattr(reporting_module, "summarize_invariant_workflow")
    assert not hasattr(reporting_module, "summarize_orbit_coverage")
    assert not hasattr(reporting_module, "summarize_orbit_coverage_feasibility")
    assert hasattr(reporting_module, "summarize_residual_batch")
    assert hasattr(reporting_module, "summarize_verification_report")
    assert hasattr(reporting_module, "summarize_vertical_slice")
    assert hasattr(reporting_module, "summarize_weak_residual_report")


def test_examples_package_runtime_api_matches_current_frozen_surface() -> None:
    examples_module = importlib.import_module("pdelie.examples")

    assert hasattr(examples_module, "run_heat_vertical_slice_example")
    assert hasattr(examples_module, "run_invariant_workflow_summary_example")
    assert hasattr(examples_module, "run_kdv_vertical_slice_example")
    assert hasattr(examples_module, "run_orbit_coverage_diagnostics_example")
    assert not hasattr(examples_module, "run_ks_vertical_slice_example")
    assert not hasattr(examples_module, "run_orbit_coverage_feasibility")


def test_discovery_package_runtime_api_matches_frozen_milestone_surface() -> None:
    discovery_module = importlib.import_module("pdelie.discovery")

    assert hasattr(discovery_module, "build_translation_canonical_discovery_inputs")
    assert hasattr(discovery_module, "evaluate_discovery_recovery")
    assert hasattr(discovery_module, "fit_pysindy_discovery")
    assert hasattr(discovery_module, "summarize_recovery_grid")
    assert hasattr(discovery_module, "to_pysindy_trajectories")
    assert not hasattr(discovery_module, "_fit_pysindy_smoke")


def test_portability_package_runtime_api_matches_frozen_m2_surface() -> None:
    portability_module = importlib.import_module("pdelie.portability")

    assert hasattr(portability_module, "coerce_generator_family")
    assert hasattr(portability_module, "export_generator_family_manifest")
    assert hasattr(portability_module, "import_generator_family_manifest")
    assert not hasattr(portability_module, "GeneratorFamily")


def test_symmetry_package_runtime_api_matches_frozen_m4_surface() -> None:
    symmetry_module = importlib.import_module("pdelie.symmetry")

    assert hasattr(symmetry_module, "fit_translation_generator")
    assert hasattr(symmetry_module, "diagnose_generator_family_closure")
    assert hasattr(symmetry_module, "compare_generator_spans")
    assert hasattr(symmetry_module, "render_generator_family")
    assert hasattr(symmetry_module, "to_sympy_component_expressions")
    assert not hasattr(symmetry_module, "OperatorSymmetry")
    assert not hasattr(symmetry_module, "build_translation_orbit_views")


def test_viz_package_runtime_api_matches_frozen_m5_surface() -> None:
    viz_module = importlib.import_module("pdelie.viz")

    assert hasattr(viz_module, "plot_generator_coefficients")
    assert hasattr(viz_module, "plot_generator_symbolic_summary")
    assert hasattr(viz_module, "plot_verification_curve")
    assert hasattr(viz_module, "plot_span_diagnostics")
    assert hasattr(viz_module, "plot_closure_diagnostics")


def test_viz_package_import_succeeds_without_matplotlib_until_renderer_use(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import_module = importlib.import_module

    def _fake_import_module(name: str, package: str | None = None):
        if name == "matplotlib" or name.startswith("matplotlib."):
            raise ModuleNotFoundError("No module named 'matplotlib'", name="matplotlib")
        return original_import_module(name, package)

    for module_name in list(sys.modules):
        if module_name == "pdelie.viz" or module_name.startswith("pdelie.viz."):
            sys.modules.pop(module_name)

    monkeypatch.setattr(importlib, "import_module", _fake_import_module)

    viz_module = importlib.import_module("pdelie.viz")
    report = VerificationReport(
        norm="relative_l2",
        epsilon_values=np.logspace(-4, -1, 7),
        error_curve=np.logspace(-7, -4, 7),
        classification="exact",
        diagnostics={},
    )

    assert hasattr(viz_module, "plot_verification_curve")
    with pytest.raises(ImportError, match="Matplotlib is required for pdelie\\.viz"):
        viz_module.plot_verification_curve(report)
