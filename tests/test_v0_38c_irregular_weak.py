"""v0.38c: WK-1 .. WK-12, asserted.

Rules frozen in ``docs/design/v0_38c_hypothesis_freeze.md``.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie.design.lineage import DesignRowLineage
from pdelie.errors import ScopeValidationError
from pdelie.residuals.irregular_weak import (
    QUADRATURE_RULES,
    WEAK_ROW_IDENTITY_PREFIX,
    WeakWindow,
    nonuniform_trapezoidal_weights,
    validate_quadrature_weights,
    weak_window_overlap_fraction,
)

_RULE = "nonuniform_trapezoidal"


def _sample_identities(count: int) -> tuple[str, ...]:
    return tuple(
        DesignRowLineage(
            trajectory_id="t", source_coordinate_id=f"x_{i}", mask_id="m"
        ).identity()
        for i in range(count)
    )


def _window(count: int = 4, **overrides) -> WeakWindow:
    kwargs = {
        "window_id": "w0",
        "support_start": 0.0,
        "support_end": 1.0,
        "sample_row_identities": _sample_identities(count),
        "quadrature_rule": _RULE,
    }
    kwargs.update(overrides)
    return WeakWindow(**kwargs)


def _irregular(count: int = 40) -> np.ndarray:
    rng = np.random.default_rng(13)
    return np.sort(
        np.concatenate([[0.0], np.cumsum(rng.uniform(0.01, 1.0, count - 1))])
    )


# --------------------------------------------------------------------------
# WK-1, WK-2 -- a weak row is a window, in its own namespace
# --------------------------------------------------------------------------


def test_wk2_weak_and_strong_row_identities_cannot_collide() -> None:
    """The distinction this sub-phase turns on.

    ``DesignRowLineage.identity()`` is a bare hex digest, so it can never begin
    with the weak prefix. The two sets are disjoint by construction rather than
    unlikely to collide.
    """
    strong = _sample_identities(20)
    weak = _window().identity()
    assert weak.startswith(WEAK_ROW_IDENTITY_PREFIX)
    assert not any(identity.startswith(WEAK_ROW_IDENTITY_PREFIX) for identity in strong)
    assert weak not in strong


def test_wk1_the_identity_is_the_window_not_a_sample() -> None:
    """Two windows over the same samples but different supports differ."""
    identities = _sample_identities(4)
    a = _window(sample_row_identities=identities, support_end=1.0)
    b = _window(sample_row_identities=identities, support_end=2.0)
    assert a.identity() != b.identity()


def test_wk1_the_identity_ignores_the_window_label() -> None:
    """A label is not an identity; two identically-supported windows are one row."""
    identities = _sample_identities(4)
    a = _window(window_id="alpha", sample_row_identities=identities)
    b = _window(window_id="beta", sample_row_identities=identities)
    assert a.identity() == b.identity()


# --------------------------------------------------------------------------
# WK-3 -- a window says which samples an upstream mask removed
# --------------------------------------------------------------------------


def test_wk3_a_window_reports_which_of_its_samples_were_excluded() -> None:
    window = _window(count=4)
    excluded = window.excluded_by([window.sample_row_identities[1]])
    assert excluded == (window.sample_row_identities[1],)


def test_wk3_an_unaffected_window_reports_nothing() -> None:
    window = _window(count=4)
    assert window.excluded_by(["some_other_row"]) == ()


# --------------------------------------------------------------------------
# WK-4 -- overlap is declared, not inferred
# --------------------------------------------------------------------------


def test_wk4_overlap_is_reported() -> None:
    identities = _sample_identities(10)
    windows = [
        _window(
            window_id=f"w{k}",
            support_start=float(k),
            support_end=float(k + 3),
            sample_row_identities=identities[k : k + 4],
        )
        for k in range(0, 7, 2)
    ]
    report = weak_window_overlap_fraction(windows)
    assert report["overlap_fraction"] > 0.0
    assert report["windows_are_independent"] is False


def test_wk4_disjoint_windows_are_reported_independent() -> None:
    identities = _sample_identities(8)
    windows = [
        _window(
            window_id=f"w{k}",
            support_start=float(k),
            support_end=float(k + 1),
            sample_row_identities=identities[4 * k : 4 * k + 4],
        )
        for k in range(2)
    ]
    report = weak_window_overlap_fraction(windows)
    assert report["overlap_fraction"] == 0.0
    assert report["windows_are_independent"] is True


# --------------------------------------------------------------------------
# WK-5 -- exactly two rules
# --------------------------------------------------------------------------


def test_wk5_only_two_rules_exist() -> None:
    assert set(QUADRATURE_RULES) == {
        "nonuniform_trapezoidal",
        "user_supplied_validated_weights",
    }


@pytest.mark.parametrize("rule", ["simpson", "gauss_legendre", "romberg", ""])
def test_wk5_a_third_rule_is_refused_not_mapped(rule: str) -> None:
    """Approximating a rule nobody asked for produces a payload describing a
    computation nobody performed."""
    x = np.linspace(0.0, 3.0, 4)
    with pytest.raises(ScopeValidationError, match="is not one of"):
        validate_quadrature_weights(nonuniform_trapezoidal_weights(x), x, rule=rule)


def test_wk5_a_window_refuses_an_unknown_rule() -> None:
    with pytest.raises(ScopeValidationError, match="is not one of"):
        _window(quadrature_rule="simpson")


# --------------------------------------------------------------------------
# WK-6 .. WK-9 -- trapezoidal derived, user weights validated
# --------------------------------------------------------------------------


@pytest.mark.parametrize("count", [4, 17, 40])
def test_wk6_trapezoidal_integrates_the_constant_exactly(count: int) -> None:
    x = _irregular(count)
    report = validate_quadrature_weights(
        nonuniform_trapezoidal_weights(x), x, rule=_RULE
    )
    assert report["constant_exactness_error"] <= report["constant_exactness_tolerance"]


def test_wk6_trapezoidal_is_exact_on_linear_integrands() -> None:
    """A property of the rule, not of the grid: it holds on any spacing."""
    x = _irregular(40)
    report = validate_quadrature_weights(
        nonuniform_trapezoidal_weights(x), x, rule=_RULE
    )
    assert report["linear_exactness_relative"] < 1e-12


def test_wk6_trapezoidal_reduces_to_the_uniform_rule() -> None:
    """On equal spacings the interior weights are h and the ends h/2."""
    x = np.linspace(0.0, 4.0, 5)
    weights = nonuniform_trapezoidal_weights(x)
    assert weights[0] == pytest.approx(0.5)
    assert weights[-1] == pytest.approx(0.5)
    assert np.allclose(weights[1:-1], 1.0)


def test_wk7_weights_that_cannot_integrate_one_are_refused() -> None:
    x = np.linspace(0.0, 3.0, 4)
    with pytest.raises(ScopeValidationError, match="not a quadrature rule"):
        validate_quadrature_weights(np.ones(4), x, rule="user_supplied_validated_weights")


def test_wk9_failing_weights_are_not_renormalised() -> None:
    """Renormalising would hide the failure and change the declared rule."""
    x = np.linspace(0.0, 3.0, 4)
    bad = np.ones(4)
    with pytest.raises(ScopeValidationError, match="rather than renormalised"):
        validate_quadrature_weights(bad, x, rule="user_supplied_validated_weights")
    assert np.array_equal(bad, np.ones(4)), "the caller's array was mutated"


def test_wk8_the_tolerance_is_derived_from_node_count_and_interval() -> None:
    """n * eps * interval_length -- the form comes from the arithmetic."""
    x = np.linspace(0.0, 10.0, 25)
    report = validate_quadrature_weights(
        nonuniform_trapezoidal_weights(x), x, rule=_RULE
    )
    assert report["constant_exactness_tolerance"] == pytest.approx(
        25 * np.finfo(float).eps * 10.0
    )


def test_wk8_the_tolerance_does_not_admit_a_real_error() -> None:
    """A 1% error must be refused however many nodes there are."""
    x = np.linspace(0.0, 3.0, 100)
    weights = nonuniform_trapezoidal_weights(x) * 1.01
    with pytest.raises(ScopeValidationError, match="exceeds the derived tolerance"):
        validate_quadrature_weights(weights, x, rule=_RULE)


def test_a_weight_count_mismatch_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="one weight per node"):
        validate_quadrature_weights(np.ones(3), np.linspace(0.0, 3.0, 4), rule=_RULE)


def test_duplicate_coordinates_are_refused_by_the_shared_validator() -> None:
    """The v0.38b rule, reused rather than reimplemented."""
    with pytest.raises(ScopeValidationError, match="refused, not"):
        nonuniform_trapezoidal_weights(np.array([0.0, 1.0, 1.0, 2.0]))


# --------------------------------------------------------------------------
# WK-10, WK-11 -- the release-scoped flag
# --------------------------------------------------------------------------


def test_wk10_payloads_carry_the_release_scoped_flag() -> None:
    payload = _window().as_dict()
    assert payload["diagnostic_only_v0_38"] is True


def test_wk11_the_unscoped_key_is_absent() -> None:
    """So a consumer cannot read whichever it happens to find first."""
    payload = _window().as_dict()
    assert "diagnostic_only" not in payload, (
        "both the scoped and unscoped keys are present; a consumer reading the "
        "wrong one would get a claim with no release attached to it"
    )


# --------------------------------------------------------------------------
# WK-12 -- the unbounded-error question is stated, not omitted
# --------------------------------------------------------------------------


def test_wk12_the_payload_says_the_quadrature_error_is_unbounded() -> None:
    """A payload omitting the question reads as if it had been answered."""
    x = _irregular(20)
    report = validate_quadrature_weights(
        nonuniform_trapezoidal_weights(x), x, rule=_RULE
    )
    assert report["irregular_quadrature_error_bounded"] is False


# --------------------------------------------------------------------------
# Structural refusals and scope
# --------------------------------------------------------------------------


def test_an_empty_or_reversed_support_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="empty or"):
        _window(support_start=1.0, support_end=1.0)


def test_a_window_consuming_no_samples_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="integrated"):
        _window(sample_row_identities=())


def test_a_repeated_sample_in_one_window_is_refused() -> None:
    identity = _sample_identities(1)[0]
    with pytest.raises(ScopeValidationError, match="counted twice"):
        _window(sample_row_identities=(identity, identity))


def test_the_uniform_weak_form_is_untouched() -> None:
    """v0.38c is a parallel path, not a replacement."""
    import pdelie.residuals.weak_1d as uniform

    assert uniform.__all__ == [
        "evaluate_weak_burgers_residual",
        "evaluate_weak_heat_residual",
    ]


def test_v0_38c_adds_no_public_surface_to_the_residuals_package() -> None:
    """The M3 guard freezes ``pdelie.residuals.__all__`` at eight names.

    v0.38c honours it rather than widening it: everything here is imported from
    ``pdelie.residuals.irregular_weak`` directly. Re-exporting would have been
    convenient and would have made a milestone-scope guard fail for a reason
    that guard was right about -- the residuals surface is deliberately small.
    """
    import pdelie
    import pdelie.residuals as package

    assert len(package.__all__) == 8
    for name in (
        "WeakWindow",
        "QUADRATURE_RULES",
        "nonuniform_trapezoidal_weights",
        "validate_quadrature_weights",
        "weak_window_overlap_fraction",
    ):
        assert name not in package.__all__
        assert name not in pdelie.__all__


def test_the_payloads_are_strict_json() -> None:
    x = _irregular(12)
    json.dumps(_window().as_dict(), allow_nan=False)
    json.dumps(
        validate_quadrature_weights(nonuniform_trapezoidal_weights(x), x, rule=_RULE),
        allow_nan=False,
    )
