from __future__ import annotations

import numpy as np

from pdelie.contracts import DerivativeBatch, FieldBatch
from pdelie.errors import ScopeValidationError


def _reshape_for_axis(values: np.ndarray, axis: int, axis_size: int) -> tuple[int, ...]:
    shape = [1] * values.ndim
    shape[axis] = axis_size
    return tuple(shape)


def compute_spectral_fd_derivatives(field: FieldBatch) -> DerivativeBatch:
    field.validate()

    if field.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError("spectral_fd only supports dims ('batch', 'time', 'x', 'var') in V0.1.")
    if len(field.var_names) != 1:
        raise ScopeValidationError("spectral_fd only supports a single variable in V0.1.")
    if field.metadata["boundary_conditions"].get("x") != "periodic":
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
    u_xx = np.real(np.fft.ifft(-(wavenumbers**2) * spectrum, axis=x_axis))
    u_t = np.gradient(values, dt, axis=t_axis, edge_order=2)

    derivatives = DerivativeBatch(
        derivatives={
            "u_x": np.asarray(u_x, dtype=float),
            "u_xx": np.asarray(u_xx, dtype=float),
            "u_t": np.asarray(u_t, dtype=float),
        },
        backend="spectral_fd",
        config={
            "spatial_method": "spectral",
            "temporal_method": "finite_difference",
            "temporal_edge_order": 2,
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
