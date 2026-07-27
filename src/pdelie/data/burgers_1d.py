from __future__ import annotations

from collections.abc import Callable

import numpy as np

from pdelie.contracts import FieldBatch
from pdelie.data._coefficient_profiles import (
    ALLOWED_DIFFUSIVITY_FORMS,
    DIFFUSIVITY_FORM_CONSERVATIVE,
    DIFFUSIVITY_FORM_NONCONSERVATIVE,
    NU_TREATMENT_POLICY_FIXED_BACKGROUND,
    resolve_coefficient_profile,
    validate_equation_form,
)
from pdelie.data.heat_1d import DEFAULT_DOMAIN_LENGTH
from pdelie.errors import ShapeValidationError

DEFAULT_BURGERS_DIFFUSIVITY = 0.1
DEFAULT_BURGERS_AMPLITUDE = 0.15


def sample_burgers_mode_coefficients(
    *,
    batch_size: int,
    num_modes: int,
    seed: int,
    amplitude: float = DEFAULT_BURGERS_AMPLITUDE,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    mode_scale = amplitude / np.arange(1, num_modes + 1, dtype=float)
    cosine = rng.normal(size=(batch_size, num_modes)) * mode_scale
    sine = rng.normal(size=(batch_size, num_modes)) * mode_scale
    return cosine, sine


def evaluate_burgers_initial_condition(
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


def _spectral_periodic_derivatives(values: np.ndarray, dx: float) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(values, dtype=float)
    wavenumbers = 2.0 * np.pi * np.fft.fftfreq(values.shape[-1], d=dx).reshape(_reshape_last_axis(values))
    spectrum = np.fft.fft(values, axis=-1)
    u_x = np.real(np.fft.ifft((1j * wavenumbers) * spectrum, axis=-1))
    u_xx = np.real(np.fft.ifft(-(wavenumbers**2) * spectrum, axis=-1))
    return u_x, u_xx


def _burgers_rhs(values: np.ndarray, *, diffusivity: float, dx: float) -> np.ndarray:
    u_x, u_xx = _spectral_periodic_derivatives(values, dx)
    return _apply_two_thirds_filter(-values * u_x + diffusivity * u_xx)


def _spectral_first_derivative(values: np.ndarray, dx: float) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    wavenumbers = 2.0 * np.pi * np.fft.fftfreq(values.shape[-1], d=dx).reshape(_reshape_last_axis(values))
    return np.real(np.fft.ifft((1j * wavenumbers) * np.fft.fft(values, axis=-1), axis=-1))


def _variable_burgers_rhs(
    values: np.ndarray, *, diffusivity_values: np.ndarray, dx: float, form: str
) -> np.ndarray:
    """Burgers RHS with a variable diffusivity.

    * ``conservative_divergence``: ``-u u_x + d/dx( nu(x) du/dx )``.
    * ``nonconservative_nu_uxx``: ``-u u_x + nu(x) * u_xx``.

    See ``pdelie.data.heat_1d._variable_heat_rhs`` for why the form is recorded
    rather than assumed. The two-thirds dealiasing filter is applied exactly as
    on the constant-coefficient path.
    """
    u_x, u_xx = _spectral_periodic_derivatives(values, dx)
    if form == DIFFUSIVITY_FORM_NONCONSERVATIVE:
        diffusion = diffusivity_values * u_xx
    else:
        diffusion = _spectral_first_derivative(diffusivity_values * u_x, dx)
    return _apply_two_thirds_filter(-values * u_x + diffusion)


def _rollout_variable_burgers_periodic(
    initial_values: np.ndarray,
    *,
    output_times: np.ndarray,
    diffusivity_values: np.ndarray,
    form: str,
    domain_length: float = DEFAULT_DOMAIN_LENGTH,
    num_substeps: int = 4,
) -> np.ndarray:
    initial_values = np.asarray(initial_values, dtype=float)
    output_times = np.asarray(output_times, dtype=float)

    output_dt = float(output_times[1] - output_times[0])
    if not np.allclose(np.diff(output_times), output_dt, atol=1e-12, rtol=0.0):
        raise ShapeValidationError("output_times must be uniformly spaced.")

    dx = float(domain_length / initial_values.shape[-1])
    internal_dt = output_dt / float(num_substeps)
    state = _apply_two_thirds_filter(initial_values)
    rollout = np.empty((initial_values.shape[0], output_times.size, initial_values.shape[1]), dtype=float)
    rollout[:, 0, :] = state

    for time_index in range(1, output_times.size):
        for _ in range(num_substeps):
            k1 = _variable_burgers_rhs(state, diffusivity_values=diffusivity_values, dx=dx, form=form)
            k2 = _variable_burgers_rhs(
                state + 0.5 * internal_dt * k1, diffusivity_values=diffusivity_values, dx=dx, form=form
            )
            k3 = _variable_burgers_rhs(
                state + 0.5 * internal_dt * k2, diffusivity_values=diffusivity_values, dx=dx, form=form
            )
            k4 = _variable_burgers_rhs(
                state + internal_dt * k3, diffusivity_values=diffusivity_values, dx=dx, form=form
            )
            state = _apply_two_thirds_filter(state + (internal_dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4))
        rollout[:, time_index, :] = state

    return rollout


def _rollout_burgers_periodic(
    initial_values: np.ndarray,
    *,
    output_times: np.ndarray,
    diffusivity: float,
    domain_length: float = DEFAULT_DOMAIN_LENGTH,
    num_substeps: int = 4,
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
    rollout = np.empty((initial_values.shape[0], output_times.size, initial_values.shape[1]), dtype=float)
    rollout[:, 0, :] = state

    for time_index in range(1, output_times.size):
        for _ in range(num_substeps):
            k1 = _burgers_rhs(state, diffusivity=diffusivity, dx=dx)
            k2 = _burgers_rhs(state + 0.5 * internal_dt * k1, diffusivity=diffusivity, dx=dx)
            k3 = _burgers_rhs(state + 0.5 * internal_dt * k2, diffusivity=diffusivity, dx=dx)
            k4 = _burgers_rhs(state + internal_dt * k3, diffusivity=diffusivity, dx=dx)
            state = _apply_two_thirds_filter(state + (internal_dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4))
        rollout[:, time_index, :] = state

    return rollout


def generate_burgers_1d_field_batch(
    *,
    batch_size: int = 4,
    num_times: int = 33,
    num_points: int = 64,
    diffusivity: float = DEFAULT_BURGERS_DIFFUSIVITY,
    max_time: float = 0.25,
    num_modes: int = 3,
    amplitude: float = DEFAULT_BURGERS_AMPLITUDE,
    seed: int = 0,
    num_substeps: int = 4,
    diffusivity_profile: np.ndarray | Callable[[np.ndarray], np.ndarray] | None = None,
    diffusivity_form: str = DIFFUSIVITY_FORM_CONSERVATIVE,
) -> FieldBatch:
    """Generate a periodic 1-D Burgers FieldBatch.

    ``diffusivity_profile`` (v0.33d) selects a variable-coefficient diffusivity
    ``nu(x)``, given either as an array sampled on the generator's ``x`` grid or
    as a callable invoked once on that grid. Leaving it ``None`` keeps the
    constant-coefficient rollout byte-for-byte unchanged.
    """
    x = np.linspace(0.0, DEFAULT_DOMAIN_LENGTH, num_points, endpoint=False, dtype=float)
    t = np.linspace(0.0, max_time, num_times, dtype=float)
    cosine, sine = sample_burgers_mode_coefficients(
        batch_size=batch_size,
        num_modes=num_modes,
        seed=seed,
        amplitude=amplitude,
    )
    initial_values = evaluate_burgers_initial_condition(
        x=x,
        cosine_coefficients=cosine,
        sine_coefficients=sine,
    )

    # Validation fires before any numerical work.
    normalized_form = validate_equation_form(
        diffusivity_form, allowed=ALLOWED_DIFFUSIVITY_FORMS, name="diffusivity_form"
    )
    diffusivity_values, profile_tags = resolve_coefficient_profile(
        diffusivity_profile,
        x=x,
        constant_value=diffusivity,
        prefix="nu",
        name="diffusivity_profile",
        require_positive=True,
    )

    if diffusivity_values is None:
        values = _rollout_burgers_periodic(
            initial_values,
            output_times=t,
            diffusivity=diffusivity,
            domain_length=DEFAULT_DOMAIN_LENGTH,
            num_substeps=num_substeps,
        )
    else:
        values = _rollout_variable_burgers_periodic(
            initial_values,
            output_times=t,
            diffusivity_values=diffusivity_values,
            form=normalized_form,
            domain_length=DEFAULT_DOMAIN_LENGTH,
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
            "parameter_tags": {
                "nu": diffusivity,
                "nu_form": normalized_form,
                "nu_treatment_policy": NU_TREATMENT_POLICY_FIXED_BACKGROUND,
                **profile_tags,
            },
        },
        preprocess_log=[],
    )
