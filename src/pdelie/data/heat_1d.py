from __future__ import annotations

import numpy as np

from pdelie.contracts import FieldBatch
from pdelie.errors import ShapeValidationError


DEFAULT_DOMAIN_LENGTH = 2.0 * np.pi


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
) -> FieldBatch:
    x = np.linspace(0.0, DEFAULT_DOMAIN_LENGTH, num_points, endpoint=False, dtype=float)
    t = np.linspace(0.0, max_time, num_times, dtype=float)
    cosine, sine = sample_heat_mode_coefficients(batch_size=batch_size, num_modes=num_modes, seed=seed)
    values = evaluate_heat_fourier_series(
        x=x,
        t=t,
        cosine_coefficients=cosine,
        sine_coefficients=sine,
        diffusivity=diffusivity,
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
            "parameter_tags": {"nu": diffusivity},
        },
        preprocess_log=[],
    )
