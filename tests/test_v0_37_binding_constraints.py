"""The v0.37 constraints document must stay true about the code it describes.

`docs/planning/V0_37_BINDING_DESIGN_CONSTRAINTS.md` makes checkable claims about
this repository: that a vocabulary has certain members, that a type carries no
`seed`, that two schema keys are used a certain number of times. A planning doc
that quietly goes stale is worse than no planning doc, because it is still
quoted.

These tests are the reason the document is allowed to state measurements
inline. Every number in it that could drift is asserted here.

The specific failure this guards against is the one that produced the document:
a critique written against types that did not exist, endorsed without anyone
grepping for them. A document asserting facts about code should fail when the
code moves.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pdelie.actions import COEFFICIENT_RELATIONS, ProblemActionSpec
from pdelie.actions.interaction_rules import RULE_COUNT
from pdelie.symmetry.admissibility import BACKGROUND_TREATMENT_LABELS

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC = REPO_ROOT / "docs/planning/V0_37_BINDING_DESIGN_CONSTRAINTS.md"
SRC = REPO_ROOT / "src/pdelie"


def _doc() -> str:
    return DOC.read_text()


def test_document_exists_and_is_marked_binding() -> None:
    assert "**Status:** binding" in _doc()


# --- C-1: no seed in an action spec -----------------------------------------


def test_c1_actions_package_still_carries_no_seed() -> None:
    """The document claims this. If it stops being true, the claim must fail."""
    offenders = [
        path.relative_to(REPO_ROOT)
        for path in (SRC / "actions").rglob("*.py")
        if "seed" in path.read_text()
    ]
    assert not offenders, f"C-1 claims pdelie.actions has no seed; found in {offenders}"


def test_c1_problem_action_spec_has_no_seed_field() -> None:
    assert "seed" not in ProblemActionSpec.__dataclass_fields__


# --- C-3 / C-3a: the coefficient axis and its three layers ------------------


@pytest.mark.parametrize("value", sorted(COEFFICIENT_RELATIONS))
def test_c3_every_shipped_coefficient_relation_appears_in_the_document(value: str) -> None:
    """The doc tabulates layer 2's vocabulary; adding a value must update it."""
    assert f"`{value}`" in _doc(), f"COEFFICIENT_RELATIONS value {value!r} is undocumented"


@pytest.mark.parametrize("label", sorted(BACKGROUND_TREATMENT_LABELS))
def test_c3a_every_v0_34b_outcome_label_appears_in_the_document(label: str) -> None:
    """Layer 3's vocabulary is frozen; the doc must show it whole."""
    assert label in _doc(), f"v0.34b label {label!r} is missing from the layer table"


def test_c3a_names_all_three_layers_and_keeps_them_distinct() -> None:
    text = _doc()
    for phrase in ("Declared capability", "Claimed action", "Measured outcome"):
        assert phrase in text, phrase
    # The layer-1 tag is a real, shipped generator tag, not an invention.
    assert "nu_treatment_policy" in text


def test_c3a_layer_one_tag_is_actually_emitted_by_the_generators() -> None:
    """C-2 says treatment_policy must be generalised, not invented."""
    emitting = [
        path.name
        for path in (SRC / "data").glob("*.py")
        if "nu_treatment_policy" in path.read_text()
    ]
    assert len(emitting) >= 3, f"expected the v0.33d tag on several generators, got {emitting}"


def test_c3a_cross_layer_contradiction_rule_is_stated() -> None:
    """The real content of C-2: two layers permitted to disagree."""
    text = _doc()
    assert "cross-layer" in text.lower()
    assert "must be refused" in text


# --- C-2: the rename decision -----------------------------------------------


def test_c2_records_that_the_v0_34b_label_is_frozen_into_support_matrices() -> None:
    """Renaming it would break released specs; the doc must say where."""
    text = _doc()
    assert "support_matrix.v0_34.json" in text
    for name in ("support_matrix.v0_34.json", "support_matrix.v0_35.json"):
        assert (REPO_ROOT / "docs/specs" / name).is_file(), name


def test_c2_the_frozen_label_really_is_in_those_support_matrices() -> None:
    for name in ("support_matrix.v0_34.json", "support_matrix.v0_35.json"):
        text = (REPO_ROOT / "docs/specs" / name).read_text()
        assert "co_transforming_background_equivalence" in text, name


# --- C-5: the schema-key count ----------------------------------------------


def _count_key(key: str) -> int:
    pattern = re.compile(rf'"{key}"')
    return sum(len(pattern.findall(path.read_text())) for path in SRC.rglob("*.py"))


def test_c5_documented_schema_key_counts_are_current() -> None:
    """The doc's whole argument rests on these two numbers being close.

    If a future change makes one dominant, the "there is no standard" conclusion
    may no longer hold and the constraint should be revisited rather than quoted.
    """
    text = _doc()
    # The quoted pattern already excludes "summary_schema_version" -- the
    # opening quote cannot match mid-identifier -- so these are disjoint counts
    # and must not be subtracted from one another.
    plain = _count_key("schema_version")
    summary = _count_key("summary_schema_version")
    assert str(plain) in text, f"documented schema_version count is stale; now {plain}"
    assert str(summary) in text, f"documented summary_schema_version count is stale; now {summary}"
    assert abs(plain - summary) <= 5, (
        f"the counts have diverged ({plain} vs {summary}); C-5's premise that "
        f"neither is the standard should be re-examined"
    )


def test_c5_actions_payloads_still_carry_no_schema_key() -> None:
    spec = ProblemActionSpec(
        action_id="probe",
        equation_relation="same_equation",
        parameter_relation="preserved",
        domain_relation="preserved",
        boundary_relation="preserved",
    )
    payload = spec.as_dict()
    assert "schema_version" not in payload
    assert "summary_schema_version" not in payload


# --- consistency with the code the document cites ---------------------------


def test_the_referenced_interaction_rule_exists() -> None:
    """C-3 says a seventh rule refuses co_transformed with a null action."""
    assert RULE_COUNT == 7
    from pdelie.actions import validate_action_spec
    from pdelie.errors import ScopeValidationError

    spec = ProblemActionSpec(
        action_id="unpaired",
        equation_relation="same_equation",
        parameter_relation="preserved",
        domain_relation="preserved",
        boundary_relation="preserved",
        coefficient_relation="co_transformed",
    )
    with pytest.raises(ScopeValidationError, match="co_transformed"):
        validate_action_spec(spec)


def test_document_does_not_claim_absent_types_exist() -> None:
    """It must keep saying these are absent for as long as they are absent."""
    absent = ("ProblemActionBundle", "ExpectedResidualRelation", "ActionExecutionConfig")
    for name in absent:
        found = [p for p in SRC.rglob("*.py") if name in p.read_text()]
        assert not found, (
            f"{name} now exists in {found}; the document says it does not and "
            f"must be updated"
        )


# --- status vocabulary and forward scoping ----------------------------------

#: Every constraint carries exactly one of these. A constraint with no status is
#: an ambiguous item, which is the thing the status column exists to remove.
STATUS_VALUES = ("satisfied_in_v0_36", "binds_absent_design", "resolves_in_v0_37a")

#: Deliberately forward-scoped: neither names a defect in shipped code, so
#: neither blocks the v0.36.0 tag.
FORWARD_SCOPED = ("C-2", "C-5")

CONSTRAINT_IDS = ("C-1", "C-2", "C-3", "C-3a", "C-4", "C-5", "C-6")


def test_every_constraint_section_declares_a_status() -> None:
    """An unmarked constraint reads as blocking when it may not be."""
    text = _doc()
    sections = re.findall(r"^## (C-\d+a?) — .*$", text, flags=re.MULTILINE)
    assert set(sections) == set(CONSTRAINT_IDS), sections
    for block in re.split(r"^## ", text, flags=re.MULTILINE)[1:]:
        if not block.startswith("C-"):
            continue
        identifier = block.split(" ", 1)[0]
        declared = [value for value in STATUS_VALUES if f"`{value}`" in block]
        assert declared, f"{identifier} declares no status"


def test_the_summary_table_has_a_status_column() -> None:
    text = _doc()
    assert "| # | Constraint | Status |" in text
    for value in STATUS_VALUES:
        assert f"`{value}`" in text, value


@pytest.mark.parametrize("identifier", FORWARD_SCOPED)
def test_forward_scoped_items_say_they_do_not_block_the_release(identifier: str) -> None:
    """C-2 and C-5 ship open, explicitly, rather than ambiguously."""
    block = next(
        part
        for part in re.split(r"^## ", _doc(), flags=re.MULTILINE)[1:]
        if part.startswith(f"{identifier} —")
    )
    assert "`resolves_in_v0_37a`" in block, identifier
    assert "Does not block v0.36.0" in block, identifier


def test_forward_scoped_items_name_their_resolution_vehicle() -> None:
    """A deferred decision with no owner is a decision nobody makes."""
    text = _doc()
    assert "V0_37A_HYPOTHESIS_FREEZE.md" in text
    assert "Resolution vehicle" in text
    # Each forward-scoped item must have numbered decisions, not a vague pointer.
    vehicle = text.split("Resolution vehicle", 1)[1]
    for identifier in FORWARD_SCOPED:
        assert f"**{identifier} — `resolves_in_v0_37a`.**" in vehicle, identifier


def test_no_constraint_is_marked_satisfied_without_a_test_backing_it() -> None:
    """satisfied_in_v0_36 is the only status that makes a claim about code.

    C-1, C-3, C-3a each have assertions above. If a future constraint is marked
    satisfied, it needs the same.
    """
    text = _doc()
    satisfied = [
        part.split(" ", 1)[0]
        for part in re.split(r"^## ", text, flags=re.MULTILINE)[1:]
        if part.startswith("C-") and "`satisfied_in_v0_36`" in part
    ]
    assert set(satisfied) == {"C-1", "C-3", "C-3a"}, (
        f"a constraint changed status to satisfied_in_v0_36 ({satisfied}); add "
        f"the assertion that backs it before updating this list"
    )
