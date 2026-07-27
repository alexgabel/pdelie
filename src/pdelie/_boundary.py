"""Internal boundary-condition helpers.

Implements the v0.30b runtime plumbing for the structured `BoundaryConditionSpec`
designed in `docs/design/BOUNDARY_CONDITION_SPEC.md`.

The helpers in this module are the single canonical entry point for reading and
normalizing `metadata['boundary_conditions']['x']`. All consumers that need to
know the boundary type must go through `get_x_boundary_type` or `is_x_periodic`
rather than comparing the raw value directly. This keeps the legacy 0.1 string
form and the 0.2 structured form interchangeable while the codebase migrates.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pdelie.errors import SchemaValidationError, ScopeValidationError

ALLOWED_X_BOUNDARY_TYPES = frozenset({"periodic", "dirichlet", "neumann", "open_unknown"})
ALLOWED_BOUNDARY_FACE_SOURCES = frozenset({"user_supplied", "default", "inferred_unspecified"})

# Legacy 0.1 string inputs accepted by adapters and `FieldBatch.from_dict`.
# Per the v0.30a design, `"open"` is renamed to `"open_unknown"` on normalization
# so the canonical name reflects the PDELie convention "finite domain, BC unstated".
_LEGACY_X_BOUNDARY_STRING_ALIASES: dict[str, str] = {
    "periodic": "periodic",
    "dirichlet": "dirichlet",
    "neumann": "neumann",
    "open": "open_unknown",
    "open_unknown": "open_unknown",
}

# Migration provenance marker recorded in `preprocess_log` when a 0.1 payload
# is normalized to the 0.2 structured form.
LEGACY_BOUNDARY_NORMALIZATION_OPERATION = "schema_0_1_to_0_2_boundary_normalization"

_BC_TYPES_WITH_FACES = frozenset({"dirichlet", "neumann"})


@dataclass(frozen=True, slots=True)
class BoundaryFace:
    """One face (left or right) of a non-periodic boundary.

    The library does not invent boundary values. A face whose `value` is `None`
    or whose `source` is `"inferred_unspecified"` always counts as missing data
    for the purpose of `BoundaryConditionSpec.specified`.
    """

    value: float | None
    time_dependent: bool
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": None if self.value is None else float(self.value),
            "time_dependent": bool(self.time_dependent),
            "source": str(self.source),
        }

    @classmethod
    def from_dict(cls, value: object) -> BoundaryFace:
        if not isinstance(value, Mapping):
            raise SchemaValidationError("BoundaryFace must be a mapping.")
        raw_value = value.get("value")
        normalized_value = _validate_optional_finite_scalar(raw_value, name="BoundaryFace.value")
        raw_time_dependent = value.get("time_dependent", False)
        if not isinstance(raw_time_dependent, bool):
            raise SchemaValidationError("BoundaryFace.time_dependent must be a bool.")
        raw_source = value.get("source", "user_supplied")
        if not isinstance(raw_source, str):
            raise SchemaValidationError("BoundaryFace.source must be a string.")
        if raw_source not in ALLOWED_BOUNDARY_FACE_SOURCES:
            raise SchemaValidationError(
                "BoundaryFace.source must be one of "
                f"{sorted(ALLOWED_BOUNDARY_FACE_SOURCES)}; got {raw_source!r}."
            )
        return cls(value=normalized_value, time_dependent=bool(raw_time_dependent), source=raw_source)


@dataclass(frozen=True, slots=True)
class BoundaryConditionSpec:
    """Structured representation of `metadata['boundary_conditions']['x']`.

    For `type == 'periodic'` and `type == 'open_unknown'`, both `left` and
    `right` must be `None`. For `type in {'dirichlet', 'neumann'}`, each face
    may be `None` (one-sided constraint) or a `BoundaryFace`.

    `specified` records whether the boundary is fully described. The library
    never infers boundary values: a `BoundaryFace` whose `value` is `None` or
    whose `source` is `"inferred_unspecified"` keeps the overall spec
    unspecified.
    """

    type: str
    left: BoundaryFace | None
    right: BoundaryFace | None
    specified: bool
    notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": str(self.type),
            "left": None if self.left is None else self.left.to_dict(),
            "right": None if self.right is None else self.right.to_dict(),
            "specified": bool(self.specified),
            "notes": None if self.notes is None else str(self.notes),
        }

    @classmethod
    def from_dict(cls, value: object) -> BoundaryConditionSpec:
        if not isinstance(value, Mapping):
            raise SchemaValidationError("BoundaryConditionSpec must be a mapping.")
        raw_type = value.get("type")
        if not isinstance(raw_type, str) or raw_type not in ALLOWED_X_BOUNDARY_TYPES:
            raise ScopeValidationError(
                "BoundaryConditionSpec.type must be one of "
                f"{sorted(ALLOWED_X_BOUNDARY_TYPES)}; got {raw_type!r}."
            )
        bc_type = raw_type

        raw_left = value.get("left")
        raw_right = value.get("right")
        left = None if raw_left is None else BoundaryFace.from_dict(raw_left)
        right = None if raw_right is None else BoundaryFace.from_dict(raw_right)

        if bc_type == "periodic" and (left is not None or right is not None):
            raise SchemaValidationError(
                "Periodic boundary spec must have left=None and right=None."
            )
        if bc_type == "open_unknown" and (left is not None or right is not None):
            raise SchemaValidationError(
                "open_unknown boundary spec must have left=None and right=None."
            )

        if "specified" in value:
            raw_specified = value["specified"]
            if not isinstance(raw_specified, bool):
                raise SchemaValidationError("BoundaryConditionSpec.specified must be a bool.")
            specified = bool(raw_specified)
        else:
            specified = _infer_specified(bc_type, left, right)

        raw_notes = value.get("notes")
        if raw_notes is not None and not isinstance(raw_notes, str):
            raise SchemaValidationError("BoundaryConditionSpec.notes must be a string or None.")
        notes = None if raw_notes is None else str(raw_notes)

        return cls(type=bc_type, left=left, right=right, specified=specified, notes=notes)


def normalize_x_boundary_condition(value: object) -> dict[str, Any]:
    """Normalize a `metadata['boundary_conditions']['x']` value to the canonical structured form.

    Accepts:
    - legacy 0.1 string: `"periodic"`, `"dirichlet"`, `"neumann"`, `"open"`, `"open_unknown"`
    - structured dict matching `BoundaryConditionSpec.from_dict`

    Returns the canonical structured dict (`BoundaryConditionSpec.to_dict()`).

    Raises:
    - `ScopeValidationError` for unsupported strings or unsupported `type` keys.
    - `SchemaValidationError` for malformed dicts or non-string non-mapping values.
    """
    if isinstance(value, str):
        canonical_type = _LEGACY_X_BOUNDARY_STRING_ALIASES.get(value)
        if canonical_type is None:
            raise ScopeValidationError(
                f"Unsupported x boundary string {value!r}. "
                "Supported legacy strings: "
                f"{sorted(_LEGACY_X_BOUNDARY_STRING_ALIASES.keys())}; "
                f"supported canonical types: {sorted(ALLOWED_X_BOUNDARY_TYPES)}."
            )
        if canonical_type == "periodic":
            spec = BoundaryConditionSpec(
                type="periodic", left=None, right=None, specified=True, notes=None
            )
        elif canonical_type == "open_unknown":
            spec = BoundaryConditionSpec(
                type="open_unknown",
                left=None,
                right=None,
                specified=False,
                notes="normalized from legacy 0.1 string",
            )
        else:
            # dirichlet, neumann: library does not invent values
            unspecified_face = BoundaryFace(
                value=None, time_dependent=False, source="inferred_unspecified"
            )
            spec = BoundaryConditionSpec(
                type=canonical_type,
                left=unspecified_face,
                right=unspecified_face,
                specified=False,
                notes="normalized from legacy 0.1 string",
            )
        return spec.to_dict()

    if isinstance(value, Mapping):
        return BoundaryConditionSpec.from_dict(value).to_dict()

    raise SchemaValidationError(
        "boundary_conditions['x'] must be a string or a mapping; got "
        f"{type(value).__name__}."
    )


def get_x_boundary_type(metadata_or_field: object) -> str:
    """Return the canonical x-boundary type from a `FieldBatch` or metadata dict.

    Accepts both the legacy 0.1 string representation and the 0.2 structured form.
    Returns one of: `'periodic'`, `'dirichlet'`, `'neumann'`, `'open_unknown'`.

    Raises:
    - `ScopeValidationError` if the value is a recognized format but the type is unsupported.
    - `SchemaValidationError` if the input shape is malformed.
    """
    metadata = _resolve_metadata(metadata_or_field)
    bcs = metadata.get("boundary_conditions")
    if not isinstance(bcs, Mapping):
        raise SchemaValidationError("metadata['boundary_conditions'] must be a mapping.")
    x_bc = bcs.get("x")
    if isinstance(x_bc, str):
        canonical = _LEGACY_X_BOUNDARY_STRING_ALIASES.get(x_bc)
        if canonical is None:
            raise ScopeValidationError(
                f"Unsupported x boundary string {x_bc!r}. "
                f"Supported canonical types: {sorted(ALLOWED_X_BOUNDARY_TYPES)}."
            )
        return canonical
    if isinstance(x_bc, Mapping):
        raw_type = x_bc.get("type")
        if raw_type not in ALLOWED_X_BOUNDARY_TYPES:
            raise ScopeValidationError(
                "BoundaryConditionSpec.type must be one of "
                f"{sorted(ALLOWED_X_BOUNDARY_TYPES)}; got {raw_type!r}."
            )
        return str(raw_type)
    raise SchemaValidationError(
        "boundary_conditions['x'] must be a string or mapping; got "
        f"{type(x_bc).__name__}."
    )


def is_x_periodic(metadata_or_field: object) -> bool:
    """Return True iff the x boundary condition is periodic.

    Errors (unsupported string, malformed dict, missing metadata) propagate to the caller.
    """
    return get_x_boundary_type(metadata_or_field) == "periodic"


# --- private helpers --------------------------------------------------------


def _validate_optional_finite_scalar(value: object, *, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SchemaValidationError(f"{name} must be a finite scalar or None.")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise SchemaValidationError(f"{name} must be finite.")
    return normalized


def _infer_specified(
    bc_type: str, left: BoundaryFace | None, right: BoundaryFace | None
) -> bool:
    if bc_type == "periodic":
        return True
    if bc_type == "open_unknown":
        return False
    if bc_type in _BC_TYPES_WITH_FACES:
        faces = [face for face in (left, right) if face is not None]
        if not faces:
            return False
        for face in faces:
            if face.value is None or face.source == "inferred_unspecified":
                return False
        return True
    return False


def _resolve_metadata(metadata_or_field: object) -> Mapping[str, Any]:
    if hasattr(metadata_or_field, "metadata"):
        metadata = metadata_or_field.metadata
        if not isinstance(metadata, Mapping):
            raise SchemaValidationError("FieldBatch.metadata must be a mapping.")
        return metadata
    if isinstance(metadata_or_field, Mapping):
        return metadata_or_field
    raise SchemaValidationError("Expected FieldBatch or metadata mapping.")


__all__ = [
    "ALLOWED_BOUNDARY_FACE_SOURCES",
    "ALLOWED_X_BOUNDARY_TYPES",
    "LEGACY_BOUNDARY_NORMALIZATION_OPERATION",
    "BoundaryConditionSpec",
    "BoundaryFace",
    "get_x_boundary_type",
    "is_x_periodic",
    "normalize_x_boundary_condition",
]
