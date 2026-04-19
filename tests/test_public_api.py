from __future__ import annotations

import importlib

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
    from pdelie.discovery import to_pysindy_trajectories
    from pdelie.invariants import InvariantApplier
    from pdelie.symmetry import (
        compare_generator_spans,
        render_generator_family,
        to_sympy_component_expressions,
    )

    assert InvariantApplier is not None
    assert to_pysindy_trajectories is not None
    assert compare_generator_spans is not None
    assert render_generator_family is not None
    assert to_sympy_component_expressions is not None


def test_root_package_does_not_export_runtime_invariant_applier() -> None:
    assert not hasattr(pdelie, "InvariantApplier")
    assert not hasattr(pdelie, "to_pysindy_trajectories")
    assert not hasattr(pdelie, "compare_generator_spans")
    assert not hasattr(pdelie, "render_generator_family")
    assert not hasattr(pdelie, "to_sympy_component_expressions")


def test_invariants_package_runtime_api_matches_frozen_milestone_surface() -> None:
    invariants_module = importlib.import_module("pdelie.invariants")

    assert hasattr(invariants_module, "InvariantApplier")
    assert not hasattr(invariants_module, "InvariantMapSpec")


def test_discovery_package_runtime_api_matches_frozen_milestone_surface() -> None:
    discovery_module = importlib.import_module("pdelie.discovery")

    assert hasattr(discovery_module, "to_pysindy_trajectories")
    assert not hasattr(discovery_module, "_fit_pysindy_smoke")


def test_symmetry_package_runtime_api_matches_frozen_m3_surface() -> None:
    symmetry_module = importlib.import_module("pdelie.symmetry")

    assert hasattr(symmetry_module, "fit_translation_generator")
    assert hasattr(symmetry_module, "compare_generator_spans")
    assert hasattr(symmetry_module, "render_generator_family")
    assert hasattr(symmetry_module, "to_sympy_component_expressions")
