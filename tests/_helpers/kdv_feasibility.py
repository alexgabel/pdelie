from __future__ import annotations

import numpy as np

from pdelie import DerivativeBatch, FieldBatch, ResidualBatch
from pdelie.data.heat_1d import DEFAULT_DOMAIN_LENGTH
from pdelie.errors import ShapeValidationError


KDV_FEASIBILITY_CONFIG: dict[str, object] = {
    "batch_size": 2,
    "num_times": 17,
    "num_points": 64,
    "max_time": 0.03,
    "num_modes": 3,
    "amplitude": 0.08,
    "num_substeps": 8,
    "domain_length": DEFAULT_DOMAIN_LENGTH,
    "equation": "u_t + 6*u*u_x + u_xxx = 0",
}


def sample_kdv_mode_coefficients(
    *,
    batch_size: int,
    num_modes: int,
    seed: int,
    amplitude: float,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    mode_scale = amplitude / np.arange(1, num_modes + 1, dtype=float)
    cosine = rng.normal(size=(batch_size, num_modes)) * mode_scale
    sine = rng.normal(size=(batch_size, num_modes)) * mode_scale
    return cosine, sine


def evaluate_kdv_fourier_series(
    *,
    x: np.ndarray,
    cosine_coefficients: np.ndarray,
    sine_coefficients: np.ndarray,
) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    cosine_coefficients = np.asarray(cosine_coefficients, dtype=float)
    sine_coefficients = np.asarray(sine_coefficients, dtype=float)

    if cosine_coefficients.shape != sine_coefficients.shape:
        raise ShapeValidationError("cosine_coefficients and sine_coefficients must match.")
    if cosine_coefficients.ndim != 2:
        raise ShapeValidationError("Coefficient arrays must have shape (batch, num_modes).")

    modes = np.arange(1, cosine_coefficients.shape[1] + 1, dtype=float)
    spatial_cos = np.cos(np.outer(modes, x))
    spatial_sin = np.sin(np.outer(modes, x))
    batch_cos = cosine_coefficients[:, :, None]
    batch_sin = sine_coefficients[:, :, None]
    values = np.sum(batch_cos * spatial_cos[None, :, :] + batch_sin * spatial_sin[None, :, :], axis=1)
    return _apply_two_thirds_filter(values)


def _reshape_last_axis(values: np.ndarray) -> tuple[int, ...]:
    shape = [1] * values.ndim
    shape[-1] = values.shape[-1]
    return tuple(shape)


def _apply_two_thirds_filter(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    mode_numbers = np.fft.fftfreq(values.shape[-1]) * values.shape[-1]
    mask = (np.abs(mode_numbers) <= values.shape[-1] / 3.0).reshape(_reshape_last_axis(values))
    spectrum = np.fft.fft(values, axis=-1)
    return np.real(np.fft.ifft(spectrum * mask, axis=-1))


def _spectral_spatial_derivatives(values: np.ndarray, *, dx: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = np.asarray(values, dtype=float)
    wavenumbers = 2.0 * np.pi * np.fft.fftfreq(values.shape[-1], d=dx).reshape(_reshape_last_axis(values))
    spectrum = np.fft.fft(values, axis=-1)
    u_x = np.real(np.fft.ifft((1j * wavenumbers) * spectrum, axis=-1))
    u_xx = np.real(np.fft.ifft(-(wavenumbers**2) * spectrum, axis=-1))
    u_xxx = np.real(np.fft.ifft(-(1j) * (wavenumbers**3) * spectrum, axis=-1))
    return u_x, u_xx, u_xxx


def _kdv_rhs(values: np.ndarray, *, dx: float) -> np.ndarray:
    filtered = _apply_two_thirds_filter(values)
    u_x, _, u_xxx = _spectral_spatial_derivatives(filtered, dx=dx)
    nonlinear = _apply_two_thirds_filter(filtered * u_x)
    return _apply_two_thirds_filter(-6.0 * nonlinear - u_xxx)


def _rollout_kdv_periodic(
    initial_values: np.ndarray,
    *,
    output_times: np.ndarray,
    domain_length: float,
    num_substeps: int,
) -> np.ndarray:
    initial_values = np.asarray(initial_values, dtype=float)
    output_times = np.asarray(output_times, dtype=float)

    if initial_values.ndim != 2:
        raise ShapeValidationError("initial_values must have shape (batch, x).")
    if output_times.ndim != 1 or output_times.size < 2:
        raise ShapeValidationError("output_times must be one-dimensional with at least two entries.")
    if num_substeps < 1:
        raise ShapeValidationError("num_substeps must be at least 1.")

    output_dt = float(output_times[1] - output_times[0])
    if not np.allclose(np.diff(output_times), output_dt, atol=1e-12, rtol=0.0):
        raise ShapeValidationError("output_times must be uniformly spaced.")

    dx = float(domain_length / initial_values.shape[-1])
    internal_dt = output_dt / float(num_substeps)
    state = _apply_two_thirds_filter(initial_values)
    rollout = np.empty((initial_values.shape[0], output_times.size, initial_values.shape[-1]), dtype=float)
    rollout[:, 0, :] = state

    for time_index in range(1, output_times.size):
        for _ in range(num_substeps):
            k1 = _kdv_rhs(state, dx=dx)
            k2 = _kdv_rhs(state + 0.5 * internal_dt * k1, dx=dx)
            k3 = _kdv_rhs(state + 0.5 * internal_dt * k2, dx=dx)
            k4 = _kdv_rhs(state + internal_dt * k3, dx=dx)
            state = _apply_two_thirds_filter(state + (internal_dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4))
        rollout[:, time_index, :] = state

    return rollout


def generate_kdv_1d_field_batch(
    *,
    batch_size: int = 2,
    num_times: int = 17,
    num_points: int = 64,
    max_time: float = 0.05,
    num_modes: int = 3,
    amplitude: float = 0.08,
    seed: int = 0,
    num_substeps: int = 8,
    domain_length: float = DEFAULT_DOMAIN_LENGTH,
) -> FieldBatch:
    x = np.linspace(0.0, domain_length, num_points, endpoint=False, dtype=float)
    t = np.linspace(0.0, max_time, num_times, dtype=float)
    cosine, sine = sample_kdv_mode_coefficients(
        batch_size=batch_size,
        num_modes=num_modes,
        seed=seed,
        amplitude=amplitude,
    )
    initial_values = evaluate_kdv_fourier_series(
        x=x,
        cosine_coefficients=cosine,
        sine_coefficients=sine,
    )
    values = _rollout_kdv_periodic(
        initial_values,
        output_times=t,
        domain_length=domain_length,
        num_substeps=num_substeps,
    )

    return FieldBatch(
        values=values[..., None],
        dims=("batch", "time", "x", "var"),
        coords={"time": t, "x": x},
        var_names=["u"],
        metadata={
            "boundary_conditions": {"x": "periodic"},
            "coordinate_system": "cartesian",
            "grid_regularity": "uniform",
            "grid_type": "rectilinear",
            "parameter_tags": {"equation": "kdv_normalized"},
        },
        preprocess_log=[],
    )


def compute_kdv_feasibility_derivatives(field: FieldBatch) -> DerivativeBatch:
    field.validate()
    values = np.asarray(field.values[..., 0], dtype=float)
    x = np.asarray(field.coords["x"], dtype=float)
    t = np.asarray(field.coords["time"], dtype=float)
    dx = float(x[1] - x[0])
    if t.ndim != 1 or t.size < 3:
        raise ShapeValidationError("KdV feasibility derivatives require a one-dimensional time coordinate with at least 3 points.")
    dt = float(t[1] - t[0])
    if not np.allclose(np.diff(t), dt, atol=1e-12, rtol=0.0):
        raise ShapeValidationError("KdV feasibility derivatives require a uniform time grid.")

    u_x, u_xx, u_xxx = _spectral_spatial_derivatives(values, dx=dx)
    u_t = np.gradient(values, dt, axis=1, edge_order=2)

    derivatives = DerivativeBatch(
        derivatives={
            "u_x": u_x[..., None],
            "u_xx": u_xx[..., None],
            "u_xxx": u_xxx[..., None],
            "u_t": u_t[..., None],
        },
        backend="spectral_fd",
        config={
            "spatial_method": "spectral",
            "temporal_method": "finite_difference",
            "temporal_edge_order": 2,
            "spatial_max_order": 3,
            "dealiasing": "two_thirds",
        },
        boundary_assumptions="periodic in x; finite differences in time",
        diagnostics={
            "dx": dx,
            "dt": dt,
            "x_points": int(x.size),
            "time_points": int(t.size),
        },
    )
    derivatives.validate_against(field)
    return derivatives


def evaluate_kdv_feasibility_residual(
    field: FieldBatch,
    derivatives: DerivativeBatch | None = None,
) -> ResidualBatch:
    field.validate()
    if derivatives is None:
        derivatives = compute_kdv_feasibility_derivatives(field)
    derivatives.validate_against(field)

    u = np.asarray(field.values, dtype=float)
    residual = (
        derivatives.derivatives["u_t"]
        + 6.0 * u * derivatives.derivatives["u_x"]
        + derivatives.derivatives["u_xxx"]
    )
    batch = ResidualBatch(
        residual=residual,
        definition_type="analytic",
        normalization="none",
        diagnostics={
            "backend": derivatives.backend,
            "equation": KDV_FEASIBILITY_CONFIG["equation"],
            "max_abs_residual": float(np.max(np.abs(residual))),
        },
    )
    batch.validate_against(field)
    return batch


def exact_fourier_third_derivative(
    *,
    x: np.ndarray,
    cosine_coefficients: np.ndarray,
    sine_coefficients: np.ndarray,
) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    cosine_coefficients = np.asarray(cosine_coefficients, dtype=float)
    sine_coefficients = np.asarray(sine_coefficients, dtype=float)

    modes = np.arange(1, cosine_coefficients.shape[1] + 1, dtype=float)
    spatial_cos = np.cos(np.outer(modes, x))
    spatial_sin = np.sin(np.outer(modes, x))
    batch_cos = cosine_coefficients[:, :, None]
    batch_sin = sine_coefficients[:, :, None]

    values = np.sum(
        batch_cos * (modes[None, :, None] ** 3) * spatial_sin[None, :, :]
        - batch_sin * (modes[None, :, None] ** 3) * spatial_cos[None, :, :],
        axis=1,
    )
    return values


def compute_mass(field: FieldBatch) -> np.ndarray:
    values = np.asarray(field.values[..., 0], dtype=float)
    dx = float(field.coords["x"][1] - field.coords["x"][0])
    return dx * np.sum(values, axis=-1)


def compute_l2_norm(field: FieldBatch) -> np.ndarray:
    values = np.asarray(field.values[..., 0], dtype=float)
    dx = float(field.coords["x"][1] - field.coords["x"][0])
    return np.sqrt(dx * np.sum(values**2, axis=-1))
