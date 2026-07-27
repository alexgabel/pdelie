from __future__ import annotations

from collections.abc import Callable

import numpy as np

from pdelie.contracts import FieldBatch
from pdelie.data._coefficient_profiles import (
    ADVECTION_FORM_CONSERVATIVE,
    ADVECTION_FORM_NONCONSERVATIVE,
    ALLOWED_ADVECTION_FORMS,
    ALLOWED_DIFFUSIVITY_FORMS,
    DIFFUSIVITY_FORM_CONSERVATIVE,
    DIFFUSIVITY_FORM_NONCONSERVATIVE,
    NU_TREATMENT_POLICY_FIXED_BACKGROUND,
    resolve_coefficient_profile,
    validate_equation_form,
)
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


def _spectral_first_derivative(values: np.ndarray, dx: float) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    shape = [1] * values.ndim
    shape[-1] = values.shape[-1]
    wavenumbers = 2.0 * np.pi * np.fft.fftfreq(values.shape[-1], d=dx).reshape(tuple(shape))
    derivative = np.real(np.fft.ifft((1j * wavenumbers) * np.fft.fft(values, axis=-1), axis=-1))
    return np.asarray(derivative, dtype=float)


def _spectral_second_derivative(values: np.ndarray, dx: float) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    shape = [1] * values.ndim
    shape[-1] = values.shape[-1]
    wavenumbers = 2.0 * np.pi * np.fft.fftfreq(values.shape[-1], d=dx).reshape(tuple(shape))
    second = np.real(np.fft.ifft(-(wavenumbers**2) * np.fft.fft(values, axis=-1), axis=-1))
    return np.asarray(second, dtype=float)


def _variable_advection_diffusion_rhs(
    values: np.ndarray,
    *,
    advection_values: np.ndarray,
    diffusivity_values: np.ndarray,
    dx: float,
    diffusivity_form: str,
    advection_form: str,
) -> np.ndarray:
    """Variable-coefficient advection-diffusion RHS in the requested forms.

    Diffusive term -- ``conservative_divergence``: ``d/dx( nu(x) du/dx )``;
    ``nonconservative_nu_uxx``: ``nu(x) * u_xx``.

    Advective term -- ``nonconservative_c_ux``: ``-c(x) u_x``, which is what the
    constant-coefficient ``AdvectionDiffusionResidualEvaluator`` models with a
    scalar ``c``; ``conservative_divergence``: ``-d/dx( c(x) u )``.

    Both selections are recorded in ``parameter_tags`` (``nu_form`` / ``c_form``)
    so the v0.34a residual evaluators dispatch rather than guess.
    """
    u_x = _spectral_first_derivative(values, dx)

    if diffusivity_form == DIFFUSIVITY_FORM_NONCONSERVATIVE:
        diffusion = diffusivity_values * _spectral_second_derivative(values, dx)
    else:
        diffusion = _spectral_first_derivative(diffusivity_values * u_x, dx)

    if advection_form == ADVECTION_FORM_CONSERVATIVE:
        advection = -_spectral_first_derivative(advection_values * values, dx)
    else:
        advection = -advection_values * u_x

    return np.asarray(advection + diffusion, dtype=float)


def _rollout_variable_advection_diffusion_periodic(
    initial_values: np.ndarray,
    *,
    output_times: np.ndarray,
    domain_length: float,
    advection_values: np.ndarray,
    diffusivity_values: np.ndarray,
    diffusivity_form: str,
    advection_form: str,
    num_substeps: int = 64,
) -> np.ndarray:
    """RK4 rollout for the variable-coefficient path.

    The constant-coefficient generator uses an exact spectral multiplier, which
    is only valid when both coefficients are constant; a variable coefficient
    has no such closed form.
    """
    initial_values = np.asarray(initial_values, dtype=float)
    output_times = np.asarray(output_times, dtype=float)

    output_dt = float(output_times[1] - output_times[0])
    if not np.allclose(np.diff(output_times), output_dt, atol=1e-12, rtol=0.0):
        raise ShapeValidationError("output_times must be uniformly spaced.")

    dx = float(domain_length / initial_values.shape[-1])
    internal_dt = output_dt / float(num_substeps)
    state = initial_values
    rollout = np.empty((initial_values.shape[0], output_times.size, initial_values.shape[1]), dtype=float)
    rollout[:, 0, :] = state

    def rhs(current: np.ndarray) -> np.ndarray:
        return _variable_advection_diffusion_rhs(
            current,
            advection_values=advection_values,
            diffusivity_values=diffusivity_values,
            dx=dx,
            diffusivity_form=diffusivity_form,
            advection_form=advection_form,
        )

    for time_index in range(1, output_times.size):
        for _ in range(num_substeps):
            k1 = rhs(state)
            k2 = rhs(state + 0.5 * internal_dt * k1)
            k3 = rhs(state + 0.5 * internal_dt * k2)
            k4 = rhs(state + internal_dt * k3)
            state = state + (internal_dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        rollout[:, time_index, :] = state

    return rollout


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
    diffusivity_profile: np.ndarray | Callable[[np.ndarray], np.ndarray] | None = None,
    advection_profile: np.ndarray | Callable[[np.ndarray], np.ndarray] | None = None,
    diffusivity_form: str = DIFFUSIVITY_FORM_CONSERVATIVE,
    advection_form: str = ADVECTION_FORM_NONCONSERVATIVE,
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
    # Validation fires before any numerical work.
    normalized_diffusivity_form = validate_equation_form(
        diffusivity_form, allowed=ALLOWED_DIFFUSIVITY_FORMS, name="diffusivity_form"
    )
    normalized_advection_form = validate_equation_form(
        advection_form, allowed=ALLOWED_ADVECTION_FORMS, name="advection_form"
    )
    diffusivity_values, diffusivity_tags = resolve_coefficient_profile(
        diffusivity_profile,
        x=x,
        constant_value=normalized_diffusivity,
        prefix="nu",
        name="diffusivity_profile",
        require_positive=True,
    )
    advection_values, advection_tags = resolve_coefficient_profile(
        advection_profile,
        x=x,
        constant_value=normalized_advection_speed,
        prefix="c",
        name="advection_profile",
        require_positive=False,
    )

    if diffusivity_values is None and advection_values is None:
        values = _rollout_advection_diffusion_periodic(
            initial_values,
            output_times=t,
            domain_length=normalized_domain_length,
            advection_speed=normalized_advection_speed,
            diffusivity=normalized_diffusivity,
        )
    else:
        # A single variable coefficient is enough to invalidate the exact
        # spectral multiplier; the other coefficient is broadcast as a constant.
        resolved_diffusivity = (
            np.full(x.size, normalized_diffusivity, dtype=float)
            if diffusivity_values is None
            else diffusivity_values
        )
        resolved_advection = (
            np.full(x.size, normalized_advection_speed, dtype=float)
            if advection_values is None
            else advection_values
        )
        values = _rollout_variable_advection_diffusion_periodic(
            initial_values,
            output_times=t,
            domain_length=normalized_domain_length,
            advection_values=resolved_advection,
            diffusivity_values=resolved_diffusivity,
            diffusivity_form=normalized_diffusivity_form,
            advection_form=normalized_advection_form,
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
                "nu_form": normalized_diffusivity_form,
                "c_form": normalized_advection_form,
                "nu_treatment_policy": NU_TREATMENT_POLICY_FIXED_BACKGROUND,
                **diffusivity_tags,
                **advection_tags,
            },
        },
        preprocess_log=[],
    )
