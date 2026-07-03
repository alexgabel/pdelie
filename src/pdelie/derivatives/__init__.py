from __future__ import annotations

from pdelie._boundary import is_x_periodic
from pdelie.contracts import DerivativeBatch, FieldBatch
from pdelie.derivatives.finite_difference import compute_finite_difference_derivatives
from pdelie.derivatives.spectral_fd import compute_spectral_fd_derivatives
from pdelie.errors import ScopeValidationError


_ALLOWED_DERIVATIVE_BACKEND_NAMES = frozenset(
    {"auto", "spectral_fd", "finite_difference"}
)


def compute_derivatives(
    field: FieldBatch,
    *,
    backend: str = "auto",
    max_spatial_order: int = 2,
) -> DerivativeBatch:
    """Backend-aware derivative dispatcher.

    - ``backend="auto"``: choose ``spectral_fd`` for periodic data, ``finite_difference``
      for any supported nonperiodic boundary type. The chosen backend always records
      ``backend_selected_by_boundary_condition=True`` and a non-null
      ``backend_selection_reason`` in ``DerivativeBatch.config`` so the selection is
      auditable from the artifact itself.
    - ``backend="spectral_fd"`` or ``backend="finite_difference"``: direct dispatch.
      Mismatch between explicit backend and field BC raises ``ScopeValidationError``;
      the dispatcher never silently falls back from one backend to the other.
    - Unknown backend names raise ``ScopeValidationError``.

    Both downstream backends require periodic / nonperiodic data respectively. The
    dispatcher does not relax those requirements.
    """
    if not isinstance(backend, str) or backend not in _ALLOWED_DERIVATIVE_BACKEND_NAMES:
        raise ScopeValidationError(
            "compute_derivatives backend must be one of "
            f"{sorted(_ALLOWED_DERIVATIVE_BACKEND_NAMES)}; got {backend!r}."
        )

    if backend == "auto":
        if is_x_periodic(field):
            selected_backend = "spectral_fd"
            selection_reason = "periodic_x_uses_spectral_fd"
        else:
            selected_backend = "finite_difference"
            selection_reason = "nonperiodic_x_uses_finite_difference"
    else:
        selected_backend = backend
        selection_reason = None

    if selected_backend == "spectral_fd":
        derivatives = compute_spectral_fd_derivatives(
            field, max_spatial_order=max_spatial_order
        )
    elif selected_backend == "finite_difference":
        derivatives = compute_finite_difference_derivatives(
            field, max_spatial_order=max_spatial_order
        )
    else:  # pragma: no cover — guarded by the allowed-set check above
        raise ScopeValidationError(
            f"compute_derivatives received an unsupported resolved backend: {selected_backend!r}."
        )

    if backend == "auto":
        config = dict(derivatives.config)
        config["backend_selected_by_boundary_condition"] = True
        config["backend_selection_reason"] = selection_reason
        derivatives.config = config

    return derivatives


__all__ = [
    "compute_derivatives",
    "compute_finite_difference_derivatives",
    "compute_spectral_fd_derivatives",
]

