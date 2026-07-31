"""v0.36a-alpha: per-class comparison functions.

One comparator per portability class. Each returns a
:class:`ComparisonResult` carrying a :data:`MIGRATION_LABELS` value, the observed
deviation, and a per-component breakdown -- so a failing stage reports *where* it
failed, not merely that it did.

What a comparator may and may not decide
========================================

A comparator may return only the labels its evidence supports:

* ``exactly_preserved`` -- bytes are equal;
* ``numerically_equivalent_within_tolerance`` -- within the supplied tolerance;
* ``qualitatively_preserved`` -- the named invariant holds;
* ``unexplained_regression`` -- none of the above.

The remaining three labels -- ``intentional_contract_change``,
``platform_specific_difference``, ``blocked_missing_legacy_dependency`` -- are
**policy decisions carrying a human justification** and are assigned by
:mod:`pdelie.audit.pipeline_migration`, never here. A comparator that could
relabel its own failure as intentional would be able to explain away every
regression it found.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from pdelie.errors import ScopeValidationError, ShapeValidationError

__all__ = [
    "COMPARATOR_ASSIGNABLE_LABELS",
    "MIGRATION_LABELS",
    "QUALITATIVE_INVARIANTS",
    "ComparisonResult",
    "compare_exact",
    "compare_numeric",
    "compare_qualitative",
    "principal_angles",
]

MigrationLabel = Literal[
    "exactly_preserved",
    "numerically_equivalent_within_tolerance",
    "qualitatively_preserved",
    "intentional_contract_change",
    "platform_specific_difference",
    "unexplained_regression",
    "blocked_missing_legacy_dependency",
]

#: The frozen seven-value vocabulary.
MIGRATION_LABELS: tuple[str, ...] = (
    "exactly_preserved",
    "numerically_equivalent_within_tolerance",
    "qualitatively_preserved",
    "intentional_contract_change",
    "platform_specific_difference",
    "unexplained_regression",
    "blocked_missing_legacy_dependency",
)

#: The subset a comparator may assign from array evidence alone.
COMPARATOR_ASSIGNABLE_LABELS: tuple[str, ...] = (
    "exactly_preserved",
    "numerically_equivalent_within_tolerance",
    "qualitatively_preserved",
    "unexplained_regression",
)

#: Invariants :func:`compare_qualitative` knows how to check.
QUALITATIVE_INVARIANTS: tuple[str, ...] = (
    "sign",
    "rank",
    "monotonicity",
    "support_containment",
    "ordering",
)


@dataclass(frozen=True)
class ComparisonResult:
    """The outcome of comparing one stage's legacy and modern arrays."""

    label: str
    comparison_class: str
    max_absolute_deviation: float | None
    max_relative_deviation: float | None
    drift_breakdown: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "comparison_class": self.comparison_class,
            "max_absolute_deviation": self.max_absolute_deviation,
            "max_relative_deviation": self.max_relative_deviation,
            "drift_breakdown": dict(self.drift_breakdown),
            "warnings": list(self.warnings),
        }


def _validated_pair(a: object, b: object) -> tuple[np.ndarray, np.ndarray]:
    left = np.asarray(a)
    right = np.asarray(b)
    if left.shape != right.shape:
        raise ShapeValidationError(
            f"cannot compare arrays of different shape: {left.shape} vs {right.shape}. "
            f"A shape change is a contract change and must be labelled by policy."
        )
    return left, right


def compare_exact(a: object, b: object) -> ComparisonResult:
    """Byte-equality check for the ``exact_discrete`` class.

    Returns ``exactly_preserved`` or ``unexplained_regression``. There is no
    tolerance here by construction: this class is for artifacts with no
    floating-point path between input and output, where any difference is a real
    difference.
    """
    left, right = _validated_pair(a, b)
    if np.array_equal(left, right):
        return ComparisonResult(
            label="exactly_preserved",
            comparison_class="exact_discrete",
            max_absolute_deviation=0.0,
            max_relative_deviation=0.0,
            drift_breakdown={"element_count": int(left.size), "mismatched_elements": 0},
        )

    mismatched = int(np.count_nonzero(left != right))
    breakdown: dict[str, Any] = {
        "element_count": int(left.size),
        "mismatched_elements": mismatched,
        "mismatch_fraction": float(mismatched / left.size),
    }
    absolute: float | None = None
    if np.issubdtype(left.dtype, np.number) and np.issubdtype(right.dtype, np.number):
        absolute = float(np.abs(left.astype(float) - right.astype(float)).max())
        breakdown["first_mismatch_index"] = [
            int(value) for value in np.argwhere(left != right)[0]
        ]
    return ComparisonResult(
        label="unexplained_regression",
        comparison_class="exact_discrete",
        max_absolute_deviation=absolute,
        max_relative_deviation=None,
        drift_breakdown=breakdown,
        warnings=("exact_discrete_stage_is_not_byte_equal",),
    )


def compare_numeric(a: object, b: object, *, rtol: float, atol: float) -> ComparisonResult:
    """Tolerance comparison for the ``tolerance_numeric`` class.

    Both tolerances are required keywords. ``rtol`` alone compares nothing near
    zero, and a default would be a threshold frozen without measurement --
    exactly what the freeze process forbids.
    """
    if not isinstance(rtol, (int, float)) or isinstance(rtol, bool) or rtol < 0:
        raise ScopeValidationError("rtol must be a non-negative real number.")
    if not isinstance(atol, (int, float)) or isinstance(atol, bool) or atol < 0:
        raise ScopeValidationError("atol must be a non-negative real number.")

    left, right = _validated_pair(a, b)
    if not (np.issubdtype(left.dtype, np.number) and np.issubdtype(right.dtype, np.number)):
        raise ScopeValidationError(
            "compare_numeric requires numeric dtypes; use compare_exact for "
            "boolean or integer-identity stages."
        )

    left_f = left.astype(float)
    right_f = right.astype(float)
    warnings_out: list[str] = []

    finite = np.isfinite(left_f) & np.isfinite(right_f)
    if not finite.all():
        warnings_out.append("non_finite_values_present_and_excluded_from_deviation")
    if not finite.any():
        return ComparisonResult(
            label="unexplained_regression",
            comparison_class="tolerance_numeric",
            max_absolute_deviation=None,
            max_relative_deviation=None,
            drift_breakdown={"element_count": int(left.size), "finite_elements": 0},
            warnings=(*warnings_out, "no_finite_elements_to_compare"),
        )

    difference = np.abs(left_f - right_f)
    max_absolute = float(difference[finite].max())
    scale = float(np.abs(left_f[finite]).max())
    max_relative = float(max_absolute / scale) if scale > 0.0 else 0.0

    close = np.allclose(left_f[finite], right_f[finite], rtol=rtol, atol=atol)
    breakdown: dict[str, Any] = {
        "element_count": int(left.size),
        "finite_elements": int(finite.sum()),
        "rtol": float(rtol),
        "atol": float(atol),
        "reference_scale": scale,
        "elements_outside_tolerance": int(
            np.count_nonzero(
                difference[finite] > (atol + rtol * np.abs(right_f[finite]))
            )
        ),
    }
    if close:
        # A pass that only just passes is worth surfacing: it means the
        # tolerance is doing the work, not the agreement.
        if max_relative > 0.1 * max(rtol, 1e-300):
            warnings_out.append("deviation_within_one_order_of_the_tolerance")
        return ComparisonResult(
            label="numerically_equivalent_within_tolerance",
            comparison_class="tolerance_numeric",
            max_absolute_deviation=max_absolute,
            max_relative_deviation=max_relative,
            drift_breakdown=breakdown,
            warnings=tuple(warnings_out),
        )

    return ComparisonResult(
        label="unexplained_regression",
        comparison_class="tolerance_numeric",
        max_absolute_deviation=max_absolute,
        max_relative_deviation=max_relative,
        drift_breakdown=breakdown,
        warnings=(*warnings_out, "deviation_exceeds_supplied_tolerance"),
    )


def principal_angles(a: object, b: object) -> np.ndarray:
    """Principal angles (radians) between the column spaces of two matrices.

    The correct comparison for subspaces. Raw ``U``/``V`` factors from an SVD are
    not comparable across implementations -- column signs and the basis within a
    degenerate eigenspace are both arbitrary -- but the subspace they span is
    well defined.
    """
    left = np.asarray(a, dtype=float)
    right = np.asarray(b, dtype=float)
    if left.ndim != 2 or right.ndim != 2:
        raise ShapeValidationError("principal_angles requires two-dimensional inputs.")
    if left.shape[0] != right.shape[0]:
        raise ShapeValidationError(
            f"subspaces must live in the same ambient dimension; got "
            f"{left.shape[0]} and {right.shape[0]}."
        )
    q_left, _ = np.linalg.qr(left)
    q_right, _ = np.linalg.qr(right)
    singular = np.linalg.svd(q_left.T @ q_right, compute_uv=False)
    return np.arccos(np.clip(singular, -1.0, 1.0))


def _invariant_sign(left: np.ndarray, right: np.ndarray) -> tuple[bool, dict[str, Any]]:
    same = np.sign(left) == np.sign(right)
    return bool(same.all()), {"sign_mismatches": int(np.count_nonzero(~same))}


def _invariant_rank(left: np.ndarray, right: np.ndarray) -> tuple[bool, dict[str, Any]]:
    if left.ndim != 2:
        raise ShapeValidationError("the 'rank' invariant requires two-dimensional arrays.")
    left_rank = int(np.linalg.matrix_rank(left))
    right_rank = int(np.linalg.matrix_rank(right))
    return left_rank == right_rank, {"legacy_rank": left_rank, "modern_rank": right_rank}


def _invariant_monotonicity(
    left: np.ndarray, right: np.ndarray
) -> tuple[bool, dict[str, Any]]:
    left_direction = np.sign(np.diff(left.reshape(-1)))
    right_direction = np.sign(np.diff(right.reshape(-1)))
    same = left_direction == right_direction
    return bool(same.all()), {"direction_mismatches": int(np.count_nonzero(~same))}


def _invariant_support_containment(
    left: np.ndarray, right: np.ndarray
) -> tuple[bool, dict[str, Any]]:
    legacy = set(np.flatnonzero(np.asarray(left).reshape(-1)).tolist())
    modern = set(np.flatnonzero(np.asarray(right).reshape(-1)).tolist())
    return legacy <= modern, {
        "legacy_support_size": len(legacy),
        "modern_support_size": len(modern),
        "missing_from_modern": sorted(legacy - modern),
        "added_by_modern": sorted(modern - legacy),
    }


def _invariant_ordering(left: np.ndarray, right: np.ndarray) -> tuple[bool, dict[str, Any]]:
    left_order = np.argsort(left.reshape(-1), kind="stable")
    right_order = np.argsort(right.reshape(-1), kind="stable")
    same = np.array_equal(left_order, right_order)
    return bool(same), {"ordering_identical": bool(same)}


_INVARIANT_CHECKS = {
    "sign": _invariant_sign,
    "rank": _invariant_rank,
    "monotonicity": _invariant_monotonicity,
    "support_containment": _invariant_support_containment,
    "ordering": _invariant_ordering,
}


def compare_qualitative(a: object, b: object, *, invariant: str) -> ComparisonResult:
    """Invariant comparison for the ``qualitative_invariant`` class.

    Used where the raw value is not unique -- a subspace basis, a permutation
    among tied elements, a sign convention -- but a well-defined property is.
    """
    if invariant not in QUALITATIVE_INVARIANTS:
        raise ScopeValidationError(
            f"invariant {invariant!r} is not one of {list(QUALITATIVE_INVARIANTS)}."
        )
    left, right = _validated_pair(a, b)
    holds, breakdown = _INVARIANT_CHECKS[invariant](left, right)
    breakdown["invariant"] = invariant

    return ComparisonResult(
        label="qualitatively_preserved" if holds else "unexplained_regression",
        comparison_class="qualitative_invariant",
        max_absolute_deviation=None,
        max_relative_deviation=None,
        drift_breakdown=breakdown,
        warnings=() if holds else (f"qualitative_invariant_{invariant}_not_preserved",),
    )


def compare_subspaces(
    a: object, b: object, *, max_principal_angle_rad: float
) -> ComparisonResult:
    """Subspace comparison via principal angles.

    Provided because "compare the SVD" is the single most common way to write an
    assertion that cannot hold across implementations. Compare what is invariant.
    """
    if (
        not isinstance(max_principal_angle_rad, (int, float))
        or isinstance(max_principal_angle_rad, bool)
        or max_principal_angle_rad < 0
    ):
        raise ScopeValidationError("max_principal_angle_rad must be a non-negative real.")
    angles = principal_angles(a, b)
    largest = float(angles.max()) if angles.size else 0.0
    holds = largest <= max_principal_angle_rad
    return ComparisonResult(
        label="qualitatively_preserved" if holds else "unexplained_regression",
        comparison_class="qualitative_invariant",
        max_absolute_deviation=largest,
        max_relative_deviation=None,
        drift_breakdown={
            "invariant": "subspace_principal_angles",
            "principal_angles_rad": [float(value) for value in angles],
            "max_principal_angle_rad": largest,
            "threshold_rad": float(max_principal_angle_rad),
        },
        warnings=() if holds else ("subspace_principal_angle_exceeds_threshold",),
    )


def compare_selected_rows_by_objective(
    legacy_objective: float,
    modern_objective: float,
    *,
    rtol: float,
) -> ComparisonResult:
    """Compare a row selection by the value it achieves, not by which rows it picked.

    Two pivoted-QR implementations can select different rows and be equally
    correct when column norms tie -- measured in v0.35c, where SciPy pivots the
    same orthonormal matrix differently under different LAPACK builds. What must
    agree is the objective the selection achieves.
    """
    for name, value in (("legacy_objective", legacy_objective), ("modern_objective", modern_objective)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ScopeValidationError(f"{name} must be a real number.")
    left = float(legacy_objective)
    right = float(modern_objective)
    scale = max(abs(left), 1e-300)
    relative = abs(left - right) / scale
    holds = relative <= rtol
    return ComparisonResult(
        label="qualitatively_preserved" if holds else "unexplained_regression",
        comparison_class="qualitative_invariant",
        max_absolute_deviation=abs(left - right),
        max_relative_deviation=relative,
        drift_breakdown={
            "invariant": "selected_row_objective_value",
            "legacy_objective": left,
            "modern_objective": right,
            "rtol": float(rtol),
        },
        warnings=() if holds else ("selected_row_objective_differs",),
    )


def summarize_labels(results: Sequence[ComparisonResult]) -> dict[str, int]:
    """Count each label across a set of stage comparisons."""
    counts = dict.fromkeys(MIGRATION_LABELS, 0)
    for result in results:
        counts[result.label] += 1
    return counts
