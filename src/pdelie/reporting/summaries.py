from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from itertools import combinations
from numbers import Integral
from typing import Any

import numpy as np

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
_SPLIT_LEAKAGE_RISK_LABELS = frozenset(
    {
        "no_detected_overlap",
        "traceable_overlap",
        "missing_provenance",
        "inconclusive",
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
    elif boundary_conditions.get("x") != "periodic":
        failures.append("x_boundary_not_periodic")
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
        stable_scope={
            "dims": ["batch", "time", "x", "var"],
            "scalar_1d_periodic": True,
            "grid_type": "rectilinear",
            "grid_regularity": "uniform",
        },
    )


def summarize_residual_batch(residual: ResidualBatch) -> dict[str, Any]:
    if not isinstance(residual, ResidualBatch):
        raise SchemaValidationError("summarize_residual_batch requires a ResidualBatch.")

    residual_values = _require_finite(residual.residual, name="ResidualBatch.residual")
    return _summary_payload(
        "residual_batch",
        residual_shape=list(residual_values.shape),
        definition_type=residual.definition_type,
        normalization=residual.normalization,
        max_abs_residual=float(np.max(np.abs(residual_values))),
        rms_residual=float(np.sqrt(np.mean(np.square(residual_values)))),
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
) -> dict[str, Any]:
    if extra_metrics is None:
        normalized_extra_metrics: Mapping[str, Any] = {}
    else:
        normalized_extra_metrics = _require_mapping(extra_metrics, name="extra_metrics")

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

    return _summary_payload(
        "generator_confidence",
        confidence_label=label,
        component_statuses=component_statuses,
        residual=residual_summary,
        generator=generator_summary,
        fit_diagnostics=fit_summary,
        verification=verification_summary,
        candidate_validation=candidate_validation_summary,
        coverage=coverage_summary,
        consistency=consistency_summary,
        orbit=orbit_summary,
        thresholds=normalized_thresholds,
        missing_evidence=missing_evidence,
        extra_metrics=normalized_extra_metrics,
    )


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
