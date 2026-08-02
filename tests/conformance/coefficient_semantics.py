"""v0.38e CF-1: six generic conformance fixtures.

Each exercises one distinction the coefficient-values semantics turns on, with
no equation family, no profile registry and no benchmark involved. A later
sub-phase can import these to check it honours the same rules.

The six:

======  ==========================================================
CF-a    identical arrays -- both identities hold
CF-b    dtype cast -- scientific holds, storage does not
CF-c    one perturbed sample -- neither holds at a tight tolerance
CF-d    the non-transitivity chain -- a~b, b~c, a!~c
CF-e    shape mismatch -- not comparable, refused
CF-f    NaN payloads -- storage-identical, scientifically refused
======  ==========================================================

CF-d is the one that matters most. It is a concrete triple proving approximate
equality is not an equivalence relation, so nothing may key a container on it.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from pdelie.artifact.refs import ArtifactRef, content_artifact_id
from pdelie.contracts.error_metric_spec import ErrorMetricSpec

__all__ = [
    "CONFORMANCE_FIXTURES",
    "LINF_ABSOLUTE",
    "NON_TRANSITIVE_TOLERANCE",
    "CoefficientFixture",
    "non_transitivity_triple",
    "values_ref",
]


def values_ref(values: np.ndarray, *, stage_id: str = "v0_38e_conformance") -> ArtifactRef:
    """A genuinely content-addressed ref for an array.

    ``artifact_id`` is the SHA-256 of the bytes, not a label. Two arrays with
    identical bytes therefore produce the same ref -- which is the property the
    resolver rules depend on, so a fixture that faked the id would be testing
    against a weaker contract than the one that ships.
    """
    payload = values.tobytes()
    return ArtifactRef(
        artifact_id=content_artifact_id(payload),
        artifact_kind="coefficient_values",
        schema_version="0.1",
        producer_stage_id=stage_id,
        byte_count=len(payload),
    )

#: The metric the fixtures declare. Named, because an unnamed norm is how a
#: bound in one norm comes to be compared against a measurement in another.
LINF_ABSOLUTE = ErrorMetricSpec(
    metric_spec_id="v0_38e_conformance_linf_absolute",
    quantity="absolute",
    norm="linf",
)

#: The tolerance CF-d is built around. Chosen so each adjacent pair sits inside
#: it and the endpoints sit outside; it is a property of the fixture, not a
#: threshold anything is measured against.
NON_TRANSITIVE_TOLERANCE = 0.6


@dataclass(frozen=True)
class CoefficientFixture:
    """One fixture: two arrays and what each identity should say about them."""

    fixture_id: str
    left: np.ndarray
    right: np.ndarray
    storage_identical: bool
    scientifically_identical: bool | None
    tolerance: float
    note: str

    @property
    def scientific_identity_is_refused(self) -> bool:
        """``None`` means the comparison is refused, not that it is False."""
        return self.scientifically_identical is None


_BASE = np.array([0.0, 1.0, 2.0, 3.0], dtype=np.float64)


def non_transitivity_triple() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Three arrays with ``a~b``, ``b~c`` and ``a!~c`` at the fixture tolerance.

    Steps of 0.5 each, endpoints 1.0 apart, tolerance 0.6. There is no way to
    choose a tolerance that makes this transitive; that is the point.
    """
    a = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float64)
    b = a + 0.5
    c = b + 0.5
    return a, b, c


_NAN_LEFT = np.array([0.0, np.nan, 2.0], dtype=np.float64)
_NAN_RIGHT = _NAN_LEFT.copy()

CONFORMANCE_FIXTURES: tuple[CoefficientFixture, ...] = (
    CoefficientFixture(
        fixture_id="CF-a",
        left=_BASE,
        right=_BASE.copy(),
        storage_identical=True,
        scientifically_identical=True,
        tolerance=0.0,
        note="Identical bits. Both identities hold, and CI-5's forward direction "
        "says the second follows from the first at every tolerance.",
    ),
    CoefficientFixture(
        fixture_id="CF-b",
        left=_BASE,
        right=_BASE.astype(np.float32),
        storage_identical=False,
        scientifically_identical=True,
        tolerance=1e-6,
        note="The same field at two precisions. Storage differs on dtype; the "
        "physics does not. This is the case that makes CI-5's implication "
        "strict rather than vacuous.",
    ),
    CoefficientFixture(
        fixture_id="CF-c",
        left=_BASE,
        right=_BASE + np.array([0.0, 0.0, 0.5, 0.0]),
        storage_identical=False,
        scientifically_identical=False,
        tolerance=1e-9,
        note="One sample moved. Neither identity holds, which is the "
        "uninteresting agreeing case and is included so the suite is not "
        "made only of edge cases.",
    ),
    CoefficientFixture(
        fixture_id="CF-d",
        left=non_transitivity_triple()[0],
        right=non_transitivity_triple()[2],
        storage_identical=False,
        scientifically_identical=False,
        tolerance=NON_TRANSITIVE_TOLERANCE,
        note="The endpoints of the non-transitivity chain. Each adjacent pair is "
        "within tolerance and the endpoints are not, so approximate equality "
        "induces no equivalence classes and must not back a hash or a set.",
    ),
    CoefficientFixture(
        fixture_id="CF-e",
        left=_BASE,
        right=_BASE[:3],
        storage_identical=False,
        scientifically_identical=None,
        tolerance=1.0,
        note="Different shapes. Refused rather than answered: these are not the "
        "same field sampled differently, and broadcasting would invent a "
        "comparison nobody asked for.",
    ),
    CoefficientFixture(
        fixture_id="CF-f",
        left=_NAN_LEFT,
        right=_NAN_RIGHT,
        storage_identical=True,
        scientifically_identical=None,
        tolerance=1.0,
        note="Identical NaN payloads. Storage identity says yes -- they are "
        "plainly the same stored array. Scientific identity refuses, because "
        "no norm of a NaN difference is an error. The two answers differ and "
        "both are correct, which is the clearest statement of why there are "
        "two functions.",
    ),
)
