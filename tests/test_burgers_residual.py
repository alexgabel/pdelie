from __future__ import annotations

import numpy as np
import pytest

from pdelie import FieldBatch, SchemaValidationError
from pdelie.data import generate_burgers_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.residuals import BurgersResidualEvaluator


def test_burgers_residual_is_near_zero_on_clean_data() -> None:
    field = generate_burgers_1d_field_batch(batch_size=2, num_times=33, num_points=64, seed=3)
    evaluator = BurgersResidualEvaluator()
    residual = evaluator.evaluate(field)
    assert residual.definition_type == "analytic"
    assert residual.normalization == "none"
    assert np.max(np.abs(residual.residual)) < 1e-2


def test_burgers_residual_increases_for_perturbed_fields() -> None:
    field = generate_burgers_1d_field_batch(batch_size=2, num_times=33, num_points=64, seed=3)
    rng = np.random.default_rng(9)
    perturbed = FieldBatch(
        values=field.values + 0.05 * rng.normal(size=field.values.shape),
        dims=field.dims,
        coords=field.coords,
        var_names=field.var_names,
        metadata=field.metadata,
        preprocess_log=field.preprocess_log,
    )
    evaluator = BurgersResidualEvaluator()
    clean_norm = np.linalg.norm(evaluator.evaluate(field).residual)
    perturbed_norm = np.linalg.norm(evaluator.evaluate(perturbed).residual)
    assert perturbed_norm > 5.0 * clean_norm


def test_burgers_residual_requires_ut_ux_and_uxx() -> None:
    field = generate_burgers_1d_field_batch(batch_size=1, num_times=17, num_points=32, seed=1)
    derivatives = compute_spectral_fd_derivatives(field)
    derivatives.derivatives.pop("u_x")
    evaluator = BurgersResidualEvaluator()
    with pytest.raises(SchemaValidationError):
        evaluator.evaluate(field, derivatives)
