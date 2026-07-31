"""v0.36b: how derivatives were taken, declared as data.

``DifferentiationPolicySpec`` records the backend, the order, the boundary
handling, and -- critically -- the **stencil half-width**, because that is what
determines where a derivative is valid and therefore which rows may enter a
design matrix.

The stencil width is not cosmetic
=================================

v0.33c's defect was that masking the design matrix *before* differentiation let
a stencil read across the mask boundary. The fix was a three-mask decomposition
in which derivative validity is eroded by the stencil half-width. A policy spec
that omitted the half-width could not express why the eroded mask has the shape
it does, so it is required rather than optional.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from pdelie.artifact.semantic_hash import semantic_hash
from pdelie.errors import ScopeValidationError

__all__ = [
    "DIFFERENTIATION_BACKENDS",
    "DIFFERENTIATION_BOUNDARY_HANDLING",
    "DifferentiationPolicySpec",
]

#: Backends the repository actually ships. ``spectral_fd`` is the periodic
#: default; ``finite_difference`` is what nonperiodic boundaries dispatch to.
DIFFERENTIATION_BACKENDS: tuple[str, ...] = ("spectral_fd", "finite_difference")

#: How the backend treats the domain edge.
DIFFERENTIATION_BOUNDARY_HANDLING: tuple[str, ...] = (
    "periodic_wrap",
    "one_sided_stencil",
    "interior_only_trim",
)


@dataclass(frozen=True)
class DifferentiationPolicySpec:
    """The differentiation configuration a stage actually used."""

    backend: str
    max_spatial_order: int
    boundary_handling: str
    stencil_half_width: int
    temporal_method: str = "finite_difference"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.backend not in DIFFERENTIATION_BACKENDS:
            raise ScopeValidationError(
                f"backend {self.backend!r} is not one of {list(DIFFERENTIATION_BACKENDS)}."
            )
        if self.boundary_handling not in DIFFERENTIATION_BOUNDARY_HANDLING:
            raise ScopeValidationError(
                f"boundary_handling {self.boundary_handling!r} is not one of "
                f"{list(DIFFERENTIATION_BOUNDARY_HANDLING)}."
            )
        for name in ("max_spatial_order", "stencil_half_width"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ScopeValidationError(f"{name} must be an integer.")
            if value < 0:
                raise ScopeValidationError(f"{name} must be non-negative.")
        if self.max_spatial_order > 0 and self.stencil_half_width == 0 and (
            self.backend == "finite_difference"
        ):
            raise ScopeValidationError(
                "a finite-difference policy with a positive spatial order must "
                "declare a positive stencil_half_width; the half-width is what "
                "determines derivative validity near a mask or domain edge."
            )
        if self.backend == "spectral_fd" and self.boundary_handling != "periodic_wrap":
            raise ScopeValidationError(
                "the spectral backend is only valid under periodic_wrap boundary "
                "handling; nonperiodic data dispatches to finite_difference."
            )
        if not isinstance(self.temporal_method, str) or not self.temporal_method.strip():
            raise ScopeValidationError("temporal_method must be a non-empty string.")
        if not isinstance(self.metadata, Mapping):
            raise ScopeValidationError("metadata must be a mapping.")
        object.__setattr__(self, "metadata", dict(self.metadata))
        semantic_hash(self.as_dict())

    def identity(self) -> str:
        return semantic_hash(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "max_spatial_order": self.max_spatial_order,
            "boundary_handling": self.boundary_handling,
            "stencil_half_width": self.stencil_half_width,
            "temporal_method": self.temporal_method,
            "metadata": dict(self.metadata),
        }
