"""v0.36b: what was observed, declared separately from how it was differentiated.

``ObservationOperatorSpec`` describes the map from the true field to what the
pipeline actually saw: which points, under what mask, at what noise level, with
what sensor geometry.

Why this is separate from ``DifferentiationPolicySpec``
======================================================

Because they answer different questions and can be wrong independently. The
v0.33c mask defect is the case in point: the three-mask decomposition
(observation, derivative-validity, regression-row) exists precisely because
"what we observed" and "where a derivative stencil is valid" are different sets,
and conflating them leaked stencil support across the mask boundary. One spec
carrying both would reintroduce that conflation as a data model.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from pdelie.artifact.refs import JSONValue  # noqa: F401  (re-exported vocabulary)
from pdelie.artifact.semantic_hash import semantic_hash
from pdelie.errors import ScopeValidationError

__all__ = ["OBSERVATION_OPERATOR_KINDS", "ObservationOperatorSpec"]

#: Frozen vocabulary. ``identity`` means the pipeline saw the generated field
#: unaltered -- the common case, and worth naming rather than leaving implicit.
OBSERVATION_OPERATOR_KINDS: tuple[str, ...] = (
    "identity",
    "masked_subsample",
    "point_sensors",
    "line_average",
    "downsampled_grid",
)


@dataclass(frozen=True)
class ObservationOperatorSpec:
    """How the observed field relates to the underlying field."""

    operator_kind: str
    observed_point_count: int
    total_point_count: int
    mask_id: str | None = None
    sensor_layout: str | None = None
    noise_model: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.operator_kind not in OBSERVATION_OPERATOR_KINDS:
            raise ScopeValidationError(
                f"operator_kind {self.operator_kind!r} is not one of "
                f"{list(OBSERVATION_OPERATOR_KINDS)}."
            )
        for name in ("observed_point_count", "total_point_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ScopeValidationError(f"{name} must be an integer.")
            if value < 0:
                raise ScopeValidationError(f"{name} must be non-negative.")
        if self.observed_point_count > self.total_point_count:
            raise ScopeValidationError(
                f"observed_point_count ({self.observed_point_count}) exceeds "
                f"total_point_count ({self.total_point_count}); an observation "
                f"operator cannot produce more points than the field has."
            )
        if self.operator_kind == "identity" and (
            self.observed_point_count != self.total_point_count
        ):
            raise ScopeValidationError(
                "operator_kind='identity' must observe every point; declare "
                "'masked_subsample' or 'downsampled_grid' instead."
            )
        for name in ("mask_id", "sensor_layout", "noise_model"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ScopeValidationError(f"{name} must be a non-empty string or None.")
        if not isinstance(self.metadata, Mapping):
            raise ScopeValidationError("metadata must be a mapping.")
        object.__setattr__(self, "metadata", dict(self.metadata))
        semantic_hash(self.as_dict())

    @property
    def observed_fraction(self) -> float:
        if self.total_point_count == 0:
            return 0.0
        return self.observed_point_count / self.total_point_count

    def identity(self) -> str:
        return semantic_hash(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "operator_kind": self.operator_kind,
            "observed_point_count": self.observed_point_count,
            "total_point_count": self.total_point_count,
            "mask_id": self.mask_id,
            "sensor_layout": self.sensor_layout,
            "noise_model": self.noise_model,
            "metadata": dict(self.metadata),
        }
