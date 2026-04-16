from __future__ import annotations

import numpy as np

from pdelie.data import generate_heat_1d_field_batch


def test_heat_generator_is_reproducible_by_seed() -> None:
    first = generate_heat_1d_field_batch(seed=7)
    second = generate_heat_1d_field_batch(seed=7)
    np.testing.assert_allclose(first.values, second.values)


def test_heat_generator_uses_uniform_periodic_grid_metadata() -> None:
    field = generate_heat_1d_field_batch(seed=1, num_points=32)
    x = field.coords["x"]
    diffs = np.diff(x)
    assert field.metadata["boundary_conditions"]["x"] == "periodic"
    assert field.metadata["grid_regularity"] == "uniform"
    np.testing.assert_allclose(diffs, diffs[0])


def test_heat_generator_shapes_and_var_axis_are_stable() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=9, num_points=16, seed=5)
    assert field.dims == ("batch", "time", "x", "var")
    assert field.var_names == ["u"]
    assert field.values.shape == (3, 9, 16, 1)
    assert np.isfinite(field.values).all()


def test_heat_generator_exhibits_expected_energy_decay() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=11, seed=11)
    energy = np.sum(field.values[..., 0] ** 2, axis=2)
    assert np.all(energy[:, -1] <= energy[:, 0] + 1e-10)
