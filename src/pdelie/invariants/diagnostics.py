from __future__ import annotations

from copy import deepcopy
import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from pdelie.contracts import (
    FieldBatch,
    GeneratorFamily,
    InvariantMapSpec,
    _translation_generator_basis_spec,
)
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.invariants.apply import InvariantApplier
from pdelie.residuals import ResidualEvaluator


_SUMMARY_SCHEMA_VERSION = "0.1"
_RELATIVE_L2_EPS = 1e-12
_RESIDUAL_ABSOLUTE_TOLERANCE = 1e-8
_RESIDUAL_RELATIVE_TOLERANCE = 1e-6


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _validate_json_compatible(payload: dict[str, Any], *, name: str) -> dict[str, Any]:
    safe_payload = _json_safe(payload)
    try:
        json.dumps(safe_payload)
    except TypeError as exc:
        raise SchemaValidationError(f"{name} must be JSON-compatible after diagnostic conversion.") from exc
    return safe_payload


def _finite_float(value: Any, *, name: str) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{name} must be a finite float.") from exc
    if not np.isfinite(normalized):
        raise SchemaValidationError(f"{name} must be finite.")
    return normalized


def _finite_sequence(value: Any, *, name: str) -> list[float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise SchemaValidationError(f"{name} must be a non-empty sequence of finite floats.")
    normalized = [_finite_float(item, name=f"{name}[{index}]") for index, item in enumerate(value)]
    if not normalized:
        raise SchemaValidationError(f"{name} must be non-empty.")
    return normalized


def _normalize_periodic_grid(
    x: Any,
    *,
    domain_length: float | None,
) -> tuple[np.ndarray, float, float, float]:
    coordinates = np.asarray(x, dtype=float)
    if coordinates.ndim != 1 or coordinates.size < 2:
        raise SchemaValidationError("x must be a one-dimensional coordinate array with at least two points.")
    if not np.all(np.isfinite(coordinates)):
        raise SchemaValidationError("x must contain only finite values.")

    diffs = np.diff(coordinates)
    if not np.all(diffs > 0.0):
        raise ScopeValidationError("x must be strictly increasing for the endpoint-excluded periodic grid.")
    dx = float(diffs[0])
    uniform_atol = max(1e-12 * max(abs(float(coordinates[-1] - coordinates[0])), 1.0), 1e-14)
    if not np.allclose(diffs, dx, rtol=0.0, atol=uniform_atol):
        raise ScopeValidationError("x must be uniformly spaced.")

    inferred_domain_length = float(coordinates.size * dx)
    if domain_length is None:
        resolved_domain_length = inferred_domain_length
    else:
        resolved_domain_length = _finite_float(domain_length, name="domain_length")
        if resolved_domain_length <= 0.0:
            raise SchemaValidationError("domain_length must be positive.")
        boundary_tolerance = 1e-12 * resolved_domain_length
        if np.isclose(coordinates[-1] - coordinates[0], resolved_domain_length, rtol=0.0, atol=boundary_tolerance):
            raise ScopeValidationError("endpoint-duplicated periodic grids are not supported.")
        if not np.isclose(inferred_domain_length, resolved_domain_length, rtol=0.0, atol=boundary_tolerance):
            raise ScopeValidationError("domain_length must equal len(x) * dx for endpoint-excluded periodic grids.")

    boundary_tolerance = 1e-12 * resolved_domain_length
    return coordinates, dx, resolved_domain_length, boundary_tolerance


def _normalize_windows(windows: Any, *, domain_length: float, boundary_tolerance: float) -> tuple[list[dict[str, float]], list[dict[str, float]]]:
    if isinstance(windows, (str, bytes)) or not isinstance(windows, Sequence):
        raise SchemaValidationError("windows must be a non-empty sequence of mappings.")
    raw_windows: list[dict[str, float]] = []
    normalized_windows: list[dict[str, float]] = []
    for index, window in enumerate(windows):
        if not isinstance(window, Mapping):
            raise SchemaValidationError(f"windows[{index}] must be a mapping with start and width.")
        if "start" not in window or "width" not in window:
            raise SchemaValidationError(f"windows[{index}] must include start and width.")
        start = _finite_float(window["start"], name=f"windows[{index}].start")
        width = _finite_float(window["width"], name=f"windows[{index}].width")
        if width <= 0.0:
            raise SchemaValidationError(f"windows[{index}].width must be positive.")
        if width > domain_length + boundary_tolerance:
            raise ScopeValidationError(f"windows[{index}].width must not exceed domain_length.")
        normalized_width = domain_length if np.isclose(width, domain_length, rtol=0.0, atol=boundary_tolerance) else width
        raw_windows.append({"start": start, "width": width})
        normalized_windows.append({"start": float(start % domain_length), "width": float(normalized_width)})
    if not raw_windows:
        raise SchemaValidationError("windows must be non-empty.")
    return raw_windows, normalized_windows


def _window_contains(
    transformed_x: np.ndarray,
    *,
    start: float,
    width: float,
    domain_length: float,
    boundary_tolerance: float,
) -> np.ndarray:
    if np.isclose(width, domain_length, rtol=0.0, atol=boundary_tolerance):
        return np.ones_like(transformed_x, dtype=bool)
    normalized = (np.asarray(transformed_x, dtype=float) - start) % domain_length
    normalized = np.where(normalized >= domain_length - boundary_tolerance, 0.0, normalized)
    return (normalized <= boundary_tolerance) | (normalized < max(width - boundary_tolerance, 0.0))


def _zero_run_lengths(counts: np.ndarray) -> list[int]:
    uncovered = np.asarray(counts) == 0
    if not np.any(uncovered):
        return []
    doubled = np.concatenate([uncovered, uncovered])
    runs: list[int] = []
    current = 0
    for value in doubled:
        if value:
            current += 1
        elif current:
            runs.append(min(current, uncovered.size))
            current = 0
    if current:
        runs.append(min(current, uncovered.size))
    return runs


def compute_periodic_window_coverage(
    *,
    x: Any,
    windows: Any,
    shifts: Any,
    domain_length: float | None = None,
) -> dict[str, Any]:
    coordinates, dx, resolved_domain_length, boundary_tolerance = _normalize_periodic_grid(
        x,
        domain_length=domain_length,
    )
    raw_windows, normalized_windows = _normalize_windows(
        windows,
        domain_length=resolved_domain_length,
        boundary_tolerance=boundary_tolerance,
    )
    raw_shifts = _finite_sequence(shifts, name="shifts")
    normalized_shifts = [float(shift % resolved_domain_length) for shift in raw_shifts]

    coverage_counts = np.zeros(coordinates.size, dtype=int)
    normalized_x = coordinates % resolved_domain_length
    for window in normalized_windows:
        for shift in raw_shifts:
            transformed_x = (normalized_x + float(shift)) % resolved_domain_length
            coverage_counts += _window_contains(
                transformed_x,
                start=window["start"],
                width=window["width"],
                domain_length=resolved_domain_length,
                boundary_tolerance=boundary_tolerance,
            ).astype(int)

    covered = int(np.count_nonzero(coverage_counts))
    zero_runs = _zero_run_lengths(coverage_counts)
    max_uncovered_run_points = int(max(zero_runs, default=0))
    return _validate_json_compatible(
        {
            "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
            "summary_type": "periodic_window_coverage",
            "coverage_type": "grid_point",
            "coverage_convention": "preimage_of_fixed_window_under_translation",
            "shift_convention": "field_shift_then_fixed_window",
            "window_convention": "half_open",
            "boundary_tolerance": boundary_tolerance,
            "domain_length": resolved_domain_length,
            "inferred_domain_length": float(coordinates.size * dx),
            "dx": dx,
            "grid_point_count": int(coordinates.size),
            "raw_windows": raw_windows,
            "normalized_windows": normalized_windows,
            "raw_shifts": raw_shifts,
            "normalized_shifts": normalized_shifts,
            "coverage_counts": coverage_counts,
            "covered_grid_point_count": covered,
            "coverage_fraction": float(covered / coordinates.size),
            "min_coverage_count": int(np.min(coverage_counts)),
            "max_coverage_count": int(np.max(coverage_counts)),
            "mean_coverage_count": float(np.mean(coverage_counts)),
            "max_uncovered_run_points": max_uncovered_run_points,
            "max_uncovered_run_length": float(max_uncovered_run_points * dx),
        },
        name="periodic_window_coverage summary",
    )


def _translation_generator() -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )


_TRANSLATION_GENERATOR_METADATA = _translation_generator().to_dict()


def _translation_spec(shift: float) -> InvariantMapSpec:
    return InvariantMapSpec(
        generator_metadata=deepcopy(_TRANSLATION_GENERATOR_METADATA),
        construction_method="uniform_translation",
        parameters={"axis": "x", "shift": float(shift)},
        domain_validity="global",
        inverse_available=True,
        diagnostics={"source": "uniform_translation_consistency"},
    )


def _relative_l2(left: np.ndarray, right: np.ndarray) -> float:
    left_values = np.asarray(left, dtype=float)
    right_values = np.asarray(right, dtype=float)
    return float(np.linalg.norm(left_values - right_values) / (np.linalg.norm(right_values) + _RELATIVE_L2_EPS))


def _residual_rms(field: FieldBatch, evaluator: ResidualEvaluator) -> float:
    residual = evaluator.evaluate(field).residual
    normalized = np.asarray(residual, dtype=float)
    if not np.all(np.isfinite(normalized)):
        raise ScopeValidationError("residual evaluator produced non-finite residual values.")
    return float(np.sqrt(np.mean(np.square(normalized))))


def _validate_consistency_field(field: FieldBatch) -> tuple[float, float]:
    if not isinstance(field, FieldBatch):
        raise SchemaValidationError("field must be a FieldBatch.")
    field.validate()
    if field.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError("diagnose_uniform_translation_consistency requires dims ('batch', 'time', 'x', 'var').")
    if len(field.var_names) != 1:
        raise ScopeValidationError("diagnose_uniform_translation_consistency requires a scalar field.")
    if field.metadata["boundary_conditions"].get("x") != "periodic":
        raise ScopeValidationError("diagnose_uniform_translation_consistency requires periodic x boundary conditions.")
    _, dx, domain_length, _ = _normalize_periodic_grid(field.coords["x"], domain_length=None)
    return dx, domain_length


def _structure_flags(transformed: FieldBatch, original: FieldBatch) -> dict[str, bool]:
    return {
        "dims_preserved": transformed.dims == original.dims,
        "shape_preserved": transformed.values.shape == original.values.shape,
        "coords_preserved": all(
            np.allclose(transformed.coords[name], original.coords[name], rtol=0.0, atol=1e-12)
            for name in original.coords
        ),
        "metadata_preserved": transformed.metadata == original.metadata,
        "var_names_preserved": transformed.var_names == original.var_names,
        "mask_preserved": (
            transformed.mask is None if original.mask is None else np.array_equal(transformed.mask, original.mask)
        ),
    }


def diagnose_uniform_translation_consistency(
    field: FieldBatch,
    *,
    shifts: Any,
    residual_evaluator: ResidualEvaluator | None = None,
) -> dict[str, Any]:
    dx, domain_length = _validate_consistency_field(field)
    raw_shifts = _finite_sequence(shifts, name="shifts")
    normalized_shifts = [float(shift % domain_length) for shift in raw_shifts]
    if residual_evaluator is not None and not isinstance(residual_evaluator, ResidualEvaluator):
        raise SchemaValidationError("residual_evaluator must be a ResidualEvaluator or None.")

    applier = InvariantApplier()
    before_rms = None if residual_evaluator is None else _residual_rms(field, residual_evaluator)
    shift_reports: list[dict[str, Any]] = []

    for raw_shift, normalized_shift in zip(raw_shifts, normalized_shifts, strict=True):
        transformed = applier.apply(field, _translation_spec(raw_shift))
        inverted = applier.apply(transformed, _translation_spec(-raw_shift))
        period_wrapped = applier.apply(field, _translation_spec(raw_shift + domain_length))
        provenance = transformed.preprocess_log[-1]
        parameters = provenance.get("parameters", {})
        inverse_relative_l2_error = _relative_l2(inverted.values, field.values)
        period_wrap_relative_l2_error = _relative_l2(period_wrapped.values, transformed.values)
        report: dict[str, Any] = {
            "shift": raw_shift,
            "normalized_shift": normalized_shift,
            **_structure_flags(transformed, field),
            "inverse_relative_l2_error": inverse_relative_l2_error,
            "period_wrap_relative_l2_error": period_wrap_relative_l2_error,
            "inverse_passed": inverse_relative_l2_error <= 1e-8,
            "period_wrap_passed": period_wrap_relative_l2_error <= 1e-8,
            "preprocess_log_length_delta": len(transformed.preprocess_log) - len(field.preprocess_log),
            "provenance_operation": provenance.get("operation"),
            "provenance_construction_method": provenance.get("construction_method"),
            "provenance_axis": parameters.get("axis"),
            "provenance_shift": parameters.get("shift"),
        }
        if before_rms is None:
            report.update(
                {
                    "residual_rms_before": None,
                    "residual_rms_after": None,
                    "residual_absolute_rms_delta": None,
                    "residual_relative_rms_delta": None,
                    "residual_stability_passed": None,
                }
            )
        else:
            after_rms = _residual_rms(transformed, residual_evaluator)
            absolute_delta = abs(after_rms - before_rms)
            relative_delta = absolute_delta / (abs(before_rms) + _RELATIVE_L2_EPS)
            report.update(
                {
                    "residual_rms_before": before_rms,
                    "residual_rms_after": after_rms,
                    "residual_absolute_rms_delta": float(absolute_delta),
                    "residual_relative_rms_delta": float(relative_delta),
                    "residual_stability_passed": (
                        absolute_delta <= _RESIDUAL_ABSOLUTE_TOLERANCE
                        or relative_delta <= _RESIDUAL_RELATIVE_TOLERANCE
                    ),
                }
            )
        shift_reports.append(report)

    return _validate_json_compatible(
        {
            "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
            "summary_type": "uniform_translation_consistency",
            "field_dims": field.dims,
            "field_shape": list(field.values.shape),
            "equation": field.metadata["parameter_tags"].get("equation"),
            "domain_length": domain_length,
            "dx": dx,
            "raw_shifts": raw_shifts,
            "normalized_shifts": normalized_shifts,
            "residual_evaluator": None if residual_evaluator is None else type(residual_evaluator).__name__,
            "residual_absolute_tolerance": _RESIDUAL_ABSOLUTE_TOLERANCE,
            "residual_relative_tolerance": _RESIDUAL_RELATIVE_TOLERANCE,
            "shift_reports": shift_reports,
        },
        name="uniform_translation_consistency summary",
    )
