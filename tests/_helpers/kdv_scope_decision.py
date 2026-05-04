from __future__ import annotations

import numpy as np

from pdelie.data import generate_kdv_1d_field_batch
from pdelie.data.heat_1d import DEFAULT_DOMAIN_LENGTH
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.residuals import KdVResidualEvaluator
from tests._helpers.kdv_feasibility import _rollout_kdv_periodic, _spectral_spatial_derivatives
from tests._helpers.weak_reaction_diffusion_feasibility import _simpson_weights


def _residual_metrics(case_name: str, *, category: str, **kwargs: object) -> dict[str, object]:
    field = generate_kdv_1d_field_batch(**kwargs)
    derivatives = compute_spectral_fd_derivatives(field, max_spatial_order=3)
    residual = KdVResidualEvaluator().evaluate(field, derivatives)
    return {
        "case_name": case_name,
        "evidence_category": category,
        "field_shape": list(field.values.shape),
        "finite": bool(np.all(np.isfinite(field.values))),
        "max_abs_residual": float(residual.diagnostics["max_abs_residual"]),
        "rms_residual": float(residual.diagnostics["rms_residual"]),
        "equation": field.metadata["parameter_tags"]["equation"],
    }


def _configurable_coefficient_feasibility() -> dict[str, object]:
    x = np.linspace(0.0, DEFAULT_DOMAIN_LENGTH, 64, endpoint=False, dtype=float)
    dx = float(x[1] - x[0])
    u = 0.07 * np.sin(x)[None, :]
    u_x, _, u_xxx = _spectral_spatial_derivatives(u, dx=dx)

    alpha = 6.0
    beta = 1.0
    alpha_delta = 0.5
    beta_delta = -0.25
    base = alpha * u * u_x + beta * u_xxx
    alpha_changed = (alpha + alpha_delta) * u * u_x + beta * u_xxx
    beta_changed = alpha * u * u_x + (beta + beta_delta) * u_xxx

    alpha_error = float(np.max(np.abs((alpha_changed - base) - alpha_delta * u * u_x)))
    beta_error = float(np.max(np.abs((beta_changed - base) - beta_delta * u_xxx)))
    tolerance = 1e-12
    return {
        "summary_schema_version": "0.1",
        "summary_type": "kdv_configurable_coefficient_feasibility",
        "visibility": "internal_diagnostic_only",
        "evidence_category": "diagnostic_only",
        "equation_form": "u_t + alpha*u*u_x + beta*u_xxx = 0",
        "alpha_scaling_abs_error": alpha_error,
        "beta_scaling_abs_error": beta_error,
        "tolerance": tolerance,
        "passed": bool(alpha_error <= tolerance and beta_error <= tolerance),
        "public_api": {"configurable_kdv_residual_evaluator": False},
    }


def _custom_initial_condition_feasibility() -> dict[str, object]:
    x = np.linspace(0.0, DEFAULT_DOMAIN_LENGTH, 64, endpoint=False, dtype=float)
    output_times = np.linspace(0.0, 0.03, 17, dtype=float)
    initial = (0.04 * np.cos(x) + 0.02 * np.sin(2.0 * x))[None, :]

    first = _rollout_kdv_periodic(
        initial,
        output_times=output_times,
        domain_length=DEFAULT_DOMAIN_LENGTH,
        num_substeps=8,
    )
    second = _rollout_kdv_periodic(
        initial,
        output_times=output_times,
        domain_length=DEFAULT_DOMAIN_LENGTH,
        num_substeps=8,
    )
    return {
        "summary_schema_version": "0.1",
        "summary_type": "kdv_custom_initial_condition_feasibility",
        "visibility": "internal_diagnostic_only",
        "evidence_category": "diagnostic_only",
        "field_shape": list(first.shape),
        "finite": bool(np.all(np.isfinite(first))),
        "deterministic": bool(np.allclose(first, second, rtol=0.0, atol=0.0)),
        "public_api": {"custom_initial_condition_generator": False},
    }


def _sixth_order_bump(axis: np.ndarray) -> np.ndarray:
    return np.power(1.0 - np.square(axis), 3)


def _sixth_order_bump_prime(axis: np.ndarray) -> np.ndarray:
    return -6.0 * axis + 12.0 * np.power(axis, 3) - 6.0 * np.power(axis, 5)


def _sixth_order_bump_second(axis: np.ndarray) -> np.ndarray:
    return -6.0 + 36.0 * np.square(axis) - 30.0 * np.power(axis, 4)


def _sixth_order_bump_third(axis: np.ndarray) -> np.ndarray:
    return 72.0 * axis - 120.0 * np.power(axis, 3)


def run_internal_weak_kdv_identity_checks(*, size: int = 513) -> dict[str, object]:
    axis = np.linspace(-1.0, 1.0, size, dtype=float)
    spacing = float(axis[1] - axis[0])
    weights = _simpson_weights(size, spacing=spacing)
    phi = _sixth_order_bump(axis)
    phi_prime = _sixth_order_bump_prime(axis)
    phi_second = _sixth_order_bump_second(axis)
    phi_third = _sixth_order_bump_third(axis)

    u = np.sin(np.pi * axis)
    u_third = -(np.pi**3) * np.cos(np.pi * axis)
    ibp_left = float(np.sum(u_third * phi * weights))
    ibp_right = float(-np.sum(u * phi_third * weights))
    ibp_error = abs(ibp_left - ibp_right)
    boundary_abs = {
        "phi": float(np.max(np.abs(phi[[0, -1]]))),
        "phi_prime": float(np.max(np.abs(phi_prime[[0, -1]]))),
        "phi_second": float(np.max(np.abs(phi_second[[0, -1]]))),
    }
    tolerance = 1e-8
    return {
        "summary_schema_version": "0.1",
        "summary_type": "weak_kdv_identity_feasibility",
        "visibility": "internal_diagnostic_only",
        "evidence_category": "diagnostic_only",
        "test_function_family": "sixth_order_boundary_regular_bump",
        "quadrature_rule": "composite_simpson_1d_v1",
        "boundary_abs": boundary_abs,
        "third_order_integration_by_parts_abs_error": float(ibp_error),
        "tolerance": tolerance,
        "passed": bool(max(boundary_abs.values()) <= tolerance and ibp_error <= tolerance),
        "public_api": {"weak_kdv_residual": False, "weak_derivative_backend": False},
    }


def run_internal_kdv_scope_matrix() -> dict[str, object]:
    cases = [
        _residual_metrics(
            "frozen_default",
            category="current_frozen_supported",
            batch_size=2,
            num_times=17,
            num_points=64,
            max_time=0.03,
            num_modes=3,
            amplitude=0.08,
            seed=25100,
            num_substeps=8,
        ),
        _residual_metrics(
            "longer_horizon",
            category="diagnostic_only",
            batch_size=2,
            num_times=17,
            num_points=64,
            max_time=0.06,
            num_modes=3,
            amplitude=0.08,
            seed=25101,
            num_substeps=16,
        ),
        _residual_metrics(
            "larger_amplitude",
            category="diagnostic_only",
            batch_size=2,
            num_times=17,
            num_points=64,
            max_time=0.03,
            num_modes=3,
            amplitude=0.12,
            seed=25102,
            num_substeps=12,
        ),
        _residual_metrics(
            "more_modes",
            category="diagnostic_only",
            batch_size=2,
            num_times=17,
            num_points=64,
            max_time=0.03,
            num_modes=5,
            amplitude=0.06,
            seed=25103,
            num_substeps=12,
        ),
    ]
    return {
        "summary_schema_version": "0.1",
        "summary_type": "kdv_scope_decision_matrix",
        "visibility": "internal_diagnostic_only",
        "cases": cases,
        "custom_initial_condition_feasibility": _custom_initial_condition_feasibility(),
        "configurable_coefficient_feasibility": _configurable_coefficient_feasibility(),
        "weak_kdv_identity_feasibility": run_internal_weak_kdv_identity_checks(),
        "conclusion": "keep_public_kdv_surface_frozen",
    }
