from __future__ import annotations

import json
import subprocess
import sys

import numpy as np

import pdelie
from pdelie.examples import (
    run_formula_generator_validation_example,
    run_heat_vertical_slice_example,
    run_invariant_workflow_summary_example,
    run_kdv_vertical_slice_example,
    run_orbit_coverage_diagnostics_example,
    run_reaction_diffusion_vertical_slice_example,
    run_symmetry_candidate_validation_example,
    run_translation_orbit_batch_example,
)


def _assert_vertical_slice_summary(result: dict[str, object]) -> None:
    assert json.loads(json.dumps(result)) == result
    assert result["summary_schema_version"] == "0.1"
    assert result["summary_type"] == "vertical_slice"
    assert result["derivative_backend"] == "spectral_fd"
    assert result["residual"]["summary_type"] == "residual_batch"
    assert result["generator"]["summary_type"] == "generator_family"
    assert result["verification"]["summary_type"] == "verification_report"


def _assert_repeated_summary_matches(first: dict[str, object], second: dict[str, object]) -> None:
    for key in (
        "summary_schema_version",
        "summary_type",
        "derivative_backend",
        "derivative_keys",
        "derivative_config",
        "derivative_diagnostics",
        "extra_metrics",
    ):
        assert first[key] == second[key]

    for section in ("residual", "generator", "verification"):
        for key, first_value in first[section].items():
            second_value = second[section][key]
            if key in {"coefficients", "epsilon_values", "error_curve"}:
                np.testing.assert_allclose(np.asarray(first_value, dtype=float), np.asarray(second_value, dtype=float))
            elif key == "diagnostics":
                _assert_nested_summary_matches(first_value, second_value)
            elif key in {
                "max_abs_residual",
                "rms_residual",
                "translation_span_distance",
                "first_epsilon",
                "first_error",
                "max_error",
            }:
                np.testing.assert_allclose(float(first_value), float(second_value))
            else:
                assert first_value == second_value


def _assert_nested_summary_matches(first: object, second: object) -> None:
    if isinstance(first, dict) and isinstance(second, dict):
        assert first.keys() == second.keys()
        for key in first:
            _assert_nested_summary_matches(first[key], second[key])
        return
    if isinstance(first, list) and isinstance(second, list):
        assert len(first) == len(second)
        for first_item, second_item in zip(first, second, strict=True):
            _assert_nested_summary_matches(first_item, second_item)
        return
    if isinstance(first, bool) or isinstance(second, bool):
        assert first == second
        return
    if isinstance(first, (int, float)) and isinstance(second, (int, float)):
        np.testing.assert_allclose(float(first), float(second))
        return
    assert first == second


def _run_module_json(module_name: str) -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, "-m", module_name],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stderr == ""
    return json.loads(completed.stdout)


def test_heat_vertical_slice_example_runs_end_to_end() -> None:
    result = run_heat_vertical_slice_example()
    _assert_vertical_slice_summary(result)

    assert result["extra_metrics"] == {
        "example_name": "heat_vertical_slice",
        "equation": "heat_1d",
        "training_seed": 100,
        "heldout_seed": 101,
        "training_batch_size": 4,
        "heldout_batch_size": 3,
    }
    assert result["generator"]["parameterization"] == "polynomial_translation_affine"
    assert result["verification"]["classification"] == "exact"
    assert result["verification"]["first_error"] < 1e-6
    assert not hasattr(pdelie, "run_heat_vertical_slice_example")


def test_heat_vertical_slice_example_is_deterministic() -> None:
    first = run_heat_vertical_slice_example()
    second = run_heat_vertical_slice_example()

    _assert_repeated_summary_matches(first, second)


def test_kdv_vertical_slice_example_runs_end_to_end_and_is_json_serializable() -> None:
    result = run_kdv_vertical_slice_example()
    _assert_vertical_slice_summary(result)

    assert result["extra_metrics"]["example_name"] == "kdv_vertical_slice"
    assert result["extra_metrics"]["equation"] == "kdv_normalized"
    assert result["extra_metrics"]["generator_seed"] == 9001
    assert result["extra_metrics"]["split_seed"] == 9002
    assert result["extra_metrics"]["train_size"] == 2
    assert result["residual"]["max_abs_residual"] < 1e-2
    assert result["residual"]["rms_residual"] < 2e-3
    assert result["extra_metrics"]["mass_drift"] <= 1e-8
    assert result["extra_metrics"]["relative_l2_drift"] <= 5e-3
    assert result["generator"]["parameterization"] == "polynomial_translation_affine"
    assert result["generator"]["fit_mode"] == "svd"
    assert result["generator"]["reference_fallback_used"] is False
    assert result["generator"]["translation_span_distance"] <= 5e-2
    assert result["verification"]["classification"] != "failed"
    assert result["verification"]["first_error"] < 1e-4
    assert not hasattr(pdelie, "run_kdv_vertical_slice_example")


def test_kdv_vertical_slice_example_is_deterministic() -> None:
    first = run_kdv_vertical_slice_example()
    second = run_kdv_vertical_slice_example()

    _assert_repeated_summary_matches(first, second)


def test_reaction_diffusion_vertical_slice_example_runs_end_to_end_and_is_json_serializable() -> None:
    result = run_reaction_diffusion_vertical_slice_example()
    _assert_vertical_slice_summary(result)

    assert result["extra_metrics"]["example_name"] == "reaction_diffusion_vertical_slice"
    assert result["extra_metrics"]["equation"] == "reaction_diffusion_fisher_kpp"
    assert result["extra_metrics"]["generator_seed"] == 18018
    assert result["extra_metrics"]["split_seed"] == 18019
    assert result["extra_metrics"]["train_size"] == 2
    assert result["residual"]["max_abs_residual"] < 5e-4
    assert result["residual"]["rms_residual"] < 5e-5
    assert np.isfinite(float(result["extra_metrics"]["mean_drift_diagnostic"]))
    assert np.isfinite(float(result["extra_metrics"]["relative_l2_drift_diagnostic"]))
    assert result["generator"]["parameterization"] == "polynomial_translation_affine"
    assert result["generator"]["fit_mode"] == "svd"
    assert result["generator"]["reference_fallback_used"] is False
    assert result["generator"]["translation_span_distance"] <= 5e-2
    assert result["verification"]["classification"] != "failed"
    assert result["verification"]["first_error"] < 5e-4
    assert not hasattr(pdelie, "run_reaction_diffusion_vertical_slice_example")


def test_reaction_diffusion_vertical_slice_example_is_deterministic() -> None:
    first = run_reaction_diffusion_vertical_slice_example()
    second = run_reaction_diffusion_vertical_slice_example()

    _assert_repeated_summary_matches(first, second)


def test_heat_vertical_slice_module_prints_json_only() -> None:
    parsed = _run_module_json("pdelie.examples.heat_vertical_slice")

    _assert_vertical_slice_summary(parsed)
    assert parsed["verification"]["classification"] == "exact"


def test_kdv_vertical_slice_module_prints_json_only() -> None:
    parsed = _run_module_json("pdelie.examples.kdv_vertical_slice")

    _assert_vertical_slice_summary(parsed)
    assert parsed["verification"]["classification"] != "failed"


def test_reaction_diffusion_vertical_slice_module_prints_json_only() -> None:
    parsed = _run_module_json("pdelie.examples.reaction_diffusion_vertical_slice")

    _assert_vertical_slice_summary(parsed)
    assert parsed["verification"]["classification"] != "failed"


def test_orbit_coverage_diagnostics_example_runs_end_to_end() -> None:
    result = run_orbit_coverage_diagnostics_example()

    assert json.loads(json.dumps(result)) == result
    assert result["summary_schema_version"] == "0.1"
    assert result["summary_type"] == "orbit_coverage_diagnostics_example"
    assert result["extra_metrics"]["example_name"] == "orbit_coverage_diagnostics"
    assert len(result["coverage_cases"]) == 2
    assert len(result["transform_consistency_cases"]) == 2
    assert result["coverage_cases"][0]["summary_type"] == "periodic_window_coverage"
    np.testing.assert_allclose(result["coverage_cases"][0]["coverage_fraction"], 0.5)
    np.testing.assert_allclose(result["coverage_cases"][1]["coverage_fraction"], 1.0)
    for summary in result["transform_consistency_cases"]:
        assert summary["summary_type"] == "uniform_translation_consistency"
        for report in summary["shift_reports"]:
            assert report["inverse_passed"] is True
            assert report["period_wrap_passed"] is True
            assert report["residual_stability_passed"] is True
    assert not hasattr(pdelie, "run_orbit_coverage_diagnostics_example")


def test_orbit_coverage_diagnostics_module_prints_json_only() -> None:
    parsed = _run_module_json("pdelie.examples.orbit_coverage_diagnostics")

    assert parsed["summary_type"] == "orbit_coverage_diagnostics_example"
    np.testing.assert_allclose(parsed["coverage_cases"][0]["coverage_fraction"], 0.5)
    np.testing.assert_allclose(parsed["coverage_cases"][1]["coverage_fraction"], 1.0)


def test_invariant_workflow_summary_example_runs_end_to_end() -> None:
    result = run_invariant_workflow_summary_example()

    assert json.loads(json.dumps(result)) == result
    assert result["summary_schema_version"] == "0.1"
    assert result["summary_type"] == "invariant_workflow_summary_example"
    assert result["extra_metrics"]["example_name"] == "invariant_workflow_summary"
    assert len(result["workflows"]) == 2
    cases = {workflow["extra_metrics"]["case_name"]: workflow for workflow in result["workflows"]}
    assert set(cases) == {"heat", "kdv"}
    for workflow in cases.values():
        assert workflow["summary_type"] == "invariant_workflow"
        assert workflow["orbit"]["summary_type"] == "uniform_translation_orbit"
        assert workflow["orbit"]["orbit_passed"] is True
        assert workflow["coverage"]["summary_type"] == "periodic_window_coverage"
        assert workflow["consistency"]["summary_type"] == "uniform_translation_consistency"
        assert workflow["generator"]["summary_type"] == "generator_family"
        assert workflow["fit_diagnostics"]["summary_type"] == "generator_fit_diagnostics"
        assert workflow["verification"]["summary_type"] == "verification_report"
        assert workflow["verification"]["classification"] != "failed"
    assert cases["heat"]["verification"]["classification"] == "exact"
    assert cases["kdv"]["fit_diagnostics"]["reference_fallback_used"] is False
    assert not hasattr(pdelie, "run_invariant_workflow_summary_example")


def test_invariant_workflow_summary_module_prints_json_only() -> None:
    parsed = _run_module_json("pdelie.examples.invariant_workflow_summary")

    assert parsed["summary_type"] == "invariant_workflow_summary_example"
    assert len(parsed["workflows"]) == 2
    for workflow in parsed["workflows"]:
        assert workflow["summary_type"] == "invariant_workflow"
        assert workflow["orbit"]["orbit_passed"] is True


def test_translation_orbit_batch_example_runs_end_to_end() -> None:
    result = run_translation_orbit_batch_example()

    assert json.loads(json.dumps(result)) == result
    assert result["summary_schema_version"] == "0.1"
    assert result["summary_type"] == "translation_orbit_batch_example"
    assert result["extra_metrics"]["example_name"] == "translation_orbit_batch"
    assert result["extra_metrics"]["duplicate_shifts_preserved"] is True
    assert result["extra_metrics"]["ordering"] == "shift_major"
    assert len(result["cases"]) == 2
    cases = {case["case_name"]: case for case in result["cases"]}
    assert set(cases) == {"heat", "kdv"}
    for case in cases.values():
        assert case["orbit_shape"][0] == case["source_shape"][0] * len(result["extra_metrics"]["shifts"])
        assert case["orbit_report"]["summary_type"] == "uniform_translation_orbit_batch"
        assert case["orbit_report"]["duplicate_shifts_preserved"] is True
        assert case["orbit_report"]["ordering"] == "shift_major"
        assert case["orbit_report"]["source_batch_indices"] == [0, 1] * len(result["extra_metrics"]["shifts"])
        assert case["residual"]["summary_type"] == "residual_batch"
        assert np.isfinite(float(case["residual"]["max_abs_residual"]))
    assert cases["kdv"]["orbit_report"]["source_field_id"] == "kdv_seed_15012"
    assert not hasattr(pdelie, "run_translation_orbit_batch_example")


def test_translation_orbit_batch_module_prints_json_only() -> None:
    parsed = _run_module_json("pdelie.examples.translation_orbit_batch")

    assert parsed["summary_type"] == "translation_orbit_batch_example"
    assert len(parsed["cases"]) == 2
    for case in parsed["cases"]:
        assert case["orbit_report"]["summary_type"] == "uniform_translation_orbit_batch"


def test_symmetry_candidate_validation_example_runs_end_to_end() -> None:
    result = run_symmetry_candidate_validation_example()

    assert json.loads(json.dumps(result)) == result
    assert result["summary_schema_version"] == "0.1"
    assert result["summary_type"] == "symmetry_candidate_validation_example"
    assert result["extra_metrics"]["example_name"] == "symmetry_candidate_validation"
    assert result["extra_metrics"]["candidate_kinds"] == ["generator_family", "invariant_map_spec"]
    assert result["extra_metrics"]["interpretation"] == "configured_empirical_validation_not_mathematical_proof"
    assert len(result["cases"]) == 4
    cases = {case["case_name"]: case for case in result["cases"]}
    assert set(cases) == {
        "failed_wrong_span_generator",
        "heat_generator_family",
        "heat_invariant_map_spec_payload",
        "kdv_generator_family",
    }
    assert cases["failed_wrong_span_generator"]["report"]["conclusion"] == "failed"
    for name in ("heat_generator_family", "heat_invariant_map_spec_payload", "kdv_generator_family"):
        assert cases[name]["report"]["summary_type"] == "symmetry_candidate_validation"
        assert cases[name]["report"]["conclusion"] == "validated"
    assert not hasattr(pdelie, "run_symmetry_candidate_validation_example")


def test_symmetry_candidate_validation_module_prints_json_only() -> None:
    parsed = _run_module_json("pdelie.examples.symmetry_candidate_validation")

    assert parsed["summary_type"] == "symmetry_candidate_validation_example"
    assert len(parsed["cases"]) == 4
    assert "failed" in parsed["extra_metrics"]["conclusions"]


def test_formula_generator_validation_example_runs_end_to_end() -> None:
    result = run_formula_generator_validation_example()

    assert json.loads(json.dumps(result)) == result
    assert result["summary_schema_version"] == "0.1"
    assert result["summary_type"] == "formula_generator_validation_example"
    assert result["extra_metrics"]["example_name"] == "formula_generator_validation"
    assert result["extra_metrics"]["candidate_kinds"] == ["formula_generator_family"]
    assert result["extra_metrics"]["expression_policy"] == "safe_json_ast_no_callables_no_executable_strings"
    assert len(result["cases"]) == 5
    cases = {case["case_name"]: case for case in result["cases"]}
    assert set(cases) == {
        "affine_formula",
        "failed_nonfinite_formula",
        "formula_with_uniform_translation_transform",
        "rational_formula",
        "trigonometric_formula",
    }
    assert cases["formula_with_uniform_translation_transform"]["report"]["conclusion"] == "validated"
    assert cases["failed_nonfinite_formula"]["report"]["conclusion"] == "failed"
    for name in ("affine_formula", "rational_formula", "trigonometric_formula"):
        assert cases[name]["report"]["candidate_kind"] == "formula_generator_family"
        assert cases[name]["report"]["conclusion"] == "partially_validated"
    assert not hasattr(pdelie, "run_formula_generator_validation_example")


def test_formula_generator_validation_module_prints_json_only() -> None:
    parsed = _run_module_json("pdelie.examples.formula_generator_validation")

    assert parsed["summary_type"] == "formula_generator_validation_example"
    assert len(parsed["cases"]) == 5
    assert "failed" in parsed["extra_metrics"]["conclusions"]
