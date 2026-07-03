from __future__ import annotations

from copy import deepcopy
import importlib
from typing import Any, Mapping, Sequence

import numpy as np

from pdelie._boundary import get_x_boundary_type
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


def _require_xarray(*, caller: str = "pdelie.data.from_xarray"):
    try:
        return importlib.import_module("xarray")
    except ModuleNotFoundError as exc:
        raise ImportError(f"xarray is required for {caller}; install pdelie[xarray].") from exc


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
    # Accept any supported boundary type (periodic, dirichlet, neumann, open_unknown).
    # Unsupported strings or malformed structured specs are rejected by the helper.
    # Derivative and residual support for non-periodic data is deferred to a later v0.30 milestone;
    # the adapter constructs FieldBatch objects but downstream consumers still reject nonperiodic.
    get_x_boundary_type({"boundary_conditions": boundary_conditions})

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
    return normalized_mask


def _validate_dataset_var_name(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaValidationError(f"{name} must be a non-empty string.")
    return value


def _is_dataset_data_var_candidate(data_array: object) -> bool:
    try:
        normalized_dims = _normalize_dims(data_array.dims)
        raw_values = np.asarray(data_array.values)
        if np.issubdtype(raw_values.dtype, np.bool_):
            return False
        values_array = _to_float_array(data_array.values, name="data_var.values")
    except (SchemaValidationError, ScopeValidationError, ShapeValidationError):
        return False
    if values_array.ndim != len(normalized_dims):
        return False
    if "var" in normalized_dims and values_array.shape[normalized_dims.index("var")] != 1:
        return False
    return True


def _compatible_dataset_data_vars(dataset: object, *, mask_var: str | None) -> list[str]:
    return [
        str(name)
        for name, data_array in dataset.data_vars.items()
        if str(name) != mask_var and _is_dataset_data_var_candidate(data_array)
    ]


def _resolve_dataset_data_var(dataset: object, *, data_var: str | None, mask_var: str | None) -> str:
    if data_var is not None:
        selected = _validate_dataset_var_name(data_var, name="data_var")
        if selected not in dataset.data_vars:
            raise SchemaValidationError(f"data_var {selected!r} is not present in the xarray.Dataset.")
        if selected == mask_var:
            raise SchemaValidationError("data_var and mask_var must refer to different Dataset variables.")
        if not _is_dataset_data_var_candidate(dataset.data_vars[selected]):
            raise SchemaValidationError(
                f"data_var {selected!r} is not a compatible numeric scalar data variable in the frozen Dataset slice."
            )
        return selected

    candidates = _compatible_dataset_data_vars(dataset, mask_var=mask_var)
    if not candidates:
        raise SchemaValidationError("from_xarray_dataset could not find a compatible numeric scalar data variable.")
    if len(candidates) > 1:
        raise SchemaValidationError(
            "from_xarray_dataset requires explicit data_var when multiple compatible variables are present: "
            f"{candidates}."
        )
    return candidates[0]


def _resolve_dataset_mask(dataset: object, *, mask_var: str | None, data_array: object) -> object | None:
    if mask_var is None:
        return None
    selected = _validate_dataset_var_name(mask_var, name="mask_var")
    if selected not in dataset.data_vars:
        raise SchemaValidationError(f"mask_var {selected!r} is not present in the xarray.Dataset.")
    mask = dataset.data_vars[selected]
    if tuple(str(dim) for dim in mask.dims) != tuple(str(dim) for dim in data_array.dims):
        raise ShapeValidationError("mask_var dims must exactly match the selected data variable dims.")
    if tuple(mask.shape) != tuple(data_array.shape):
        raise ShapeValidationError("mask_var shape must exactly match the selected data variable shape.")
    return mask


def from_xarray(
    data_array: object,
    *,
    var_name: str | None = None,
    metadata: Mapping[str, Any],
    mask: object | None = None,
    preprocess_log: Sequence[Mapping[str, Any]] | None = None,
) -> FieldBatch:
    xr = _require_xarray(caller="pdelie.data.from_xarray")

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
        coords={"time": time_coord, "x": x_coord},
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


def from_xarray_dataset(
    dataset: object,
    *,
    data_var: str | None = None,
    var_name: str | None = None,
    metadata: Mapping[str, Any],
    mask_var: str | None = None,
    preprocess_log: Sequence[Mapping[str, Any]] | None = None,
) -> FieldBatch:
    xr = _require_xarray(caller="pdelie.data.from_xarray_dataset")

    if isinstance(dataset, xr.DataArray):
        raise ScopeValidationError("from_xarray_dataset only supports xarray.Dataset; use from_xarray for DataArray inputs.")
    if not isinstance(dataset, xr.Dataset):
        raise SchemaValidationError("dataset must be an xarray.Dataset.")

    normalized_mask_var = None if mask_var is None else _validate_dataset_var_name(mask_var, name="mask_var")
    selected_data_var = _resolve_dataset_data_var(dataset, data_var=data_var, mask_var=normalized_mask_var)
    data_array = dataset.data_vars[selected_data_var]
    mask = _resolve_dataset_mask(dataset, mask_var=normalized_mask_var, data_array=data_array)
    resolved_var_name = _validate_string(var_name, name="var_name") if var_name is not None else selected_data_var
    normalized_preprocess_log = _validate_preprocess_log(preprocess_log)

    dataset_entry = {
        "operation": "from_xarray_dataset",
        "parameters": {
            "selected_data_var": selected_data_var,
            "selected_mask_var": normalized_mask_var,
            "dataset_data_vars": [str(name) for name in dataset.data_vars],
            "source_layout": [str(dim) for dim in data_array.dims],
            "imported_shape": list(data_array.shape),
        },
    }
    return from_xarray(
        data_array,
        var_name=resolved_var_name,
        metadata=metadata,
        mask=mask,
        preprocess_log=[*normalized_preprocess_log, dataset_entry],
    )


__all__ = ["from_xarray", "from_xarray_dataset"]
