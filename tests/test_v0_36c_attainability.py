"""v0.36c: the attainability report and its paired statistics."""

from __future__ import annotations

import json
import re

import numpy as np
import pytest

from pdelie.artifact import ArtifactRef, content_artifact_id
from pdelie.design import (
    DesignBudget,
    DesignCandidateRecord,
    attainability_report,
    paired_bootstrap_interval,
    qr_pivot_selection_comparator,
    random_budget_matched_design,
    raw_local_design,
)
from pdelie.errors import ScopeValidationError, ShapeValidationError

SEEDS = ["s0", "s1", "s2", "s3", "s4", "s5"]
ACCESS = {
    "uses_true_support": False, "uses_true_coefficients": False,
    "requires_full_domain": False, "requires_unobserved_rows": False,
    "requires_heldout_data": False, "uses_future_time": False,
}


def budget(**overrides) -> DesignBudget:
    base = {
        "budget_value": 5.0, "budget_unit": "rows", "num_views": 1,
        "allocation_policy": "uniform", "grouping_policy": "by_trajectory",
        "duplicate_policy": "retain", "row_weight_policy": "unit", "train_only": True,
    }
    base.update(overrides)
    return DesignBudget(**base)


def matrix() -> np.ndarray:
    return np.random.default_rng(20360).standard_normal((12, 4))


def candidates() -> list[DesignCandidateRecord]:
    m, b = matrix(), budget()
    return [
        raw_local_design(m, 5, budget=b, design_id="reference"),
        qr_pivot_selection_comparator(m, 5, budget=b, design_id="qr"),
        random_budget_matched_design(m, 5, budget=b, seed=1, design_id="random"),
    ]


def metrics(**overrides) -> dict:
    base = {
        "reference": [1.0, 1.1, 0.9, 1.05, 0.95, 1.0],
        "qr": [0.6, 0.65, 0.55, 0.62, 0.58, 0.6],
        "random": [1.2, 1.3, 1.1, 1.25, 1.15, 1.2],
    }
    base.update(overrides)
    return base


# --- report shape -----------------------------------------------------------


def test_report_is_strict_json_and_carries_the_summary_type() -> None:
    report = attainability_report(
        candidates(), reference_design_id="reference",
        downstream_metrics=metrics(), seed_ids=SEEDS,
    )
    encoded = json.dumps(report, allow_nan=False)
    assert "NaN" not in encoded and "Infinity" not in encoded
    assert report["summary_type"] == "pdelie_attainable_design_comparison"
    assert report["diagnostic_only"] is True


def test_no_report_contains_the_unqualified_word_oracle() -> None:
    report = attainability_report(
        candidates(), reference_design_id="reference",
        downstream_metrics=metrics(), seed_ids=SEEDS,
    )
    assert not re.search(r"\boracle\b", json.dumps(report))


def test_every_candidate_declares_six_access_flags_in_the_report() -> None:
    """The c-gate: all(len(c.information_access) >= 6 for c in candidates)."""
    report = attainability_report(
        candidates(), reference_design_id="reference",
        downstream_metrics=metrics(), seed_ids=SEEDS,
    )
    for entry in report["candidates"]:
        assert len(entry["information_access"]) >= 6


def test_paired_deltas_use_the_same_seed_ids_on_both_sides() -> None:
    """The c-gate: pair['seed_ids_A'] == pair['seed_ids_B'].

    Pairing is what removes the seed's own effect on the problem; unequal seed
    lists would silently turn a paired interval into an unpaired one.
    """
    report = attainability_report(
        candidates(), reference_design_id="reference",
        downstream_metrics=metrics(), seed_ids=SEEDS,
    )
    assert report["paired_deltas"]
    for pair in report["paired_deltas"]:
        assert pair["seed_ids_a"] == pair["seed_ids_b"] == SEEDS


def test_failed_run_count_matches_the_none_entries() -> None:
    """The c-gate: report['failed_run_count'] == sum(1 for m in metrics if m is None)."""
    supplied = metrics(qr=[0.6, None, 0.55, None, 0.58, 0.6])
    report = attainability_report(
        candidates(), reference_design_id="reference",
        downstream_metrics=supplied, seed_ids=SEEDS,
    )
    expected = sum(
        1 for values in supplied.values() if values is not None
        for value in values if value is None
    )
    assert report["failed_run_count"] == expected == 2


def test_a_design_that_never_ran_is_distinct_from_one_that_failed() -> None:
    report = attainability_report(
        candidates(), reference_design_id="reference",
        downstream_metrics=metrics(random=None), seed_ids=SEEDS,
    )
    assert report["designs_that_never_ran"] == ["random"]
    entry = next(p for p in report["paired_deltas"] if p["design_id"] == "random")
    assert entry["interval"]["interval_available"] is False


# --- budget fairness --------------------------------------------------------


def test_matched_budgets_produce_no_incomparable_pairs() -> None:
    report = attainability_report(
        candidates(), reference_design_id="reference",
        downstream_metrics=metrics(), seed_ids=SEEDS,
    )
    assert report["budget_incomparable_pairs"] == []
    assert all(pair["budget_fair"] for pair in report["paired_deltas"])


def test_a_mismatched_budget_is_flagged_but_its_delta_still_reported() -> None:
    """Suppressing the delta would hide information; presenting it as a
    like-for-like win would be worse."""
    m = matrix()
    records = [
        raw_local_design(m, 5, budget=budget(), design_id="reference"),
        qr_pivot_selection_comparator(
            m, 5, budget=budget(budget_unit="unique_rows"), design_id="qr"
        ),
    ]
    report = attainability_report(
        records, reference_design_id="reference",
        downstream_metrics={"reference": metrics()["reference"], "qr": metrics()["qr"]},
        seed_ids=SEEDS,
    )
    assert len(report["budget_incomparable_pairs"]) == 1
    entry = report["budget_incomparable_pairs"][0]
    assert entry["differing_budget_fields"] == ["budget_unit"]
    assert entry["delta_still_reported_but_not_budget_fair"] is True
    assert entry["mean_difference"] is not None
    assert next(p for p in report["paired_deltas"] if p["design_id"] == "qr")["budget_fair"] is False


def test_incomparable_entries_carry_every_required_field() -> None:
    m = matrix()
    records = [
        raw_local_design(m, 5, budget=budget(), design_id="reference"),
        qr_pivot_selection_comparator(m, 5, budget=budget(num_views=3), design_id="qr"),
    ]
    report = attainability_report(
        records, reference_design_id="reference",
        downstream_metrics={"reference": metrics()["reference"], "qr": metrics()["qr"]},
        seed_ids=SEEDS,
    )
    for entry in report["budget_incomparable_pairs"]:
        assert {"designs", "reason", "differing_budget_fields",
                "delta_still_reported_but_not_budget_fair", "mean_difference"} <= set(entry)


# --- statistics -------------------------------------------------------------


def test_paired_bootstrap_reproduces_byte_identically_under_a_fixed_seed() -> None:
    kwargs = {"seed_ids": SEEDS, "n_resamples": 500, "interval_level": 0.95,
              "resampling_unit": "seed", "seed": 11}
    first = paired_bootstrap_interval(metrics()["qr"], metrics()["reference"], **kwargs)
    second = paired_bootstrap_interval(metrics()["qr"], metrics()["reference"], **kwargs)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_row_level_resampling_is_refused() -> None:
    """Rows of a PDE design matrix are adjacent samples of a continuous field."""
    with pytest.raises(ScopeValidationError, match="Row-level resampling is not offered"):
        paired_bootstrap_interval(
            metrics()["qr"], metrics()["reference"], seed_ids=SEEDS,
            n_resamples=10, interval_level=0.95, resampling_unit="row", seed=1,
        )


def test_a_consistent_difference_gives_an_interval_excluding_zero() -> None:
    """Sanity: the statistic must respond to the data."""
    result = paired_bootstrap_interval(
        metrics()["qr"], metrics()["reference"], seed_ids=SEEDS,
        n_resamples=2000, interval_level=0.95, resampling_unit="seed", seed=3,
    )
    assert result["interval_available"] is True
    assert result["mean_difference"] < 0
    assert result["excludes_zero"] is True
    assert result["lower"] <= result["mean_difference"] <= result["upper"]


def test_pairs_where_either_side_failed_are_excluded_and_counted() -> None:
    result = paired_bootstrap_interval(
        [0.6, None, 0.55, 0.62, None, 0.6], metrics()["reference"],
        seed_ids=SEEDS, n_resamples=200, interval_level=0.95,
        resampling_unit="seed", seed=3,
    )
    assert result["paired_count"] == 4
    assert result["failed_pair_count"] == 2
    assert result["paired_seed_ids"] == ["s0", "s2", "s3", "s5"]


def test_no_usable_pair_reports_unavailable_rather_than_guessing() -> None:
    result = paired_bootstrap_interval(
        [None] * 6, metrics()["reference"], seed_ids=SEEDS,
        n_resamples=10, interval_level=0.95, resampling_unit="seed", seed=1,
    )
    assert result["interval_available"] is False
    assert result["lower"] is None and result["upper"] is None


def test_nan_metrics_are_refused_because_they_propagate_silently() -> None:
    with pytest.raises(ScopeValidationError, match="A failed run is None, not NaN"):
        paired_bootstrap_interval(
            [float("nan")] * 6, metrics()["reference"], seed_ids=SEEDS,
            n_resamples=10, interval_level=0.95, resampling_unit="seed", seed=1,
        )


def test_metric_length_must_match_seed_ids() -> None:
    with pytest.raises(ShapeValidationError, match="positional against seed_ids"):
        paired_bootstrap_interval(
            [0.5], metrics()["reference"], seed_ids=SEEDS,
            n_resamples=10, interval_level=0.95, resampling_unit="seed", seed=1,
        )


def test_interval_level_and_seed_are_validated() -> None:
    common = {"seed_ids": SEEDS, "n_resamples": 10, "resampling_unit": "seed"}
    with pytest.raises(ScopeValidationError, match="strictly between 0 and 1"):
        paired_bootstrap_interval(metrics()["qr"], metrics()["reference"],
                                  interval_level=1.5, seed=1, **common)
    with pytest.raises(ScopeValidationError, match="seed must be an integer"):
        paired_bootstrap_interval(metrics()["qr"], metrics()["reference"],
                                  interval_level=0.95, seed="1", **common)


# --- validation and integration ---------------------------------------------


def test_unknown_reference_and_missing_metrics_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="is not among the candidates"):
        attainability_report(candidates(), reference_design_id="ghost",
                             downstream_metrics=metrics(), seed_ids=SEEDS)
    with pytest.raises(ScopeValidationError, match="pass None to say it never ran"):
        attainability_report(candidates(), reference_design_id="reference",
                             downstream_metrics={"reference": metrics()["reference"]},
                             seed_ids=SEEDS)


def test_duplicate_design_ids_are_refused() -> None:
    m, b = matrix(), budget()
    duplicated = [raw_local_design(m, 5, budget=b, design_id="same"),
                  qr_pivot_selection_comparator(m, 5, budget=b, design_id="same")]
    with pytest.raises(ScopeValidationError, match="repeat design_id"):
        attainability_report(duplicated, reference_design_id="same",
                             downstream_metrics={"same": metrics()["qr"]}, seed_ids=SEEDS)


def test_a_sparse_recovery_report_can_be_referenced_by_artifact_id() -> None:
    """Integration with v0.36d: the report is referenced, not embedded."""
    ref = ArtifactRef(
        artifact_id=content_artifact_id(b"a sparse recovery report"),
        artifact_kind="pdelie_sparse_recovery_assumption_report",
        schema_version="0.1", producer_stage_id="sparse_recovery", byte_count=24,
    )
    report = attainability_report(
        candidates(), reference_design_id="reference", downstream_metrics=metrics(),
        seed_ids=SEEDS, sparse_recovery_report_artifact=ref,
    )
    assert report["sparse_recovery_report_artifact_id"] == ref.artifact_id
    with pytest.raises(ScopeValidationError, match="ArtifactRef or None"):
        attainability_report(candidates(), reference_design_id="reference",
                             downstream_metrics=metrics(), seed_ids=SEEDS,
                             sparse_recovery_report_artifact="an-id")
