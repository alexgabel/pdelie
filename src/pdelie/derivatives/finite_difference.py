"""Nonperiodic low-order finite-difference derivative backend.

v0.30c v1 surface: supports `u_t`, `u_x`, and `u_xx` only on scalar 1D
nonperiodic uniform grids. Higher-order spatial derivatives on nonperiodic
data are intentionally not part of the stable v0.30 surface — repeated
``np.gradient`` propagates boundary error and quickly degrades by ``u_xxx``
on typical 64-point grids. See `docs/design/DERIVATIVE_BACKEND_POLICY.md`.

This backend never silently auto-routes periodic data. Periodic users must
go through ``compute_spectral_fd_derivatives``; the
``compute_derivatives(backend="auto")`` dispatcher in
``pdelie.derivatives.__init__`` records which backend it chose and why.
"""
from __future__ import annotations

from typing import Any

import numpy as np

from pdelie._boundary import get_x_boundary_type
from pdelie.contracts import DerivativeBatch, FieldBatch
from pdelie.errors import ScopeValidationError

_SUPPORTED_X_BOUNDARY_TYPES = frozenset({"dirichlet", "neumann", "open_unknown"})
_RECOMMENDED_RESIDUAL_DOMAIN_POLICY = "interior_only"
_RECOMMENDED_BOUNDARY_TRIM_WIDTH = 4


def _validate_max_spatial_order(max_spatial_order: object) -> int:
    if isinstance(max_spatial_order, (bool, np.bool_)) or not isinstance(
        max_spatial_order, (int, np.integer)
    ):
        raise ScopeValidationError(
            "compute_finite_difference_derivatives max_spatial_order must be 1 or 2 in v0.30c."
        )
    normalized = int(max_spatial_order)
    if normalized not in {1, 2}:
        raise ScopeValidationError(
            "compute_finite_difference_derivatives max_spatial_order must be 1 or 2 in v0.30c. "
            "Higher orders on nonperiodic data are deferred."
        )
    return normalized


def compute_finite_difference_derivatives(
    field: FieldBatch,
    *,
    max_spatial_order: int = 2,
) -> DerivativeBatch:
    """Compute `u_t`, `u_x`, and (optionally) `u_xx` on a scalar 1D nonperiodic field.

    Uses ``numpy.gradient`` with ``edge_order=2`` for both axes. Reject periodic data —
    use ``compute_spectral_fd_derivatives`` for that path.

    Field requirements:
    - dims ``("batch", "time", "x", "var")``
    - single scalar variable
    - uniform x and uniform time, each with at least 3 points (edge_order=2 needs N>=3)
    - boundary type ``dirichlet``, ``neumann``, or ``open_unknown``
    """
    normalized_max_spatial_order = _validate_max_spatial_order(max_spatial_order)
    field.validate()

    if field.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError(
            "compute_finite_difference_derivatives only supports dims ('batch', 'time', 'x', 'var') in v0.30c."
        )
    if len(field.var_names) != 1:
        raise ScopeValidationError(
            "compute_finite_difference_derivatives only supports a single scalar variable in v0.30c."
        )

    boundary_type = get_x_boundary_type(field)
    if boundary_type == "periodic":
        raise ScopeValidationError(
            "compute_finite_difference_derivatives rejects periodic data. "
            "Use compute_spectral_fd_derivatives or compute_derivatives(backend='auto') instead."
        )
    if boundary_type not in _SUPPORTED_X_BOUNDARY_TYPES:
        raise ScopeValidationError(
            f"compute_finite_difference_derivatives requires one of {sorted(_SUPPORTED_X_BOUNDARY_TYPES)}; "
            f"got {boundary_type!r}."
        )

    x = field.coords["x"]
    t = field.coords["time"]
    if x.size < 3:
        raise ScopeValidationError(
            "compute_finite_difference_derivatives requires at least 3 x-points for edge_order=2."
        )
    if t.size < 3:
        raise ScopeValidationError(
            "compute_finite_difference_derivatives requires at least 3 time points for edge_order=2."
        )

    dx = float(x[1] - x[0])
    dt = float(t[1] - t[0])
    if not np.allclose(np.diff(x), dx, atol=1e-12, rtol=0.0):
        raise ScopeValidationError(
            "compute_finite_difference_derivatives requires a uniform x grid."
        )
    if not np.allclose(np.diff(t), dt, atol=1e-12, rtol=0.0):
        raise ScopeValidationError(
            "compute_finite_difference_derivatives requires a uniform time grid."
        )
    if dx <= 0.0 or dt <= 0.0:
        raise ScopeValidationError(
            "compute_finite_difference_derivatives requires strictly increasing x and time coordinates."
        )

    x_axis = field.dims.index("x")
    t_axis = field.dims.index("time")
    values = np.asarray(field.values, dtype=float)

    u_t = np.gradient(values, dt, axis=t_axis, edge_order=2)
    u_x = np.gradient(values, dx, axis=x_axis, edge_order=2)

    derivative_arrays: dict[str, np.ndarray[Any, Any]] = {
        "u_t": np.asarray(u_t, dtype=float),
        "u_x": np.asarray(u_x, dtype=float),
    }
    if normalized_max_spatial_order >= 2:
        u_xx = np.gradient(u_x, dx, axis=x_axis, edge_order=2)
        derivative_arrays["u_xx"] = np.asarray(u_xx, dtype=float)

    config: dict[str, object] = {
        "spatial_method": "finite_difference_centered",
        "temporal_method": "finite_difference",
        "stencil_edge_order": 2,
        "spatial_max_order": int(normalized_max_spatial_order),
        "boundary_handling": str(boundary_type),
        "backend_selected_by_boundary_condition": False,
        "backend_selection_reason": None,
        "recommended_residual_domain_policy": _RECOMMENDED_RESIDUAL_DOMAIN_POLICY,
        "recommended_boundary_trim_width": int(_RECOMMENDED_BOUNDARY_TRIM_WIDTH),
    }

    derivatives = DerivativeBatch(
        derivatives=derivative_arrays,
        backend="finite_difference",
        config=config,
        boundary_assumptions=f"{boundary_type} in x; finite differences in time",
        diagnostics={
            "dx": float(dx),
            "dt": float(dt),
            "x_points": int(x.size),
            "time_points": int(t.size),
        },
    )
    derivatives.validate_against(field)
    return derivatives


__all__ = ["compute_finite_difference_derivatives"]
