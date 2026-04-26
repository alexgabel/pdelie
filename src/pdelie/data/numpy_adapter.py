from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

import numpy as np

from pdelie.contracts import FieldBatch, REQUIRED_METADATA_KEYS, _is_uniform
from pdelie.errors import SchemaValidationError, ScopeValidationError, ShapeValidationError


_ACCEPTED_LAYOUTS = frozenset(
    {
        ("time", "x"),
        ("batch", "time", "x"),
        ("time", "x", "var"),
        ("batch", "time", "x", "var"),
    }
)
_CANONICAL_DIMS = ("batch", "time", "x", "var")
_TIME_UNIFORM_ABS_TOL = 1e-12


def _validate_mapping(value: object, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{name} must be a mapping.")
    return value


def _validate_string(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaValidationError(f"{name} must be a non-empty string.")
    return value


def _normalize_dims(dims: object) -> tuple[str, ...]:
    if not isinstance(dims, (list, tuple)):
        raise SchemaValidationError("dims must be a list or tuple of strings.")
    normalized = tuple(str(dim) for dim in dims)
    if any(not dim for dim in normalized):
        raise SchemaValidationError("dims entries must be non-empty strings.")
    if len(set(normalized)) != len(normalized):
        raise SchemaValidationError("dims entries must be unique.")
    if normalized not in _ACCEPTED_LAYOUTS:
        raise ScopeValidationError(
            "from_numpy only supports the frozen V0.7 layouts: "
            "('time', 'x'), ('batch', 'time', 'x'), ('time', 'x', 'var'), ('batch', 'time', 'x', 'var')."
        )
    return normalized


def _to_float_array(value: object, *, name: str) -> np.ndarray:
    try:
        return np.asarray(value, dtype=float)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{name} must be numeric and array-like.") from exc


def _strictly_increasing(coord: np.ndarray) -> bool:
    return bool(np.all(np.diff(coord) > 0.0))


def _validate_time_coord(coord: object, *, expected_length: int) -> np.ndarray:
    time = _to_float_array(coord, name="coords['time']")
    if time.ndim != 1:
        raise ShapeValidationError("coords['time'] must be one-dimensional.")
    if time.shape[0] != expected_length:
        raise ShapeValidationError("coords['time'] length must match the time axis.")
    if time.size < 3:
        raise ScopeValidationError("from_numpy requires at least three time points.")
    if not np.isfinite(time).all():
        raise SchemaValidationError("coords['time'] must contain only finite values.")
    if not _strictly_increasing(time):
        raise SchemaValidationError("coords['time'] must be strictly increasing.")
    time_step = float(time[1] - time[0])
    if not np.allclose(np.diff(time), time_step, atol=_TIME_UNIFORM_ABS_TOL, rtol=0.0):
        raise ScopeValidationError("from_numpy requires uniformly spaced time coordinates.")
    return time.copy()


def _validate_x_coord(coord: object, *, expected_length: int) -> np.ndarray:
    x = _to_float_array(coord, name="coords['x']")
    if x.ndim != 1:
        raise ShapeValidationError("coords['x'] must be one-dimensional.")
    if x.shape[0] != expected_length:
        raise ShapeValidationError("coords['x'] length must match the x axis.")
    if x.size < 4:
        raise ScopeValidationError("from_numpy requires at least four x-points.")
    if not np.isfinite(x).all():
        raise SchemaValidationError("coords['x'] must contain only finite values.")
    if not _strictly_increasing(x):
        raise SchemaValidationError("coords['x'] must be strictly increasing.")
    if not _is_uniform(x):
        raise ScopeValidationError("from_numpy only supports uniform rectilinear x coordinates.")
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
        raise ScopeValidationError("from_numpy only supports rectilinear grids.")
    if metadata["grid_regularity"] != "uniform":
        raise ScopeValidationError("from_numpy only supports uniform rectilinear grids.")
    if metadata["coordinate_system"] != "cartesian":
        raise ScopeValidationError("from_numpy only supports cartesian coordinates.")
    if boundary_conditions["x"] != "periodic":
        raise ScopeValidationError("from_numpy only supports periodic x boundary conditions.")

    return metadata


def _validate_preprocess_log(value: object) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SchemaValidationError("preprocess_log must be a sequence of mappings.")

    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise SchemaValidationError(f"preprocess_log[{index}] must be a mapping.")
        normalized.append(deepcopy(dict(item)))
    return normalized


def _validate_mask(mask: object, *, expected_shape: tuple[int, ...]) -> np.ndarray:
    normalized = np.asarray(mask, dtype=bool)
    if normalized.shape != expected_shape:
        raise ShapeValidationError("mask must match the pre-normalized values shape.")
    return normalized.copy()


def _canonicalize_values(
    values: np.ndarray,
    *,
    dims: tuple[str, ...],
) -> tuple[np.ndarray, bool, bool]:
    canonical = values.copy()
    injected_batch_axis = False
    injected_var_axis = False

    if "batch" not in dims:
        canonical = np.expand_dims(canonical, axis=0)
        injected_batch_axis = True
    if "var" not in dims:
        canonical = np.expand_dims(canonical, axis=-1)
        injected_var_axis = True

    return canonical, injected_batch_axis, injected_var_axis


def _canonicalize_mask(
    mask: np.ndarray | None,
    *,
    injected_batch_axis: bool,
    injected_var_axis: bool,
) -> np.ndarray | None:
    if mask is None:
        return None
    canonical = mask.copy()
    if injected_batch_axis:
        canonical = np.expand_dims(canonical, axis=0)
    if injected_var_axis:
        canonical = np.expand_dims(canonical, axis=-1)
    return canonical.copy()


def from_numpy(
    values: object,
    *,
    dims: tuple[str, ...] | list[str],
    coords: Mapping[str, object],
    var_name: str,
    metadata: Mapping[str, Any],
    mask: object | None = None,
    preprocess_log: Sequence[Mapping[str, Any]] | None = None,
) -> FieldBatch:
    normalized_dims = _normalize_dims(dims)
    normalized_var_name = _validate_string(var_name, name="var_name")

    values_array = _to_float_array(values, name="values")
    if values_array.ndim != len(normalized_dims):
        raise ShapeValidationError("values rank must match dims length.")

    if "var" in normalized_dims:
        var_axis = normalized_dims.index("var")
        if values_array.shape[var_axis] != 1:
            raise ScopeValidationError("from_numpy only supports a singleton var axis in the stable scalar slice.")

    coords_mapping = _validate_mapping(coords, name="coords")
    if "time" not in coords_mapping:
        raise SchemaValidationError("coords['time'] is required.")
    if "x" not in coords_mapping:
        raise SchemaValidationError("coords['x'] is required.")

    time_coord = _validate_time_coord(coords_mapping["time"], expected_length=values_array.shape[normalized_dims.index("time")])
    x_coord = _validate_x_coord(coords_mapping["x"], expected_length=values_array.shape[normalized_dims.index("x")])
    normalized_metadata = _validate_metadata(metadata)
    normalized_preprocess_log = _validate_preprocess_log(preprocess_log)
    normalized_mask = None if mask is None else _validate_mask(mask, expected_shape=values_array.shape)

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
        var_names=[normalized_var_name],
        metadata=deepcopy(normalized_metadata),
        preprocess_log=[
            *deepcopy(normalized_preprocess_log),
            {
                "operation": "from_numpy",
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


__all__ = ["from_numpy"]
