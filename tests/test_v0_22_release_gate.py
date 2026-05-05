from __future__ import annotations

import importlib
import json
import re
import tomllib
from pathlib import Path

import numpy as np
import pdelie
from pdelie.data import generate_heat_1d_field_batch
from pdelie.discovery import (
    summarize_discovery_bridge_output,
    summarize_discovery_result,
    to_pysindy_trajectories,
)
from pdelie.examples import run_downstream_discovery_contracts_example
from pdelie.invariants import build_uniform_translation_orbit_batch
from pdelie.reporting import summarize_downstream_discovery_workflow, summarize_field_batch_readiness
from pdelie.residuals import HeatResidualEvaluator


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def _manual_result() -> dict[str, object]:
    return {
        "status": "success",
        "backend": "manual",
        "feature_names": ["u"],
        "library_feature_names": ["u_xx"],
        "coefficients": np.asarray([[0.1]], dtype=float),
        "equation_terms": {"u": {"u_xx": 0.1}},
        "equation_strings": {"u": "0.1*u_xx"},
        "fit_diagnostics": {"terms_are_backend_native": False, "canonicalized": True},
    }
def test_v0_22_release_gate_downstream_contract_apis_are_documented_and_submodule_only() -> None:
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    discovery_module = importlib.import_module("pdelie.discovery")
    reporting_module = importlib.import_module("pdelie.reporting")
    examples_module = importlib.import_module("pdelie.examples")

    assert hasattr(discovery_module, "summarize_discovery_bridge_output")
    assert hasattr(discovery_module, "summarize_discovery_result")
    assert hasattr(reporting_module, "summarize_downstream_discovery_workflow")
    assert hasattr(examples_module, "run_downstream_discovery_contracts_example")
    assert not hasattr(pdelie, "summarize_discovery_bridge_output")
    assert not hasattr(pdelie, "summarize_discovery_result")
    assert not hasattr(pdelie, "summarize_downstream_discovery_workflow")
    assert not hasattr(pdelie, "run_downstream_discovery_contracts_example")
    assert "pdelie.discovery.summarize_discovery_bridge_output" in api_stability
    assert "pdelie.discovery.summarize_discovery_result" in api_stability
    assert "pdelie.reporting.summarize_downstream_discovery_workflow" in api_stability
    assert "summary_type = \"discovery_bridge_output\"" in api_stability
    assert "summary_type = \"discovery_result\"" in api_stability
    assert "summary_type = \"downstream_discovery_workflow\"" in api_stability
    assert "no root `pdelie` exports" in api_stability


def test_v0_22_release_gate_reports_are_json_safe_and_compact() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=9, num_points=8, seed=22022)
    trajectories, time_values, feature_names = to_pysindy_trajectories(field)
    bridge = summarize_discovery_bridge_output(trajectories, time_values, feature_names)
    result = summarize_discovery_result(_manual_result(), target_terms={"u": {"u_xx": 0.1}})
    orbit = build_uniform_translation_orbit_batch(field, shifts=[0.0, 2.0 * np.pi])
    readiness = summarize_field_batch_readiness(field, residual_evaluator=HeatResidualEvaluator())
    workflow = summarize_downstream_discovery_workflow(
        field_readiness=readiness,
        orbit_batch=orbit,
        discovery_inputs=bridge,
        discovery_result=result,
    )

    assert json.loads(json.dumps(bridge)) == bridge
    assert json.loads(json.dumps(result)) == result
    assert json.loads(json.dumps(workflow)) == workflow
    assert bridge["summary_type"] == "discovery_bridge_output"
    assert result["summary_type"] == "discovery_result"
    assert "coefficients" not in result
    assert result["coefficient_summary"]["shape"] == [1, 1]
    assert result["recovery"]["aggregate"]["exact_count"] == 1
    assert workflow["summary_type"] == "downstream_discovery_workflow"
    assert workflow["component_statuses"]["orbit_provenance"]["status"] == "passed"


def test_v0_22_release_gate_example_outputs_downstream_workflow() -> None:
    result = run_downstream_discovery_contracts_example()

    assert json.loads(json.dumps(result)) == result
    assert result["summary_type"] == "downstream_discovery_contracts_example"
    assert result["workflow"]["summary_type"] == "downstream_discovery_workflow"
    assert result["discovery_inputs"]["summary_type"] == "discovery_bridge_output"
    assert result["discovery_result"]["summary_type"] == "discovery_result"
    assert result["extra_metrics"]["split_policy"] == "not_managed_by_pdelie"


def test_v0_22_release_gate_no_deferred_surface_leaked() -> None:
    root_forbidden = {
        "run_downstream_discovery_contracts_example",
        "summarize_discovery_bridge_output",
        "summarize_discovery_result",
        "summarize_downstream_discovery_workflow",
    }
    deferred_forbidden = {
        "from_pdebench",
        "from_the_well",
        "generate_ks_1d_field_batch",
        "KSResidualEvaluator",
        "load_field_batch",
        "load_pdebench",
        "load_the_well",
        "split_orbit_train_heldout",
        "summarize_discovery_benchmark",
        "train_test_translation_orbit_split",
        "WeakKSResidualEvaluator",
    }

    for name in sorted(root_forbidden | deferred_forbidden):
        assert not hasattr(pdelie, name), f"pdelie.{name}"

    modules = [
        importlib.import_module("pdelie.data"),
        importlib.import_module("pdelie.discovery"),
        importlib.import_module("pdelie.invariants"),
        importlib.import_module("pdelie.reporting"),
        importlib.import_module("pdelie.residuals"),
        importlib.import_module("pdelie.symmetry"),
    ]
    for module in modules:
        for name in sorted(deferred_forbidden):
            assert not hasattr(module, name), f"{module.__name__}.{name}"
