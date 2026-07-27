from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import pytest

import pdelie
from pdelie.contracts import FieldBatch
from pdelie.data import generate_heat_1d_field_batch
from pdelie.errors import SchemaValidationError
from pdelie.examples import run_split_leakage_provenance_example
from pdelie.invariants import build_uniform_translation_orbit_batch
from pdelie.reporting import (
    summarize_downstream_discovery_workflow,
    summarize_split_leakage_provenance,
)


def _assert_json_safe_plain(value: Any) -> None:
    json.loads(json.dumps(value, allow_nan=False))
    if isinstance(value, FieldBatch):
        raise TypeError("reports must not contain FieldBatch objects")
    if isinstance(value, Mapping):
        for item in value.values():
            _assert_json_safe_plain(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            _assert_json_safe_plain(item)


def test_split_provenance_no_detected_overlap_with_user_source_ids() -> None:
    report = summarize_split_leakage_provenance(
        partitions=["train", "train", "heldout"],
        source_ids=["source-0", "source-1", "source-2"],
        sample_metadata=[
            {"row": 0, "source": "source-0"},
            {"row": 1, "source": "source-1"},
            {"row": 2, "source": "source-2"},
        ],
        source_report_id="manual-split",
        extra_metrics={"purpose": "unit-test"},
    )

    _assert_json_safe_plain(report)
    assert report["summary_schema_version"] == "0.1"
    assert report["summary_type"] == "split_leakage_provenance"
    assert report["partition_counts"] == {"train": 2, "heldout": 1}
    assert report["sample_count"] == 3
    assert report["risk_label"] == "no_detected_overlap"
    assert report["duplicate_source_across_partitions"] is False
    assert report["duplicate_shifted_source_across_partitions"] is False
    assert report["identity_shift_cross_partition_overlap"] is False
    assert report["source_id_traceable"] is True
    assert report["source_index_traceable"] is False
    assert report["returns_field_batch"] is False
    assert report["policy"]["creates_splits"] is False
    assert report["policy"]["prevents_leakage"] is False


def test_split_provenance_rejects_invalid_inputs_and_nonstandard_json() -> None:
    with pytest.raises(SchemaValidationError):
        summarize_split_leakage_provenance(partitions=[])
    with pytest.raises(SchemaValidationError):
        summarize_split_leakage_provenance(partitions=["train", ""])
    with pytest.raises(SchemaValidationError):
        summarize_split_leakage_provenance(partitions=["train", 1])  # type: ignore[list-item]
    with pytest.raises(SchemaValidationError):
        summarize_split_leakage_provenance(partitions=["train"], source_ids=["a", "b"])
    with pytest.raises(SchemaValidationError):
        summarize_split_leakage_provenance(partitions=["train"], sample_metadata=[{"bad": float("nan")}])
    with pytest.raises(SchemaValidationError):
        summarize_split_leakage_provenance(partitions=["train"], extra_metrics={"bad": np.inf})
    with pytest.raises(SchemaValidationError):
        summarize_split_leakage_provenance(
            partitions=["train"],
            orbit_batch={
                "summary_type": "uniform_translation_orbit_batch",
                "output_batch_size": 1,
                "source_batch_indices": [0],
                "shift_indices": [0],
                "raw_shifts": [float("nan")],
            },
        )
    with pytest.raises(SchemaValidationError):
        summarize_split_leakage_provenance(
            partitions=["train"],
            orbit_batch={
                "summary_type": "uniform_translation_orbit_batch",
                "output_batch_size": 1,
                "source_batch_indices": [0.0],
                "shift_indices": [0],
                "raw_shifts": [0.0],
            },
        )


def test_split_provenance_detects_source_overlap_across_partitions() -> None:
    report = summarize_split_leakage_provenance(
        partitions=["train", "heldout", "validation"],
        source_ids=["same-source", "same-source", "other-source"],
    )

    assert report["risk_label"] == "traceable_overlap"
    assert report["duplicate_source_across_partitions"] is True
    assert report["duplicate_shifted_source_across_partitions"] is False
    assert report["partition_pair_diagnostics"]["heldout|train"]["source_overlap_count"] == 1
    assert "source_overlap_across_partitions" in report["risk_reasons"]


def test_split_provenance_accepts_orbit_batch_result_and_reports_identity_shift_overlap() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=9, num_points=16, seed=23001)
    x = np.asarray(field.coords["x"], dtype=float)
    domain_length = float(x.size * (x[1] - x[0]))
    orbit = build_uniform_translation_orbit_batch(field, shifts=[0.0, domain_length])

    report = summarize_split_leakage_provenance(
        partitions=["train", "train", "heldout", "heldout"],
        orbit_batch=orbit,
        source_ids=["source-0", "source-1"],
    )

    _assert_json_safe_plain(report)
    assert report["provenance_available"] is True
    assert report["source_index_traceable"] is True
    assert report["shift_index_traceable"] is True
    assert report["risk_label"] == "traceable_overlap"
    assert report["duplicate_source_across_partitions"] is True
    assert report["identity_shift_cross_partition_overlap"] is True
    assert report["duplicate_shifted_source_across_partitions"] is False
    assert report["partition_pair_diagnostics"]["heldout|train"]["identity_shift_overlap_count"] == 2


def test_split_provenance_accepts_orbit_batch_report_and_distinguishes_same_shift_overlap() -> None:
    orbit_report = {
        "summary_schema_version": "0.1",
        "summary_type": "uniform_translation_orbit_batch",
        "output_batch_size": 2,
        "source_batch_size": 1,
        "source_batch_indices": [0, 0],
        "shift_indices": [0, 0],
        "raw_shifts": [0.0],
        "normalized_shifts": [0.0],
    }

    report = summarize_split_leakage_provenance(
        partitions=["train", "heldout"],
        orbit_batch=orbit_report,
        source_ids=["source-0"],
    )

    assert report["risk_label"] == "traceable_overlap"
    assert report["duplicate_source_across_partitions"] is True
    assert report["duplicate_shifted_source_across_partitions"] is True
    assert report["identity_shift_cross_partition_overlap"] is True
    pair = report["partition_pair_diagnostics"]["heldout|train"]
    assert pair["source_overlap_count"] == 1
    assert pair["shifted_source_overlap_count"] == 1
    assert pair["identity_shift_overlap_count"] == 1


def test_split_provenance_missing_or_partial_orbit_provenance_is_not_policy() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=9, num_points=16, seed=23002)
    orbit = build_uniform_translation_orbit_batch(
        field,
        shifts=[0.0, np.pi / 4.0],
        keep_source_index=False,
        keep_shift_index=False,
    )

    missing = summarize_split_leakage_provenance(
        partitions=["train", "heldout", "train", "heldout"],
        orbit_batch=orbit,
    )
    partial = summarize_split_leakage_provenance(
        partitions=["train", "heldout"],
        orbit_batch={
            "summary_schema_version": "0.1",
            "summary_type": "uniform_translation_orbit_batch",
            "output_batch_size": 2,
            "source_batch_indices": None,
            "shift_indices": [0, 1],
            "raw_shifts": [0.0, 0.1],
            "normalized_shifts": [0.0, 0.1],
        },
    )

    assert missing["risk_label"] == "missing_provenance"
    assert missing["policy"]["creates_splits"] is False
    assert missing["policy"]["prevents_leakage"] is False
    assert partial["risk_label"] == "inconclusive"


def test_split_provenance_rejects_partition_or_source_count_mismatch() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=9, num_points=16, seed=23003)
    orbit = build_uniform_translation_orbit_batch(field, shifts=[0.0, np.pi / 4.0])

    with pytest.raises(SchemaValidationError):
        summarize_split_leakage_provenance(partitions=["train"], orbit_batch=orbit)
    with pytest.raises(SchemaValidationError):
        summarize_split_leakage_provenance(
            partitions=["train", "train", "heldout", "heldout"],
            orbit_batch=orbit,
            source_ids=["only-one-source-id"],
        )


def test_downstream_workflow_nests_split_provenance_report() -> None:
    split_report = summarize_split_leakage_provenance(
        partitions=["train", "heldout"],
        source_ids=["same", "same"],
    )
    workflow = summarize_downstream_discovery_workflow(split_provenance=split_report)

    _assert_json_safe_plain(workflow)
    assert workflow["summary_type"] == "downstream_discovery_workflow"
    assert workflow["split_provenance"]["summary_type"] == "split_leakage_provenance"
    assert workflow["component_statuses"]["split_provenance"]["status"] == "warning"
    assert workflow["workflow_label"] == "needs_attention"

    with pytest.raises(SchemaValidationError):
        summarize_downstream_discovery_workflow(split_provenance={"summary_type": "discovery_result"})


def test_split_leakage_provenance_example_is_json_only_and_report_only() -> None:
    result = run_split_leakage_provenance_example()

    _assert_json_safe_plain(result)
    assert result["summary_type"] == "split_leakage_provenance_example"
    assert result["clean_split"]["risk_label"] == "no_detected_overlap"
    assert result["traceable_overlap"]["risk_label"] == "traceable_overlap"
    assert result["missing_provenance"]["risk_label"] == "missing_provenance"
    assert result["workflow"]["split_provenance"]["summary_type"] == "split_leakage_provenance"
    assert result["extra_metrics"]["split_policy"] == "not_managed_by_pdelie"
    assert not hasattr(pdelie, "run_split_leakage_provenance_example")
    assert not hasattr(pdelie, "summarize_split_leakage_provenance")

    completed = subprocess.run(
        [sys.executable, "-m", "pdelie.examples.split_leakage_provenance"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stderr == ""
    parsed = json.loads(completed.stdout)
    assert parsed["summary_type"] == "split_leakage_provenance_example"
