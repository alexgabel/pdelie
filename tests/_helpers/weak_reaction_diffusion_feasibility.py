from __future__ import annotations

import numpy as np

from pdelie.data import generate_reaction_diffusion_1d_field_batch


def _simpson_weights(size: int, *, spacing: float) -> np.ndarray:
    if size < 3 or size % 2 == 0:
        raise ValueError("composite Simpson quadrature requires an odd size >= 3.")
    weights = np.ones(size, dtype=float)
    weights[1:-1:2] = 4.0
    weights[2:-1:2] = 2.0
    return weights * (spacing / 3.0)


def _beta(values: np.ndarray) -> np.ndarray:
    return np.square(1.0 - np.square(values))


def _beta_prime(values: np.ndarray) -> np.ndarray:
    return -4.0 * values * (1.0 - np.square(values))


def _beta_second(values: np.ndarray) -> np.ndarray:
    return -4.0 + 12.0 * np.square(values)


def _integral(values: np.ndarray, weights: np.ndarray) -> float:
    return float(np.sum(values * weights))


def _identity_grid(size: int = 65) -> dict[str, np.ndarray]:
    axis = np.linspace(-1.0, 1.0, size, dtype=float)
    spacing = float(axis[1] - axis[0])
    weights_1d = _simpson_weights(size, spacing=spacing)
    weights = np.outer(weights_1d, weights_1d)

    t = axis[:, None]
    x = axis[None, :]
    beta_t = _beta(axis)[:, None]
    beta_x = _beta(axis)[None, :]
    phi = beta_t * beta_x
    phi_t = _beta_prime(axis)[:, None] * beta_x
    phi_xx = beta_t * _beta_second(axis)[None, :]
    return {
        "t": t,
        "x": x,
        "weights": weights,
        "phi": phi,
        "phi_t": phi_t,
        "phi_xx": phi_xx,
    }


def _fisher_weak_expression(
    u: np.ndarray,
    *,
    phi_t: np.ndarray,
    phi_xx: np.ndarray,
    phi: np.ndarray,
    weights: np.ndarray,
    diffusivity: float,
    reaction_rate: float,
) -> float:
    return (
        -_integral(u * phi_t, weights)
        - diffusivity * _integral(u * phi_xx, weights)
        - reaction_rate * _integral(u * phi, weights)
        + reaction_rate * _integral(np.square(u) * phi, weights)
    )


def run_internal_fisher_kpp_weak_feasibility(
    *,
    diffusivity: float = 0.05,
    reaction_rate: float = 1.0,
    tolerance: float = 5e-6,
) -> dict[str, object]:
    """Return test-only identity-first weak Fisher-KPP feasibility diagnostics."""

    grid = _identity_grid()
    t = grid["t"]
    x = grid["x"]
    weights = grid["weights"]
    phi = grid["phi"]
    phi_t = grid["phi_t"]
    phi_xx = grid["phi_xx"]

    constant = np.ones_like(phi)
    constant_error = abs(
        _fisher_weak_expression(
            constant,
            phi_t=phi_t,
            phi_xx=phi_xx,
            phi=phi,
            weights=weights,
            diffusivity=diffusivity,
            reaction_rate=reaction_rate,
        )
    )

    pure_time = t + np.zeros_like(x)
    pure_time_left = _integral(np.ones_like(phi) * phi, weights)
    pure_time_right = -_integral(pure_time * phi_t, weights)
    pure_time_error = abs(pure_time_left - pure_time_right)

    pure_space = np.sin(np.pi * x) + np.zeros_like(t)
    pure_space_xx = -np.pi * np.pi * pure_space
    ibp_error = abs(_integral(pure_space_xx * phi, weights) - _integral(pure_space * phi_xx, weights))

    manufactured = 0.3 + 0.05 * np.sin(np.pi * x) * np.cos(np.pi * t)
    manufactured_t = -0.05 * np.pi * np.sin(np.pi * x) * np.sin(np.pi * t)
    manufactured_xx = -0.05 * np.pi * np.pi * np.sin(np.pi * x) * np.cos(np.pi * t)
    strong_residual = (
        manufactured_t
        - diffusivity * manufactured_xx
        - reaction_rate * manufactured * (1.0 - manufactured)
    )
    weak_expression = _fisher_weak_expression(
        manufactured,
        phi_t=phi_t,
        phi_xx=phi_xx,
        phi=phi,
        weights=weights,
        diffusivity=diffusivity,
        reaction_rate=reaction_rate,
    )
    manufactured_error = abs(weak_expression - _integral(strong_residual * phi, weights))

    generated = generate_reaction_diffusion_1d_field_batch(
        batch_size=1,
        num_times=17,
        num_points=32,
        diffusivity=diffusivity,
        reaction_rate=reaction_rate,
        seed=24024,
    )
    generated_values = np.asarray(generated.values, dtype=float)
    generated_sanity = {
        "field_shape": list(generated_values.shape),
        "finite": bool(np.all(np.isfinite(generated_values))),
        "equation": generated.metadata["parameter_tags"]["equation"],
    }

    identity_tests = {
        "constant_field": {"abs_error": float(constant_error), "passed": bool(constant_error <= tolerance)},
        "pure_time_sign": {"abs_error": float(pure_time_error), "passed": bool(pure_time_error <= tolerance)},
        "pure_space_fourier_integration_by_parts": {
            "abs_error": float(ibp_error),
            "passed": bool(ibp_error <= tolerance),
        },
        "manufactured_fisher_kpp_smooth_field": {
            "abs_error": float(manufactured_error),
            "passed": bool(manufactured_error <= tolerance),
        },
    }
    return {
        "summary_schema_version": "0.1",
        "summary_type": "weak_reaction_diffusion_feasibility",
        "visibility": "internal_diagnostic_only",
        "pde": "reaction_diffusion_fisher_kpp",
        "quadrature_rule": "composite_simpson_tensor_product_v1",
        "identity_tolerance": float(tolerance),
        "identity_tests": identity_tests,
        "generated_field_sanity": generated_sanity,
        "conclusion": "diagnostic_only",
        "all_identity_tests_passed": bool(all(test["passed"] for test in identity_tests.values())),
        "public_export_guard": {
            "weak_reaction_diffusion_public_api": False,
            "weak_derivative_backend_public_api": False,
            "wsindy_design_matrix_public_api": False,
        },
    }
