from __future__ import annotations

import numpy as np

from pdelie import DerivativeBatch, FieldBatch, ResidualBatch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.errors import SchemaValidationError, ScopeValidationError, ShapeValidationError
from pdelie.residuals.base import ResidualEvaluator


KS_FEASIBILITY_CONFIG: dict[str, object] = {
    "batch_size": 5,
    "num_times": 33,
    "num_points": 128,
    "max_time": 0.2,
    "num_modes": 6,
    "amplitude": 0.08,
    "seed": 11101,
    "num_substeps": 8,
    "domain_length": 32.0 * np.pi,
    "equation": "u_t + u*u_x + u_xx + u_xxxx = 0",
    "rollout": "ETDRK4",
    "nonlinear_form": "conservative_spectral_half_d_x_u_squared",
}
_REQUIRED_KS_DERIVATIVES = ("u_t", "u_x", "u_xx", "u_xxxx")


def _reshape_last_axis(values: np.ndarray) -> tuple[int, ...]:
    shape = [1] * values.ndim
    shape[-1] = values.shape[-1]
    return tuple(shape)


def _two_thirds_mask(num_points: int) -> np.ndarray:
    mode_numbers = np.fft.fftfreq(num_points) * num_points
    return np.abs(mode_numbers) <= (num_points / 3.0)


def apply_two_thirds_filter(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    mask = _two_thirds_mask(values.shape[-1]).reshape(_reshape_last_axis(values))
    spectrum = np.fft.fft(values, axis=-1)
    return np.real(np.fft.ifft(spectrum * mask, axis=-1))


def sample_ks_mode_coefficients(
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


def evaluate_ks_fourier_series(
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
    values = np.sum(
        cosine_coefficients[:, :, None] * spatial_cos[None, :, :]
        + sine_coefficients[:, :, None] * spatial_sin[None, :, :],
        axis=1,
    )
    return apply_two_thirds_filter(values)


def _etdrk4_coefficients(linear_operator: np.ndarray, *, dt: float) -> tuple[np.ndarray, ...]:
    scaled = dt * linear_operator
    exp_full = np.exp(scaled)
    exp_half = np.exp(scaled / 2.0)
    roots = np.exp(1j * np.pi * (np.arange(1, 33, dtype=float) - 0.5) / 32.0)
    contour = scaled[:, None] + roots[None, :]

    q = dt * np.mean((np.exp(contour / 2.0) - 1.0) / contour, axis=1).real
    f1 = dt * np.mean(
        (-4.0 - contour + np.exp(contour) * (4.0 - 3.0 * contour + contour**2)) / contour**3,
        axis=1,
    ).real
    f2 = dt * np.mean((2.0 + contour + np.exp(contour) * (-2.0 + contour)) / contour**3, axis=1).real
    f3 = dt * np.mean(
        (-4.0 - 3.0 * contour - contour**2 + np.exp(contour) * (4.0 - contour)) / contour**3,
        axis=1,
    ).real
    return exp_full, exp_half, q, f1, f2, f3


def _rollout_ks_etdrk4(
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

    num_points = initial_values.shape[-1]
    wavenumbers = 2.0 * np.pi * np.fft.fftfreq(num_points, d=float(domain_length) / num_points)
    dealias_mask = _two_thirds_mask(num_points)
    linear_operator = wavenumbers**2 - wavenumbers**4
    internal_dt = output_dt / float(num_substeps)
    exp_full, exp_half, q, f1, f2, f3 = _etdrk4_coefficients(linear_operator, dt=internal_dt)
    ik = 1j * wavenumbers

    def nonlinear_term(spectrum: np.ndarray) -> np.ndarray:
        values = np.fft.ifft(spectrum, axis=-1).real
        nonlinear_values = apply_two_thirds_filter(values * values)
        return -0.5 * ik * np.fft.fft(nonlinear_values, axis=-1) * dealias_mask

    state = apply_two_thirds_filter(initial_values)
    spectrum = np.fft.fft(state, axis=-1) * dealias_mask
    zero_mode = spectrum[:, 0].copy()
    rollout = np.empty((initial_values.shape[0], output_times.size, num_points), dtype=float)
    rollout[:, 0, :] = np.fft.ifft(spectrum, axis=-1).real

    for time_index in range(1, output_times.size):
        for _ in range(num_substeps):
            n1 = nonlinear_term(spectrum)
            a = exp_half * spectrum + q * n1
            n2 = nonlinear_term(a)
            b = exp_half * spectrum + q * n2
            n3 = nonlinear_term(b)
            c = exp_half * a + q * (2.0 * n3 - n1)
            n4 = nonlinear_term(c)
            spectrum = exp_full * spectrum + f1 * n1 + 2.0 * f2 * (n2 + n3) + f3 * n4
            spectrum *= dealias_mask
            spectrum[:, 0] = zero_mode
        rollout[:, time_index, :] = np.fft.ifft(spectrum, axis=-1).real

    return rollout


def generate_ks_feasibility_field_batch(
    *,
    batch_size: int = int(KS_FEASIBILITY_CONFIG["batch_size"]),
    num_times: int = int(KS_FEASIBILITY_CONFIG["num_times"]),
    num_points: int = int(KS_FEASIBILITY_CONFIG["num_points"]),
    max_time: float = float(KS_FEASIBILITY_CONFIG["max_time"]),
    num_modes: int = int(KS_FEASIBILITY_CONFIG["num_modes"]),
    amplitude: float = float(KS_FEASIBILITY_CONFIG["amplitude"]),
    seed: int = int(KS_FEASIBILITY_CONFIG["seed"]),
    num_substeps: int = int(KS_FEASIBILITY_CONFIG["num_substeps"]),
    domain_length: float = float(KS_FEASIBILITY_CONFIG["domain_length"]),
) -> FieldBatch:
    x = np.linspace(0.0, domain_length, num_points, endpoint=False, dtype=float)
    t = np.linspace(0.0, max_time, num_times, dtype=float)
    cosine, sine = sample_ks_mode_coefficients(
        batch_size=batch_size,
        num_modes=num_modes,
        seed=seed,
        amplitude=amplitude,
    )
    initial_values = evaluate_ks_fourier_series(
        x=x,
        domain_length=domain_length,
        cosine_coefficients=cosine,
        sine_coefficients=sine,
    )
    values = _rollout_ks_etdrk4(
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
            "parameter_tags": {"equation": "ks_normalized"},
        },
        preprocess_log=[],
    )


def compute_mass(field: FieldBatch) -> np.ndarray:
    values = np.asarray(field.values[..., 0], dtype=float)
    dx = float(field.coords["x"][1] - field.coords["x"][0])
    return dx * np.sum(values, axis=-1)


def compute_l2_norm(field: FieldBatch) -> np.ndarray:
    values = np.asarray(field.values[..., 0], dtype=float)
    dx = float(field.coords["x"][1] - field.coords["x"][0])
    return np.sqrt(dx * np.sum(values**2, axis=-1))


def _validate_ks_feasibility_field(field: FieldBatch) -> None:
    field.validate()

    if field.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError("KSFeasibilityResidualEvaluator only supports dims ('batch', 'time', 'x', 'var').")
    if len(field.var_names) != 1 or field.values.shape[-1] != 1:
        raise ScopeValidationError("KSFeasibilityResidualEvaluator only supports scalar FieldBatch inputs.")
    if field.mask is not None:
        raise ScopeValidationError("KSFeasibilityResidualEvaluator does not support masked fields.")
    if not np.all(np.isfinite(field.values)):
        raise ScopeValidationError("KSFeasibilityResidualEvaluator requires finite field values.")
    if field.metadata["boundary_conditions"].get("x") != "periodic":
        raise ScopeValidationError("KSFeasibilityResidualEvaluator requires periodic boundary conditions in x.")

    parameter_tags = field.metadata.get("parameter_tags")
    if not isinstance(parameter_tags, dict):
        raise SchemaValidationError("KSFeasibilityResidualEvaluator requires field.metadata['parameter_tags'] to be a mapping.")
    if parameter_tags.get("equation") != "ks_normalized":
        raise ScopeValidationError(
            "KSFeasibilityResidualEvaluator requires field.metadata['parameter_tags']['equation'] == 'ks_normalized'."
        )


class KSFeasibilityResidualEvaluator(ResidualEvaluator):
    def evaluate(
        self,
        field: FieldBatch,
        derivatives: DerivativeBatch | None = None,
    ) -> ResidualBatch:
        _validate_ks_feasibility_field(field)
        if derivatives is None:
            derivatives = compute_spectral_fd_derivatives(field, max_spatial_order=4)
        derivatives.validate_against(field)

        for name in _REQUIRED_KS_DERIVATIVES:
            if name not in derivatives.derivatives:
                raise SchemaValidationError(f"KSFeasibilityResidualEvaluator requires derivative '{name}'.")

        values = np.asarray(field.values, dtype=float)
        residual = (
            derivatives.derivatives["u_t"]
            + values * derivatives.derivatives["u_x"]
            + derivatives.derivatives["u_xx"]
            + derivatives.derivatives["u_xxxx"]
        )
        batch = ResidualBatch(
            residual=residual,
            definition_type="analytic",
            normalization="none",
            diagnostics={
                "equation": KS_FEASIBILITY_CONFIG["equation"],
                "backend": derivatives.backend,
                "max_abs_residual": float(np.max(np.abs(residual))),
                "rms_residual": float(np.sqrt(np.mean(np.square(residual)))),
            },
        )
        batch.validate_against(field)
        return batch
