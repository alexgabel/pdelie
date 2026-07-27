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
from pdelie.errors import ShapeValidationError

DEFAULT_DOMAIN_LENGTH = 2.0 * np.pi

#: RK4 substeps per output interval on the variable-coefficient path. The
#: constant-coefficient path is analytic and takes no substeps at all.
_VARIABLE_COEFFICIENT_SUBSTEPS = 64


def _spectral_dx(values: np.ndarray, wavenumbers: np.ndarray) -> np.ndarray:
    first = np.real(np.fft.ifft(1j * wavenumbers * np.fft.fft(values, axis=-1), axis=-1))
    return np.asarray(first, dtype=float)


def _spectral_dxx(values: np.ndarray, wavenumbers: np.ndarray) -> np.ndarray:
    second = np.real(np.fft.ifft(-(wavenumbers**2) * np.fft.fft(values, axis=-1), axis=-1))
    return np.asarray(second, dtype=float)


def _variable_heat_rhs(
    values: np.ndarray,
    diffusivity: np.ndarray,
    wavenumbers: np.ndarray,
    *,
    form: str,
) -> np.ndarray:
    """Variable-coefficient heat operator in the requested equation form.

    * ``conservative_divergence``: ``d/dx( nu(x) du/dx )``. Preserves the spatial
      integral of ``u`` for periodic data at any ``nu(x)``.
    * ``nonconservative_nu_uxx``: ``nu(x) * u_xx``. Does not.

    The two coincide analytically for constant ``nu`` and differ for any
    ``nu(x)``, which is why the choice is recorded as
    ``parameter_tags["nu_form"]`` -- the v0.34a variable-coefficient residual
    evaluators dispatch on it rather than guessing.

    The constant-coefficient residual evaluators consume ``nu * u_xx`` with a
    scalar ``nu``, so a variable-coefficient field is a documented mismatch for
    them under either form; that mismatch is the v0.33d admissibility crash test.
    """
    if form == DIFFUSIVITY_FORM_NONCONSERVATIVE:
        return np.asarray(diffusivity * _spectral_dxx(values, wavenumbers), dtype=float)
    return _spectral_dx(diffusivity * _spectral_dx(values, wavenumbers), wavenumbers)


def _rollout_variable_heat_periodic(
    initial_values: np.ndarray,
    *,
    output_times: np.ndarray,
    diffusivity_values: np.ndarray,
    domain_length: float,
    form: str,
    num_substeps: int = _VARIABLE_COEFFICIENT_SUBSTEPS,
) -> np.ndarray:
    num_points = initial_values.shape[-1]
    wavenumbers = 2.0 * np.pi * np.fft.fftfreq(num_points, d=domain_length / num_points)

    output_dt = float(output_times[1] - output_times[0])
    if not np.allclose(np.diff(output_times), output_dt, atol=1e-12, rtol=0.0):
        raise ShapeValidationError("output_times must be uniformly spaced.")
    internal_dt = output_dt / float(num_substeps)

    state = np.asarray(initial_values, dtype=float)
    rollout = np.empty((state.shape[0], output_times.size, num_points), dtype=float)
    rollout[:, 0, :] = state

    for time_index in range(1, output_times.size):
        for _ in range(num_substeps):
            k1 = _variable_heat_rhs(state, diffusivity_values, wavenumbers, form=form)
            k2 = _variable_heat_rhs(state + 0.5 * internal_dt * k1, diffusivity_values, wavenumbers, form=form)
            k3 = _variable_heat_rhs(state + 0.5 * internal_dt * k2, diffusivity_values, wavenumbers, form=form)
            k4 = _variable_heat_rhs(state + internal_dt * k3, diffusivity_values, wavenumbers, form=form)
            state = state + (internal_dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        rollout[:, time_index, :] = state

    return rollout


def sample_heat_mode_coefficients(
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


def evaluate_heat_fourier_series(
    *,
    x: np.ndarray,
    t: np.ndarray,
    cosine_coefficients: np.ndarray,
    sine_coefficients: np.ndarray,
    diffusivity: float,
) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    t = np.asarray(t, dtype=float)
    cosine_coefficients = np.asarray(cosine_coefficients, dtype=float)
    sine_coefficients = np.asarray(sine_coefficients, dtype=float)

    if cosine_coefficients.shape != sine_coefficients.shape:
        raise ShapeValidationError("cosine_coefficients and sine_coefficients must match.")
    if cosine_coefficients.ndim != 2:
        raise ShapeValidationError("Coefficient arrays must have shape (batch, num_modes).")

    modes = np.arange(1, cosine_coefficients.shape[1] + 1, dtype=float)
    spatial_cos = np.cos(np.outer(modes, x))
    spatial_sin = np.sin(np.outer(modes, x))
    temporal_decay = np.exp(-diffusivity * np.square(modes)[None, :] * t[:, None])

    batch_cos = cosine_coefficients[:, None, :, None]
    batch_sin = sine_coefficients[:, None, :, None]
    temporal = temporal_decay[None, :, :, None]
    spatial = spatial_cos[None, None, :, :] * batch_cos + spatial_sin[None, None, :, :] * batch_sin
    return np.sum(temporal * spatial, axis=2)


def generate_heat_1d_field_batch(
    *,
    batch_size: int = 4,
    num_times: int = 17,
    num_points: int = 64,
    diffusivity: float = 0.1,
    max_time: float = 0.6,
    num_modes: int = 3,
    seed: int = 0,
    diffusivity_profile: np.ndarray | Callable[[np.ndarray], np.ndarray] | None = None,
    diffusivity_form: str = DIFFUSIVITY_FORM_CONSERVATIVE,
) -> FieldBatch:
    """Generate a periodic 1-D heat FieldBatch.

    ``diffusivity_profile`` (v0.33d) selects a variable-coefficient diffusivity
    ``nu(x)``, given either as an array sampled on the generator's ``x`` grid or
    as a callable invoked once on that grid. Leaving it ``None`` keeps the
    constant-coefficient analytic Fourier path byte-for-byte unchanged.

    The variable-coefficient path has no closed form, so it integrates with RK4
    from the same initial condition the analytic path produces at ``t=0``.
    ``diffusivity_form`` selects the operator: ``"conservative_divergence"``
    (default) integrates ``d/dx( nu(x) du/dx )``, ``"nonconservative_nu_uxx"``
    integrates ``nu(x) * u_xx``. The two coincide for constant ``nu``.

    Profile provenance, the equation form (``nu_form``), and the coefficient
    treatment policy (``nu_treatment_policy``) are recorded in
    ``metadata["parameter_tags"]``.
    """
    x = np.linspace(0.0, DEFAULT_DOMAIN_LENGTH, num_points, endpoint=False, dtype=float)
    t = np.linspace(0.0, max_time, num_times, dtype=float)
    cosine, sine = sample_heat_mode_coefficients(batch_size=batch_size, num_modes=num_modes, seed=seed)

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
        # Constant-coefficient path: unchanged analytic Fourier series.
        values = evaluate_heat_fourier_series(
            x=x,
            t=t,
            cosine_coefficients=cosine,
            sine_coefficients=sine,
            diffusivity=diffusivity,
        )
    else:
        initial_values = evaluate_heat_fourier_series(
            x=x,
            t=t[:1],
            cosine_coefficients=cosine,
            sine_coefficients=sine,
            diffusivity=diffusivity,
        )[:, 0, :]
        values = _rollout_variable_heat_periodic(
            initial_values,
            output_times=t,
            diffusivity_values=diffusivity_values,
            domain_length=DEFAULT_DOMAIN_LENGTH,
            form=normalized_form,
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
