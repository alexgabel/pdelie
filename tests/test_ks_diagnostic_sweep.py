from __future__ import annotations

import importlib
import json
from numbers import Number
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import pdelie
from tests._helpers.ks_diagnostic_sweep import (
    KS_SWEEP_EPSILONS,
    KS_SWEEP_VARIANTS,
    cached_ks_fit_diagnostic_sweep,
    run_ks_fit_diagnostic_sweep,
)


@pytest.fixture(scope="module")
def sweep_summary() -> dict[str, object]:
    return cached_ks_fit_diagnostic_sweep()


def _variant_by_name(summary: dict[str, object], name: str) -> dict[str, object]:
    variants = summary["variants"]
    assert isinstance(variants, list)
    for variant in variants:
        assert isinstance(variant, dict)
        if variant["variant_name"] == name:
            return variant
    raise AssertionError(f"missing variant {name!r}")


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
        np.testing.assert_allclose(left, right, rtol=1e-7, atol=1e-10)
        return
    assert left == right


def test_ks_diagnostic_sweep_output_is_json_plain(sweep_summary: dict[str, object]) -> None:
    assert sweep_summary["summary_schema_version"] == "0.1"
    assert sweep_summary["summary_type"] == "ks_fit_diagnostic_sweep"
    assert json.loads(json.dumps(sweep_summary)) == sweep_summary
    _assert_json_plain(sweep_summary)


def test_ks_diagnostic_sweep_matrix_is_frozen(sweep_summary: dict[str, object]) -> None:
    expected_variant_names = [str(variant["variant_name"]) for variant in KS_SWEEP_VARIANTS]

    assert sweep_summary["epsilons"] == [float(epsilon) for epsilon in KS_SWEEP_EPSILONS]
    assert sweep_summary["train_size"] == 2
    assert sweep_summary["split_seed"] == 11102

    variants = sweep_summary["variants"]
    assert isinstance(variants, list)
    assert [variant["variant_name"] for variant in variants] == expected_variant_names
    for variant in variants:
        assert isinstance(variant, dict)
        fits = variant["fits"]
        assert isinstance(fits, list)
        assert [fit["epsilon"] for fit in fits] == [float(epsilon) for epsilon in KS_SWEEP_EPSILONS]


def test_ks_diagnostic_sweep_writes_no_artifacts_and_is_deterministic(
    sweep_summary: dict[str, object],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workdir = tmp_path
    monkeypatch.chdir(workdir)

    assert list(workdir.iterdir()) == []
    repeated = run_ks_fit_diagnostic_sweep()
    assert list(workdir.iterdir()) == []
    _assert_summary_close(sweep_summary, repeated)


def test_ks_diagnostic_sweep_fit_diagnostics_are_well_formed(sweep_summary: dict[str, object]) -> None:
    variants = sweep_summary["variants"]
    assert isinstance(variants, list)

    for variant in variants:
        assert isinstance(variant, dict)
        for fit in variant["fits"]:
            assert isinstance(fit, dict)
            singular_values = fit["singular_values"]
            assert isinstance(singular_values, list)
            assert singular_values
            singular_array = np.asarray(singular_values, dtype=float)
            assert np.all(np.isfinite(singular_array))
            assert np.all(singular_array >= 0.0)
            assert np.all(singular_array[:-1] >= singular_array[1:] - 1e-12)

            condition_number = fit["condition_number"]
            if condition_number is not None:
                assert isinstance(condition_number, float)
                assert np.isfinite(condition_number)
                assert condition_number > 0.0

            fit_diagnostics = fit["fit_diagnostics"]
            assert isinstance(fit_diagnostics, dict)
            assert fit_diagnostics["summary_type"] == "generator_fit_diagnostics"
            assert fit_diagnostics["singular_values"] == singular_values
            assert fit_diagnostics["condition_number"] == condition_number


def test_ks_diagnostic_sweep_variant_aggregates(sweep_summary: dict[str, object]) -> None:
    variants = sweep_summary["variants"]
    assert isinstance(variants, list)

    for variant in variants:
        assert isinstance(variant, dict)
        assert set(variant["condition_number_summary"]) == {"min", "median", "max"}
        assert set(variant["svd_span_distance_summary"]) == {"min", "median", "max"}
        assert isinstance(variant["any_direct_svd_in_tolerance"], bool)
        assert isinstance(variant["fallback_reason_stable"], bool)
        assert isinstance(variant["fallback_reasons"], list)
        assert variant["conclusion"] in {
            "direct_svd_recovered",
            "fallback_stable_across_epsilons",
            "epsilon_sensitive",
            "inconclusive",
        }


def test_ks_diagnostic_sweep_default_variant_records_stable_fallback(
    sweep_summary: dict[str, object],
) -> None:
    default = _variant_by_name(sweep_summary, "default")

    assert default["conclusion"] == "fallback_stable_across_epsilons"
    assert default["fallback_reason_stable"] is True
    assert default["fallback_reasons"] == ["svd_translation_span_drift"]
    assert default["any_direct_svd_in_tolerance"] is False
    assert default["mass_drift"] <= 1e-8
    assert "relative_l2_drift" in default
    assert default["relative_l2_drift"] >= 0.0

    for fit in default["fits"]:
        assert fit["evidence_label"] == "reference_fallback"
        assert fit["reference_fallback_used"] is True
        assert fit["fallback_reason"] == "svd_translation_span_drift"
        assert fit["svd_span_distance"] > 1e-1
        assert fit["selected_span_distance"] <= 1e-1
        assert fit["first_verification_error"] < 5e-4
        assert fit["classification"] != "failed"
        assert fit["transform_mode"] == "uniform_translation"


def test_ks_diagnostic_sweep_all_frozen_variants_remain_fallback_stable(
    sweep_summary: dict[str, object],
) -> None:
    variants = sweep_summary["variants"]
    assert isinstance(variants, list)

    for variant in variants:
        assert isinstance(variant, dict)
        assert variant["conclusion"] == "fallback_stable_across_epsilons"
        assert variant["fallback_reasons"] == ["svd_translation_span_drift"]
        assert variant["any_direct_svd_in_tolerance"] is False


def test_ks_diagnostic_sweep_adds_no_public_ks_surface() -> None:
    data_module = importlib.import_module("pdelie.data")
    residuals_module = importlib.import_module("pdelie.residuals")
    examples_module = importlib.import_module("pdelie.examples")

    assert not hasattr(data_module, "generate_ks_1d_field_batch")
    assert not hasattr(data_module, "generate_ks_feasibility_field_batch")
    assert not hasattr(residuals_module, "KSResidualEvaluator")
    assert not hasattr(residuals_module, "KuramotoSivashinskyResidualEvaluator")
    assert not hasattr(examples_module, "run_ks_vertical_slice_example")
    assert not hasattr(pdelie, "generate_ks_1d_field_batch")
    assert not hasattr(pdelie, "KSResidualEvaluator")
    assert not hasattr(pdelie, "KuramotoSivashinskyResidualEvaluator")
    assert not hasattr(pdelie, "run_ks_vertical_slice_example")
