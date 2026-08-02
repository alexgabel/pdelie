"""v0.38 §8: periodicity is checked at three layers, and C-4 fails the right one.

The point of the layering is that C-4 passed the structural check. Every gate
agreed the domain was periodic while the profile was ``tanh``. These tests
reconstruct that situation and assert the values layer catches it.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie.contracts.periodicity_validation import (
    ANALYTICAL_PERIODICITY_STATUSES,
    PERIODIC_FORM_CLASSIFICATION,
    WRAP_CONSISTENCY_STATUSES,
    PeriodicityValidation,
    classify_analytical_periodicity,
    validate_periodicity,
)
from pdelie.errors import ScopeValidationError

_X = np.linspace(0.0, 2.0 * np.pi, 64, endpoint=False)


def _sinusoidal() -> np.ndarray:
    return 0.1 * (1.0 + 0.5 * np.sin(2.0 * _X))


def _tanh() -> np.ndarray:
    """C-4's *form* -- tanh on a periodic domain -- not C-4's exact parameters.

    C-4 measured a seam-to-interior ratio of 6.25. This fixture is steeper and
    reports a much larger one. Both are far outside any tolerance a periodic
    profile needs; the fixture is not a reproduction of that measurement and is
    not cited as one.
    """
    return np.tanh(3.0 * (_X - np.pi))


# --------------------------------------------------------------------------
# Layer 1 alone is not enough -- the whole reason for the other two
# --------------------------------------------------------------------------


def test_the_c4_profile_passes_the_structural_layer() -> None:
    """It did, in production, through a freeze and two pilots."""
    result = validate_periodicity(
        periodic_axis_declared=True, values=_tanh(), tolerance_ratio=2.0
    )
    assert result.periodic_axis_declared is True


def test_the_c4_profile_fails_the_values_layer() -> None:
    """The layer that would have caught it before the pilot did."""
    result = validate_periodicity(
        periodic_axis_declared=True, values=_tanh(), tolerance_ratio=2.0
    )
    assert result.wrap_value_consistency == "outside_tolerance"
    assert result.wrap_value_ratio is not None and result.wrap_value_ratio > 2.0


def test_the_c4_profile_is_refuted_at_the_analytical_layer() -> None:
    assert classify_analytical_periodicity({"profile_id": "monotone_smooth"}) == "refuted"


def test_a_declaration_does_not_pass_on_metadata_alone() -> None:
    """The rule, stated as an assertion.

    Declaring a periodic axis over a nonperiodic profile must not produce a
    periodic verdict at any layer but the structural one.
    """
    result = validate_periodicity(
        periodic_axis_declared=True,
        values=_tanh(),
        analytical_spec={"profile_id": "monotone_smooth"},
        tolerance_ratio=2.0,
    )
    assert result.periodic_axis_declared is True
    assert not result.is_periodic_at_every_layer


# --------------------------------------------------------------------------
# A genuinely periodic profile passes all three
# --------------------------------------------------------------------------


def test_a_sinusoidal_profile_passes_every_layer() -> None:
    result = validate_periodicity(
        periodic_axis_declared=True,
        values=_sinusoidal(),
        analytical_spec={"profile_id": "sinusoidal"},
        tolerance_ratio=2.0,
    )
    assert result.is_periodic_at_every_layer
    assert result.wrap_value_consistency == "within_tolerance"
    assert result.wrap_derivative_consistency == "within_tolerance"
    assert result.analytical_periodicity == "confirmed"


def test_the_two_profiles_are_separated_by_the_values_ratio() -> None:
    """Quantified, so the layer is known to discriminate rather than assumed to."""
    periodic = validate_periodicity(
        periodic_axis_declared=True, values=_sinusoidal(), tolerance_ratio=2.0
    )
    nonperiodic = validate_periodicity(
        periodic_axis_declared=True, values=_tanh(), tolerance_ratio=2.0
    )
    assert periodic.wrap_value_ratio is not None
    assert nonperiodic.wrap_value_ratio is not None
    assert nonperiodic.wrap_value_ratio > 5.0 * periodic.wrap_value_ratio, (
        f"seam ratios {periodic.wrap_value_ratio:.3f} (sinusoidal) and "
        f"{nonperiodic.wrap_value_ratio:.3f} (tanh) are too close for this layer "
        f"to discriminate"
    )


def test_a_profile_that_joins_in_value_but_kinks_is_caught_by_the_derivative_layer() -> None:
    """The case that justifies a separate derivative layer.

    ``|sin x|`` meets itself exactly at the wrap -- the value layer sees nothing
    wrong -- and has a corner there. "Smooth across the seam" is a claim about
    the slope, so a values-only check would pass a profile that is continuous
    and not smooth.
    """
    kinked = np.abs(np.sin(_X))
    result = validate_periodicity(
        periodic_axis_declared=True, values=kinked, tolerance_ratio=2.0
    )
    assert result.wrap_value_consistency == "within_tolerance", (
        "premise: this profile does join in value, or it demonstrates nothing "
        "the tanh case does not already"
    )
    assert result.wrap_derivative_consistency == "outside_tolerance"
    assert not result.is_periodic_at_every_layer


def test_the_c4_historical_ratio_is_quoted_accurately() -> None:
    """Guard a number the module cites, against the source it came from.

    C-4's seam step was 1.9998 against a typical interior step of 0.3198. The
    quotient is what the docstring quotes; the tanh fixture here is steeper and
    must not be mistaken for that measurement.
    """
    from pdelie.contracts import periodicity_validation

    assert abs(1.9998 / 0.3198 - 6.25) < 0.01
    assert "6.25" in periodicity_validation.validate_periodicity.__doc__


# --------------------------------------------------------------------------
# not_evaluated is not a pass
# --------------------------------------------------------------------------


def test_omitting_values_reports_not_evaluated_rather_than_passing() -> None:
    result = validate_periodicity(periodic_axis_declared=True)
    assert result.wrap_value_consistency == "not_evaluated"
    assert result.wrap_derivative_consistency == "not_evaluated"
    assert not result.is_periodic_at_every_layer, (
        "a check that did not run must not satisfy the all-layers property"
    )


def test_undetermined_is_not_confirmed() -> None:
    """An unrecognised form is an absence of evidence, not evidence."""
    result = validate_periodicity(
        periodic_axis_declared=True,
        values=_sinusoidal(),
        analytical_spec={"profile_id": "a_form_nobody_classified"},
        tolerance_ratio=2.0,
    )
    assert result.analytical_periodicity == "undetermined"
    assert not result.is_periodic_at_every_layer


def test_an_unlisted_profile_is_never_assumed_periodic() -> None:
    assert classify_analytical_periodicity({"profile_id": "brand_new"}) == "undetermined"
    assert classify_analytical_periodicity(None) == "not_declared"
    assert classify_analytical_periodicity({}) == "undetermined"


# --------------------------------------------------------------------------
# The tolerance is declared, never defaulted
# --------------------------------------------------------------------------


def test_values_without_a_tolerance_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="tolerance_ratio is required"):
        validate_periodicity(periodic_axis_declared=True, values=_sinusoidal())


@pytest.mark.parametrize("bad", [0.0, -1.0, float("inf"), float("nan")])
def test_a_nonpositive_or_nonfinite_tolerance_is_refused(bad: float) -> None:
    with pytest.raises(ScopeValidationError, match="finite and positive"):
        validate_periodicity(
            periodic_axis_declared=True, values=_sinusoidal(), tolerance_ratio=bad
        )


def test_too_few_samples_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="at least four samples"):
        validate_periodicity(
            periodic_axis_declared=True,
            values=np.array([1.0, 2.0]),
            tolerance_ratio=2.0,
        )


def test_non_finite_values_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="non-finite"):
        validate_periodicity(
            periodic_axis_declared=True,
            values=np.array([1.0, np.nan, 2.0, 3.0]),
            tolerance_ratio=2.0,
        )


# --------------------------------------------------------------------------
# Scale-freedom and the constant edge case
# --------------------------------------------------------------------------


def test_the_values_layer_is_scale_free() -> None:
    """Rescaling the profile must not change the verdict.

    An absolute threshold would classify the same profile differently in metres
    and in kilometres.
    """
    base = validate_periodicity(
        periodic_axis_declared=True, values=_tanh(), tolerance_ratio=2.0
    )
    scaled = validate_periodicity(
        periodic_axis_declared=True, values=1000.0 * _tanh(), tolerance_ratio=2.0
    )
    assert base.wrap_value_consistency == scaled.wrap_value_consistency
    assert base.wrap_value_ratio == pytest.approx(scaled.wrap_value_ratio)


def test_a_constant_profile_wraps_trivially() -> None:
    result = validate_periodicity(
        periodic_axis_declared=True,
        values=np.full(32, 0.1),
        analytical_spec={"profile_id": "constant"},
        tolerance_ratio=2.0,
    )
    assert result.wrap_value_ratio == 0.0
    assert result.is_periodic_at_every_layer


def test_a_constant_profile_with_one_seam_step_is_caught() -> None:
    """Zero interior variation must not make any seam acceptable."""
    values = np.full(32, 0.1)
    values[-1] = 0.9
    result = validate_periodicity(
        periodic_axis_declared=True, values=values, tolerance_ratio=2.0
    )
    assert result.wrap_value_consistency == "outside_tolerance"


# --------------------------------------------------------------------------
# Payload
# --------------------------------------------------------------------------


def test_the_payload_carries_all_four_layers_and_is_strict_json() -> None:
    result = validate_periodicity(
        periodic_axis_declared=True,
        values=_sinusoidal(),
        analytical_spec={"profile_id": "sinusoidal"},
        tolerance_ratio=2.0,
    )
    payload = result.as_dict()
    assert set(payload) == {
        "periodic_axis_declared",
        "wrap_value_consistency",
        "wrap_derivative_consistency",
        "analytical_periodicity",
        "wrap_value_ratio",
        "wrap_derivative_ratio",
        "tolerance_ratio",
    }
    json.dumps(payload, allow_nan=False)


def test_the_status_vocabularies_are_closed() -> None:
    with pytest.raises(ScopeValidationError, match="not one of"):
        PeriodicityValidation(
            periodic_axis_declared=True,
            wrap_value_consistency="probably_fine",
            wrap_derivative_consistency="within_tolerance",
            analytical_periodicity="confirmed",
            wrap_value_ratio=0.0,
            wrap_derivative_ratio=0.0,
            tolerance_ratio=2.0,
        )
    assert "not_evaluated" in WRAP_CONSISTENCY_STATUSES
    assert "undetermined" in ANALYTICAL_PERIODICITY_STATUSES


def test_the_form_classification_covers_every_shipped_profile() -> None:
    """A profile the registry ships but this table omits defaults to undetermined
    -- which is safe, but silent. Assert the two stay in step."""
    from pdelie.benchmarks.parameter_equivariant import PROFILE_REGISTRY

    missing = sorted(set(PROFILE_REGISTRY) - set(PERIODIC_FORM_CLASSIFICATION))
    assert not missing, (
        f"profiles {missing} ship but are unclassified for periodicity, so they "
        f"silently report 'undetermined'. Classify them explicitly."
    )
