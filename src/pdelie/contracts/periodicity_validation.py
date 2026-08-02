"""v0.38: periodicity is validated at three layers, not declared at one.

``ProfileGeometrySpec`` refuses ``periodic_smooth`` when no periodic axis is
named. That is a **structural** check, and structure is the weakest of the three
things "periodic" can mean:

===============  =========================================================
Layer            The question it answers
===============  =========================================================
**Structural**   Is a periodic coordinate axis declared?
**Values**       Do the sampled values -- and their slope -- actually join
                 across the wrap, to a declared tolerance?
**Analytical**   Does the source specification define a periodic function
                 at all?
===============  =========================================================

Why all three
=============

C-4 passed the structural check. Its bundle declared ``periodic_uniform``, its
axis was periodic, and every gate agreed -- while the profile was ``tanh``,
which is nonperiodic by construction. At the seam it jumped ``1.9998`` against a
typical adjacent step of ``0.3198``. Structure said periodic; the values said
otherwise; the analytical form had never been asked.

A declaration must not pass merely because the metadata says periodic.

The values layer is scale-free
==============================

The wrap jump is compared against the *typical interior step*, not against an
absolute number. An absolute threshold would classify the same profile
differently in different units, and would need a value nobody has measured. The
ratio needs neither: a profile that genuinely wraps has a seam step
indistinguishable from its interior steps.

The tolerance is caller-declared, with no default -- same rule as
``scientific_identity``. A defaulted tolerance is a claim nobody made.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from pdelie.errors import ScopeValidationError

__all__ = [
    "ANALYTICAL_PERIODICITY_STATUSES",
    "PERIODIC_FORM_CLASSIFICATION",
    "WRAP_CONSISTENCY_STATUSES",
    "PeriodicityValidation",
    "classify_analytical_periodicity",
    "validate_periodicity",
]

#: Values-layer outcomes. ``not_evaluated`` is distinct from a pass: a check
#: that did not run has produced no evidence, and must not read as one.
WRAP_CONSISTENCY_STATUSES: tuple[str, ...] = (
    "within_tolerance",
    "outside_tolerance",
    "not_evaluated",
)

#: Analytical-layer outcomes. ``undetermined`` is not ``confirmed``: an
#: unrecognised form is an absence of evidence, and collapsing the two is how a
#: nonperiodic profile passes for want of a rule about it.
ANALYTICAL_PERIODICITY_STATUSES: tuple[str, ...] = (
    "confirmed",
    "refuted",
    "undetermined",
    "not_declared",
)

#: What the shipped profile forms are known to be. Growth-only: an unlisted form
#: is ``undetermined``, never assumed periodic.
PERIODIC_FORM_CLASSIFICATION: dict[str, str] = {
    "constant": "confirmed",
    "sinusoidal": "confirmed",
    "higher_frequency": "confirmed",
    # Nonzero everywhere on a bounded domain, so its two ends do not meet. This
    # is the C-6 profile: legal, and not periodic.
    "localized_bump": "undetermined",
    # The C-4 profile. tanh is monotone, so its ends cannot meet.
    "monotone_smooth": "refuted",
}


@dataclass(frozen=True)
class PeriodicityValidation:
    """What each layer concluded, kept separate."""

    periodic_axis_declared: bool
    wrap_value_consistency: str
    wrap_derivative_consistency: str
    analytical_periodicity: str
    wrap_value_ratio: float | None
    wrap_derivative_ratio: float | None
    tolerance_ratio: float | None

    def __post_init__(self) -> None:
        for name, allowed in (
            ("wrap_value_consistency", WRAP_CONSISTENCY_STATUSES),
            ("wrap_derivative_consistency", WRAP_CONSISTENCY_STATUSES),
            ("analytical_periodicity", ANALYTICAL_PERIODICITY_STATUSES),
        ):
            value = getattr(self, name)
            if value not in allowed:
                raise ScopeValidationError(f"{name} {value!r} is not one of {list(allowed)}.")

    @property
    def is_periodic_at_every_layer(self) -> bool:
        """All three agree. Deliberately strict.

        ``undetermined`` does not satisfy it: a profile whose analytical form
        nobody has classified has not been shown to be periodic, and a
        load-bearing use needs showing rather than not-refuted.
        """
        return (
            self.periodic_axis_declared
            and self.wrap_value_consistency == "within_tolerance"
            and self.wrap_derivative_consistency == "within_tolerance"
            and self.analytical_periodicity == "confirmed"
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "periodic_axis_declared": self.periodic_axis_declared,
            "wrap_value_consistency": self.wrap_value_consistency,
            "wrap_derivative_consistency": self.wrap_derivative_consistency,
            "analytical_periodicity": self.analytical_periodicity,
            "wrap_value_ratio": self.wrap_value_ratio,
            "wrap_derivative_ratio": self.wrap_derivative_ratio,
            "tolerance_ratio": self.tolerance_ratio,
        }


def classify_analytical_periodicity(analytical_spec: object) -> str:
    """Layer 3: does the declared source form define a periodic function?

    An unrecognised form returns ``undetermined``, never ``confirmed``. Assuming
    periodicity for want of a rule is how C-4 got through.
    """
    if analytical_spec is None:
        return "not_declared"
    if not isinstance(analytical_spec, dict):
        raise ScopeValidationError("analytical_spec must be a mapping or None.")
    profile_id = analytical_spec.get("profile_id")
    if not isinstance(profile_id, str):
        return "undetermined"
    return PERIODIC_FORM_CLASSIFICATION.get(profile_id, "undetermined")


def _wrap_ratio(samples: np.ndarray) -> tuple[float, float]:
    """Return ``(seam_step, typical_interior_step)`` for a wrapped sequence.

    ``typical`` is the **median** absolute interior step, not the mean: one
    large seam-like feature in the interior would drag a mean upward and hide
    the very discontinuity this exists to find.
    """
    interior = np.abs(np.diff(samples))
    seam = float(abs(samples[0] - samples[-1]))
    return seam, float(np.median(interior))


def validate_periodicity(
    *,
    periodic_axis_declared: bool,
    values: np.ndarray | None = None,
    analytical_spec: object = None,
    tolerance_ratio: float | None = None,
) -> PeriodicityValidation:
    """Run all three layers and report each separately.

    ``tolerance_ratio`` is how many typical interior steps the seam step may be.
    Required whenever ``values`` are supplied, and with no default: a defaulted
    tolerance is a claim nobody made.

    For scale, the historical C-4 measurement was a seam step of ``1.9998``
    against a typical interior step of ``0.3198`` -- a ratio of ``6.25`` on that
    profile at that resolution. The tanh fixture in the test suite is steeper
    and reports a far larger ratio; both are far outside any tolerance a
    periodic profile would need.

    Layers that cannot run report ``not_evaluated`` rather than passing. A check
    that did not happen is not a check that succeeded, and the two must never
    collapse into one value.
    """
    if not isinstance(periodic_axis_declared, bool):
        raise ScopeValidationError("periodic_axis_declared must be a bool.")

    value_status = "not_evaluated"
    derivative_status = "not_evaluated"
    value_ratio: float | None = None
    derivative_ratio: float | None = None

    if values is not None:
        if tolerance_ratio is None:
            raise ScopeValidationError(
                "tolerance_ratio is required when values are supplied. There is "
                "no default: a defaulted tolerance is a claim nobody made, and "
                "the seam-to-interior ratio is the number this check turns on."
            )
        if not isinstance(tolerance_ratio, (int, float)) or isinstance(tolerance_ratio, bool):
            raise ScopeValidationError("tolerance_ratio must be a real number.")
        tolerance_ratio = float(tolerance_ratio)
        if not np.isfinite(tolerance_ratio) or tolerance_ratio <= 0.0:
            raise ScopeValidationError("tolerance_ratio must be finite and positive.")

        samples = np.asarray(values, dtype=float).ravel()
        if samples.size < 4:
            raise ScopeValidationError(
                f"periodicity needs at least four samples to compare a seam step "
                f"against interior steps; got {samples.size}."
            )
        if not np.all(np.isfinite(samples)):
            raise ScopeValidationError("values contain a non-finite entry.")

        seam, typical = _wrap_ratio(samples)
        if typical == 0.0:
            # A constant profile: every interior step is zero, so the ratio is
            # undefined. The seam step decides it directly -- and for a constant
            # profile it is zero too.
            value_ratio = 0.0 if seam == 0.0 else float("inf")
        else:
            value_ratio = seam / typical
        value_status = (
            "within_tolerance" if value_ratio <= tolerance_ratio else "outside_tolerance"
        )

        # Layer 2b: does the SLOPE join across the seam, or does the profile
        # kink there? A profile can meet in value and still corner, and
        # "smooth across the wrap" is a claim about the slope, not just the
        # value.
        #
        # Built on the fully wrapped step sequence so the seam is an ordinary
        # position in it. Curvature is the change in step; the two curvatures
        # that involve the seam step are compared against the median interior
        # curvature. Same units on both sides, unlike an earlier version here
        # which divided a step by a second difference and produced a ratio that
        # meant nothing.
        steps = np.append(np.diff(samples), float(samples[0] - samples[-1]))
        curvature = np.abs(np.diff(np.append(steps, steps[0])))
        seam_curvature = float(np.max(curvature[-2:]))
        interior_curvature = float(np.median(curvature[:-2]))
        if interior_curvature == 0.0:
            derivative_ratio = 0.0 if seam_curvature == 0.0 else float("inf")
        else:
            derivative_ratio = seam_curvature / interior_curvature
        derivative_status = (
            "within_tolerance"
            if derivative_ratio <= tolerance_ratio
            else "outside_tolerance"
        )

    return PeriodicityValidation(
        periodic_axis_declared=periodic_axis_declared,
        wrap_value_consistency=value_status,
        wrap_derivative_consistency=derivative_status,
        analytical_periodicity=classify_analytical_periodicity(analytical_spec),
        wrap_value_ratio=value_ratio,
        wrap_derivative_ratio=derivative_ratio,
        tolerance_ratio=tolerance_ratio,
    )
