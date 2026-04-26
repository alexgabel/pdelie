from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np

from pdelie.contracts import FieldBatch
from pdelie.errors import SchemaValidationError, ScopeValidationError


def _validate_field(field: object, *, function_name: str) -> FieldBatch:
    if not isinstance(field, FieldBatch):
        raise SchemaValidationError(f"{function_name} requires a FieldBatch input.")
    field.validate()
    return field


def _validate_nonnegative_scalar_float(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise SchemaValidationError(f"{name} must be a finite non-negative scalar.")
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{name} must be a finite non-negative scalar.") from exc
    if not np.isfinite(normalized) or normalized < 0.0:
        raise SchemaValidationError(f"{name} must be a finite non-negative scalar.")
    return normalized


def _validate_positive_integer_like(value: object, *, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise SchemaValidationError(f"{name} must be a positive integer.")
    normalized = int(value)
    if normalized < 1:
        raise SchemaValidationError(f"{name} must be a positive integer.")
    return normalized


def _validate_integer_like(value: object, *, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise SchemaValidationError(f"{name} must be an integer.")
    return int(value)


def _clone_field(
    field: FieldBatch,
    *,
    values: np.ndarray,
    coords: dict[str, np.ndarray],
    preprocess_entry: dict[str, Any],
    mask: np.ndarray | None,
) -> FieldBatch:
    return FieldBatch(
        values=values,
        dims=field.dims,
        coords={name: coord.copy() for name, coord in coords.items()},
        var_names=list(field.var_names),
        metadata=deepcopy(field.metadata),
        preprocess_log=[*deepcopy(field.preprocess_log), deepcopy(preprocess_entry)],
        mask=None if mask is None else mask.copy(),
    )


def add_gaussian_noise(
    field: FieldBatch,
    *,
    std_fraction: float,
    seed: int,
) -> FieldBatch:
    field = _validate_field(field, function_name="add_gaussian_noise")
    noise_fraction = _validate_nonnegative_scalar_float(std_fraction, name="std_fraction")
    normalized_seed = _validate_integer_like(seed, name="seed")

    values = np.asarray(field.values, dtype=float).copy()
    finite_mask = np.isfinite(values)
    if field.mask is None:
        eligible = finite_mask
        output_mask = None
    else:
        output_mask = field.mask.copy()
        eligible = finite_mask & ~output_mask

    if not np.any(eligible):
        raise SchemaValidationError("add_gaussian_noise requires at least one finite unmasked value.")

    reference_rms = float(np.sqrt(np.mean(np.square(values[eligible]))))
    noise_std = float(noise_fraction * reference_rms)

    if noise_std != 0.0:
        rng = np.random.default_rng(normalized_seed)
        eligible_count = int(np.count_nonzero(eligible))
        noise = rng.normal(scale=noise_std, size=eligible_count)
        values[eligible] = values[eligible] + noise

    return _clone_field(
        field,
        values=values,
        coords=field.coords,
        mask=output_mask,
        preprocess_entry={
            "operation": "add_gaussian_noise",
            "parameters": {
                "std_fraction": noise_fraction,
                "seed": normalized_seed,
                "noise_std": noise_std,
            },
        },
    )


def _subsample_axis(
    field: FieldBatch,
    *,
    dim_name: str,
    stride: int,
    function_name: str,
) -> FieldBatch:
    field = _validate_field(field, function_name=function_name)
    normalized_stride = _validate_positive_integer_like(stride, name="stride")
    if dim_name not in field.dims:
        raise ScopeValidationError(f"{function_name} requires a '{dim_name}' dimension.")

    axis = field.dims.index(dim_name)
    slicer = [slice(None)] * field.values.ndim
    slicer[axis] = slice(None, None, normalized_stride)
    values = field.values[tuple(slicer)].copy()
    coords = {name: coord.copy() for name, coord in field.coords.items()}
    if dim_name in coords:
        coords[dim_name] = coords[dim_name][::normalized_stride].copy()

    if dim_name == "x" and coords["x"].size < 2:
        raise ScopeValidationError("subsample_x must leave at least two x-points.")

    output_mask = None if field.mask is None else field.mask[tuple(slicer)].copy()
    return _clone_field(
        field,
        values=values,
        coords=coords,
        mask=output_mask,
        preprocess_entry={
            "operation": function_name,
            "parameters": {
                "stride": normalized_stride,
                "original_length": int(field.values.shape[axis]),
                "new_length": int(values.shape[axis]),
            },
        },
    )


def subsample_time(field: FieldBatch, *, stride: int) -> FieldBatch:
    return _subsample_axis(field, dim_name="time", stride=stride, function_name="subsample_time")


def subsample_x(field: FieldBatch, *, stride: int) -> FieldBatch:
    return _subsample_axis(field, dim_name="x", stride=stride, function_name="subsample_x")


def split_batch_train_heldout(
    field: FieldBatch,
    *,
    train_size: int,
    seed: int,
) -> tuple[FieldBatch, FieldBatch]:
    field = _validate_field(field, function_name="split_batch_train_heldout")
    normalized_train_size = _validate_integer_like(train_size, name="train_size")
    normalized_seed = _validate_integer_like(seed, name="seed")

    if "batch" not in field.dims:
        raise ScopeValidationError("split_batch_train_heldout requires a 'batch' dimension.")

    batch_axis = field.dims.index("batch")
    batch_size = int(field.values.shape[batch_axis])
    if batch_size < 2:
        raise SchemaValidationError("split_batch_train_heldout requires at least two batch items.")
    if not 1 <= normalized_train_size < batch_size:
        raise SchemaValidationError("train_size must satisfy 1 <= train_size < batch_size.")

    permutation = np.random.default_rng(normalized_seed).permutation(batch_size)
    train_indices = sorted(int(index) for index in permutation[:normalized_train_size])
    heldout_indices = sorted(int(index) for index in permutation[normalized_train_size:])

    def _slice_batch(indices: list[int], *, split_name: str) -> FieldBatch:
        values = np.take(field.values, indices=indices, axis=batch_axis).copy()
        mask = None if field.mask is None else np.take(field.mask, indices=indices, axis=batch_axis).copy()
        return _clone_field(
            field,
            values=values,
            coords=field.coords,
            mask=mask,
            preprocess_entry={
                "operation": "split_batch_train_heldout",
                "parameters": {
                    "train_size": normalized_train_size,
                    "seed": normalized_seed,
                    "split": split_name,
                    "selected_batch_indices": list(indices),
                },
            },
        )

    return _slice_batch(train_indices, split_name="train"), _slice_batch(heldout_indices, split_name="heldout")
