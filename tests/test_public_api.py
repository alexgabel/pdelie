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
    from pdelie.data import add_gaussian_noise, from_numpy, from_xarray, split_batch_train_heldout, subsample_time, subsample_x
    from pdelie.discovery import (
        build_translation_canonical_discovery_inputs,
        evaluate_discovery_recovery,
        fit_pysindy_discovery,
        summarize_recovery_grid,
        to_pysindy_trajectories,
    )
    from pdelie.invariants import InvariantApplier
    from pdelie.portability import (
        coerce_generator_family,
        export_generator_family_manifest,
        import_generator_family_manifest,
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
    assert split_batch_train_heldout is not None
    assert subsample_time is not None
    assert subsample_x is not None
    assert InvariantApplier is not None
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
    assert not hasattr(pdelie, "evaluate_discovery_recovery")
    assert not hasattr(pdelie, "fit_pysindy_discovery")
    assert not hasattr(pdelie, "from_numpy")
    assert not hasattr(pdelie, "from_xarray")
    assert not hasattr(pdelie, "split_batch_train_heldout")
    assert not hasattr(pdelie, "subsample_time")
    assert not hasattr(pdelie, "subsample_x")
    assert not hasattr(pdelie, "summarize_recovery_grid")
    assert not hasattr(pdelie, "to_pysindy_trajectories")
    assert not hasattr(pdelie, "coerce_generator_family")
    assert not hasattr(pdelie, "export_generator_family_manifest")
    assert not hasattr(pdelie, "import_generator_family_manifest")
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
    assert not hasattr(invariants_module, "InvariantMapSpec")


def test_data_package_runtime_api_matches_frozen_v0_7_m2_surface() -> None:
    data_module = importlib.import_module("pdelie.data")

    assert hasattr(data_module, "add_gaussian_noise")
    assert hasattr(data_module, "from_numpy")
    assert hasattr(data_module, "from_xarray")
    assert hasattr(data_module, "subsample_time")
    assert hasattr(data_module, "subsample_x")
    assert hasattr(data_module, "split_batch_train_heldout")


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
