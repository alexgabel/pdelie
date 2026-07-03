from __future__ import annotations

import numpy as np

from pdelie._boundary import is_x_periodic
from pdelie.contracts import DerivativeBatch, FieldBatch
from pdelie.errors import ScopeValidationError


def _reshape_for_axis(values: np.ndarray, axis: int, axis_size: int) -> tuple[int, ...]:
    shape = [1] * values.ndim
    shape[axis] = axis_size
    return tuple(shape)


def _validate_max_spatial_order(max_spatial_order: object) -> int:
    if isinstance(max_spatial_order, (bool, np.bool_)) or not isinstance(max_spatial_order, (int, np.integer)):
        raise ScopeValidationError("spectral_fd max_spatial_order must be one of 1, 2, 3, or 4.")
    normalized = int(max_spatial_order)
    if normalized not in {1, 2, 3, 4}:
        raise ScopeValidationError("spectral_fd max_spatial_order must be one of 1, 2, 3, or 4.")
    return normalized


def compute_spectral_fd_derivatives(field: FieldBatch, *, max_spatial_order: int = 2) -> DerivativeBatch:
    normalized_max_spatial_order = _validate_max_spatial_order(max_spatial_order)
    field.validate()

    if field.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError("spectral_fd only supports dims ('batch', 'time', 'x', 'var') in V0.1.")
    if len(field.var_names) != 1:
        raise ScopeValidationError("spectral_fd only supports a single variable in V0.1.")
    if not is_x_periodic(field):
        raise ScopeValidationError("spectral_fd requires periodic boundary conditions in x.")

    x = field.coords["x"]
    t = field.coords["time"]
    if x.size < 4 or t.size < 3:
        raise ScopeValidationError("spectral_fd requires at least 4 x-points and 3 time points.")

    dx = float(x[1] - x[0])
    dt = float(t[1] - t[0])
    if not np.allclose(np.diff(t), dt, atol=1e-12, rtol=0.0):
        raise ScopeValidationError("spectral_fd requires a uniform time grid.")

    x_axis = field.dims.index("x")
    t_axis = field.dims.index("time")
    values = np.asarray(field.values, dtype=float)

    wavenumbers = 2.0 * np.pi * np.fft.fftfreq(x.size, d=dx).reshape(_reshape_for_axis(values, x_axis, x.size))
    spectrum = np.fft.fft(values, axis=x_axis)
    u_x = np.real(np.fft.ifft((1j * wavenumbers) * spectrum, axis=x_axis))
    u_t = np.gradient(values, dt, axis=t_axis, edge_order=2)

    derivative_arrays = {
        "u_x": np.asarray(u_x, dtype=float),
        "u_t": np.asarray(u_t, dtype=float),
    }
    if normalized_max_spatial_order >= 2:
        u_xx = np.real(np.fft.ifft(-(wavenumbers**2) * spectrum, axis=x_axis))
        derivative_arrays = {
            "u_x": np.asarray(u_x, dtype=float),
            "u_xx": np.asarray(u_xx, dtype=float),
            "u_t": np.asarray(u_t, dtype=float),
        }
    if normalized_max_spatial_order >= 3:
        u_xxx = np.real(np.fft.ifft(((1j * wavenumbers) ** 3) * spectrum, axis=x_axis))
        derivative_arrays["u_xxx"] = np.asarray(u_xxx, dtype=float)
    if normalized_max_spatial_order >= 4:
        u_xxxx = np.real(np.fft.ifft((wavenumbers**4) * spectrum, axis=x_axis))
        derivative_arrays["u_xxxx"] = np.asarray(u_xxxx, dtype=float)

    config = {
        "spatial_method": "spectral",
        "temporal_method": "finite_difference",
        "temporal_edge_order": 2,
    }
    if normalized_max_spatial_order != 2:
        config["spatial_max_order"] = normalized_max_spatial_order

    derivatives = DerivativeBatch(
        derivatives=derivative_arrays,
        backend="spectral_fd",
        config=config,
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
