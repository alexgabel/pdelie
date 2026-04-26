from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

import pdelie
from pdelie import FieldBatch, SchemaValidationError, ScopeValidationError, ShapeValidationError
from pdelie.data import from_numpy


def _metadata(*, x_boundary: str = "periodic") -> dict[str, object]:
    return {
        "boundary_conditions": {"x": x_boundary},
        "coordinate_system": "cartesian",
        "grid_regularity": "uniform",
        "grid_type": "rectilinear",
        "parameter_tags": {"nu": 0.1},
    }


def _time() -> np.ndarray:
    return np.linspace(0.0, 0.2, 4, dtype=float)


def _x() -> np.ndarray:
    return np.linspace(0.0, 2.0 * np.pi, 8, endpoint=False, dtype=float)


@pytest.mark.parametrize(
    ("dims", "shape", "expected_shape", "injected_batch_axis", "injected_var_axis"),
    [
        (("time", "x"), (4, 8), (1, 4, 8, 1), True, True),
        (("batch", "time", "x"), (2, 4, 8), (2, 4, 8, 1), False, True),
        (("time", "x", "var"), (4, 8, 1), (1, 4, 8, 1), True, False),
        (("batch", "time", "x", "var"), (2, 4, 8, 1), (2, 4, 8, 1), False, False),
    ],
)
def test_from_numpy_accepts_frozen_v0_7_layouts(
    dims: tuple[str, ...],
    shape: tuple[int, ...],
    expected_shape: tuple[int, ...],
    injected_batch_axis: bool,
    injected_var_axis: bool,
) -> None:
    values = np.arange(np.prod(shape), dtype=float).reshape(shape)
    coords = {"time": _time(), "x": _x()}
    metadata = _metadata()
    preprocess_log = [{"operation": "source", "parameters": {"nested": {"level": 1}}}]

    field = from_numpy(
        values,
        dims=dims,
        coords=coords,
        var_name="u",
        metadata=metadata,
        preprocess_log=preprocess_log,
    )

    assert isinstance(field, FieldBatch)
    assert field.dims == ("batch", "time", "x", "var")
    assert field.values.shape == expected_shape
    assert field.var_names == ["u"]
    assert field.mask is None
    assert field.preprocess_log[:-1] == preprocess_log
    assert field.preprocess_log[-1]["operation"] == "from_numpy"
    assert field.preprocess_log[-1]["parameters"] == {
        "source_layout": list(dims),
        "imported_shape": list(shape),
        "canonical_shape": list(expected_shape),
        "injected_batch_axis": injected_batch_axis,
        "injected_var_axis": injected_var_axis,
        "mask_provided": False,
    }


def test_from_numpy_copies_values_coords_and_deep_copies_metadata_and_preprocess_log() -> None:
    values = np.arange(32, dtype=float).reshape(4, 8)
    coords = {"time": _time(), "x": _x()}
    metadata = _metadata()
    preprocess_log = [{"operation": "source", "parameters": {"nested": {"level": 1}}}]

    field = from_numpy(
        values,
        dims=("time", "x"),
        coords=coords,
        var_name="u",
        metadata=metadata,
        preprocess_log=preprocess_log,
    )

    assert not np.shares_memory(field.values[..., 0], values)
    assert not np.shares_memory(field.coords["time"], coords["time"])
    assert not np.shares_memory(field.coords["x"], coords["x"])

    field.values[0, 0, 0, 0] = 999.0
    field.coords["time"][0] = 999.0
    field.coords["x"][0] = 999.0
    field.metadata["boundary_conditions"]["x"] = "changed"
    field.preprocess_log[0]["parameters"]["nested"]["level"] = 99

    assert values[0, 0] != 999.0
    assert coords["time"][0] != 999.0
    assert coords["x"][0] != 999.0
    assert metadata["boundary_conditions"]["x"] == "periodic"
    assert preprocess_log[0]["parameters"]["nested"]["level"] == 1


def test_from_numpy_normalizes_and_copies_mask_to_canonical_shape() -> None:
    values = np.arange(32, dtype=float).reshape(4, 8)
    mask = np.zeros((4, 8), dtype=bool)
    mask[1, 2] = True

    field = from_numpy(
        values,
        dims=("time", "x"),
        coords={"time": _time(), "x": _x()},
        var_name="u",
        metadata=_metadata(),
        mask=mask,
    )

    assert field.mask is not None
    assert field.mask.shape == (1, 4, 8, 1)
    assert bool(field.mask[0, 1, 2, 0]) is True
    assert not np.shares_memory(field.mask[..., 0], mask)

    field.mask[0, 1, 2, 0] = False
    assert bool(mask[1, 2]) is True
    assert field.preprocess_log[-1]["parameters"]["mask_provided"] is True


def test_from_numpy_preserves_nans_without_creating_mask() -> None:
    values = np.arange(32, dtype=float).reshape(4, 8)
    values[2, 3] = np.nan

    field = from_numpy(
        values,
        dims=("time", "x"),
        coords={"time": _time(), "x": _x()},
        var_name="u",
        metadata=_metadata(),
    )

    assert np.isnan(field.values[0, 2, 3, 0])
    assert field.mask is None


def test_from_numpy_rejects_nonuniform_x() -> None:
    with pytest.raises(ScopeValidationError, match="uniform rectilinear x"):
        from_numpy(
            np.zeros((4, 8), dtype=float),
            dims=("time", "x"),
            coords={"time": _time(), "x": np.array([0.0, 0.5, 1.0, 1.6, 2.4, 3.2, 4.1, 5.0])},
            var_name="u",
            metadata=_metadata(),
        )


def test_from_numpy_rejects_nonuniform_time() -> None:
    with pytest.raises(ScopeValidationError, match="uniformly spaced time"):
        from_numpy(
            np.zeros((4, 8), dtype=float),
            dims=("time", "x"),
            coords={"time": np.array([0.0, 0.05, 0.11, 0.2]), "x": _x()},
            var_name="u",
            metadata=_metadata(),
        )


@pytest.mark.parametrize("missing_coord", ["time", "x"])
def test_from_numpy_rejects_missing_required_coordinates(missing_coord: str) -> None:
    coords = {"time": _time(), "x": _x()}
    coords.pop(missing_coord)

    with pytest.raises(SchemaValidationError, match=rf"coords\['{missing_coord}'\] is required"):
        from_numpy(
            np.zeros((4, 8), dtype=float),
            dims=("time", "x"),
            coords=coords,
            var_name="u",
            metadata=_metadata(),
        )


@pytest.mark.parametrize(
    "dims",
    [
        ("x", "time"),
        ("batch", "x", "time"),
        ("time",),
        ("batch", "time", "x", "y"),
    ],
)
def test_from_numpy_rejects_unsupported_layouts(dims: tuple[str, ...]) -> None:
    with pytest.raises(ScopeValidationError, match="only supports the frozen V0\\.7 layouts"):
        from_numpy(
            np.zeros((4, 8), dtype=float) if len(dims) == 2 else np.zeros((1, 4, 8), dtype=float),
            dims=dims,
            coords={"time": _time(), "x": _x()},
            var_name="u",
            metadata=_metadata(),
        )


def test_from_numpy_rejects_var_length_greater_than_one() -> None:
    with pytest.raises(ScopeValidationError, match="singleton var axis"):
        from_numpy(
            np.zeros((4, 8, 2), dtype=float),
            dims=("time", "x", "var"),
            coords={"time": _time(), "x": _x()},
            var_name="u",
            metadata=_metadata(),
        )


@pytest.mark.parametrize(
    ("metadata", "error_type"),
    [
        ({"boundary_conditions": {"x": "periodic"}}, SchemaValidationError),
        (
            {
                "boundary_conditions": {"x": "periodic"},
                "coordinate_system": "cartesian",
                "grid_regularity": "uniform",
                "grid_type": "rectilinear",
                "parameter_tags": "not-a-mapping",
            },
            SchemaValidationError,
        ),
    ],
)
def test_from_numpy_rejects_missing_or_invalid_metadata(
    metadata: dict[str, object],
    error_type: type[Exception],
) -> None:
    with pytest.raises(error_type):
        from_numpy(
            np.zeros((4, 8), dtype=float),
            dims=("time", "x"),
            coords={"time": _time(), "x": _x()},
            var_name="u",
            metadata=metadata,
        )


def test_from_numpy_rejects_non_periodic_x_boundary_condition() -> None:
    with pytest.raises(ScopeValidationError, match="periodic x boundary conditions"):
        from_numpy(
            np.zeros((4, 8), dtype=float),
            dims=("time", "x"),
            coords={"time": _time(), "x": _x()},
            var_name="u",
            metadata=_metadata(x_boundary="dirichlet"),
        )


def test_from_numpy_rejects_shape_mismatches() -> None:
    with pytest.raises(ShapeValidationError, match="values rank must match dims length"):
        from_numpy(
            np.zeros((4, 8, 1), dtype=float),
            dims=("time", "x"),
            coords={"time": _time(), "x": _x()},
            var_name="u",
            metadata=_metadata(),
        )

    with pytest.raises(ShapeValidationError, match="coords\\['time'\\] length must match"):
        from_numpy(
            np.zeros((4, 8), dtype=float),
            dims=("time", "x"),
            coords={"time": np.linspace(0.0, 0.2, 5), "x": _x()},
            var_name="u",
            metadata=_metadata(),
        )

    with pytest.raises(ShapeValidationError, match="mask must match the pre-normalized values shape"):
        from_numpy(
            np.zeros((4, 8), dtype=float),
            dims=("time", "x"),
            coords={"time": _time(), "x": _x()},
            var_name="u",
            metadata=_metadata(),
            mask=np.zeros((1, 4, 8, 1), dtype=bool),
        )


def test_from_numpy_rejects_invalid_var_name() -> None:
    with pytest.raises(SchemaValidationError, match="var_name must be a non-empty string"):
        from_numpy(
            np.zeros((4, 8), dtype=float),
            dims=("time", "x"),
            coords={"time": _time(), "x": _x()},
            var_name="",
            metadata=_metadata(),
        )


def test_root_package_does_not_export_from_numpy() -> None:
    assert not hasattr(pdelie, "from_numpy")
