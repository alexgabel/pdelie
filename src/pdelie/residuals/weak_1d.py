from __future__ import annotations

from collections.abc import Callable, Mapping

import numpy as np

from pdelie._boundary import is_x_periodic
from pdelie.contracts import FieldBatch
from pdelie.errors import SchemaValidationError, ScopeValidationError

_COORDINATE_UNIFORM_ABS_TOL = 1e-12
_TIME_WINDOW_SIZE = 5
_X_WINDOW_SIZE = 9
_TIME_HALF_WIDTH = 2
_X_HALF_WIDTH = 4
_TIME_STRIDE = 1
_X_STRIDE = 1
_TIME_OFFSETS = np.arange(-_TIME_HALF_WIDTH, _TIME_HALF_WIDTH + 1, dtype=int)
_X_OFFSETS = np.arange(-_X_HALF_WIDTH, _X_HALF_WIDTH + 1, dtype=int)
_METHOD_FAMILY = "local_separable_quartic_bump_trapezoid_v1"
_QUADRATURE = "composite_tensor_product_trapezoidal_native_window"
_TEST_FUNCTION = "separable_quartic_bump_beta"


def _beta(values: np.ndarray) -> np.ndarray:
    result = np.zeros_like(values, dtype=float)
    supported = np.abs(values) <= 1.0
    result[supported] = np.square(1.0 - np.square(values[supported]))
    return result


def _beta_prime(values: np.ndarray) -> np.ndarray:
    result = np.zeros_like(values, dtype=float)
    supported = np.abs(values) <= 1.0
    result[supported] = -4.0 * values[supported] * (1.0 - np.square(values[supported]))
    return result


def _beta_second(values: np.ndarray) -> np.ndarray:
    result = np.zeros_like(values, dtype=float)
    supported = np.abs(values) <= 1.0
    result[supported] = -4.0 + 12.0 * np.square(values[supported])
    return result


def _validate_field_input(field: object, *, function_name: str) -> FieldBatch:
    if not isinstance(field, FieldBatch):
        raise SchemaValidationError(f"{function_name} requires a FieldBatch input.")
    field.validate()
    return field


def _validate_strict_uniform_increasing_coordinate(
    coord: np.ndarray,
    *,
    name: str,
    function_name: str,
) -> float:
    if coord.ndim != 1:
        raise ScopeValidationError(f"{function_name} requires one-dimensional {name} coordinates.")
    if coord.size < 2:
        raise ScopeValidationError(f"{function_name} requires at least two {name} coordinates.")
    if not np.all(np.isfinite(coord)):
        raise ScopeValidationError(f"{function_name} requires finite {name} coordinates.")

    deltas = np.diff(coord)
    if not np.all(deltas > 0.0):
        raise ScopeValidationError(f"{function_name} requires strictly increasing {name} coordinates.")

    spacing = float(deltas[0])
    if not np.allclose(deltas, spacing, atol=_COORDINATE_UNIFORM_ABS_TOL, rtol=0.0):
        raise ScopeValidationError(f"{function_name} requires uniformly spaced {name} coordinates.")
    return spacing


def _validate_supported_field(field: FieldBatch, *, function_name: str) -> tuple[float, float]:
    if field.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError(
            f"{function_name} only supports dims ('batch', 'time', 'x', 'var') in V0.8 Milestone 2."
        )
    if len(field.var_names) != 1:
        raise ScopeValidationError(f"{function_name} only supports a single scalar variable in V0.8 Milestone 2.")
    if field.mask is not None:
        raise ScopeValidationError(f"{function_name} does not support masked fields in V0.8 Milestone 2.")

    values = np.asarray(field.values, dtype=float)
    if not np.all(np.isfinite(values)):
        raise ScopeValidationError(f"{function_name} requires finite field values in V0.8 Milestone 2.")
    if values.shape[field.dims.index("batch")] < 1:
        raise SchemaValidationError(f"{function_name} requires at least one batch sample.")
    if values.shape[field.dims.index("time")] < _TIME_WINDOW_SIZE:
        raise ScopeValidationError(
            f"{function_name} requires at least {_TIME_WINDOW_SIZE} time points in V0.8 Milestone 2."
        )
    if values.shape[field.dims.index("x")] < _X_WINDOW_SIZE:
        raise ScopeValidationError(
            f"{function_name} requires at least {_X_WINDOW_SIZE} x-points in V0.8 Milestone 2."
        )

    time = np.asarray(field.coords["time"], dtype=float)
    x = np.asarray(field.coords["x"], dtype=float)
    dt = _validate_strict_uniform_increasing_coordinate(time, name="time", function_name=function_name)
    dx = _validate_strict_uniform_increasing_coordinate(x, name="x", function_name=function_name)

    if not is_x_periodic(field):
        raise ScopeValidationError(f"{function_name} requires periodic boundary conditions in x.")
    return dt, dx


def _validate_finite_scalar(value: object, *, name: str, function_name: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise SchemaValidationError(f"{function_name} requires {name} to be a finite scalar.")
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{function_name} requires {name} to be a finite scalar.") from exc
    if not np.isfinite(normalized):
        raise SchemaValidationError(f"{function_name} requires {name} to be a finite scalar.")
    return normalized


def _resolve_diffusivity(field: FieldBatch, diffusivity: float | None, *, function_name: str) -> float:
    if diffusivity is not None:
        return _validate_finite_scalar(diffusivity, name="diffusivity", function_name=function_name)

    parameter_tags = field.metadata.get("parameter_tags")
    if not isinstance(parameter_tags, Mapping):
        raise SchemaValidationError(
            f"{function_name} requires field.metadata['parameter_tags']['nu'] when diffusivity is not provided."
        )
    nu = parameter_tags.get("nu")
    if nu is None:
        raise SchemaValidationError(
            f"{function_name} requires field.metadata['parameter_tags']['nu'] when diffusivity is not provided."
        )
    try:
        normalized = float(nu)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(
            f"{function_name} requires field.metadata['parameter_tags']['nu'] to be castable to float."
        ) from exc
    if not np.isfinite(normalized):
        raise SchemaValidationError(
            f"{function_name} requires field.metadata['parameter_tags']['nu'] to be a finite scalar."
        )
    return normalized


def _trapezoid_weights(size: int) -> np.ndarray:
    weights = np.ones(size, dtype=float)
    weights[0] = 0.5
    weights[-1] = 0.5
    return weights


def _window_centers(time: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return time[_TIME_HALF_WIDTH : time.shape[0] - _TIME_HALF_WIDTH].copy(), x.copy()


def _compute_base_kernels(*, dt: float, dx: float) -> dict[str, np.ndarray]:
    h_t = float(_TIME_HALF_WIDTH * dt)
    h_x = float(_X_HALF_WIDTH * dx)

    s_t = _TIME_OFFSETS.astype(float) / float(_TIME_HALF_WIDTH)
    s_x = _X_OFFSETS.astype(float) / float(_X_HALF_WIDTH)

    beta_t = _beta(s_t)
    beta_t_prime = _beta_prime(s_t)
    beta_x = _beta(s_x)
    beta_x_prime = _beta_prime(s_x)
    beta_x_second = _beta_second(s_x)

    phi_t = (beta_t_prime[:, None] * beta_x[None, :]) / h_t
    phi_x = (beta_t[:, None] * beta_x_prime[None, :]) / h_x
    phi_xx = (beta_t[:, None] * beta_x_second[None, :]) / (h_x * h_x)

    weights = np.outer(_trapezoid_weights(_TIME_WINDOW_SIZE), _trapezoid_weights(_X_WINDOW_SIZE)) * (dt * dx)

    return {
        "phi_t": phi_t,
        "phi_x": phi_x,
        "phi_xx": phi_xx,
        "weights": weights,
    }


def _compute_window_residuals(
    values: np.ndarray,
    *,
    linear_kernel: np.ndarray,
    nonlinear_kernel: np.ndarray | None = None,
) -> np.ndarray:
    batch_size, num_times, num_points = values.shape
    num_time_windows = num_times - 2 * _TIME_HALF_WIDTH
    x_index_windows = (np.arange(num_points, dtype=int)[:, None] + _X_OFFSETS[None, :]) % num_points
    residuals = np.empty((batch_size, num_time_windows, num_points), dtype=float)

    for output_time_index, time_center in enumerate(range(_TIME_HALF_WIDTH, num_times - _TIME_HALF_WIDTH, _TIME_STRIDE)):
        time_indices = time_center + _TIME_OFFSETS
        time_slice = values[:, time_indices, :]
        for x_center in range(0, num_points, _X_STRIDE):
            window = time_slice[:, :, x_index_windows[x_center]]
            residual = np.sum(window * linear_kernel[None, :, :], axis=(1, 2))
            if nonlinear_kernel is not None:
                residual = residual + np.sum(np.square(window) * nonlinear_kernel[None, :, :], axis=(1, 2))
            residuals[:, output_time_index, x_center] = residual

    return residuals[..., None]


def _make_diagnostics(
    *,
    strong_form: str,
    weak_form: str,
    diffusivity: float,
    num_time_windows: int,
    num_x_windows: int,
    window_residuals: np.ndarray,
) -> dict[str, object]:
    return {
        "strong_form": strong_form,
        "weak_form": weak_form,
        "diffusivity": float(diffusivity),
        "time_window_size": _TIME_WINDOW_SIZE,
        "x_window_size": _X_WINDOW_SIZE,
        "time_window_stride": _TIME_STRIDE,
        "x_window_stride": _X_STRIDE,
        "quadrature": _QUADRATURE,
        "test_function": _TEST_FUNCTION,
        "periodic_x_wrapping": True,
        "window_counts": {"time": int(num_time_windows), "x": int(num_x_windows)},
        "max_abs_residual": float(np.max(np.abs(window_residuals))),
        "l2_residual": float(np.linalg.norm(window_residuals)),
    }


def _evaluate_weak_report(
    field: FieldBatch,
    *,
    diffusivity: float | None,
    function_name: str,
    equation: str,
    equation_form: str,
    strong_form: str,
    weak_form: str,
    nonlinear_kernel_factory: Callable[[dict[str, np.ndarray]], np.ndarray | None],
) -> dict[str, object]:
    field = _validate_field_input(field, function_name=function_name)
    dt, dx = _validate_supported_field(field, function_name=function_name)
    nu = _resolve_diffusivity(field, diffusivity, function_name=function_name)

    time = np.asarray(field.coords["time"], dtype=float)
    x = np.asarray(field.coords["x"], dtype=float)
    kernels = _compute_base_kernels(dt=dt, dx=dx)
    linear_kernel = kernels["weights"] * (-kernels["phi_t"] - nu * kernels["phi_xx"])
    nonlinear_kernel = nonlinear_kernel_factory(kernels)
    values = np.asarray(field.values[..., 0], dtype=float)
    window_residuals = _compute_window_residuals(values, linear_kernel=linear_kernel, nonlinear_kernel=nonlinear_kernel)
    time_window_centers, x_window_centers = _window_centers(time, x)

    return {
        "equation": equation,
        "equation_form": equation_form,
        "method_family": _METHOD_FAMILY,
        "window_residuals": window_residuals,
        "time_window_centers": time_window_centers,
        "x_window_centers": x_window_centers,
        "normalization": "none",
        "diagnostics": _make_diagnostics(
            strong_form=strong_form,
            weak_form=weak_form,
            diffusivity=nu,
            num_time_windows=time_window_centers.shape[0],
            num_x_windows=x_window_centers.shape[0],
            window_residuals=window_residuals,
        ),
    }


def evaluate_weak_heat_residual(
    field: FieldBatch,
    *,
    diffusivity: float | None = None,
) -> dict[str, object]:
    return _evaluate_weak_report(
        field,
        diffusivity=diffusivity,
        function_name="evaluate_weak_heat_residual",
        equation="heat_1d",
        equation_form="nonconservative",
        strong_form="u_t - nu u_xx = 0",
        weak_form="-u phi_t - nu u phi_xx",
        nonlinear_kernel_factory=lambda kernels: None,
    )


def evaluate_weak_burgers_residual(
    field: FieldBatch,
    *,
    diffusivity: float | None = None,
) -> dict[str, object]:
    return _evaluate_weak_report(
        field,
        diffusivity=diffusivity,
        function_name="evaluate_weak_burgers_residual",
        equation="burgers_1d",
        equation_form="conservative",
        strong_form="u_t + 1/2 (u^2)_x - nu u_xx = 0",
        weak_form="-u phi_t - 1/2 u^2 phi_x - nu u phi_xx",
        nonlinear_kernel_factory=lambda kernels: kernels["weights"] * (-0.5 * kernels["phi_x"]),
    )


__all__ = ["evaluate_weak_burgers_residual", "evaluate_weak_heat_residual"]
