"""v0.38d: derivative error against a stated reference, and honest timing.

This is the layer that reports errors, so the two error-reporting defects this
arc already produced are designed against structurally rather than warned about.

**v0.37c pilot 1** blocked because a bound derived in ``‖·‖∞`` was compared
against a measurement emitted in ``‖·‖₂`` -- a factor of 11.96 between two
numbers both called "the error". Every error here carries an
:class:`ErrorMetricSpec`, and comparison goes through ``require_matching_metric``.

**The v0.38b pilot's first sweep** reported a *uniform* grid as the worst case,
because it computed a relative error at a zero crossing and divided by a
``1e-12`` floor. Here a relative error exists **only** in the ``signal`` regime;
at the floor it is ``None``, and the regime is always reported.

A reference that does not exist is said, not omitted
====================================================

Real data has no closed-form derivative. ``reference_kind = "none"`` is a
first-class outcome with every error field ``None`` -- never ``0.0``, which
would read as a perfect measurement, and never omitted, which would read as a
question that had been answered.

Rules DE-1 .. DE-14 are frozen in ``docs/design/v0_38d_hypothesis_freeze.md``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from pdelie.contracts.error_metric_spec import ErrorMetricSpec
from pdelie.errors import ScopeValidationError

__all__ = [
    "REFERENCE_KINDS",
    "REPORTING_REGIMES",
    "DerivativeErrorReport",
    "RuntimeStats",
    "compare_against_bound",
    "measure_derivative_error",
    "summarize_runtime",
]

#: DE-1. Closed. ``none`` is an outcome, not an absence.
REFERENCE_KINDS: tuple[str, ...] = ("analytical", "refined_grid", "none")

#: DE-5. Which regime a number should be read in.
REPORTING_REGIMES: tuple[str, ...] = ("signal", "floor", "not_applicable")


@dataclass(frozen=True)
class DerivativeErrorReport:
    """Measured error, the reference it is against, and how to read it."""

    reference_kind: str
    metric_spec_id: str
    norm: str
    reporting_regime: str
    absolute_error: float | None
    relative_error: float | None
    reference_magnitude: float | None
    floor_threshold: float | None

    def __post_init__(self) -> None:
        if self.reference_kind not in REFERENCE_KINDS:
            raise ScopeValidationError(
                f"reference_kind {self.reference_kind!r} is not one of "
                f"{list(REFERENCE_KINDS)}."
            )
        if self.reporting_regime not in REPORTING_REGIMES:
            raise ScopeValidationError(
                f"reporting_regime {self.reporting_regime!r} is not one of "
                f"{list(REPORTING_REGIMES)}."
            )
        # DE-3: with no reference there is no error, and no field pretends there
        # is. 0.0 would read as a perfect measurement.
        if self.reference_kind == "none":
            for name in ("absolute_error", "relative_error", "reference_magnitude"):
                if getattr(self, name) is not None:
                    raise ScopeValidationError(
                        f"reference_kind is 'none' but {name} is "
                        f"{getattr(self, name)!r}. With no reference there is no "
                        f"error; a number here would be indistinguishable from a "
                        f"measured zero."
                    )
        # DE-6: a relative error exists only where the reference has magnitude.
        if self.reporting_regime == "floor" and self.relative_error is not None:
            raise ScopeValidationError(
                "a relative error was reported in the 'floor' regime. A relative "
                "difference against a near-zero reference is not a number, and "
                "reporting one is how a uniform grid comes to look like the worst "
                "case."
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "reference_kind": self.reference_kind,
            "metric_spec_id": self.metric_spec_id,
            "norm": self.norm,
            "reporting_regime": self.reporting_regime,
            "absolute_error": self.absolute_error,
            "relative_error": self.relative_error,
            "reference_magnitude": self.reference_magnitude,
            "floor_threshold": self.floor_threshold,
        }


def measure_derivative_error(
    computed: np.ndarray,
    reference: np.ndarray | None,
    *,
    metric: ErrorMetricSpec,
    reference_kind: str,
    reference_scale: float | None = None,
) -> DerivativeErrorReport:
    """Measure error against a reference, or report that there is none.

    DE-4: ``reference_kind`` is checked against what was actually supplied. A
    caller declaring ``analytical`` while passing no reference is refused, not
    believed -- the same rule as ``formal_accuracy`` and
    ``full_field_derivatives_available``.

    DE-7: the floor boundary is **derived** as ``n * eps * reference_scale``.

    ``reference_scale`` is the *characteristic magnitude of the quantity over
    its domain* -- not the pointwise value here. It is required whenever a
    single point is compared, and there is no default.

**Runs 1 and 2 both blocked on criterion B-1.**

    Run 1 derived the scale from ``max|computed|``. At a zero crossing that is
    itself ~0, so the floor collapsed to ``2.3e-29`` and a relative error of
    **6.07** was emitted -- the v0.38b defect reproduced by the code written to
    prevent it.

    Run 2 took the scale from the caller and set the floor at
    ``n * eps * scale`` = ``3.6e-15``. Still *signal*: the reference magnitude
    at the crossing was ``2.1e-14``, six times that. The formula covers error in
    the **comparison arithmetic** and not error in **producing the reference**.
    Evaluating ``-16 sin(4x)`` near ``x = pi`` inherits ``x``'s own
    representation error amplified by ``|d/dx| = 64``, giving ``~4e-14`` -- and
    this layer cannot know how a caller produced their reference, so it cannot
    derive that term.

    **Resolved by using a relative boundary at ``sqrt(eps)``.** A quantity
    computed to relative accuracy ``eps`` carries absolute noise ``eps * scale``;
    it is distinguishable from that noise once it exceeds it by a comfortable
    margin, and ``sqrt(eps)`` -- the geometric mean of ``eps`` and 1 -- is the
    conventional margin. It is a **stated convention with a rationale, not a
    quantity that falls out of an equation**, and is recorded as such rather
    than dressed up as a derivation.

    At the crossing the reference is ``1.3e-15`` of scale, far below
    ``sqrt(eps) ~ 1.5e-8``: floor. Away from it the reference is ``0.125`` of
    scale: signal.
    """
    if not isinstance(metric, ErrorMetricSpec):
        raise ScopeValidationError(
            "measure_derivative_error requires an ErrorMetricSpec. There is no "
            "default metric: a bound derived in one norm and compared against a "
            "measurement in another is the v0.37c pilot-1 defect."
        )
    if reference_kind not in REFERENCE_KINDS:
        raise ScopeValidationError(
            f"reference_kind {reference_kind!r} is not one of {list(REFERENCE_KINDS)}."
        )

    # DE-4: declaration checked against what was supplied, never trusted.
    if reference_kind == "none" and reference is not None:
        raise ScopeValidationError(
            "reference_kind is 'none' but a reference was supplied. The kind is "
            "derived from what is present, not declared over it."
        )
    if reference_kind != "none" and reference is None:
        raise ScopeValidationError(
            f"reference_kind is {reference_kind!r} but no reference was supplied. "
            f"Declaring a reference that is not there would report an error "
            f"against nothing."
        )

    if reference_kind == "none":
        return DerivativeErrorReport(
            reference_kind="none",
            metric_spec_id=metric.metric_spec_id,
            norm=metric.norm,
            reporting_regime="not_applicable",
            absolute_error=None,
            relative_error=None,
            reference_magnitude=None,
            floor_threshold=None,
        )

    approximation = np.asarray(computed, dtype=float).ravel()
    truth = np.asarray(reference, dtype=float).ravel()
    if approximation.shape != truth.shape:
        raise ScopeValidationError(
            f"computed has {approximation.size} value(s) and reference has "
            f"{truth.size}; they are not comparable."
        )
    if approximation.size == 0:
        raise ScopeValidationError("nothing to compare.")
    if not (np.all(np.isfinite(approximation)) and np.all(np.isfinite(truth))):
        raise ScopeValidationError(
            "computed or reference contains a non-finite value; no norm of the "
            "difference is a meaningful error."
        )

    difference = approximation - truth
    if metric.norm == "linf":
        absolute = float(np.max(np.abs(difference)))
        magnitude = float(np.max(np.abs(truth)))
    elif metric.norm == "l2":
        absolute = float(np.sqrt(np.sum(difference**2)))
        magnitude = float(np.sqrt(np.sum(truth**2)))
    else:  # pragma: no cover - ErrorMetricSpec closes the vocabulary
        raise ScopeValidationError(f"unhandled norm {metric.norm!r}.")

    # DE-7, as amended after run 1 blocked.
    if reference_scale is None:
        if truth.size < 2:
            raise ScopeValidationError(
                "reference_scale is required when comparing a single point. The "
                "floor boundary asks whether the reference is distinguishable "
                "from zero relative to the QUANTITY'S scale, and a one-element "
                "reference carries no scale of its own -- deriving one from the "
                "point itself makes the threshold vanish exactly where it is "
                "needed, which is how pilot run 1 emitted a relative error of "
                "6.07 at a zero crossing."
            )
        # With a population, the quantity's own extent is a legitimate scale.
        scale = float(np.max(np.abs(truth)))
    else:
        if not isinstance(reference_scale, (int, float)) or isinstance(reference_scale, bool):
            raise ScopeValidationError("reference_scale must be a real number.")
        scale = float(reference_scale)
        if not np.isfinite(scale) or scale <= 0.0:
            raise ScopeValidationError(
                f"reference_scale must be finite and positive; got {scale!r}. A "
                f"zero scale would put every point at the floor."
            )
    # A RELATIVE boundary, because the absolute one cannot see reference-
    # production error. See the docstring: runs 1 and 2 both blocked here.
    floor_threshold = float(np.sqrt(np.finfo(float).eps)) * scale
    in_signal = magnitude > floor_threshold

    return DerivativeErrorReport(
        reference_kind=reference_kind,
        metric_spec_id=metric.metric_spec_id,
        norm=metric.norm,
        reporting_regime="signal" if in_signal else "floor",
        absolute_error=absolute,
        # DE-6: only in the signal regime.
        relative_error=(absolute / magnitude) if in_signal else None,
        reference_magnitude=magnitude,
        floor_threshold=floor_threshold,
    )


def compare_against_bound(
    report: DerivativeErrorReport, bound: float, *, bound_metric: ErrorMetricSpec
) -> dict[str, Any]:
    """DE-10: compare a measurement against a bound, or refuse.

    The metric identities must match. A ``‖·‖∞`` bound compared against a
    ``‖·‖₂`` measurement is the v0.37c pilot-1 defect, and this is where it
    becomes impossible rather than merely discouraged.
    """
    from pdelie.contracts.error_metric_spec import require_matching_metric

    if report.reference_kind == "none":
        raise ScopeValidationError(
            "there is no measurement to compare: reference_kind is 'none'. A "
            "comparison here would be against an absent number."
        )
    measurement_metric = ErrorMetricSpec(
        metric_spec_id=report.metric_spec_id,
        quantity="absolute",
        norm=report.norm,
    )
    require_matching_metric(bound_metric, measurement_metric, where="derivative error")

    assert report.absolute_error is not None
    return {
        "metric_spec_id": report.metric_spec_id,
        "norm": report.norm,
        "bound": float(bound),
        "measured": report.absolute_error,
        "within_bound": report.absolute_error <= float(bound),
        "reporting_regime": report.reporting_regime,
    }


@dataclass(frozen=True)
class RuntimeStats:
    """DE-11 … DE-14. Median and spread, never a mean."""

    backend: str
    warmup_runs: int
    measured_runs: int
    median_seconds: float
    iqr_seconds: float

    def __post_init__(self) -> None:
        if not isinstance(self.backend, str) or not self.backend.strip():
            raise ScopeValidationError("backend must be a non-empty string.")
        if self.warmup_runs < 0:
            raise ScopeValidationError("warmup_runs must be non-negative.")
        # DE-13: an IQR over one sample is not a spread.
        if self.measured_runs < 2:
            raise ScopeValidationError(
                f"measured_runs is {self.measured_runs}; at least two are needed. "
                f"A single timing is a sample of one and its spread is not a "
                f"spread."
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "warmup_runs": self.warmup_runs,
            "measured_runs": self.measured_runs,
            "median_seconds": self.median_seconds,
            "iqr_seconds": self.iqr_seconds,
            # DE-14: never compared across platforms, and the payload says so
            # rather than leaving a reader to assume it is portable.
            "portability_class": "platform_specific_diagnostic",
        }


def summarize_runtime(
    durations: Sequence[float], *, backend: str, warmup_runs: int
) -> RuntimeStats:
    """Median and IQR over measured runs.

    DE-12: **no mean is computed.** A mean without a spread hides bimodality
    from warmup, and reporting both invites the mean to be quoted alone.
    """
    values = np.asarray(list(durations), dtype=float)
    if values.size and not np.all(np.isfinite(values)):
        raise ScopeValidationError("durations contain a non-finite value.")
    if values.size and np.any(values < 0.0):
        raise ScopeValidationError("durations contain a negative value.")

    quartiles = (
        np.percentile(values, [25.0, 75.0]) if values.size >= 2 else np.array([0.0, 0.0])
    )
    return RuntimeStats(
        backend=backend,
        warmup_runs=int(warmup_runs),
        measured_runs=int(values.size),
        median_seconds=float(np.median(values)) if values.size else 0.0,
        iqr_seconds=float(quartiles[1] - quartiles[0]),
    )
