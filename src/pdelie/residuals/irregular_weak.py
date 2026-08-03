"""v0.38c: weak-form quadrature on irregularly spaced 1-D samples.

A weak row is a window, not a sample
====================================

This is the distinction the sub-phase turns on. v0.38a identifies design rows by
``DesignRowLineage`` over **samples**. A weak-form row is an integral over a
support region covering many samples -- a different object, and a mask built for
one does not describe the other.

:class:`WeakWindow` therefore carries its own identity, namespaced so it cannot
be confused with a sample-row identity. Two things sharing one name is how the
rest of this arc's defects began.

Quadrature is narrowed, and user weights are validated
======================================================

Exactly two rules (C-3): ``nonuniform_trapezoidal``, derived from the
coordinates, and ``user_supplied_validated_weights``, which are **validated, not
trusted**. A rule that cannot integrate the constant ``1`` over its own interval
is not a quadrature rule, and that is the check.

Failing weights are **refused**. There is no renormalisation: renormalising would
make the failure invisible while silently changing the caller's declared rule
into a different one.

The validation tolerance is derived, not guessed
================================================

Summing ``n`` weights accumulates ``O(n * eps)`` relative error, so the bound is
``n * eps * interval_length``. Same derivation pattern as v0.38b's FN-12
amendment: the *form* comes from the arithmetic, and measurement only confirms
the constant is bounded.

Rules WK-1 .. WK-12 are frozen in ``docs/design/v0_38c_hypothesis_freeze.md``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from pdelie.artifact.semantic_hash import semantic_hash
from pdelie.errors import ScopeValidationError

__all__ = [
    "QUADRATURE_RULES",
    "WEAK_ROW_IDENTITY_PREFIX",
    "WeakWindow",
    "nonuniform_trapezoidal_weights",
    "validate_quadrature_weights",
    "weak_window_overlap_fraction",
]

#: WK-5. Exactly two. A third name is refused rather than mapped onto whichever
#: of these looks closest -- approximating a rule the caller did not ask for is
#: how a payload comes to describe a computation nobody performed.
QUADRATURE_RULES: tuple[str, ...] = (
    "nonuniform_trapezoidal",
    "user_supplied_validated_weights",
)

#: WK-2. Namespaced so a weak-row identity can never equal a sample-row
#: identity. ``DesignRowLineage.identity()`` is a bare SHA-256 hex digest; this
#: prefix makes the two sets provably disjoint rather than merely unlikely to
#: collide.
WEAK_ROW_IDENTITY_PREFIX = "weakwin:"


def nonuniform_trapezoidal_weights(coordinates: np.ndarray) -> np.ndarray:
    """WK-6: trapezoidal weights derived from the coordinates.

    On a non-uniform grid the weight at an interior node is half the sum of its
    two adjacent spacings; the endpoints get half of their single spacing. This
    reduces to the familiar uniform rule when the spacings are equal, and is
    exact for linear integrands on any spacing.

    Coordinates are validated by the v0.38b validator, so duplicates and
    unsorted input are refused here for the same reasons they are refused there
    -- and by the same code, rather than by a second copy of the rule.
    """
    from pdelie.differentiation.fornberg import validate_coordinates

    values = validate_coordinates(coordinates, where="quadrature coordinates")
    spacings = np.diff(values)
    weights = np.zeros_like(values)
    weights[0] = spacings[0] / 2.0
    weights[-1] = spacings[-1] / 2.0
    if values.size > 2:
        weights[1:-1] = (spacings[:-1] + spacings[1:]) / 2.0
    return weights


def validate_quadrature_weights(
    weights: np.ndarray, coordinates: np.ndarray, *, rule: str
) -> dict[str, Any]:
    """WK-7 … WK-9: validate weights, or refuse them.

    The check is exactness on the constant: ``sum(w)`` must equal the interval
    length. A rule that cannot integrate ``1`` over its own interval is not a
    quadrature rule, whatever else it does correctly.

    Linear exactness is **measured and reported, not required**. Trapezoidal
    achieves it; a caller's rule might legitimately not, and refusing on that
    basis would reject valid higher-or-lower-order rules. Reporting it lets a
    reader see what they have.
    """
    from pdelie.differentiation.fornberg import validate_coordinates

    if rule not in QUADRATURE_RULES:
        raise ScopeValidationError(
            f"quadrature rule {rule!r} is not one of {list(QUADRATURE_RULES)}. It "
            f"is refused rather than mapped onto the closest admitted rule: "
            f"approximating a rule the caller did not ask for produces a payload "
            f"describing a computation nobody performed."
        )

    nodes = validate_coordinates(coordinates, where="quadrature coordinates")
    array = np.asarray(weights, dtype=float).ravel()
    if array.shape != nodes.shape:
        raise ScopeValidationError(
            f"{array.size} weight(s) for {nodes.size} coordinate(s); a quadrature "
            f"rule needs one weight per node."
        )
    if not np.all(np.isfinite(array)):
        raise ScopeValidationError("quadrature weights contain a non-finite value.")

    interval_length = float(nodes[-1] - nodes[0])
    # WK-8: derived, not guessed. Summing n weights accumulates O(n*eps)
    # relative error, so the admissible deviation scales with n and with the
    # magnitude being summed.
    tolerance = nodes.size * float(np.finfo(float).eps) * interval_length
    constant_error = abs(float(np.sum(array)) - interval_length)
    if constant_error > tolerance:
        raise ScopeValidationError(
            f"quadrature weights sum to {float(np.sum(array))!r} over an interval "
            f"of length {interval_length!r}; the error {constant_error:.3e} "
            f"exceeds the derived tolerance {tolerance:.3e}. A rule that cannot "
            f"integrate the constant 1 over its own interval is not a quadrature "
            f"rule. It is refused rather than renormalised -- renormalising would "
            f"hide the failure while turning the declared rule into a different "
            f"one."
        )

    # Reported, not required.
    exact_linear = float(np.sum(array * nodes))
    true_linear = float((nodes[-1] ** 2 - nodes[0] ** 2) / 2.0)
    linear_error = abs(exact_linear - true_linear)
    linear_scale = max(abs(true_linear), interval_length)

    return {
        "quadrature_rule": rule,
        "node_count": int(nodes.size),
        "interval_length": interval_length,
        "constant_exactness_error": constant_error,
        "constant_exactness_tolerance": tolerance,
        "linear_exactness_error": linear_error,
        "linear_exactness_relative": linear_error / linear_scale,
        # WK-12: stated rather than omitted. Quadrature error on scattered nodes
        # is not bounded here, and a payload that simply left the question out
        # would read as if it had been answered.
        "irregular_quadrature_error_bounded": False,
    }


@dataclass(frozen=True)
class WeakWindow:
    """One weak-form row: a support interval and the samples it consumed."""

    window_id: str
    support_start: float
    support_end: float
    #: WK-3. Sample-row identities, in order. A window whose samples were
    #: excluded upstream is itself excluded, and can say which caused it.
    sample_row_identities: tuple[str, ...]
    quadrature_rule: str

    def __post_init__(self) -> None:
        if not isinstance(self.window_id, str) or not self.window_id.strip():
            raise ScopeValidationError("window_id must be a non-empty string.")
        if self.quadrature_rule not in QUADRATURE_RULES:
            raise ScopeValidationError(
                f"quadrature_rule {self.quadrature_rule!r} is not one of "
                f"{list(QUADRATURE_RULES)}."
            )
        if not (self.support_end > self.support_start):
            raise ScopeValidationError(
                f"support [{self.support_start}, {self.support_end}] is empty or "
                f"reversed. A window integrating over nothing is not a row."
            )
        identities = tuple(str(value) for value in self.sample_row_identities)
        if not identities:
            raise ScopeValidationError(
                "a window consumed no samples, so nothing was integrated."
            )
        if len(set(identities)) != len(identities):
            raise ScopeValidationError(
                "sample_row_identities repeats; a sample counted twice would be "
                "weighted twice with nothing recording it."
            )
        object.__setattr__(self, "sample_row_identities", identities)

    def identity(self) -> str:
        """WK-1/WK-2: identified by the window, in its own namespace.

        The prefix makes weak-row and sample-row identities provably disjoint
        sets rather than merely unlikely to collide -- ``DesignRowLineage``
        identities are bare hex digests and can never begin with it.
        """
        return WEAK_ROW_IDENTITY_PREFIX + semantic_hash(
            {
                "support_start": self.support_start,
                "support_end": self.support_end,
                "sample_row_identities": list(self.sample_row_identities),
                "quadrature_rule": self.quadrature_rule,
            }
        )

    def excluded_by(self, excluded_sample_identities: Sequence[str]) -> tuple[str, ...]:
        """WK-3: which of this window's samples an upstream mask excluded."""
        excluded = set(excluded_sample_identities)
        return tuple(i for i in self.sample_row_identities if i in excluded)

    def as_dict(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "weak_row_identity": self.identity(),
            "support_start": self.support_start,
            "support_end": self.support_end,
            "sample_count": len(self.sample_row_identities),
            "quadrature_rule": self.quadrature_rule,
            # WK-10: release-scoped. A flag asserting a property forever cannot
            # be revisited when the property changes.
            "diagnostic_only_v0_38": True,
        }


def weak_window_overlap_fraction(windows: Sequence[WeakWindow]) -> dict[str, Any]:
    """WK-4: how much the windows share, declared rather than inferred.

    Two windows sharing samples are not independent evidence. A report that
    lists window residuals without saying how much they overlap invites them to
    be read as independent, which is the mistake this exists to prevent.
    """
    if not windows:
        raise ScopeValidationError("no windows to describe.")
    total = 0
    shared = 0
    seen: dict[str, int] = {}
    for window in windows:
        for identity in window.sample_row_identities:
            total += 1
            seen[identity] = seen.get(identity, 0) + 1
    for count in seen.values():
        if count > 1:
            shared += count - 1
    return {
        "window_count": len(windows),
        "sample_slots_total": total,
        "distinct_samples": len(seen),
        "shared_slots": shared,
        "overlap_fraction": (shared / total) if total else 0.0,
        "windows_are_independent": shared == 0,
    }
