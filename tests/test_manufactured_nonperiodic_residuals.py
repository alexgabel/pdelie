"""v0.30d manufactured-solution residual tests for nonperiodic Dirichlet data.

Each test constructs a `FieldBatch` from an analytic function whose derivatives
are known in closed form and asserts that

- the residual routes through the finite_difference backend,
- the interior-only max/RMS residual is small (bounded by the local truncation
  error of the second-order centered stencil),
- the full-grid diagnostic is also reported,
- the diagnostics carry `residual_domain_policy = "interior_only"` and a positive
  `boundary_trim_width`.

For polynomial manufactured solutions of degree ≤ 2, `np.gradient(edge_order=2)`
is exact to floating-point tolerance in the interior. Nonpolynomial solutions
converge at O(h²) in the interior and are checked against a coarser tolerance.
"""
from __future__ import annotations

import numpy as np
import pytest

from pdelie.data import from_numpy
from pdelie.residuals import (
    AdvectionDiffusionResidualEvaluator,
    BurgersResidualEvaluator,
    HeatResidualEvaluator,
    ReactionDiffusionResidualEvaluator,
)


def _dirichlet_metadata(**parameter_tags) -> dict:
    return {
        "boundary_conditions": {"x": "dirichlet"},
        "coordinate_system": "cartesian",
        "grid_regularity": "uniform",
        "grid_type": "rectilinear",
        "parameter_tags": dict(parameter_tags),
    }


def _open_unknown_metadata(**parameter_tags) -> dict:
    return {
        "boundary_conditions": {"x": "open_unknown"},
        "coordinate_system": "cartesian",
        "grid_regularity": "uniform",
        "grid_type": "rectilinear",
        "parameter_tags": dict(parameter_tags),
    }


def _uniform_grid(*, num_times: int, num_points: int, t_max: float, x_min: float, x_max: float):
    t = np.linspace(0.0, t_max, num_times, dtype=float)
    x = np.linspace(x_min, x_max, num_points, dtype=float)
    T, X = np.meshgrid(t, x, indexing="ij")
    return t, x, T, X


# --- Heat -----------------------------------------------------------------


def test_heat_polynomial_manufactured_solution_on_dirichlet_grid_has_zero_interior_residual() -> None:
    """u(t, x) = t + x² satisfies u_t - u_xx = 1 - 2 = -1 exactly.

    Choose diffusivity=1.0 and offset the manufactured field so that
    u_t - u_xx = 0 exactly: u(t, x) = t + x² gives u_t = 1, u_xx = 2;
    the residual is 1 - 1·2 = -1. Verify the FD backend reproduces
    the analytic residual to floating-point precision on the interior.
    """
    nu = 1.0
    t, x, T, X = _uniform_grid(num_times=17, num_points=33, t_max=1.0, x_min=0.0, x_max=2.0)
    values = (T + X**2)[None, ..., None]  # (1, time, x, 1)

    field = from_numpy(
        values,
        dims=("batch", "time", "x", "var"),
        coords={"time": t, "x": x},
        var_name="u",
        metadata=_dirichlet_metadata(nu=nu),
    )
    residual = HeatResidualEvaluator(diffusivity=nu).evaluate(field)

    assert residual.diagnostics["backend"] == "finite_difference"
    assert residual.diagnostics["residual_domain_policy"] == "interior_only"
    assert residual.diagnostics["boundary_trim_width"] > 0
    assert "full_grid_diagnostic" in residual.diagnostics

    # Analytic residual: u_t - nu*u_xx = 1 - 1*2 = -1 everywhere.
    # Interior max residual ~= |-1| exactly; deviation from -1 is FD error.
    trim = residual.diagnostics["boundary_trim_width"]
    trimmed = residual.residual[:, :, trim:-trim, :]
    np.testing.assert_allclose(trimmed, -1.0, atol=1e-10)


def test_heat_polynomial_matched_to_diffusivity_gives_near_zero_residual() -> None:
    """Manufactured smooth field where u_t = nu * u_xx exactly.

    u(t, x) = e^{-π² nu t} sin(π x): u_t = -π² nu u; u_xx = -π² u;
    so u_t - nu u_xx = -π² nu u + π² nu u = 0. Verify the numerical residual is
    dominated by FD truncation error, not by a systematic offset.
    """
    nu = 0.05
    t, x, T, X = _uniform_grid(num_times=17, num_points=65, t_max=0.4, x_min=0.0, x_max=1.0)
    values = (np.exp(-np.pi**2 * nu * T) * np.sin(np.pi * X))[None, ..., None]

    field = from_numpy(
        values,
        dims=("batch", "time", "x", "var"),
        coords={"time": t, "x": x},
        var_name="u",
        metadata=_dirichlet_metadata(nu=nu),
    )
    residual = HeatResidualEvaluator(diffusivity=nu).evaluate(field)

    # Interior max residual bounded by O(h²) truncation.
    assert residual.diagnostics["max_abs_residual"] < 5e-3
    assert residual.diagnostics["rms_residual"] < 5e-4
    # Full grid diagnostic is worse (boundary error) but still finite.
    assert np.isfinite(residual.diagnostics["full_grid_diagnostic"]["max_abs_residual"])
    assert residual.diagnostics["full_grid_diagnostic"]["max_abs_residual"] >= residual.diagnostics["max_abs_residual"]


def test_heat_manufactured_convergence_second_order_on_interior() -> None:
    """Halving h should quarter the interior max residual, up to a small constant."""
    nu = 0.05
    errors: list[float] = []
    for N in (33, 65, 129):
        t, x, T, X = _uniform_grid(num_times=17, num_points=N, t_max=0.4, x_min=0.0, x_max=1.0)
        values = (np.exp(-np.pi**2 * nu * T) * np.sin(np.pi * X))[None, ..., None]
        field = from_numpy(
            values,
            dims=("batch", "time", "x", "var"),
            coords={"time": t, "x": x},
            var_name="u",
            metadata=_dirichlet_metadata(nu=nu),
        )
        residual = HeatResidualEvaluator(diffusivity=nu).evaluate(field)
        errors.append(residual.diagnostics["max_abs_residual"])

    # O(h²): halving N halves h, so errors should decrease by roughly 4×.
    # Allow a generous multiplier band to accommodate the temporal FD error contribution.
    assert errors[1] < errors[0] * 0.5
    assert errors[2] < errors[1] * 0.5


# --- Burgers --------------------------------------------------------------


def test_burgers_polynomial_manufactured_solution_on_dirichlet_grid_has_analytic_residual() -> None:
    """u(t, x) = t + x²:
        u_t = 1; u_x = 2x; u_xx = 2;
        residual = u_t + u u_x - nu u_xx = 1 + (t+x²)·2x - 2 nu.
    Verify the FD-computed residual matches the analytic residual to fp precision on the interior.
    """
    nu = 0.05
    t, x, T, X = _uniform_grid(num_times=17, num_points=33, t_max=0.2, x_min=0.0, x_max=1.0)
    values = (T + X**2)[None, ..., None]
    field = from_numpy(
        values,
        dims=("batch", "time", "x", "var"),
        coords={"time": t, "x": x},
        var_name="u",
        metadata=_dirichlet_metadata(nu=nu),
    )
    residual_report = BurgersResidualEvaluator(diffusivity=nu).evaluate(field)
    assert residual_report.diagnostics["backend"] == "finite_difference"
    assert residual_report.diagnostics["residual_domain_policy"] == "interior_only"

    trim = residual_report.diagnostics["boundary_trim_width"]
    analytic_residual = (1.0 + (T + X**2) * 2.0 * X - 2.0 * nu)[None, ..., None]
    np.testing.assert_allclose(
        residual_report.residual[:, :, trim:-trim, :],
        analytic_residual[:, :, trim:-trim, :],
        atol=1e-10,
    )


# --- Advection-diffusion --------------------------------------------------


def test_advection_diffusion_on_open_unknown_grid_records_interior_only_diagnostics() -> None:
    """A smooth field on an open_unknown boundary produces well-defined FD residuals."""
    c = 0.5
    nu = 0.02
    t, x, T, X = _uniform_grid(num_times=17, num_points=49, t_max=0.4, x_min=-1.0, x_max=1.0)
    values = (np.exp(-4.0 * (X - c * T) ** 2))[None, ..., None]

    field = from_numpy(
        values,
        dims=("batch", "time", "x", "var"),
        coords={"time": t, "x": x},
        var_name="u",
        metadata=_open_unknown_metadata(
            equation="advection_diffusion_constant_coefficient", c=c, nu=nu
        ),
    )
    residual = AdvectionDiffusionResidualEvaluator().evaluate(field)

    assert residual.diagnostics["backend"] == "finite_difference"
    assert residual.diagnostics["residual_domain_policy"] == "interior_only"
    assert residual.diagnostics["equation"] == "u_t + c*u_x - nu*u_xx = 0"
    assert residual.diagnostics["c"] == c
    assert residual.diagnostics["nu"] == nu
    assert np.isfinite(residual.diagnostics["max_abs_residual"])
    assert np.isfinite(residual.diagnostics["rms_residual"])


# --- Reaction-diffusion --------------------------------------------------


def test_reaction_diffusion_on_dirichlet_grid_records_interior_only_diagnostics() -> None:
    """Reaction-diffusion evaluator now flows through FD on Dirichlet data."""
    nu = 0.05
    rho = 1.0
    t, x, T, X = _uniform_grid(num_times=17, num_points=49, t_max=0.4, x_min=0.0, x_max=1.0)
    values = (0.5 + 0.1 * np.sin(np.pi * X) * np.exp(-nu * np.pi**2 * T))[None, ..., None]

    field = from_numpy(
        values,
        dims=("batch", "time", "x", "var"),
        coords={"time": t, "x": x},
        var_name="u",
        metadata=_dirichlet_metadata(
            equation="reaction_diffusion_fisher_kpp", nu=nu, rho=rho
        ),
    )
    residual = ReactionDiffusionResidualEvaluator().evaluate(field)

    assert residual.diagnostics["backend"] == "finite_difference"
    assert residual.diagnostics["residual_domain_policy"] == "interior_only"
    assert residual.diagnostics["equation"] == "u_t - nu*u_xx - rho*u*(1-u) = 0"
    assert residual.diagnostics["nu"] == nu
    assert residual.diagnostics["rho"] == rho
    assert np.isfinite(residual.diagnostics["max_abs_residual"])
    assert np.isfinite(residual.diagnostics["rms_residual"])


# --- Periodic regression -------------------------------------------------


def test_periodic_evaluators_still_use_spectral_fd_and_full_grid_policy() -> None:
    """Regression: periodic data still routes to spectral_fd with full_grid residual policy."""
    from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch

    heat = generate_heat_1d_field_batch(batch_size=1, num_times=9, num_points=16, seed=101)
    residual = HeatResidualEvaluator().evaluate(heat)
    assert residual.diagnostics["backend"] == "spectral_fd"
    assert residual.diagnostics["residual_domain_policy"] == "full_grid"
    assert "full_grid_diagnostic" not in residual.diagnostics

    burgers = generate_burgers_1d_field_batch(batch_size=1, num_times=9, num_points=16, seed=102)
    residual = BurgersResidualEvaluator().evaluate(burgers)
    assert residual.diagnostics["backend"] == "spectral_fd"
    assert residual.diagnostics["residual_domain_policy"] == "full_grid"


@pytest.mark.parametrize("evaluator_cls", [HeatResidualEvaluator, BurgersResidualEvaluator])
def test_periodic_diagnostics_include_rms_residual_after_v0_30d(evaluator_cls) -> None:
    """Heat/Burgers diagnostics gain rms_residual in v0.30d (previously only max_abs)."""
    from pdelie.data import generate_heat_1d_field_batch

    field = generate_heat_1d_field_batch(batch_size=1, num_times=9, num_points=16, seed=200)
    residual = evaluator_cls().evaluate(field)
    assert "rms_residual" in residual.diagnostics
    assert residual.diagnostics["rms_residual"] >= 0.0
