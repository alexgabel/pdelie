from __future__ import annotations

import numpy as np

from pdelie.data import generate_burgers_1d_field_batch
from pdelie.data.burgers_1d import _rollout_burgers_periodic


def test_burgers_generator_is_reproducible_by_seed() -> None:
    first = generate_burgers_1d_field_batch(seed=7)
    second = generate_burgers_1d_field_batch(seed=7)
    np.testing.assert_allclose(first.values, second.values)


def test_burgers_generator_uses_uniform_periodic_grid_metadata() -> None:
    field = generate_burgers_1d_field_batch(seed=1, num_points=32)
    x = field.coords["x"]
    diffs = np.diff(x)
    assert field.metadata["boundary_conditions"]["x"] == "periodic"
    assert field.metadata["grid_regularity"] == "uniform"
    np.testing.assert_allclose(diffs, diffs[0])


def test_burgers_generator_shapes_and_var_axis_are_stable() -> None:
    field = generate_burgers_1d_field_batch(batch_size=3, num_times=9, num_points=16, seed=5)
    assert field.dims == ("batch", "time", "x", "var")
    assert field.var_names == ["u"]
    assert field.values.shape == (3, 9, 16, 1)
    assert np.isfinite(field.values).all()


def test_zero_state_burgers_rollout_remains_zero() -> None:
    output_times = np.linspace(0.0, 0.2, 5, dtype=float)
    initial_values = np.zeros((2, 32), dtype=float)
    rollout = _rollout_burgers_periodic(
        initial_values,
        output_times=output_times,
        diffusivity=0.1,
        num_substeps=4,
    )
    np.testing.assert_allclose(rollout, 0.0, atol=1e-12)
