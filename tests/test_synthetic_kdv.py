from __future__ import annotations

import numpy as np
import pytest

from pdelie import PDELieValidationError
from pdelie.data import generate_kdv_1d_field_batch
from pdelie.data.heat_1d import DEFAULT_DOMAIN_LENGTH


def _compute_mass(values: np.ndarray, *, dx: float) -> np.ndarray:
    return dx * np.sum(values[..., 0], axis=-1)


def _compute_l2_norm(values: np.ndarray, *, dx: float) -> np.ndarray:
    return np.sqrt(dx * np.sum(np.square(values[..., 0]), axis=-1))


def test_kdv_generator_is_reproducible_and_seed_sensitive() -> None:
    first = generate_kdv_1d_field_batch(seed=9010)
    second = generate_kdv_1d_field_batch(seed=9010)
    different = generate_kdv_1d_field_batch(seed=9011)

    np.testing.assert_allclose(first.values, second.values, rtol=0.0, atol=0.0)
    assert not np.allclose(first.values, different.values, rtol=0.0, atol=0.0)


def test_kdv_generator_freezes_canonical_shape_coordinates_and_metadata() -> None:
    batch_size = 3
    num_times = 7
    num_points = 32
    max_time = 0.03
    domain_length = DEFAULT_DOMAIN_LENGTH

    field = generate_kdv_1d_field_batch(
        batch_size=batch_size,
        num_times=num_times,
        num_points=num_points,
        max_time=max_time,
        domain_length=domain_length,
        seed=9020,
    )

    assert field.values.shape == (batch_size, num_times, num_points, 1)
    assert field.dims == ("batch", "time", "x", "var")
    assert field.var_names == ["u"]
    assert field.mask is None
    assert field.preprocess_log == []

    np.testing.assert_allclose(field.coords["x"], np.linspace(0.0, domain_length, num_points, endpoint=False))
    assert field.coords["x"][0] == pytest.approx(0.0)
    assert field.coords["x"][-1] == pytest.approx(domain_length * (num_points - 1) / num_points)
    np.testing.assert_allclose(field.coords["time"], np.linspace(0.0, max_time, num_times))
    assert field.coords["time"][0] == pytest.approx(0.0)
    assert field.coords["time"][-1] == pytest.approx(max_time)

    assert field.metadata["boundary_conditions"]["x"] == "periodic"
    assert field.metadata["grid_type"] == "rectilinear"
    assert field.metadata["grid_regularity"] == "uniform"
    assert field.metadata["coordinate_system"] == "cartesian"
    assert field.metadata["parameter_tags"] == {"equation": "kdv_normalized"}
    field.validate()


def test_kdv_default_fixture_preserves_mass_and_l2_norm() -> None:
    field = generate_kdv_1d_field_batch(seed=9030)
    dx = float(field.coords["x"][1] - field.coords["x"][0])
    mass = _compute_mass(field.values, dx=dx)
    l2 = _compute_l2_norm(field.values, dx=dx)

    mass_drift = np.max(np.abs(mass - mass[:, [0]]))
    relative_l2_drift = np.max(np.abs(l2 - l2[:, [0]]) / np.maximum(np.abs(l2[:, [0]]), 1e-12))

    assert mass_drift <= 1e-8
    assert relative_l2_drift <= 5e-3


def test_kdv_zero_amplitude_is_valid_and_finite() -> None:
    field = generate_kdv_1d_field_batch(amplitude=0.0, seed=9040)

    assert np.all(np.isfinite(field.values))
    np.testing.assert_allclose(field.values, np.zeros_like(field.values), rtol=0.0, atol=0.0)
    field.validate()


def test_kdv_generator_accepts_numpy_integer_scalars() -> None:
    field = generate_kdv_1d_field_batch(
        batch_size=np.int64(1),
        num_times=np.int64(3),
        num_points=np.int64(16),
        num_modes=np.int64(1),
        seed=np.int64(9050),
        num_substeps=np.int64(1),
    )

    assert field.values.shape == (1, 3, 16, 1)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"batch_size": True},
        {"batch_size": np.bool_(False)},
        {"batch_size": 1.0},
        {"batch_size": 0},
        {"num_times": 2},
        {"num_points": 15},
        {"num_modes": 0},
        {"num_modes": 6, "num_points": 16},
        {"num_substeps": 0},
        {"max_time": 0.0},
        {"max_time": np.inf},
        {"amplitude": -0.01},
        {"amplitude": np.nan},
        {"seed": True},
        {"seed": -1},
        {"seed": 1.0},
        {"domain_length": 0.0},
        {"domain_length": np.inf},
    ],
)
def test_kdv_generator_rejects_invalid_parameters(kwargs: dict[str, object]) -> None:
    with pytest.raises(PDELieValidationError):
        generate_kdv_1d_field_batch(**kwargs)
