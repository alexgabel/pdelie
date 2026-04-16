from __future__ import annotations

import json
from dataclasses import dataclass, fields
from typing import Any, ClassVar, Mapping

import numpy as np

from pdelie.errors import (
    SchemaValidationError,
    ScopeValidationError,
    ShapeValidationError,
)


REQUIRED_METADATA_KEYS = (
    "boundary_conditions",
    "coordinate_system",
    "grid_regularity",
    "grid_type",
    "parameter_tags",
)
ALLOWED_DERIVATIVE_BACKENDS = frozenset({"spectral_fd", "spectral", "finite", "weak"})
ALLOWED_RESIDUAL_TYPES = frozenset({"analytic", "weak", "surrogate", "operator"})
ALLOWED_CLASSIFICATIONS = frozenset({"exact", "approximate", "failed"})
SPATIAL_DIMS = ("x", "y", "z")


def _to_numpy(value: Any) -> np.ndarray:
    return np.asarray(value, dtype=float)


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _is_uniform(coord: np.ndarray, tol: float = 1e-10) -> bool:
    if coord.ndim != 1:
        return False
    if coord.size <= 2:
        return True
    diffs = np.diff(coord)
    return np.allclose(diffs, diffs[0], atol=tol, rtol=0.0)


def _validate_json_round_trip(payload: dict[str, Any]) -> None:
    try:
        json.dumps(payload)
    except TypeError as exc:
        raise SchemaValidationError("Object must be JSON-compatible.") from exc


def _validate_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{name} must be a mapping.")
    return value


def _validate_dims_order(dims: tuple[str, ...]) -> None:
    if not dims:
        raise SchemaValidationError("dims must not be empty.")
    if dims[-1] != "var":
        raise SchemaValidationError("dims must end with 'var'.")

    remaining = list(dims[:-1])
    if remaining and remaining[0] == "batch":
        remaining.pop(0)
    if remaining and remaining[0] == "time":
        remaining.pop(0)

    spatial = [dim for dim in remaining if dim in SPATIAL_DIMS]
    if spatial != remaining:
        raise SchemaValidationError("Only batch, time, spatial dims, and var are allowed.")

    expected_prefix = [dim for dim in SPATIAL_DIMS if dim in spatial]
    if spatial != expected_prefix:
        raise SchemaValidationError("Spatial dims must be ordered as x, y, z.")


@dataclass(slots=True)
class FieldBatch:
    schema_version: str = "0.1"
    values: np.ndarray = None  # type: ignore[assignment]
    dims: tuple[str, ...] = ()
    coords: dict[str, np.ndarray] = None  # type: ignore[assignment]
    var_names: list[str] = None  # type: ignore[assignment]
    metadata: dict[str, Any] = None  # type: ignore[assignment]
    preprocess_log: list[dict[str, Any]] = None  # type: ignore[assignment]
    mask: np.ndarray | None = None

    SCHEMA_VERSION: ClassVar[str] = "0.1"

    def __post_init__(self) -> None:
        self.values = _to_numpy(self.values)
        self.dims = tuple(self.dims)
        self.coords = {
            str(name): _to_numpy(coord) for name, coord in _validate_mapping(self.coords, "coords").items()
        }
        self.var_names = [str(name) for name in self.var_names]
        self.metadata = dict(_validate_mapping(self.metadata, "metadata"))
        if self.preprocess_log is None:
            raise SchemaValidationError("preprocess_log must be provided.")
        self.preprocess_log = [dict(item) for item in self.preprocess_log]
        if self.mask is not None:
            self.mask = np.asarray(self.mask, dtype=bool)
        self.validate()

    def validate(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise SchemaValidationError("Unsupported FieldBatch schema_version.")
        if self.values.ndim != len(self.dims):
            raise ShapeValidationError("values rank must match dims length.")

        _validate_dims_order(self.dims)

        if len(set(self.dims)) != len(self.dims):
            raise SchemaValidationError("dims entries must be unique.")
        if not self.var_names:
            raise SchemaValidationError("var_names must not be empty.")
        if self.values.shape[-1] != len(self.var_names):
            raise ShapeValidationError("var_names length must match the var axis.")

        required_coord_dims = [dim for dim in self.dims if dim not in {"batch", "var"}]
        missing_coords = [dim for dim in required_coord_dims if dim not in self.coords]
        if missing_coords:
            raise SchemaValidationError(f"Missing coordinate arrays for dims: {missing_coords}.")

        for dim_name, coord in self.coords.items():
            if dim_name not in self.dims:
                raise SchemaValidationError(f"Coordinate '{dim_name}' is not present in dims.")
            if coord.ndim != 1:
                raise ShapeValidationError(f"Coordinate '{dim_name}' must be one-dimensional.")
            axis = self.dims.index(dim_name)
            if coord.shape[0] != self.values.shape[axis]:
                raise ShapeValidationError(f"Coordinate '{dim_name}' length must match its axis.")
            if dim_name in SPATIAL_DIMS and not _is_uniform(coord):
                raise ScopeValidationError("Stable V0.1 scope only supports uniform rectilinear grids.")

        missing_metadata = [key for key in REQUIRED_METADATA_KEYS if key not in self.metadata]
        if missing_metadata:
            raise SchemaValidationError(f"metadata is missing required keys: {missing_metadata}.")

        if self.metadata["grid_type"] != "rectilinear":
            raise ScopeValidationError("Stable V0.1 scope only supports rectilinear grids.")
        if self.metadata["grid_regularity"] != "uniform":
            raise ScopeValidationError("Stable V0.1 scope only supports uniform rectilinear grids.")

        if not isinstance(self.metadata["boundary_conditions"], Mapping):
            raise SchemaValidationError("metadata['boundary_conditions'] must be a mapping.")
        if not isinstance(self.metadata["parameter_tags"], Mapping):
            raise SchemaValidationError("metadata['parameter_tags'] must be a mapping.")

        if self.mask is not None and self.mask.shape != self.values.shape:
            raise ShapeValidationError("mask must match the shape of values.")

        _validate_json_round_trip(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "values": _json_safe(self.values),
            "dims": list(self.dims),
            "coords": _json_safe(self.coords),
            "var_names": list(self.var_names),
            "metadata": _json_safe(self.metadata),
            "preprocess_log": _json_safe(self.preprocess_log),
            "mask": _json_safe(self.mask),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FieldBatch":
        return cls(
            schema_version=str(payload["schema_version"]),
            values=np.asarray(payload["values"], dtype=float),
            dims=tuple(payload["dims"]),
            coords={str(name): np.asarray(coord, dtype=float) for name, coord in payload["coords"].items()},
            var_names=[str(name) for name in payload["var_names"]],
            metadata=dict(payload["metadata"]),
            preprocess_log=[dict(item) for item in payload["preprocess_log"]],
            mask=None if payload.get("mask") is None else np.asarray(payload["mask"], dtype=bool),
        )


@dataclass(slots=True)
class DerivativeBatch:
    schema_version: str = "0.1"
    derivatives: dict[str, np.ndarray] = None  # type: ignore[assignment]
    backend: str = ""
    config: dict[str, Any] = None  # type: ignore[assignment]
    boundary_assumptions: str = ""
    diagnostics: dict[str, Any] = None  # type: ignore[assignment]

    SCHEMA_VERSION: ClassVar[str] = "0.1"

    def __post_init__(self) -> None:
        self.derivatives = {
            str(name): _to_numpy(array)
            for name, array in _validate_mapping(self.derivatives, "derivatives").items()
        }
        self.config = dict(_validate_mapping(self.config, "config"))
        self.diagnostics = dict(_validate_mapping(self.diagnostics, "diagnostics"))
        self.validate()

    def validate(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise SchemaValidationError("Unsupported DerivativeBatch schema_version.")
        if self.backend not in ALLOWED_DERIVATIVE_BACKENDS:
            raise SchemaValidationError(f"Unsupported derivative backend: {self.backend}.")
        if not self.derivatives:
            raise SchemaValidationError("derivatives must not be empty.")
        if not isinstance(self.boundary_assumptions, str) or not self.boundary_assumptions:
            raise SchemaValidationError("boundary_assumptions must be a non-empty string.")

        shapes = {array.shape for array in self.derivatives.values()}
        if len(shapes) != 1:
            raise ShapeValidationError("All derivative arrays must share the same shape.")

        _validate_json_round_trip(self.to_dict())

    def validate_against(self, field: FieldBatch) -> None:
        for name, array in self.derivatives.items():
            if array.shape != field.values.shape:
                raise ShapeValidationError(f"Derivative '{name}' must match the FieldBatch shape.")
            if "_" not in name:
                raise SchemaValidationError(f"Derivative '{name}' must encode a variable and wrt suffix.")
            variable_name, suffix = name.split("_", 1)
            if variable_name not in field.var_names:
                raise SchemaValidationError(f"Derivative '{name}' references an unknown variable.")
            axis_suffixes = tuple(char for char in suffix if char.isalpha())
            if not axis_suffixes:
                raise SchemaValidationError(f"Derivative '{name}' must include derivative directions.")
            for axis_name in axis_suffixes:
                if axis_name == "t":
                    if "time" not in field.dims:
                        raise SchemaValidationError("Time derivatives require a time dimension.")
                    continue
                if axis_name not in SPATIAL_DIMS or axis_name not in field.dims:
                    raise SchemaValidationError(f"Derivative '{name}' references an unsupported dimension.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "derivatives": _json_safe(self.derivatives),
            "backend": self.backend,
            "config": _json_safe(self.config),
            "boundary_assumptions": self.boundary_assumptions,
            "diagnostics": _json_safe(self.diagnostics),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DerivativeBatch":
        return cls(
            schema_version=str(payload["schema_version"]),
            derivatives={
                str(name): np.asarray(array, dtype=float) for name, array in payload["derivatives"].items()
            },
            backend=str(payload["backend"]),
            config=dict(payload["config"]),
            boundary_assumptions=str(payload["boundary_assumptions"]),
            diagnostics=dict(payload["diagnostics"]),
        )


@dataclass(slots=True)
class ResidualBatch:
    schema_version: str = "0.1"
    residual: np.ndarray = None  # type: ignore[assignment]
    definition_type: str = ""
    normalization: str = ""
    diagnostics: dict[str, Any] = None  # type: ignore[assignment]

    SCHEMA_VERSION: ClassVar[str] = "0.1"

    def __post_init__(self) -> None:
        self.residual = _to_numpy(self.residual)
        self.diagnostics = dict(_validate_mapping(self.diagnostics, "diagnostics"))
        self.validate()

    def validate(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise SchemaValidationError("Unsupported ResidualBatch schema_version.")
        if self.definition_type not in ALLOWED_RESIDUAL_TYPES:
            raise SchemaValidationError(f"Unsupported residual definition_type: {self.definition_type}.")
        if not isinstance(self.normalization, str) or not self.normalization:
            raise SchemaValidationError("normalization must be a non-empty string.")
        _validate_json_round_trip(self.to_dict())

    def validate_against(self, field: FieldBatch) -> None:
        if self.residual.shape != field.values.shape:
            raise ShapeValidationError("ResidualBatch residual must match the FieldBatch shape.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "residual": _json_safe(self.residual),
            "definition_type": self.definition_type,
            "normalization": self.normalization,
            "diagnostics": _json_safe(self.diagnostics),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResidualBatch":
        return cls(
            schema_version=str(payload["schema_version"]),
            residual=np.asarray(payload["residual"], dtype=float),
            definition_type=str(payload["definition_type"]),
            normalization=str(payload["normalization"]),
            diagnostics=dict(payload["diagnostics"]),
        )


@dataclass(slots=True)
class GeneratorFamily:
    schema_version: str = "0.1"
    parameterization: str = ""
    coefficients: np.ndarray = None  # type: ignore[assignment]
    normalization: str = ""
    diagnostics: dict[str, Any] = None  # type: ignore[assignment]

    SCHEMA_VERSION: ClassVar[str] = "0.1"

    def __post_init__(self) -> None:
        self.coefficients = _to_numpy(self.coefficients)
        self.diagnostics = dict(_validate_mapping(self.diagnostics, "diagnostics"))
        self.validate()

    def validate(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise SchemaValidationError("Unsupported GeneratorFamily schema_version.")
        if self.coefficients.ndim != 1 or self.coefficients.size == 0:
            raise ShapeValidationError("coefficients must be a non-empty one-dimensional array.")
        if not isinstance(self.parameterization, str) or not self.parameterization:
            raise SchemaValidationError("parameterization must be a non-empty string.")
        if not isinstance(self.normalization, str) or not self.normalization:
            raise SchemaValidationError("normalization must be a non-empty string.")
        if self.normalization == "l2_unit":
            norm = np.linalg.norm(self.coefficients)
            if not np.isclose(norm, 1.0, atol=1e-8):
                raise ShapeValidationError("l2_unit generators must have unit L2 norm.")
        _validate_json_round_trip(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "parameterization": self.parameterization,
            "coefficients": _json_safe(self.coefficients),
            "normalization": self.normalization,
            "diagnostics": _json_safe(self.diagnostics),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GeneratorFamily":
        return cls(
            schema_version=str(payload["schema_version"]),
            parameterization=str(payload["parameterization"]),
            coefficients=np.asarray(payload["coefficients"], dtype=float),
            normalization=str(payload["normalization"]),
            diagnostics=dict(payload["diagnostics"]),
        )


@dataclass(slots=True)
class VerificationReport:
    schema_version: str = "0.1"
    norm: str = ""
    epsilon_values: np.ndarray = None  # type: ignore[assignment]
    error_curve: np.ndarray = None  # type: ignore[assignment]
    classification: str = ""
    diagnostics: dict[str, Any] = None  # type: ignore[assignment]

    SCHEMA_VERSION: ClassVar[str] = "0.1"

    def __post_init__(self) -> None:
        self.epsilon_values = _to_numpy(self.epsilon_values)
        self.error_curve = _to_numpy(self.error_curve)
        self.diagnostics = dict(_validate_mapping(self.diagnostics, "diagnostics"))
        self.validate()

    def validate(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise SchemaValidationError("Unsupported VerificationReport schema_version.")
        if self.classification not in ALLOWED_CLASSIFICATIONS:
            raise SchemaValidationError(f"Unsupported classification: {self.classification}.")
        if not isinstance(self.norm, str) or not self.norm:
            raise SchemaValidationError("norm must be a non-empty string.")
        if self.epsilon_values.ndim != 1 or self.error_curve.ndim != 1:
            raise ShapeValidationError("epsilon_values and error_curve must be one-dimensional.")
        if self.epsilon_values.size < 5:
            raise ShapeValidationError("epsilon_values must contain at least 5 values.")
        if self.epsilon_values.shape != self.error_curve.shape:
            raise ShapeValidationError("error_curve must match epsilon_values shape.")
        if np.any(np.diff(self.epsilon_values) <= 0.0):
            raise ShapeValidationError("epsilon_values must be strictly increasing.")
        _validate_json_round_trip(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "norm": self.norm,
            "epsilon_values": _json_safe(self.epsilon_values),
            "error_curve": _json_safe(self.error_curve),
            "classification": self.classification,
            "diagnostics": _json_safe(self.diagnostics),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "VerificationReport":
        return cls(
            schema_version=str(payload["schema_version"]),
            norm=str(payload["norm"]),
            epsilon_values=np.asarray(payload["epsilon_values"], dtype=float),
            error_curve=np.asarray(payload["error_curve"], dtype=float),
            classification=str(payload["classification"]),
            diagnostics=dict(payload["diagnostics"]),
        )

