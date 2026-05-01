from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from pdelie.contracts import DerivativeBatch, GeneratorFamily, ResidualBatch, VerificationReport
from pdelie.errors import PDELieValidationError, SchemaValidationError, ScopeValidationError
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

_INVARIANT_REPORT_SUMMARY_TYPES = frozenset(
    {
        "periodic_window_coverage",
        "uniform_translation_consistency",
        "uniform_translation_orbit",
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
