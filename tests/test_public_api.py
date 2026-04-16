from __future__ import annotations

from pdelie import (
    DerivativeBatch,
    FieldBatch,
    GeneratorFamily,
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
    assert VerificationReport is not None
