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
from pdelie.discovery import to_pysindy_trajectories
from pdelie.invariants import InvariantApplier


def test_stable_public_api_is_importable() -> None:
    assert FieldBatch is not None
    assert DerivativeBatch is not None
    assert ResidualBatch is not None
    assert ResidualEvaluator is not None
    assert GeneratorFamily is not None
    assert InvariantMapSpec is not None
    assert VerificationReport is not None
    assert InvariantApplier is not None
    assert to_pysindy_trajectories is not None


def test_root_package_does_not_export_runtime_invariant_applier() -> None:
    assert not hasattr(pdelie, "InvariantApplier")
    assert not hasattr(pdelie, "to_pysindy_trajectories")


def test_invariants_package_runtime_api_matches_frozen_milestone_surface() -> None:
    invariants_module = importlib.import_module("pdelie.invariants")

    assert hasattr(invariants_module, "InvariantApplier")
    assert not hasattr(invariants_module, "InvariantMapSpec")


def test_discovery_package_runtime_api_matches_frozen_milestone_surface() -> None:
    discovery_module = importlib.import_module("pdelie.discovery")

    assert hasattr(discovery_module, "to_pysindy_trajectories")
    assert not hasattr(discovery_module, "_fit_pysindy_smoke")
