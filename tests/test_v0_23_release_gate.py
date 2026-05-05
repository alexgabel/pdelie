from __future__ import annotations

import importlib
import json
import re
import tomllib
from pathlib import Path

import numpy as np
import pdelie
from pdelie.data import generate_heat_1d_field_batch
from pdelie.examples import run_split_leakage_provenance_example
from pdelie.invariants import build_uniform_translation_orbit_batch
from pdelie.reporting import summarize_downstream_discovery_workflow, summarize_split_leakage_provenance


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")
def test_v0_23_release_gate_split_provenance_api_is_documented_and_submodule_only() -> None:
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    reporting_module = importlib.import_module("pdelie.reporting")
    examples_module = importlib.import_module("pdelie.examples")

    assert hasattr(reporting_module, "summarize_split_leakage_provenance")
    assert hasattr(examples_module, "run_split_leakage_provenance_example")
    assert not hasattr(pdelie, "summarize_split_leakage_provenance")
    assert not hasattr(pdelie, "run_split_leakage_provenance_example")
    assert "pdelie.reporting.summarize_split_leakage_provenance" in api_stability
    assert "summary_type = \"split_leakage_provenance\"" in api_stability
    assert "no_detected_overlap" in api_stability
    assert "traceable_overlap" in api_stability
    assert "missing_provenance" in api_stability
    assert "inconclusive" in api_stability
    assert "these APIs have no root `pdelie` exports" in api_stability


def test_v0_23_release_gate_split_provenance_reports_overlap_and_no_policy() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=9, num_points=16, seed=23023)
    x = np.asarray(field.coords["x"], dtype=float)
    domain_length = float(x.size * (x[1] - x[0]))
    orbit = build_uniform_translation_orbit_batch(field, shifts=[0.0, domain_length])

    split = summarize_split_leakage_provenance(
        partitions=["train", "train", "heldout", "heldout"],
        orbit_batch=orbit,
        source_ids=["source-0", "source-1"],
    )
    clean = summarize_split_leakage_provenance(
        partitions=["train", "heldout"],
        source_ids=["source-0", "source-1"],
    )
    workflow = summarize_downstream_discovery_workflow(orbit_batch=orbit, split_provenance=split)

    assert json.loads(json.dumps(split, allow_nan=False)) == split
    assert json.loads(json.dumps(clean, allow_nan=False)) == clean
    assert json.loads(json.dumps(workflow, allow_nan=False)) == workflow
    assert split["summary_type"] == "split_leakage_provenance"
    assert split["risk_label"] == "traceable_overlap"
    assert split["duplicate_source_across_partitions"] is True
    assert split["identity_shift_cross_partition_overlap"] is True
    assert clean["risk_label"] == "no_detected_overlap"
    assert split["policy"]["creates_splits"] is False
    assert split["policy"]["prevents_leakage"] is False
    assert workflow["split_provenance"]["summary_type"] == "split_leakage_provenance"
    assert workflow["component_statuses"]["split_provenance"]["status"] == "warning"


def test_v0_23_release_gate_example_outputs_split_provenance_summary() -> None:
    result = run_split_leakage_provenance_example()

    assert json.loads(json.dumps(result, allow_nan=False)) == result
    assert result["summary_type"] == "split_leakage_provenance_example"
    assert result["clean_split"]["risk_label"] == "no_detected_overlap"
    assert result["traceable_overlap"]["risk_label"] == "traceable_overlap"
    assert result["missing_provenance"]["risk_label"] == "missing_provenance"
    assert result["workflow"]["split_provenance"]["summary_type"] == "split_leakage_provenance"
    assert result["extra_metrics"]["split_policy"] == "not_managed_by_pdelie"


def test_v0_23_release_gate_no_deferred_surface_leaked() -> None:
    forbidden = {
        "from_pdebench",
        "from_the_well",
        "generate_ks_1d_field_batch",
        "KSResidualEvaluator",
        "load_field_batch",
        "load_pdebench",
        "load_the_well",
        "split_leakage_enforcer",
        "split_orbit_train_heldout",
        "summarize_leakage_prevention",
        "train_test_translation_orbit_split",
        "WeakKSResidualEvaluator",
    }

    for name in sorted(forbidden | {"run_split_leakage_provenance_example", "summarize_split_leakage_provenance"}):
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
        for name in sorted(forbidden):
            assert not hasattr(module, name), f"{module.__name__}.{name}"
