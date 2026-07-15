from __future__ import annotations

import importlib
import json
from collections.abc import Mapping, Sequence
from itertools import combinations
from numbers import Integral
from typing import Any

import numpy as np

from pdelie._boundary import get_x_boundary_type
from pdelie.contracts import (
    REQUIRED_METADATA_KEYS,
    DerivativeBatch,
    FieldBatch,
    GeneratorFamily,
    ResidualBatch,
    VerificationReport,
)
from pdelie.errors import PDELieValidationError, SchemaValidationError, ScopeValidationError
from pdelie.invariants import OrbitBatchResult
from pdelie.residuals.base import ResidualEvaluator
from pdelie.symmetry.formula import FormulaGeneratorFamily
from pdelie.symmetry.parameterization import translation_span_distance
from pdelie.symmetry.parameterization.polynomial_translation import DEFAULT_TRANSLATION_SPAN_TOLERANCE

_SUMMARY_SCHEMA_VERSION = "0.1"
_FIT_EVIDENCE_LABELS = frozenset(
    {
        "direct_svd_in_tolerance",
        "direct_svd_out_of_tolerance",
        "reference_fallback",
        "mixed",
        "unavailable",
    }
)
_CONFIDENCE_LABELS = frozenset({"strong", "qualified", "failed", "insufficient_evidence"})
_CONFIDENCE_COMPONENT_STATUSES = frozenset({"passed", "warning", "failed", "not_configured", "unavailable"})
_READINESS_LABELS = frozenset({"ready", "needs_attention", "not_ready"})
_BOUNDARY_CONDITION_WARNING_KEYS = frozenset(
    {
        "x_boundary_legacy_string_under_schema_0_2",
        "x_boundary_open_unknown",
        "x_boundary_dirichlet_unspecified",
        "x_boundary_neumann_unspecified",
    }
)

# --- v0.32b: additive generator-confidence field vocabularies ---------------
# See docs/design/GENERATOR_CONFIDENCE_ADDITIVE_FIELDS.md for the frozen shapes.
_METHOD_SCORE_DIRECTIONS = frozenset(
    {"lower_is_better", "higher_is_better", "diagnostic_only"}
)
_METHOD_SCORE_ENTRY_KEYS = frozenset(
    {"value", "direction", "description", "units"}
)
_UNCERTAINTY_METHOD_VOCABULARY = frozenset({"bootstrap", "point_estimate"})
_UNCERTAINTY_RESAMPLING_UNITS = frozenset(
    {"batch", "trajectory", "not_applicable"}
)
_UNCERTAINTY_REPORT_KEYS = frozenset(
    {
        "method",
        "resampling_unit",
        "sample_count",
        "seed",
        "interval_level",
        "intervals",
        "point_estimates",
        "failed_resamples",
        "warnings",
        "diagnostic_only",
    }
)
_CALIBRATION_REPORT_KEYS = frozenset(
    {
        "method",
        "target",
        "sample_count",
        "metrics",
        "warnings",
        "diagnostic_only",
    }
)


def _x_boundary_warnings(metadata: object) -> list[str]:
    """Return the v0.30c boundary_condition_warnings list for a FieldBatch/Dataset metadata.

    Warnings, not failures: nonperiodic boundaries are accepted but signal that
    downstream derivative and residual support is still strict-periodic.

    Empty for periodic (legacy string or structured). Empty for malformed/missing
    boundary metadata (those cases are reported separately by the metadata
    failures list).
    """
    if not isinstance(metadata, Mapping):
        return []
    bcs = metadata.get("boundary_conditions")
    if not isinstance(bcs, Mapping):
        return []
    x_bc = bcs.get("x")
    try:
        canonical = get_x_boundary_type({"boundary_conditions": bcs})
    except (ScopeValidationError, SchemaValidationError):
        return []

    warnings: list[str] = []
    if isinstance(x_bc, str):
        # Legacy 0.1 string form embedded in a 0.2 FieldBatch; recommend structured form
        # for any nonperiodic type (the structured form is the only way to record
        # `specified=True` for dirichlet/neumann).
        if canonical != "periodic":
            warnings.append("x_boundary_legacy_string_under_schema_0_2")
            if canonical == "open_unknown":
                warnings.append("x_boundary_open_unknown")
            elif canonical in {"dirichlet", "neumann"}:
                warnings.append(f"x_boundary_{canonical}_unspecified")
        return warnings

    # Structured dict form
    if canonical == "periodic":
        return warnings
    if canonical == "open_unknown":
        warnings.append("x_boundary_open_unknown")
        return warnings
    if canonical in {"dirichlet", "neumann"}:
        specified = x_bc.get("specified") if isinstance(x_bc, Mapping) else None
        if specified is not True:
            warnings.append(f"x_boundary_{canonical}_unspecified")
        return warnings
    return warnings  # pragma: no cover — guarded by get_x_boundary_type allowlist
_SPLIT_LEAKAGE_RISK_LABELS = frozenset(
    {
        "no_detected_overlap",
        "traceable_overlap",
        "missing_provenance",
        "inconclusive",
    }
)
_WEAK_FORM_SUPPORTABILITY_LABELS = frozenset(
    {
        "supported_existing_slice",
        "diagnostic_only",
        "failed",
        "insufficient_evidence",
    }
)
_CONFIDENCE_THRESHOLD_KEYS = frozenset(
    {
        "residual_max_abs",
        "residual_rms",
        "verification_first_error",
        "verification_max_error",
        "coverage_fraction_min",
    }
)
_WEAK_REPORT_KEYS = frozenset(
    {
        "equation",
        "equation_form",
        "method_family",
        "window_residuals",
        "time_window_centers",
        "x_window_centers",
        "normalization",
        "diagnostics",
    }
)
_WEAK_SUPPORTABILITY_THRESHOLD_KEYS = frozenset(
    {
        "weak_report_max_abs",
        "weak_report_rms",
        "weak_report_l2",
        "finite_required",
        "min_weak_rows",
        "max_skipped_fraction",
        "imported_parity_abs_tol",
        "imported_parity_rel_tol",
        "robustness_required_cases",
    }
)
_WEAK_CONTRACT_FIELDS = (
    "schema_version",
    "equation",
    "equation_form",
    "test_function_family",
    "test_function_order",
    "operator_order_supported",
    "integration_by_parts_depth",
    "boundary_vanishing_order",
    "patch_shape",
    "patch_stride",
    "quadrature_rule",
    "normalization",
    "valid_window_policy",
    "row_count",
    "skipped_patch_count",
    "finite_value_policy",
)
_FROZEN_PUBLIC_WEAK_EQUATIONS = frozenset({"heat_1d", "burgers_1d"})
_XARRAY_DATASET_ACCEPTED_LAYOUTS = frozenset(
    {
        ("time", "x"),
        ("batch", "time", "x"),
        ("time", "x", "var"),
        ("batch", "time", "x", "var"),
    }
)

def _json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _validate_json_compatible(value: Any, *, name: str) -> Any:
    safe_value = _json_safe(value)
    try:
        json.dumps(safe_value)
    except TypeError as exc:
        raise SchemaValidationError(f"{name} must be JSON-compatible after reporting conversion.") from exc
    return safe_value


def _validate_strict_json_compatible(value: Any, *, name: str) -> Any:
    safe_value = _json_safe(value)
    try:
        json.dumps(safe_value, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{name} must be strict JSON-compatible after reporting conversion.") from exc
    return safe_value


def _require_finite(array: np.ndarray, *, name: str) -> np.ndarray:
    normalized = np.asarray(array, dtype=float)
    if not np.all(np.isfinite(normalized)):
        raise ScopeValidationError(f"{name} must contain finite values.")
    return normalized


def _require_mapping(value: object, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{name} must be a mapping.")
    return value


def _finite_float_or_none(value: Any, *, name: str) -> float | None:
    if value is None:
        return None
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(
            f"{name} must be a float-like value or None; non-finite values are normalized to None."
        ) from exc
    if not np.isfinite(normalized):
        return None
    return normalized


def _finite_list_or_none(value: Any, *, name: str) -> Any:
    if value is None:
        return None
    return _require_finite(np.asarray(value, dtype=float), name=name).tolist()


def _finite_mapping_or_none(value: Any, *, name: str) -> dict[str, float] | None:
    if value is None:
        return None
    value_mapping = _require_mapping(value, name=name)
    normalized_mapping: dict[str, float] = {}
    for key, item in value_mapping.items():
        field_name = f"{name}.{key}"
        try:
            normalized = _require_finite(np.asarray(item, dtype=float), name=field_name)
        except (TypeError, ValueError) as exc:
            raise SchemaValidationError(f"{field_name} must be a finite scalar float.") from exc
        if normalized.size != 1:
            raise SchemaValidationError(f"{field_name} must be a finite scalar float.")
        normalized_mapping[str(key)] = float(normalized.item())
    return normalized_mapping


def _summary_payload(summary_type: str, **items: Any) -> dict[str, Any]:
    payload = {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": summary_type,
        **items,
    }
    return _validate_json_compatible(payload, name=f"{summary_type} summary")


def _validate_finite_scalar(value: Any, *, name: str) -> float | None:
    """v0.32b strict validator: finite float or None. NaN/Inf raise."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise SchemaValidationError(
            f"{name} must be a finite float or None; boolean values are not accepted."
        )
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(
            f"{name} must be a finite float or None."
        ) from exc
    if not np.isfinite(normalized):
        raise SchemaValidationError(
            f"{name} must be a finite float or None; NaN/Inf are forbidden."
        )
    return normalized


def _validate_v0_32b_method_scores(
    value: Any, *, name: str
) -> dict[str, dict[str, Any]] | None:
    """Validate the additive method_scores field on the confidence report.

    See docs/design/GENERATOR_CONFIDENCE_ADDITIVE_FIELDS.md. Enforces:

    - value is a non-empty mapping (or None -> None).
    - each entry has EXACTLY {value, direction, description, units}.
    - direction is in the frozen vocabulary.
    - value is a finite float or None (NaN/Inf raise).
    - description is a non-empty string.
    - units is a non-empty string or None.
    """
    if value is None:
        return None
    mapping = _require_mapping(value, name=name)
    if not mapping:
        raise SchemaValidationError(
            f"{name} must be non-empty when provided; use None to opt out."
        )
    normalized: dict[str, dict[str, Any]] = {}
    for raw_key, raw_entry in mapping.items():
        score_key = str(raw_key)
        entry_name = f"{name}[{score_key!r}]"
        entry = _require_mapping(raw_entry, name=entry_name)
        entry_keys = set(entry.keys())
        if entry_keys != _METHOD_SCORE_ENTRY_KEYS:
            missing = _METHOD_SCORE_ENTRY_KEYS - entry_keys
            extra = entry_keys - _METHOD_SCORE_ENTRY_KEYS
            raise SchemaValidationError(
                f"{entry_name} must have exactly keys "
                f"{sorted(_METHOD_SCORE_ENTRY_KEYS)}; "
                f"missing={sorted(missing)!r}, extra={sorted(extra)!r}."
            )
        direction = entry["direction"]
        if direction not in _METHOD_SCORE_DIRECTIONS:
            raise SchemaValidationError(
                f"{entry_name}.direction must be one of "
                f"{sorted(_METHOD_SCORE_DIRECTIONS)}; got {direction!r}."
            )
        description = entry["description"]
        if not isinstance(description, str) or not description.strip():
            raise SchemaValidationError(
                f"{entry_name}.description must be a non-empty string."
            )
        units = entry["units"]
        if units is not None and (
            not isinstance(units, str) or not units.strip()
        ):
            raise SchemaValidationError(
                f"{entry_name}.units must be a non-empty string or None."
            )
        score_value = _validate_finite_scalar(
            entry["value"], name=f"{entry_name}.value"
        )
        normalized[score_key] = {
            "value": score_value,
            "direction": direction,
            "description": description,
            "units": units,
        }
    return normalized


def _validate_non_negative_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool):
        raise SchemaValidationError(
            f"{name} must be a non-negative integer; boolean values are not accepted."
        )
    if not isinstance(value, int):
        raise SchemaValidationError(f"{name} must be a non-negative integer.")
    if value < 0:
        raise SchemaValidationError(f"{name} must be a non-negative integer.")
    return int(value)


def _validate_optional_seed(value: Any, *, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise SchemaValidationError(
            f"{name} must be an integer or None; boolean values are not accepted."
        )
    if not isinstance(value, int):
        raise SchemaValidationError(f"{name} must be an integer or None.")
    return int(value)


def _validate_str_list(value: Any, *, name: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SchemaValidationError(f"{name} must be a list of strings.")
    out: list[str] = []
    for index, entry in enumerate(value):
        if not isinstance(entry, str):
            raise SchemaValidationError(
                f"{name}[{index}] must be a string; got {type(entry).__name__!r}."
            )
        out.append(entry)
    return out


def _validate_v0_32b_uncertainty_report(
    value: Any, *, name: str
) -> dict[str, Any] | None:
    """Validate the additive uncertainty_report field on the confidence report.

    See docs/design/GENERATOR_CONFIDENCE_ADDITIVE_FIELDS.md.
    """
    if value is None:
        return None
    mapping = _require_mapping(value, name=name)
    keys = set(mapping.keys())
    if keys != _UNCERTAINTY_REPORT_KEYS:
        missing = _UNCERTAINTY_REPORT_KEYS - keys
        extra = keys - _UNCERTAINTY_REPORT_KEYS
        raise SchemaValidationError(
            f"{name} must have exactly keys "
            f"{sorted(_UNCERTAINTY_REPORT_KEYS)}; "
            f"missing={sorted(missing)!r}, extra={sorted(extra)!r}."
        )
    method = mapping["method"]
    if method not in _UNCERTAINTY_METHOD_VOCABULARY:
        raise SchemaValidationError(
            f"{name}.method must be one of "
            f"{sorted(_UNCERTAINTY_METHOD_VOCABULARY)}; got {method!r}."
        )
    resampling_unit = mapping["resampling_unit"]
    if resampling_unit not in _UNCERTAINTY_RESAMPLING_UNITS:
        raise SchemaValidationError(
            f"{name}.resampling_unit must be one of "
            f"{sorted(_UNCERTAINTY_RESAMPLING_UNITS)}; got {resampling_unit!r}."
        )
    sample_count = _validate_non_negative_int(
        mapping["sample_count"], name=f"{name}.sample_count"
    )
    seed = _validate_optional_seed(mapping["seed"], name=f"{name}.seed")
    interval_level_raw = mapping["interval_level"]
    interval_level = _validate_finite_scalar(
        interval_level_raw, name=f"{name}.interval_level"
    )
    if interval_level is None or not (0.0 <= interval_level <= 1.0):
        raise SchemaValidationError(
            f"{name}.interval_level must be a finite float in [0.0, 1.0]."
        )
    intervals_raw = _require_mapping(
        mapping["intervals"], name=f"{name}.intervals"
    )
    intervals: dict[str, dict[str, float | None]] = {}
    for raw_key, raw_entry in intervals_raw.items():
        interval_name = f"{name}.intervals[{str(raw_key)!r}]"
        interval_entry = _require_mapping(raw_entry, name=interval_name)
        interval_keys = set(interval_entry.keys())
        if interval_keys != {"low", "high"}:
            raise SchemaValidationError(
                f"{interval_name} must have exactly keys ['high', 'low']; "
                f"got {sorted(interval_keys)!r}."
            )
        low = _validate_finite_scalar(
            interval_entry["low"], name=f"{interval_name}.low"
        )
        high = _validate_finite_scalar(
            interval_entry["high"], name=f"{interval_name}.high"
        )
        intervals[str(raw_key)] = {"low": low, "high": high}
    point_estimates_raw = _require_mapping(
        mapping["point_estimates"], name=f"{name}.point_estimates"
    )
    point_estimates: dict[str, float | None] = {}
    for raw_key, raw_entry in point_estimates_raw.items():
        est_name = f"{name}.point_estimates[{str(raw_key)!r}]"
        point_estimates[str(raw_key)] = _validate_finite_scalar(
            raw_entry, name=est_name
        )
    failed_resamples = _validate_non_negative_int(
        mapping["failed_resamples"], name=f"{name}.failed_resamples"
    )
    warnings_list = _validate_str_list(
        mapping["warnings"], name=f"{name}.warnings"
    )
    diagnostic_only = mapping["diagnostic_only"]
    if not isinstance(diagnostic_only, bool):
        raise SchemaValidationError(
            f"{name}.diagnostic_only must be a boolean."
        )
    if diagnostic_only is not True:
        raise SchemaValidationError(
            f"{name}.diagnostic_only must be True in v0.32b."
        )
    return {
        "method": method,
        "resampling_unit": resampling_unit,
        "sample_count": sample_count,
        "seed": seed,
        "interval_level": interval_level,
        "intervals": intervals,
        "point_estimates": point_estimates,
        "failed_resamples": failed_resamples,
        "warnings": warnings_list,
        "diagnostic_only": diagnostic_only,
    }


def _validate_v0_32b_calibration_report(
    value: Any, *, name: str
) -> dict[str, Any] | None:
    """Validate the additive calibration_report field on the confidence report.

    See docs/design/GENERATOR_CONFIDENCE_ADDITIVE_FIELDS.md.
    """
    if value is None:
        return None
    mapping = _require_mapping(value, name=name)
    keys = set(mapping.keys())
    if keys != _CALIBRATION_REPORT_KEYS:
        missing = _CALIBRATION_REPORT_KEYS - keys
        extra = keys - _CALIBRATION_REPORT_KEYS
        raise SchemaValidationError(
            f"{name} must have exactly keys "
            f"{sorted(_CALIBRATION_REPORT_KEYS)}; "
            f"missing={sorted(missing)!r}, extra={sorted(extra)!r}."
        )
    method = mapping["method"]
    if not isinstance(method, str) or not method.strip():
        raise SchemaValidationError(
            f"{name}.method must be a non-empty string."
        )
    target = mapping["target"]
    if not isinstance(target, str) or not target.strip():
        raise SchemaValidationError(
            f"{name}.target must be a non-empty string."
        )
    sample_count = _validate_non_negative_int(
        mapping["sample_count"], name=f"{name}.sample_count"
    )
    metrics_raw = _require_mapping(mapping["metrics"], name=f"{name}.metrics")
    metrics: dict[str, float | None] = {}
    for raw_key, raw_entry in metrics_raw.items():
        metric_name = f"{name}.metrics[{str(raw_key)!r}]"
        metrics[str(raw_key)] = _validate_finite_scalar(
            raw_entry, name=metric_name
        )
    warnings_list = _validate_str_list(
        mapping["warnings"], name=f"{name}.warnings"
    )
    diagnostic_only = mapping["diagnostic_only"]
    if not isinstance(diagnostic_only, bool):
        raise SchemaValidationError(
            f"{name}.diagnostic_only must be a boolean."
        )
    if diagnostic_only is not True:
        raise SchemaValidationError(
            f"{name}.diagnostic_only must be True in v0.32b."
        )
    return {
        "method": method,
        "target": target,
        "sample_count": sample_count,
        "metrics": metrics,
        "warnings": warnings_list,
        "diagnostic_only": diagnostic_only,
    }


def _runtime_report(
    value: Any,
    *,
    name: str,
    expected_summary_types: set[str] | frozenset[str],
) -> dict[str, Any]:
    report = _require_mapping(value, name=name)
    summary_type = report.get("summary_type")
    if summary_type not in expected_summary_types:
        raise SchemaValidationError(
            f"{name} must have summary_type in {sorted(expected_summary_types)}."
        )
    return _validate_json_compatible(dict(report), name=name)


def _runtime_report_or_list(
    value: Any,
    *,
    name: str,
    expected_summary_types: set[str] | frozenset[str],
) -> dict[str, Any] | list[dict[str, Any]] | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return _runtime_report(value, name=name, expected_summary_types=expected_summary_types)
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise SchemaValidationError(f"{name} must be a report mapping or sequence of report mappings.")
    return [
        _runtime_report(item, name=f"{name}[{index}]", expected_summary_types=expected_summary_types)
        for index, item in enumerate(value)
    ]


def _generator_summary_or_none(value: Any, *, name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, GeneratorFamily):
        return summarize_generator_family(value)
    return _runtime_report(value, name=name, expected_summary_types={"generator_family"})


def _fit_diagnostic_summary_or_none(value: Any, *, name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, GeneratorFamily):
        return summarize_generator_fit_diagnostics(value)
    return _runtime_report(value, name=name, expected_summary_types={"generator_fit_diagnostics"})


def _verification_summary_or_none(value: Any, *, name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, VerificationReport):
        return summarize_verification_report(value)
    return _runtime_report(value, name=name, expected_summary_types={"verification_report"})


def _residual_summary_or_none(value: Any, *, name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, ResidualBatch):
        return summarize_residual_batch(value)
    return _runtime_report(value, name=name, expected_summary_types={"residual_batch", "weak_residual_report"})


def _candidate_validation_summary_or_none(value: Any, *, name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    return _runtime_report(value, name=name, expected_summary_types={"symmetry_candidate_validation"})


def _coverage_summary_or_list_or_none(value: Any, *, name: str) -> dict[str, Any] | list[dict[str, Any]] | None:
    return _runtime_report_or_list(value, name=name, expected_summary_types={"periodic_window_coverage"})


def _consistency_summary_or_list_or_none(value: Any, *, name: str) -> dict[str, Any] | list[dict[str, Any]] | None:
    return _runtime_report_or_list(value, name=name, expected_summary_types={"uniform_translation_consistency"})


def _orbit_summary_or_list_or_none(value: Any, *, name: str) -> dict[str, Any] | list[dict[str, Any]] | None:
    return _runtime_report_or_list(value, name=name, expected_summary_types={"uniform_translation_orbit"})


def _orbit_batch_summary_or_none(value: Any, *, name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if isinstance(value, OrbitBatchResult):
        return _runtime_report(
            value.report,
            name=name,
            expected_summary_types={"uniform_translation_orbit_batch"},
        )
    return _runtime_report(value, name=name, expected_summary_types={"uniform_translation_orbit_batch"})


def _discovery_bridge_summary_or_none(value: Any, *, name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    return _runtime_report(value, name=name, expected_summary_types={"discovery_bridge_output"})


def _discovery_result_summary_or_none(value: Any, *, name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    return _runtime_report(value, name=name, expected_summary_types={"discovery_result"})


def _split_provenance_summary_or_none(value: Any, *, name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    return _runtime_report(value, name=name, expected_summary_types={"split_leakage_provenance"})


def _thresholds_or_empty(value: Mapping[str, Any] | None) -> dict[str, float]:
    if value is None:
        return {}
    thresholds = _finite_mapping_or_none(value, name="thresholds")
    assert thresholds is not None
    unknown = sorted(set(thresholds).difference(_CONFIDENCE_THRESHOLD_KEYS))
    if unknown:
        raise SchemaValidationError(f"thresholds contains unsupported keys: {unknown}.")
    return thresholds


def _component_status(status: str, *, reason: str, details: Mapping[str, Any] | None = None) -> dict[str, Any]:
    if status not in _CONFIDENCE_COMPONENT_STATUSES:
        raise AssertionError(f"unsupported confidence component status: {status}")
    return {
        "status": status,
        "reason": reason,
        "details": {} if details is None else dict(details),
    }


def _confidence_status_rank(status: str) -> int:
    return {
        "failed": 4,
        "warning": 3,
        "not_configured": 2,
        "passed": 1,
        "unavailable": 0,
    }[status]


def _combine_statuses(items: Sequence[dict[str, Any]], *, unavailable_reason: str) -> dict[str, Any]:
    if not items:
        return _component_status("unavailable", reason=unavailable_reason)
    return max(items, key=lambda item: _confidence_status_rank(str(item["status"])))


def _confidence_residual_status(
    residual: Mapping[str, Any] | None,
    thresholds: Mapping[str, float],
) -> dict[str, Any]:
    if residual is None:
        return _component_status("unavailable", reason="residual_not_provided")

    configured = {
        "max_abs_residual": thresholds.get("residual_max_abs"),
        "rms_residual": thresholds.get("residual_rms"),
    }
    configured = {metric: threshold for metric, threshold in configured.items() if threshold is not None}
    if not configured:
        return _component_status("not_configured", reason="residual_thresholds_not_configured")

    checked: dict[str, dict[str, float]] = {}
    missing: list[str] = []
    failed = False
    for metric, threshold in configured.items():
        value = _finite_float_or_none(residual.get(metric), name=f"residual.{metric}")
        if value is None:
            missing.append(metric)
            continue
        checked[metric] = {"value": value, "threshold": threshold}
        if value > threshold:
            failed = True

    if failed:
        return _component_status("failed", reason="residual_threshold_exceeded", details={"checked": checked})
    if missing and not checked:
        return _component_status("unavailable", reason="residual_threshold_metrics_missing", details={"missing": missing})
    if missing:
        return _component_status(
            "warning",
            reason="residual_partially_configured",
            details={"checked": checked, "missing": missing},
        )
    return _component_status("passed", reason="residual_thresholds_passed", details={"checked": checked})


def _confidence_fit_status(fit: Mapping[str, Any] | None) -> dict[str, Any]:
    if fit is None:
        return _component_status("unavailable", reason="fit_diagnostics_not_provided")
    label = fit.get("evidence_label")
    if label == "direct_svd_in_tolerance":
        return _component_status("passed", reason="direct_svd_in_tolerance")
    if label == "direct_svd_out_of_tolerance":
        return _component_status("failed", reason="direct_svd_out_of_tolerance")
    if label in {"reference_fallback", "mixed", "unavailable"}:
        return _component_status("warning", reason=f"fit_evidence_{label}")
    return _component_status("warning", reason="fit_evidence_unknown")


def _confidence_verification_status(
    verification: Mapping[str, Any] | None,
    thresholds: Mapping[str, float],
) -> dict[str, Any]:
    if verification is None:
        return _component_status("unavailable", reason="verification_not_provided")
    if verification.get("classification") == "failed":
        return _component_status("failed", reason="verification_classification_failed")

    configured = {
        "first_error": thresholds.get("verification_first_error"),
        "max_error": thresholds.get("verification_max_error"),
    }
    checked: dict[str, dict[str, float]] = {}
    failed = False
    for metric, threshold in configured.items():
        if threshold is None:
            continue
        value = _finite_float_or_none(verification.get(metric), name=f"verification.{metric}")
        if value is None:
            return _component_status("warning", reason=f"verification_{metric}_missing")
        checked[metric] = {"value": value, "threshold": threshold}
        if value > threshold:
            failed = True
    if failed:
        return _component_status("failed", reason="verification_threshold_exceeded", details={"checked": checked})
    return _component_status("passed", reason="verification_passed", details={"checked": checked})


def _confidence_candidate_validation_status(validation: Mapping[str, Any] | None) -> dict[str, Any]:
    if validation is None:
        return _component_status("unavailable", reason="candidate_validation_not_provided")
    conclusion = validation.get("conclusion")
    if conclusion == "validated":
        return _component_status("passed", reason="candidate_validated")
    if conclusion == "partially_validated":
        return _component_status("warning", reason="candidate_partially_validated")
    if conclusion == "failed":
        return _component_status("failed", reason="candidate_validation_failed")
    return _component_status("warning", reason="candidate_validation_unknown")


def _as_report_list(value: dict[str, Any] | list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _confidence_coverage_status(
    coverage: dict[str, Any] | list[dict[str, Any]] | None,
    thresholds: Mapping[str, float],
) -> dict[str, Any]:
    reports = _as_report_list(coverage)
    if not reports:
        return _component_status("unavailable", reason="coverage_not_provided")
    threshold = thresholds.get("coverage_fraction_min")
    if threshold is None:
        return _component_status("not_configured", reason="coverage_threshold_not_configured")

    fractions = []
    for index, report in enumerate(reports):
        fraction = _finite_float_or_none(report.get("coverage_fraction"), name=f"coverage[{index}].coverage_fraction")
        if fraction is None:
            return _component_status("warning", reason="coverage_fraction_missing")
        fractions.append(fraction)
    failed = any(fraction < threshold for fraction in fractions)
    status = "failed" if failed else "passed"
    reason = "coverage_threshold_failed" if failed else "coverage_threshold_passed"
    return _component_status(status, reason=reason, details={"coverage_fractions": fractions, "threshold": threshold})


def _collect_pass_booleans(value: Any) -> list[bool]:
    if isinstance(value, Mapping):
        collected: list[bool] = []
        for key, item in value.items():
            if isinstance(item, bool) and str(key).endswith("_passed"):
                collected.append(item)
            else:
                collected.extend(_collect_pass_booleans(item))
        return collected
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        collected = []
        for item in value:
            collected.extend(_collect_pass_booleans(item))
        return collected
    return []


def _confidence_pass_boolean_status(
    value: dict[str, Any] | list[dict[str, Any]] | None,
    *,
    unavailable_reason: str,
    not_configured_reason: str,
    failed_reason: str,
    passed_reason: str,
) -> dict[str, Any]:
    reports = _as_report_list(value)
    if not reports:
        return _component_status("unavailable", reason=unavailable_reason)
    pass_booleans = _collect_pass_booleans(reports)
    if not pass_booleans:
        return _component_status("not_configured", reason=not_configured_reason)
    if not all(pass_booleans):
        return _component_status("failed", reason=failed_reason, details={"pass_boolean_count": len(pass_booleans)})
    return _component_status("passed", reason=passed_reason, details={"pass_boolean_count": len(pass_booleans)})


def _confidence_label(component_statuses: Mapping[str, Mapping[str, Any]], *, evidence_present: bool) -> str:
    present_statuses = [
        str(status["status"])
        for status in component_statuses.values()
        if status["status"] != "unavailable"
    ]
    if any(status == "failed" for status in present_statuses):
        return "failed"
    if not evidence_present:
        return "insufficient_evidence"
    if any(status in {"warning", "not_configured"} for status in present_statuses):
        return "qualified"
    return "strong"


def _readiness_label(component_statuses: Mapping[str, Mapping[str, Any]]) -> str:
    statuses = [str(status["status"]) for status in component_statuses.values()]
    if any(status == "failed" for status in statuses):
        return "not_ready"
    if any(status == "warning" for status in statuses):
        return "needs_attention"
    return "ready"


def _safe_array(value: Any, *, name: str) -> tuple[np.ndarray | None, dict[str, Any] | None]:
    try:
        return np.asarray(value, dtype=float), None
    except (TypeError, ValueError) as exc:
        return None, {"error_type": type(exc).__name__, "message": f"{name} must be numeric array-like."}


def _strictly_increasing(values: np.ndarray) -> bool:
    return bool(values.ndim == 1 and values.size >= 2 and np.all(np.diff(values) > 0.0))


def _readiness_field_diagnostics(field: FieldBatch) -> tuple[dict[str, Any], dict[str, Any]]:
    values, value_error = _safe_array(field.values, name="field.values")
    if values is None:
        return (
            _component_status("failed", reason="field_values_not_numeric", details=value_error),
            {
                "schema_version": field.schema_version,
                "dims": list(field.dims),
                "shape": None,
                "var_names": list(field.var_names),
                "batch_size": None,
                "time_points": None,
                "x_points": None,
                "var_count": len(field.var_names),
            },
        )

    expected_dims = ("batch", "time", "x", "var")
    details = {
        "schema_version": field.schema_version,
        "dims": list(field.dims),
        "shape": list(values.shape),
        "var_names": list(field.var_names),
        "batch_size": int(values.shape[field.dims.index("batch")]) if "batch" in field.dims else None,
        "time_points": int(values.shape[field.dims.index("time")]) if "time" in field.dims else None,
        "x_points": int(values.shape[field.dims.index("x")]) if "x" in field.dims else None,
        "var_count": len(field.var_names),
    }
    failures: list[str] = []
    if field.schema_version != FieldBatch.SCHEMA_VERSION:
        failures.append("unsupported_schema_version")
    if tuple(field.dims) != expected_dims:
        failures.append("noncanonical_dims")
    if values.ndim != len(field.dims):
        failures.append("rank_dims_mismatch")
    if len(set(field.dims)) != len(field.dims):
        failures.append("duplicate_dims")
    if len(field.var_names) != 1:
        failures.append("non_scalar_var_count")
    elif values.ndim == len(field.dims) and values.shape[-1] != len(field.var_names):
        failures.append("var_axis_mismatch")
    if failures:
        return _component_status("failed", reason="field_shape_or_dims_not_ready", details={"failures": failures}), details
    return _component_status("passed", reason="field_shape_and_dims_ready"), details


def _readiness_value_status(field: FieldBatch) -> tuple[dict[str, Any], dict[str, Any]]:
    values, value_error = _safe_array(field.values, name="field.values")
    if values is None:
        return _component_status("failed", reason="field_values_not_numeric", details=value_error), {}
    finite_count = int(np.count_nonzero(np.isfinite(values)))
    total_count = int(values.size)
    diagnostics = {
        "finite_value_count": finite_count,
        "total_value_count": total_count,
        "nonfinite_value_count": int(total_count - finite_count),
    }
    if finite_count != total_count:
        return _component_status("failed", reason="field_values_nonfinite", details=diagnostics), diagnostics
    return _component_status("passed", reason="field_values_finite", details=diagnostics), diagnostics


def _readiness_mask_status(field: FieldBatch) -> tuple[dict[str, Any], dict[str, Any]]:
    if field.mask is None:
        diagnostics = {"mask_present": False, "masked_value_count": 0}
        return _component_status("passed", reason="field_unmasked", details=diagnostics), diagnostics
    mask = np.asarray(field.mask, dtype=bool)
    values = np.asarray(field.values)
    diagnostics = {
        "mask_present": True,
        "mask_shape": list(mask.shape),
        "expected_shape": list(values.shape),
        "masked_value_count": int(np.count_nonzero(mask)),
    }
    if mask.shape != values.shape:
        return _component_status("failed", reason="mask_shape_mismatch", details=diagnostics), diagnostics
    return _component_status("warning", reason="masked_fields_need_attention", details=diagnostics), diagnostics


def _finite_metadata_float(value: Any) -> float | None:
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return None
    if not np.isfinite(normalized):
        return None
    return normalized


def _readiness_coordinate_status(
    field: FieldBatch,
    *,
    name: str,
    minimum_points: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if name not in field.coords:
        diagnostics = {"present": False}
        return _component_status("failed", reason=f"{name}_coordinate_missing", details=diagnostics), diagnostics

    coord, coord_error = _safe_array(field.coords[name], name=f"field.coords['{name}']")
    if coord is None:
        diagnostics = {"present": True, **(coord_error or {})}
        return _component_status("failed", reason=f"{name}_coordinate_not_numeric", details=diagnostics), diagnostics

    expected_length = None
    if name in field.dims:
        values = np.asarray(field.values)
        expected_length = int(values.shape[field.dims.index(name)])

    finite = bool(np.all(np.isfinite(coord)))
    increasing = _strictly_increasing(coord)
    diffs = np.diff(coord) if coord.ndim == 1 and coord.size >= 2 else np.asarray([], dtype=float)
    uniform = bool(
        coord.ndim == 1
        and (
            coord.size <= 2
            or (
                coord.size > 2
                and diffs.size > 0
                and np.allclose(diffs, float(diffs[0]), atol=1e-10, rtol=0.0)
            )
        )
    )
    spacing = float(diffs[0]) if finite and increasing and uniform and diffs.size > 0 else None
    diagnostics: dict[str, Any] = {
        "present": True,
        "length": int(coord.shape[0]) if coord.ndim == 1 else None,
        "expected_length": expected_length,
        "finite": finite,
        "strictly_increasing": increasing,
        "uniform": uniform,
        "spacing": spacing,
    }
    if name == "x" and spacing is not None:
        inferred_domain_length = float(coord.shape[0] * spacing)
        observed_span = float(coord[-1] - coord[0])
        parameter_tags = field.metadata.get("parameter_tags", {}) if isinstance(field.metadata, Mapping) else {}
        domain_length_tag = (
            _finite_metadata_float(parameter_tags.get("domain_length"))
            if isinstance(parameter_tags, Mapping)
            else None
        )
        tolerance = 1e-10 * abs(domain_length_tag) if domain_length_tag is not None else None
        endpoint_duplicated = bool(
            domain_length_tag is not None
            and tolerance is not None
            and abs(observed_span - domain_length_tag) <= tolerance
            and abs(inferred_domain_length - domain_length_tag) > tolerance
        )
        diagnostics.update(
            {
                "inferred_domain_length": inferred_domain_length,
                "observed_span": observed_span,
                "domain_length_tag": domain_length_tag,
                "endpoint_duplicated_detected": endpoint_duplicated,
            }
        )

    failures: list[str] = []
    if coord.ndim != 1:
        failures.append("not_one_dimensional")
    if expected_length is None:
        failures.append("dimension_missing_from_field_dims")
    elif coord.ndim == 1 and coord.shape[0] != expected_length:
        failures.append("length_mismatch")
    if coord.ndim == 1 and coord.shape[0] < minimum_points:
        failures.append("too_few_points")
    if not finite:
        failures.append("nonfinite")
    if not increasing:
        failures.append("not_strictly_increasing")
    if not uniform:
        failures.append("not_uniform")
    if diagnostics.get("endpoint_duplicated_detected") is True:
        failures.append("endpoint_duplicated_periodic_grid")
    if failures:
        return _component_status("failed", reason=f"{name}_coordinate_not_ready", details={"failures": failures}), diagnostics
    return _component_status("passed", reason=f"{name}_coordinate_ready"), diagnostics


def _readiness_metadata_status(
    field: FieldBatch,
    *,
    expected_equation: str | None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    metadata = field.metadata
    if not isinstance(metadata, Mapping):
        diagnostics = {"metadata_is_mapping": False}
        metadata_status = _component_status("failed", reason="metadata_not_mapping", details=diagnostics)
        equation_status = _component_status("not_configured", reason="expected_equation_not_configured")
        return metadata_status, equation_status, diagnostics, {}

    missing = [key for key in REQUIRED_METADATA_KEYS if key not in metadata]
    boundary_conditions = metadata.get("boundary_conditions")
    parameter_tags = metadata.get("parameter_tags")
    diagnostics = {
        "required_keys": list(REQUIRED_METADATA_KEYS),
        "missing_keys": missing,
        "boundary_conditions": boundary_conditions if isinstance(boundary_conditions, Mapping) else None,
        "grid_type": metadata.get("grid_type"),
        "grid_regularity": metadata.get("grid_regularity"),
        "coordinate_system": metadata.get("coordinate_system"),
        "parameter_tags": parameter_tags if isinstance(parameter_tags, Mapping) else None,
        "equation": parameter_tags.get("equation") if isinstance(parameter_tags, Mapping) else None,
    }
    failures: list[str] = []
    if missing:
        failures.append("missing_required_metadata")
    if not isinstance(boundary_conditions, Mapping):
        failures.append("boundary_conditions_not_mapping")
    else:
        try:
            get_x_boundary_type({"boundary_conditions": boundary_conditions})
        except (ScopeValidationError, SchemaValidationError):
            failures.append("x_boundary_unsupported")
    if metadata.get("grid_type") != "rectilinear":
        failures.append("grid_type_not_rectilinear")
    if metadata.get("grid_regularity") != "uniform":
        failures.append("grid_regularity_not_uniform")
    if metadata.get("coordinate_system") != "cartesian":
        failures.append("coordinate_system_not_cartesian")
    if not isinstance(parameter_tags, Mapping):
        failures.append("parameter_tags_not_mapping")

    suggestions = {
        "grid_type": "rectilinear",
        "grid_regularity": "uniform",
        "coordinate_system": "cartesian",
        "boundary_conditions": {"x": "periodic"},
    }

    if failures:
        metadata_status = _component_status("failed", reason="metadata_not_ready", details={"failures": failures})
    else:
        metadata_status = _component_status("passed", reason="metadata_ready")

    if expected_equation is None:
        equation_status = _component_status("not_configured", reason="expected_equation_not_configured")
    elif not isinstance(expected_equation, str) or not expected_equation:
        raise SchemaValidationError("expected_equation must be a non-empty string or None.")
    elif not isinstance(parameter_tags, Mapping) or parameter_tags.get("equation") != expected_equation:
        equation_status = _component_status(
            "failed",
            reason="expected_equation_mismatch",
            details={"expected": expected_equation, "observed": diagnostics["equation"]},
        )
    else:
        equation_status = _component_status("passed", reason="expected_equation_matched")

    return metadata_status, equation_status, diagnostics, suggestions


def _readiness_residual_preflight(
    field: FieldBatch,
    residual_evaluator: ResidualEvaluator | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if residual_evaluator is None:
        diagnostics = {"configured": False, "residual": None, "error": None}
        return _component_status("not_configured", reason="residual_evaluator_not_configured"), diagnostics
    if not isinstance(residual_evaluator, ResidualEvaluator):
        raise SchemaValidationError("residual_evaluator must be a ResidualEvaluator or None.")

    try:
        residual = residual_evaluator.evaluate(field)
        residual_summary = summarize_residual_batch(residual)
    except PDELieValidationError as exc:
        diagnostics = {
            "configured": True,
            "residual": None,
            "error": {"error_type": type(exc).__name__, "message": str(exc)},
        }
        return _component_status("failed", reason="residual_preflight_validation_failed"), diagnostics

    diagnostics = {"configured": True, "residual": residual_summary, "error": None}
    return _component_status("passed", reason="residual_preflight_passed"), diagnostics


def summarize_field_batch_readiness(
    field: FieldBatch,
    *,
    residual_evaluator: ResidualEvaluator | None = None,
    expected_equation: str | None = None,
) -> dict[str, Any]:
    if not isinstance(field, FieldBatch):
        raise SchemaValidationError("summarize_field_batch_readiness requires a FieldBatch.")

    field_status, field_diagnostics = _readiness_field_diagnostics(field)
    value_status, value_diagnostics = _readiness_value_status(field)
    mask_status, mask_diagnostics = _readiness_mask_status(field)
    time_status, time_diagnostics = _readiness_coordinate_status(field, name="time", minimum_points=3)
    x_status, x_diagnostics = _readiness_coordinate_status(field, name="x", minimum_points=4)
    metadata_status, equation_status, metadata_diagnostics, metadata_suggestions = _readiness_metadata_status(
        field,
        expected_equation=expected_equation,
    )
    residual_status, residual_preflight = _readiness_residual_preflight(field, residual_evaluator)

    component_statuses = {
        "field": field_status,
        "values": value_status,
        "mask": mask_status,
        "time_coordinate": time_status,
        "x_coordinate": x_status,
        "metadata": metadata_status,
        "expected_equation": equation_status,
        "residual_preflight": residual_status,
    }
    label = _readiness_label(component_statuses)
    if label not in _READINESS_LABELS:
        raise AssertionError(f"unsupported readiness label: {label}")

    boundary_condition_warnings = _x_boundary_warnings(field.metadata)
    if boundary_condition_warnings and label == "ready":
        label = "needs_attention"

    return _summary_payload(
        "field_batch_readiness",
        readiness_label=label,
        component_statuses=component_statuses,
        field=field_diagnostics,
        value_diagnostics=value_diagnostics,
        mask_diagnostics=mask_diagnostics,
        coordinate_diagnostics={"time": time_diagnostics, "x": x_diagnostics},
        metadata_diagnostics=metadata_diagnostics,
        metadata_suggestions=metadata_suggestions,
        residual_preflight=residual_preflight,
        boundary_condition_warnings=boundary_condition_warnings,
        stable_scope={
            "dims": ["batch", "time", "x", "var"],
            "scalar_1d_periodic": True,
            "grid_type": "rectilinear",
            "grid_regularity": "uniform",
        },
    )


def _require_xarray_dataset(value: object):
    try:
        xr = importlib.import_module("xarray")
    except ModuleNotFoundError as exc:
        raise ImportError(
            "xarray is required for summarize_xarray_dataset_readiness; install pdelie[xarray]."
        ) from exc
    if isinstance(value, xr.DataArray):
        raise ScopeValidationError("summarize_xarray_dataset_readiness requires an xarray.Dataset, not a DataArray.")
    if not isinstance(value, xr.Dataset):
        raise SchemaValidationError("summarize_xarray_dataset_readiness requires an xarray.Dataset.")
    return xr


def _dataset_var_diagnostics(dataset: object, *, mask_var: str | None) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for name, data_array in dataset.data_vars.items():
        normalized_name = str(name)
        dims = tuple(str(dim) for dim in data_array.dims)
        shape = list(data_array.shape)
        is_mask_candidate = normalized_name == mask_var
        failures: list[str] = []
        if dims not in _XARRAY_DATASET_ACCEPTED_LAYOUTS:
            failures.append("unsupported_layout")
        try:
            raw_values = np.asarray(data_array.values)
            boolean_mask_like = bool(np.issubdtype(raw_values.dtype, np.bool_))
            values = np.asarray(raw_values, dtype=float)
            numeric = True
            finite = bool(np.all(np.isfinite(values)))
        except (TypeError, ValueError):
            values = None
            boolean_mask_like = False
            numeric = False
            finite = False
            failures.append("not_numeric")
        if boolean_mask_like:
            failures.append("boolean_mask_like")
        if values is not None and values.ndim != len(dims):
            failures.append("rank_dims_mismatch")
        if values is not None and "var" in dims and values.shape[dims.index("var")] != 1:
            failures.append("non_singleton_var_axis")
        if values is not None and not finite:
            failures.append("nonfinite_values")
        reports.append(
            {
                "name": normalized_name,
                "dims": list(dims),
                "shape": shape,
                "dtype": str(data_array.dtype),
                "numeric": numeric,
                "finite": finite,
                "boolean_mask_like": boolean_mask_like,
                "mask_candidate": is_mask_candidate,
                "compatible": not failures and not is_mask_candidate,
                "failures": failures,
            }
        )
    return reports


def _dataset_coord_diagnostics(data_array: object | None, metadata: Mapping[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    diagnostics: dict[str, Any] = {}
    statuses: list[dict[str, Any]] = []
    for name, minimum_points in (("time", 3), ("x", 4)):
        if data_array is None:
            diagnostics[name] = {"present": False}
            statuses.append(_component_status("unavailable", reason=f"{name}_coordinate_unavailable"))
            continue
        if name not in data_array.coords:
            diagnostics[name] = {"present": False}
            statuses.append(_component_status("failed", reason=f"{name}_coordinate_missing"))
            continue
        coord, coord_error = _safe_array(data_array.coords[name].values, name=f"coords['{name}']")
        if coord is None:
            diagnostics[name] = {"present": True, **(coord_error or {})}
            statuses.append(_component_status("failed", reason=f"{name}_coordinate_not_numeric"))
            continue
        finite = bool(np.all(np.isfinite(coord)))
        increasing = _strictly_increasing(coord)
        diffs = np.diff(coord) if coord.ndim == 1 and coord.size >= 2 else np.asarray([], dtype=float)
        uniform = bool(
            coord.ndim == 1
            and (
                coord.size <= 2
                or (
                    coord.size > 2
                    and diffs.size > 0
                    and np.allclose(diffs, float(diffs[0]), atol=1e-10, rtol=0.0)
                )
            )
        )
        spacing = float(diffs[0]) if finite and increasing and uniform and diffs.size > 0 else None
        failures: list[str] = []
        if coord.ndim != 1:
            failures.append("not_one_dimensional")
        if coord.ndim == 1 and coord.shape[0] < minimum_points:
            failures.append("too_few_points")
        if not finite:
            failures.append("nonfinite")
        if not increasing:
            failures.append("not_strictly_increasing")
        if not uniform:
            failures.append("not_uniform")
        details: dict[str, Any] = {
            "present": True,
            "length": int(coord.shape[0]) if coord.ndim == 1 else None,
            "finite": finite,
            "strictly_increasing": increasing,
            "uniform": uniform,
            "spacing": spacing,
        }
        if name == "x" and spacing is not None:
            inferred_domain_length = float(coord.shape[0] * spacing)
            parameter_tags = metadata.get("parameter_tags", {}) if isinstance(metadata, Mapping) else {}
            domain_length_tag = (
                _finite_metadata_float(parameter_tags.get("domain_length"))
                if isinstance(parameter_tags, Mapping)
                else None
            )
            details.update(
                {
                    "inferred_domain_length": inferred_domain_length,
                    "observed_span": float(coord[-1] - coord[0]),
                    "domain_length_tag": domain_length_tag,
                }
            )
        diagnostics[name] = details
        if failures:
            statuses.append(_component_status("failed", reason=f"{name}_coordinate_not_ready", details={"failures": failures}))
        else:
            statuses.append(_component_status("passed", reason=f"{name}_coordinate_ready"))
    return _combine_statuses(statuses, unavailable_reason="coordinates_unavailable"), diagnostics


def _dataset_metadata_status(
    metadata: Mapping[str, Any] | None,
    *,
    expected_equation: str | None,
    suggestions: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    if metadata is None:
        diagnostics = {
            "metadata_provided": False,
            "required_keys": list(REQUIRED_METADATA_KEYS),
            "missing_keys": list(REQUIRED_METADATA_KEYS),
        }
        equation_status = (
            _component_status("failed", reason="expected_equation_without_metadata")
            if expected_equation is not None
            else _component_status("not_configured", reason="expected_equation_not_configured")
        )
        return _component_status("failed", reason="metadata_required_for_conversion"), equation_status, diagnostics, dict(suggestions)
    if not isinstance(metadata, Mapping):
        raise SchemaValidationError("metadata must be a mapping or None.")
    normalized_metadata = _validate_strict_json_compatible(dict(metadata), name="metadata")
    missing = [key for key in REQUIRED_METADATA_KEYS if key not in normalized_metadata]
    boundary_conditions = normalized_metadata.get("boundary_conditions")
    parameter_tags = normalized_metadata.get("parameter_tags")
    diagnostics = {
        "metadata_provided": True,
        "required_keys": list(REQUIRED_METADATA_KEYS),
        "missing_keys": missing,
        "boundary_conditions": boundary_conditions if isinstance(boundary_conditions, Mapping) else None,
        "grid_type": normalized_metadata.get("grid_type"),
        "grid_regularity": normalized_metadata.get("grid_regularity"),
        "coordinate_system": normalized_metadata.get("coordinate_system"),
        "parameter_tags": parameter_tags if isinstance(parameter_tags, Mapping) else None,
        "equation": parameter_tags.get("equation") if isinstance(parameter_tags, Mapping) else None,
    }
    failures: list[str] = []
    if missing:
        failures.append("missing_required_metadata")
    if not isinstance(boundary_conditions, Mapping):
        failures.append("boundary_conditions_not_mapping")
    else:
        try:
            get_x_boundary_type({"boundary_conditions": boundary_conditions})
        except (ScopeValidationError, SchemaValidationError):
            failures.append("x_boundary_unsupported")
    if normalized_metadata.get("grid_type") != "rectilinear":
        failures.append("grid_type_not_rectilinear")
    if normalized_metadata.get("grid_regularity") != "uniform":
        failures.append("grid_regularity_not_uniform")
    if normalized_metadata.get("coordinate_system") != "cartesian":
        failures.append("coordinate_system_not_cartesian")
    if not isinstance(parameter_tags, Mapping):
        failures.append("parameter_tags_not_mapping")
    metadata_status = (
        _component_status("failed", reason="metadata_not_ready", details={"failures": failures})
        if failures
        else _component_status("passed", reason="metadata_ready")
    )
    if expected_equation is None:
        equation_status = _component_status("not_configured", reason="expected_equation_not_configured")
    elif not isinstance(expected_equation, str) or not expected_equation:
        raise SchemaValidationError("expected_equation must be a non-empty string or None.")
    elif not isinstance(parameter_tags, Mapping) or parameter_tags.get("equation") != expected_equation:
        equation_status = _component_status(
            "failed",
            reason="expected_equation_mismatch",
            details={"expected": expected_equation, "observed": diagnostics["equation"]},
        )
    else:
        equation_status = _component_status("passed", reason="expected_equation_matched")
    return metadata_status, equation_status, diagnostics, dict(suggestions)


def summarize_xarray_dataset_readiness(
    dataset: object,
    *,
    data_var: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    mask_var: str | None = None,
    expected_equation: str | None = None,
) -> dict[str, Any]:
    _require_xarray_dataset(dataset)
    if expected_equation is not None and (not isinstance(expected_equation, str) or not expected_equation):
        raise SchemaValidationError("expected_equation must be a non-empty string or None.")
    dataset_attr_keys = sorted(str(key) for key in dataset.attrs)
    try:
        _validate_strict_json_compatible(list(dataset.attrs.values()), name="dataset.attrs values")
    except SchemaValidationError:
        dataset_attrs_values_json_compatible = False
    else:
        dataset_attrs_values_json_compatible = True
    normalized_mask_var = None if mask_var is None else _require_mapping({"mask_var": mask_var}, name="mask_var container")["mask_var"]
    if normalized_mask_var is not None and (not isinstance(normalized_mask_var, str) or not normalized_mask_var):
        raise SchemaValidationError("mask_var must be a non-empty string or None.")
    if data_var is not None and (not isinstance(data_var, str) or not data_var):
        raise SchemaValidationError("data_var must be a non-empty string or None.")

    candidate_variables = _dataset_var_diagnostics(dataset, mask_var=normalized_mask_var)
    compatible_names = [report["name"] for report in candidate_variables if report["compatible"]]
    selected_data_var: str | None = None
    data_var_failures: list[str] = []
    if data_var is not None:
        if data_var not in dataset.data_vars:
            data_var_failures.append("data_var_missing")
        elif data_var == normalized_mask_var:
            data_var_failures.append("data_var_equals_mask_var")
        else:
            selected_data_var = data_var
            selected_report = next(report for report in candidate_variables if report["name"] == data_var)
            if not selected_report["compatible"]:
                data_var_failures.extend(str(item) for item in selected_report["failures"])
    elif len(compatible_names) == 1:
        selected_data_var = compatible_names[0]
    elif not compatible_names:
        data_var_failures.append("no_compatible_data_var")
    else:
        data_var_failures.append("ambiguous_data_var")

    data_var_status = (
        _component_status("failed", reason="dataset_data_var_not_ready", details={"failures": data_var_failures})
        if data_var_failures
        else _component_status("passed", reason="dataset_data_var_ready")
    )
    selected_array = None if selected_data_var is None else dataset.data_vars[selected_data_var]

    mask_failures: list[str] = []
    if normalized_mask_var is None:
        mask_status = _component_status("not_configured", reason="mask_var_not_configured")
    elif normalized_mask_var not in dataset.data_vars:
        mask_status = _component_status("failed", reason="mask_var_missing")
        mask_failures.append("mask_var_missing")
    elif selected_array is None:
        mask_status = _component_status("unavailable", reason="mask_var_unchecked_without_data_var")
    else:
        mask_array = dataset.data_vars[normalized_mask_var]
        if tuple(str(dim) for dim in mask_array.dims) != tuple(str(dim) for dim in selected_array.dims):
            mask_failures.append("mask_dims_mismatch")
        if tuple(mask_array.shape) != tuple(selected_array.shape):
            mask_failures.append("mask_shape_mismatch")
        mask_status = (
            _component_status("failed", reason="mask_var_not_ready", details={"failures": mask_failures})
            if mask_failures
            else _component_status("passed", reason="mask_var_ready")
        )

    coordinate_status, coordinate_diagnostics = _dataset_coord_diagnostics(selected_array, metadata)
    suggestions = {
        "compatible_data_vars": compatible_names,
        "selected_data_var": selected_data_var,
        "dataset_attr_keys": dataset_attr_keys,
        "grid_type": "rectilinear",
        "grid_regularity": "uniform",
        "coordinate_system": "cartesian",
        "boundary_conditions": {"x": "periodic"},
    }
    if coordinate_diagnostics.get("x", {}).get("inferred_domain_length") is not None:
        suggestions["parameter_tags"] = {"domain_length": coordinate_diagnostics["x"]["inferred_domain_length"]}
    metadata_status, equation_status, metadata_diagnostics, metadata_suggestions = _dataset_metadata_status(
        metadata,
        expected_equation=expected_equation,
        suggestions=suggestions,
    )

    conversion_status: dict[str, Any]
    conversion_preflight: dict[str, Any]
    if selected_data_var is None or metadata is None:
        conversion_status = _component_status("unavailable", reason="conversion_preflight_not_available")
        conversion_preflight = {"configured": False, "field_readiness": None, "error": None}
    else:
        try:
            from pdelie.data import from_xarray_dataset

            field = from_xarray_dataset(
                dataset,
                data_var=selected_data_var,
                metadata=metadata,
                mask_var=normalized_mask_var,
            )
            field_readiness = summarize_field_batch_readiness(field, expected_equation=expected_equation)
        except PDELieValidationError as exc:
            conversion_status = _component_status("failed", reason="conversion_preflight_validation_failed")
            conversion_preflight = {
                "configured": True,
                "field_readiness": None,
                "error": {"error_type": type(exc).__name__, "message": str(exc)},
            }
        else:
            conversion_status = _component_status("passed", reason="conversion_preflight_passed")
            conversion_preflight = {"configured": True, "field_readiness": field_readiness, "error": None}

    component_statuses = {
        "dataset": _component_status("passed", reason="dataset_object_ready"),
        "data_variable": data_var_status,
        "mask_variable": mask_status,
        "coordinates": coordinate_status,
        "metadata": metadata_status,
        "expected_equation": equation_status,
        "conversion_preflight": conversion_status,
    }
    label = _readiness_label(component_statuses)
    boundary_condition_warnings = _x_boundary_warnings(metadata)
    if boundary_condition_warnings and label == "ready":
        label = "needs_attention"
    payload = {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": "xarray_dataset_readiness",
        "readiness_label": label,
        "component_statuses": component_statuses,
        "dataset": {
            "data_vars": [str(name) for name in dataset.data_vars],
            "dims": {str(name): int(length) for name, length in dataset.sizes.items()},
            "attrs_keys": dataset_attr_keys,
            "attrs_values_json_compatible": dataset_attrs_values_json_compatible,
        },
        "selected_data_var": selected_data_var,
        "candidate_variables": candidate_variables,
        "mask": {"mask_var": normalized_mask_var, "failures": mask_failures},
        "coordinate_diagnostics": coordinate_diagnostics,
        "metadata_diagnostics": metadata_diagnostics,
        "metadata_suggestions": metadata_suggestions,
        "conversion_preflight": conversion_preflight,
        "boundary_condition_warnings": boundary_condition_warnings,
        "stable_scope": {
            "dataset_input": True,
            "scalar_1d_periodic": True,
            "file_loaders": False,
            "metadata_inference": "report_only_conservative",
        },
    }
    return _validate_strict_json_compatible(payload, name="xarray_dataset_readiness summary")


def summarize_residual_batch(residual: ResidualBatch) -> dict[str, Any]:
    if not isinstance(residual, ResidualBatch):
        raise SchemaValidationError("summarize_residual_batch requires a ResidualBatch.")

    residual_values = _require_finite(residual.residual, name="ResidualBatch.residual")

    # v0.30c additive: surface a residual_domain_policy field if the evaluator (or any
    # caller-supplied diagnostics) records one. Default is "not_configured" so the
    # field is always present and strict-JSON serializable.
    diagnostics = residual.diagnostics if isinstance(residual.diagnostics, Mapping) else {}
    raw_policy = diagnostics.get("residual_domain_policy")
    residual_domain_policy = (
        str(raw_policy) if isinstance(raw_policy, str) and raw_policy else "not_configured"
    )

    return _summary_payload(
        "residual_batch",
        residual_shape=list(residual_values.shape),
        definition_type=residual.definition_type,
        normalization=residual.normalization,
        max_abs_residual=float(np.max(np.abs(residual_values))),
        rms_residual=float(np.sqrt(np.mean(np.square(residual_values)))),
        residual_domain_policy=residual_domain_policy,
        diagnostics=residual.diagnostics,
    )


def summarize_weak_residual_report(report: Mapping[str, Any]) -> dict[str, Any]:
    report_mapping = _require_mapping(report, name="weak residual report")
    missing = sorted(_WEAK_REPORT_KEYS.difference(report_mapping))
    if missing:
        raise SchemaValidationError(f"weak residual report is missing required fields: {missing}.")

    diagnostics = _require_mapping(report_mapping["diagnostics"], name="weak residual report diagnostics")
    window_residuals = _require_finite(
        np.asarray(report_mapping["window_residuals"], dtype=float),
        name="weak residual report window_residuals",
    )
    if window_residuals.ndim != 4 or window_residuals.shape[-1] != 1:
        raise SchemaValidationError(
            "weak residual report window_residuals must have shape (batch, time_window, x_window, 1)."
        )

    return _summary_payload(
        "weak_residual_report",
        equation=str(report_mapping["equation"]),
        equation_form=str(report_mapping["equation_form"]),
        method_family=str(report_mapping["method_family"]),
        normalization=str(report_mapping["normalization"]),
        window_residual_shape=list(window_residuals.shape),
        max_abs_residual=float(np.max(np.abs(window_residuals))),
        l2_residual=float(np.linalg.norm(window_residuals.ravel(), ord=2)),
        diagnostics=diagnostics,
    )


def _non_negative_integral_or_none(value: Any, *, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise SchemaValidationError(f"{name} must be a non-negative integer.")
    normalized = int(value)
    if normalized < 0:
        raise SchemaValidationError(f"{name} must be a non-negative integer.")
    return normalized


def _positive_integer_sequence_or_none(value: Any, *, name: str) -> list[int] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise SchemaValidationError(f"{name} must be a sequence of positive integers.")
    normalized: list[int] = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, Integral):
            raise SchemaValidationError(f"{name}[{index}] must be a positive integer.")
        integer = int(item)
        if integer <= 0:
            raise SchemaValidationError(f"{name}[{index}] must be a positive integer.")
        normalized.append(integer)
    return normalized


def _string_or_none(value: Any, *, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise SchemaValidationError(f"{name} must be a non-empty string when provided.")
    return value


def _weak_thresholds_or_empty(value: Mapping[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    mapping = _require_mapping(value, name="thresholds")
    unknown = sorted(set(mapping).difference(_WEAK_SUPPORTABILITY_THRESHOLD_KEYS))
    if unknown:
        raise SchemaValidationError(f"thresholds contains unsupported weak-form keys: {unknown}.")

    normalized: dict[str, Any] = {}
    for key, item in mapping.items():
        if key == "finite_required":
            if not isinstance(item, bool):
                raise SchemaValidationError("thresholds.finite_required must be a boolean.")
            normalized[key] = item
        elif key == "robustness_required_cases":
            if isinstance(item, (str, bytes)) or not isinstance(item, Sequence):
                raise SchemaValidationError("thresholds.robustness_required_cases must be a sequence of strings.")
            cases = []
            for index, case in enumerate(item):
                if not isinstance(case, str) or not case.strip():
                    raise SchemaValidationError(
                        f"thresholds.robustness_required_cases[{index}] must be a non-empty string."
                    )
                cases.append(case)
            normalized[key] = cases
        elif key == "min_weak_rows":
            normalized[key] = _non_negative_integral_or_none(item, name=f"thresholds.{key}")
        elif key == "max_skipped_fraction":
            fraction = _finite_float_or_none(item, name=f"thresholds.{key}")
            if fraction is None or fraction < 0.0 or fraction > 1.0:
                raise SchemaValidationError(f"thresholds.{key} must be a finite fraction in [0, 1].")
            normalized[key] = fraction
        else:
            scalar = _finite_float_or_none(item, name=f"thresholds.{key}")
            if scalar is None or scalar < 0.0:
                raise SchemaValidationError(f"thresholds.{key} must be a finite non-negative scalar.")
            normalized[key] = scalar
    return normalized


def _weak_report_summary_and_metrics(
    *,
    weak_report: Mapping[str, Any] | None,
    weak_report_summary: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if weak_report is not None and weak_report_summary is not None:
        raise SchemaValidationError("Provide either weak_report or weak_report_summary, not both.")
    if weak_report is None and weak_report_summary is None:
        return None, None

    if weak_report is not None:
        summary = summarize_weak_residual_report(weak_report)
        residuals = _require_finite(
            np.asarray(_require_mapping(weak_report, name="weak_report")["window_residuals"], dtype=float),
            name="weak_report.window_residuals",
        )
        row_count = int(residuals.size)
        metrics = {
            "max_abs_residual": float(np.max(np.abs(residuals))),
            "rms_residual": float(np.sqrt(np.mean(np.square(residuals)))),
            "l2_residual": float(np.linalg.norm(residuals.ravel(), ord=2)),
            "row_count": row_count,
            "finite": True,
        }
        return summary, metrics

    assert weak_report_summary is not None
    summary = _runtime_report(
        weak_report_summary,
        name="weak_report_summary",
        expected_summary_types={"weak_residual_report"},
    )
    shape = summary.get("window_residual_shape")
    row_count = None
    if isinstance(shape, Sequence) and not isinstance(shape, (str, bytes)):
        row_count = 1
        for item in shape:
            if isinstance(item, bool) or not isinstance(item, Integral) or int(item) <= 0:
                row_count = None
                break
            row_count *= int(item)
    l2 = _finite_float_or_none(summary.get("l2_residual"), name="weak_report_summary.l2_residual")
    metrics = {
        "max_abs_residual": _finite_float_or_none(
            summary.get("max_abs_residual"),
            name="weak_report_summary.max_abs_residual",
        ),
        "rms_residual": None if l2 is None or row_count in (None, 0) else float(l2 / np.sqrt(float(row_count))),
        "l2_residual": l2,
        "row_count": row_count,
        "finite": True,
    }
    return summary, metrics


def _operator_order_for_weak_equation(equation: str | None) -> int | None:
    if equation in {"heat_1d", "burgers_1d"}:
        return 2
    return None


def _contract_from_weak_report_summary(summary: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if summary is None:
        return None
    diagnostics = _require_mapping(summary.get("diagnostics", {}), name="weak_report_summary.diagnostics")
    shape = summary.get("window_residual_shape")
    row_count = None
    if isinstance(shape, Sequence) and not isinstance(shape, (str, bytes)):
        row_count = 1
        for item in shape:
            if isinstance(item, bool) or not isinstance(item, Integral):
                row_count = None
                break
            row_count *= int(item)
    window_counts = diagnostics.get("window_counts")
    if isinstance(window_counts, Mapping) and row_count is None:
        time_count = window_counts.get("time")
        x_count = window_counts.get("x")
        if isinstance(time_count, Integral) and isinstance(x_count, Integral):
            row_count = int(time_count) * int(x_count)

    equation = str(summary.get("equation")) if summary.get("equation") is not None else None
    return {
        "schema_version": "0.1",
        "equation": equation,
        "equation_form": str(summary.get("equation_form")) if summary.get("equation_form") is not None else None,
        "test_function_family": diagnostics.get("test_function"),
        "test_function_order": 4 if diagnostics.get("test_function") == "separable_quartic_bump_beta" else None,
        "operator_order_supported": _operator_order_for_weak_equation(equation),
        "integration_by_parts_depth": _operator_order_for_weak_equation(equation),
        "boundary_vanishing_order": 1,
        "patch_shape": [
            diagnostics.get("time_window_size"),
            diagnostics.get("x_window_size"),
        ],
        "patch_stride": [
            diagnostics.get("time_window_stride"),
            diagnostics.get("x_window_stride"),
        ],
        "quadrature_rule": diagnostics.get("quadrature"),
        "normalization": summary.get("normalization"),
        "valid_window_policy": "interior_time_periodic_x_wrapped",
        "row_count": row_count,
        "skipped_patch_count": 0,
        "finite_value_policy": "finite_window_residuals_required",
    }


def _normalize_weak_contract(value: Any, *, name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    safe = _validate_strict_json_compatible(_require_mapping(value, name=name), name=name)
    assert isinstance(safe, Mapping)
    normalized = {field: safe.get(field) for field in _WEAK_CONTRACT_FIELDS}

    for field in (
        "schema_version",
        "equation",
        "equation_form",
        "test_function_family",
        "quadrature_rule",
        "normalization",
        "valid_window_policy",
        "finite_value_policy",
    ):
        normalized[field] = _string_or_none(normalized[field], name=f"{name}.{field}")

    for field in (
        "test_function_order",
        "operator_order_supported",
        "integration_by_parts_depth",
        "boundary_vanishing_order",
        "row_count",
        "skipped_patch_count",
    ):
        normalized[field] = _non_negative_integral_or_none(normalized[field], name=f"{name}.{field}")

    normalized["patch_shape"] = _positive_integer_sequence_or_none(
        normalized["patch_shape"],
        name=f"{name}.patch_shape",
    )
    normalized["patch_stride"] = _positive_integer_sequence_or_none(
        normalized["patch_stride"],
        name=f"{name}.patch_stride",
    )
    return dict(normalized)


def _weak_report_status(
    summary: Mapping[str, Any] | None,
    metrics: Mapping[str, Any] | None,
    thresholds: Mapping[str, Any],
) -> dict[str, Any]:
    if summary is None or metrics is None:
        return _component_status("unavailable", reason="weak_report_not_provided")

    equation = summary.get("equation")
    details: dict[str, Any] = {"equation": equation, "checked": {}}
    if equation not in _FROZEN_PUBLIC_WEAK_EQUATIONS:
        return _component_status(
            "warning",
            reason="weak_report_not_frozen_public_heat_burgers_slice",
            details=details,
        )

    checks = {
        "max_abs_residual": thresholds.get("weak_report_max_abs"),
        "rms_residual": thresholds.get("weak_report_rms"),
        "l2_residual": thresholds.get("weak_report_l2"),
    }
    failed = False
    missing: list[str] = []
    for metric, threshold in checks.items():
        if threshold is None:
            continue
        value = _finite_float_or_none(metrics.get(metric), name=f"weak_report_metrics.{metric}")
        if value is None:
            missing.append(metric)
            failed = True
            continue
        details["checked"][metric] = {"value": value, "threshold": threshold}
        if value > threshold:
            failed = True

    if thresholds.get("finite_required") is True and metrics.get("finite") is not True:
        failed = True
        details["finite_required"] = True

    if missing:
        details["missing_metrics"] = missing
    if failed:
        return _component_status("failed", reason="weak_report_threshold_failed", details=details)
    return _component_status("passed", reason="weak_report_supported_existing_slice", details=details)


def _weak_contract_status(contract: Mapping[str, Any] | None, thresholds: Mapping[str, Any]) -> dict[str, Any]:
    if contract is None:
        return _component_status("unavailable", reason="weak_contract_not_provided")

    details = {
        "quadrature_rule": contract.get("quadrature_rule"),
        "row_count": contract.get("row_count"),
        "skipped_patch_count": contract.get("skipped_patch_count"),
    }
    failures: list[str] = []
    if contract.get("quadrature_rule") is None:
        failures.append("quadrature_rule_missing")

    min_rows = thresholds.get("min_weak_rows")
    row_count = contract.get("row_count")
    if min_rows is not None and (not isinstance(row_count, Integral) or int(row_count) < int(min_rows)):
        failures.append("row_count_below_threshold")
        details["min_weak_rows"] = int(min_rows)

    max_skipped_fraction = thresholds.get("max_skipped_fraction")
    skipped_count = contract.get("skipped_patch_count")
    if max_skipped_fraction is not None:
        if not isinstance(row_count, Integral) or not isinstance(skipped_count, Integral):
            failures.append("skipped_fraction_unavailable")
        else:
            denominator = int(row_count) + int(skipped_count)
            skipped_fraction = 0.0 if denominator == 0 else float(int(skipped_count) / denominator)
            details["skipped_fraction"] = skipped_fraction
            details["max_skipped_fraction"] = float(max_skipped_fraction)
            if skipped_fraction > float(max_skipped_fraction):
                failures.append("skipped_fraction_above_threshold")

    if thresholds.get("finite_required") is True and contract.get("finite_value_policy") is None:
        failures.append("finite_value_policy_missing")

    if failures:
        return _component_status(
            "failed",
            reason="weak_contract_threshold_failed",
            details={"failures": failures, **details},
        )
    return _component_status("passed", reason="weak_contract_recorded", details=details)


def _strong_residual_support_status(summary: Mapping[str, Any] | None) -> dict[str, Any]:
    if summary is None:
        return _component_status("unavailable", reason="strong_residual_not_provided")
    return _component_status(
        "passed",
        reason="strong_residual_summarized",
        details={
            "max_abs_residual": summary.get("max_abs_residual"),
            "rms_residual": summary.get("rms_residual"),
        },
    )


def _mapping_or_sequence_strict(value: Any, *, name: str) -> dict[str, Any] | list[Any] | None:
    if value is None:
        return None
    if isinstance(value, Mapping):
        return _validate_strict_json_compatible(dict(value), name=name)
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise SchemaValidationError(f"{name} must be a mapping or sequence.")
    return _validate_strict_json_compatible(list(value), name=name)


def _contains_failed_status(value: Any) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in {"status", "conclusion", "label"} and item in {"failed", "not_ready"}:
                return True
            if _contains_failed_status(item):
                return True
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return any(_contains_failed_status(item) for item in value)
    return False


def _case_names_from_report(value: Any) -> set[str]:
    names: set[str] = set()
    if isinstance(value, Mapping):
        cases = value.get("cases")
        if isinstance(cases, Sequence) and not isinstance(cases, (str, bytes)):
            for item in cases:
                if isinstance(item, Mapping):
                    case_name = item.get("case_name", item.get("name"))
                    if isinstance(case_name, str):
                        names.add(case_name)
        for key, item in value.items():
            if key != "cases" and isinstance(item, Mapping):
                names.add(str(key))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            if isinstance(item, Mapping):
                case_name = item.get("case_name", item.get("name"))
                if isinstance(case_name, str):
                    names.add(case_name)
    return names


def _robustness_status(value: Any, thresholds: Mapping[str, Any]) -> dict[str, Any]:
    if value is None:
        return _component_status("unavailable", reason="robustness_not_provided")
    if _contains_failed_status(value):
        return _component_status("failed", reason="robustness_report_failed")
    required_cases = thresholds.get("robustness_required_cases")
    if required_cases:
        available = _case_names_from_report(value)
        missing = [case for case in required_cases if case not in available]
        if missing:
            return _component_status("failed", reason="robustness_required_cases_missing", details={"missing": missing})
        return _component_status(
            "passed",
            reason="robustness_required_cases_present",
            details={"cases": sorted(available)},
        )
    return _component_status("passed", reason="robustness_summarized")


def _first_metric(value: Any, keys: set[str]) -> float | None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in keys:
                scalar = _finite_float_or_none(item, name=str(key))
                if scalar is not None:
                    return scalar
            nested = _first_metric(item, keys)
            if nested is not None:
                return nested
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in value:
            nested = _first_metric(item, keys)
            if nested is not None:
                return nested
    return None


def _imported_parity_status(value: Any, thresholds: Mapping[str, Any]) -> dict[str, Any]:
    if value is None:
        return _component_status("unavailable", reason="imported_parity_not_provided")
    if _contains_failed_status(value):
        return _component_status("failed", reason="imported_parity_report_failed")
    details: dict[str, Any] = {}
    abs_tol = thresholds.get("imported_parity_abs_tol")
    rel_tol = thresholds.get("imported_parity_rel_tol")
    failed = False
    if abs_tol is not None:
        abs_delta = _first_metric(
            value,
            {"max_abs_delta", "max_abs_difference", "max_abs_error", "absolute_delta", "abs_delta"},
        )
        details["absolute_delta"] = abs_delta
        details["absolute_tolerance"] = abs_tol
        failed = failed or abs_delta is None or abs_delta > abs_tol
    if rel_tol is not None:
        rel_delta = _first_metric(
            value,
            {"max_relative_delta", "max_relative_difference", "relative_delta", "rel_delta"},
        )
        details["relative_delta"] = rel_delta
        details["relative_tolerance"] = rel_tol
        failed = failed or rel_delta is None or rel_delta > rel_tol
    if failed:
        return _component_status("failed", reason="imported_parity_threshold_failed", details=details)
    return _component_status("passed", reason="imported_parity_summarized", details=details)


def _feasibility_status(value: Any) -> dict[str, Any]:
    if value is None:
        return _component_status("unavailable", reason="feasibility_not_provided")
    if _contains_failed_status(value):
        return _component_status("failed", reason="feasibility_report_failed")
    visibility = value.get("visibility") if isinstance(value, Mapping) else None
    if visibility == "internal_diagnostic_only":
        return _component_status("warning", reason="internal_feasibility_diagnostic_only")
    return _component_status("warning", reason="feasibility_not_public_support")


def _weak_supportability_label(
    *,
    weak_summary: Mapping[str, Any] | None,
    weak_contract: Mapping[str, Any] | None,
    feasibility: Any,
    component_statuses: Mapping[str, Mapping[str, Any]],
) -> str:
    statuses = [str(status["status"]) for status in component_statuses.values() if status["status"] != "unavailable"]
    if any(status == "failed" for status in statuses):
        return "failed"

    public_weak_report = weak_summary is not None and weak_summary.get("equation") in _FROZEN_PUBLIC_WEAK_EQUATIONS
    if public_weak_report:
        return "supported_existing_slice"

    internal_diagnostic_feasibility = (
        isinstance(feasibility, Mapping) and feasibility.get("visibility") == "internal_diagnostic_only"
    )
    if internal_diagnostic_feasibility:
        return "diagnostic_only"

    if weak_summary is not None or feasibility is not None:
        return "diagnostic_only"
    return "insufficient_evidence"


def summarize_weak_form_supportability(
    *,
    weak_report: Mapping[str, Any] | None = None,
    weak_report_summary: Mapping[str, Any] | None = None,
    weak_contract: Mapping[str, Any] | None = None,
    strong_residual: ResidualBatch | Mapping[str, Any] | None = None,
    strong_residual_summary: Mapping[str, Any] | None = None,
    robustness: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    imported_parity: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    feasibility: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    thresholds: Mapping[str, Any] | None = None,
    extra_metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize weak-form supportability without promoting a weak backend.

    The label is empirical and report-local. It is not a WSINDy implementation, weak
    sparse-recovery policy, or mathematical proof of weak-form validity.
    """

    normalized_thresholds = _weak_thresholds_or_empty(thresholds)
    weak_summary, weak_metrics = _weak_report_summary_and_metrics(
        weak_report=weak_report,
        weak_report_summary=weak_report_summary,
    )
    derived_contract = _contract_from_weak_report_summary(weak_summary)
    normalized_contract = _normalize_weak_contract(
        weak_contract if weak_contract is not None else derived_contract,
        name="weak_contract",
    )

    if strong_residual is not None and strong_residual_summary is not None:
        raise SchemaValidationError("Provide either strong_residual or strong_residual_summary, not both.")
    if strong_residual_summary is not None:
        strong_summary = _runtime_report(
            strong_residual_summary,
            name="strong_residual_summary",
            expected_summary_types={"residual_batch"},
        )
    else:
        strong_summary = _residual_summary_or_none(strong_residual, name="strong_residual")
        if strong_summary is not None and strong_summary.get("summary_type") != "residual_batch":
            raise SchemaValidationError("strong_residual must summarize to summary_type 'residual_batch'.")

    normalized_robustness = _mapping_or_sequence_strict(robustness, name="robustness")
    normalized_imported_parity = _mapping_or_sequence_strict(imported_parity, name="imported_parity")
    normalized_feasibility = _mapping_or_sequence_strict(feasibility, name="feasibility")
    normalized_extra_metrics = (
        {}
        if extra_metrics is None
        else _validate_strict_json_compatible(_require_mapping(extra_metrics, name="extra_metrics"), name="extra_metrics")
    )

    component_statuses = {
        "weak_report": _weak_report_status(weak_summary, weak_metrics, normalized_thresholds),
        "weak_contract": _weak_contract_status(normalized_contract, normalized_thresholds),
        "strong_residual": _strong_residual_support_status(strong_summary),
        "robustness": _robustness_status(normalized_robustness, normalized_thresholds),
        "imported_parity": _imported_parity_status(normalized_imported_parity, normalized_thresholds),
        "feasibility": _feasibility_status(normalized_feasibility),
    }
    label = _weak_supportability_label(
        weak_summary=weak_summary,
        weak_contract=normalized_contract,
        feasibility=normalized_feasibility,
        component_statuses=component_statuses,
    )
    if label not in _WEAK_FORM_SUPPORTABILITY_LABELS:
        raise AssertionError(f"unsupported weak supportability label: {label}")

    missing_evidence = [
        component
        for component, status in component_statuses.items()
        if status["status"] == "unavailable"
    ]
    quadrature_rule = None
    if normalized_contract is not None:
        quadrature_rule = normalized_contract.get("quadrature_rule")
    if quadrature_rule is None and isinstance(normalized_feasibility, Mapping):
        quadrature_rule = normalized_feasibility.get("quadrature_rule")
    if quadrature_rule is None:
        quadrature_rule = "not_configured"

    payload = {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": "weak_form_supportability",
        "supportability_label": label,
        "component_statuses": component_statuses,
        "weak_report": weak_summary,
        "weak_report_metrics": weak_metrics,
        "weak_contract": normalized_contract,
        "quadrature_rule": quadrature_rule,
        "strong_residual": strong_summary,
        "robustness": normalized_robustness,
        "imported_parity": normalized_imported_parity,
        "feasibility": normalized_feasibility,
        "thresholds": normalized_thresholds,
        "missing_evidence": missing_evidence,
        "policy": {
            "scope": "frozen_public_heat_burgers_weak_residual_report_slice",
            "supports_wsindy": False,
            # supports_weak_derivative_backend refers to the pdelie-native
            # strong-derivative-only public weak-residual reporting slice
            # (see src/pdelie/residuals/weak_1d.py). It is unrelated to the
            # v0.31b2 diagnostic wrapper around PySINDy's WeakPDELibrary,
            # which is a distinct, non-promoting surface tracked via the
            # separate ``supports_pysindy_weak_library_diagnostic`` flag.
            "supports_weak_derivative_backend": False,
            "supports_pysindy_weak_library_diagnostic": True,
            "supports_weak_sparse_recovery": False,
            "supports_weak_kdv": False,
            "supports_weak_ks": False,
            "supports_public_weak_reaction_diffusion": False,
            "interpretation": "empirical_configured_supportability_not_mathematical_proof",
        },
        "extra_metrics": normalized_extra_metrics,
    }
    return _validate_strict_json_compatible(payload, name="weak_form_supportability summary")


def _selected_coefficients_fallback(generator: GeneratorFamily) -> list[float] | list[list[float]]:
    coefficients = _require_finite(generator.coefficients, name="GeneratorFamily.coefficients")
    if coefficients.ndim == 2 and coefficients.shape[0] == 1:
        return coefficients[0].tolist()
    return coefficients.tolist()


def _translation_span_or_none(coefficients: Any, *, parameterization: str) -> float | None:
    if coefficients is None or parameterization != "polynomial_translation_affine":
        return None
    try:
        return float(translation_span_distance(np.asarray(coefficients, dtype=float)))
    except (PDELieValidationError, TypeError, ValueError):
        return None


def _condition_number_from_diagnostics(diagnostics: Mapping[str, Any]) -> float | None:
    singular_values = diagnostics.get("singular_values")
    if singular_values is not None:
        normalized = _require_finite(np.asarray(singular_values, dtype=float), name="singular_values").ravel()
        if normalized.size == 0:
            return None
        largest = float(np.max(normalized))
        smallest = float(np.min(normalized))
        if not np.isfinite(largest) or not np.isfinite(smallest) or smallest == 0.0:
            return None
        return largest / smallest
    return _finite_float_or_none(diagnostics.get("condition_number"), name="condition_number")


def _evidence_label_from_diagnostics(diagnostics: Mapping[str, Any]) -> str:
    label = diagnostics.get("evidence_label")
    if isinstance(label, str) and label in _FIT_EVIDENCE_LABELS:
        return label

    reference_fallback_used = diagnostics.get("reference_fallback_used")
    svd_span_distance = _finite_float_or_none(diagnostics.get("svd_span_distance"), name="svd_span_distance")
    if reference_fallback_used is True:
        return "reference_fallback"
    if reference_fallback_used is False and svd_span_distance is not None:
        if svd_span_distance <= DEFAULT_TRANSLATION_SPAN_TOLERANCE:
            return "direct_svd_in_tolerance"
        return "direct_svd_out_of_tolerance"
    return "unavailable"


def summarize_generator_fit_diagnostics(generator: GeneratorFamily) -> dict[str, Any]:
    if not isinstance(generator, GeneratorFamily):
        raise SchemaValidationError("summarize_generator_fit_diagnostics requires a GeneratorFamily.")

    diagnostics = dict(generator.diagnostics)
    selected_coefficients = diagnostics.get("selected_coefficients", _selected_coefficients_fallback(generator))
    selected_span_distance = _finite_float_or_none(
        diagnostics.get(
            "selected_span_distance",
            _translation_span_or_none(selected_coefficients, parameterization=generator.parameterization),
        ),
        name="selected_span_distance",
    )

    return _summary_payload(
        "generator_fit_diagnostics",
        parameterization=generator.parameterization,
        fit_mode=diagnostics.get("fit_mode"),
        training_epsilon=_finite_float_or_none(diagnostics.get("training_epsilon"), name="training_epsilon"),
        basis=_json_safe(diagnostics.get("basis")),
        basis_delta_norms=_finite_mapping_or_none(diagnostics.get("basis_delta_norms"), name="basis_delta_norms"),
        design_column_norms=_finite_mapping_or_none(
            diagnostics.get("design_column_norms"),
            name="design_column_norms",
        ),
        singular_values=_finite_list_or_none(diagnostics.get("singular_values"), name="singular_values"),
        condition_number=_condition_number_from_diagnostics(diagnostics),
        fit_residual=_finite_float_or_none(diagnostics.get("fit_residual"), name="fit_residual"),
        min_delta_basis=diagnostics.get("min_delta_basis"),
        selected_coefficients=_finite_list_or_none(selected_coefficients, name="selected_coefficients"),
        svd_coefficients=_finite_list_or_none(diagnostics.get("svd_coefficients"), name="svd_coefficients"),
        selected_span_distance=selected_span_distance,
        svd_span_distance=_finite_float_or_none(diagnostics.get("svd_span_distance"), name="svd_span_distance"),
        reference_fallback_used=diagnostics.get("reference_fallback_used"),
        fallback_reason=diagnostics.get("fallback_reason"),
        evidence_label=_evidence_label_from_diagnostics(diagnostics),
    )


def summarize_generator_family(generator: GeneratorFamily) -> dict[str, Any]:
    if not isinstance(generator, GeneratorFamily):
        raise SchemaValidationError("summarize_generator_family requires a GeneratorFamily.")

    coefficients = _require_finite(generator.coefficients, name="GeneratorFamily.coefficients")
    translation_distance = (
        float(translation_span_distance(coefficients))
        if generator.parameterization == "polynomial_translation_affine"
        else None
    )
    diagnostics = dict(generator.diagnostics)

    return _summary_payload(
        "generator_family",
        parameterization=generator.parameterization,
        normalization=generator.normalization,
        coefficient_shape=list(coefficients.shape),
        coefficients=coefficients,
        generator_names=generator.generator_names,
        translation_span_distance=translation_distance,
        fit_mode=diagnostics.get("fit_mode"),
        reference_fallback_used=diagnostics.get("reference_fallback_used"),
        fallback_reason=diagnostics.get("fallback_reason"),
        diagnostics=diagnostics,
    )


def _formula_expression_nodes(expression: Mapping[str, Any]) -> list[str]:
    node = str(expression["node"])
    if node == "add":
        return [node, *[item for term in expression["terms"] for item in _formula_expression_nodes(term)]]
    if node == "mul":
        return [node, *[item for factor in expression["factors"] for item in _formula_expression_nodes(factor)]]
    if node == "pow":
        return [node, *_formula_expression_nodes(expression["base"])]
    if node in {"sin", "cos", "reciprocal"}:
        return [node, *_formula_expression_nodes(expression["arg"])]
    return [node]


def _formula_symbolic_references(expression: Mapping[str, Any]) -> list[dict[str, Any]]:
    node = str(expression["node"])
    if node == "symbolic_reference":
        return [{"label": expression["label"], "metadata": expression["metadata"]}]
    if node == "add":
        return [item for term in expression["terms"] for item in _formula_symbolic_references(term)]
    if node == "mul":
        return [item for factor in expression["factors"] for item in _formula_symbolic_references(factor)]
    if node == "pow":
        return _formula_symbolic_references(expression["base"])
    if node in {"sin", "cos", "reciprocal"}:
        return _formula_symbolic_references(expression["arg"])
    return []


def summarize_formula_generator_family(formula: FormulaGeneratorFamily) -> dict[str, Any]:
    if not isinstance(formula, FormulaGeneratorFamily):
        raise SchemaValidationError("summarize_formula_generator_family requires a FormulaGeneratorFamily.")

    formula.validate()
    generator_names = [generator["name"] for generator in formula.formula_generators]
    formula_kinds: dict[str, int] = {}
    symbolic_references: list[dict[str, Any]] = []
    component_nodes: dict[str, list[str]] = {component: [] for component in formula.component_names}
    for generator in formula.formula_generators:
        for component in formula.component_names:
            expression = generator["components"][component]
            nodes = _formula_expression_nodes(expression)
            for node in nodes:
                formula_kinds[node] = formula_kinds.get(node, 0) + 1
            component_nodes[component].append(str(expression["node"]))
            for reference in _formula_symbolic_references(expression):
                symbolic_references.append(
                    {
                        "generator_name": generator["name"],
                        "component": component,
                        "label": reference["label"],
                        "metadata": reference["metadata"],
                    }
                )

    return _summary_payload(
        "formula_generator_family",
        parameterization=formula.parameterization,
        schema_version=formula.schema_version,
        variables=list(formula.variables),
        component_names=list(formula.component_names),
        generator_count=len(formula.formula_generators),
        generator_names=generator_names,
        formula_kinds=formula_kinds,
        component_nodes=component_nodes,
        finite_transform_available=formula.finite_transform_spec is not None,
        finite_transform_construction_method=(
            None
            if formula.finite_transform_spec is None
            else formula.finite_transform_spec.get("construction_method")
        ),
        symbolic_references=symbolic_references,
        reciprocal_denominator_floor=FormulaGeneratorFamily.RECIPROCAL_DENOMINATOR_FLOOR,
        diagnostics=formula.diagnostics,
    )


def summarize_verification_report(report: VerificationReport) -> dict[str, Any]:
    if not isinstance(report, VerificationReport):
        raise SchemaValidationError("summarize_verification_report requires a VerificationReport.")

    epsilon_values = _require_finite(report.epsilon_values, name="VerificationReport.epsilon_values")
    error_curve = _require_finite(report.error_curve, name="VerificationReport.error_curve")

    return _summary_payload(
        "verification_report",
        norm=report.norm,
        classification=report.classification,
        epsilon_values=epsilon_values,
        error_curve=error_curve,
        first_epsilon=float(epsilon_values[0]),
        first_error=float(error_curve[0]),
        max_error=float(np.max(error_curve)),
        diagnostics=report.diagnostics,
    )


def summarize_vertical_slice(
    *,
    derivatives: DerivativeBatch,
    residual: ResidualBatch,
    generator: GeneratorFamily,
    verification: VerificationReport,
    extra_metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(derivatives, DerivativeBatch):
        raise SchemaValidationError("summarize_vertical_slice requires derivatives to be a DerivativeBatch.")
    if extra_metrics is None:
        normalized_extra_metrics: Mapping[str, Any] = {}
    else:
        normalized_extra_metrics = _require_mapping(extra_metrics, name="extra_metrics")

    return _summary_payload(
        "vertical_slice",
        derivative_backend=derivatives.backend,
        derivative_keys=sorted(str(name) for name in derivatives.derivatives),
        derivative_config=derivatives.config,
        derivative_diagnostics=derivatives.diagnostics,
        residual=summarize_residual_batch(residual),
        generator=summarize_generator_family(generator),
        verification=summarize_verification_report(verification),
        extra_metrics=normalized_extra_metrics,
    )


def enrich_method_scores(
    values: Mapping[str, float | None] | None,
    metadata: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]] | None:
    """v0.32b: pair a plain ``dict[str, float | None]`` with a metadata map.

    ``values`` come from :class:`SymmetryMethodResult.method_scores`, keeping
    the v0.30.1 registry contract intact.

    ``metadata`` is the method's frozen ``SCORE_METADATA`` class attribute:
    ``{score_name: {"direction": ..., "description": ..., "units": ...}}``.

    Returns the enriched-form ``dict[str, {"value", "direction",
    "description", "units"}]`` accepted by
    :func:`summarize_generator_confidence`. Returns ``None`` when ``values``
    is ``None``.

    Raises :class:`SchemaValidationError` if:
    - a score value has no metadata entry, or
    - a value is not a finite float or ``None``, or
    - a metadata direction is not in the frozen vocabulary.
    """
    if values is None:
        return None
    values_map = _require_mapping(values, name="values")
    metadata_map = _require_mapping(metadata, name="metadata")
    enriched: dict[str, dict[str, Any]] = {}
    for raw_key, raw_value in values_map.items():
        score_name = str(raw_key)
        if score_name not in metadata_map:
            raise SchemaValidationError(
                f"enrich_method_scores: no metadata entry for score "
                f"{score_name!r}; metadata keys="
                f"{sorted(metadata_map.keys())!r}."
            )
        entry_metadata = _require_mapping(
            metadata_map[score_name],
            name=f"metadata[{score_name!r}]",
        )
        direction = entry_metadata.get("direction")
        if direction not in _METHOD_SCORE_DIRECTIONS:
            raise SchemaValidationError(
                f"enrich_method_scores: metadata[{score_name!r}].direction "
                f"must be one of {sorted(_METHOD_SCORE_DIRECTIONS)}; got "
                f"{direction!r}."
            )
        description = entry_metadata.get("description")
        if not isinstance(description, str) or not description.strip():
            raise SchemaValidationError(
                f"enrich_method_scores: metadata[{score_name!r}].description "
                "must be a non-empty string."
            )
        units = entry_metadata.get("units")
        if units is not None and (
            not isinstance(units, str) or not units.strip()
        ):
            raise SchemaValidationError(
                f"enrich_method_scores: metadata[{score_name!r}].units must "
                "be a non-empty string or None."
            )
        score_value = _validate_finite_scalar(
            raw_value, name=f"values[{score_name!r}]"
        )
        enriched[score_name] = {
            "value": score_value,
            "direction": direction,
            "description": description,
            "units": units,
        }
    return enriched


def summarize_generator_confidence(
    *,
    residual: ResidualBatch | Mapping[str, Any] | None = None,
    generator: GeneratorFamily | Mapping[str, Any] | None = None,
    fit_diagnostics: GeneratorFamily | Mapping[str, Any] | None = None,
    verification: VerificationReport | Mapping[str, Any] | None = None,
    candidate_validation: Mapping[str, Any] | None = None,
    coverage: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    consistency: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    orbit: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    thresholds: Mapping[str, Any] | None = None,
    extra_metrics: Mapping[str, Any] | None = None,
    method_scores: Mapping[str, Any] | None = None,
    uncertainty_report: Mapping[str, Any] | None = None,
    calibration_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if extra_metrics is None:
        normalized_extra_metrics: Mapping[str, Any] = {}
    else:
        normalized_extra_metrics = _require_mapping(extra_metrics, name="extra_metrics")

    # v0.32b additive fields — default None for backward compatibility.
    normalized_method_scores = _validate_v0_32b_method_scores(
        method_scores, name="method_scores"
    )
    normalized_uncertainty_report = _validate_v0_32b_uncertainty_report(
        uncertainty_report, name="uncertainty_report"
    )
    normalized_calibration_report = _validate_v0_32b_calibration_report(
        calibration_report, name="calibration_report"
    )

    normalized_thresholds = _thresholds_or_empty(thresholds)
    residual_summary = _residual_summary_or_none(residual, name="residual")
    generator_summary = _generator_summary_or_none(generator, name="generator")
    if fit_diagnostics is None and isinstance(generator, GeneratorFamily):
        fit_summary = summarize_generator_fit_diagnostics(generator)
    else:
        fit_summary = _fit_diagnostic_summary_or_none(fit_diagnostics, name="fit_diagnostics")
    verification_summary = _verification_summary_or_none(verification, name="verification")
    candidate_validation_summary = _candidate_validation_summary_or_none(
        candidate_validation,
        name="candidate_validation",
    )
    coverage_summary = _coverage_summary_or_list_or_none(coverage, name="coverage")
    consistency_summary = _consistency_summary_or_list_or_none(consistency, name="consistency")
    orbit_summary = _orbit_summary_or_list_or_none(orbit, name="orbit")

    component_statuses = {
        "residual": _confidence_residual_status(residual_summary, normalized_thresholds),
        "fit": _confidence_fit_status(fit_summary),
        "verification": _confidence_verification_status(verification_summary, normalized_thresholds),
        "candidate_validation": _confidence_candidate_validation_status(candidate_validation_summary),
        "coverage": _confidence_coverage_status(coverage_summary, normalized_thresholds),
        "consistency": _confidence_pass_boolean_status(
            consistency_summary,
            unavailable_reason="consistency_not_provided",
            not_configured_reason="consistency_pass_flags_not_reported",
            failed_reason="consistency_pass_flag_failed",
            passed_reason="consistency_pass_flags_passed",
        ),
        "orbit": _confidence_pass_boolean_status(
            orbit_summary,
            unavailable_reason="orbit_not_provided",
            not_configured_reason="orbit_pass_flags_not_reported",
            failed_reason="orbit_pass_flag_failed",
            passed_reason="orbit_pass_flags_passed",
        ),
    }
    missing_evidence = [
        component
        for component, status in component_statuses.items()
        if status["status"] == "unavailable"
    ]
    evidence_present = any(
        item is not None
        for item in (fit_summary, verification_summary, candidate_validation_summary)
    )
    label = _confidence_label(component_statuses, evidence_present=evidence_present)
    if label not in _CONFIDENCE_LABELS:
        raise AssertionError(f"unsupported confidence label: {label}")

    payload = {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": "generator_confidence",
        "confidence_label": label,
        "component_statuses": component_statuses,
        "residual": residual_summary,
        "generator": generator_summary,
        "fit_diagnostics": fit_summary,
        "verification": verification_summary,
        "candidate_validation": candidate_validation_summary,
        "coverage": coverage_summary,
        "consistency": consistency_summary,
        "orbit": orbit_summary,
        "thresholds": normalized_thresholds,
        "missing_evidence": missing_evidence,
        "extra_metrics": normalized_extra_metrics,
        # v0.32b additive fields (default-None for backward compatibility).
        "method_scores": normalized_method_scores,
        "uncertainty_report": normalized_uncertainty_report,
        "calibration_report": normalized_calibration_report,
    }
    validated: dict[str, Any] = _validate_strict_json_compatible(
        payload, name="generator confidence summary"
    )
    return validated


def summarize_invariant_workflow(
    *,
    orbit: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    coverage: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    consistency: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    generator: GeneratorFamily | Mapping[str, Any] | None = None,
    verification: VerificationReport | Mapping[str, Any] | None = None,
    fit_diagnostics: GeneratorFamily | Mapping[str, Any] | None = None,
    extra_metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if extra_metrics is None:
        normalized_extra_metrics: Mapping[str, Any] = {}
    else:
        normalized_extra_metrics = _require_mapping(extra_metrics, name="extra_metrics")

    generator_summary = _generator_summary_or_none(generator, name="generator")
    if fit_diagnostics is None and isinstance(generator, GeneratorFamily):
        fit_summary = summarize_generator_fit_diagnostics(generator)
    else:
        fit_summary = _fit_diagnostic_summary_or_none(fit_diagnostics, name="fit_diagnostics")

    return _summary_payload(
        "invariant_workflow",
        orbit=_runtime_report_or_list(
            orbit,
            name="orbit",
            expected_summary_types={"uniform_translation_orbit"},
        ),
        coverage=_runtime_report_or_list(
            coverage,
            name="coverage",
            expected_summary_types={"periodic_window_coverage"},
        ),
        consistency=_runtime_report_or_list(
            consistency,
            name="consistency",
            expected_summary_types={"uniform_translation_consistency"},
        ),
        generator=generator_summary,
        fit_diagnostics=fit_summary,
        verification=_verification_summary_or_none(verification, name="verification"),
        extra_metrics=normalized_extra_metrics,
    )


def _workflow_readiness_status(report: Mapping[str, Any] | None) -> dict[str, Any]:
    if report is None:
        return _component_status("unavailable", reason="field_readiness_not_provided")
    label = report.get("readiness_label")
    if label == "ready":
        return _component_status("passed", reason="field_readiness_ready")
    if label == "needs_attention":
        return _component_status("warning", reason="field_readiness_needs_attention")
    if label == "not_ready":
        return _component_status("failed", reason="field_readiness_not_ready")
    return _component_status("warning", reason="field_readiness_unknown")


def _workflow_confidence_status(report: Mapping[str, Any] | None) -> dict[str, Any]:
    if report is None:
        return _component_status("unavailable", reason="generator_confidence_not_provided")
    label = report.get("confidence_label")
    if label == "strong":
        return _component_status("passed", reason="generator_confidence_strong")
    if label in {"qualified", "insufficient_evidence"}:
        return _component_status("warning", reason=f"generator_confidence_{label}")
    if label == "failed":
        return _component_status("failed", reason="generator_confidence_failed")
    return _component_status("warning", reason="generator_confidence_unknown")


def _workflow_discovery_inputs_status(report: Mapping[str, Any] | None) -> dict[str, Any]:
    if report is None:
        return _component_status("unavailable", reason="discovery_inputs_not_provided")
    return _component_status(
        "passed",
        reason="discovery_inputs_summarized",
        details={
            "trajectory_count": report.get("trajectory_count"),
            "num_state_features": report.get("num_state_features"),
        },
    )


def _workflow_discovery_result_status(report: Mapping[str, Any] | None) -> dict[str, Any]:
    if report is None:
        return _component_status("unavailable", reason="discovery_result_not_provided")
    if report.get("status") == "success":
        return _component_status("passed", reason="discovery_result_success")
    if report.get("status") == "failed":
        return _component_status("failed", reason="discovery_result_failed")
    return _component_status("warning", reason="discovery_result_unknown_status")


def _workflow_orbit_provenance_status(report: Mapping[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if report is None:
        return _component_status("unavailable", reason="orbit_batch_not_provided"), None

    output_batch_size = report.get("output_batch_size")
    source_indices = report.get("source_batch_indices")
    shift_indices = report.get("shift_indices")
    details = {
        "output_batch_size": output_batch_size,
        "source_indices_present": isinstance(source_indices, list),
        "shift_indices_present": isinstance(shift_indices, list),
        "source_index_count": len(source_indices) if isinstance(source_indices, list) else None,
        "shift_index_count": len(shift_indices) if isinstance(shift_indices, list) else None,
    }
    if not isinstance(output_batch_size, int):
        return (
            _component_status("warning", reason="orbit_batch_size_unavailable", details=details),
            details,
        )
    if not isinstance(source_indices, list) and not isinstance(shift_indices, list):
        return (
            _component_status("warning", reason="orbit_provenance_indices_not_recorded", details=details),
            details,
        )
    if not isinstance(source_indices, list) or not isinstance(shift_indices, list):
        return (
            _component_status("warning", reason="orbit_provenance_partially_recorded", details=details),
            details,
        )
    if len(source_indices) != output_batch_size or len(shift_indices) != output_batch_size:
        return (
            _component_status("failed", reason="orbit_provenance_index_count_mismatch", details=details),
            details,
        )
    return _component_status("passed", reason="orbit_provenance_traceable", details=details), details


def _workflow_label(component_statuses: Mapping[str, Mapping[str, Any]]) -> str:
    statuses = [str(status["status"]) for status in component_statuses.values()]
    if any(status == "failed" for status in statuses):
        return "failed"
    if any(status in {"warning", "not_configured", "unavailable"} for status in statuses):
        return "needs_attention"
    return "ready"


def _normalize_partitions(partitions: Any) -> list[str]:
    if isinstance(partitions, (str, bytes)) or not isinstance(partitions, Sequence):
        raise SchemaValidationError("partitions must be a non-empty sequence of non-empty strings.")
    normalized = list(partitions)
    if not normalized:
        raise SchemaValidationError("partitions must be non-empty.")
    result: list[str] = []
    for index, label in enumerate(normalized):
        if not isinstance(label, str) or not label.strip():
            raise SchemaValidationError(f"partitions[{index}] must be a non-empty string.")
        result.append(label)
    return result


def _normalize_optional_sequence(value: Any, *, name: str, expected_length: int | None = None) -> list[Any] | None:
    if value is None:
        return None
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise SchemaValidationError(f"{name} must be a sequence.")
    normalized = list(value)
    if expected_length is not None and len(normalized) != expected_length:
        raise SchemaValidationError(f"{name} length must match the audited sample count.")
    return _validate_strict_json_compatible(normalized, name=name)


def _normalize_index_sequence(
    value: Any,
    *,
    name: str,
    expected_length: int,
) -> list[int] | None:
    if value is None:
        return None
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise SchemaValidationError(f"{name} must be a sequence of non-negative integers.")
    normalized: list[int] = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, Integral):
            raise SchemaValidationError(f"{name}[{index}] must be a non-negative integer.")
        integer = int(item)
        if integer < 0:
            raise SchemaValidationError(f"{name}[{index}] must be a non-negative integer.")
        normalized.append(integer)
    if len(normalized) != expected_length:
        raise SchemaValidationError(f"{name} length must match the audited sample count.")
    return normalized


def _partition_counts(partitions: Sequence[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for label in partitions:
        counts[label] = counts.get(label, 0) + 1
    return counts


def _source_keys_from_provenance(
    *,
    sample_count: int,
    source_indices: Sequence[int] | None,
    source_ids: Sequence[Any] | None,
    source_batch_size: int | None,
) -> list[Any] | None:
    if source_indices is not None:
        if source_ids is not None:
            required = source_batch_size
            if required is None and source_indices:
                required = max(source_indices) + 1
            if required is not None and len(source_ids) != required:
                raise SchemaValidationError(
                    "source_ids length must match the source batch size when orbit source indices are present."
                )
            if any(index >= len(source_ids) for index in source_indices):
                raise SchemaValidationError("orbit source indices must be within source_ids.")
            return [source_ids[index] for index in source_indices]
        return list(source_indices)
    if source_ids is not None:
        if len(source_ids) != sample_count:
            raise SchemaValidationError(
                "source_ids length must match partitions when no orbit source indices are present."
            )
        return list(source_ids)
    return None


def _shift_keys_from_provenance(
    *,
    shift_indices: Sequence[int] | None,
    raw_shifts: Sequence[Any] | None,
    normalized_shifts: Sequence[Any] | None,
) -> tuple[list[Any] | None, list[bool] | None]:
    if shift_indices is None:
        return None, None
    shift_keys: list[Any] = list(shift_indices)
    identity_flags: list[bool] | None = None
    if normalized_shifts is not None:
        normalized = _finite_list_or_none(normalized_shifts, name="orbit_batch.normalized_shifts")
        assert normalized is not None
        identity_lookup: dict[int, bool] = {}
        tolerance = 1e-12
        for index, value in enumerate(normalized):
            identity_lookup[index] = bool(abs(float(value)) <= tolerance)
        if any(index >= len(normalized) for index in shift_indices):
            raise SchemaValidationError("orbit shift indices must be within normalized_shifts.")
        identity_flags = [identity_lookup.get(index, False) for index in shift_indices]
    elif raw_shifts is not None:
        normalized = _finite_list_or_none(raw_shifts, name="orbit_batch.raw_shifts")
        assert normalized is not None
        identity_lookup = {index: bool(abs(float(value)) <= 1e-12) for index, value in enumerate(normalized)}
        if any(index >= len(normalized) for index in shift_indices):
            raise SchemaValidationError("orbit shift indices must be within raw_shifts.")
        identity_flags = [identity_lookup.get(index, False) for index in shift_indices]
    return shift_keys, identity_flags


def _cross_partition_keys(
    *,
    keys: Sequence[Any],
    partitions: Sequence[str],
) -> tuple[bool, dict[str, set[str]], dict[str, int]]:
    by_key: dict[str, set[str]] = {}
    for key, partition in zip(keys, partitions, strict=True):
        key_string = json.dumps(_json_safe(key), sort_keys=True, allow_nan=False)
        by_key.setdefault(key_string, set()).add(partition)

    pair_counts: dict[str, int] = {}
    for partition_set in by_key.values():
        if len(partition_set) <= 1:
            continue
        for left, right in combinations(sorted(partition_set), 2):
            pair_key = f"{left}|{right}"
            pair_counts[pair_key] = pair_counts.get(pair_key, 0) + 1
    return any(len(partition_set) > 1 for partition_set in by_key.values()), by_key, pair_counts


def _partition_pair_diagnostics(
    *,
    partitions: Sequence[str],
    source_pair_counts: Mapping[str, int],
    shifted_pair_counts: Mapping[str, int],
    identity_pair_counts: Mapping[str, int],
) -> dict[str, dict[str, int]]:
    labels = sorted(set(partitions))
    diagnostics: dict[str, dict[str, int]] = {}
    for left, right in combinations(labels, 2):
        pair_key = f"{left}|{right}"
        diagnostics[pair_key] = {
            "source_overlap_count": int(source_pair_counts.get(pair_key, 0)),
            "shifted_source_overlap_count": int(shifted_pair_counts.get(pair_key, 0)),
            "identity_shift_overlap_count": int(identity_pair_counts.get(pair_key, 0)),
        }
    return diagnostics


def _split_risk_label(
    *,
    source_keys_present: bool,
    shift_keys_present: bool,
    source_overlap: bool,
    shifted_overlap: bool,
    identity_overlap: bool,
) -> tuple[str, list[str]]:
    if source_overlap or shifted_overlap or identity_overlap:
        reasons = []
        if source_overlap:
            reasons.append("source_overlap_across_partitions")
        if shifted_overlap:
            reasons.append("source_and_shift_overlap_across_partitions")
        if identity_overlap:
            reasons.append("identity_shift_overlap_across_partitions")
        return "traceable_overlap", reasons
    if source_keys_present:
        reasons = ["source_provenance_available_no_cross_partition_overlap"]
        if not shift_keys_present:
            reasons.append("shift_provenance_missing_but_source_overlap_absent")
        return "no_detected_overlap", reasons
    if shift_keys_present:
        return "inconclusive", ["shift_provenance_available_without_source_provenance"]
    return "missing_provenance", ["source_and_shift_provenance_missing"]


def _split_component_statuses(
    *,
    risk_label: str,
    source_traceable: bool,
    shift_traceable: bool,
    sample_metadata_present: bool,
) -> dict[str, dict[str, Any]]:
    if risk_label == "traceable_overlap":
        overlap_status = _component_status("warning", reason="traceable_cross_partition_overlap")
    elif risk_label == "no_detected_overlap":
        overlap_status = _component_status("passed", reason="no_cross_partition_overlap_detected")
    elif risk_label == "missing_provenance":
        overlap_status = _component_status("warning", reason="provenance_missing")
    else:
        overlap_status = _component_status("warning", reason="provenance_inconclusive")
    return {
        "partitions": _component_status("passed", reason="partitions_valid"),
        "source_provenance": _component_status(
            "passed" if source_traceable else "warning",
            reason="source_provenance_traceable" if source_traceable else "source_provenance_missing",
        ),
        "shift_provenance": _component_status(
            "passed" if shift_traceable else "warning",
            reason="shift_provenance_traceable" if shift_traceable else "shift_provenance_missing",
        ),
        "sample_metadata": _component_status(
            "passed" if sample_metadata_present else "not_configured",
            reason="sample_metadata_recorded" if sample_metadata_present else "sample_metadata_not_provided",
        ),
        "overlap_risk": overlap_status,
    }


def summarize_split_leakage_provenance(
    *,
    partitions: Sequence[str],
    orbit_batch: OrbitBatchResult | Mapping[str, Any] | None = None,
    source_ids: Sequence[Any] | None = None,
    sample_metadata: Sequence[Mapping[str, Any]] | None = None,
    source_report_id: Any | None = None,
    extra_metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Report detectable provenance overlap across user-supplied partitions.

    This helper does not create splits, enforce leakage policy, or judge benchmark validity.
    """

    normalized_partitions = _normalize_partitions(partitions)
    sample_count = len(normalized_partitions)
    orbit_batch_summary = _orbit_batch_summary_or_none(orbit_batch, name="orbit_batch")
    if orbit_batch_summary is not None:
        orbit_batch_summary = _validate_strict_json_compatible(orbit_batch_summary, name="orbit_batch")
    if orbit_batch_summary is not None:
        orbit_sample_count = orbit_batch_summary.get("output_batch_size")
        if not isinstance(orbit_sample_count, int):
            raise SchemaValidationError("orbit_batch.output_batch_size must be an integer.")
        if orbit_sample_count != sample_count:
            raise SchemaValidationError("partitions length must match orbit_batch.output_batch_size.")

    normalized_source_ids = _normalize_optional_sequence(source_ids, name="source_ids")
    normalized_sample_metadata = _normalize_optional_sequence(
        sample_metadata,
        name="sample_metadata",
        expected_length=sample_count,
    )
    normalized_source_report_id = _validate_strict_json_compatible(source_report_id, name="source_report_id")
    normalized_extra_metrics = (
        {}
        if extra_metrics is None
        else _validate_strict_json_compatible(_require_mapping(extra_metrics, name="extra_metrics"), name="extra_metrics")
    )

    source_indices = None
    shift_indices = None
    source_batch_size = None
    raw_shifts = None
    normalized_shifts = None
    if orbit_batch_summary is not None:
        source_indices = _normalize_index_sequence(
            orbit_batch_summary.get("source_batch_indices"),
            name="orbit_batch.source_batch_indices",
            expected_length=sample_count,
        )
        shift_indices = _normalize_index_sequence(
            orbit_batch_summary.get("shift_indices"),
            name="orbit_batch.shift_indices",
            expected_length=sample_count,
        )
        source_batch_size = orbit_batch_summary.get("source_batch_size")
        if source_batch_size is not None and (not isinstance(source_batch_size, int) or source_batch_size < 0):
            raise SchemaValidationError("orbit_batch.source_batch_size must be a non-negative integer when present.")
        raw_shifts = orbit_batch_summary.get("raw_shifts")
        normalized_shifts = orbit_batch_summary.get("normalized_shifts")

    source_keys = _source_keys_from_provenance(
        sample_count=sample_count,
        source_indices=source_indices,
        source_ids=normalized_source_ids,
        source_batch_size=source_batch_size,
    )
    shift_keys, identity_flags = _shift_keys_from_provenance(
        shift_indices=shift_indices,
        raw_shifts=raw_shifts,
        normalized_shifts=normalized_shifts,
    )

    source_overlap = False
    source_pair_counts: dict[str, int] = {}
    if source_keys is not None:
        source_overlap, _, source_pair_counts = _cross_partition_keys(keys=source_keys, partitions=normalized_partitions)

    shifted_overlap = False
    shifted_pair_counts: dict[str, int] = {}
    if source_keys is not None and shift_keys is not None:
        shifted_keys = list(zip(source_keys, shift_keys, strict=True))
        shifted_overlap, _, shifted_pair_counts = _cross_partition_keys(
            keys=shifted_keys,
            partitions=normalized_partitions,
        )

    identity_overlap = False
    identity_pair_counts: dict[str, int] = {}
    if source_keys is not None and identity_flags is not None:
        identity_keys = [
            source_key
            for source_key, identity in zip(source_keys, identity_flags, strict=True)
            if identity
        ]
        identity_partitions = [
            partition
            for partition, identity in zip(normalized_partitions, identity_flags, strict=True)
            if identity
        ]
        if identity_keys:
            identity_overlap, _, identity_pair_counts = _cross_partition_keys(
                keys=identity_keys,
                partitions=identity_partitions,
            )

    source_traceable = source_keys is not None
    shift_traceable = shift_keys is not None
    risk_label, risk_reasons = _split_risk_label(
        source_keys_present=source_traceable,
        shift_keys_present=shift_traceable,
        source_overlap=source_overlap,
        shifted_overlap=shifted_overlap,
        identity_overlap=identity_overlap,
    )
    if risk_label not in _SPLIT_LEAKAGE_RISK_LABELS:
        raise AssertionError(f"unsupported split leakage risk label: {risk_label}")

    component_statuses = _split_component_statuses(
        risk_label=risk_label,
        source_traceable=source_traceable,
        shift_traceable=shift_traceable,
        sample_metadata_present=normalized_sample_metadata is not None,
    )

    return _summary_payload(
        "split_leakage_provenance",
        partition_counts=_partition_counts(normalized_partitions),
        sample_count=sample_count,
        provenance_available=source_traceable or shift_traceable,
        source_index_traceable=source_indices is not None,
        source_id_traceable=source_keys is not None and source_indices is None,
        shift_index_traceable=shift_indices is not None,
        duplicate_source_across_partitions=source_overlap,
        duplicate_shifted_source_across_partitions=shifted_overlap,
        identity_shift_cross_partition_overlap=identity_overlap,
        partition_pair_diagnostics=_partition_pair_diagnostics(
            partitions=normalized_partitions,
            source_pair_counts=source_pair_counts,
            shifted_pair_counts=shifted_pair_counts,
            identity_pair_counts=identity_pair_counts,
        ),
        risk_label=risk_label,
        risk_reasons=risk_reasons,
        component_statuses=component_statuses,
        source_report_id=normalized_source_report_id,
        source_ids=normalized_source_ids,
        sample_metadata=normalized_sample_metadata,
        orbit_batch=orbit_batch_summary,
        returns_field_batch=False,
        policy={
            "partitions_are_user_supplied": True,
            "creates_splits": False,
            "prevents_leakage": False,
            "defines_benchmark_success": False,
        },
        extra_metrics=normalized_extra_metrics,
    )


def _workflow_split_provenance_status(report: Mapping[str, Any] | None) -> dict[str, Any]:
    if report is None:
        return _component_status("unavailable", reason="split_provenance_not_provided")
    label = report.get("risk_label")
    if label == "no_detected_overlap":
        return _component_status("passed", reason="split_provenance_no_detected_overlap")
    if label == "traceable_overlap":
        return _component_status("warning", reason="split_provenance_traceable_overlap")
    if label == "missing_provenance":
        return _component_status("warning", reason="split_provenance_missing_provenance")
    if label == "inconclusive":
        return _component_status("warning", reason="split_provenance_inconclusive")
    return _component_status("warning", reason="split_provenance_unknown")


def summarize_downstream_discovery_workflow(
    *,
    field_readiness: Mapping[str, Any] | None = None,
    generator_confidence: Mapping[str, Any] | None = None,
    orbit_batch: OrbitBatchResult | Mapping[str, Any] | None = None,
    discovery_inputs: Mapping[str, Any] | None = None,
    discovery_result: Mapping[str, Any] | None = None,
    split_provenance: Mapping[str, Any] | None = None,
    extra_metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Combine downstream discovery runtime reports without imposing split or leakage policy."""

    if extra_metrics is None:
        normalized_extra_metrics: Mapping[str, Any] = {}
    else:
        normalized_extra_metrics = _require_mapping(extra_metrics, name="extra_metrics")

    readiness_summary = (
        None
        if field_readiness is None
        else _runtime_report(
            field_readiness,
            name="field_readiness",
            expected_summary_types={"field_batch_readiness"},
        )
    )
    confidence_summary = (
        None
        if generator_confidence is None
        else _runtime_report(
            generator_confidence,
            name="generator_confidence",
            expected_summary_types={"generator_confidence"},
        )
    )
    orbit_batch_summary = _orbit_batch_summary_or_none(orbit_batch, name="orbit_batch")
    discovery_inputs_summary = _discovery_bridge_summary_or_none(discovery_inputs, name="discovery_inputs")
    discovery_result_summary = _discovery_result_summary_or_none(discovery_result, name="discovery_result")
    split_provenance_summary = _split_provenance_summary_or_none(split_provenance, name="split_provenance")
    orbit_provenance_status, orbit_provenance = _workflow_orbit_provenance_status(orbit_batch_summary)

    component_statuses = {
        "field_readiness": _workflow_readiness_status(readiness_summary),
        "generator_confidence": _workflow_confidence_status(confidence_summary),
        "orbit_provenance": orbit_provenance_status,
        "discovery_inputs": _workflow_discovery_inputs_status(discovery_inputs_summary),
        "discovery_result": _workflow_discovery_result_status(discovery_result_summary),
        "split_provenance": _workflow_split_provenance_status(split_provenance_summary),
    }
    missing_evidence = [
        component
        for component, status in component_statuses.items()
        if status["status"] == "unavailable"
    ]

    return _summary_payload(
        "downstream_discovery_workflow",
        workflow_label=_workflow_label(component_statuses),
        component_statuses=component_statuses,
        field_readiness=readiness_summary,
        generator_confidence=confidence_summary,
        orbit_batch=orbit_batch_summary,
        orbit_provenance=orbit_provenance,
        discovery_inputs=discovery_inputs_summary,
        discovery_result=discovery_result_summary,
        split_provenance=split_provenance_summary,
        missing_evidence=missing_evidence,
        extra_metrics=normalized_extra_metrics,
    )
