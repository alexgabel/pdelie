from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import numpy as np

from pdelie.errors import SchemaValidationError


_REQUIRED_RECOVERY_NUMERIC_FIELDS = (
    "support_precision",
    "support_recall",
    "support_f1",
    "target_sparsity",
    "discovered_sparsity",
    "coefficient_l2_error",
    "coefficient_relative_l2_error",
    "coefficient_linf_error",
)
_OPTIONAL_RESIDUAL_FIELDS = (
    "train_residual_l2",
    "heldout_residual_l2",
    "heldout_residual_rms",
)
_ALLOWED_CLASSIFICATIONS = frozenset({"exact", "partial", "failed"})


def _validate_mapping(value: object, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{name} must be a mapping.")
    return value


def _normalize_condition_value(key: str, value: object) -> object:
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        normalized = float(value)
        if not np.isfinite(normalized):
            raise SchemaValidationError(f"conditions[{key!r}] must be finite when provided as a float.")
        return normalized
    if isinstance(value, str):
        return value
    raise SchemaValidationError(
        f"conditions[{key!r}] must be a JSON-scalar value (str, bool, int, finite float, or None)."
    )


def _condition_sort_token(value: object) -> tuple[str, str]:
    if value is None:
        return ("none", "None")
    if isinstance(value, bool):
        return ("bool", repr(value))
    if isinstance(value, int):
        return ("int", repr(value))
    if isinstance(value, float):
        return ("float", repr(value))
    return ("str", repr(value))


def _normalize_conditions(value: object) -> tuple[dict[str, object], tuple[tuple[str, str, str], ...]]:
    mapping = _validate_mapping(value, name="conditions")
    normalized: dict[str, object] = {}
    for key, condition_value in mapping.items():
        if not isinstance(key, str) or not key:
            raise SchemaValidationError("conditions keys must be non-empty strings.")
        normalized[key] = _normalize_condition_value(key, condition_value)

    sorted_keys = sorted(normalized)
    ordered_conditions = {key: normalized[key] for key in sorted_keys}
    group_key = tuple((key, *_condition_sort_token(ordered_conditions[key])) for key in sorted_keys)
    return ordered_conditions, group_key


def _validate_numeric_scalar(value: object, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise SchemaValidationError(f"{name} must be a finite numeric scalar.")
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{name} must be a finite numeric scalar.") from exc
    if not np.isfinite(normalized):
        raise SchemaValidationError(f"{name} must be a finite numeric scalar.")
    return normalized


def _normalize_recovery(value: object) -> dict[str, object]:
    mapping = _validate_mapping(value, name="recovery")
    missing = [
        key for key in ("classification", *_REQUIRED_RECOVERY_NUMERIC_FIELDS) if key not in mapping
    ]
    if missing:
        raise SchemaValidationError(f"recovery is missing required fields: {missing}.")

    classification = mapping["classification"]
    if not isinstance(classification, str) or classification not in _ALLOWED_CLASSIFICATIONS:
        raise SchemaValidationError("recovery['classification'] must be one of: exact, partial, failed.")

    normalized: dict[str, object] = {"classification": classification}
    for key in _REQUIRED_RECOVERY_NUMERIC_FIELDS:
        normalized[key] = _validate_numeric_scalar(mapping[key], name=f"recovery[{key!r}]")

    for key in _OPTIONAL_RESIDUAL_FIELDS:
        if key in mapping:
            normalized[key] = _validate_numeric_scalar(mapping[key], name=f"recovery[{key!r}]")

    return normalized


def summarize_recovery_grid(records: Iterable[object]) -> list[dict[str, object]]:
    grouped: dict[tuple[tuple[str, str, str], ...], dict[str, object]] = {}

    for index, raw_record in enumerate(records):
        record = _validate_mapping(raw_record, name=f"records[{index}]")
        if "conditions" not in record or "recovery" not in record:
            raise SchemaValidationError("Each record must include 'conditions' and 'recovery' mappings.")

        conditions, group_key = _normalize_conditions(record["conditions"])
        recovery = _normalize_recovery(record["recovery"])
        group = grouped.setdefault(group_key, {"conditions": conditions, "records": []})
        records_list = group["records"]
        assert isinstance(records_list, list)
        records_list.append(recovery)

    rows: list[dict[str, object]] = []
    for group_key in sorted(grouped):
        group = grouped[group_key]
        group_records = group["records"]
        assert isinstance(group_records, list)
        num_records = len(group_records)
        exact_count = sum(1 for record in group_records if record["classification"] == "exact")
        partial_count = sum(1 for record in group_records if record["classification"] == "partial")
        failed_count = sum(1 for record in group_records if record["classification"] == "failed")

        row: dict[str, object] = {
            "conditions": group["conditions"],
            "num_records": num_records,
            "exact_count": exact_count,
            "partial_count": partial_count,
            "failed_count": failed_count,
            "exact_rate": float(exact_count / num_records),
            "partial_rate": float(partial_count / num_records),
            "failed_rate": float(failed_count / num_records),
        }

        for key in _REQUIRED_RECOVERY_NUMERIC_FIELDS:
            values = np.asarray([record[key] for record in group_records], dtype=float)
            row[f"mean_{key}"] = float(np.mean(values))

        for key in _OPTIONAL_RESIDUAL_FIELDS:
            if all(key in record for record in group_records):
                values = np.asarray([record[key] for record in group_records], dtype=float)
                row[f"mean_{key}"] = float(np.mean(values))

        rows.append(row)

    return rows
