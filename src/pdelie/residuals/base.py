from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from pdelie.contracts import DerivativeBatch, FieldBatch, ResidualBatch


class ResidualEvaluator(ABC):
    @abstractmethod
    def evaluate(
        self,
        field: FieldBatch,
        derivatives: DerivativeBatch | None = None,
    ) -> ResidualBatch:
        raise NotImplementedError


_DEFAULT_BOUNDARY_TRIM_WIDTH = 4


def build_residual_diagnostics_from_derivatives(
    residual: np.ndarray,
    field: FieldBatch,
    derivatives: DerivativeBatch,
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute residual diagnostics honoring the derivative backend's recommended domain policy.

    Behavior by ``derivatives.config['recommended_residual_domain_policy']``:

    - ``"interior_only"`` (default for ``finite_difference`` backend on nonperiodic data):
      report ``residual_domain_policy = "interior_only"`` and ``boundary_trim_width = k``
      where ``k`` is read from ``derivatives.config['recommended_boundary_trim_width']``
      (default 4). ``max_abs_residual`` and ``rms_residual`` are computed over the
      interior only (trimming ``k`` points from each end of the x axis). A nested
      ``full_grid_diagnostic`` block reports the same metrics over the full grid so
      users can see the boundary contamination explicitly.

    - Anything else (``"full_grid"``, ``None``, or an unrecognized value): report
      ``residual_domain_policy = "full_grid"`` and compute metrics over the full grid.
      No ``full_grid_diagnostic`` block is emitted (the primary metrics already are the
      full-grid ones).

    The ``extra`` mapping is merged into the diagnostics after the standard keys. It
    must not contain reserved keys (``backend``, ``residual_domain_policy``,
    ``boundary_trim_width``, ``max_abs_residual``, ``rms_residual``,
    ``full_grid_diagnostic``); reserved keys in ``extra`` are silently overridden by
    the computed values to keep the schema stable.
    """
    residual = np.asarray(residual, dtype=float)
    x_axis = field.dims.index("x")

    full_grid_max = float(np.max(np.abs(residual)))
    full_grid_rms = float(np.sqrt(np.mean(np.square(residual))))

    config = derivatives.config or {}
    recommended_policy = config.get("recommended_residual_domain_policy")

    if recommended_policy == "interior_only":
        requested_trim = config.get("recommended_boundary_trim_width", _DEFAULT_BOUNDARY_TRIM_WIDTH)
        try:
            trim = int(requested_trim)
        except (TypeError, ValueError):
            trim = _DEFAULT_BOUNDARY_TRIM_WIDTH
        n_x = residual.shape[x_axis]
        if trim < 0 or 2 * trim >= n_x:
            # Fallback: too aggressive a trim; degrade to full grid but keep the
            # policy label honest so callers can detect the degradation.
            interior = residual
            actual_trim = 0
        else:
            slicer = [slice(None)] * residual.ndim
            slicer[x_axis] = slice(trim, n_x - trim)
            interior = residual[tuple(slicer)]
            actual_trim = trim

        interior_max = float(np.max(np.abs(interior)))
        interior_rms = float(np.sqrt(np.mean(np.square(interior))))

        diagnostics: dict[str, Any] = {}
        if extra:
            diagnostics.update(extra)
        diagnostics.update(
            {
                "backend": derivatives.backend,
                "residual_domain_policy": "interior_only",
                "boundary_trim_width": actual_trim,
                "max_abs_residual": interior_max,
                "rms_residual": interior_rms,
                "full_grid_diagnostic": {
                    "max_abs_residual": full_grid_max,
                    "rms_residual": full_grid_rms,
                },
            }
        )
        return diagnostics

    diagnostics = {}
    if extra:
        diagnostics.update(extra)
    diagnostics.update(
        {
            "backend": derivatives.backend,
            "residual_domain_policy": "full_grid",
            "max_abs_residual": full_grid_max,
            "rms_residual": full_grid_rms,
        }
    )
    return diagnostics
