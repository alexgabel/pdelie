from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import numpy as np

from pdelie.contracts import DerivativeBatch, GeneratorFamily, ResidualBatch, VerificationReport
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.symmetry.parameterization import translation_span_distance


_SUMMARY_SCHEMA_VERSION = "0.1"
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


def _require_finite(array: np.ndarray, *, name: str) -> np.ndarray:
    normalized = np.asarray(array, dtype=float)
    if not np.all(np.isfinite(normalized)):
        raise ScopeValidationError(f"{name} must contain finite values.")
    return normalized


def _require_mapping(value: object, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{name} must be a mapping.")
    return value


def _summary_payload(summary_type: str, **items: Any) -> dict[str, Any]:
    payload = {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": summary_type,
        **items,
    }
    return _validate_json_compatible(payload, name=f"{summary_type} summary")


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
