"""Which norm a measurement is in, declared rather than assumed.

The v0.37c pilot blocked because a bound derived in ``linf`` was compared
against a measurement emitted in ``l2``. Both quantities were correct. Neither
said which it was, so the comparison read as a factor-of-12 discrepancy in the
physics rather than a unit mismatch.

:class:`ErrorMetricSpec` makes that class structurally impossible: an analytical
bound and the measurement it bounds must reference the **same**
``metric_spec_id``, and :func:`require_matching_metric` refuses the pair when
they do not.

The rule is deliberately about identity, not about equality of fields. Two specs
with identical contents but different ids are still a mismatch, because it means
someone declared the metric twice and nobody checked they agreed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pdelie.errors import ScopeValidationError

__all__ = [
    "ERROR_METRIC_NORMS",
    "ERROR_METRIC_QUANTITIES",
    "ErrorMetricSpec",
    "require_matching_metric",
]

#: Norms a measurement may be reported in.
ERROR_METRIC_NORMS: tuple[str, ...] = ("l2", "linf")

#: What the number is relative to.
ERROR_METRIC_QUANTITIES: tuple[str, ...] = ("absolute", "relative", "normalized")


@dataclass(frozen=True)
class ErrorMetricSpec:
    """A named, closed description of how an error number was produced."""

    metric_spec_id: str
    quantity: str
    norm: str
    reduction_axes: tuple[str, ...] = ()
    normalization_reference: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.metric_spec_id, str) or not self.metric_spec_id.strip():
            raise ScopeValidationError("metric_spec_id must be a non-empty string.")
        if self.quantity not in ERROR_METRIC_QUANTITIES:
            raise ScopeValidationError(
                f"quantity {self.quantity!r} is not one of {list(ERROR_METRIC_QUANTITIES)}."
            )
        if self.norm not in ERROR_METRIC_NORMS:
            raise ScopeValidationError(
                f"norm {self.norm!r} is not one of {list(ERROR_METRIC_NORMS)}. An "
                f"unnamed norm is how a bound in one norm comes to be compared "
                f"against a measurement in another."
            )
        object.__setattr__(self, "reduction_axes", tuple(str(a) for a in self.reduction_axes))
        if self.quantity == "normalized" and not (self.normalization_reference or "").strip():
            raise ScopeValidationError(
                "a normalized quantity must name what it is normalized by; "
                "'normalized' without a reference is not a description."
            )
        if self.quantity != "normalized" and self.normalization_reference:
            raise ScopeValidationError(
                f"quantity {self.quantity!r} carries a normalization_reference; "
                f"only 'normalized' may."
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "metric_spec_id": self.metric_spec_id,
            "quantity": self.quantity,
            "norm": self.norm,
            "reduction_axes": list(self.reduction_axes),
            "normalization_reference": self.normalization_reference,
        }


def require_matching_metric(
    bound: ErrorMetricSpec, measurement: ErrorMetricSpec, *, where: str
) -> None:
    """Refuse a bound and a measurement that are not in the same metric.

    Compares ``metric_spec_id``, not field contents. Two specs that happen to
    agree but were declared separately are still refused: it means the metric
    was written down twice and nobody checked the copies matched.
    """
    for name, spec in (("bound", bound), ("measurement", measurement)):
        if not isinstance(spec, ErrorMetricSpec):
            raise ScopeValidationError(f"{where}: {name} must be an ErrorMetricSpec.")
    if bound.metric_spec_id != measurement.metric_spec_id:
        raise ScopeValidationError(
            f"{where}: the bound is stated in metric {bound.metric_spec_id!r} "
            f"({bound.quantity}/{bound.norm}) and the measurement in "
            f"{measurement.metric_spec_id!r} ({measurement.quantity}/"
            f"{measurement.norm}). These are different quantities and comparing "
            f"them produces a discrepancy that looks physical and is not."
        )
