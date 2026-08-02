"""v0.38b: finite-difference weights on a non-uniform 1-D grid.

Fornberg's recursion (Fornberg 1988) computes weights for a derivative of any
order at any evaluation point over an arbitrary node set. v0.38a decided which
rows are admissible; this module computes the derivatives, and produces four of
the five exclusion reasons v0.38a declared.

Accuracy is derived, not declared
=================================

``formal_accuracy = stencil_size - derivative_order``. It comes from the stencil
**actually used**, and there is no parameter by which a caller may assert it --
C-2 of the v0.38 binding constraints, and the same rule that
``full_field_derivatives_available`` follows.

The derivation, and its oracle
==============================

Weights over ``n`` nodes are exact for polynomials of degree ``<= n-1``.
Approximating a ``d``-th derivative annihilates the first ``d`` Taylor terms and
reproduces the next ``n-d`` exactly, leaving a leading error of order
``h^(n-d)``.

That is one derivation, written once. Its independent second derivation is a
manufactured solution -- polynomial exactness checked against a closed-form
answer on a deliberately non-uniform node set -- in
``docs/design/FORNBERG_ACCURACY_ORACLE.md`` and
``tests/test_v0_38b_fornberg_oracle.py``.

Degenerate grids are refused, never repaired
============================================

Duplicate coordinates are refused rather than deduplicated, and unsorted ones
refused rather than sorted. A silent sort changes which row is which and a
silent dedup changes the count; both are unrecoverable once downstream has
consumed the result, whereas a refusal is recoverable by the caller who knows
what they meant.

Thresholds are measured, and they are diagnostics
=================================================

The G-5 ratio and the stencil cap were **piloted, not guessed** (C-2), and are
frozen at the v0.38b confirmatory freeze with the measurements behind them in
``docs/design/v0_38b_pilot_report.md``.

The pilot's substantive finding: weight magnitude grows ~400x between a uniform
grid and a spacing ratio of ~340, and the **achieved error floor moves by about
one order of magnitude**. The amplified weights multiply function values that are
correspondingly closer together, and the errors largely cancel.

So neither threshold is a correctness boundary. G-5 reports that the floor has
measurably degraded; the cap guards against unbounded stencil growth that buys no
accuracy and costs admissible rows. Neither refuses a computation.

Rules FN-1 .. FN-17 are frozen in ``docs/design/v0_38b_hypothesis_freeze.md``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from pdelie.errors import ScopeValidationError

#: Spacing ratio above which a grid is reported strongly non-uniform.
#:
#: Frozen at the v0.38b confirmatory freeze. It is the lowest ratio at which any
#: measured derivative order showed >=10x floor degradation from uniform
#: (d=1: 2.79e-15 -> 2.53e-14), across 3 functions x 2 grid sizes x 2 stretching
#: families.
#:
#: A REPORTING threshold, not a refusal boundary: the pilot found no ratio at
#: which differentiation became unusable for d <= 3, up to 1.6e8.
G5_SPACING_RATIO_THRESHOLD: float = 10.0

#: Largest stencil this layer will form.
#:
#: Truncation error reaches the roundoff floor at 11 nodes; the cap sits one
#: step past that. Past saturation, extra nodes buy no accuracy and cost
#: admissible rows -- a stencil of n excludes n-1 rows at the boundaries.
#:
#: Justified by diminishing returns plus row cost, NOT by instability: no
#: instability was observed at any stencil size tested. That evidence is thinner
#: than G-5's and the pilot report says so.
MAX_STENCIL_SIZE: int = 13

__all__ = [
    "G5_SPACING_RATIO_THRESHOLD",
    "MAX_STENCIL_SIZE",
    "FornbergWeights",
    "GridRegularity",
    "classify_coordinate_defect",
    "classify_row_exclusions",
    "describe_grid_regularity",
    "fornberg_weights",
    "validate_coordinates",
]


def validate_coordinates(coordinates: np.ndarray, *, where: str = "coordinates") -> np.ndarray:
    """FN-6 … FN-9: refuse a degenerate grid rather than repair it."""
    values = np.asarray(coordinates, dtype=float).ravel()
    if values.size < 2:
        raise ScopeValidationError(
            f"{where} has {values.size} point(s). A single point has no spacing, "
            f"so there is no ratio to report and no stencil to form."
        )
    if not np.all(np.isfinite(values)):
        raise ScopeValidationError(f"{where} contains a non-finite value.")

    differences = np.diff(values)
    if np.any(differences == 0.0):
        repeated = sorted({float(v) for v in values[:-1][differences == 0.0]})
        raise ScopeValidationError(
            f"{where} repeats {repeated[:5]}. Duplicates are refused, not "
            f"deduplicated: a silent dedup changes the row count, and nothing "
            f"downstream can tell that it happened."
        )
    if np.any(differences < 0.0):
        raise ScopeValidationError(
            f"{where} is not strictly increasing. It is refused rather than "
            f"sorted: a silent sort changes which row is which, and the mask and "
            f"the data would then disagree with nothing able to notice."
        )
    return values


@dataclass(frozen=True)
class GridRegularity:
    """How non-uniform a grid is. Scale-free, and carries no verdict yet."""

    spacing_ratio: float
    min_spacing: float
    max_spacing: float
    node_count: int

    @property
    def is_uniform(self) -> bool:
        """Within the floating-point noise floor of a genuinely uniform grid.

        **FN-12 as originally frozen demanded exactly 1.0, and pilot run 1
        blocked on it (criterion B-4).** A ``linspace`` does not have bitwise
        constant spacings: the deviation was measured at ``0.637 * n * eps``,
        stable across three different domain spans, so it is accumulated
        arithmetic and not a property of any one grid.

        The freeze anticipated this and required an amendment carrying the
        measured deviation rather than a silent loosening. The bound is
        ``n * eps`` -- linear in the node count, which is what floating-point
        accumulation predicts, and confirmed by measurement with 1.5x margin
        over the worst case observed.

        It is a *derived* bound, not a fitted one: the linear form comes from
        the arithmetic, and the measurement only confirms the constant is below
        one.
        """
        return self.spacing_ratio - 1.0 <= self.node_count * float(np.finfo(float).eps)

    @property
    def g5_verdict(self) -> str:
        """``strongly_non_uniform`` / ``within_g5``.

        A report, not a refusal. The pilot measured no spacing ratio at which
        differentiation became unusable for derivative orders 1-3; what it did
        measure is that the achieved error floor degrades by roughly an order of
        magnitude, and this says when that has happened.
        """
        return (
            "strongly_non_uniform"
            if self.spacing_ratio > G5_SPACING_RATIO_THRESHOLD
            else "within_g5"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "spacing_ratio": self.spacing_ratio,
            "min_spacing": self.min_spacing,
            "max_spacing": self.max_spacing,
            "node_count": self.node_count,
            "is_uniform": self.is_uniform,
            "uniformity_tolerance": self.node_count * float(np.finfo(float).eps),
            "g5_threshold": G5_SPACING_RATIO_THRESHOLD,
            "g5_verdict": self.g5_verdict,
        }


def describe_grid_regularity(coordinates: np.ndarray) -> GridRegularity:
    """FN-10: report the spacing ratio on every grid, uniform ones included.

    The ratio is ``max/min``, so it is dimensionless -- the same grid in metres
    and in kilometres reports the same number. An absolute spacing test would
    not.
    """
    values = validate_coordinates(coordinates)
    spacings = np.diff(values)
    minimum = float(np.min(spacings))
    maximum = float(np.max(spacings))
    # Computed from the extremes rather than by comparing every pair, so a grid
    # whose spacings differ only in the last ulp still reports exactly 1.0 when
    # min and max are the same float.
    return GridRegularity(
        spacing_ratio=maximum / minimum,
        min_spacing=minimum,
        max_spacing=maximum,
        node_count=int(values.size),
    )


@dataclass(frozen=True)
class FornbergWeights:
    """Weights for one derivative at one point, and what they are good for."""

    weights: np.ndarray
    derivative_order: int
    stencil_size: int
    evaluation_point: float
    evaluated_at_node: bool

    @property
    def formal_accuracy(self) -> int:
        """FN-2: derived from the stencil actually used.

        There is no constructor parameter for this, deliberately. A
        caller-supplied accuracy is a claim about someone else's arithmetic.
        """
        return self.stencil_size - self.derivative_order

    def as_dict(self) -> dict[str, Any]:
        return {
            "derivative_order": self.derivative_order,
            "stencil_size": self.stencil_size,
            "formal_accuracy": self.formal_accuracy,
            "evaluation_point": self.evaluation_point,
            "evaluated_at_node": self.evaluated_at_node,
            "weight_magnitude_max": float(np.max(np.abs(self.weights))),
        }


def fornberg_weights(
    nodes: np.ndarray, evaluation_point: float, derivative_order: int
) -> FornbergWeights:
    """Fornberg's recursion for finite-difference weights on arbitrary nodes.

    FN-3: a stencil smaller than ``derivative_order + 1`` is refused. Fewer
    nodes than the derivative order cannot determine it, and returning weights
    anyway would produce a number with no approximation property at all --
    which is worse than an error, because it looks like an answer.

    FN-5: ``evaluation_point`` need not be a node.
    """
    if not isinstance(derivative_order, int) or isinstance(derivative_order, bool):
        raise ScopeValidationError("derivative_order must be an int.")
    if derivative_order < 0:
        raise ScopeValidationError("derivative_order must be non-negative.")
    if not isinstance(evaluation_point, (int, float)) or isinstance(evaluation_point, bool):
        raise ScopeValidationError("evaluation_point must be a real number.")
    point = float(evaluation_point)
    if not np.isfinite(point):
        raise ScopeValidationError("evaluation_point must be finite.")

    values = validate_coordinates(nodes, where="nodes")
    size = int(values.size)
    if size > MAX_STENCIL_SIZE:
        raise ScopeValidationError(
            f"a stencil of {size} nodes exceeds the cap of {MAX_STENCIL_SIZE}. "
            f"Truncation error reaches the roundoff floor at 11 nodes, so beyond "
            f"the cap extra nodes buy no accuracy and cost admissible rows -- a "
            f"stencil of n excludes n-1 rows at the boundaries. See "
            f"docs/design/v0_38b_pilot_report.md."
        )
    if size < derivative_order + 1:
        raise ScopeValidationError(
            f"a stencil of {size} node(s) cannot determine derivative order "
            f"{derivative_order}: at least {derivative_order + 1} are needed. "
            f"Returning weights anyway would produce a number with no "
            f"approximation property, which is worse than an error because it "
            f"looks like an answer."
        )

    # Fornberg (1988), "Generation of Finite Difference Formulas on Arbitrarily
    # Spaced Grids". delta[m, n, v] is the weight of node v in the m-th
    # derivative formula using nodes 0..n.
    delta = np.zeros((derivative_order + 1, size, size), dtype=float)
    delta[0, 0, 0] = 1.0
    c1 = 1.0
    for n in range(1, size):
        c2 = 1.0
        for v in range(n):
            c3 = values[n] - values[v]
            c2 *= c3
            for m in range(min(n, derivative_order) + 1):
                delta[m, n, v] = (
                    (values[n] - point) * delta[m, n - 1, v]
                    - (m * delta[m - 1, n - 1, v] if m > 0 else 0.0)
                ) / c3
        for m in range(min(n, derivative_order) + 1):
            delta[m, n, n] = (
                c1
                / c2
                * (
                    (m * delta[m - 1, n - 1, n - 1] if m > 0 else 0.0)
                    - (values[n - 1] - point) * delta[m, n - 1, n - 1]
                )
            )
        c1 = c2

    return FornbergWeights(
        weights=delta[derivative_order, size - 1, :].copy(),
        derivative_order=derivative_order,
        stencil_size=size,
        evaluation_point=point,
        evaluated_at_node=bool(np.any(values == point)),
    )


# ---------------------------------------------------------------------------
# Row-mask producers (FN-13 .. FN-15)
# ---------------------------------------------------------------------------
#
# v0.38a declared five exclusion reasons and produced none: build_row_mask took
# its exclusions from the caller, so the vocabulary shipped without the
# conditions that trigger it. Its pilot report recorded which sub-phase owed
# each producer. This closes four of them.


def classify_row_exclusions(
    coordinates: np.ndarray,
    *,
    stencil_size: int,
    derivative_order: int,
    computed_derivatives: Sequence[str] = (),
    required_derivatives: Sequence[str] = (),
) -> dict[int, str]:
    """Which rows cannot carry a derivative, and why.

    Returns ``{row_index: reason}`` in the form
    :func:`~pdelie.design.row_mask.build_row_mask` consumes. Only rows that are
    genuinely inadmissible appear; an admissible row is absent rather than
    present with a null reason.

    The coordinate checks run first and raise, because a degenerate grid is not
    a per-row condition -- duplicates and unsorted input are refused for the
    whole grid rather than excluding the rows that happen to touch them.
    """
    values = validate_coordinates(coordinates)
    if stencil_size > MAX_STENCIL_SIZE:
        raise ScopeValidationError(
            f"stencil_size {stencil_size} exceeds the cap of {MAX_STENCIL_SIZE}."
        )
    if stencil_size < derivative_order + 1:
        raise ScopeValidationError(
            f"a stencil of {stencil_size} cannot determine derivative order "
            f"{derivative_order}."
        )

    exclusions: dict[int, str] = {}

    # FN-15: a derivative was asked for and none can be formed anywhere.
    missing = set(required_derivatives) - set(computed_derivatives)
    if missing:
        for index in range(int(values.size)):
            exclusions[index] = "derivative_unavailable"
        return exclusions

    # FN-13: the stencil must fit within the available coordinates. A centred
    # stencil of `stencil_size` needs half of it on each side, so the first and
    # last rows cannot carry one. They are EXCLUDED rather than silently given a
    # one-sided stencil: a one-sided formula has different accuracy, and
    # substituting it would make formal_accuracy wrong for those rows while
    # nothing recorded that it had happened.
    half = stencil_size // 2
    for index in range(int(values.size)):
        if index < half or index >= int(values.size) - half:
            exclusions[index] = "stencil_does_not_fit"

    return exclusions


def classify_coordinate_defect(coordinates: np.ndarray) -> str | None:
    """FN-14: name the coordinate defect, or ``None`` if there is none.

    A companion to :func:`validate_coordinates` for callers that want the
    reason as a mask vocabulary term rather than an exception -- for example to
    record it in a report before deciding whether to proceed.

    It does not repair anything. It names what
    :func:`validate_coordinates` would refuse.
    """
    values = np.asarray(coordinates, dtype=float).ravel()
    if values.size < 2 or not np.all(np.isfinite(values)):
        return "coordinate_missing"
    differences = np.diff(values)
    if np.any(differences == 0.0):
        return "duplicate_coordinate"
    if np.any(differences < 0.0):
        # Unsorted input has no reason of its own in the v0.38a vocabulary, and
        # a new one is not invented here: growth is a deliberate act at a freeze,
        # not a side effect of needing a label. It is refused by
        # validate_coordinates, which is the correct handling.
        return None
    return None
