"""v0.38a: RM-1 .. RM-14, asserted.

Rules frozen in ``docs/design/v0_38a_hypothesis_freeze.md``.
"""

from __future__ import annotations

import inspect
import json

import pytest

from pdelie.design.lineage import DesignRowLineage
from pdelie.design.row_mask import (
    EXCLUSION_REASONS,
    RowMask,
    build_row_mask,
    compose_masks,
    derive_full_field_derivatives_available,
)
from pdelie.errors import ScopeValidationError


def _lineages(count: int = 4) -> list[DesignRowLineage]:
    return [
        DesignRowLineage(
            trajectory_id="traj_0",
            source_coordinate_id=f"x_{index}",
            mask_id="upstream",
        )
        for index in range(count)
    ]


def _mask(
    exclusions: dict[int, str] | None = None,
    *,
    count: int = 4,
    mask_id: str = "m",
    computed: tuple[str, ...] = ("u_t", "u_x", "u_xx"),
) -> RowMask:
    return build_row_mask(
        _lineages(count),
        exclusions or {},
        required_derivatives=("u_t", "u_x", "u_xx"),
        computed_derivatives=computed,
        mask_id=mask_id,
    )


# --------------------------------------------------------------------------
# RM-1 -- identity comes from v0.36b, and there is no second scheme
# --------------------------------------------------------------------------


def test_rm1_row_identity_is_the_lineage_semantic_hash() -> None:
    lineages = _lineages(3)
    mask = _mask(count=3)
    assert mask.row_identities == tuple(lineage.identity() for lineage in lineages)


def test_rm1_no_second_identity_scheme_is_defined() -> None:
    """A parallel identity would be a second answer to one question."""
    import pdelie.design.row_mask as module

    for forbidden in ("row_id", "compute_row_id", "make_row_identity", "RowIdentity"):
        assert not hasattr(module, forbidden), (
            f"row_mask defines {forbidden!r}; identity is DesignRowLineage.identity()"
        )


# --------------------------------------------------------------------------
# RM-2, RM-3 -- identities stored, positions derived, mismatch refused
# --------------------------------------------------------------------------


def test_rm2_positions_are_derived_not_stored() -> None:
    mask = _mask({1: "stencil_does_not_fit"})
    assert not any(
        isinstance(getattr(mask, name, None), (int,))
        for name in ("positions", "indices", "row_positions")
    )
    assert mask.positions_in(mask.row_identities) == (0, 2, 3)


def test_rm3_a_reordered_row_set_still_resolves_by_identity() -> None:
    """The point of identities: a reorder must not silently re-point the mask."""
    mask = _mask({1: "stencil_does_not_fit"})
    original = list(mask.row_identities)
    reordered = [original[2], original[0], original[3], original[1]]
    positions = mask.positions_in(reordered)
    assert [reordered[p] for p in positions] == [
        original[2],
        original[0],
        original[3],
    ], "the mask followed positions rather than identities"


def test_rm3_applying_to_an_unknown_row_set_is_refused() -> None:
    mask = _mask()
    with pytest.raises(ScopeValidationError, match="has never seen"):
        mask.positions_in([*mask.row_identities, "a_row_from_somewhere_else"])


def test_rm3_applying_to_a_truncated_row_set_is_refused() -> None:
    """A filtered matrix must not keep a mask that no longer describes it."""
    mask = _mask()
    with pytest.raises(ScopeValidationError, match="absent from the supplied set"):
        mask.positions_in(mask.row_identities[:2])


def test_rm4_selection_preserves_original_order() -> None:
    mask = _mask({0: "observation_masked"})
    assert mask.included == mask.row_identities[1:]


# --------------------------------------------------------------------------
# RM-5 .. RM-8 -- reasons
# --------------------------------------------------------------------------


def test_rm5_an_unknown_reason_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="not one of"):
        _mask({0: "seemed_wrong"})


@pytest.mark.parametrize("reason", EXCLUSION_REASONS)
def test_rm5_every_frozen_reason_is_constructible(reason: str) -> None:
    """B-1 of the pilot: a reason nothing can produce is a phantom entry."""
    mask = _mask({0: reason})
    assert mask.reason_counts()[reason] == 1


#: Which sub-phase is expected to *produce* each reason from real logic, as
#: opposed to a test constructing one directly. v0.38a ships the vocabulary and
#: the mask type; the producers arrive with the layers that can detect these
#: conditions.
_EXPECTED_PRODUCER: dict[str, str] = {
    "stencil_does_not_fit": "v0.38b",
    "coordinate_missing": "v0.38b",
    "derivative_unavailable": "v0.38b",
    "observation_masked": "v0.38a",
    "duplicate_coordinate": "v0.38b",
}


def test_no_shipped_logic_produces_a_reason_yet_and_that_is_stated() -> None:
    """Honest reading of pilot criterion B-1.

    Every reason is *constructible* -- the parametrized test above proves that.
    None is yet *produced* by shipped detection logic: ``build_row_mask`` takes
    the exclusions from its caller, so v0.38a supplies the vocabulary and the
    type while v0.38b supplies the conditions that trigger them.

    Constructible and produced are different claims, and a suite that only
    demonstrates the first should not be read as establishing the second. This
    test records which sub-phase owes each producer, so the gap is visible
    rather than inferred from an absence.
    """
    assert set(_EXPECTED_PRODUCER) == set(EXCLUSION_REASONS), (
        "a reason was added or removed without recording which sub-phase "
        "produces it"
    )
    unowned = [r for r, owner in _EXPECTED_PRODUCER.items() if not owner]
    assert not unowned, f"reasons with no named producer: {unowned}"


def test_rm6_the_vocabulary_only_grows() -> None:
    for reason in (
        "stencil_does_not_fit",
        "coordinate_missing",
        "derivative_unavailable",
        "observation_masked",
        "duplicate_coordinate",
    ):
        assert reason in EXCLUSION_REASONS


def test_rm7_an_included_row_carries_no_reason() -> None:
    """`None` and "included" must not both mean admissible."""
    mask = _mask({1: "coordinate_missing"})
    for identity in mask.included:
        assert identity not in mask.exclusions


def test_rm8_reason_counts_report_zeros_too() -> None:
    """A mapping omitting the zeros cannot be told apart from one never checked."""
    counts = _mask({0: "observation_masked"}).reason_counts()
    assert set(counts) == set(EXCLUSION_REASONS)
    assert counts["observation_masked"] == 1
    assert counts["duplicate_coordinate"] == 0


def test_a_reason_for_an_unknown_row_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="not in row_identities"):
        RowMask(
            row_identities=("r1", "r2"),
            exclusions={"r9": "observation_masked"},
            full_field_derivatives_available=True,
            mask_id="m",
        )


# --------------------------------------------------------------------------
# RM-9 .. RM-11 -- derived provenance
# --------------------------------------------------------------------------


def test_rm9_availability_is_derived_from_what_was_computed() -> None:
    assert derive_full_field_derivatives_available(("u_t", "u_x"), ("u_t", "u_x", "u_xx"))
    assert not derive_full_field_derivatives_available(("u_t", "u_xx"), ("u_t",))


def test_rm10_no_constructor_accepts_it_as_an_argument() -> None:
    """Absence is checked, not merely unwritten."""
    parameters = inspect.signature(build_row_mask).parameters
    assert "full_field_derivatives_available" not in parameters, (
        "build_row_mask accepts the availability flag; RM-9 requires it derived"
    )
    assert "required_derivatives" in parameters
    assert "computed_derivatives" in parameters


def test_rm9_an_empty_requirement_is_refused_rather_than_trivially_true() -> None:
    """Otherwise a field with no derivatives reports full availability."""
    with pytest.raises(ScopeValidationError, match="has no content"):
        derive_full_field_derivatives_available((), ("u_t",))


def test_availability_reflects_a_missing_derivative() -> None:
    mask = _mask(computed=("u_t", "u_x"))
    assert mask.full_field_derivatives_available is False


# --------------------------------------------------------------------------
# RM-12 .. RM-14 -- composition
# --------------------------------------------------------------------------


def test_rm12_composition_is_commutative_on_the_admitted_set() -> None:
    left = _mask({0: "stencil_does_not_fit"}, mask_id="left")
    right = _mask({2: "coordinate_missing"}, mask_id="right")
    forward = compose_masks(left, right, mask_id="fr")
    backward = compose_masks(right, left, mask_id="bk")
    assert forward.included == backward.included


def test_rm12_composition_is_associative_on_the_admitted_set() -> None:
    a = _mask({0: "stencil_does_not_fit"}, mask_id="a")
    b = _mask({1: "coordinate_missing"}, mask_id="b")
    c = _mask({2: "observation_masked"}, mask_id="c")
    left = compose_masks(compose_masks(a, b, mask_id="ab"), c, mask_id="abc")
    right = compose_masks(a, compose_masks(b, c, mask_id="bc"), mask_id="abc2")
    assert left.included == right.included


def test_rm13_a_doubly_excluded_row_keeps_both_reasons() -> None:
    left = _mask({0: "stencil_does_not_fit"}, mask_id="left")
    right = _mask({0: "observation_masked"}, mask_id="right")
    composed = compose_masks(left, right, mask_id="both")
    identity = composed.row_identities[0]
    assert composed.exclusions[identity] == "stencil_does_not_fit"
    assert composed.secondary_exclusions[identity] == "observation_masked"
    assert composed.as_dict()["doubly_excluded_count"] == 1


def test_rm13_a_singly_excluded_row_records_no_secondary_reason() -> None:
    left = _mask({0: "stencil_does_not_fit"}, mask_id="left")
    right = _mask({1: "observation_masked"}, mask_id="right")
    composed = compose_masks(left, right, mask_id="ab")
    assert composed.secondary_exclusions == {}


def test_rm14_composing_over_different_row_sets_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="different row-identity sets"):
        compose_masks(_mask(count=4), _mask(count=3), mask_id="x")


def test_composing_over_reordered_rows_is_refused() -> None:
    """Row order carries meaning, so one order must not be silently adopted."""
    base = _mask()
    flipped = RowMask(
        row_identities=tuple(reversed(base.row_identities)),
        exclusions={},
        full_field_derivatives_available=True,
        mask_id="flipped",
    )
    with pytest.raises(ScopeValidationError, match="different orders"):
        compose_masks(base, flipped, mask_id="x")


def test_composition_availability_is_conjunctive() -> None:
    """One mask's ignorance must not be reported as the composition's knowledge."""
    known = _mask(mask_id="known")
    partial = _mask(mask_id="partial", computed=("u_t",))
    assert known.full_field_derivatives_available is True
    assert partial.full_field_derivatives_available is False
    assert compose_masks(known, partial, mask_id="c").full_field_derivatives_available is False


# --------------------------------------------------------------------------
# Structural refusals
# --------------------------------------------------------------------------


def test_an_empty_mask_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="describes nothing"):
        RowMask(
            row_identities=(),
            exclusions={},
            full_field_derivatives_available=True,
            mask_id="empty",
        )


def test_duplicate_row_identities_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="Identity must identify"):
        RowMask(
            row_identities=("r1", "r1"),
            exclusions={},
            full_field_derivatives_available=True,
            mask_id="dup",
        )


def test_a_secondary_reason_without_a_primary_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="carries no primary reason"):
        RowMask(
            row_identities=("r1", "r2"),
            exclusions={},
            full_field_derivatives_available=True,
            mask_id="m",
            secondary_exclusions={"r1": "observation_masked"},
        )


def test_the_payload_is_strict_json() -> None:
    json.dumps(_mask({0: "stencil_does_not_fit"}).as_dict(), allow_nan=False)
