"""v0.38e: CI-1 .. CI-5 and RR-1 .. RR-4, asserted.

Rules are frozen in ``docs/design/v0_38e_hypothesis_freeze.md``; the reasoning
is in ``docs/design/COEFFICIENT_VALUES_SEMANTICS.md``.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import numpy as np
import pytest

from pdelie.actions.coefficient_array_identity import (
    scientific_identity,
    storage_representation_identity,
)
from pdelie.actions.problem_spec import CoefficientFieldRef
from pdelie.actions.resolver import (
    ArtifactResolver,
    InMemoryResolver,
    MissingArtifactError,
    resolve_coefficient_values,
)
from pdelie.artifact.refs import ArtifactRef
from pdelie.contracts.error_metric_spec import ErrorMetricSpec
from pdelie.errors import ScopeValidationError

from .conformance.coefficient_semantics import (
    CONFORMANCE_FIXTURES,
    LINF_ABSOLUTE,
    NON_TRANSITIVE_TOLERANCE,
    non_transitivity_triple,
    values_ref,
)

# --------------------------------------------------------------------------
# CI-1 -- separate functions, no shared implementation, no mode flag
# --------------------------------------------------------------------------


def test_ci1_neither_identity_calls_the_other() -> None:
    """A flag turning one into the other would be the conflation with steps."""
    import pdelie.actions.coefficient_array_identity as module

    tree = ast.parse(Path(module.__file__).read_text())
    for name in ("storage_representation_identity", "scientific_identity"):
        other = (
            "scientific_identity"
            if name == "storage_representation_identity"
            else "storage_representation_identity"
        )
        function = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == name
        )
        called = {
            child.func.id
            for child in ast.walk(function)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
        }
        assert other not in called, f"{name} calls {other}; CI-1 requires them separate"


def test_ci2_storage_identity_takes_no_tolerance() -> None:
    """There is no approximate version of "same bits"."""
    parameters = inspect.signature(storage_representation_identity).parameters
    for forbidden in ("tolerance", "rtol", "atol", "metric", "approximate"):
        assert forbidden not in parameters, (
            f"storage_representation_identity accepts {forbidden!r}; a tolerance "
            f"here would only ever make it answer the other question"
        )


def test_ci3_scientific_identity_requires_metric_and_tolerance() -> None:
    """Neither defaults. A defaulted tolerance is a claim nobody made."""
    parameters = inspect.signature(scientific_identity).parameters
    for required in ("metric", "tolerance"):
        assert parameters[required].default is inspect.Parameter.empty, (
            f"{required} has a default; CI-3 forbids one"
        )

    left = np.array([0.0, 1.0])
    with pytest.raises(ScopeValidationError, match="requires an ErrorMetricSpec"):
        scientific_identity(left, left.copy(), metric="linf", tolerance=1e-9)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# CI-4 -- scientific identity is not an equivalence relation
# --------------------------------------------------------------------------


def test_ci4_scientific_identity_is_not_transitive() -> None:
    """The concrete triple. This is why nothing may key a container on it."""
    a, b, c = non_transitivity_triple()

    def same(left: np.ndarray, right: np.ndarray) -> bool:
        return scientific_identity(
            left, right, metric=LINF_ABSOLUTE, tolerance=NON_TRANSITIVE_TOLERANCE
        ).identical

    assert same(a, b), "a ~ b must hold for the chain to demonstrate anything"
    assert same(b, c), "b ~ c must hold for the chain to demonstrate anything"
    assert not same(a, c), (
        "a ~ c must NOT hold -- if it did, this fixture would prove nothing and "
        "CI-4 would have no evidence behind it"
    )


def test_ci4_storage_identity_is_an_equivalence_relation() -> None:
    """The half that may back a hash: reflexive, symmetric, transitive."""
    a = np.array([1.0, 2.0, 3.0])
    b = a.copy()
    c = b.copy()

    def same(left: np.ndarray, right: np.ndarray) -> bool:
        return storage_representation_identity(left, right).identical

    assert same(a, a), "reflexive"
    assert same(a, b) == same(b, a), "symmetric"
    assert same(a, b) and same(b, c) and same(a, c), "transitive"


# --------------------------------------------------------------------------
# CI-5 -- storage implies scientific; never the converse
# --------------------------------------------------------------------------


@pytest.mark.parametrize("norm", ["l2", "linf"])
def test_ci5_storage_identity_implies_scientific_identity(norm: str) -> None:
    """Identical bits agree under every metric, at tolerance zero."""
    metric = ErrorMetricSpec(
        metric_spec_id=f"ci5_{norm}", quantity="absolute", norm=norm
    )
    values = np.array([0.0, -1.5, 2.25, 1e12])
    assert storage_representation_identity(values, values.copy()).identical
    assert scientific_identity(
        values, values.copy(), metric=metric, tolerance=0.0
    ).identical


def test_ci5_converse_fails_and_the_implication_is_strict() -> None:
    """A dtype cast: scientifically identical, not storage-identical.

    Without this case CI-5 would be vacuously true -- an implication nobody
    could distinguish from an equivalence.
    """
    wide = np.array([0.0, 1.0, 2.0], dtype=np.float64)
    narrow = wide.astype(np.float32)

    storage = storage_representation_identity(wide, narrow)
    assert not storage.identical
    assert storage.differing_attribute == "dtype"

    assert scientific_identity(
        wide, narrow, metric=LINF_ABSOLUTE, tolerance=1e-6
    ).identical


# --------------------------------------------------------------------------
# CF-1 -- the six conformance fixtures
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture", CONFORMANCE_FIXTURES, ids=lambda f: f.fixture_id
)
def test_cf1_conformance_fixture(fixture: object) -> None:
    assert storage_representation_identity(
        fixture.left, fixture.right  # type: ignore[attr-defined]
    ).identical is fixture.storage_identical  # type: ignore[attr-defined]

    if fixture.scientific_identity_is_refused:  # type: ignore[attr-defined]
        with pytest.raises(ScopeValidationError):
            scientific_identity(
                fixture.left,  # type: ignore[attr-defined]
                fixture.right,  # type: ignore[attr-defined]
                metric=LINF_ABSOLUTE,
                tolerance=fixture.tolerance,  # type: ignore[attr-defined]
            )
        return

    assert scientific_identity(
        fixture.left,  # type: ignore[attr-defined]
        fixture.right,  # type: ignore[attr-defined]
        metric=LINF_ABSOLUTE,
        tolerance=fixture.tolerance,  # type: ignore[attr-defined]
    ).identical is fixture.scientifically_identical  # type: ignore[attr-defined]


def test_cf1_covers_both_disagreeing_directions() -> None:
    """Guard the fixture set: it must contain the cases that make it useful.

    A suite where the two identities always agree would pass every test above
    and demonstrate nothing about why there are two functions.
    """
    disagreeing = [
        f
        for f in CONFORMANCE_FIXTURES
        if f.scientifically_identical is not None
        and f.storage_identical is not f.scientifically_identical
    ]
    assert disagreeing, "no fixture where the two identities disagree"
    refused = [f for f in CONFORMANCE_FIXTURES if f.scientific_identity_is_refused]
    assert refused, "no fixture where scientific identity is refused"
    assert any(f.storage_identical for f in refused), (
        "no fixture that is storage-identical while scientific identity refuses "
        "-- CF-f is the clearest statement of the distinction and must be present"
    )


# --------------------------------------------------------------------------
# Refusals
# --------------------------------------------------------------------------


def test_shape_mismatch_is_refused_not_broadcast() -> None:
    with pytest.raises(ScopeValidationError, match="not comparable"):
        scientific_identity(
            np.zeros(4), np.zeros(3), metric=LINF_ABSOLUTE, tolerance=1.0
        )


def test_nan_difference_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="non-finite"):
        scientific_identity(
            np.array([0.0, np.nan]),
            np.array([0.0, 1.0]),
            metric=LINF_ABSOLUTE,
            tolerance=1.0,
        )


def test_relative_metric_against_a_zero_reference_is_refused() -> None:
    """Relative difference at the floor is meaningless; report absolute there."""
    metric = ErrorMetricSpec(
        metric_spec_id="rel_linf", quantity="relative", norm="linf"
    )
    with pytest.raises(ScopeValidationError, match="zero magnitude"):
        scientific_identity(
            np.array([1e-18, 0.0]), np.zeros(2), metric=metric, tolerance=1.0
        )


def test_negative_tolerance_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="finite and non-negative"):
        scientific_identity(
            np.zeros(2), np.zeros(2), metric=LINF_ABSOLUTE, tolerance=-1.0
        )


def test_non_array_input_is_refused_rather_than_coerced() -> None:
    with pytest.raises(ScopeValidationError, match="not a numpy array"):
        storage_representation_identity([1.0, 2.0], np.zeros(2))  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# RR-1 .. RR-4 -- the resolver
# --------------------------------------------------------------------------


def test_rr1_there_is_no_module_level_registry() -> None:
    """The rejected design, asserted absent rather than merely not written."""
    import pdelie.actions.resolver as module

    for forbidden in (
        "register_resolver",
        "set_default_resolver",
        "get_resolver",
        "DEFAULT_RESOLVER",
        "_REGISTRY",
    ):
        assert not hasattr(module, forbidden), (
            f"resolver module exposes {forbidden!r}; RR-1 forbids a global, "
            f"because it makes the values a run reads depend on import order"
        )


def test_rr1_resolver_is_a_required_argument() -> None:
    parameters = inspect.signature(resolve_coefficient_values).parameters
    assert parameters["resolver"].default is inspect.Parameter.empty
    assert parameters["resolver"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD


def test_rr2_a_missing_artifact_raises_rather_than_returning_empty() -> None:
    present = np.zeros(3)
    absent = np.ones(3)
    resolver = InMemoryResolver({values_ref(present).artifact_id: present})
    ref = CoefficientFieldRef(
        field_name="nu",
        coordinate_dependency=("x",),
        treatment="fixed_background",
        values_artifact=values_ref(absent),
    )
    with pytest.raises(MissingArtifactError, match="not held by this resolver"):
        resolve_coefficient_values(ref, resolver)


def test_rr3_a_resolver_declares_whether_it_caches() -> None:
    resolver = InMemoryResolver({"a": np.zeros(2)})
    assert resolver.is_caching is False
    assert isinstance(resolver, ArtifactResolver)


def test_rr4_the_protocol_exposes_no_action_parameter() -> None:
    """A resolver that could transform could apply an undeclared action."""
    parameters = inspect.signature(ArtifactResolver.resolve).parameters
    assert set(parameters) == {"self", "ref"}, (
        f"ArtifactResolver.resolve takes {sorted(parameters)}; RR-4 allows only "
        f"the reference -- deciding what to do with the values is the executor's"
    )


def test_an_analytical_field_is_refused_rather_than_resolved_to_empty() -> None:
    """"Analytical, nothing stored" and "stored, but empty" must differ."""
    resolver = InMemoryResolver({})
    ref = CoefficientFieldRef(
        field_name="nu",
        coordinate_dependency=("x",),
        treatment="fixed_background",
        analytical_spec={"form": "constant", "value": 0.1},
    )
    with pytest.raises(MissingArtifactError, match="analytical_spec"):
        resolve_coefficient_values(ref, resolver)


def test_a_resolver_that_does_not_satisfy_the_protocol_is_refused() -> None:
    class NotAResolver:
        def resolve(self, ref: ArtifactRef) -> np.ndarray:
            return np.zeros(2)

    ref = CoefficientFieldRef(
        field_name="nu",
        coordinate_dependency=("x",),
        treatment="fixed_background",
        values_artifact=values_ref(np.zeros(2)),
    )
    with pytest.raises(ScopeValidationError, match="ArtifactResolver protocol"):
        resolve_coefficient_values(ref, NotAResolver())  # type: ignore[arg-type]


def test_a_successful_resolution_returns_the_stored_array() -> None:
    values = np.array([0.1, 0.2, 0.3])
    ref_for_values = values_ref(values)
    resolver = InMemoryResolver({ref_for_values.artifact_id: values})
    ref = CoefficientFieldRef(
        field_name="nu",
        coordinate_dependency=("x",),
        treatment="co_transformable_background",
        values_artifact=ref_for_values,
    )
    resolved = resolve_coefficient_values(ref, resolver)
    assert storage_representation_identity(resolved, values).identical
