from __future__ import annotations

from collections.abc import Callable, Mapping

import numpy as np

from pdelie import FieldBatch, GeneratorFamily, SchemaValidationError, ScopeValidationError
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.symmetry.fitting.translation_baseline import _select_translation_coefficients
from pdelie.symmetry.parameterization.polynomial_translation import (
    DEFAULT_TRANSLATION_SPAN_TOLERANCE,
    POLYNOMIAL_TRANSLATION_BASIS,
    _coerce_translation_coefficients,
    apply_pointwise_translation,
    build_translation_basis,
    evaluate_translation_xi,
    normalize_translation_coefficients,
    translation_reference_coefficients,
    translation_span_distance,
)
from pdelie.verification import DEFAULT_EPSILON_VALUES
from pdelie.verification.finite_transform import _apply_uniform_translation

ReportEvaluator = Callable[[FieldBatch], dict[str, object]]

_EXPECTED_METHOD_FAMILY = "local_separable_quartic_bump_trapezoid_v1"
_WEAK_REPORT_CONTRACT_FALLBACK_TOLERANCE = DEFAULT_TRANSLATION_SPAN_TOLERANCE
_EXPECTED_REPORT_KEYS = frozenset(
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


def _select_weak_report_translation_coefficients(
    svd_coefficients: np.ndarray,
    basis_delta_norms: dict[str, float],
) -> tuple[np.ndarray, str, bool, str | None, str, float]:
    coefficients, fit_mode, reference_fallback_used, fallback_reason, min_delta_basis = _select_translation_coefficients(
        svd_coefficients,
        basis_delta_norms,
    )
    selected_span_distance = float(translation_span_distance(coefficients))
    if selected_span_distance > _WEAK_REPORT_CONTRACT_FALLBACK_TOLERANCE:
        coefficients = translation_reference_coefficients()
        fit_mode = "reference_fallback"
        reference_fallback_used = True
        fallback_reason = "weak_report_contract_span_drift"
        selected_span_distance = 0.0
    return coefficients, fit_mode, reference_fallback_used, fallback_reason, min_delta_basis, selected_span_distance


def _validate_positive_finite_scalar(value: object, *, name: str, function_name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise SchemaValidationError(f"{function_name} requires {name} to be a finite positive scalar.")
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{function_name} requires {name} to be a finite positive scalar.") from exc
    if not np.isfinite(normalized) or normalized <= 0.0:
        raise SchemaValidationError(f"{function_name} requires {name} to be a finite positive scalar.")
    return normalized


def _validate_epsilon_values(epsilon_values: object, *, function_name: str) -> np.ndarray:
    try:
        values = np.asarray(epsilon_values, dtype=float)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{function_name} requires epsilon_values to be finite numeric array-like.") from exc
    if values.ndim != 1 or values.size == 0:
        raise SchemaValidationError(f"{function_name} requires epsilon_values to be a non-empty one-dimensional array.")
    if not np.all(np.isfinite(values)) or np.any(values <= 0.0):
        raise SchemaValidationError(f"{function_name} requires epsilon_values to contain only positive finite values.")
    return values


def _evaluate_report(
    field: FieldBatch,
    report_evaluator: ReportEvaluator,
    *,
    function_name: str,
) -> dict[str, object]:
    report = report_evaluator(field)
    if not isinstance(report, Mapping):
        raise SchemaValidationError(f"{function_name} requires report_evaluator to return a mapping.")

    missing = sorted(_EXPECTED_REPORT_KEYS.difference(report))
    if missing:
        raise SchemaValidationError(
            f"{function_name} requires report_evaluator to return the frozen weak report keys; missing {missing}."
        )

    method_family = report["method_family"]
    if method_family != _EXPECTED_METHOD_FAMILY:
        raise ScopeValidationError(
            f"{function_name} requires method_family {_EXPECTED_METHOD_FAMILY!r}, got {method_family!r}."
        )
    if report["normalization"] != "none":
        raise ScopeValidationError(f"{function_name} requires weak reports with normalization='none'.")
    if not isinstance(report["diagnostics"], Mapping):
        raise SchemaValidationError(f"{function_name} requires weak report diagnostics to be a mapping.")

    window_residuals = np.asarray(report["window_residuals"], dtype=float)
    time_window_centers = np.asarray(report["time_window_centers"], dtype=float)
    x_window_centers = np.asarray(report["x_window_centers"], dtype=float)

    if window_residuals.ndim != 4:
        raise SchemaValidationError(f"{function_name} requires window_residuals to be rank 4.")
    if time_window_centers.ndim != 1 or x_window_centers.ndim != 1:
        raise SchemaValidationError(f"{function_name} requires one-dimensional window center coordinates.")
    if window_residuals.shape[1] != time_window_centers.size:
        raise SchemaValidationError(
            f"{function_name} requires time_window_centers length to match the time-window residual axis."
        )
    if window_residuals.shape[2] != x_window_centers.size:
        raise SchemaValidationError(
            f"{function_name} requires x_window_centers length to match the x-window residual axis."
        )
    if window_residuals.shape[3] != 1:
        raise SchemaValidationError(f"{function_name} requires a singleton weak-report var axis.")
    if not np.all(np.isfinite(window_residuals)):
        raise SchemaValidationError(f"{function_name} requires finite window_residuals.")

    return {
        "equation": str(report["equation"]),
        "equation_form": str(report["equation_form"]),
        "method_family": str(method_family),
        "window_residuals": window_residuals,
        "report_shape": tuple(int(dim) for dim in window_residuals.shape),
        "time_window_centers": time_window_centers,
        "x_window_centers": x_window_centers,
    }


def _assert_matching_report_layout(
    reference: dict[str, object],
    candidate: dict[str, object],
    *,
    function_name: str,
) -> None:
    if candidate["method_family"] != reference["method_family"]:
        raise ScopeValidationError(f"{function_name} requires transformed reports to preserve method_family.")
    if candidate["equation"] != reference["equation"]:
        raise ScopeValidationError(f"{function_name} requires transformed reports to preserve equation.")
    if candidate["equation_form"] != reference["equation_form"]:
        raise ScopeValidationError(f"{function_name} requires transformed reports to preserve equation_form.")
    if candidate["report_shape"] != reference["report_shape"]:
        raise ScopeValidationError(f"{function_name} requires transformed reports to preserve report shape.")

    np.testing.assert_allclose(
        np.asarray(candidate["time_window_centers"], dtype=float),
        np.asarray(reference["time_window_centers"], dtype=float),
        rtol=0.0,
        atol=1e-12,
        err_msg=f"{function_name} requires transformed reports to preserve time-window centers.",
    )
    np.testing.assert_allclose(
        np.asarray(candidate["x_window_centers"], dtype=float),
        np.asarray(reference["x_window_centers"], dtype=float),
        rtol=0.0,
        atol=1e-12,
        err_msg=f"{function_name} requires transformed reports to preserve x-window centers.",
    )


def fit_translation_generator_from_weak_reports(
    field: FieldBatch,
    report_evaluator: ReportEvaluator,
    *,
    epsilon: float = 1e-4,
) -> dict[str, object]:
    field.validate()
    normalized_epsilon = _validate_positive_finite_scalar(
        epsilon,
        name="epsilon",
        function_name="fit_translation_generator_from_weak_reports",
    )
    baseline_report = _evaluate_report(
        field,
        report_evaluator,
        function_name="fit_translation_generator_from_weak_reports",
    )
    basis = build_translation_basis(field)

    columns: list[np.ndarray] = []
    basis_delta_norms: dict[str, float] = {}
    for basis_name in POLYNOMIAL_TRANSLATION_BASIS:
        transformed = apply_pointwise_translation(field, basis[basis_name], normalized_epsilon)
        transformed_report = _evaluate_report(
            transformed,
            report_evaluator,
            function_name="fit_translation_generator_from_weak_reports",
        )
        _assert_matching_report_layout(
            baseline_report,
            transformed_report,
            function_name="fit_translation_generator_from_weak_reports",
        )
        delta = (
            np.asarray(transformed_report["window_residuals"], dtype=float)
            - np.asarray(baseline_report["window_residuals"], dtype=float)
        ) / normalized_epsilon
        flattened = delta.reshape(-1)
        columns.append(flattened)
        basis_delta_norms[basis_name] = float(np.linalg.norm(flattened))

    design = np.column_stack(columns)
    _, singular_values, vh = np.linalg.svd(design, full_matrices=False)
    smallest_singular_value = float(singular_values[-1])
    condition_number = (
        float(singular_values[0] / smallest_singular_value) if smallest_singular_value > 0.0 else float("inf")
    )
    rank_estimate = int(np.linalg.matrix_rank(design))
    svd_coefficients = normalize_translation_coefficients(vh[-1])
    (
        coefficients,
        fit_mode,
        reference_fallback_used,
        fallback_reason,
        min_delta_basis,
        selected_span_distance,
    ) = _select_weak_report_translation_coefficients(
        svd_coefficients,
        basis_delta_norms,
    )

    generator = GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=coefficients.reshape(1, -1),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={
            "basis": list(POLYNOMIAL_TRANSLATION_BASIS),
            "basis_delta_norms": basis_delta_norms,
            "fallback_reason": fallback_reason,
            "fit_mode": fit_mode,
            "fit_residual": smallest_singular_value,
            "method_family": str(baseline_report["method_family"]),
            "min_delta_basis": min_delta_basis,
            "reference_fallback_used": reference_fallback_used,
            "reference_fallback_tolerance": _WEAK_REPORT_CONTRACT_FALLBACK_TOLERANCE,
            "report_shape": list(baseline_report["report_shape"]),
            "selected_span_distance": selected_span_distance,
            "singular_values": singular_values.tolist(),
            "smallest_singular_value": smallest_singular_value,
            "condition_number": condition_number,
            "rank_estimate": rank_estimate,
            "svd_coefficients": svd_coefficients.tolist(),
            "svd_span_distance": float(translation_span_distance(svd_coefficients)),
            "training_epsilon": normalized_epsilon,
            "transform_implementation": "apply_pointwise_translation",
        },
    )

    return {
        "generator": generator,
        "fit_mode": fit_mode,
        "reference_fallback_used": reference_fallback_used,
        "fallback_reason": fallback_reason,
        "min_delta_basis": min_delta_basis,
        "svd_span_distance": float(translation_span_distance(svd_coefficients)),
        "selected_span_distance": selected_span_distance,
        "basis_delta_norms": basis_delta_norms,
        "singular_values": singular_values,
        "smallest_singular_value": smallest_singular_value,
        "condition_number": condition_number,
        "rank_estimate": rank_estimate,
        "training_epsilon": normalized_epsilon,
        "reference_fallback_tolerance": _WEAK_REPORT_CONTRACT_FALLBACK_TOLERANCE,
        "report_shape": tuple(int(dim) for dim in baseline_report["report_shape"]),
        "time_window_centers": np.asarray(baseline_report["time_window_centers"], dtype=float).copy(),
        "x_window_centers": np.asarray(baseline_report["x_window_centers"], dtype=float).copy(),
        "method_family": str(baseline_report["method_family"]),
    }


def verify_translation_generator_from_weak_reports(
    field: FieldBatch,
    generator: GeneratorFamily,
    report_evaluator: ReportEvaluator,
    *,
    epsilon_values: np.ndarray | None = None,
    min_heldout_initial_conditions: int = 3,
    span_tolerance: float = DEFAULT_TRANSLATION_SPAN_TOLERANCE,
) -> dict[str, object]:
    field.validate()
    generator.validate()

    if field.values.shape[0] < min_heldout_initial_conditions:
        raise ScopeValidationError(
            f"Held-out verification requires at least {min_heldout_initial_conditions} unseen initial conditions."
        )

    normalized_span_tolerance = _validate_positive_finite_scalar(
        span_tolerance,
        name="span_tolerance",
        function_name="verify_translation_generator_from_weak_reports",
    )
    epsilon_array = (
        DEFAULT_EPSILON_VALUES
        if epsilon_values is None
        else _validate_epsilon_values(
            epsilon_values,
            function_name="verify_translation_generator_from_weak_reports",
        )
    )
    translation_coefficients = _coerce_translation_coefficients(generator.coefficients)
    span_distance = translation_span_distance(translation_coefficients)
    baseline_report = _evaluate_report(
        field,
        report_evaluator,
        function_name="verify_translation_generator_from_weak_reports",
    )
    xi = evaluate_translation_xi(field, translation_coefficients)
    use_uniform_translation = span_distance <= normalized_span_tolerance

    relative_to_field_norm_batch_errors: list[list[float]] = []
    relative_to_baseline_report_norm_batch_errors: list[list[float]] = []
    baseline_values = np.asarray(field.values, dtype=float)
    baseline_window_residuals = np.asarray(baseline_report["window_residuals"], dtype=float)
    for epsilon in epsilon_array:
        if use_uniform_translation:
            transformed = _apply_uniform_translation(field, float(epsilon * translation_coefficients[0]))
        else:
            transformed = apply_pointwise_translation(field, xi, float(epsilon))

        transformed_report = _evaluate_report(
            transformed,
            report_evaluator,
            function_name="verify_translation_generator_from_weak_reports",
        )
        _assert_matching_report_layout(
            baseline_report,
            transformed_report,
            function_name="verify_translation_generator_from_weak_reports",
        )
        diff = (
            np.asarray(transformed_report["window_residuals"], dtype=float)
            - np.asarray(baseline_report["window_residuals"], dtype=float)
        )
        epsilon_field_norm_errors = [
            float(np.linalg.norm(diff[batch_index]) / (np.linalg.norm(baseline_values[batch_index]) + 1e-12))
            for batch_index in range(field.values.shape[0])
        ]
        epsilon_baseline_report_norm_errors = [
            float(np.linalg.norm(diff[batch_index]) / (np.linalg.norm(baseline_window_residuals[batch_index]) + 1e-12))
            for batch_index in range(field.values.shape[0])
        ]
        relative_to_field_norm_batch_errors.append(epsilon_field_norm_errors)
        relative_to_baseline_report_norm_batch_errors.append(epsilon_baseline_report_norm_errors)

    relative_to_field_norm_error_curve = np.median(np.asarray(relative_to_field_norm_batch_errors, dtype=float), axis=1)
    relative_to_baseline_report_norm_error_curve = np.median(
        np.asarray(relative_to_baseline_report_norm_batch_errors, dtype=float),
        axis=1,
    )
    return {
        "relative_to_field_norm_error_curve": relative_to_field_norm_error_curve,
        "relative_to_field_norm_batch_errors": relative_to_field_norm_batch_errors,
        "relative_to_baseline_report_norm_error_curve": relative_to_baseline_report_norm_error_curve,
        "relative_to_baseline_report_norm_batch_errors": relative_to_baseline_report_norm_batch_errors,
        "span_distance": float(span_distance),
        "span_tolerance": normalized_span_tolerance,
        "transform_mode": "uniform_translation" if use_uniform_translation else "pointwise_translation",
        "heldout_initial_conditions": int(field.values.shape[0]),
        "report_shape": tuple(int(dim) for dim in baseline_report["report_shape"]),
        "time_window_centers": np.asarray(baseline_report["time_window_centers"], dtype=float).copy(),
        "x_window_centers": np.asarray(baseline_report["x_window_centers"], dtype=float).copy(),
        "method_family": str(baseline_report["method_family"]),
    }


__all__ = [
    "fit_translation_generator_from_weak_reports",
    "verify_translation_generator_from_weak_reports",
]
