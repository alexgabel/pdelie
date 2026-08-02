"""v0.38e: resolving a coefficient reference to values, explicitly.

A :class:`CoefficientFieldRef` carries an ``ArtifactRef``, not an array. Getting
from one to the other is *resolution*, and this module fixes how it happens.

Why there is no registry
========================

The obvious design is a module-level ``register_resolver()`` and a global
lookup. It is rejected here, permanently.

A global resolver makes the values a function reads depend on import order and
on whatever else in the process registered last. Two runs of the same bundle can
then resolve to different arrays with nothing in the report saying so -- the
declaration and the execution disagree, and the mechanism that would let you
notice is the thing that was made implicit.

So: **every call site takes a resolver argument.** It is more typing. It is also
the difference between "this run read those values" being a fact in the call and
a fact in the process state.

Rules RR-1 .. RR-4 are frozen in ``docs/design/v0_38e_hypothesis_freeze.md``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

import numpy as np

from pdelie.artifact.refs import ArtifactRef
from pdelie.errors import ScopeValidationError

__all__ = [
    "ArtifactResolver",
    "InMemoryResolver",
    "MissingArtifactError",
    "resolve_coefficient_values",
]


class MissingArtifactError(ScopeValidationError):
    """A reference did not resolve.

    RR-2: this is raised rather than returning ``None`` or an empty array. A
    caller who forgets to check a sentinel gets a silently wrong measurement; a
    caller who ignores an exception gets a traceback.
    """


@runtime_checkable
class ArtifactResolver(Protocol):
    """Maps an artifact reference to its values.

    RR-4: a resolver never sees the action. It answers "what is stored under
    this reference", and what is done with the answer belongs to the executor. A
    resolver that could transform could apply an action nobody declared, and the
    report would attribute the result to the declared one.
    """

    #: RR-3: resolution is not caching. A memoizing resolver declares itself,
    #: because a stale cache turns a content-addressed reference into a false
    #: statement and nothing downstream can tell.
    is_caching: bool

    def resolve(self, ref: ArtifactRef) -> np.ndarray:
        """Return the values, or raise :class:`MissingArtifactError`."""
        ...


class InMemoryResolver:
    """A resolver over an explicit mapping. Not a cache.

    The reference implementation and the one the conformance fixtures use. It
    holds exactly what it was constructed with and never populates itself, so
    ``is_caching`` is ``False`` and stays that way.
    """

    is_caching = False

    def __init__(self, values: Mapping[str, np.ndarray]) -> None:
        if not isinstance(values, Mapping):
            raise ScopeValidationError("InMemoryResolver requires a mapping.")
        resolved: dict[str, np.ndarray] = {}
        for artifact_id, array in values.items():
            if not isinstance(artifact_id, str) or not artifact_id.strip():
                raise ScopeValidationError("artifact ids must be non-empty strings.")
            if not isinstance(array, np.ndarray):
                raise ScopeValidationError(
                    f"values[{artifact_id!r}] is {type(array).__name__}, not a numpy "
                    f"array. Coercing here would decide a dtype silently."
                )
            resolved[artifact_id] = array
        self._values = resolved

    def resolve(self, ref: ArtifactRef) -> np.ndarray:
        if not isinstance(ref, ArtifactRef):
            raise ScopeValidationError("resolve requires an ArtifactRef.")
        try:
            return self._values[ref.artifact_id]
        except KeyError:
            raise MissingArtifactError(
                f"artifact {ref.artifact_id!r} is not held by this resolver. It "
                f"holds {sorted(self._values)}. This raises rather than returning "
                f"an empty array, so a missing coefficient cannot be measured as "
                f"a zero one."
            ) from None

    def known_artifact_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._values))


def resolve_coefficient_values(
    ref: object,
    resolver: ArtifactResolver,
    *,
    where: str = "coefficient field",
) -> np.ndarray:
    """Resolve one :class:`CoefficientFieldRef` to its values.

    RR-1: ``resolver`` is a required positional argument. There is deliberately
    no default and no fallback to a global -- see the module docstring.

    A field declaring an ``analytical_spec`` and no ``values_artifact`` has no
    stored values to resolve. That is refused here rather than returning an
    empty array, because "analytical, so nothing stored" and "stored, but empty"
    are different situations that must not produce the same object.
    """
    # Imported here rather than at module scope: problem_spec imports nothing
    # from this module, and keeping it that way means the contract layer stays
    # free of any resolution machinery.
    from pdelie.actions.problem_spec import CoefficientFieldRef

    if not isinstance(ref, CoefficientFieldRef):
        raise ScopeValidationError(
            f"{where}: expected a CoefficientFieldRef, got {type(ref).__name__}."
        )
    if not isinstance(resolver, ArtifactResolver):
        raise ScopeValidationError(
            f"{where}: resolver does not satisfy the ArtifactResolver protocol. It "
            f"must expose `resolve(ref)` and a boolean `is_caching`."
        )
    if ref.values_artifact is None:
        raise MissingArtifactError(
            f"{where} {ref.field_name!r} declares no values_artifact"
            + (
                " -- it carries an analytical_spec, so it has no stored values to "
                "resolve. Evaluate the analytical form instead of resolving."
                if ref.analytical_spec is not None
                else ". There is nothing to resolve."
            )
        )
    values = resolver.resolve(ref.values_artifact)
    if not isinstance(values, np.ndarray):
        raise ScopeValidationError(
            f"{where}: resolver returned {type(values).__name__}, not a numpy "
            f"array. RR-2 -- a resolver returns values or raises."
        )
    return values
