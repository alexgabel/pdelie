from __future__ import annotations

import json

import numpy as np

from pdelie.data import generate_heat_1d_field_batch
from pdelie.invariants import build_uniform_translation_orbit_batch
from pdelie.reporting import (
    summarize_downstream_discovery_workflow,
    summarize_split_leakage_provenance,
)

_SUMMARY_SCHEMA_VERSION = "0.1"


def run_split_leakage_provenance_example() -> dict[str, object]:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=9, num_points=16, seed=23023)
    x = np.asarray(field.coords["x"], dtype=float)
    domain_length = float(x.size * (x[1] - x[0]))

    clean_split = summarize_split_leakage_provenance(
        partitions=["train", "heldout"],
        source_ids=["heat-source-0", "heat-source-1"],
        source_report_id="clean-user-split",
        extra_metrics={"case": "clean_user_supplied_split"},
    )

    orbit = build_uniform_translation_orbit_batch(
        field,
        shifts=[0.0, domain_length],
        source_field_id="heat-orbit-source",
    )
    traceable_overlap = summarize_split_leakage_provenance(
        partitions=["train", "train", "heldout", "heldout"],
        orbit_batch=orbit,
        source_ids=["heat-source-0", "heat-source-1"],
        source_report_id="orbit-overlap-split",
        extra_metrics={"case": "orbit_materialized_overlap"},
    )

    missing_orbit = build_uniform_translation_orbit_batch(
        field,
        shifts=[0.0, np.pi / 4.0],
        keep_source_index=False,
        keep_shift_index=False,
        source_field_id="heat-orbit-missing-provenance",
    )
    missing_provenance = summarize_split_leakage_provenance(
        partitions=["train", "heldout", "train", "heldout"],
        orbit_batch=missing_orbit,
        source_report_id="missing-provenance-split",
        extra_metrics={"case": "orbit_without_source_shift_indices"},
    )

    workflow = summarize_downstream_discovery_workflow(
        orbit_batch=orbit,
        split_provenance=traceable_overlap,
        extra_metrics={"example_name": "split_leakage_provenance"},
    )

    return {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": "split_leakage_provenance_example",
        "clean_split": clean_split,
        "traceable_overlap": traceable_overlap,
        "missing_provenance": missing_provenance,
        "workflow": workflow,
        "extra_metrics": {
            "example_name": "split_leakage_provenance",
            "clean_risk_label": clean_split["risk_label"],
            "overlap_risk_label": traceable_overlap["risk_label"],
            "missing_risk_label": missing_provenance["risk_label"],
            "split_policy": "not_managed_by_pdelie",
        },
    }


def main() -> None:
    print(json.dumps(run_split_leakage_provenance_example(), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
