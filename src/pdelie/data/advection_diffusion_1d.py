from __future__ import annotations

import numpy as np

from pdelie.contracts import FieldBatch
from pdelie.data.heat_1d import DEFAULT_DOMAIN_LENGTH as _DEFAULT_DOMAIN_LENGTH
from pdelie.errors import SchemaValidationError, ScopeValidationError, ShapeValidationError


__all__ = ["generate_advection_diffusion_1d_field_batch"]


DEFAULT_ADVECTION_DIFFUSION_EQUATION = "advection_diffusion_constant_coefficient"
DEFAULT_ADVECTION_DIFFUSION_SPEED = 0.75
DEFAULT_ADVECTION_DIFFUSION_DIFFUSIVITY = 0.05


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


def _sample_mode_coefficients(
    *,
    batch_size: int,
    num_modes: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    mode_scale = 1.0 / np.arange(1, num_modes + 1, dtype=float)
    cosine = rng.normal(size=(batch_size, num_modes)) * mode_scale
    sine = rng.normal(size=(batch_size, num_modes)) * mode_scale
    return cosine, sine


def _evaluate_zero_mean_fourier_initial_condition(
    *,
    x: np.ndarray,
    domain_length: float,
    cosine_coefficients: np.ndarray,
    sine_coefficients: np.ndarray,
    amplitude: float,
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
    values = np.sum(
        cosine_coefficients[:, :, None] * spatial_cos[None, :, :]
        + sine_coefficients[:, :, None] * spatial_sin[None, :, :],
        axis=1,
    )
    max_abs = np.maximum(np.max(np.abs(values), axis=1, keepdims=True), 1e-12)
    return float(amplitude) * values / max_abs


def _rollout_advection_diffusion_periodic(
    initial_values: np.ndarray,
    *,
    output_times: np.ndarray,
    domain_length: float,
    advection_speed: float,
    diffusivity: float,
) -> np.ndarray:
    initial_values = np.asarray(initial_values, dtype=float)
    output_times = np.asarray(output_times, dtype=float)

    if initial_values.ndim != 2:
        raise ShapeValidationError("initial_values must have shape (batch, x).")
    if output_times.ndim != 1 or output_times.size < 2:
        raise ShapeValidationError("output_times must be one-dimensional with at least two entries.")
    if not np.all(np.isfinite(initial_values)) or not np.all(np.isfinite(output_times)):
        raise ShapeValidationError("initial_values and output_times must be finite.")

    dx = float(domain_length / initial_values.shape[-1])
    wavenumbers = 2.0 * np.pi * np.fft.fftfreq(initial_values.shape[-1], d=dx)
    spectrum0 = np.fft.fft(initial_values, axis=-1)
    rate = -float(diffusivity) * wavenumbers**2 - 1j * float(advection_speed) * wavenumbers
    multipliers = np.exp(output_times[:, None] * rate[None, :])
    spectrum = spectrum0[:, None, :] * multipliers[None, :, :]
    return np.real(np.fft.ifft(spectrum, axis=-1))


def generate_advection_diffusion_1d_field_batch(
    *,
    batch_size: int = 5,
    num_times: int = 65,
    num_points: int = 64,
    max_time: float = 0.4,
    advection_speed: float = DEFAULT_ADVECTION_DIFFUSION_SPEED,
    diffusivity: float = DEFAULT_ADVECTION_DIFFUSION_DIFFUSIVITY,
    num_modes: int = 6,
    amplitude: float = 0.2,
    domain_length: float = _DEFAULT_DOMAIN_LENGTH,
    seed: int = 0,
) -> FieldBatch:
    normalized_batch_size = _validate_integer_like(batch_size, name="batch_size", minimum=1)
    normalized_num_times = _validate_integer_like(num_times, name="num_times", minimum=3)
    normalized_num_points = _validate_integer_like(num_points, name="num_points", minimum=16)
    normalized_num_modes = _validate_integer_like(num_modes, name="num_modes", minimum=1)
    normalized_seed = _validate_integer_like(seed, name="seed", minimum=0)
    normalized_max_time = _validate_finite_float(max_time, name="max_time", positive=True)
    normalized_advection_speed = _validate_finite_float(advection_speed, name="advection_speed", positive=False)
    normalized_diffusivity = _validate_finite_float(diffusivity, name="diffusivity", positive=True)
    normalized_amplitude = _validate_finite_float(amplitude, name="amplitude", positive=False, nonnegative=True)
    normalized_domain_length = _validate_finite_float(domain_length, name="domain_length", positive=True)

    max_modes = normalized_num_points // 3
    if normalized_num_modes > max_modes:
        raise ScopeValidationError("num_modes must be no greater than floor(num_points / 3).")
    if normalized_amplitude > 1.0:
        raise ScopeValidationError("amplitude must be no greater than 1.0 for the frozen advection-diffusion fixture.")

    x = np.linspace(0.0, normalized_domain_length, normalized_num_points, endpoint=False, dtype=float)
    t = np.linspace(0.0, normalized_max_time, normalized_num_times, dtype=float)
    cosine, sine = _sample_mode_coefficients(
        batch_size=normalized_batch_size,
        num_modes=normalized_num_modes,
        seed=normalized_seed,
    )
    initial_values = _evaluate_zero_mean_fourier_initial_condition(
        x=x,
        domain_length=normalized_domain_length,
        cosine_coefficients=cosine,
        sine_coefficients=sine,
        amplitude=normalized_amplitude,
    )
    values = _rollout_advection_diffusion_periodic(
        initial_values,
        output_times=t,
        domain_length=normalized_domain_length,
        advection_speed=normalized_advection_speed,
        diffusivity=normalized_diffusivity,
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
            "parameter_tags": {
                "equation": DEFAULT_ADVECTION_DIFFUSION_EQUATION,
                "c": normalized_advection_speed,
                "nu": normalized_diffusivity,
            },
        },
        preprocess_log=[],
    )
