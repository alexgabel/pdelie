from __future__ import annotations

from typing import Any

import numpy as np

from pdelie.contracts import FieldBatch, InvariantMapSpec
from pdelie.errors import SchemaValidationError, ScopeValidationError


def _validate_supported_field(field: FieldBatch) -> None:
    if field.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError("InvariantApplier only supports dims ('batch', 'time', 'x', 'var') in V0.3 Milestone 1.")
    if len(field.var_names) != 1:
        raise ScopeValidationError("InvariantApplier only supports a single scalar variable in V0.3 Milestone 1.")
    if field.metadata["boundary_conditions"].get("x") != "periodic":
        raise ScopeValidationError("InvariantApplier requires periodic boundary conditions in x.")


def _apply_uniform_translation(
    values: np.ndarray,
    axis: int,
    grid_size: int,
    dx: float,
    shift: float,
) -> np.ndarray:
    wavenumbers = 2.0 * np.pi * np.fft.fftfreq(grid_size, d=dx)
    phase = np.exp(-1j * wavenumbers * shift)
    reshape = [1] * values.ndim
    reshape[axis] = grid_size
    return np.real(np.fft.ifft(np.fft.fft(values, axis=axis) * phase.reshape(tuple(reshape)), axis=axis))


def _shift_field_values(field: FieldBatch, shift: float) -> np.ndarray:
    x = field.coords["x"]
    dx = float(x[1] - x[0])
    x_axis = field.dims.index("x")
    return _apply_uniform_translation(
        values=field.values,
        axis=x_axis,
        grid_size=x.size,
        dx=dx,
        shift=shift,
    )


def _copy_mapping(value: dict[str, Any]) -> dict[str, Any]:
    return {str(key): item for key, item in value.items()}


class InvariantApplier:
    def apply(self, field: FieldBatch, spec: InvariantMapSpec) -> FieldBatch:
        field.validate()
        spec.validate()
        _validate_supported_field(field)

        if spec.generator_metadata["parameterization"] != "polynomial_translation_affine":
            raise ScopeValidationError(
                "InvariantApplier only supports polynomial_translation_affine generators in V0.3 Milestone 1."
            )
        if spec.construction_method != "uniform_translation":
            raise ScopeValidationError(
                "InvariantApplier only supports the 'uniform_translation' construction_method in V0.3 Milestone 1."
            )
        if spec.domain_validity != "global":
            raise ScopeValidationError("InvariantApplier only supports global invariant specs in V0.3 Milestone 1.")
        if spec.diagnostics.get("approximate", False):
            raise ScopeValidationError("InvariantApplier does not support approximate invariant specs in V0.3 Milestone 1.")

        axis = spec.parameters.get("axis", "x")
        if axis != "x":
            raise ScopeValidationError("InvariantApplier only supports translation along x in V0.3 Milestone 1.")

        if "shift" not in spec.parameters:
            raise SchemaValidationError("uniform_translation invariant parameters must include 'shift'.")
        try:
            shift = float(spec.parameters["shift"])
        except (TypeError, ValueError) as exc:
            raise SchemaValidationError("uniform_translation invariant parameter 'shift' must be numeric.") from exc
        if not np.isfinite(shift):
            raise SchemaValidationError("uniform_translation invariant parameter 'shift' must be finite.")

        shifted_values = _shift_field_values(field, shift)
        preprocess_entry = {
            "operation": "invariant_apply",
            "construction_method": spec.construction_method,
            "generator_metadata": _copy_mapping(spec.generator_metadata),
            "parameters": _copy_mapping(spec.parameters),
            "domain_validity": spec.domain_validity,
            "inverse_available": spec.inverse_available,
            "diagnostics": _copy_mapping(spec.diagnostics),
        }

        return FieldBatch(
            values=shifted_values,
            dims=field.dims,
            coords={name: coord.copy() for name, coord in field.coords.items()},
            var_names=list(field.var_names),
            metadata=dict(field.metadata),
            preprocess_log=[*field.preprocess_log, preprocess_entry],
            mask=None if field.mask is None else field.mask.copy(),
        )
