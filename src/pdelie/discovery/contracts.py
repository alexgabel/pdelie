from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from pdelie.discovery.evaluation import evaluate_discovery_recovery
from pdelie.errors import SchemaValidationError


_SUMMARY_SCHEMA_VERSION = "0.1"
_RESULT_STATUSES = frozenset({"success", "failed"})


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


def _summary_payload(summary_type: str, **items: Any) -> dict[str, Any]:
    return _validate_json_compatible(
        {
            "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
            "summary_type": summary_type,
            **items,
        },
        name=f"{summary_type} summary",
    )


def _require_mapping(value: object, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{name} must be a mapping.")
    return value


def _finite_float(value: object, *, name: str) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{name} must be a finite scalar float.") from exc
    if not np.isfinite(normalized):
        raise SchemaValidationError(f"{name} must be a finite scalar float.")
    return normalized


def _support_epsilon(value: object) -> float:
    epsilon = _finite_float(value, name="support_epsilon")
    if epsilon < 0.0:
        raise SchemaValidationError("support_epsilon must be non-negative.")
    return epsilon


def _validate_trajectories(trajectories: object) -> list[np.ndarray]:
    if not isinstance(trajectories, (list, tuple)) or not trajectories:
        raise SchemaValidationError("trajectories must be a non-empty list or tuple of 2D finite numeric arrays.")

    normalized: list[np.ndarray] = []
    expected_shape: tuple[int, int] | None = None
    for index, trajectory in enumerate(trajectories):
        try:
            array = np.asarray(trajectory, dtype=float)
        except (TypeError, ValueError) as exc:
            raise SchemaValidationError(
                f"trajectories[{index}] must be a 2D finite numeric array."
            ) from exc
        if array.ndim != 2 or 0 in array.shape:
            raise SchemaValidationError(f"trajectories[{index}] must be a non-empty 2D finite numeric array.")
        if not np.all(np.isfinite(array)):
            raise SchemaValidationError(f"trajectories[{index}] must contain only finite values.")
        shape = tuple(int(dim) for dim in array.shape)
        if expected_shape is None:
            expected_shape = shape
        elif shape != expected_shape:
            raise SchemaValidationError("all trajectories must share identical shape.")
        normalized.append(array)
    return normalized


def _validate_time_values(time_values: object, *, num_times: int) -> np.ndarray:
    try:
        array = np.asarray(time_values, dtype=float)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError("time_values must be a one-dimensional finite numeric array.") from exc
    if array.ndim != 1 or array.size != num_times:
        raise SchemaValidationError("time_values must be one-dimensional and match trajectory time dimension.")
    if array.size < 2:
        raise SchemaValidationError("time_values must contain at least two entries.")
    if not np.all(np.isfinite(array)):
        raise SchemaValidationError("time_values must contain only finite values.")
    if not np.all(np.diff(array) > 0.0):
        raise SchemaValidationError("time_values must be strictly increasing.")
    return array


def _validate_feature_names(feature_names: object, *, num_features: int) -> list[str]:
    if isinstance(feature_names, (str, bytes)) or not isinstance(feature_names, Sequence):
        raise SchemaValidationError("feature_names must be a sequence of unique non-empty strings.")
    normalized = list(feature_names)
    if len(normalized) != num_features:
        raise SchemaValidationError("feature_names length must match trajectory feature dimension.")
    if any(not isinstance(name, str) or not name for name in normalized):
        raise SchemaValidationError("feature_names must contain only non-empty strings.")
    if len(set(normalized)) != len(normalized):
        raise SchemaValidationError("feature_names must be unique.")
    return normalized


def _validate_string_mapping(value: object, *, name: str, feature_names: Sequence[str]) -> dict[str, str]:
    mapping = _require_mapping(value, name=name)
    normalized: dict[str, str] = {}
    expected_keys = set(feature_names)
    if set(mapping) != expected_keys:
        raise SchemaValidationError(f"{name} keys must exactly match feature_names.")
    for key, item in mapping.items():
        if not isinstance(key, str) or not key:
            raise SchemaValidationError(f"{name} keys must be non-empty strings.")
        if not isinstance(item, str):
            raise SchemaValidationError(f"{name}.{key} must be a string.")
        normalized[key] = item
    return normalized


def _validate_term_mapping(value: object, *, name: str) -> dict[str, float]:
    mapping = _require_mapping(value, name=name)
    normalized: dict[str, float] = {}
    for term, coefficient in mapping.items():
        if not isinstance(term, str) or not term:
            raise SchemaValidationError(f"{name} term keys must be non-empty strings.")
        normalized[term] = _finite_float(coefficient, name=f"{name}.{term}")
    return normalized


def _validate_feature_term_mapping(
    value: object,
    *,
    name: str,
    feature_names: Sequence[str],
) -> dict[str, dict[str, float]]:
    mapping = _require_mapping(value, name=name)
    expected_keys = set(feature_names)
    if set(mapping) != expected_keys:
        raise SchemaValidationError(f"{name} keys must exactly match feature_names.")
    return {
        str(feature_name): _validate_term_mapping(
            mapping[feature_name],
            name=f"{name}.{feature_name}",
        )
        for feature_name in feature_names
    }


def _coefficient_summary(coefficients: object, *, support_epsilon: float) -> dict[str, Any]:
    if coefficients is None:
        return {
            "present": False,
            "shape": None,
            "finite": None,
            "l2_norm": None,
            "linf_norm": None,
            "nonzero_count": None,
        }
    try:
        array = np.asarray(coefficients, dtype=float)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError("coefficients must be a finite numeric array or None.") from exc
    if array.ndim != 2:
        raise SchemaValidationError("coefficients must be a 2D numeric array when supplied.")
    if not np.all(np.isfinite(array)):
        raise SchemaValidationError("coefficients must contain only finite values.")
    return {
        "present": True,
        "shape": [int(dim) for dim in array.shape],
        "finite": True,
        "l2_norm": float(np.linalg.norm(array)),
        "linf_norm": float(np.max(np.abs(array))) if array.size else 0.0,
        "nonzero_count": int(np.count_nonzero(np.abs(array) > support_epsilon)),
    }


def _residual_summary_or_none(value: object, *, name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    try:
        array = np.asarray(value, dtype=float).reshape(-1)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{name} must be a finite numeric scalar or array-like.") from exc
    if array.size == 0:
        raise SchemaValidationError(f"{name} must be non-empty after flattening.")
    if not np.all(np.isfinite(array)):
        raise SchemaValidationError(f"{name} must contain only finite values.")
    return {
        "size": int(array.size),
        "l2_norm": float(np.linalg.norm(array)),
        "rms": float(np.sqrt(np.mean(array**2))),
        "max_abs": float(np.max(np.abs(array))),
    }


def _recovery_summary(
    target_terms: object,
    discovered_terms: Mapping[str, Mapping[str, float]],
    *,
    feature_names: Sequence[str],
    support_epsilon: float,
    train_residual: object | None,
    heldout_residual: object | None,
) -> dict[str, Any]:
    normalized_targets = _validate_feature_term_mapping(
        target_terms,
        name="target_terms",
        feature_names=feature_names,
    )
    by_feature: dict[str, dict[str, object]] = {}
    counts = {"exact": 0, "partial": 0, "failed": 0}
    for feature_name in feature_names:
        recovery = evaluate_discovery_recovery(
            normalized_targets[feature_name],
            discovered_terms[feature_name],
            support_epsilon=support_epsilon,
            train_residual=train_residual,
            heldout_residual=heldout_residual,
        )
        classification = str(recovery["classification"])
        counts[classification] = counts.get(classification, 0) + 1
        by_feature[feature_name] = recovery

    total = len(feature_names)
    return {
        "support_epsilon": support_epsilon,
        "by_feature": by_feature,
        "aggregate": {
            "feature_count": total,
            "exact_count": counts["exact"],
            "partial_count": counts["partial"],
            "failed_count": counts["failed"],
            "exact_rate": float(counts["exact"] / total) if total else 0.0,
            "partial_rate": float(counts["partial"] / total) if total else 0.0,
            "failed_rate": float(counts["failed"] / total) if total else 0.0,
        },
    }


def summarize_discovery_bridge_output(
    trajectories: object,
    time_values: object,
    feature_names: object,
    *,
    source_field_id: object | None = None,
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize downstream discovery bridge arrays without returning transformed fields."""

    normalized_trajectories = _validate_trajectories(trajectories)
    num_times, num_features = normalized_trajectories[0].shape
    normalized_time = _validate_time_values(time_values, num_times=num_times)
    normalized_features = _validate_feature_names(feature_names, num_features=num_features)
    normalized_provenance = (
        None
        if provenance is None
        else _validate_json_compatible(_require_mapping(provenance, name="provenance"), name="provenance")
    )
    normalized_source_field_id = (
        None
        if source_field_id is None
        else _validate_json_compatible(source_field_id, name="source_field_id")
    )

    return _summary_payload(
        "discovery_bridge_output",
        source_field_id=normalized_source_field_id,
        provenance=normalized_provenance,
        trajectory_count=len(normalized_trajectories),
        trajectory_shape=[int(dim) for dim in normalized_trajectories[0].shape],
        trajectory_shapes=[[int(dim) for dim in trajectory.shape] for trajectory in normalized_trajectories],
        num_times=int(num_times),
        num_state_features=int(num_features),
        feature_names=normalized_features,
        time_start=float(normalized_time[0]),
        time_end=float(normalized_time[-1]),
        time_span=float(normalized_time[-1] - normalized_time[0]),
        strictly_increasing_time=True,
        finite=True,
        returns_field_batch=False,
    )


def summarize_discovery_result(
    result: Mapping[str, Any],
    *,
    target_terms: Mapping[str, Mapping[str, float]] | None = None,
    support_epsilon: float = 1e-8,
    train_residual: object | None = None,
    heldout_residual: object | None = None,
    source_result_id: object | None = None,
) -> dict[str, Any]:
    """Normalize backend-native discovery results into a compact JSON-compatible report."""

    result_mapping = _require_mapping(result, name="result")
    epsilon = _support_epsilon(support_epsilon)
    status = result_mapping.get("status")
    if status not in _RESULT_STATUSES:
        raise SchemaValidationError(f"result.status must be one of {sorted(_RESULT_STATUSES)}.")
    backend = result_mapping.get("backend")
    if not isinstance(backend, str) or not backend:
        raise SchemaValidationError("result.backend must be a non-empty string.")

    feature_name_input = result_mapping.get("feature_names")
    feature_names = _validate_feature_names(
        feature_name_input,
        num_features=len(feature_name_input) if isinstance(feature_name_input, Sequence) and not isinstance(feature_name_input, (str, bytes)) else -1,
    )
    raw_equation_terms = result_mapping.get("equation_terms", {})
    raw_equation_strings = result_mapping.get("equation_strings", {})
    if status == "failed" and raw_equation_terms == {}:
        equation_terms = {feature_name: {} for feature_name in feature_names}
    else:
        equation_terms = _validate_feature_term_mapping(
            raw_equation_terms,
            name="result.equation_terms",
            feature_names=feature_names,
        )
    if status == "failed" and raw_equation_strings == {}:
        equation_strings = {feature_name: "" for feature_name in feature_names}
    else:
        equation_strings = _validate_string_mapping(
            raw_equation_strings,
            name="result.equation_strings",
            feature_names=feature_names,
        )
    library_feature_names = result_mapping.get("library_feature_names", [])
    if isinstance(library_feature_names, (str, bytes)) or not isinstance(library_feature_names, Sequence):
        raise SchemaValidationError("result.library_feature_names must be a sequence when supplied.")
    normalized_library_feature_names = [
        str(name) for name in library_feature_names if isinstance(name, str) and name
    ]
    if len(normalized_library_feature_names) != len(list(library_feature_names)):
        raise SchemaValidationError("result.library_feature_names must contain only non-empty strings.")

    coefficient_summary = _coefficient_summary(
        result_mapping.get("coefficients"),
        support_epsilon=epsilon,
    )
    fit_diagnostics = _validate_json_compatible(
        _require_mapping(result_mapping.get("fit_diagnostics", {}), name="result.fit_diagnostics"),
        name="result.fit_diagnostics",
    )
    fit_config = _validate_json_compatible(
        result_mapping.get("fit_config", {}),
        name="result.fit_config",
    )
    normalized_source_result_id = (
        None
        if source_result_id is None
        else _validate_json_compatible(source_result_id, name="source_result_id")
    )
    failure_reason = result_mapping.get("failure_reason")
    if failure_reason is not None and (not isinstance(failure_reason, str) or not failure_reason):
        raise SchemaValidationError("result.failure_reason must be a non-empty string when supplied.")

    recovery = None
    if target_terms is not None:
        recovery = _recovery_summary(
            target_terms,
            equation_terms,
            feature_names=feature_names,
            support_epsilon=epsilon,
            train_residual=train_residual,
            heldout_residual=heldout_residual,
        )

    return _summary_payload(
        "discovery_result",
        source_result_id=normalized_source_result_id,
        status=status,
        backend=backend,
        feature_names=feature_names,
        library_feature_names=normalized_library_feature_names,
        equation_terms=equation_terms,
        equation_strings=equation_strings,
        coefficient_summary=coefficient_summary,
        support_epsilon=epsilon,
        fit_diagnostics=fit_diagnostics,
        fit_config=fit_config,
        failure_reason=failure_reason,
        residuals={
            "train": _residual_summary_or_none(train_residual, name="train_residual"),
            "heldout": _residual_summary_or_none(heldout_residual, name="heldout_residual"),
        },
        recovery=recovery,
        returns_coefficients=False,
    )
