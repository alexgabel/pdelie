from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie.data import generate_heat_1d_field_batch
from pdelie.discovery import (
    summarize_discovery_bridge_output,
    summarize_discovery_result,
    to_pysindy_trajectories,
)
from pdelie.errors import SchemaValidationError
from pdelie.examples import run_downstream_discovery_contracts_example
from pdelie.invariants import build_uniform_translation_orbit_batch
from pdelie.reporting import (
    summarize_downstream_discovery_workflow,
    summarize_field_batch_readiness,
    summarize_generator_confidence,
)
from pdelie.residuals import HeatResidualEvaluator


def _manual_result(*, status: str = "success", coefficients: object = [[0.1]]) -> dict[str, object]:
    if status == "failed":
        return {
            "status": "failed",
            "backend": "manual",
            "feature_names": ["u"],
            "library_feature_names": [],
            "coefficients": None,
            "equation_terms": {},
            "equation_strings": {},
            "fit_diagnostics": {"exception_type": "RuntimeError"},
            "failure_reason": "backend_fit_failed",
        }
    return {
        "status": "success",
        "backend": "manual",
        "feature_names": ["u"],
        "library_feature_names": ["u_xx"],
        "coefficients": coefficients,
        "equation_terms": {"u": {"u_xx": 0.1}},
        "equation_strings": {"u": "0.1*u_xx"},
        "fit_diagnostics": {"terms_are_backend_native": False, "canonicalized": True},
    }


def test_summarize_discovery_bridge_output_accepts_pysindy_bridge_shape_and_is_json_safe() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=9, num_points=8, seed=22001)
    trajectories, time_values, feature_names = to_pysindy_trajectories(field)

    summary = summarize_discovery_bridge_output(
        trajectories,
        time_values,
        feature_names,
        source_field_id="field-1",
        provenance={"bridge": "to_pysindy_trajectories"},
    )

    assert json.loads(json.dumps(summary)) == summary
    assert summary["summary_schema_version"] == "0.1"
    assert summary["summary_type"] == "discovery_bridge_output"
    assert summary["trajectory_count"] == 2
    assert summary["trajectory_shape"] == [9, 8]
    assert summary["feature_names"] == feature_names
    assert summary["strictly_increasing_time"] is True
    assert summary["finite"] is True
    assert summary["returns_field_batch"] is False


def test_summarize_discovery_bridge_output_rejects_invalid_bridge_payloads() -> None:
    with pytest.raises(SchemaValidationError):
        summarize_discovery_bridge_output([], [0.0, 1.0], ["u"])
    with pytest.raises(SchemaValidationError):
        summarize_discovery_bridge_output([np.ones((2, 1)), np.ones((3, 1))], [0.0, 1.0], ["u"])
    with pytest.raises(SchemaValidationError):
        summarize_discovery_bridge_output([np.ones((2, 1))], [0.0, 0.0], ["u"])
    with pytest.raises(SchemaValidationError):
        summarize_discovery_bridge_output([np.ones((2, 1))], [0.0, 1.0], ["u", "u"])
    with pytest.raises(SchemaValidationError):
        summarize_discovery_bridge_output([np.array([[np.nan]])], [0.0], ["u"])
    with pytest.raises(SchemaValidationError):
        summarize_discovery_bridge_output(
            [np.ones((2, 1))],
            [0.0, 1.0],
            ["u"],
            provenance={"bad": float("nan")},
        )


def test_summarize_discovery_result_compacts_coefficients_and_recovery() -> None:
    result = _manual_result(coefficients=np.asarray([[0.1, 0.0]]))
    result["library_feature_names"] = ["u_xx", "u"]
    summary = summarize_discovery_result(
        result,
        target_terms={"u": {"u_xx": 0.1}},
        train_residual=[0.0, 1e-3],
        heldout_residual=[0.0, 2e-3],
        source_result_id="result-1",
    )

    assert json.loads(json.dumps(summary)) == summary
    assert summary["summary_type"] == "discovery_result"
    assert summary["status"] == "success"
    assert summary["coefficient_summary"]["shape"] == [1, 2]
    assert summary["coefficient_summary"]["nonzero_count"] == 1
    assert "coefficients" not in summary
    assert summary["returns_coefficients"] is False
    assert summary["recovery"]["aggregate"]["exact_count"] == 1
    assert summary["recovery"]["by_feature"]["u"]["classification"] == "exact"
    assert summary["residuals"]["heldout"]["rms"] > 0.0


def test_summarize_discovery_result_accepts_backend_failure_mapping() -> None:
    summary = summarize_discovery_result(_manual_result(status="failed"))

    assert summary["summary_type"] == "discovery_result"
    assert summary["status"] == "failed"
    assert summary["failure_reason"] == "backend_fit_failed"
    assert summary["coefficient_summary"]["present"] is False
    assert summary["equation_terms"] == {"u": {}}


def test_summarize_discovery_result_rejects_ambiguous_target_and_nonfinite_values() -> None:
    with pytest.raises(SchemaValidationError):
        summarize_discovery_result(_manual_result(), target_terms={"u_xx": 0.1})  # type: ignore[arg-type]
    with pytest.raises(SchemaValidationError):
        summarize_discovery_result(_manual_result(coefficients=[[np.nan]]))
    with pytest.raises(SchemaValidationError):
        summarize_discovery_result(_manual_result(), support_epsilon=-1.0)
    malformed = dict(_manual_result())
    malformed.pop("equation_terms")
    with pytest.raises(SchemaValidationError):
        summarize_discovery_result(malformed)


def test_summarize_downstream_discovery_workflow_combines_reports_and_orbit_provenance() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=9, num_points=8, seed=22002)
    trajectories, time_values, feature_names = to_pysindy_trajectories(field)
    readiness = summarize_field_batch_readiness(field, residual_evaluator=HeatResidualEvaluator())
    confidence = summarize_generator_confidence(
        fit_diagnostics={
            "summary_schema_version": "0.1",
            "summary_type": "generator_fit_diagnostics",
            "evidence_label": "reference_fallback",
        }
    )
    orbit = build_uniform_translation_orbit_batch(field, shifts=[0.0, 2.0 * np.pi])
    bridge = summarize_discovery_bridge_output(trajectories, time_values, feature_names)
    result = summarize_discovery_result(_manual_result(), target_terms={"u": {"u_xx": 0.1}})

    workflow = summarize_downstream_discovery_workflow(
        field_readiness=readiness,
        generator_confidence=confidence,
        orbit_batch=orbit,
        discovery_inputs=bridge,
        discovery_result=result,
    )

    assert json.loads(json.dumps(workflow)) == workflow
    assert workflow["summary_type"] == "downstream_discovery_workflow"
    assert workflow["workflow_label"] == "needs_attention"
    assert workflow["component_statuses"]["orbit_provenance"]["status"] == "passed"
    assert workflow["orbit_provenance"]["source_indices_present"] is True
    assert workflow["orbit_provenance"]["shift_indices_present"] is True


def test_summarize_downstream_discovery_workflow_rejects_malformed_nested_reports() -> None:
    with pytest.raises(SchemaValidationError):
        summarize_downstream_discovery_workflow(discovery_inputs={"summary_type": "discovery_result"})
    with pytest.raises(SchemaValidationError):
        summarize_downstream_discovery_workflow(orbit_batch={"summary_type": "uniform_translation_orbit"})


def test_downstream_discovery_contracts_example_is_json_safe_and_report_only() -> None:
    result = run_downstream_discovery_contracts_example()

    assert json.loads(json.dumps(result)) == result
    assert result["summary_type"] == "downstream_discovery_contracts_example"
    assert result["workflow"]["summary_type"] == "downstream_discovery_workflow"
    assert result["discovery_inputs"]["returns_field_batch"] is False
    assert result["discovery_result"]["returns_coefficients"] is False
    assert result["extra_metrics"]["split_policy"] == "not_managed_by_pdelie"
