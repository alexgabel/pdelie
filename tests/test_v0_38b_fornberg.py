"""v0.38b: FN-1 .. FN-17, and the thresholds the pilot measured.

Rules frozen in ``docs/design/v0_38b_hypothesis_freeze.md``; the threshold values
and the evidence behind them are in ``docs/design/v0_38b_pilot_report.md``.
"""

from __future__ import annotations

import inspect
import json

import numpy as np
import pytest

from pdelie.design.lineage import DesignRowLineage
from pdelie.design.row_mask import EXCLUSION_REASONS, build_row_mask
from pdelie.differentiation.fornberg import (
    G5_SPACING_RATIO_THRESHOLD,
    MAX_STENCIL_SIZE,
    classify_coordinate_defect,
    classify_row_exclusions,
    describe_grid_regularity,
    fornberg_weights,
    validate_coordinates,
)
from pdelie.errors import ScopeValidationError

_IRREGULAR = np.array([0.0, 0.31, 1.07, 1.13, 2.71, 4.02])


# --------------------------------------------------------------------------
# FN-1, FN-4 -- the weights are right
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("order", "expected"),
    [
        (1, [1 / 12, -2 / 3, 0.0, 2 / 3, -1 / 12]),
        (2, [-1 / 12, 4 / 3, -5 / 2, 4 / 3, -1 / 12]),
    ],
)
def test_fn1_uniform_weights_match_the_textbook_stencils(
    order: int, expected: list[float]
) -> None:
    """A known-answer check the recursion cannot pass by accident."""
    weights = fornberg_weights(np.arange(-2.0, 3.0), 0.0, order)
    assert np.allclose(weights.weights, expected, atol=1e-14)


@pytest.mark.parametrize("order", [1, 2, 3])
def test_fn4_weights_sum_to_zero_for_every_derivative_order(order: int) -> None:
    """A derivative of a constant is zero, so the weights must annihilate it."""
    weights = fornberg_weights(_IRREGULAR, 2.0, order)
    assert abs(float(np.sum(weights.weights))) < 1e-12


# --------------------------------------------------------------------------
# FN-2, FN-3 -- accuracy derived, undersized stencil refused
# --------------------------------------------------------------------------


def test_fn2_formal_accuracy_is_derived_from_the_stencil_used() -> None:
    weights = fornberg_weights(_IRREGULAR, 2.0, 2)
    assert weights.formal_accuracy == weights.stencil_size - weights.derivative_order == 4


def test_fn2_no_parameter_can_assert_the_accuracy() -> None:
    """Absence is checked, not merely unwritten."""
    parameters = inspect.signature(fornberg_weights).parameters
    assert "formal_accuracy" not in parameters
    assert "accuracy" not in parameters


def test_fn3_a_stencil_too_small_for_the_order_is_refused() -> None:
    """Returning weights anyway looks like an answer and has no accuracy at all."""
    with pytest.raises(ScopeValidationError, match="cannot determine derivative order"):
        fornberg_weights(np.array([0.0, 1.0]), 0.5, 2)


def test_fn5_the_evaluation_point_need_not_be_a_node() -> None:
    off_node = fornberg_weights(_IRREGULAR, 1.6, 1)
    on_node = fornberg_weights(_IRREGULAR, 1.07, 1)
    assert off_node.evaluated_at_node is False
    assert on_node.evaluated_at_node is True


# --------------------------------------------------------------------------
# FN-6 .. FN-9 -- degenerate grids refused, never repaired
# --------------------------------------------------------------------------


def test_fn6_duplicate_coordinates_are_refused_not_deduplicated() -> None:
    with pytest.raises(ScopeValidationError, match="refused, not"):
        validate_coordinates(np.array([0.0, 1.0, 1.0, 2.0]))


def test_fn7_unsorted_coordinates_are_refused_not_sorted() -> None:
    with pytest.raises(ScopeValidationError, match="rather than sorted"):
        validate_coordinates(np.array([0.0, 2.0, 1.0, 3.0]))


def test_fn8_non_finite_coordinates_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="non-finite"):
        validate_coordinates(np.array([0.0, np.nan, 2.0]))


def test_fn9_a_single_point_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="no spacing"):
        validate_coordinates(np.array([1.0]))


def test_a_repaired_grid_is_never_returned() -> None:
    """The returned array must be the input, not a fixed-up version of it."""
    original = np.array([0.0, 0.5, 1.7, 3.0])
    assert np.array_equal(validate_coordinates(original), original)


# --------------------------------------------------------------------------
# FN-10, FN-12 -- the regularity diagnostic
# --------------------------------------------------------------------------


def test_fn10_the_ratio_is_scale_free() -> None:
    """The same grid in metres and kilometres must report the same number."""
    metres = describe_grid_regularity(_IRREGULAR)
    kilometres = describe_grid_regularity(_IRREGULAR * 1000.0)
    assert metres.spacing_ratio == pytest.approx(kilometres.spacing_ratio)


@pytest.mark.parametrize("count", [8, 33, 129, 1024, 4096])
def test_fn12_a_uniform_grid_reads_uniform_at_every_size(count: int) -> None:
    """Amended after pilot run 1 blocked on requiring exactly 1.0."""
    regularity = describe_grid_regularity(np.linspace(0.0, 2.0 * np.pi, count, endpoint=False))
    assert regularity.is_uniform, (
        f"n={count}: ratio-1 = {regularity.spacing_ratio - 1:.3e} against a "
        f"tolerance of {count * np.finfo(float).eps:.3e}"
    )


def test_fn12_the_tolerance_does_not_swallow_real_non_uniformity() -> None:
    """Seven orders of margin, measured. A loose bound would be worse than none."""
    perturbed = np.linspace(0.0, 1.0, 129)
    perturbed[64] += 1e-9
    regularity = describe_grid_regularity(perturbed)
    assert not regularity.is_uniform
    assert regularity.spacing_ratio - 1.0 > 1e3 * (129 * np.finfo(float).eps)


# --------------------------------------------------------------------------
# The piloted thresholds
# --------------------------------------------------------------------------


def test_the_g5_verdict_is_a_report_not_a_refusal() -> None:
    """The pilot found no ratio at which differentiation became unusable."""
    strongly = np.array([0.0, 1.0, 1.01, 30.0])
    regularity = describe_grid_regularity(strongly)
    assert regularity.g5_verdict == "strongly_non_uniform"
    # And it still computes, because G-5 reports rather than refuses.
    weights = fornberg_weights(strongly, 1.0, 1)
    assert np.isfinite(weights.weights).all()


def test_the_g5_threshold_matches_the_pilot_report() -> None:
    """The value and its evidence must not drift apart."""
    from pathlib import Path

    report = (
        Path(__file__).resolve().parents[1] / "docs/design/v0_38b_pilot_report.md"
    ).read_text()
    # Both values must appear as the report's frozen figures. Checked against
    # the constants rather than against literals, so changing one without
    # re-piloting fails here instead of leaving the evidence describing a value
    # the code no longer uses.
    assert f"Frozen value: `{G5_SPACING_RATIO_THRESHOLD}`" in report, (
        f"the pilot report does not record G-5 = {G5_SPACING_RATIO_THRESHOLD}"
    )
    assert f"Frozen cap: `{MAX_STENCIL_SIZE}`" in report, (
        f"the pilot report does not record the cap = {MAX_STENCIL_SIZE}"
    )


def test_a_stencil_over_the_cap_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="exceeds the cap"):
        fornberg_weights(np.arange(float(MAX_STENCIL_SIZE + 1)), 5.0, 1)


def test_a_stencil_at_the_cap_is_allowed() -> None:
    weights = fornberg_weights(np.arange(float(MAX_STENCIL_SIZE)), 6.0, 1)
    assert weights.stencil_size == MAX_STENCIL_SIZE


# --------------------------------------------------------------------------
# FN-13 .. FN-15 -- the four owed producers
# --------------------------------------------------------------------------


def test_fn13_stencil_does_not_fit_is_produced_at_the_boundaries() -> None:
    exclusions = classify_row_exclusions(
        np.linspace(0.0, 1.0, 9), stencil_size=5, derivative_order=2
    )
    assert set(exclusions) == {0, 1, 7, 8}
    assert set(exclusions.values()) == {"stencil_does_not_fit"}


def test_fn13_a_one_sided_stencil_is_not_silently_substituted() -> None:
    """Substituting one would make formal_accuracy wrong for those rows."""
    exclusions = classify_row_exclusions(
        np.linspace(0.0, 1.0, 9), stencil_size=5, derivative_order=2
    )
    assert 0 in exclusions, "the first row must be excluded, not given a one-sided formula"


def test_fn15_derivative_unavailable_is_produced() -> None:
    exclusions = classify_row_exclusions(
        np.linspace(0.0, 1.0, 9),
        stencil_size=5,
        derivative_order=2,
        required_derivatives=("u_xx",),
        computed_derivatives=(),
    )
    assert set(exclusions.values()) == {"derivative_unavailable"}


def test_fn14_coordinate_defects_are_named() -> None:
    assert classify_coordinate_defect(np.array([0.0, 1.0, 1.0])) == "duplicate_coordinate"
    assert classify_coordinate_defect(np.array([0.0])) == "coordinate_missing"
    assert classify_coordinate_defect(np.array([0.0, np.inf])) == "coordinate_missing"
    assert classify_coordinate_defect(np.linspace(0.0, 1.0, 5)) is None


def test_v0_38b_closes_the_producer_gap_v0_38a_recorded() -> None:
    """v0.38a shipped five reasons and produced none. Four are now produced."""
    produced = set()
    produced.update(
        classify_row_exclusions(
            np.linspace(0.0, 1.0, 9), stencil_size=5, derivative_order=2
        ).values()
    )
    produced.update(
        classify_row_exclusions(
            np.linspace(0.0, 1.0, 9),
            stencil_size=5,
            derivative_order=2,
            required_derivatives=("u_xx",),
            computed_derivatives=(),
        ).values()
    )
    for coordinates in (np.array([0.0, 1.0, 1.0]), np.array([0.0])):
        defect = classify_coordinate_defect(coordinates)
        if defect is not None:
            produced.add(defect)

    assert produced == set(EXCLUSION_REASONS) - {"observation_masked"}, (
        f"v0.38b owes four producers; it produces {sorted(produced)}. "
        f"observation_masked comes from the upstream field mask, not from here."
    )


def test_the_producers_feed_a_real_row_mask() -> None:
    """End to end: exclusions from this layer build a v0.38a mask."""
    coordinates = np.linspace(0.0, 1.0, 9)
    lineages = [
        DesignRowLineage(
            trajectory_id="t", source_coordinate_id=f"x_{i}", mask_id="upstream"
        )
        for i in range(coordinates.size)
    ]
    mask = build_row_mask(
        lineages,
        classify_row_exclusions(coordinates, stencil_size=5, derivative_order=2),
        required_derivatives=("u_xx",),
        computed_derivatives=("u_t", "u_x", "u_xx"),
        mask_id="v0_38b",
    )
    assert len(mask.included) == 5
    assert mask.reason_counts()["stencil_does_not_fit"] == 4
    assert mask.full_field_derivatives_available is True
    json.dumps(mask.as_dict(), allow_nan=False)


# --------------------------------------------------------------------------
# Payload
# --------------------------------------------------------------------------


def test_the_payloads_are_strict_json() -> None:
    json.dumps(describe_grid_regularity(_IRREGULAR).as_dict(), allow_nan=False)
    json.dumps(fornberg_weights(_IRREGULAR, 1.6, 2).as_dict(), allow_nan=False)
