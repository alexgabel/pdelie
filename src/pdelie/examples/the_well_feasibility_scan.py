"""v0.32d The Well feasibility scan (metadata-only, submodule-only).

Enumerates the datasets in The Well v1 release from the frozen catalogue at
``configs/external_data/the_well_feasibility_scan.json`` and reports whether
each admits a scientifically honest scalar 1D slice under PDELie's
(``batch``, ``time``, ``x``, ``var``) contract. The scan performs NO network
I/O — no partial downloads, no metadata queries, no head requests — and is
safe to run in default CI.

Every dataset in The Well v1 release is either 2D or 3D on a structured grid
and either carries multiple physically coupled channels or is coupled through
the geometry itself. The scan's frozen conclusion is
``blocked_multichannel_required``. This is the correct v0.32d result — not a
solvable gap. The v0.32d cookbook set does NOT drop channels, does NOT
average dimensions, and does NOT relabel a slice as a standalone PDE.

Non-goals: no broad ``from_the_well`` adapter; no adapter registry; no
model training; no recovery benchmark claim; no root ``pdelie`` re-export.
"""

from __future__ import annotations

import importlib.metadata as _importlib_metadata
import json
from pathlib import Path
from typing import Any

from pdelie.errors import SchemaValidationError

_SUMMARY_TYPE = "pdelie_the_well_feasibility_scan"
_SUMMARY_SCHEMA_VERSION = "0.1"

_CONFIG_PATH = (
    Path(__file__).resolve().parent
    / "_external_data"
    / "the_well_feasibility_scan.json"
)

_ALLOWED_CONCLUSIONS = frozenset(
    {
        "blocked_multichannel_required",
        "blocked_scan_metadata_missing",
    }
)


def load_the_well_feasibility_scan_config() -> dict[str, Any]:
    """Return the frozen v0.32d The Well feasibility scan config."""
    payload: dict[str, Any] = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    if json.loads(json.dumps(payload, allow_nan=False)) != payload:
        raise SchemaValidationError(
            "the_well_feasibility_scan config is not strict-JSON."
        )
    return payload


def _resolve_backend_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for dist_name, key in (
        ("pdelie", "pdelie"),
        ("numpy", "numpy"),
    ):
        try:
            versions[key] = _importlib_metadata.version(dist_name)
        except _importlib_metadata.PackageNotFoundError:
            continue
    return versions


def run_the_well_feasibility_scan() -> dict[str, Any]:
    """Run the metadata-only feasibility scan and return a strict-JSON report.

    Emits ``conclusion = "blocked_multichannel_required"`` because every
    dataset in The Well v1 release is either 2D or 3D and either carries
    multiple physically coupled channels or is geometrically coupled. The
    scan performs NO network I/O.
    """
    config = load_the_well_feasibility_scan_config()

    datasets_out: list[dict[str, Any]] = []
    for entry in config["datasets"]:
        datasets_out.append(
            {
                "dataset_name": entry["dataset_name"],
                "spatial_dimensionality": entry["spatial_dimensionality"],
                "variable_count_reported": entry["variable_count_reported"],
                "field_types": entry["field_types"],
                "coordinate_layout": entry["coordinate_layout"],
                "approximate_size": entry["approximate_size"],
                "scalar_1d_extractable": bool(entry["scalar_1d_extractable"]),
                "block_reason": entry["block_reason"],
            }
        )

    scalar_1d_count = sum(
        1 for entry in datasets_out if entry["scalar_1d_extractable"]
    )
    conclusion = (
        "blocked_multichannel_required" if scalar_1d_count == 0 else "blocked_scan_metadata_missing"
    )
    if conclusion not in _ALLOWED_CONCLUSIONS:
        raise SchemaValidationError(
            f"the_well_feasibility_scan conclusion {conclusion!r} outside "
            f"allowed vocabulary {sorted(_ALLOWED_CONCLUSIONS)}."
        )

    payload: dict[str, Any] = {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": _SUMMARY_TYPE,
        "source_project": config["source_project"],
        "release": config["release"],
        "citation": config["citation"],
        "record_url": config["record_url"],
        "code_url": config["code_url"],
        "policy": dict(config["policy"]),
        "datasets": datasets_out,
        "dataset_count": len(datasets_out),
        "scalar_1d_extractable_count": scalar_1d_count,
        "conclusion": conclusion,
        "conclusion_reason": config["conclusion_reason"],
        "conclusion_note": config["conclusion_note_ohana_2024_appendix"],
        "non_claims": list(config["non_claims"]),
        "provenance": {
            "config_slug": "the_well_feasibility_scan",
            "backend_versions": _resolve_backend_versions(),
        },
    }
    if json.loads(json.dumps(payload, allow_nan=False)) != payload:
        raise SchemaValidationError(
            "the_well_feasibility_scan report is not strict-JSON."
        )
    return payload


def main() -> None:
    print(json.dumps(run_the_well_feasibility_scan(), indent=2))


if __name__ == "__main__":
    main()
