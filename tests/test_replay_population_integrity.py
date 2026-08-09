"""Adversarial tests for the Gate F row population.

Every test here mutates something and asserts the guard **rejects** it. A test
that only checks the happy path proves nothing: the population that broke run
`31326189317` satisfied every check written at the time.

What actually happened
======================

The gate swept derivative orders 1-4. The v0.38b freeze supports 1-3, so the
d=4 rows had to be labelled exploratory. The repair threaded ``order=`` through
the call sites *with a regex*. It matched the ``floor_regime`` and ``none_kind``
constructors and missed the two ``signal_regime`` ones, so ten rows -- 2 kinds x
5 functions, at d=4 -- emitted ``derivative_order: null``.

F-4 then read: *no gate row lies outside derivative orders 1-3*. It treated
``None`` as in scope. So the ten rows were gate evidence, F-4 passed, and F-7's
worst observed value landed on one of them.

**F-4 could not have failed.** Not "did not" -- could not. The rows it was meant
to exclude were invisible to it in exactly the way that made them dangerous.

So the tests below are written against the mutation, not the fixture.
"""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from replay_contracts import (  # noqa: E402
    NON_ORDER_PARAMETERIZED_FAMILIES,
    ORDER_PARAMETERIZED_FAMILIES,
    ContractViolation,
    ReplayRowSpec,
    declaration_for,
    parse_row_id_for_audit,
)

EXPECTED = json.loads((REPO_ROOT / "configs/gate_f_expected_rows.json").read_text())
SCOPE = json.loads((REPO_ROOT / "configs/gate_f_replay_scope.json").read_text())


def _valid_gate_row() -> ReplayRowSpec:
    return ReplayRowSpec(
        workload_id="fornberg_uniform_polynomial_exactness",
        workload_family="fornberg",
        order_parameterized=True,
        derivative_order=2,
        portability_class="tolerance_numeric",
        gate_use="gate_evidence",
        label="n7_i3",
    )


# --------------------------------------------------------------------------
# 1-6: the construction-time invariants. Each mutation must raise.
# --------------------------------------------------------------------------


def test_1_an_order_parameterized_row_cannot_omit_its_order() -> None:
    """**The exact defect.** Ten rows did this and were counted as gate evidence."""
    with pytest.raises(ContractViolation, match="may not be None"):
        replace(_valid_gate_row(), derivative_order=None)


def test_2_a_non_order_parameterized_row_cannot_carry_an_order() -> None:
    """The converse hole. Without it, a mislabelled family passes silently."""
    with pytest.raises(ContractViolation, match="carries no derivative order"):
        ReplayRowSpec(
            workload_id="weak_overlap_declaration",
            workload_family="weak",
            order_parameterized=False,
            derivative_order=2,
            portability_class="tolerance_numeric",
            gate_use="gate_evidence",
            label="w0",
        )


def test_3_derivative_order_four_cannot_be_gate_evidence() -> None:
    """d=4 is outside the v0.38b freeze. The row is kept, never as evidence."""
    with pytest.raises(ContractViolation, match="outside the frozen scope"):
        replace(_valid_gate_row(), derivative_order=4)


def test_4_gate_evidence_outside_one_two_three_is_refused() -> None:
    """Including orders nobody has yet swept. A future d=5 must not default in."""
    for order in (0, 5, 9):
        with pytest.raises(ContractViolation):
            replace(_valid_gate_row(), derivative_order=order)


def test_5_an_unknown_family_is_refused_not_defaulted() -> None:
    with pytest.raises(ContractViolation, match="unknown workload family"):
        replace(_valid_gate_row(), workload_family="spectral")


def test_6_an_unknown_portability_class_is_refused() -> None:
    with pytest.raises(ContractViolation, match="portability_class"):
        replace(_valid_gate_row(), portability_class="probably_fine")


# --------------------------------------------------------------------------
# 7-9: the dependency direction. row_id is generated, never a source.
# --------------------------------------------------------------------------


def test_7_row_id_is_generated_from_the_typed_order() -> None:
    assert _valid_gate_row().row_id == "n7_i3_d2"
    assert replace(_valid_gate_row(), derivative_order=1).row_id == "n7_i3_d1"


def test_8_the_audit_parser_is_never_the_source_of_an_order() -> None:
    """It may confirm the display string. It may not supply the value.

    Guarded structurally: no module that makes a gate decision may assign from
    ``parse_row_id_for_audit``. Making the row key authoritative would rebuild
    the same defect on a new foundation -- a display identifier is not a data
    contract, and a row key can be renamed by a formatting change.
    """
    assert parse_row_id_for_audit("expx3_d4") == 4
    assert parse_row_id_for_audit("case0") is None

    for name in ("compare_replay.py", "replay_workloads.py"):
        tree = ast.parse((REPO_ROOT / "scripts" / name).read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            value = node.value
            called = isinstance(value, ast.Call) and (
                getattr(value.func, "id", None) == "parse_row_id_for_audit"
            )
            if called:
                targets = [getattr(t, "id", "") for t in node.targets]
                assert all("audit" in t or "displayed" in t for t in targets), (
                    f"{name}:{node.lineno} assigns the parsed row-key order to "
                    f"{targets}, which reads like a semantic value. The order "
                    f"must come from the typed spec."
                )


def test_9_a_row_keys_displayed_order_agrees_with_its_typed_order() -> None:
    """Across the whole frozen manifest, not a sample."""
    for row in EXPECTED["rows"]:
        displayed = parse_row_id_for_audit(row["row_key"])
        if row["order_parameterized"]:
            assert displayed == row["derivative_order"], (
                f"{row['workload']}/{row['row_key']} displays {displayed} but "
                f"carries {row['derivative_order']}"
            )
        else:
            assert row["derivative_order"] is None


# --------------------------------------------------------------------------
# 10-12: the population itself, and the checks over it.
# --------------------------------------------------------------------------


def test_10_no_gate_row_in_the_frozen_manifest_is_out_of_scope() -> None:
    """The assertion F-4 was meant to make, over the artifact it now governs."""
    supported = set(SCOPE["supported_derivative_orders"])
    offenders = [
        f"{r['workload']}/{r['row_key']}@d={r['derivative_order']}"
        for r in EXPECTED["rows"]
        if r["gate_use"] == "gate_evidence"
        and r["derivative_order"] is not None
        and r["derivative_order"] not in supported
    ]
    assert not offenders, offenders


def test_11_every_null_order_gate_row_belongs_to_a_declared_non_order_family() -> None:
    """F-4a. The check that makes F-4 non-vacuous.

    ``None`` is acceptable only where a *declared* contract says the family has
    no derivative order. It is never acceptable merely because the value is
    absent -- that reading is what made the ten leaked rows invisible.
    """
    offenders = [
        f"{r['workload']}/{r['row_key']} (family {r['workload_family']})"
        for r in EXPECTED["rows"]
        if r["gate_use"] == "gate_evidence"
        and r["derivative_order"] is None
        and r["workload_family"] not in NON_ORDER_PARAMETERIZED_FAMILIES
    ]
    assert not offenders, (
        f"gate rows carry no derivative order but belong to an order-"
        f"parameterised family: {offenders}"
    )

    # And the guard is not vacuous in the other direction: such rows exist, so
    # the check has a real population to run over.
    null_order = [r for r in EXPECTED["rows"] if r["derivative_order"] is None]
    assert len(null_order) == 58, (
        f"expected 58 legitimately order-free rows, found {len(null_order)}. "
        f"If this changed, the manifest changed and needs re-review."
    )


def test_12_the_counts_are_derived_from_the_manifest_not_asserted() -> None:
    """The corrected partition, and the record of what it replaced.

    239/47 was the defect's own arithmetic. Re-asserting it would have frozen
    the bug into the contract that was supposed to catch it.
    """
    rows = EXPECTED["rows"]
    gate = [r for r in rows if r["gate_use"] == "gate_evidence"]
    expl = [r for r in rows if r["gate_use"] == "exploratory_only"]

    assert EXPECTED["totals"] == {
        "all_rows": len(rows),
        "gate_evidence": len(gate),
        "exploratory_only": len(expl),
    }, "the manifest's stated totals disagree with its own row list"

    assert (len(gate), len(expl)) == (229, 57)
    assert len(rows) == 286, (
        "the total must be unchanged: the correction reclassified ten rows, it "
        "did not add or delete any measurement"
    )
    assert SCOPE["row_counts"]["superseded_gate_count"] == 239
    assert len(gate) + 10 == 239, (
        "the correction must account for exactly the ten leaked rows: "
        "2 reference kinds x 5 functions at derivative order 4"
    )


# --------------------------------------------------------------------------
# Supporting invariants
# --------------------------------------------------------------------------


def test_the_families_are_declared_per_workload_not_parsed_from_the_name() -> None:
    """``fornberg_fn_12_uniform_spacing_ratio`` is the case that proves it.

    It carries the ``fornberg`` prefix and measures the *grid's* spacing ratio,
    which has no derivative order. A prefix heuristic mislabels it as
    order-parameterised, and the typed contract rejected exactly that on its
    first run -- before the code shipped.
    """
    family, order_parameterized = declaration_for("fornberg_fn_12_uniform_spacing_ratio")
    assert family == "grid"
    assert order_parameterized is False

    family, order_parameterized = declaration_for("fornberg_uniform_polynomial_exactness")
    assert family == "fornberg"
    assert order_parameterized is True


def test_an_undeclared_workload_is_refused() -> None:
    with pytest.raises(ContractViolation, match="no entry in workload_declarations"):
        declaration_for("fornberg_something_invented_later")


def test_every_frozen_workload_is_declared() -> None:
    assert set(SCOPE["workload_declarations"]) == set(SCOPE["workload_ids"])


def test_the_family_sets_are_disjoint_and_cover_every_declaration() -> None:
    assert not (ORDER_PARAMETERIZED_FAMILIES & NON_ORDER_PARAMETERIZED_FAMILIES)
    declared = {d["family"] for d in SCOPE["workload_declarations"].values()}
    assert declared <= (ORDER_PARAMETERIZED_FAMILIES | NON_ORDER_PARAMETERIZED_FAMILIES)


def test_the_comparator_counts_bits_independently_of_floor_classification() -> None:
    """F-6 asks whether the bits matched. Floor selects which statistic is
    meaningful, and has no bearing on that question.

    The previous ordering classified a comparison as floor and skipped it before
    counting, so the bitwise denominator excluded precisely the small-magnitude
    rows a libm change would perturb first.
    """
    text = (REPO_ROOT / "scripts/compare_replay.py").read_text()
    for counter in (
        "numeric_comparisons_total",
        "numeric_comparisons_bitwise_equal",
        "numeric_comparisons_bitwise_different",
        "signal_comparisons",
        "floor_comparisons",
        "not_comparable",
    ):
        assert counter in text, f"{counter} is missing from the comparator"

    total = text.index("numeric_comparisons_total += 1")
    floor = text.index("floor_comparisons += 1")
    assert total < floor, (
        "the bitwise counter must increment before the floor branch, or floor "
        "rows leave the denominator"
    )


def test_the_comparator_requires_set_equality_not_a_count() -> None:
    """A count check passes on the wrong 229 rows.

    The broken population had the correct total (286) at every moment.
    """
    text = (REPO_ROOT / "scripts/compare_replay.py").read_text()
    assert "EXPECTED_KEYS" in text and "EXPECTED_GATE_KEYS" in text
    assert "!= EXPECTED_KEYS" in text
    assert "!= EXPECTED_GATE_KEYS" in text, "F-3a partition check is absent"


def test_the_comparator_does_not_import_the_generator() -> None:
    """Independence. A shared helper cannot certify its own output.

    ``parse_row_id_for_audit`` is duplicated in both deliberately: an error
    common to generator and comparator would otherwise cancel itself out.
    """
    tree = ast.parse((REPO_ROOT / "scripts/compare_replay.py").read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module not in ("replay_workloads", "replay_contracts"), (
                f"compare_replay imports {node.module}; it must read the frozen "
                f"artifacts instead, so a defect in the generator cannot make "
                f"the comparator agree with it"
            )


# --------------------------------------------------------------------------
# Driving the comparator itself.
#
# The tests above assert things about the frozen *manifest*. That is not
# enough, and a mutation run proved it: disabling F-4a inside
# ``compare_replay.structural_checks`` left all of them green. Checking the
# artifact is not checking the checker -- which is the whole defect class this
# module exists for, reproduced one level up.
#
# These build synthetic runner payloads and assert the comparator rejects them.
# --------------------------------------------------------------------------


def _payload(rows: list[dict]) -> dict:
    return {
        "platform": {"system": "Linux", "machine": "x86_64", "python": "3.12.10"},
        "counts": {"total": len(rows), "v0_38b": 0, "v0_38c": 0, "v0_38d": 0},
        "rows": rows,
    }


def _frozen_rows() -> list[dict]:
    """The exact frozen population, as a runner would emit it."""
    return [
        {
            "workload": r["workload"],
            "row_key": r["row_key"],
            "workload_family": r["workload_family"],
            "order_parameterized": r["order_parameterized"],
            "derivative_order": r["derivative_order"],
            "gate_use": r["gate_use"],
            "portability_class": r["portability_class"],
            "scope": (
                "in_frozen_scope"
                if r["gate_use"] == "gate_evidence"
                else "outside_frozen_scope"
            ),
        }
        for r in EXPECTED["rows"]
    ]


def _check(rows: list[dict]) -> list[str]:
    import compare_replay

    return compare_replay.structural_checks({"Linux/x86_64-py3.12.10": _payload(rows)})


def test_the_comparator_accepts_the_frozen_population() -> None:
    """The control. Without it, every rejection test below could pass because
    the comparator rejects everything."""
    assert _check(_frozen_rows()) == []


def test_the_comparator_rejects_the_exact_leaked_population() -> None:
    """**The regression test for run 31326189317.**

    Reconstructs what that run emitted: ten ``deriv_ref_signal_regime_*`` rows
    at d=4, relabelled as gate evidence with ``derivative_order: null``. The
    total stays 286 and every workload is present, so every check that existed
    at the time still passes. F-4a is what refuses it.
    """
    rows = _frozen_rows()
    leaked = 0
    for row in rows:
        if row["workload"].startswith("deriv_ref_signal_regime") and (
            row["derivative_order"] == 4
        ):
            row["derivative_order"] = None
            row["gate_use"] = "gate_evidence"
            row["scope"] = "in_frozen_scope"
            leaked += 1
    assert leaked == 10, f"expected to reconstruct 10 leaked rows, made {leaked}"

    problems = _check(rows)
    assert problems, (
        "the comparator accepted the population that broke run 31326189317"
    )
    assert any("order-parameterised" in p for p in problems), problems


def test_the_comparator_rejects_a_d4_row_admitted_as_gate_evidence() -> None:
    rows = _frozen_rows()
    for row in rows:
        if row["derivative_order"] == 4:
            row["gate_use"] = "gate_evidence"
            row["scope"] = "in_frozen_scope"
            break
    problems = _check(rows)
    assert any("outside the frozen scope" in p or "partition" in p for p in problems), problems


def test_the_comparator_rejects_a_changed_partition_at_the_same_total() -> None:
    """F-3a. The total is untouched; only the split moves."""
    rows = _frozen_rows()
    for row in rows:
        if row["gate_use"] == "exploratory_only":
            row["gate_use"] = "gate_evidence"
            break
    assert len(rows) == 286
    assert any("partition" in p for p in _check(rows)), _check(rows)


def test_the_comparator_rejects_a_missing_row() -> None:
    rows = _frozen_rows()[:-1]
    assert any("differs from the frozen manifest" in p for p in _check(rows))


def test_the_comparator_rejects_an_extra_row() -> None:
    rows = _frozen_rows()
    rows.append({**rows[0], "row_key": rows[0]["row_key"] + "_extra"})
    assert any("differs from the frozen manifest" in p for p in _check(rows))


def test_the_comparator_rejects_a_gate_row_with_no_family_at_all() -> None:
    """Scope that cannot be established is refused, never defaulted."""
    rows = _frozen_rows()
    for row in rows:
        if row["gate_use"] == "gate_evidence" and row["derivative_order"] is None:
            del row["workload_family"]
            break
    assert any("cannot be established" in p for p in _check(rows)), _check(rows)


def test_the_comparator_rejects_a_row_key_disagreeing_with_its_typed_order() -> None:
    """A formatting bug must not pass silently, and must not be believed."""
    rows = _frozen_rows()
    for row in rows:
        if row["derivative_order"] == 2:
            row["row_key"] = row["row_key"].replace("_d2", "_d3")
            break
    problems = _check(rows)
    assert problems, "a row key contradicting its typed order was accepted"
