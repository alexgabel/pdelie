from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from pdelie.contracts import FieldBatch
from pdelie.data import from_numpy, generate_reaction_diffusion_1d_field_batch
from pdelie.errors import SchemaValidationError, ScopeValidationError


def test_reaction_diffusion_generator_is_deterministic_and_seed_sensitive() -> None:
    first = generate_reaction_diffusion_1d_field_batch(seed=18018)
    second = generate_reaction_diffusion_1d_field_batch(seed=18018)
    different = generate_reaction_diffusion_1d_field_batch(seed=18019)

    np.testing.assert_allclose(first.values, second.values)
    assert not np.allclose(first.values, different.values)
    np.testing.assert_allclose(first.coords["time"], second.coords["time"])
    np.testing.assert_allclose(first.coords["x"], second.coords["x"])


def test_reaction_diffusion_generator_returns_canonical_field_batch() -> None:
    field = generate_reaction_diffusion_1d_field_batch(batch_size=3, seed=18018)

    field.validate()
    assert field.dims == ("batch", "time", "x", "var")
    assert field.values.shape == (3, 65, 64, 1)
    assert field.var_names == ["u"]
    assert field.mask is None
    assert np.isfinite(field.values).all()
    assert np.min(field.values) > 0.0
    assert np.max(field.values) < 1.0

    time = field.coords["time"]
    x = field.coords["x"]
    assert np.all(np.diff(time) > 0.0)
    np.testing.assert_allclose(np.diff(time), time[1] - time[0])
    np.testing.assert_allclose(x[0], 0.0)
    assert x[-1] < 2.0 * np.pi
    np.testing.assert_allclose(np.diff(x), x[1] - x[0])

    tags = field.metadata["parameter_tags"]
    assert tags["equation"] == "reaction_diffusion_fisher_kpp"
    assert tags["nu"] == 0.05
    assert tags["rho"] == 1.0
    assert field.metadata["boundary_conditions"]["x"] == "periodic"


def test_reaction_diffusion_generator_import_round_trip_with_from_numpy() -> None:
    field = generate_reaction_diffusion_1d_field_batch(batch_size=2, seed=18018)
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
        ({"num_substeps": 0}, SchemaValidationError),
        ({"seed": -1}, SchemaValidationError),
        ({"max_time": 0.0}, SchemaValidationError),
        ({"diffusivity": 0.0}, SchemaValidationError),
        ({"diffusivity": -0.1}, SchemaValidationError),
        ({"reaction_rate": 0.0}, SchemaValidationError),
        ({"reaction_rate": float("nan")}, SchemaValidationError),
        ({"amplitude": -0.1}, SchemaValidationError),
        ({"amplitude": 0.25}, ScopeValidationError),
        ({"domain_length": 0.0}, SchemaValidationError),
    ],
)
def test_reaction_diffusion_generator_rejects_invalid_parameters(
    kwargs: dict[str, object],
    error_type: type[Exception],
) -> None:
    with pytest.raises(error_type):
        generate_reaction_diffusion_1d_field_batch(**kwargs)


def test_reaction_diffusion_generator_metadata_can_be_preserved_in_field_copy() -> None:
    field = generate_reaction_diffusion_1d_field_batch(seed=18018)
    metadata = deepcopy(field.metadata)
    copied = FieldBatch(
        values=field.values.copy(),
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=metadata,
        preprocess_log=list(field.preprocess_log),
        mask=None,
    )

    copied.validate()
    assert copied.metadata["parameter_tags"]["equation"] == "reaction_diffusion_fisher_kpp"
