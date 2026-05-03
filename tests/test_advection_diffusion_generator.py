from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from pdelie.contracts import FieldBatch
from pdelie.data import from_numpy, generate_advection_diffusion_1d_field_batch
from pdelie.errors import SchemaValidationError, ScopeValidationError


def test_advection_diffusion_generator_is_deterministic_and_seed_sensitive() -> None:
    first = generate_advection_diffusion_1d_field_batch(seed=19018)
    second = generate_advection_diffusion_1d_field_batch(seed=19018)
    different = generate_advection_diffusion_1d_field_batch(seed=19019)

    np.testing.assert_allclose(first.values, second.values)
    assert not np.allclose(first.values, different.values)
    np.testing.assert_allclose(first.coords["time"], second.coords["time"])
    np.testing.assert_allclose(first.coords["x"], second.coords["x"])


def test_advection_diffusion_generator_returns_canonical_field_batch() -> None:
    field = generate_advection_diffusion_1d_field_batch(batch_size=3, seed=19018)

    field.validate()
    assert field.dims == ("batch", "time", "x", "var")
    assert field.values.shape == (3, 65, 64, 1)
    assert field.var_names == ["u"]
    assert field.mask is None
    assert np.isfinite(field.values).all()

    time = field.coords["time"]
    x = field.coords["x"]
    assert np.all(np.diff(time) > 0.0)
    np.testing.assert_allclose(np.diff(time), time[1] - time[0])
    np.testing.assert_allclose(x[0], 0.0)
    assert x[-1] < 2.0 * np.pi
    np.testing.assert_allclose(np.diff(x), x[1] - x[0])

    tags = field.metadata["parameter_tags"]
    assert tags["equation"] == "advection_diffusion_constant_coefficient"
    assert tags["c"] == 0.75
    assert tags["nu"] == 0.05
    assert field.metadata["boundary_conditions"]["x"] == "periodic"


def test_advection_diffusion_generator_matches_exact_fourier_evolution() -> None:
    field = generate_advection_diffusion_1d_field_batch(batch_size=2, seed=19018)
    values = field.values[..., 0]
    x = field.coords["x"]
    time = field.coords["time"]
    tags = field.metadata["parameter_tags"]
    dx = float(x[1] - x[0])
    wavenumbers = 2.0 * np.pi * np.fft.fftfreq(x.size, d=dx)
    spectrum0 = np.fft.fft(values[:, 0, :], axis=-1)
    multiplier = np.exp(time[:, None] * (-tags["nu"] * wavenumbers[None, :] ** 2 - 1j * tags["c"] * wavenumbers[None, :]))
    expected = np.real(np.fft.ifft(spectrum0[:, None, :] * multiplier[None, :, :], axis=-1))

    np.testing.assert_allclose(values, expected, rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(np.mean(values[:, 0, :], axis=-1), 0.0, rtol=0.0, atol=1e-14)


def test_advection_diffusion_generator_import_round_trip_with_from_numpy() -> None:
    field = generate_advection_diffusion_1d_field_batch(batch_size=2, seed=19018)
    imported = from_numpy(
        field.values,
        dims=field.dims,
        coords=field.coords,
        var_name="u",
        metadata=field.metadata,
        preprocess_log=field.preprocess_log,
    )

    imported.validate()
    np.testing.assert_allclose(imported.values, field.values)
    np.testing.assert_allclose(imported.coords["time"], field.coords["time"])
    np.testing.assert_allclose(imported.coords["x"], field.coords["x"])
    assert imported.metadata == field.metadata
    assert imported.preprocess_log[-1]["operation"] == "from_numpy"


@pytest.mark.parametrize(
    ("kwargs", "error_type"),
    [
        ({"batch_size": 0}, SchemaValidationError),
        ({"num_times": 2}, SchemaValidationError),
        ({"num_points": 15}, SchemaValidationError),
        ({"num_modes": 0}, SchemaValidationError),
        ({"num_modes": 32}, ScopeValidationError),
        ({"seed": -1}, SchemaValidationError),
        ({"max_time": 0.0}, SchemaValidationError),
        ({"advection_speed": float("nan")}, SchemaValidationError),
        ({"diffusivity": 0.0}, SchemaValidationError),
        ({"diffusivity": -0.1}, SchemaValidationError),
        ({"diffusivity": float("nan")}, SchemaValidationError),
        ({"amplitude": -0.1}, SchemaValidationError),
        ({"amplitude": 1.5}, ScopeValidationError),
        ({"domain_length": 0.0}, SchemaValidationError),
    ],
)
def test_advection_diffusion_generator_rejects_invalid_parameters(
    kwargs: dict[str, object],
    error_type: type[Exception],
) -> None:
    with pytest.raises(error_type):
        generate_advection_diffusion_1d_field_batch(**kwargs)


def test_advection_diffusion_generator_allows_signed_advection_speed() -> None:
    forward = generate_advection_diffusion_1d_field_batch(advection_speed=0.75, seed=19018)
    backward = generate_advection_diffusion_1d_field_batch(advection_speed=-0.75, seed=19018)

    assert forward.metadata["parameter_tags"]["c"] == 0.75
    assert backward.metadata["parameter_tags"]["c"] == -0.75
    assert not np.allclose(forward.values[:, -1], backward.values[:, -1])


def test_advection_diffusion_generator_metadata_can_be_preserved_in_field_copy() -> None:
    field = generate_advection_diffusion_1d_field_batch(seed=19018)
    copied = FieldBatch(
        values=field.values.copy(),
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=deepcopy(field.metadata),
        preprocess_log=list(field.preprocess_log),
        mask=None,
    )

    copied.validate()
    assert copied.metadata["parameter_tags"]["equation"] == "advection_diffusion_constant_coefficient"
