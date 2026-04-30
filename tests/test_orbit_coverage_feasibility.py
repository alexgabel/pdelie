from __future__ import annotations

import importlib
import json
from numbers import Number
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import pdelie
from tests._helpers.orbit_coverage_feasibility import (
    cached_orbit_coverage_feasibility,
    run_orbit_coverage_feasibility,
)


@pytest.fixture(scope="module")
def feasibility_summary() -> dict[str, object]:
    return cached_orbit_coverage_feasibility()


def _assert_json_plain(value: object) -> None:
    assert not isinstance(value, (np.ndarray, np.generic))
    if isinstance(value, dict):
        for key, item in value.items():
            assert isinstance(key, str)
            _assert_json_plain(item)
    elif isinstance(value, list):
        for item in value:
            _assert_json_plain(item)
    else:
        assert value is None or isinstance(value, (str, bool, int, float))


def _assert_summary_close(left: Any, right: Any) -> None:
    if isinstance(left, dict):
        assert isinstance(right, dict)
        assert set(left) == set(right)
        for key in left:
            _assert_summary_close(left[key], right[key])
        return
    if isinstance(left, list):
        assert isinstance(right, list)
        assert len(left) == len(right)
        for left_item, right_item in zip(left, right, strict=True):
            _assert_summary_close(left_item, right_item)
        return
    if isinstance(left, Number) and not isinstance(left, bool):
        assert isinstance(right, Number)
        np.testing.assert_allclose(left, right, rtol=1e-9, atol=1e-12)
        return
    assert left == right


def _coverage_case(summary: dict[str, object], case_name: str) -> dict[str, object]:
    cases = summary["coverage_cases"]
    assert isinstance(cases, list)
    for case in cases:
        assert isinstance(case, dict)
        if case["case_name"] == case_name:
            return case
    raise AssertionError(f"missing coverage case {case_name!r}")


def test_orbit_coverage_feasibility_output_is_json_plain(
    feasibility_summary: dict[str, object],
) -> None:
    assert feasibility_summary["summary_schema_version"] == "0.1"
    assert feasibility_summary["summary_type"] == "orbit_coverage_feasibility"
    assert json.loads(json.dumps(feasibility_summary)) == feasibility_summary
    _assert_json_plain(feasibility_summary)


def test_orbit_coverage_feasibility_writes_no_artifacts_and_is_deterministic(
    feasibility_summary: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    assert list(tmp_path.iterdir()) == []
    repeated = run_orbit_coverage_feasibility()
    assert list(tmp_path.iterdir()) == []
    _assert_summary_close(feasibility_summary, repeated)


def test_periodic_window_coverage_cases_match_frozen_expectations(
    feasibility_summary: dict[str, object],
) -> None:
    half = _coverage_case(feasibility_summary, "half_coverage_quarter_shifts")
    full = _coverage_case(feasibility_summary, "full_coverage_quarter_shifts")

    assert half["grid_points"] == 64
    assert half["covered_grid_point_count"] == 32
    assert half["coverage_fraction"] == pytest.approx(0.5)
    assert full["grid_points"] == 64
    assert full["covered_grid_point_count"] == 64
    assert full["coverage_fraction"] == pytest.approx(1.0)

    for case in (half, full):
        assert len(case["base_windows"]) == 1
        assert len(case["shifts"]) == 4
        assert 0 <= case["min_coverage_count"] <= case["max_coverage_count"] <= len(case["shifts"])
        assert np.isfinite(case["mean_coverage_count"])
        assert case["mean_coverage_count"] >= 0.0
        assert isinstance(case["max_uncovered_run_points"], int)
        assert case["max_uncovered_run_points"] >= 0


def test_transform_consistency_preserves_structure_and_residuals(
    feasibility_summary: dict[str, object],
) -> None:
    cases = feasibility_summary["transform_consistency_cases"]
    assert isinstance(cases, list)
    assert {case["field_name"] for case in cases} == {"heat_default", "kdv_default"}

    for case in cases:
        assert isinstance(case, dict)
        assert case["equation"] in {"heat_1d", "kdv_normalized"}
        assert len(case["shifts"]) == 5
        shift_reports = case["shift_reports"]
        assert isinstance(shift_reports, list)
        assert len(shift_reports) == len(case["shifts"])

        for report in shift_reports:
            assert report["dims_preserved"] is True
            assert report["coords_preserved"] is True
            assert report["var_names_preserved"] is True
            assert report["metadata_preserved"] is True
            assert report["mask_preserved"] is True
            assert report["inverse_relative_l2_error"] <= 1e-8
            assert report["period_wrap_relative_l2_error"] <= 1e-8
            assert np.isfinite(report["residual_rms_before"])
            assert np.isfinite(report["residual_rms_after"])
            assert report["residual_relative_rms_delta"] <= 1e-6
            assert report["provenance_operation"] == "invariant_apply"
            assert report["provenance_construction_method"] == "uniform_translation"
            assert report["preprocess_log_length_delta"] == 1


def test_orbit_coverage_feasibility_adds_no_public_surface() -> None:
    reporting_module = importlib.import_module("pdelie.reporting")
    data_module = importlib.import_module("pdelie.data")
    residuals_module = importlib.import_module("pdelie.residuals")

    for name in (
        "summarize_orbit_coverage",
        "summarize_orbit_coverage_feasibility",
        "run_orbit_coverage_feasibility",
        "augment_translation_orbit",
        "build_translation_orbit_views",
        "compute_coverage_diagnostics",
    ):
        assert not hasattr(pdelie, name)
        assert not hasattr(reporting_module, name)
        assert not hasattr(data_module, name)

    assert not hasattr(residuals_module, "evaluate_weak_ks_residual")
    assert not hasattr(residuals_module, "WeakKSResidualEvaluator")
    assert not hasattr(residuals_module, "WeakKuramotoSivashinskyResidualEvaluator")
    assert not hasattr(data_module, "generate_ks_1d_field_batch")
    assert not hasattr(pdelie, "generate_ks_1d_field_batch")
    assert not hasattr(pdelie, "KSResidualEvaluator")
