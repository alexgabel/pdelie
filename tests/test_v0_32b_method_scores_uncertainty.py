"""v0.32b — strict method-score, uncertainty, and calibration reporting.

Frozen contract lives in ``docs/design/GENERATOR_CONFIDENCE_ADDITIVE_FIELDS.md``
and ``configs/planning/v0_32_method_scores_scope.json``. This module is the
external test harness the prompt calls for.

Twenty cases, grouped:

- Cases 1-3: default backward compatibility for
  :func:`summarize_generator_confidence` (no new args -> equivalent output,
  strict-JSON boundary, ``_CONFIDENCE_LABELS`` unchanged).
- Cases 4-8: ``method_scores`` shape validation.
- Cases 9-14: ``uncertainty_report`` shape validation and vocabulary.
- Case 15: ``calibration_report`` shape validation.
- Cases 16-20: end-to-end built-in coverage, bootstrap uncertainty,
  determinism, insufficient-units warning, and row-bootstrap refusal.
"""

from __future__ import annotations

import json
import math

import pytest

from pdelie.data import generate_heat_1d_field_batch
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.reporting import (
    enrich_method_scores,
    summarize_generator_confidence,
)
from pdelie.reporting.summaries import _CONFIDENCE_LABELS
from pdelie.residuals import HeatResidualEvaluator
from pdelie.symmetry import run_symmetry_method
from pdelie.symmetry.methods.polynomial_translation_svd import (
    SCORE_METADATA,
    bootstrap_uncertainty,
)

_FROZEN_SCORE_NAMES = ("span_distance", "residual_l2", "error_curve_max", "svd_condition_number")


def _make_valid_score_entry(
    value: float | None = 1.0,
    direction: str = "lower_is_better",
    description: str = "test",
    units: str | None = None,
) -> dict:
    return {
        "value": value,
        "direction": direction,
        "description": description,
        "units": units,
    }


# ---------------------------------------------------------------------------
# Cases 1-3: backward-compatible defaults + label invariant.
# ---------------------------------------------------------------------------


def test_case_01_default_call_produces_none_for_three_additive_fields() -> None:
    """No new kwargs -> method_scores/uncertainty_report/calibration_report all None."""
    summary = summarize_generator_confidence()
    assert summary["method_scores"] is None
    assert summary["uncertainty_report"] is None
    assert summary["calibration_report"] is None


def test_case_02_default_call_round_trips_strict_json() -> None:
    """Default payload round-trips through json.dumps with allow_nan=False."""
    summary = summarize_generator_confidence()
    encoded = json.dumps(summary, allow_nan=False)
    assert json.loads(encoded) == summary


def test_case_03_confidence_labels_frozen_vocabulary_unchanged() -> None:
    """The frozen four-label vocabulary is a v0.32b invariant."""
    assert _CONFIDENCE_LABELS == frozenset(
        {"strong", "qualified", "failed", "insufficient_evidence"}
    )


# ---------------------------------------------------------------------------
# Cases 4-8: method_scores shape validation.
# ---------------------------------------------------------------------------


def test_case_04_method_scores_nan_value_raises() -> None:
    """NaN inside a method-score entry raises SchemaValidationError."""
    bad = {"x": _make_valid_score_entry(value=math.nan)}
    with pytest.raises(SchemaValidationError, match="finite float"):
        summarize_generator_confidence(method_scores=bad)


def test_case_05_method_scores_infinity_value_raises() -> None:
    """+Inf inside a method-score entry raises SchemaValidationError."""
    bad = {"x": _make_valid_score_entry(value=math.inf)}
    with pytest.raises(SchemaValidationError, match="finite float"):
        summarize_generator_confidence(method_scores=bad)


def test_case_06_method_scores_unknown_direction_raises() -> None:
    """Direction outside the frozen vocabulary raises SchemaValidationError."""
    bad = {"x": _make_valid_score_entry(direction="sideways")}
    with pytest.raises(SchemaValidationError, match="direction"):
        summarize_generator_confidence(method_scores=bad)


def test_case_07_method_scores_boolean_value_raises() -> None:
    """Booleans MUST NOT appear as numeric scores."""
    bad = {"x": _make_valid_score_entry(value=True)}  # type: ignore[arg-type]
    with pytest.raises(SchemaValidationError, match="boolean"):
        summarize_generator_confidence(method_scores=bad)


def test_case_08_method_scores_missing_key_raises() -> None:
    """Every entry must carry exactly {value, direction, description, units}."""
    bad = {"x": {"value": 1.0, "direction": "lower_is_better"}}
    with pytest.raises(SchemaValidationError, match="exactly keys"):
        summarize_generator_confidence(method_scores=bad)


# ---------------------------------------------------------------------------
# Cases 9-14: uncertainty_report shape / vocabulary validation.
# ---------------------------------------------------------------------------


def _make_valid_uncertainty_report() -> dict:
    return {
        "method": "bootstrap",
        "resampling_unit": "batch",
        "sample_count": 10,
        "seed": 42,
        "interval_level": 0.95,
        "intervals": {"span_distance": {"low": 0.0, "high": 1.0}},
        "point_estimates": {"span_distance": 0.5},
        "failed_resamples": 0,
        "warnings": [],
        "diagnostic_only": True,
    }


def test_case_09_uncertainty_report_unknown_method_raises() -> None:
    bad = _make_valid_uncertainty_report()
    bad["method"] = "posterior"
    with pytest.raises(SchemaValidationError, match="method must be"):
        summarize_generator_confidence(uncertainty_report=bad)


def test_case_10_uncertainty_report_row_resampling_unit_raises() -> None:
    """Row-level bootstrap is refused at the report boundary too."""
    bad = _make_valid_uncertainty_report()
    bad["resampling_unit"] = "row"
    with pytest.raises(SchemaValidationError, match="resampling_unit"):
        summarize_generator_confidence(uncertainty_report=bad)


def test_case_11_uncertainty_report_interval_level_out_of_range_raises() -> None:
    bad = _make_valid_uncertainty_report()
    bad["interval_level"] = 1.5
    with pytest.raises(SchemaValidationError, match="interval_level"):
        summarize_generator_confidence(uncertainty_report=bad)


def test_case_12_uncertainty_report_interval_nan_endpoint_raises() -> None:
    bad = _make_valid_uncertainty_report()
    bad["intervals"] = {"x": {"low": math.nan, "high": 1.0}}
    with pytest.raises(SchemaValidationError, match="finite float"):
        summarize_generator_confidence(uncertainty_report=bad)


def test_case_13_uncertainty_report_negative_sample_count_raises() -> None:
    bad = _make_valid_uncertainty_report()
    bad["sample_count"] = -1
    with pytest.raises(SchemaValidationError, match="non-negative"):
        summarize_generator_confidence(uncertainty_report=bad)


def test_case_14_uncertainty_report_diagnostic_only_must_be_true() -> None:
    bad = _make_valid_uncertainty_report()
    bad["diagnostic_only"] = False
    with pytest.raises(SchemaValidationError, match="diagnostic_only"):
        summarize_generator_confidence(uncertainty_report=bad)


# ---------------------------------------------------------------------------
# Case 15: calibration_report shape validation.
# ---------------------------------------------------------------------------


def test_case_15_calibration_report_empty_method_raises() -> None:
    """calibration_report.method must be non-empty; diagnostic_only must be True."""
    bad = {
        "method": "",
        "target": "translation_symmetry",
        "sample_count": 100,
        "metrics": {"ece": 0.01},
        "warnings": [],
        "diagnostic_only": True,
    }
    with pytest.raises(SchemaValidationError, match="method"):
        summarize_generator_confidence(calibration_report=bad)


# ---------------------------------------------------------------------------
# Cases 16-20: built-in method + bootstrap end-to-end.
# ---------------------------------------------------------------------------


def test_case_16_built_in_method_emits_frozen_four_score_names() -> None:
    """polynomial_translation_svd.method_scores has EXACTLY the frozen four names."""
    field = generate_heat_1d_field_batch(
        batch_size=1, num_times=17, num_points=32, seed=42
    )
    result = run_symmetry_method(
        "polynomial_translation_svd",
        field,
        residual_evaluator=HeatResidualEvaluator(),
    )
    assert set(result.method_scores.keys()) == set(_FROZEN_SCORE_NAMES)
    assert set(SCORE_METADATA.keys()) == set(_FROZEN_SCORE_NAMES)


def test_case_17_enrich_method_scores_composes_with_confidence_report() -> None:
    """enrich_method_scores produces the enriched-form dict; strict-JSON round-trips."""
    field = generate_heat_1d_field_batch(
        batch_size=1, num_times=17, num_points=32, seed=42
    )
    result = run_symmetry_method(
        "polynomial_translation_svd",
        field,
        residual_evaluator=HeatResidualEvaluator(),
    )
    enriched = enrich_method_scores(result.method_scores, SCORE_METADATA)
    summary = summarize_generator_confidence(method_scores=enriched)
    for name in _FROZEN_SCORE_NAMES:
        entry = summary["method_scores"][name]
        assert set(entry.keys()) == {"value", "direction", "description", "units"}
        assert entry["direction"] == SCORE_METADATA[name]["direction"]
    encoded = json.dumps(summary, allow_nan=False)
    assert json.loads(encoded) == summary


def test_case_18_bootstrap_is_deterministic_under_fixed_seed() -> None:
    """Same seed + same field -> byte-identical uncertainty_report."""
    field = generate_heat_1d_field_batch(
        batch_size=10, num_times=17, num_points=32, seed=42
    )
    residual_evaluator = HeatResidualEvaluator()
    a = bootstrap_uncertainty(
        field, residual_evaluator, seed=7, num_resamples=8
    )
    b = bootstrap_uncertainty(
        field, residual_evaluator, seed=7, num_resamples=8
    )
    assert a == b


def test_case_19_bootstrap_below_min_units_emits_empty_intervals() -> None:
    """batch_size < min_units -> intervals are all None, warning included, no silent fallback."""
    field = generate_heat_1d_field_batch(
        batch_size=4, num_times=17, num_points=32, seed=42
    )
    report = bootstrap_uncertainty(
        field, HeatResidualEvaluator(), seed=1, num_resamples=8
    )
    assert report["sample_count"] == 4
    assert any(w.startswith("insufficient_independent_units:") for w in report["warnings"])
    for interval in report["intervals"].values():
        assert interval == {"low": None, "high": None}
    # And it round-trips into the confidence summary.
    summary = summarize_generator_confidence(uncertainty_report=report)
    assert summary["uncertainty_report"]["method"] == "bootstrap"


def test_case_20_bootstrap_refuses_row_unit_and_row_bootstrap_never_silently_used() -> None:
    """Row-level bootstrap raises ScopeValidationError with no silent fallback."""
    field = generate_heat_1d_field_batch(
        batch_size=8, num_times=17, num_points=32, seed=42
    )
    with pytest.raises(ScopeValidationError, match="row-level bootstrap"):
        bootstrap_uncertainty(
            field, HeatResidualEvaluator(), seed=1, resampling_unit="row"
        )
