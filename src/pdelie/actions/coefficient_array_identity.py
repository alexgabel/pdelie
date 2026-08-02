"""v0.38e: the two questions "are these coefficient arrays the same?" can mean.

See ``docs/design/COEFFICIENT_VALUES_SEMANTICS.md`` for the reasoning. The short
version, because the distinction is the whole point of this module:

**Storage-representation identity** -- same dtype, same shape, same bits. Asked
when deduplicating artifacts or validating a cache.

**Scientific identity** -- the same physical field to within a *declared*
tolerance, whatever the dtype. Asked when checking a co-transformation produced
the background it was meant to.

A ``float32`` and a ``float64`` view of one coefficient are scientifically
identical and not storage-identical. Both answers are right; the questions
differ.

These are two functions, not one function with a flag. A ``tolerance=None``
switch would be the conflation with extra steps -- every call site would then
have to be read to learn which question was asked.

Rules CI-1 .. CI-5 are frozen in ``docs/design/v0_38e_hypothesis_freeze.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from pdelie.contracts.error_metric_spec import ErrorMetricSpec
from pdelie.errors import ScopeValidationError

__all__ = [
    "ScientificIdentityResult",
    "StorageIdentityResult",
    "scientific_identity",
    "storage_representation_identity",
]


def _as_array(values: object, *, where: str) -> np.ndarray:
    if not isinstance(values, np.ndarray):
        raise ScopeValidationError(
            f"{where} is {type(values).__name__}, not a numpy array. Coercing here "
            f"would decide the dtype silently, which is exactly the question these "
            f"helpers exist to keep explicit."
        )
    return values


@dataclass(frozen=True)
class StorageIdentityResult:
    """Whether two arrays are the same *stored* object, and where they differ.

    ``differing_attribute`` names the first attribute that disagreed, so a
    caller reporting a mismatch does not have to re-derive why.
    """

    identical: bool
    differing_attribute: str | None
    left_dtype: str
    right_dtype: str
    left_shape: tuple[int, ...]
    right_shape: tuple[int, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "identical": self.identical,
            "differing_attribute": self.differing_attribute,
            "left_dtype": self.left_dtype,
            "right_dtype": self.right_dtype,
            "left_shape": list(self.left_shape),
            "right_shape": list(self.right_shape),
        }


@dataclass(frozen=True)
class ScientificIdentityResult:
    """Whether two arrays represent the same field under a *declared* metric.

    ``metric_spec_id`` is carried so the answer can never be quoted without the
    tolerance it was decided under -- the v0.37c pilot-1 defect was two numbers
    that both looked like "the error" and differed by a factor of twelve.
    """

    identical: bool
    metric_spec_id: str
    norm: str
    measured_error: float
    tolerance: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "identical": self.identical,
            "metric_spec_id": self.metric_spec_id,
            "norm": self.norm,
            "measured_error": self.measured_error,
            "tolerance": self.tolerance,
        }


def storage_representation_identity(
    left: np.ndarray, right: np.ndarray, *, where: str = "coefficient values"
) -> StorageIdentityResult:
    """Are these the same stored array? Exact, and it takes no tolerance.

    CI-2: there is no approximate version of "same bits". A tolerance parameter
    here would only ever be used to make this answer the other question.

    CI-4 (the useful half): this *is* an equivalence relation -- reflexive,
    symmetric and transitive -- so it may back a hash, a set, or a dict key.

    NaN is handled by comparing bit patterns rather than values. ``nan != nan``
    is correct arithmetic and the wrong answer to "are these the same stored
    array", where two identical NaN payloads plainly are.
    """
    left_array = _as_array(left, where=f"{where} (left)")
    right_array = _as_array(right, where=f"{where} (right)")

    differing: str | None = None
    if left_array.dtype != right_array.dtype:
        differing = "dtype"
    elif left_array.shape != right_array.shape:
        differing = "shape"
    elif left_array.tobytes() != right_array.tobytes():
        differing = "bytes"

    return StorageIdentityResult(
        identical=differing is None,
        differing_attribute=differing,
        left_dtype=str(left_array.dtype),
        right_dtype=str(right_array.dtype),
        left_shape=tuple(int(n) for n in left_array.shape),
        right_shape=tuple(int(n) for n in right_array.shape),
    )


def scientific_identity(
    left: np.ndarray,
    right: np.ndarray,
    *,
    metric: ErrorMetricSpec,
    tolerance: float,
    where: str = "coefficient values",
) -> ScientificIdentityResult:
    """Do these represent the same field, under a metric the caller declares?

    CI-3: ``metric`` and ``tolerance`` are both required and neither defaults. A
    defaulted tolerance is a claim nobody made, attributed to whoever reads the
    result.

    CI-4 (the sharp half): this is **not transitive**. ``a ~ b`` and ``b ~ c``
    does not give ``a ~ c``, so it is not an equivalence relation and must never
    back a hash, a set, or a dict key -- membership would depend on insertion
    order. Use :func:`storage_representation_identity` for that.

    Shape must still match. Two arrays of different shape are not the same field
    sampled differently; they are not comparable at all, and a broadcast here
    would invent a comparison the caller did not ask for.
    """
    left_array = _as_array(left, where=f"{where} (left)")
    right_array = _as_array(right, where=f"{where} (right)")

    if not isinstance(metric, ErrorMetricSpec):
        raise ScopeValidationError(
            "scientific_identity requires an ErrorMetricSpec. There is no default "
            "metric: a bound derived in one norm and compared against a "
            "measurement in another is the v0.37c pilot-1 defect."
        )
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool):
        raise ScopeValidationError("tolerance must be a real number.")
    tolerance = float(tolerance)
    if not np.isfinite(tolerance) or tolerance < 0.0:
        raise ScopeValidationError(
            f"tolerance must be finite and non-negative; got {tolerance!r}."
        )
    if left_array.shape != right_array.shape:
        raise ScopeValidationError(
            f"{where}: shapes {left_array.shape} and {right_array.shape} differ. "
            f"Arrays of different shape are not the same field sampled "
            f"differently -- they are not comparable, and broadcasting here would "
            f"invent a comparison nobody asked for."
        )

    difference = np.asarray(left_array, dtype=float) - np.asarray(right_array, dtype=float)
    if not np.all(np.isfinite(difference)):
        raise ScopeValidationError(
            f"{where}: the difference contains a non-finite value, so no norm of "
            f"it is a meaningful error. A missing value is None, never NaN."
        )

    if metric.norm == "linf":
        absolute = float(np.max(np.abs(difference))) if difference.size else 0.0
    elif metric.norm == "l2":
        absolute = float(np.sqrt(np.sum(difference**2))) if difference.size else 0.0
    else:  # pragma: no cover - ErrorMetricSpec closes the vocabulary
        raise ScopeValidationError(f"unhandled norm {metric.norm!r}.")

    if metric.quantity == "absolute":
        measured = absolute
    else:
        reference_array = np.asarray(right_array, dtype=float)
        if metric.norm == "linf":
            scale = float(np.max(np.abs(reference_array))) if reference_array.size else 0.0
        else:
            scale = float(np.sqrt(np.sum(reference_array**2))) if reference_array.size else 0.0
        if scale == 0.0:
            raise ScopeValidationError(
                f"{where}: metric {metric.metric_spec_id!r} is "
                f"{metric.quantity!r}, but the reference has zero magnitude in "
                f"{metric.norm!r}. A relative difference against zero is not a "
                f"number -- report the absolute error at the floor instead."
            )
        measured = absolute / scale

    return ScientificIdentityResult(
        identical=measured <= tolerance,
        metric_spec_id=metric.metric_spec_id,
        norm=metric.norm,
        measured_error=measured,
        tolerance=tolerance,
    )
