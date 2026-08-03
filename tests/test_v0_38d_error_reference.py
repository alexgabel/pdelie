"""v0.38d: DE-1 .. DE-14, asserted.

Rules frozen in ``docs/design/v0_38d_hypothesis_freeze.md``. The floor boundary
was amended twice during the pilot; both blocks are recorded in
``docs/design/v0_38d_pilot_report.md``.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie.contracts.error_metric_spec import ErrorMetricSpec
from pdelie.differentiation.error_reference import (
    REFERENCE_KINDS,
    REPORTING_REGIMES,
    DerivativeErrorReport,
    compare_against_bound,
    measure_derivative_error,
    summarize_runtime,
)
from pdelie.differentiation.fornberg import fornberg_weights
from pdelie.errors import ScopeValidationError

LINF = ErrorMetricSpec(metric_spec_id="v0_38d_linf", quantity="absolute", norm="linf")
L2 = ErrorMetricSpec(metric_spec_id="v0_38d_l2", quantity="absolute", norm="l2")

_X = np.linspace(0.0, 2.0 * np.pi, 201)
_U = np.sin(4.0 * _X)
_SECOND_DERIVATIVE_SCALE = 16.0


def _second_derivative_at(index: int) -> tuple[np.ndarray, np.ndarray]:
    weights = fornberg_weights(_X[index - 5 : index + 6], _X[index], 2)
    computed = np.array([float(np.dot(weights.weights, _U[index - 5 : index + 6]))])
    exact = np.array([-16.0 * np.sin(4.0 * _X[index])])
    return computed, exact


# --------------------------------------------------------------------------
# DE-5 .. DE-8 -- signal versus floor. The reason this sub-phase exists.
# --------------------------------------------------------------------------


def test_de6_no_relative_error_is_emitted_at_a_zero_crossing() -> None:
    """The v0.38b defect, reproduced deliberately and caught.

    x = pi is where sin(4x) = 0. Pilot runs 1 and 2 both emitted a relative
    error here -- 6.07 in run 1 -- which is precisely how a uniform grid came to
    look like the worst case in the v0.38b sweep.
    """
    computed, exact = _second_derivative_at(100)
    report = measure_derivative_error(
        computed,
        exact,
        metric=LINF,
        reference_kind="analytical",
        reference_scale=_SECOND_DERIVATIVE_SCALE,
    )
    assert report.reporting_regime == "floor"
    assert report.relative_error is None
    assert report.absolute_error is not None, "the absolute error is still reported"


def test_de5_the_signal_regime_reports_both() -> None:
    computed, exact = _second_derivative_at(int(0.37 * 201))
    report = measure_derivative_error(
        computed,
        exact,
        metric=LINF,
        reference_kind="analytical",
        reference_scale=_SECOND_DERIVATIVE_SCALE,
    )
    assert report.reporting_regime == "signal"
    assert report.absolute_error is not None
    assert report.relative_error is not None


def test_de7_the_boundary_does_not_swallow_a_small_but_real_value() -> None:
    """A loose floor would be worse than none: it would hide real signal.

    1e-6 of the quantity's scale is small and genuine. It must read `signal`.
    """
    report = measure_derivative_error(
        np.array([1.6e-5]),
        np.array([1.6e-5 * (1.0 + 1e-9)]),
        metric=LINF,
        reference_kind="analytical",
        reference_scale=_SECOND_DERIVATIVE_SCALE,
    )
    assert report.reporting_regime == "signal"
    assert report.relative_error == pytest.approx(1e-9, rel=1e-3)


def test_de6_the_dataclass_refuses_a_relative_error_at_the_floor() -> None:
    """Enforced at construction, so no producer can bypass the rule."""
    with pytest.raises(ScopeValidationError, match="floor"):
        DerivativeErrorReport(
            reference_kind="analytical",
            metric_spec_id="m",
            norm="linf",
            reporting_regime="floor",
            absolute_error=1.0,
            relative_error=0.5,
            reference_magnitude=1e-20,
            floor_threshold=1e-8,
        )


def test_de8_the_regime_is_always_reported() -> None:
    computed, exact = _second_derivative_at(100)
    payload = measure_derivative_error(
        computed, exact, metric=LINF, reference_kind="analytical", reference_scale=16.0
    ).as_dict()
    assert payload["reporting_regime"] in REPORTING_REGIMES


def test_a_single_point_without_a_declared_scale_is_refused() -> None:
    """Deriving a scale from the point itself is what blocked run 1."""
    with pytest.raises(ScopeValidationError, match="reference_scale is required"):
        measure_derivative_error(
            np.array([1.0]), np.array([1.0]), metric=LINF, reference_kind="analytical"
        )


def test_a_population_supplies_its_own_scale() -> None:
    """With many samples the quantity's extent is a legitimate scale."""
    computed = np.linspace(0.0, 1.0, 32)
    report = measure_derivative_error(
        computed, computed.copy(), metric=LINF, reference_kind="analytical"
    )
    assert report.reporting_regime == "signal"


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
def test_a_nonpositive_scale_is_refused(bad: float) -> None:
    with pytest.raises(ScopeValidationError, match="finite and positive"):
        measure_derivative_error(
            np.array([1.0]),
            np.array([1.0]),
            metric=LINF,
            reference_kind="analytical",
            reference_scale=bad,
        )


# --------------------------------------------------------------------------
# DE-1 .. DE-4 -- the reference
# --------------------------------------------------------------------------


def test_de1_the_reference_kinds_are_closed() -> None:
    assert set(REFERENCE_KINDS) == {"analytical", "refined_grid", "none"}


def test_de2_de3_no_reference_gives_none_never_zero() -> None:
    """A quiet zero is indistinguishable from a perfect measurement."""
    report = measure_derivative_error(
        np.array([1.0, 2.0]), None, metric=LINF, reference_kind="none"
    )
    assert report.reporting_regime == "not_applicable"
    for field in ("absolute_error", "relative_error", "reference_magnitude"):
        assert getattr(report, field) is None
    payload = report.as_dict()
    for field in ("absolute_error", "relative_error", "reference_magnitude"):
        assert field in payload and payload[field] is None, (
            "the field must be present and null, not omitted -- an omitted field "
            "reads as a question that was answered"
        )


def test_de4_a_declared_reference_that_is_not_there_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="no reference was supplied"):
        measure_derivative_error(
            np.array([1.0]), None, metric=LINF, reference_kind="analytical"
        )


def test_de4_a_reference_supplied_under_none_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="derived from what is present"):
        measure_derivative_error(
            np.array([1.0]), np.array([1.0]), metric=LINF, reference_kind="none"
        )


def test_de3_the_dataclass_refuses_a_number_under_none() -> None:
    with pytest.raises(ScopeValidationError, match="indistinguishable from a measured zero"):
        DerivativeErrorReport(
            reference_kind="none",
            metric_spec_id="m",
            norm="linf",
            reporting_regime="not_applicable",
            absolute_error=0.0,
            relative_error=None,
            reference_magnitude=None,
            floor_threshold=None,
        )


# --------------------------------------------------------------------------
# DE-9, DE-10 -- the metric must be declared and must match
# --------------------------------------------------------------------------


def test_de9_there_is_no_default_metric() -> None:
    import inspect

    parameters = inspect.signature(measure_derivative_error).parameters
    assert parameters["metric"].default is inspect.Parameter.empty


def test_de10_a_metric_mismatch_is_refused() -> None:
    """The v0.37c pilot-1 defect: an linf bound against an l2 measurement."""
    computed, exact = _second_derivative_at(int(0.37 * 201))
    report = measure_derivative_error(
        computed, exact, metric=LINF, reference_kind="analytical", reference_scale=16.0
    )
    with pytest.raises(ScopeValidationError):
        compare_against_bound(report, 1e-6, bound_metric=L2)


def test_de10_a_matching_metric_compares() -> None:
    computed, exact = _second_derivative_at(int(0.37 * 201))
    report = measure_derivative_error(
        computed, exact, metric=LINF, reference_kind="analytical", reference_scale=16.0
    )
    result = compare_against_bound(report, 1e-6, bound_metric=LINF)
    assert result["within_bound"] is True
    assert result["reporting_regime"] == "signal"


def test_comparing_against_an_absent_measurement_is_refused() -> None:
    report = measure_derivative_error(
        np.array([1.0]), None, metric=LINF, reference_kind="none"
    )
    with pytest.raises(ScopeValidationError, match="no measurement to compare"):
        compare_against_bound(report, 1.0, bound_metric=LINF)


# --------------------------------------------------------------------------
# DE-11 .. DE-14 -- timing
# --------------------------------------------------------------------------


def test_de11_the_payload_carries_all_four_fields() -> None:
    stats = summarize_runtime([0.1, 0.2, 0.15, 0.12], backend="fornberg", warmup_runs=5)
    payload = stats.as_dict()
    for key in ("warmup_runs", "measured_runs", "median_seconds", "iqr_seconds"):
        assert key in payload


def test_de12_no_mean_is_reported() -> None:
    """A mean without a spread hides bimodality; reporting both invites the
    mean to be quoted alone."""
    stats = summarize_runtime([0.1, 0.2, 0.15], backend="b", warmup_runs=1)
    assert not hasattr(stats, "mean_seconds")
    assert "mean" not in json.dumps(stats.as_dict())


def test_de13_a_single_run_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="sample of one"):
        summarize_runtime([0.1], backend="b", warmup_runs=0)


def test_de14_timing_declares_itself_platform_specific() -> None:
    stats = summarize_runtime([0.1, 0.2], backend="b", warmup_runs=0)
    assert stats.as_dict()["portability_class"] == "platform_specific_diagnostic"


def test_negative_or_non_finite_durations_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="negative"):
        summarize_runtime([0.1, -0.2], backend="b", warmup_runs=0)
    with pytest.raises(ScopeValidationError, match="non-finite"):
        summarize_runtime([0.1, float("nan")], backend="b", warmup_runs=0)


def test_the_iqr_is_a_real_spread() -> None:
    tight = summarize_runtime([1.0, 1.0, 1.0, 1.0], backend="b", warmup_runs=0)
    wide = summarize_runtime([1.0, 2.0, 3.0, 10.0], backend="b", warmup_runs=0)
    assert tight.iqr_seconds == 0.0
    assert wide.iqr_seconds > 0.0


# --------------------------------------------------------------------------
# Payload
# --------------------------------------------------------------------------


def test_the_payloads_are_strict_json() -> None:
    computed, exact = _second_derivative_at(100)
    report = measure_derivative_error(
        computed, exact, metric=LINF, reference_kind="analytical", reference_scale=16.0
    )
    json.dumps(report.as_dict(), allow_nan=False)
    json.dumps(summarize_runtime([0.1, 0.2], backend="b", warmup_runs=1).as_dict(), allow_nan=False)
