from __future__ import annotations

import numpy as np

from pdelie.contracts import FieldBatch
from pdelie.data.heat_1d import DEFAULT_DOMAIN_LENGTH as _DEFAULT_DOMAIN_LENGTH
from pdelie.errors import SchemaValidationError, ScopeValidationError, ShapeValidationError


__all__ = ["generate_kdv_1d_field_batch"]


def _validate_integer_like(value: object, *, name: str, minimum: int | None = None) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise SchemaValidationError(f"{name} must be an integer.")
    normalized = int(value)
    if minimum is not None and normalized < minimum:
        raise SchemaValidationError(f"{name} must be at least {minimum}.")
    return normalized


def _validate_finite_float(value: object, *, name: str, positive: bool, nonnegative: bool = False) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise SchemaValidationError(f"{name} must be a finite scalar.")
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{name} must be a finite scalar.") from exc
    if not np.isfinite(normalized):
        raise SchemaValidationError(f"{name} must be a finite scalar.")
    if positive and normalized <= 0.0:
        raise SchemaValidationError(f"{name} must be positive.")
    if nonnegative and normalized < 0.0:
        raise SchemaValidationError(f"{name} must be nonnegative.")
    return normalized


def _sample_kdv_mode_coefficients(
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


def _evaluate_kdv_fourier_series(
    *,
    x: np.ndarray,
    domain_length: float,
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
    phase = (2.0 * np.pi / float(domain_length)) * x
    spatial_cos = np.cos(np.outer(modes, phase))
    spatial_sin = np.sin(np.outer(modes, phase))
    batch_cos = cosine_coefficients[:, :, None]
    batch_sin = sine_coefficients[:, :, None]
    values = np.sum(batch_cos * spatial_cos[None, :, :] + batch_sin * spatial_sin[None, :, :], axis=1)
    return _apply_two_thirds_filter(values)


def _spectral_spatial_derivatives(values: np.ndarray, *, dx: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    values = np.asarray(values, dtype=float)
    wavenumbers = 2.0 * np.pi * np.fft.fftfreq(values.shape[-1], d=dx).reshape(_reshape_last_axis(values))
    spectrum = np.fft.fft(values, axis=-1)
    u_x = np.real(np.fft.ifft((1j * wavenumbers) * spectrum, axis=-1))
    u_xx = np.real(np.fft.ifft(-(wavenumbers**2) * spectrum, axis=-1))
    u_xxx = np.real(np.fft.ifft(((1j * wavenumbers) ** 3) * spectrum, axis=-1))
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
    max_time: float = 0.03,
    num_modes: int = 3,
    amplitude: float = 0.08,
    seed: int = 0,
    num_substeps: int = 8,
    domain_length: float = _DEFAULT_DOMAIN_LENGTH,
) -> FieldBatch:
    normalized_batch_size = _validate_integer_like(batch_size, name="batch_size", minimum=1)
    normalized_num_times = _validate_integer_like(num_times, name="num_times", minimum=3)
    normalized_num_points = _validate_integer_like(num_points, name="num_points", minimum=16)
    normalized_num_modes = _validate_integer_like(num_modes, name="num_modes", minimum=1)
    normalized_seed = _validate_integer_like(seed, name="seed", minimum=0)
    normalized_num_substeps = _validate_integer_like(num_substeps, name="num_substeps", minimum=1)
    normalized_max_time = _validate_finite_float(max_time, name="max_time", positive=True)
    normalized_amplitude = _validate_finite_float(amplitude, name="amplitude", positive=False, nonnegative=True)
    normalized_domain_length = _validate_finite_float(domain_length, name="domain_length", positive=True)

    max_dealiased_modes = normalized_num_points // 3
    if normalized_num_modes > max_dealiased_modes:
        raise ScopeValidationError("num_modes must be no greater than floor(num_points / 3).")

    x = np.linspace(0.0, normalized_domain_length, normalized_num_points, endpoint=False, dtype=float)
    t = np.linspace(0.0, normalized_max_time, normalized_num_times, dtype=float)
    cosine, sine = _sample_kdv_mode_coefficients(
        batch_size=normalized_batch_size,
        num_modes=normalized_num_modes,
        seed=normalized_seed,
        amplitude=normalized_amplitude,
    )
    initial_values = _evaluate_kdv_fourier_series(
        x=x,
        domain_length=normalized_domain_length,
        cosine_coefficients=cosine,
        sine_coefficients=sine,
    )
    values = _rollout_kdv_periodic(
        initial_values,
        output_times=t,
        domain_length=normalized_domain_length,
        num_substeps=normalized_num_substeps,
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
