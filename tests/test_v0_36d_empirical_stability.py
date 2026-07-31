"""v0.36d: empirical support stability.

Deliberately a separate file from the assumption report, mirroring the fact that
they are separate claims. Selection frequency is not evidence that a theoretical
condition holds.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie.diagnostics.sparse_recovery import (
    RESAMPLING_UNITS,
    empirical_support_stability_report,
)
from pdelie.errors import ScopeValidationError, ShapeValidationError


def fixture_problem(n_rows: int = 24, n_features: int = 4) -> tuple[np.ndarray, np.ndarray, list[str]]:
    rng = np.random.default_rng(20360)
    matrix = rng.standard_normal((n_rows, n_features))
    # Features 0 and 2 carry the signal; 1 and 3 are noise.
    target = 3.0 * matrix[:, 0] - 2.0 * matrix[:, 2] + 0.01 * rng.standard_normal(n_rows)
    trajectories = [f"traj_{index % 6}" for index in range(n_rows)]
    return matrix, target, trajectories


def top_two_by_correlation(matrix: np.ndarray, target: np.ndarray) -> list[int]:
    """A deterministic stand-in selection method."""
    scores = np.abs(matrix.T @ target)
    return sorted(np.argsort(scores)[::-1][:2].tolist())


def run(**overrides: object) -> dict:
    matrix, target, trajectories = fixture_problem()
    kwargs = {
        "seed": 7,
        "n_resamples": 24,
        "resampling_unit": "trajectory",
        "selection_method": top_two_by_correlation,
        "trajectory_ids": trajectories,
    }
    kwargs.update(overrides)
    return empirical_support_stability_report(matrix, target, **kwargs)  # type: ignore[arg-type]


# --- the refusal that matters -----------------------------------------------


def test_row_level_resampling_is_refused_with_a_typed_error() -> None:
    """Rows of a PDE design matrix are adjacent samples of a continuous field.

    Resampling them independently destroys the correlation structure that makes
    the design what it is.
    """
    with pytest.raises(ScopeValidationError, match="correlation structure"):
        run(resampling_unit="row")


def test_row_is_not_in_the_offered_vocabulary() -> None:
    assert "row" not in RESAMPLING_UNITS
    assert set(RESAMPLING_UNITS) == {"trajectory", "complementary_pair"}


# --- determinism ------------------------------------------------------------


@pytest.mark.parametrize("unit", RESAMPLING_UNITS)
def test_fixed_seed_reproduces_the_report_exactly(unit: str) -> None:
    first = run(resampling_unit=unit)
    second = run(resampling_unit=unit)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_different_seeds_may_differ() -> None:
    """A report identical across every seed would not be measuring resampling."""
    reports = {json.dumps(run(seed=seed), sort_keys=True) for seed in range(6)}
    assert len(reports) > 1


def test_seed_must_be_an_integer() -> None:
    for bad in (None, "7", 7.0, True):
        with pytest.raises(ScopeValidationError, match="seed must be an integer"):
            run(seed=bad)


# --- report content ---------------------------------------------------------


def test_frequencies_are_reported_per_feature_and_per_support() -> None:
    report = run()
    frequencies = report["selection_frequency_by_feature"]
    assert set(frequencies) == {"0", "1", "2", "3"}
    assert all(0.0 <= value <= 1.0 for value in frequencies.values())
    assert sum(report["support_frequency"].values()) == pytest.approx(1.0, rel=1e-9)


def test_the_signal_features_are_selected_more_often_than_the_noise_ones() -> None:
    """Sanity: the report must respond to the data, not return a constant."""
    report = run()
    frequencies = report["selection_frequency_by_feature"]
    assert frequencies["0"] > frequencies["1"]
    assert frequencies["2"] > frequencies["3"]
    assert report["most_frequent_support"] == [0, 2]


def test_report_is_strict_json_and_marked_empirical() -> None:
    report = run()
    encoded = json.dumps(report, allow_nan=False)
    assert "NaN" not in encoded and "Infinity" not in encoded
    assert report["summary_type"] == "pdelie_empirical_support_stability_report"
    assert report["is_theoretical_assumption_report"] is False
    assert report["diagnostic_only"] is True


def test_it_is_a_separate_report_from_the_assumption_one() -> None:
    """Selection frequency is not evidence that a theoretical condition holds."""
    from pdelie.diagnostics.sparse_recovery import sparse_recovery_assumption_report

    empirical = run()
    theoretical = sparse_recovery_assumption_report(
        np.eye(4), candidate_supports=[[0, 1]]
    )
    assert empirical["summary_type"] != theoretical["summary_type"]
    assert "rho_uniform" not in empirical
    assert "selection_frequency_by_feature" not in theoretical


# --- validation -------------------------------------------------------------


def test_mismatched_target_or_trajectory_length_is_refused() -> None:
    matrix, target, trajectories = fixture_problem()
    with pytest.raises(ShapeValidationError, match="target has"):
        empirical_support_stability_report(
            matrix, target[:-1], seed=1, n_resamples=2,
            resampling_unit="trajectory", selection_method=top_two_by_correlation,
            trajectory_ids=trajectories,
        )
    with pytest.raises(ShapeValidationError, match="trajectory_ids has"):
        empirical_support_stability_report(
            matrix, target, seed=1, n_resamples=2,
            resampling_unit="trajectory", selection_method=top_two_by_correlation,
            trajectory_ids=trajectories[:-1],
        )


def test_single_group_trajectory_resampling_is_refused() -> None:
    """With one group every resample is the whole dataset, which measures nothing."""
    matrix, target, _ = fixture_problem()
    with pytest.raises(ScopeValidationError, match="at least two distinct"):
        empirical_support_stability_report(
            matrix, target, seed=1, n_resamples=2,
            resampling_unit="trajectory", selection_method=top_two_by_correlation,
            trajectory_ids=["only"] * matrix.shape[0],
        )


def test_non_positive_resample_count_and_non_callable_method_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="at least 1"):
        run(n_resamples=0)
    with pytest.raises(ScopeValidationError, match="must be an integer"):
        run(n_resamples=2.5)
    with pytest.raises(ScopeValidationError, match="must be callable"):
        run(selection_method="argmax")


def test_out_of_range_selection_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="outside"):
        run(selection_method=lambda matrix, target: [0, 99])


def test_non_finite_target_is_refused() -> None:
    matrix, target, trajectories = fixture_problem()
    target[0] = np.inf
    with pytest.raises(ScopeValidationError, match="finite"):
        empirical_support_stability_report(
            matrix, target, seed=1, n_resamples=2,
            resampling_unit="trajectory", selection_method=top_two_by_correlation,
            trajectory_ids=trajectories,
        )


def test_default_trajectory_ids_treat_each_row_as_its_own_group() -> None:
    matrix, target, _ = fixture_problem()
    report = empirical_support_stability_report(
        matrix, target, seed=3, n_resamples=4,
        resampling_unit="trajectory", selection_method=top_two_by_correlation,
    )
    assert report["group_count"] == matrix.shape[0]
