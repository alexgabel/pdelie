"""What a coefficient profile's geometry is, checked against the domain.

v0.37c froze a `tanh` profile -- nonperiodic by construction -- into a benchmark
where every case declared ``domain_type = periodic_uniform``. Under a periodic
wrap the profile's seam travelled through the interior and dominated the
measurement, so the case measured a discontinuity rather than the monotone
variation it was named for. It survived a hypothesis freeze and two pilots
before anyone checked.

:class:`ProfileGeometrySpec` makes that class structurally impossible:
:func:`require_compatible_domain` refuses a nonperiodic profile paired with a
periodic wrapping action, **before any pilot runs**.

The requirement had been implicit for the whole of v0.37. Implicit requirements
are the ones that get violated.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from pdelie.errors import ScopeValidationError

__all__ = [
    "SMOOTHNESS_CLASSES",
    "ProfileGeometrySpec",
    "require_compatible_domain",
]

#: How smooth the profile is. ``monotone`` is listed and is *never* periodic on
#: a bounded domain -- that combination is what retired benchmark case C-4.
SMOOTHNESS_CLASSES: tuple[str, ...] = (
    "constant",
    "continuous",
    "smooth",
    "monotone",
    "compact_support",
)

#: Smoothness classes that cannot be periodic on a bounded domain, whatever a
#: caller declares. A monotone non-constant function takes different values at
#: the two ends by definition.
_INHERENTLY_NONPERIODIC: frozenset[str] = frozenset({"monotone"})


@dataclass(frozen=True)
class ProfileGeometrySpec:
    """The geometry of a coefficient profile, declared per axis."""

    profile_id: str
    periodic_axes: tuple[str, ...]
    smoothness_class: str
    seam_continuity_required: bool
    domain_types_supported: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.profile_id, str) or not self.profile_id.strip():
            raise ScopeValidationError("profile_id must be a non-empty string.")
        if self.smoothness_class not in SMOOTHNESS_CLASSES:
            raise ScopeValidationError(
                f"smoothness_class {self.smoothness_class!r} is not one of "
                f"{list(SMOOTHNESS_CLASSES)}."
            )
        for name in ("periodic_axes", "domain_types_supported"):
            value: object = getattr(self, name)
            if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
                raise ScopeValidationError(f"{name} must be a sequence, not a bare string.")
            object.__setattr__(self, name, tuple(str(v) for v in value))
        if not isinstance(self.seam_continuity_required, bool):
            raise ScopeValidationError("seam_continuity_required must be a bool.")

        if self.smoothness_class in _INHERENTLY_NONPERIODIC and self.periodic_axes:
            raise ScopeValidationError(
                f"profile {self.profile_id!r} declares smoothness_class "
                f"{self.smoothness_class!r} and periodic axes "
                f"{list(self.periodic_axes)}. A monotone non-constant function "
                f"takes different values at the two ends of a bounded axis, so it "
                f"cannot be periodic on one. This is the C-4 contradiction, "
                f"refused at construction."
            )

    @property
    def is_periodic_everywhere(self) -> bool:
        return bool(self.periodic_axes)

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "periodic_axes": list(self.periodic_axes),
            "smoothness_class": self.smoothness_class,
            "seam_continuity_required": self.seam_continuity_required,
            "domain_types_supported": list(self.domain_types_supported),
        }


def require_compatible_domain(
    geometry: ProfileGeometrySpec,
    domain_type: str,
    *,
    spatial_axis: str,
    action_wraps: bool,
    where: str,
) -> None:
    """Refuse a profile whose geometry contradicts the domain it will run on.

    ``action_wraps`` is whether the action applied to this problem wraps around
    the domain -- a periodic translation does. A profile that is not periodic on
    the wrapping axis carries a seam, and wrapping moves that seam through the
    interior.
    """
    if not isinstance(geometry, ProfileGeometrySpec):
        raise ScopeValidationError(f"{where}: geometry must be a ProfileGeometrySpec.")
    if domain_type not in geometry.domain_types_supported:
        raise ScopeValidationError(
            f"{where}: profile {geometry.profile_id!r} supports "
            f"{list(geometry.domain_types_supported)} and the problem declares "
            f"{domain_type!r}."
        )
    if action_wraps and spatial_axis not in geometry.periodic_axes:
        raise ScopeValidationError(
            f"{where}: profile {geometry.profile_id!r} is not periodic on axis "
            f"{spatial_axis!r}, but the action wraps around it. The profile's seam "
            f"would travel through the interior and dominate the measurement -- "
            f"this is the C-4 defect, refused before any run."
        )
