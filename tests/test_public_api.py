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


def test_root_package_does_not_export_runtime_invariant_applier() -> None:
    assert not hasattr(pdelie, "InvariantApplier")


def test_invariants_package_runtime_api_matches_frozen_milestone_surface() -> None:
    invariants_module = importlib.import_module("pdelie.invariants")

    assert hasattr(invariants_module, "InvariantApplier")
    assert not hasattr(invariants_module, "InvariantMapSpec")
