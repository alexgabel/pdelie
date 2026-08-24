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
    """The exact frozen population, as a runner would emit it.

    Carries the numeric values the manifest freezes. Before the starved-
    population defect was found this fixture emitted metadata only, and every
    test built on it therefore exercised a population the gate could not have
    compared -- which is precisely the defect it failed to catch.
    """
    rows = [
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
    for row, spec in zip(rows, EXPECTED["rows"], strict=True):
        for field in spec.get("numeric_fields", []):
            row[field] = 1.0
        if spec.get("has_metric_spec"):
            row["error_metric_spec_id"] = "replay_linf_absolute"
        row["reporting_regime"] = "signal"
        row["reference_scale"] = 1.0
    return rows


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
    """Flipping an exploratory row to gate evidence trips the PARTITION check.

    Asserted specifically, because the looser form -- accepting either the
    partition message or the scope message -- let this test stand in for a
    check of F-4 that it never performed. See the test below.
    """
    rows = _frozen_rows()
    for row in rows:
        if row["derivative_order"] == 4:
            row["gate_use"] = "gate_evidence"
            row["scope"] = "in_frozen_scope"
            break
    problems = _check(rows)
    assert any("partition" in p for p in problems), problems


def test_f4_rejects_an_out_of_scope_order_on_its_own() -> None:
    """F-4's own branch, exercised where nothing else can fire first.

    ``scripts/verify_guard_nonvacuity.py`` found F-4 to be VACUOUS: removing
    the comparator's order check turned zero tests red. Not because F-4 was
    wrong, but because every mutation reaching it tripped F-3 or F-3a first and
    short-circuited. A guard that no input can reach is dead code wearing a
    criterion's name.

    So this mutates the ORDER on a row that is already frozen gate evidence,
    leaving `row_key` and `gate_use` untouched:

      * F-3  set equality  -- row identity unchanged, passes
      * F-3a partition     -- gate_use unchanged, passes
      * F-4  order in {1,2,3} -- 4 is not, FIRES

    and asserts the scope message specifically, not merely that something
    complained.
    """
    rows = _frozen_rows()
    target = next(
        r for r in rows
        if r["gate_use"] == "gate_evidence" and r["derivative_order"] == 2
    )
    target["derivative_order"] = 4

    problems = _check(rows)
    scope_failures = [p for p in problems if "outside the frozen scope" in p]
    assert scope_failures, (
        f"F-4 did not fire on a gate row at derivative order 4. Other problems "
        f"reported: {problems}"
    )
    assert target["row_key"] in scope_failures[0]


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


def test_the_comparator_asserts_both_accounting_identities() -> None:
    """Both, and with ``fields_absent`` kept out of them.

    The first version of these counters asserted only
    ``total == equal + different``. The second identity was *documented* but
    not checked, and it was documented wrongly: it included ``fields_absent``,
    which counts row/field slots holding no pair to compare rather than
    comparisons. The Gate F replay of 2026-08-09 exposed it as
    ``325 != 76 + 249 + 1049``.

    That is the conflation defect again -- "we could not compare these two
    values" merged with "there were no two values" -- inside the counter set
    introduced to end conflation. Hence both identities are now executed.
    """
    text = (REPO_ROOT / "scripts/compare_replay.py").read_text()
    assert "fields_absent" in text, "absent fields are still counted as comparisons"
    assert text.count("assert total == (") == 2, (
        "both accounting identities must be asserted, not merely described"
    )
    assert 'r["signal_comparisons"] + r["floor_comparisons"]' in text

    absent_at = text.index("fields_absent += 1")
    nc_at = text.index("not_comparable += 1")
    assert absent_at < nc_at, (
        "the absent-field branch must be distinct from, and precede, the "
        "zero-scale branch; merging them is what produced 1049"
    )


# --------------------------------------------------------------------------
# Behavioural mutations for the bitwise accounting.
#
# The test above this block asserts the comparator's SHAPE: that the six
# counters exist and that the bitwise increment precedes the floor branch.
# That is worth keeping, but it is not a test of behaviour -- it would pass on
# a comparator whose counters were correctly named, correctly ordered, and
# wrong.
#
# Substituting a shape assertion for a behaviour assertion is the same defect
# as F-4 accepting `None`: the check cannot fail for the reason it names. So
# the three below drive `compare()` with constructed floor-regime values and
# read the counters back.
# --------------------------------------------------------------------------


def _floor_row(row_key: str, absolute_error: float) -> dict:
    """A gate row whose numeric value sits at the numerical floor.

    ``reference_scale`` of 1.0 with an error near 1e-18 is far below
    ``sqrt(eps) * scale``, so the comparator classifies it as floor and the
    relative statistic is meaningless. Whether the BITS matched is still a
    well-posed question -- more so here than anywhere else, since these are the
    values a libm change perturbs first.
    """
    return {
        "workload": "deriv_ref_floor_regime",
        "row_key": row_key,
        "workload_family": "deriv",
        "order_parameterized": True,
        "derivative_order": 2,
        "gate_use": "gate_evidence",
        "scope": "in_frozen_scope",
        "portability_class": "tolerance_numeric",
        "error_metric_spec_id": "replay_linf_absolute",
        "reporting_regime": "floor",
        "reference_scale": 1.0,
        "absolute_error": absolute_error,
    }


def _compare(left_error: float, right_error: float) -> dict:
    import compare_replay

    return compare_replay.compare(
        "Linux/x86_64-py3.12.10", _payload([_floor_row("f0_d2", left_error)]),
        "Linux/x86_64-py3.12.13", _payload([_floor_row("f0_d2", right_error)]),
    )


def test_9_a_floor_classified_equal_value_still_counts_toward_the_denominator() -> None:
    """F-6's denominator must not be narrowed by floor classification.

    Previously the comparator classified a comparison as floor and `continue`d
    *before* counting it, so the bitwise denominator silently excluded exactly
    the small-magnitude rows most likely to differ across libm versions.
    """
    result = _compare(1e-18, 1e-18)
    assert result["numeric_comparisons_total"] == 1, result
    assert result["numeric_comparisons_bitwise_equal"] == 1, result
    assert result["numeric_comparisons_bitwise_different"] == 0, result
    assert result["floor_comparisons"] == 1, "the row should still classify as floor"
    assert result["signal_comparisons"] == 0


def test_10_a_floor_classified_unequal_value_breaks_bitwise_identity() -> None:
    """F-6 must FAIL here. This is the case the old ordering silently passed.

    Two different bits at the floor is a real cross-version difference. Under
    the previous accounting it was invisible: the comparison never reached a
    counter, so `bitwise_identical` equalled the (reduced) total and the pair
    read as identical.
    """
    result = _compare(1e-18, 2e-18)
    assert result["numeric_comparisons_total"] == 1, result
    assert result["numeric_comparisons_bitwise_different"] == 1, (
        "a floor-classified value differing in its bits was not counted as a "
        "bitwise difference, so F-6 would pass on a real cross-version change"
    )
    assert result["numeric_comparisons_bitwise_equal"] == 0, result
    assert result["bitwise_differences"], "the differing row must be named"
    assert "absolute_error" in result["bitwise_differences"][0]

    # And the floor classification is still applied -- it governs which
    # statistic is meaningful, not whether the bits were compared.
    assert result["floor_comparisons"] == 1
    assert result["worst_scaled_difference"] == 0.0, (
        "a floor row must contribute nothing to F-7's scaled-difference "
        "statistic; that part of the separation must survive"
    )


def test_6_a_duplicated_row_identity_is_rejected() -> None:
    """The comparator has carried this check untested.

    A duplicate makes every count ambiguous: the same identity appearing twice
    can satisfy a total while corrupting a pairing.
    """
    rows = _frozen_rows()
    rows.append(dict(rows[0]))
    problems = _check(rows)
    assert any("duplicate" in p for p in problems), problems


# --------------------------------------------------------------------------
# The starved-population defect.
#
# An external audit found, and this reproduced, that renaming the numeric
# fields in replay_workloads.py produced a run where all 229 gate rows paired,
# `numeric_comparisons_total` was 0, the accounting identity held at
# `0 == 0 + 0`, and the comparator exited 0 declaring cross-platform agreement
# HAVING COMPARED NOTHING.
#
# Every check that existed passed. The row set was right, the partition was
# right, the orders were right, the discrete fields agreed. What was missing
# was any assertion that the rows still carried the values the gate exists to
# compare.
# --------------------------------------------------------------------------


def test_renaming_every_numeric_field_is_refused() -> None:
    """The exact reproduction. 229 rows pair; nothing is compared."""
    rows = _frozen_rows()
    for row in rows:
        for field in list(row):
            if field in {
                "absolute_error", "relative_error", "linear_exactness_relative",
                "ratio_minus_one", "spacing_ratio", "overlap_fraction",
            }:
                row[field + "_RENAMED"] = row.pop(field)
    problems = _check(rows)
    assert problems, "a population carrying no comparable value was accepted"
    assert any("carries numeric fields []" in p for p in problems), problems


def test_dropping_one_numeric_field_is_refused() -> None:
    """Partial starvation. Harder than a rename, because most rows still work."""
    rows = _frozen_rows()
    for row in rows:
        if row.get("relative_error") is not None:
            row["relative_error"] = None
            break
    problems = _check(rows)
    assert any("frozen as" in p for p in problems), problems


def test_losing_the_metric_spec_is_refused() -> None:
    """`None != None` is False, so two rows that both lost it compare as equal.

    The metric-presence expectation is FROZEN rather than inferred: the obvious
    rule -- a numeric value requires an error metric -- is wrong, and the
    archived Gate F evidence disproved it on the first run.
    `weak_overlap_declaration` carries `overlap_fraction`, a diagnostic
    quantity, and needs no metric spec.
    """
    rows = _frozen_rows()
    for row in rows:
        if row.get("error_metric_spec_id") is not None:
            row["error_metric_spec_id"] = None
            break
    assert any("error_metric_spec_id" in p for p in _check(rows)), _check(rows)


def test_a_diagnostic_quantity_is_not_required_to_carry_a_metric_spec() -> None:
    """The false-positive the control caught, asserted so it cannot return."""
    overlap = [
        r for r in EXPECTED["rows"] if r["workload"] == "weak_overlap_declaration"
    ]
    assert overlap, "the fixture this guards has disappeared"
    for row in overlap:
        assert "overlap_fraction" in row["numeric_fields"]
        assert row["has_metric_spec"] is False, (
            "overlap_fraction is a diagnostic quantity, not an error; requiring "
            "a metric spec here would reject the real archived evidence"
        )


def test_the_expected_comparison_count_matches_the_closing_replay() -> None:
    """325 is what run 31328966332 actually compared.

    The frozen expectation is not a fresh invention: it agrees with the
    population that closed Gate F.
    """
    assert EXPECTED["expected_gate_numeric_comparisons"] == 325
    assert EXPECTED["expected_gate_rows_with_no_numeric_value"] == 12


def test_the_floor_is_equality_not_a_positive_count() -> None:
    """`> 0` passes on 1 comparison where 325 were owed.

    That is the same defect with a smaller number, so the comparator asserts
    equality against the frozen expectation.
    """
    text = (REPO_ROOT / "scripts/compare_replay.py").read_text()
    assert "EXPECTED_GATE_NUMERIC_COMPARISONS" in text
    assert "!= EXPECTED_GATE_NUMERIC_COMPARISONS" in text, (
        "the comparison-count floor is not an equality check"
    )
    # Matched as separate fragments: the sentence wraps in the source, and a
    # contiguous match would fail on a reflow rather than on a regression.
    # This is the third time an assertion here has been written against wrapped
    # source text.
    assert "starved" in text
    assert "did not perform the" in text
