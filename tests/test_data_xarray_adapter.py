from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest
xr = pytest.importorskip("xarray", reason="xarray is required for from_xarray adapter tests")

import pdelie
from pdelie import FieldBatch, SchemaValidationError, ScopeValidationError, ShapeValidationError
from pdelie.data import from_xarray
from pdelie.data import xarray_adapter


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
def test_from_xarray_accepts_frozen_v0_7_layouts(
    dims: tuple[str, ...],
    shape: tuple[int, ...],
    expected_shape: tuple[int, ...],
    injected_batch_axis: bool,
    injected_var_axis: bool,
) -> None:
    values = np.arange(np.prod(shape), dtype=float).reshape(shape)
    coords: dict[str, object] = {"time": _time(), "x": _x()}
    if "batch" in dims:
        coords["batch"] = np.arange(shape[dims.index("batch")], dtype=int)
    if "var" in dims:
        coords["var"] = ["u"]

    data_array = xr.DataArray(values, dims=dims, coords=coords, name="array_name")
    preprocess_log = [{"operation": "source", "parameters": {"nested": {"level": 1}}}]

    field = from_xarray(
        data_array,
        var_name="u",
        metadata=_metadata(),
        preprocess_log=preprocess_log,
    )

    assert isinstance(field, FieldBatch)
    assert field.dims == ("batch", "time", "x", "var")
    assert field.values.shape == expected_shape
    assert field.var_names == ["u"]
    assert field.mask is None
    assert field.preprocess_log[:-1] == preprocess_log
    assert field.preprocess_log[-1]["operation"] == "from_xarray"
    assert field.preprocess_log[-1]["parameters"] == {
        "source_layout": list(dims),
        "imported_shape": list(shape),
        "canonical_shape": list(expected_shape),
        "injected_batch_axis": injected_batch_axis,
        "injected_var_axis": injected_var_axis,
        "mask_provided": False,
    }


def test_from_xarray_var_name_resolution_precedence() -> None:
    values = np.zeros((4, 8, 1), dtype=float)
    data_array = xr.DataArray(
        values,
        dims=("time", "x", "var"),
        coords={"time": _time(), "x": _x(), "var": ["coord_name"]},
        name="data_array_name",
    )

    explicit = from_xarray(data_array, var_name="explicit_name", metadata=_metadata())
    coord_fallback = from_xarray(data_array, metadata=_metadata())
    name_fallback = from_xarray(
        xr.DataArray(
            np.zeros((4, 8), dtype=float),
            dims=("time", "x"),
            coords={"time": _time(), "x": _x()},
            name="data_array_name",
        ),
        metadata=_metadata(),
    )

    assert explicit.var_names == ["explicit_name"]
    assert coord_fallback.var_names == ["coord_name"]
    assert name_fallback.var_names == ["data_array_name"]


@pytest.mark.parametrize(
    "var_coord_value",
    [
        None,
        np.nan,
        "",
    ],
)
def test_from_xarray_rejects_invalid_var_coordinate_fallback(var_coord_value: object) -> None:
    data_array = xr.DataArray(
        np.zeros((4, 8, 1), dtype=float),
        dims=("time", "x", "var"),
        coords={"time": _time(), "x": _x(), "var": [var_coord_value]},
        name=None,
    )

    with pytest.raises(SchemaValidationError):
        from_xarray(data_array, metadata=_metadata())


def test_from_xarray_rejects_missing_all_var_name_sources() -> None:
    data_array = xr.DataArray(
        np.zeros((4, 8), dtype=float),
        dims=("time", "x"),
        coords={"time": _time(), "x": _x()},
        name=None,
    )

    with pytest.raises(SchemaValidationError, match="requires a variable name"):
        from_xarray(data_array, metadata=_metadata())


def test_from_xarray_copies_values_coords_and_deep_copies_metadata_and_preprocess_log() -> None:
    values = np.arange(32, dtype=float).reshape(4, 8)
    data_array = xr.DataArray(values, dims=("time", "x"), coords={"time": _time(), "x": _x()}, name="u")
    metadata = _metadata()
    preprocess_log = [{"operation": "source", "parameters": {"nested": {"level": 1}}}]

    field = from_xarray(
        data_array,
        metadata=metadata,
        preprocess_log=preprocess_log,
    )

    assert not np.shares_memory(field.values[..., 0], values)
    assert not np.shares_memory(field.coords["time"], data_array.coords["time"].values)
    assert not np.shares_memory(field.coords["x"], data_array.coords["x"].values)

    field.values[0, 0, 0, 0] = 999.0
    field.coords["time"][0] = 999.0
    field.coords["x"][0] = 999.0
    field.metadata["boundary_conditions"]["x"] = "changed"
    field.preprocess_log[0]["parameters"]["nested"]["level"] = 99

    assert values[0, 0] != 999.0
    assert float(data_array.coords["time"].values[0]) != 999.0
    assert float(data_array.coords["x"].values[0]) != 999.0
    assert metadata["boundary_conditions"]["x"] == "periodic"
    assert preprocess_log[0]["parameters"]["nested"]["level"] == 1


def test_from_xarray_normalizes_and_copies_mask_to_canonical_shape() -> None:
    values = np.arange(32, dtype=float).reshape(4, 8)
    data_array = xr.DataArray(values, dims=("time", "x"), coords={"time": _time(), "x": _x()}, name="u")
    mask = xr.DataArray(
        np.zeros((4, 8), dtype=bool),
        dims=("time", "x"),
        coords={"time": _time(), "x": _x()},
    )
    mask.values[1, 2] = True

    field = from_xarray(
        data_array,
        metadata=_metadata(),
        mask=mask,
    )

    assert field.mask is not None
    assert field.mask.shape == (1, 4, 8, 1)
    assert bool(field.mask[0, 1, 2, 0]) is True
    assert not np.shares_memory(field.mask[..., 0], mask.values)

    field.mask[0, 1, 2, 0] = False
    assert bool(mask.values[1, 2]) is True
    assert field.preprocess_log[-1]["parameters"]["mask_provided"] is True


def test_from_xarray_preserves_nans_without_creating_mask() -> None:
    values = np.arange(32, dtype=float).reshape(4, 8)
    values[2, 3] = np.nan
    data_array = xr.DataArray(values, dims=("time", "x"), coords={"time": _time(), "x": _x()}, name="u")

    field = from_xarray(data_array, metadata=_metadata())

    assert np.isnan(field.values[0, 2, 3, 0])
    assert field.mask is None


def test_from_xarray_rejects_nonuniform_x() -> None:
    data_array = xr.DataArray(
        np.zeros((4, 8), dtype=float),
        dims=("time", "x"),
        coords={"time": _time(), "x": np.array([0.0, 0.5, 1.0, 1.6, 2.4, 3.2, 4.1, 5.0])},
        name="u",
    )

    with pytest.raises(ScopeValidationError, match="uniform rectilinear x"):
        from_xarray(data_array, metadata=_metadata())


def test_from_xarray_rejects_nonuniform_time() -> None:
    data_array = xr.DataArray(
        np.zeros((4, 8), dtype=float),
        dims=("time", "x"),
        coords={"time": np.array([0.0, 0.05, 0.11, 0.2]), "x": _x()},
        name="u",
    )

    with pytest.raises(ScopeValidationError, match="uniformly spaced time"):
        from_xarray(data_array, metadata=_metadata())


@pytest.mark.parametrize("missing_coord", ["time", "x"])
def test_from_xarray_rejects_missing_required_coordinates(missing_coord: str) -> None:
    coords: dict[str, object] = {"time": _time(), "x": _x()}
    coords.pop(missing_coord)
    data_array = xr.DataArray(np.zeros((4, 8), dtype=float), dims=("time", "x"), coords=coords, name="u")

    with pytest.raises(SchemaValidationError, match=rf"coords\['{missing_coord}'\] is required"):
        from_xarray(data_array, metadata=_metadata())


def test_from_xarray_rejects_unsupported_layouts() -> None:
    data_array = xr.DataArray(
        np.zeros((8, 4), dtype=float),
        dims=("x", "time"),
        coords={"time": _time(), "x": _x()},
        name="u",
    )

    with pytest.raises(ScopeValidationError, match="only supports the frozen V0\\.7 layouts"):
        from_xarray(data_array, metadata=_metadata())


def test_from_xarray_rejects_var_length_greater_than_one() -> None:
    data_array = xr.DataArray(
        np.zeros((4, 8, 2), dtype=float),
        dims=("time", "x", "var"),
        coords={"time": _time(), "x": _x(), "var": ["u", "v"]},
        name="u",
    )

    with pytest.raises(ScopeValidationError, match="singleton var axis"):
        from_xarray(data_array, metadata=_metadata())


def test_from_xarray_rejects_dataset_input() -> None:
    dataset = xr.Dataset({"u": (("time", "x"), np.zeros((4, 8), dtype=float))}, coords={"time": _time(), "x": _x()})

    with pytest.raises(ScopeValidationError, match="only supports xarray.DataArray"):
        from_xarray(dataset, metadata=_metadata())


def test_from_xarray_rejects_invalid_mask_inputs() -> None:
    data_array = xr.DataArray(np.zeros((4, 8), dtype=float), dims=("time", "x"), coords={"time": _time(), "x": _x()}, name="u")

    with pytest.raises(SchemaValidationError, match="mask must be an xarray.DataArray"):
        from_xarray(data_array, metadata=_metadata(), mask=np.zeros((4, 8), dtype=bool))

    wrong_dims_mask = xr.DataArray(
        np.zeros((8, 4), dtype=bool),
        dims=("x", "time"),
        coords={"time": _time(), "x": _x()},
    )
    with pytest.raises(ShapeValidationError, match="mask.dims must exactly match data_array.dims"):
        from_xarray(data_array, metadata=_metadata(), mask=wrong_dims_mask)

    wrong_shape_mask = xr.DataArray(
        np.zeros((4, 7), dtype=bool),
        dims=("time", "x"),
        coords={"time": _time(), "x": _x()[:-1]},
    )
    with pytest.raises(ShapeValidationError, match="mask must match the pre-normalized data_array shape"):
        from_xarray(data_array, metadata=_metadata(), mask=wrong_shape_mask)


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
def test_from_xarray_rejects_missing_or_invalid_metadata(
    metadata: dict[str, object],
    error_type: type[Exception],
) -> None:
    data_array = xr.DataArray(np.zeros((4, 8), dtype=float), dims=("time", "x"), coords={"time": _time(), "x": _x()}, name="u")

    with pytest.raises(error_type):
        from_xarray(data_array, metadata=metadata)


def test_from_xarray_rejects_non_periodic_x_boundary_condition() -> None:
    data_array = xr.DataArray(np.zeros((4, 8), dtype=float), dims=("time", "x"), coords={"time": _time(), "x": _x()}, name="u")

    with pytest.raises(ScopeValidationError, match="periodic x boundary conditions"):
        from_xarray(data_array, metadata=_metadata(x_boundary="dirichlet"))


def test_from_xarray_ignores_attrs_for_metadata() -> None:
    data_array = xr.DataArray(
        np.zeros((4, 8), dtype=float),
        dims=("time", "x"),
        coords={"time": _time(), "x": _x()},
        name="u",
        attrs={"boundary_conditions": {"x": "periodic"}, "grid_type": "rectilinear"},
    )

    with pytest.raises(SchemaValidationError, match="metadata is missing required keys"):
        from_xarray(data_array, metadata={})

    conflicting = deepcopy(data_array)
    conflicting.attrs["boundary_conditions"] = {"x": "dirichlet"}
    field = from_xarray(conflicting, metadata=_metadata())
    assert field.metadata["boundary_conditions"]["x"] == "periodic"

def test_from_xarray_lazy_import_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import_module = xarray_adapter.importlib.import_module

    def _fake_import_module(name: str, package: str | None = None):
        if name == "xarray":
            raise ModuleNotFoundError("No module named 'xarray'", name="xarray")
        return original_import_module(name, package)

    monkeypatch.setattr(xarray_adapter.importlib, "import_module", _fake_import_module)

    with pytest.raises(ImportError, match=r"install pdelie\[xarray\]"):
        xarray_adapter.from_xarray(object(), metadata=_metadata())


def test_root_package_does_not_export_from_xarray() -> None:
    assert not hasattr(pdelie, "from_xarray")
