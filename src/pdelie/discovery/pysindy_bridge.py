"""Runtime-only bridge helpers for narrow backend-specific downstream workflows.

This module intentionally does not define PDELie canonical objects.
The flattened trajectory format exposed here is a PySINDy bridge format only,
not PDELie's canonical downstream or PDE-discovery representation.
"""
from __future__ import annotations

import importlib

import numpy as np

from pdelie._boundary import is_x_periodic
from pdelie.contracts import FieldBatch
from pdelie.errors import ScopeValidationError


def _validate_supported_field(field: FieldBatch) -> None:
    if field.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError(
            "to_pysindy_trajectories only supports dims ('batch', 'time', 'x', 'var') in V0.3 Milestone 2."
        )
    if len(field.var_names) != 1:
        raise ScopeValidationError(
            "to_pysindy_trajectories only supports a single scalar variable in V0.3 Milestone 2."
        )
    if not is_x_periodic(field):
        raise ScopeValidationError("to_pysindy_trajectories requires periodic boundary conditions in x.")


def _require_pysindy():
    try:
        return importlib.import_module("pysindy")
    except (ModuleNotFoundError, ImportError, ValueError) as exc:
        raise ImportError(
            "PySINDy is required for the runtime downstream smoke helper. "
            "Install pdelie[downstream] or pdelie[test]."
        ) from exc


def _fit_pysindy_smoke(
    trajectory: np.ndarray,
    time_values: np.ndarray,
    feature_names: list[str],
):
    """Minimal PySINDy 2.1.x fit smoke.

    v0.32a migration: ``SINDy.__init__`` in 2.x no longer accepts
    ``feature_names``. The feature names live on ``SINDy.fit(...)``
    instead.
    """
    pysindy = _require_pysindy()
    model = pysindy.SINDy()
    model.fit(
        np.asarray(trajectory, dtype=float),
        t=np.asarray(time_values, dtype=float),
        feature_names=list(feature_names),
    )
    return model, np.asarray(model.coefficients(), dtype=float)


def to_pysindy_trajectories(field: FieldBatch) -> tuple[list[np.ndarray], np.ndarray, list[str]]:
    field.validate()
    _validate_supported_field(field)

    num_times = field.values.shape[field.dims.index("time")]
    num_points = field.values.shape[field.dims.index("x")]
    trajectories = [
        np.asarray(field.values[batch_index], dtype=float).reshape(num_times, -1).copy()
        for batch_index in range(field.values.shape[0])
    ]
    time_values = np.asarray(field.coords["time"], dtype=float).copy()
    feature_names = [f"{field.var_names[0]}__x_index_{x_index}" for x_index in range(num_points)]
    return trajectories, time_values, feature_names
