from __future__ import annotations

from copy import deepcopy
import importlib
from typing import Any, Mapping, Sequence

import numpy as np

from pdelie.contracts import FieldBatch, REQUIRED_METADATA_KEYS, _is_uniform
from pdelie.data.numpy_adapter import (
    _CANONICAL_DIMS,
    _TIME_UNIFORM_ABS_TOL,
    _canonicalize_mask,
    _canonicalize_values,
    _strictly_increasing,
    _to_float_array,
    _validate_mapping,
    _validate_preprocess_log,
    _validate_string,
)
from pdelie.errors import SchemaValidationError, ScopeValidationError, ShapeValidationError


_ACCEPTED_LAYOUTS = frozenset(
    {
        ("time", "x"),
        ("batch", "time", "x"),
        ("time", "x", "var"),
        ("batch", "time", "x", "var"),
    }
)


def _require_xarray():
    try:
        return importlib.import_module("xarray")
    except ModuleNotFoundError as exc:
        raise ImportError("xarray is required for pdelie.data.from_xarray; install pdelie[xarray].") from exc


def _normalize_dims(dims: object) -> tuple[str, ...]:
    if not isinstance(dims, (list, tuple)):
        raise SchemaValidationError("data_array.dims must be a list or tuple of strings.")
    normalized = tuple(str(dim) for dim in dims)
    if any(not dim for dim in normalized):
        raise SchemaValidationError("data_array.dims entries must be non-empty strings.")
    if len(set(normalized)) != len(normalized):
        raise SchemaValidationError("data_array.dims entries must be unique.")
    if normalized not in _ACCEPTED_LAYOUTS:
        raise ScopeValidationError(
            "from_xarray only supports the frozen V0.7 layouts: "
            "('time', 'x'), ('batch', 'time', 'x'), ('time', 'x', 'var'), ('batch', 'time', 'x', 'var')."
        )
    return normalized


def _validate_time_coord(coord: object, *, expected_length: int) -> np.ndarray:
    time = _to_float_array(coord, name="coords['time']")
    if time.ndim != 1:
        raise ShapeValidationError("coords['time'] must be one-dimensional.")
    if time.shape[0] != expected_length:
        raise ShapeValidationError("coords['time'] length must match the time axis.")
    if time.size < 3:
        raise ScopeValidationError("from_xarray requires at least three time points.")
    if not np.isfinite(time).all():
        raise SchemaValidationError("coords['time'] must contain only finite values.")
    if not _strictly_increasing(time):
        raise SchemaValidationError("coords['time'] must be strictly increasing.")
    time_step = float(time[1] - time[0])
    if not np.allclose(np.diff(time), time_step, atol=_TIME_UNIFORM_ABS_TOL, rtol=0.0):
        raise ScopeValidationError("from_xarray requires uniformly spaced time coordinates.")
    return time.copy()


def _validate_x_coord(coord: object, *, expected_length: int) -> np.ndarray:
    x = _to_float_array(coord, name="coords['x']")
    if x.ndim != 1:
        raise ShapeValidationError("coords['x'] must be one-dimensional.")
    if x.shape[0] != expected_length:
        raise ShapeValidationError("coords['x'] length must match the x axis.")
    if x.size < 4:
        raise ScopeValidationError("from_xarray requires at least four x-points.")
    if not np.isfinite(x).all():
        raise SchemaValidationError("coords['x'] must contain only finite values.")
    if not _strictly_increasing(x):
        raise SchemaValidationError("coords['x'] must be strictly increasing.")
    if not _is_uniform(x):
        raise ScopeValidationError("from_xarray only supports uniform rectilinear x coordinates.")
    return x.copy()


def _validate_metadata(value: object) -> dict[str, Any]:
    metadata = deepcopy(dict(_validate_mapping(value, name="metadata")))

    missing = [key for key in REQUIRED_METADATA_KEYS if key not in metadata]
    if missing:
        raise SchemaValidationError(f"metadata is missing required keys: {missing}.")

    boundary_conditions = metadata["boundary_conditions"]
    parameter_tags = metadata["parameter_tags"]
    if not isinstance(boundary_conditions, Mapping):
        raise SchemaValidationError("metadata['boundary_conditions'] must be a mapping.")
    if not isinstance(parameter_tags, Mapping):
        raise SchemaValidationError("metadata['parameter_tags'] must be a mapping.")
    if "x" not in boundary_conditions:
        raise SchemaValidationError("metadata['boundary_conditions'] must include an 'x' entry.")

    if metadata["grid_type"] != "rectilinear":
        raise ScopeValidationError("from_xarray only supports rectilinear grids.")
    if metadata["grid_regularity"] != "uniform":
        raise ScopeValidationError("from_xarray only supports uniform rectilinear grids.")
    if metadata["coordinate_system"] != "cartesian":
        raise ScopeValidationError("from_xarray only supports cartesian coordinates.")
    if boundary_conditions["x"] != "periodic":
        raise ScopeValidationError("from_xarray only supports periodic x boundary conditions.")

    return metadata


def _normalize_var_name_candidate(value: object, *, source_name: str) -> str:
    if value is None:
        raise SchemaValidationError(f"{source_name} must resolve to a non-empty string variable name.")
    if isinstance(value, (float, np.floating)) and not np.isfinite(float(value)):
        raise SchemaValidationError(f"{source_name} must not be a non-finite numeric value.")
    normalized = str(value)
    if not normalized:
        raise SchemaValidationError(f"{source_name} must resolve to a non-empty string variable name.")
    return normalized


def _resolve_var_name(
    data_array: object,
    *,
    normalized_dims: tuple[str, ...],
    explicit_var_name: str | None,
) -> str:
    if explicit_var_name is not None:
        return _validate_string(explicit_var_name, name="var_name")

    if "var" in normalized_dims and "var" in data_array.coords:
        var_coord = data_array.coords["var"]
        var_coord_dims = tuple(str(dim) for dim in var_coord.dims)
        if var_coord_dims != ("var",):
            raise ShapeValidationError("coords['var'] must be one-dimensional over the var axis.")
        var_values = np.asarray(var_coord.values)
        if var_values.ndim != 1:
            raise ShapeValidationError("coords['var'] must be one-dimensional.")
        if var_values.shape[0] != 1:
            raise ScopeValidationError("from_xarray only supports a singleton var axis in the stable scalar slice.")
        return _normalize_var_name_candidate(var_values[0], source_name="coords['var']")

    if data_array.name is not None:
        return _normalize_var_name_candidate(data_array.name, source_name="data_array.name")

    raise SchemaValidationError(
        "from_xarray requires a variable name via explicit var_name, a singleton coords['var'] entry, or DataArray.name."
    )


def _validate_mask(mask: object, *, data_array: object, normalized_dims: tuple[str, ...], xr: object) -> np.ndarray:
    if isinstance(mask, xr.Dataset):
        raise SchemaValidationError("mask must be an xarray.DataArray.")
    if not isinstance(mask, xr.DataArray):
        raise SchemaValidationError("mask must be an xarray.DataArray.")

    mask_dims = tuple(str(dim) for dim in mask.dims)
    if mask_dims != normalized_dims:
        raise ShapeValidationError("mask.dims must exactly match data_array.dims.")

    normalized_mask = np.asarray(mask.values, dtype=bool)
    if normalized_mask.shape != data_array.shape:
        raise ShapeValidationError("mask must match the pre-normalized data_array shape.")
    return normalized_mask.copy()


def from_xarray(
    data_array: object,
    *,
    var_name: str | None = None,
    metadata: Mapping[str, Any],
    mask: object | None = None,
    preprocess_log: Sequence[Mapping[str, Any]] | None = None,
) -> FieldBatch:
    xr = _require_xarray()

    if isinstance(data_array, xr.Dataset):
        raise ScopeValidationError("from_xarray only supports xarray.DataArray in the frozen V0.7 stable slice.")
    if not isinstance(data_array, xr.DataArray):
        raise SchemaValidationError("data_array must be an xarray.DataArray.")

    normalized_dims = _normalize_dims(data_array.dims)
    resolved_var_name = _resolve_var_name(
        data_array,
        normalized_dims=normalized_dims,
        explicit_var_name=var_name,
    )

    values_array = _to_float_array(data_array.values, name="data_array.values")
    if values_array.ndim != len(normalized_dims):
        raise ShapeValidationError("data_array values rank must match data_array.dims length.")

    if "var" in normalized_dims:
        var_axis = normalized_dims.index("var")
        if values_array.shape[var_axis] != 1:
            raise ScopeValidationError("from_xarray only supports a singleton var axis in the stable scalar slice.")

    if "time" not in data_array.coords:
        raise SchemaValidationError("coords['time'] is required.")
    if "x" not in data_array.coords:
        raise SchemaValidationError("coords['x'] is required.")

    time_coord = _validate_time_coord(
        data_array.coords["time"].values,
        expected_length=values_array.shape[normalized_dims.index("time")],
    )
    x_coord = _validate_x_coord(
        data_array.coords["x"].values,
        expected_length=values_array.shape[normalized_dims.index("x")],
    )
    normalized_metadata = _validate_metadata(metadata)
    normalized_preprocess_log = _validate_preprocess_log(preprocess_log)
    normalized_mask = None if mask is None else _validate_mask(mask, data_array=data_array, normalized_dims=normalized_dims, xr=xr)

    canonical_values, injected_batch_axis, injected_var_axis = _canonicalize_values(
        values_array,
        dims=normalized_dims,
    )
    canonical_mask = _canonicalize_mask(
        normalized_mask,
        injected_batch_axis=injected_batch_axis,
        injected_var_axis=injected_var_axis,
    )

    return FieldBatch(
        values=canonical_values.copy(),
        dims=_CANONICAL_DIMS,
        coords={"time": time_coord.copy(), "x": x_coord.copy()},
        var_names=[resolved_var_name],
        metadata=deepcopy(normalized_metadata),
        preprocess_log=[
            *deepcopy(normalized_preprocess_log),
            {
                "operation": "from_xarray",
                "parameters": {
                    "source_layout": list(normalized_dims),
                    "imported_shape": list(values_array.shape),
                    "canonical_shape": list(canonical_values.shape),
                    "injected_batch_axis": injected_batch_axis,
                    "injected_var_axis": injected_var_axis,
                    "mask_provided": mask is not None,
                },
            },
        ],
        mask=None if canonical_mask is None else canonical_mask.copy(),
    )


__all__ = ["from_xarray"]
