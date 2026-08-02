"""v0.37b: execute a declared action bundle.

v0.37a declared what an action *is*. This module applies one, and classifies
what was applied into one of six runtime paths so a report can say which
combination it measured rather than leaving it to be inferred.

Exactness, and where it stops
=============================

The only backend v0.37b implements is ``exact_grid_shift``: a periodic spatial
translation by an integer number of grid cells, applied with :func:`numpy.roll`.
That is *exact* -- it permutes samples and introduces no interpolation error at
all -- which matters because the whole point of the commutation report is to
attribute a residual difference to the transformation rather than to the
resampling used to apply it.

A shift that is **not** an integer multiple of ``dx`` is refused rather than
rounded. Rounding would silently change the action being measured, and the
resulting commutation error would be a property of the rounding, not of the
mathematics. ``fourier`` and ``linear`` are declared in
:data:`~pdelie.actions.execution_config.INTERPOLATION_BACKENDS` and are not
implemented here; asking for one raises.

The six runtime paths
=====================

======  ===============  =================  ================  ===============================
Path    State            Coefficient        Parameter         Meaning
======  ===============  =================  ================  ===============================
P-1     translation      identity           none              state only (the v0.36 path)
P-2     identity         shift              none              coefficient only
P-3     translation      shift              none              canonical co-transformation
P-4     translation      shift (opposed)    none              deliberate obstruction
P-5     identity         identity           rescale           scalar parameter only
P-6     translation      shift              rescale           complete declared action
======  ===============  =================  ================  ===============================

P-4 differs from P-3 only in the *sign* of the coefficient shift relative to the
state shift. It is expected to fail, and a report that called it ``confirmed``
would be reporting a broken measurement rather than a broken transformation.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from pdelie.actions.action_bundle import ProblemActionBundle
from pdelie.actions.execution_config import ActionExecutionConfig
from pdelie.contracts import FieldBatch
from pdelie.errors import ScopeValidationError, ShapeValidationError

__all__ = [
    "RUNTIME_PATHS",
    "BundleExecutionResult",
    "classify_runtime_path",
    "execute_bundle",
    "execute_coefficient_action",
    "execute_state_action",
    "shift_cells",
]

#: Every runtime path a bundle can be classified into.
RUNTIME_PATHS: tuple[str, ...] = ("P-1", "P-2", "P-3", "P-4", "P-5", "P-6")

#: Relative tolerance on "is this offset an integer number of cells".
#: A shift of ``k*dx`` computed in floating point will not land exactly on an
#: integer, so the check is against the accumulated error of that arithmetic,
#: not against zero.
_CELL_TOLERANCE = 1e-9


def _spatial_axis_index(field: FieldBatch, axis_name: str) -> int:
    if axis_name not in field.dims:
        raise ScopeValidationError(
            f"field has dims {list(field.dims)} and does not carry axis {axis_name!r}."
        )
    return field.dims.index(axis_name)


def _uniform_spacing(coordinate: np.ndarray, *, axis_name: str) -> float:
    values = np.asarray(coordinate, dtype=float).ravel()
    if values.size < 2:
        raise ShapeValidationError(f"axis {axis_name!r} needs at least two samples.")
    spacings = np.diff(values)
    first = float(spacings[0])
    if first <= 0.0:
        raise ScopeValidationError(f"axis {axis_name!r} must be strictly increasing.")
    if not np.allclose(spacings, first, rtol=1e-9, atol=0.0):
        raise ScopeValidationError(
            f"axis {axis_name!r} is not uniformly spaced; exact_grid_shift needs a "
            f"uniform grid, and a non-uniform one would make a cell shift "
            f"position-dependent."
        )
    return first


def shift_cells(offset: float, spacing: float, *, where: str = "shift.offset") -> int:
    """Convert a physical offset into whole grid cells, or refuse.

    ``offset`` is in the same units as the coordinate, not in cells. A shift that
    is not an integer number of cells is **refused, never rounded**: rounding
    would change the action being measured, and any commutation error that
    followed would describe the rounding rather than the transformation.
    """
    if spacing <= 0.0:
        raise ScopeValidationError("spacing must be positive.")
    cells = offset / spacing
    nearest = round(cells)
    if not math.isclose(cells, nearest, rel_tol=_CELL_TOLERANCE, abs_tol=_CELL_TOLERANCE):
        raise ScopeValidationError(
            f"{where}={offset!r} is {cells:.6f} cells at spacing {spacing!r}. "
            f"exact_grid_shift requires a whole number of cells; this is refused "
            f"rather than rounded, because rounding would silently measure a "
            f"different action than the one declared."
        )
    return int(nearest)


def _require_exact_backend(config: ActionExecutionConfig) -> None:
    if config.interpolation_backend != "exact_grid_shift":
        raise ScopeValidationError(
            f"interpolation_backend {config.interpolation_backend!r} is declared but "
            f"not implemented at v0.37b. Only 'exact_grid_shift' is available, and "
            f"it is the only one that introduces no resampling error of its own."
        )


def classify_runtime_path(bundle: ProblemActionBundle) -> str:
    """Which of the six paths this bundle exercises.

    P-4 is P-3 with the coefficient shift opposing the state shift. The
    distinction is the *sign*, so it is decided here rather than left for a
    reader to infer from two offsets in a payload.
    """
    if not isinstance(bundle, ProblemActionBundle):
        raise ScopeValidationError("classify_runtime_path requires a ProblemActionBundle.")

    state_translates = bundle.state_action.action_family == "spatial_translation"
    parameter_acts = bundle.parameter_action is not None
    acting = {
        name: action
        for name, action in bundle.coefficient_field_actions.items()
        if not action.is_identity
    }

    if not state_translates and not acting and parameter_acts:
        return "P-5"
    if not state_translates and acting and not parameter_acts:
        return "P-2"
    if state_translates and not acting and not parameter_acts:
        return "P-1"
    if state_translates and acting:
        if parameter_acts:
            return "P-6"
        state_offset = float(bundle.state_action.parameters.get("offset", 0.0))
        opposed = any(
            float(action.parameters.get("offset", 0.0)) * state_offset < 0.0
            for action in acting.values()
        )
        return "P-4" if opposed else "P-3"
    raise ScopeValidationError(
        f"bundle does not match any of the six declared runtime paths "
        f"{list(RUNTIME_PATHS)}: state_translates={state_translates}, "
        f"coefficient_actions={sorted(acting)}, parameter_action={parameter_acts}. "
        f"An unclassifiable combination is refused rather than reported as one of "
        f"the six."
    )


def execute_state_action(
    bundle: ProblemActionBundle, field: FieldBatch, config: ActionExecutionConfig
) -> FieldBatch:
    """Apply the bundle's state action to a field batch."""
    _require_exact_backend(config)
    if not isinstance(field, FieldBatch):
        raise ScopeValidationError("field must be a FieldBatch.")
    field.validate()

    family = bundle.state_action.action_family
    if family not in ("identity", "spatial_translation"):
        raise ScopeValidationError(
            f"state action family {family!r} is not executable at v0.37b; only "
            f"'identity' and 'spatial_translation' are."
        )
    if family == "identity":
        return field

    # np.roll wraps. That is the correct semantics for a periodic domain and the
    # wrong semantics for any other, where it would silently move the left edge
    # onto the right. The bundle declares which it is, so the declaration is
    # checked rather than assumed -- all six v0.37c cases are periodic, but a
    # nonperiodic bundle reaching here would be quietly mis-executed.
    domain_type = bundle.problem_instance.domain_type
    if domain_type != "periodic_uniform":
        raise ScopeValidationError(
            f"spatial_translation on domain_type {domain_type!r} is refused: the "
            f"exact_grid_shift backend wraps, which is only meaningful on a "
            f"periodic domain. A nonperiodic translation needs a crop or a "
            f"boundary-aware action, neither of which exists at v0.37b."
        )

    axis_name = bundle.problem_instance.spatial_axis_name
    axis = _spatial_axis_index(field, axis_name)
    spacing = _uniform_spacing(np.asarray(field.coords[axis_name]), axis_name=axis_name)
    offset = float(bundle.state_action.parameters.get("offset", 0.0))
    cells = shift_cells(offset, spacing, where="state_action.offset")

    shifted = np.roll(np.asarray(field.values), shift=cells, axis=axis)
    return FieldBatch(
        schema_version=field.schema_version,
        values=shifted,
        dims=field.dims,
        coords=dict(field.coords),
        var_names=field.var_names,
        metadata=dict(field.metadata),
        preprocess_log=list(field.preprocess_log),
        mask=None if field.mask is None else np.roll(np.asarray(field.mask), cells, axis=axis),
    )


def execute_coefficient_action(
    bundle: ProblemActionBundle,
    field_name: str,
    values: np.ndarray,
    config: ActionExecutionConfig,
    *,
    spacing: float,
) -> np.ndarray:
    """Apply the action declared for one coefficient field.

    ``values`` is the coefficient sampled on the spatial grid, so a ``shift``
    moves it along that grid by the same exact-cell rule the state uses.
    """
    _require_exact_backend(config)
    if field_name not in bundle.coefficient_field_actions:
        raise ScopeValidationError(
            f"bundle declares no action for coefficient field {field_name!r}."
        )
    action = bundle.coefficient_field_actions[field_name]
    array = np.asarray(values, dtype=float)

    if action.family == "identity":
        return array
    if action.family == "shift":
        cells = shift_cells(
            float(action.parameters["offset"]),
            spacing,
            where=f"coefficient_field_actions[{field_name!r}].offset",
        )
        return np.roll(array, shift=cells, axis=-1)
    if action.family == "scalar_rescale":
        return array * float(action.parameters["factor"])
    raise ScopeValidationError(f"unhandled coefficient action family {action.family!r}.")


def _resolve_parameter_targets(
    bundle: ProblemActionBundle, candidates: tuple[str, ...]
) -> frozenset[str]:
    """Which parameters a rescale acts on -- refusing rather than guessing.

    v0.38e. Until now this function did not exist and the factor was applied to
    *every* numeric parameter, because ``ActionRef`` carries no target. Measured
    on a two-parameter problem, a rescale meant for the viscosity also tripled
    the advection speed, and nothing in the report said so.

    Every v0.37c case declares exactly one numeric parameter, so "all" and "the
    declared one" were the same set and the ambiguity was unobservable. This
    changes no v0.37 result -- the same precedent as the domain gate added at
    v0.37b, which also closed a gap before it became load-bearing.

    Ambiguity is **refused, not resolved by convention**. Picking the first name
    alphabetically, or the only one that looks like a viscosity, would make the
    executed action depend on a rule written nowhere.
    """
    from pdelie.actions.coaction_consistency import (
        PARAMETER_TARGET_KEY,
        declared_parameter_targets,
    )

    declared = declared_parameter_targets(bundle)
    if declared is not None:
        return frozenset(declared)
    if len(candidates) == 1:
        return frozenset(candidates)
    if not candidates:
        raise ScopeValidationError(
            "a parameter action is declared, but the problem has no numeric "
            "parameter for it to act on."
        )
    raise ScopeValidationError(
        f"the parameter action declares no {PARAMETER_TARGET_KEY} and this "
        f"problem has {len(candidates)} numeric parameters {list(candidates)}. "
        f"Which one the action targets is not decidable from the bundle, so it "
        f"is refused rather than applied to all of them -- applying it to all "
        f"would transform quantities nobody declared an action on. Name the "
        f"target: parameters={{{PARAMETER_TARGET_KEY!r}: [...], 'factor': ...}}."
    )


@dataclass(frozen=True)
class BundleExecutionResult:
    """What executing a bundle produced, plus which path it took."""

    runtime_path: str
    transformed_field: FieldBatch
    transformed_coefficients: Mapping[str, np.ndarray]
    transformed_parameters: Mapping[str, float]
    state_shift_cells: int
    coefficient_shift_cells: Mapping[str, int]

    def as_dict(self) -> dict[str, Any]:
        """Strict-JSON summary. Arrays are described, never inlined."""
        return {
            "runtime_path": self.runtime_path,
            "state_shift_cells": self.state_shift_cells,
            "coefficient_shift_cells": dict(self.coefficient_shift_cells),
            "transformed_parameters": dict(self.transformed_parameters),
            "coefficient_field_names": sorted(self.transformed_coefficients),
        }


def execute_bundle(
    bundle: ProblemActionBundle,
    field: FieldBatch,
    config: ActionExecutionConfig,
    *,
    coefficient_values: Mapping[str, np.ndarray] | None = None,
) -> BundleExecutionResult:
    """Execute every action the bundle declares, and say which path that was."""
    if not isinstance(config, ActionExecutionConfig):
        raise ScopeValidationError("config must be an ActionExecutionConfig.")
    _require_exact_backend(config)
    runtime_path = classify_runtime_path(bundle)

    axis_name = bundle.problem_instance.spatial_axis_name
    spacing = _uniform_spacing(np.asarray(field.coords[axis_name]), axis_name=axis_name)

    transformed_field = execute_state_action(bundle, field, config)
    state_cells = (
        0
        if bundle.state_action.action_family == "identity"
        else shift_cells(
            float(bundle.state_action.parameters.get("offset", 0.0)),
            spacing,
            where="state_action.offset",
        )
    )

    supplied = dict(coefficient_values or {})
    missing = sorted(set(bundle.problem_instance.coefficient_fields) - set(supplied))
    if missing and any(
        not bundle.coefficient_field_actions[name].is_identity for name in missing
    ):
        raise ScopeValidationError(
            f"coefficient_values omits {missing}, and a non-identity action is "
            f"declared for at least one of them; there is nothing to transform."
        )

    transformed_coefficients: dict[str, np.ndarray] = {}
    coefficient_cells: dict[str, int] = {}
    for name, values in supplied.items():
        transformed_coefficients[name] = execute_coefficient_action(
            bundle, name, values, config, spacing=spacing
        )
        action = bundle.coefficient_field_actions[name]
        coefficient_cells[name] = (
            shift_cells(
                float(action.parameters["offset"]),
                spacing,
                where=f"coefficient_field_actions[{name!r}].offset",
            )
            if action.family == "shift"
            else 0
        )

    parameters = dict(bundle.problem_instance.parameters)
    transformed_parameters = {
        key: float(value)
        for key, value in parameters.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    if bundle.parameter_action is not None:
        if bundle.parameter_action.action_family != "scalar_rescale":
            raise ScopeValidationError(
                f"parameter action family {bundle.parameter_action.action_family!r} is "
                f"not executable at v0.37b; only 'scalar_rescale' is."
            )
        targets = _resolve_parameter_targets(bundle, tuple(sorted(transformed_parameters)))
        factor = float(bundle.parameter_action.parameters.get("factor", 1.0))
        transformed_parameters = {
            key: (value * factor if key in targets else value)
            for key, value in transformed_parameters.items()
        }

    return BundleExecutionResult(
        runtime_path=runtime_path,
        transformed_field=transformed_field,
        transformed_coefficients=transformed_coefficients,
        transformed_parameters=transformed_parameters,
        state_shift_cells=state_cells,
        coefficient_shift_cells=coefficient_cells,
    )
