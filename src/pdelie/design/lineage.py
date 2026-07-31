"""v0.36b: where each design row came from, and two hashes over it.

``DesignRowLineage`` answers, for one row of a design matrix: which trajectory,
which source coordinate, which view, under which action, with which derivative
support, through which mask. Exit gate A-alpha-2 requires every row of the
design matrix to carry one with ``trajectory_id``, ``source_coordinate_id``, and
``mask_id`` non-null -- so those three are required, not optional.

Two hashes, deliberately different
==================================

:func:`compute_semantic_design_hash` hashes *provenance*: which rows, in which
order, from where. :func:`compute_numeric_design_hash` hashes *bytes*.

They disagree usefully. Two runs that select the same rows through different
floating-point paths share a semantic hash and differ numerically. A run that
reorders identical rows differs in both -- **row order carries meaning**, so the
semantic hash is order-sensitive by design rather than by oversight.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from pdelie.artifact.semantic_hash import semantic_hash
from pdelie.errors import ScopeValidationError, ShapeValidationError

__all__ = [
    "DesignRowLineage",
    "compute_numeric_design_hash",
    "compute_semantic_design_hash",
]

#: Fields that may not be ``None``; A-alpha-2 asserts all three per row.
REQUIRED_LINEAGE_FIELDS: tuple[str, ...] = (
    "trajectory_id",
    "source_coordinate_id",
    "mask_id",
)


@dataclass(frozen=True)
class DesignRowLineage:
    """Provenance for one row of a design matrix."""

    trajectory_id: str
    source_coordinate_id: str
    mask_id: str
    view_id: str | None = None
    action_parameter_id: str | None = None
    derivative_support_id: str | None = None
    duplicate_group_id: str | None = None

    def __post_init__(self) -> None:
        for name in REQUIRED_LINEAGE_FIELDS:
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ScopeValidationError(
                    f"{name} must be a non-empty string. Exit gate A-alpha-2 requires "
                    f"trajectory_id, source_coordinate_id, and mask_id on every "
                    f"design row; a null one makes the row untraceable."
                )
        for name in (
            "view_id",
            "action_parameter_id",
            "derivative_support_id",
            "duplicate_group_id",
        ):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ScopeValidationError(f"{name} must be a non-empty string or None.")

    def identity(self) -> str:
        return semantic_hash(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "trajectory_id": self.trajectory_id,
            "source_coordinate_id": self.source_coordinate_id,
            "view_id": self.view_id,
            "action_parameter_id": self.action_parameter_id,
            "derivative_support_id": self.derivative_support_id,
            "mask_id": self.mask_id,
            "duplicate_group_id": self.duplicate_group_id,
        }


def compute_semantic_design_hash(rows: object) -> str:
    """Hash a design's provenance, in row order.

    Order-sensitive on purpose: two designs holding the same rows in a different
    order are different designs, because row order determines which rows a
    budgeted truncation keeps.
    """
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        raise ScopeValidationError("rows must be a sequence of DesignRowLineage.")
    if not rows:
        raise ScopeValidationError(
            "rows must be non-empty; a design with no rows has no provenance to hash."
        )
    for index, row in enumerate(rows):
        if not isinstance(row, DesignRowLineage):
            raise ScopeValidationError(
                f"rows[{index}] is {type(row).__name__}, not DesignRowLineage."
            )
    return semantic_hash({"rows": [row.as_dict() for row in rows]})


def compute_numeric_design_hash(matrix: object) -> str:
    """Hash a design matrix's bytes.

    Byte-level and therefore sensitive to dtype, shape, and column order. This
    is an ``exact_discrete`` identity check, never a numerical comparison: two
    matrices that agree to ``rtol=1e-12`` have different numeric hashes, and
    that is correct. Use the comparators for numerical agreement.
    """
    values = np.asarray(matrix)
    if values.ndim != 2:
        raise ShapeValidationError(
            f"design matrix must be two-dimensional; got shape {values.shape}."
        )
    if values.dtype == object:
        raise ScopeValidationError("design matrix must not have dtype=object.")
    contiguous = np.ascontiguousarray(values)
    digest = hashlib.sha256()
    digest.update(str(contiguous.dtype).encode("utf-8"))
    digest.update(repr(contiguous.shape).encode("utf-8"))
    digest.update(contiguous.tobytes())
    return digest.hexdigest()
