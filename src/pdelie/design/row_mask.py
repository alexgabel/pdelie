"""v0.38a: which design rows are admissible, identified rather than positioned.

A boolean array aligned to a matrix answers "is row 7 usable?" only for as long
as nothing reorders the matrix -- and filtering, sorting and concatenating are
all ordinary operations on a design matrix. After any of them the array still
has the right length and describes different rows.

:class:`RowMask` stores **row identities**, so it either still applies or
refuses to. Positions are derived on demand against a specific row set and are
never stored.

Identity comes from v0.36b
==========================

A row's identity is :meth:`DesignRowLineage.identity` -- the semantic hash that
already answers "which row is this?". v0.38a introduces no second scheme,
because a parallel identity is a second answer to one question and the two would
eventually disagree.

Rules RM-1 .. RM-14 are frozen in ``docs/design/v0_38a_hypothesis_freeze.md``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pdelie.design.lineage import DesignRowLineage
from pdelie.errors import ScopeValidationError

__all__ = [
    "EXCLUSION_REASONS",
    "RowMask",
    "compose_masks",
    "derive_full_field_derivatives_available",
]

#: Why a row is not admissible. Growth-only: retiring a reason is a claim that
#: the situation cannot arise, which is a stronger statement than "we stopped
#: producing it".
EXCLUSION_REASONS: tuple[str, ...] = (
    "stencil_does_not_fit",
    "coordinate_missing",
    "derivative_unavailable",
    "observation_masked",
    "duplicate_coordinate",
)


def derive_full_field_derivatives_available(
    required_derivatives: Iterable[str], computed_derivatives: Iterable[str]
) -> bool:
    """RM-9: derived from what was computed, never asserted.

    A caller-supplied boolean is a claim about someone else's state, and the
    v0.37 C-5 defect is what happens when a declaration and an execution are
    allowed to disagree. There is deliberately no parameter anywhere in this
    module by which this value can be supplied.
    """
    required = {str(name) for name in required_derivatives}
    computed = {str(name) for name in computed_derivatives}
    if not required:
        raise ScopeValidationError(
            "required_derivatives is empty, so 'are they all available' has no "
            "content. An empty requirement trivially succeeds and would report "
            "full availability for a field with no derivatives at all."
        )
    return required <= computed


@dataclass(frozen=True)
class RowMask:
    """Which rows are admissible, by identity, and why the others are not."""

    #: Row identities in their original order. Order carries meaning (v0.36b),
    #: so it is preserved and never sorted.
    row_identities: tuple[str, ...]
    #: Identity -> reason, for excluded rows only. RM-7: an included row carries
    #: no entry here, so `None` and "included" cannot both mean admissible.
    exclusions: Mapping[str, str]
    full_field_derivatives_available: bool
    mask_id: str
    #: RM-13. When composition finds a row excluded by both inputs, the left
    #: reason is kept and the discarded one is recorded here. Dropping it
    #: silently would lose why a row was doubly excluded -- and "excluded for one
    #: reason" and "excluded for two" are different diagnostic situations.
    secondary_exclusions: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.mask_id, str) or not self.mask_id.strip():
            raise ScopeValidationError("mask_id must be a non-empty string.")
        identities = tuple(str(value) for value in self.row_identities)
        if not identities:
            raise ScopeValidationError(
                "row_identities is empty. A mask over no rows describes nothing, "
                "and would silently satisfy any application."
            )
        if len(set(identities)) != len(identities):
            duplicates = sorted({i for i in identities if identities.count(i) > 1})
            raise ScopeValidationError(
                f"row_identities repeats {duplicates}. Identity must identify: "
                f"two rows sharing one identity cannot be told apart, and a mask "
                f"over them would apply to both or neither with no way to say."
            )
        object.__setattr__(self, "row_identities", identities)

        if not isinstance(self.exclusions, Mapping):
            raise ScopeValidationError("exclusions must be a mapping.")
        exclusions: dict[str, str] = {}
        known = set(identities)
        for identity, reason in self.exclusions.items():
            if identity not in known:
                raise ScopeValidationError(
                    f"exclusions names row {identity!r}, which is not in "
                    f"row_identities. A reason for a row the mask does not cover "
                    f"describes nothing this mask can act on."
                )
            if reason not in EXCLUSION_REASONS:
                raise ScopeValidationError(
                    f"exclusion reason {reason!r} is not one of "
                    f"{list(EXCLUSION_REASONS)}. RM-5: every excluded row carries "
                    f"exactly one reason from the frozen vocabulary."
                )
            exclusions[str(identity)] = reason
        object.__setattr__(self, "exclusions", exclusions)

        if not isinstance(self.full_field_derivatives_available, bool):
            raise ScopeValidationError(
                "full_field_derivatives_available must be a bool, and must have "
                "been derived -- see derive_full_field_derivatives_available."
            )

        if not isinstance(self.secondary_exclusions, Mapping):
            raise ScopeValidationError("secondary_exclusions must be a mapping.")
        secondary: dict[str, str] = {}
        for identity, reason in self.secondary_exclusions.items():
            if identity not in exclusions:
                raise ScopeValidationError(
                    f"secondary_exclusions names {identity!r}, which carries no "
                    f"primary reason. A second reason for a row that was never "
                    f"excluded describes nothing."
                )
            if reason not in EXCLUSION_REASONS:
                raise ScopeValidationError(
                    f"secondary exclusion reason {reason!r} is not one of "
                    f"{list(EXCLUSION_REASONS)}."
                )
            secondary[str(identity)] = reason
        object.__setattr__(self, "secondary_exclusions", secondary)

    @property
    def included(self) -> tuple[str, ...]:
        """Admissible row identities, in original order."""
        return tuple(i for i in self.row_identities if i not in self.exclusions)

    @property
    def excluded(self) -> tuple[str, ...]:
        return tuple(i for i in self.row_identities if i in self.exclusions)

    def reason_counts(self) -> dict[str, int]:
        """RM-8: how many rows each reason excluded.

        Every frozen reason appears, including at zero. A mapping that omits the
        zeros cannot be told apart from one where the reason was never checked.
        """
        counts = dict.fromkeys(EXCLUSION_REASONS, 0)
        for reason in self.exclusions.values():
            counts[reason] += 1
        return counts

    def positions_in(self, row_identities: Sequence[str]) -> tuple[int, ...]:
        """RM-2/RM-3: derive positions against *this* row set, or refuse.

        Positions are computed here and never stored. If the supplied rows are
        not the rows this mask describes, it refuses -- silently intersecting is
        how a filtered matrix keeps a mask that no longer describes it.
        """
        supplied = tuple(str(value) for value in row_identities)
        if len(set(supplied)) != len(supplied):
            raise ScopeValidationError(
                "the supplied row identities repeat; positions would be ambiguous."
            )
        unknown = [identity for identity in supplied if identity not in set(self.row_identities)]
        if unknown:
            raise ScopeValidationError(
                f"mask {self.mask_id!r} does not describe rows {unknown[:5]} "
                f"({len(unknown)} total). Applying it here would mask rows it "
                f"has never seen."
            )
        missing = [i for i in self.row_identities if i not in set(supplied)]
        if missing:
            raise ScopeValidationError(
                f"mask {self.mask_id!r} describes {len(missing)} row(s) absent "
                f"from the supplied set, e.g. {missing[:5]}. The mask and the "
                f"matrix disagree about which rows exist."
            )
        include = set(self.included)
        return tuple(index for index, identity in enumerate(supplied) if identity in include)

    def as_dict(self) -> dict[str, Any]:
        return {
            "mask_id": self.mask_id,
            "row_count": len(self.row_identities),
            "included_count": len(self.included),
            "excluded_count": len(self.excluded),
            "reason_counts": self.reason_counts(),
            "doubly_excluded_count": len(self.secondary_exclusions),
            "full_field_derivatives_available": self.full_field_derivatives_available,
        }


def compose_masks(left: RowMask, right: RowMask, *, mask_id: str) -> RowMask:
    """RM-12/RM-13/RM-14: intersect two masks over the same row identities.

    Commutative and associative on the *included set*. Where both masks exclude
    a row, the left reason is kept and the fact that a second existed is
    preserved in ``secondary_exclusion_reasons`` on the result's payload --
    discarding it silently would lose why a row was doubly excluded.

    Because the retained reason depends on argument order, composition is
    commutative in what it *admits* and not in every recorded detail. That
    distinction is stated rather than papered over: the admissible set is what
    downstream consumes, and it is order-independent.
    """
    for name, value in (("left", left), ("right", right)):
        if not isinstance(value, RowMask):
            raise ScopeValidationError(f"{name} must be a RowMask.")
    if set(left.row_identities) != set(right.row_identities):
        raise ScopeValidationError(
            "masks describe different row-identity sets, so their intersection "
            "is not defined over a common population. Composing them would "
            "produce a mask describing rows one of them never saw."
        )
    if left.row_identities != right.row_identities:
        raise ScopeValidationError(
            "masks cover the same rows in different orders. Row order carries "
            "meaning, so composing them would silently adopt one order over the "
            "other."
        )

    exclusions = dict(left.exclusions)
    secondary: dict[str, str] = {}
    for identity, reason in right.exclusions.items():
        if identity in exclusions:
            # Excluded by both. Keep the left reason; record the discarded one.
            secondary[identity] = reason
        else:
            exclusions[identity] = reason

    return RowMask(
        row_identities=left.row_identities,
        exclusions=exclusions,
        # Derived, and conjunctive: a composition is fully available only if
        # both inputs were. Taking either alone would let one mask's ignorance
        # be reported as the composition's knowledge.
        full_field_derivatives_available=(
            left.full_field_derivatives_available and right.full_field_derivatives_available
        ),
        mask_id=mask_id,
        secondary_exclusions=secondary,
    )


def build_row_mask(
    lineages: Sequence[DesignRowLineage],
    exclusions_by_index: Mapping[int, str],
    *,
    required_derivatives: Iterable[str],
    computed_derivatives: Iterable[str],
    mask_id: str,
) -> RowMask:
    """Build a mask from row lineages, converting positions to identities once.

    Positions are accepted **here and only here** -- at construction, where the
    row set is unambiguous and present. Everything downstream carries
    identities, so a later filter or sort cannot silently re-point them.
    """
    if not isinstance(lineages, Sequence):
        raise ScopeValidationError("lineages must be a sequence of DesignRowLineage.")
    # No separate str/bytes guard: a string IS a Sequence, and its elements are
    # one-character strings that fail the per-element check below with a message
    # naming the actual type. Adding the guard anyway required widening the
    # annotation to admit `str`, which made mypy call it unreachable -- a guard
    # the type system says cannot fire is worse than one the loop makes
    # redundant.
    identities: list[str] = []
    for index, lineage in enumerate(lineages):
        if not isinstance(lineage, DesignRowLineage):
            raise ScopeValidationError(
                f"lineages[{index}] is {type(lineage).__name__}, not a DesignRowLineage."
            )
        identities.append(lineage.identity())

    exclusions: dict[str, str] = {}
    for index, reason in exclusions_by_index.items():
        if not isinstance(index, int) or isinstance(index, bool):
            raise ScopeValidationError("exclusion indices must be integers.")
        if not 0 <= index < len(identities):
            raise ScopeValidationError(
                f"exclusion index {index} is out of range for {len(identities)} rows."
            )
        exclusions[identities[index]] = reason

    return RowMask(
        row_identities=tuple(identities),
        exclusions=exclusions,
        full_field_derivatives_available=derive_full_field_derivatives_available(
            required_derivatives, computed_derivatives
        ),
        mask_id=mask_id,
    )
