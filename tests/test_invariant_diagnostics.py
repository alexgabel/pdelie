from __future__ import annotations

import json
from typing import Any

import numpy as np
import pytest

from pdelie.contracts import FieldBatch
from pdelie.data import generate_heat_1d_field_batch, generate_kdv_1d_field_batch
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.invariants import (
    compute_periodic_window_coverage,
    diagnose_uniform_translation_consistency,
    summarize_uniform_translation_orbit,
)
from pdelie.residuals import HeatResidualEvaluator, KdVResidualEvaluator


DOMAIN_LENGTH = 2.0 * np.pi


def _assert_json_plain(value: object) -> None:
    assert not isinstance(value, (np.ndarray, np.generic, FieldBatch))
    if isinstance(value, dict):
        for key, item in value.items():
            assert isinstance(key, str)
            _assert_json_plain(item)
    elif isinstance(value, list):
        for item in value:
            _assert_json_plain(item)
    else:
        assert value is None or isinstance(value, (str, bool, int, float))


def _shift_report(summary: dict[str, Any], shift: float) -> dict[str, Any]:
    for report in summary["shift_reports"]:
        if report["shift"] == pytest.approx(shift):
            return report
    raise AssertionError(f"missing shift report for {shift}")


def test_periodic_window_coverage_matches_frozen_quarter_shift_cases() -> None:
    x = np.linspace(0.0, DOMAIN_LENGTH, 64, endpoint=False)

    half = compute_periodic_window_coverage(
        x=x,
        windows=[{"start": 0.0, "width": DOMAIN_LENGTH / 8.0}],
        shifts=[0.0, DOMAIN_LENGTH / 4.0, DOMAIN_LENGTH / 2.0, 3.0 * DOMAIN_LENGTH / 4.0],
        domain_length=DOMAIN_LENGTH,
    )
    full = compute_periodic_window_coverage(
        x=x,
        windows=[{"start": 0.0, "width": DOMAIN_LENGTH / 4.0}],
        shifts=[0.0, DOMAIN_LENGTH / 4.0, DOMAIN_LENGTH / 2.0, 3.0 * DOMAIN_LENGTH / 4.0],
        domain_length=DOMAIN_LENGTH,
    )

    assert half["summary_type"] == "periodic_window_coverage"
    assert half["coverage_type"] == "grid_point"
    assert half["coverage_convention"] == "preimage_of_fixed_window_under_translation"
    assert half["shift_convention"] == "field_shift_then_fixed_window"
    assert half["window_convention"] == "half_open"
    assert half["grid_point_count"] == 64
    assert half["covered_grid_point_count"] == 32
    assert half["coverage_fraction"] == pytest.approx(0.5)
    assert half["max_uncovered_run_points"] == 8
    assert half["max_uncovered_run_length"] == pytest.approx(8 * (DOMAIN_LENGTH / 64.0))

    assert full["grid_point_count"] == 64
    assert full["covered_grid_point_count"] == 64
    assert full["coverage_fraction"] == pytest.approx(1.0)
    assert full["min_coverage_count"] == 1
    assert full["max_coverage_count"] == 1
    assert json.loads(json.dumps(half)) == half
    _assert_json_plain(half)


def test_periodic_window_coverage_freezes_domain_inference_and_shift_sign_convention() -> None:
    x = np.linspace(0.0, DOMAIN_LENGTH, 8, endpoint=False)
    summary = compute_periodic_window_coverage(
        x=x,
        windows=[{"start": 0.0, "width": DOMAIN_LENGTH / 8.0}],
        shifts=[DOMAIN_LENGTH / 8.0],
    )

    assert summary["domain_length"] == pytest.approx(DOMAIN_LENGTH)
    assert summary["inferred_domain_length"] == pytest.approx(len(x) * (x[1] - x[0]))
    assert summary["dx"] == pytest.approx(DOMAIN_LENGTH / 8.0)
    assert summary["coverage_counts"] == [0, 0, 0, 0, 0, 0, 0, 1]
    assert summary["covered_grid_point_count"] == 1
    assert summary["normalized_shifts"] == pytest.approx([DOMAIN_LENGTH / 8.0])


def test_periodic_window_coverage_uses_half_open_windows_with_boundary_tolerance() -> None:
    x = np.linspace(0.0, 4.0, 4, endpoint=False)
    summary = compute_periodic_window_coverage(
        x=x,
        windows=[{"start": 0.0, "width": 1.0}],
        shifts=[0.0],
        domain_length=4.0,
    )

    assert summary["coverage_counts"] == [1, 0, 0, 0]
    assert summary["covered_grid_point_count"] == 1


def test_periodic_window_coverage_counts_duplicate_shifts_and_repeated_windows() -> None:
    x = np.linspace(0.0, DOMAIN_LENGTH, 8, endpoint=False)
    summary = compute_periodic_window_coverage(
        x=x,
        windows=[
            {"start": 0.0, "width": DOMAIN_LENGTH / 4.0},
            {"start": 0.0, "width": DOMAIN_LENGTH / 4.0},
        ],
        shifts=[0.0, 0.0],
        domain_length=DOMAIN_LENGTH,
    )

    assert summary["covered_grid_point_count"] == 2
    assert summary["coverage_fraction"] == pytest.approx(2 / 8)
    assert summary["coverage_counts"] == [4, 4, 0, 0, 0, 0, 0, 0]
    assert summary["max_coverage_count"] == 4


def test_periodic_window_coverage_handles_wraparound_and_over_domain_shifts() -> None:
    x = np.linspace(0.0, DOMAIN_LENGTH, 8, endpoint=False)
    summary = compute_periodic_window_coverage(
        x=x,
        windows=[{"start": 7.0 * DOMAIN_LENGTH / 8.0, "width": DOMAIN_LENGTH / 4.0}],
        shifts=[DOMAIN_LENGTH, -DOMAIN_LENGTH / 8.0],
        domain_length=DOMAIN_LENGTH,
    )

    assert summary["normalized_shifts"] == pytest.approx([0.0, 7.0 * DOMAIN_LENGTH / 8.0])
    assert summary["coverage_counts"] == [2, 1, 0, 0, 0, 0, 0, 1]
    assert summary["covered_grid_point_count"] == 3


@pytest.mark.parametrize(
    ("kwargs", "error_type", "match"),
    [
        ({"x": [[0.0, 1.0]], "windows": [{"start": 0.0, "width": 1.0}], "shifts": [0.0]}, SchemaValidationError, "one-dimensional"),
        ({"x": [0.0, 1.0, 2.2], "windows": [{"start": 0.0, "width": 1.0}], "shifts": [0.0]}, ScopeValidationError, "uniform"),
        ({"x": np.linspace(0.0, 4.0, 5), "windows": [{"start": 0.0, "width": 1.0}], "shifts": [0.0], "domain_length": 4.0}, ScopeValidationError, "endpoint"),
        ({"x": [0.0, 1.0, 2.0, 3.0], "windows": [{"start": 0.0, "width": 0.0}], "shifts": [0.0], "domain_length": 4.0}, SchemaValidationError, "positive"),
        ({"x": [0.0, 1.0, 2.0, 3.0], "windows": [{"start": 0.0, "width": 5.0}], "shifts": [0.0], "domain_length": 4.0}, ScopeValidationError, "domain_length"),
        ({"x": [0.0, 1.0, 2.0, 3.0], "windows": [{"start": 0.0, "width": 1.0}], "shifts": [], "domain_length": 4.0}, SchemaValidationError, "non-empty"),
        ({"x": [0.0, 1.0, 2.0, 3.0], "windows": [{"start": 0.0, "width": 1.0}], "shifts": [np.inf], "domain_length": 4.0}, SchemaValidationError, "finite"),
    ],
)
def test_periodic_window_coverage_rejects_invalid_inputs(
    kwargs: dict[str, object],
    error_type: type[Exception],
    match: str,
) -> None:
    with pytest.raises(error_type, match=match):
        compute_periodic_window_coverage(**kwargs)


def test_uniform_translation_consistency_reports_heat_and_kdv_stability() -> None:
    heat = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=64, seed=1301)
    kdv = generate_kdv_1d_field_batch(batch_size=2, num_times=17, num_points=64, seed=1302)
    shifts = [0.0, DOMAIN_LENGTH / 64.0, DOMAIN_LENGTH / 8.0, -DOMAIN_LENGTH / 8.0, DOMAIN_LENGTH]

    for field, evaluator in ((heat, HeatResidualEvaluator()), (kdv, KdVResidualEvaluator())):
        snapshot = field.to_dict()
        summary = diagnose_uniform_translation_consistency(field, shifts=shifts, residual_evaluator=evaluator)

        assert summary["summary_schema_version"] == "0.1"
        assert summary["summary_type"] == "uniform_translation_consistency"
        assert summary["residual_evaluator"] == type(evaluator).__name__
        assert summary["raw_shifts"] == pytest.approx(shifts)
        assert len(summary["shift_reports"]) == len(shifts)
        assert json.loads(json.dumps(summary)) == summary
        _assert_json_plain(summary)

        identity_report = _shift_report(summary, DOMAIN_LENGTH)
        assert identity_report["period_wrap_relative_l2_error"] <= 1e-8
        for report in summary["shift_reports"]:
            assert report["dims_preserved"] is True
            assert report["shape_preserved"] is True
            assert report["coords_preserved"] is True
            assert report["metadata_preserved"] is True
            assert report["var_names_preserved"] is True
            assert report["mask_preserved"] is True
            assert report["inverse_relative_l2_error"] <= 1e-8
            assert report["period_wrap_relative_l2_error"] <= 1e-8
            assert report["inverse_passed"] is True
            assert report["period_wrap_passed"] is True
            assert report["residual_stability_passed"] is True
            assert report["residual_absolute_rms_delta"] <= 1e-8 or report["residual_relative_rms_delta"] <= 1e-6
            assert report["preprocess_log_length_delta"] == 1
            assert report["provenance_operation"] == "invariant_apply"
            assert report["provenance_construction_method"] == "uniform_translation"
            assert report["provenance_axis"] == "x"
            assert report["provenance_shift"] == pytest.approx(report["shift"])

        assert field.to_dict() == snapshot


def test_uniform_translation_consistency_without_residual_evaluator_omits_residual_metrics() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=1303)
    summary = diagnose_uniform_translation_consistency(field, shifts=[0.0])
    report = summary["shift_reports"][0]

    assert summary["residual_evaluator"] is None
    assert report["residual_rms_before"] is None
    assert report["residual_rms_after"] is None
    assert report["residual_absolute_rms_delta"] is None
    assert report["residual_relative_rms_delta"] is None
    assert report["residual_stability_passed"] is None


def test_uniform_translation_orbit_report_combines_coverage_consistency_and_provenance() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=64, seed=14011)
    snapshot = field.to_dict()
    shifts = [0.0, DOMAIN_LENGTH / 64.0, DOMAIN_LENGTH / 8.0, DOMAIN_LENGTH / 8.0, DOMAIN_LENGTH]
    windows = [{"start": 0.0, "width": DOMAIN_LENGTH / 4.0}]

    summary = summarize_uniform_translation_orbit(
        field,
        shifts=shifts,
        windows=windows,
        residual_evaluator=HeatResidualEvaluator(),
        source_field_id="heat-orbit-fixture",
    )

    assert json.loads(json.dumps(summary)) == summary
    _assert_json_plain(summary)
    assert summary["summary_schema_version"] == "0.1"
    assert summary["summary_type"] == "uniform_translation_orbit"
    assert summary["source_field_id"] == "heat-orbit-fixture"
    assert summary["field_dims"] == list(field.dims)
    assert summary["field_shape"] == list(field.values.shape)
    assert summary["equation"] is None
    assert summary["raw_shifts"] == pytest.approx(shifts)
    assert summary["normalized_shifts"] == pytest.approx([shift % DOMAIN_LENGTH for shift in shifts])
    assert summary["transform_axis"] == "x"
    assert summary["construction_method"] == "uniform_translation"
    assert summary["transform_count"] == len(shifts)
    assert summary["coverage"]["summary_type"] == "periodic_window_coverage"
    assert summary["consistency"]["summary_type"] == "uniform_translation_consistency"
    assert len(summary["orbit_reports"]) == len(shifts)
    assert summary["orbit_passed"] is True
    assert [report["shift"] for report in summary["orbit_reports"]] == pytest.approx(shifts)
    for report in summary["orbit_reports"]:
        assert report["transform_spec"]["construction_method"] == "uniform_translation"
        assert report["transform_spec"]["parameters"]["axis"] == "x"
        assert report["inverse_passed"] is True
        assert report["period_wrap_passed"] is True
        assert report["residual_stability_passed"] is True
        assert report["consistency_passed"] is True
        assert report["provenance_operation"] == "invariant_apply"
        assert report["provenance_construction_method"] == "uniform_translation"
    assert field.to_dict() == snapshot


def test_uniform_translation_orbit_report_allows_report_only_minimal_mode() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=14012)

    summary = summarize_uniform_translation_orbit(
        field,
        shifts=[0.0, DOMAIN_LENGTH],
        source_field_id={"dataset": "synthetic", "index": 1},
    )

    assert summary["coverage"] is None
    assert summary["source_field_id"] == {"dataset": "synthetic", "index": 1}
    assert summary["orbit_passed"] is True
    for report in summary["orbit_reports"]:
        assert report["residual_stability_passed"] is None
        assert report["consistency_passed"] is True
    for report in summary["consistency"]["shift_reports"]:
        assert report["residual_rms_before"] is None


def test_uniform_translation_orbit_report_rejects_non_json_source_field_id() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=14013)

    with pytest.raises(SchemaValidationError, match="source_field_id"):
        summarize_uniform_translation_orbit(field, shifts=[0.0], source_field_id=object())


def test_uniform_translation_consistency_rejects_unsupported_inputs() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=1304)
    nonperiodic = FieldBatch(
        values=field.values,
        dims=field.dims,
        coords=field.coords,
        var_names=field.var_names,
        metadata={**field.metadata, "boundary_conditions": {"x": "dirichlet"}},
        preprocess_log=field.preprocess_log,
    )

    with pytest.raises(ScopeValidationError, match="periodic"):
        diagnose_uniform_translation_consistency(nonperiodic, shifts=[0.0])
    with pytest.raises(SchemaValidationError, match="ResidualEvaluator"):
        diagnose_uniform_translation_consistency(field, shifts=[0.0], residual_evaluator=object())
