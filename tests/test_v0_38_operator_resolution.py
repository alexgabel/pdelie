"""v0.38 §4: one enum, one resolver, one resolved object, and a hard block.

The defect: ``ProblemInstanceSpec.equation_form`` and
``parameter_tags["nu_form"]`` both described the operator and nothing reconciled
them. v0.38e derived one from the other inside the benchmark, which fixed that
consumer and left the next one free to derive it differently.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie.errors import ScopeValidationError
from pdelie.residuals.operator_resolution import (
    COEFFICIENT_FORM_TO_EQUATION_FORM,
    RESOLUTION_SOURCES,
    EquationForm,
    ResolvedResidualOperator,
    provenance_equation_form,
    resolve_residual_operator,
)


def _provenance(form: str | None) -> dict:
    tags: dict = {"nu": 0.1}
    if form is not None:
        tags["nu_form"] = form
    return {"parameter_tags": tags}


# --------------------------------------------------------------------------
# The enum is the closed vocabulary
# --------------------------------------------------------------------------


def test_the_enum_is_closed_and_serialises_to_its_value() -> None:
    assert {form.value for form in EquationForm} == {"conservative", "nonconservative"}
    assert json.dumps({"f": EquationForm.CONSERVATIVE}) == '{"f": "conservative"}'
    assert EquationForm.CONSERVATIVE == "conservative", (
        "a consumer comparing against the plain string must keep working"
    )


def test_an_unknown_form_string_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="not an equation form"):
        resolve_residual_operator(family="heat_1d", declared_form="semi_conservative")


# --------------------------------------------------------------------------
# One mapping, not two
# --------------------------------------------------------------------------


def test_the_coefficient_form_mapping_exists_in_exactly_one_place() -> None:
    """v0.38e kept a second copy inside the benchmark. It is gone."""
    import ast
    from pathlib import Path

    src = Path(__file__).resolve().parents[1] / "src" / "pdelie"
    holders: list[str] = []
    for path in sorted(src.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            keys = {k.value for k in node.keys if isinstance(k, ast.Constant)}
            if {"conservative_divergence", "nonconservative_nu_uxx"} <= keys:
                holders.append(path.name)
    assert holders == ["operator_resolution.py"], (
        f"the coefficient-form mapping appears in {holders}. Two copies is how "
        f"two consumers come to describe different operators."
    )


def test_the_mapping_covers_every_declared_form() -> None:
    assert set(COEFFICIENT_FORM_TO_EQUATION_FORM.values()) == set(EquationForm)


# --------------------------------------------------------------------------
# Disagreement blocks -- neither source is silently preferred
# --------------------------------------------------------------------------


def test_disagreement_blocks_and_names_both_sources() -> None:
    with pytest.raises(ScopeValidationError) as excinfo:
        resolve_residual_operator(
            family="heat_1d",
            declared_form="nonconservative",
            field_provenance=_provenance("conservative_divergence"),
        )
    message = str(excinfo.value)
    assert "nonconservative" in message and "conservative" in message
    assert "Neither is chosen" in message


def test_disagreement_blocks_even_when_numerically_harmless() -> None:
    """A constant coefficient makes the forms coincide. It still blocks.

    This is the case that let the defect survive a release: three of the five
    v0.37c cases could not have detected it. "Currently harmless" is not
    "correct", and the harm arrives with the first variable coefficient.
    """
    with pytest.raises(ScopeValidationError) as excinfo:
        resolve_residual_operator(
            family="heat_1d",
            declared_form="nonconservative",
            field_provenance=_provenance("conservative_divergence"),
            coefficient_is_constant=True,
        )
    message = str(excinfo.value)
    assert "coincide numerically" in message
    assert "still wrong" in message


def test_the_refusal_says_when_numbers_ARE_affected() -> None:
    with pytest.raises(ScopeValidationError, match=r"nu' \* u_x"):
        resolve_residual_operator(
            family="heat_1d",
            declared_form="nonconservative",
            field_provenance=_provenance("conservative_divergence"),
            coefficient_is_constant=False,
        )


def test_no_resolved_object_can_carry_a_disagreement() -> None:
    """``agreement_status`` has no ``disagreed`` value, by construction.

    A status that could report a conflict would imply a caller might proceed
    past one.
    """
    statuses = set()
    for declared, provenance in (
        ("conservative", "conservative_divergence"),
        ("conservative", None),
        (None, "conservative_divergence"),
    ):
        resolved = resolve_residual_operator(
            family="heat_1d",
            declared_form=declared,
            field_provenance=_provenance(provenance),
        )
        statuses.add(resolved.agreement_status)
    assert statuses == {"agreed", "declaration_only", "provenance_only"}
    assert "disagreed" not in statuses


# --------------------------------------------------------------------------
# Every resolution source is reachable and recorded
# --------------------------------------------------------------------------


def test_agreement_records_both_sources() -> None:
    resolved = resolve_residual_operator(
        family="heat_1d",
        declared_form="conservative",
        field_provenance=_provenance("conservative_divergence"),
    )
    assert resolved.resolution_source == "declaration_and_provenance_agree"
    assert resolved.equation_form is EquationForm.CONSERVATIVE
    assert resolved.declared_form is EquationForm.CONSERVATIVE
    assert resolved.provenance_form is EquationForm.CONSERVATIVE


def test_provenance_only_is_reachable() -> None:
    resolved = resolve_residual_operator(
        family="heat_1d", field_provenance=_provenance("nonconservative_nu_uxx")
    )
    assert resolved.resolution_source == "provenance_only"
    assert resolved.equation_form is EquationForm.NONCONSERVATIVE
    assert resolved.declared_form is None


def test_declaration_only_is_reachable() -> None:
    resolved = resolve_residual_operator(
        family="heat_1d", declared_form="conservative", field_provenance=_provenance(None)
    )
    assert resolved.resolution_source == "declaration_only"
    assert resolved.provenance_form is None


def test_every_declared_resolution_source_is_reachable() -> None:
    reached = set()
    for declared, provenance in (
        ("conservative", "conservative_divergence"),
        (None, "conservative_divergence"),
        ("conservative", None),
    ):
        reached.add(
            resolve_residual_operator(
                family="heat_1d",
                declared_form=declared,
                field_provenance=_provenance(provenance),
            ).resolution_source
        )
    assert reached == set(RESOLUTION_SOURCES)


# --------------------------------------------------------------------------
# Absence is an absence, not a default
# --------------------------------------------------------------------------


def test_an_untagged_field_yields_none_rather_than_a_default() -> None:
    """Manufacturing a second opinion and then reconciling against it is worse
    than having one source."""
    assert provenance_equation_form(_provenance(None)) is None


def test_no_source_at_all_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="unsourced claim"):
        resolve_residual_operator(family="heat_1d", field_provenance=_provenance(None))


def test_an_unmapped_provenance_tag_is_refused_not_guessed() -> None:
    with pytest.raises(ScopeValidationError, match="maps to no equation form"):
        resolve_residual_operator(
            family="heat_1d", field_provenance=_provenance("some_new_form")
        )


# --------------------------------------------------------------------------
# The five report fields
# --------------------------------------------------------------------------


def test_the_resolved_object_exposes_the_five_fields() -> None:
    resolved = resolve_residual_operator(
        family="heat_1d",
        declared_form="conservative",
        field_provenance=_provenance("conservative_divergence"),
    )
    payload = resolved.as_dict()
    assert set(payload) == {
        "family",
        "declared_form",
        "provenance_form",
        "resolved_form",
        "resolution_source",
        "agreement_status",
    }
    json.dumps(payload, allow_nan=False)


def test_a_resolved_object_cannot_be_built_from_a_bare_string() -> None:
    with pytest.raises(ScopeValidationError, match="must be an EquationForm"):
        ResolvedResidualOperator(
            family="heat_1d",
            equation_form="conservative",  # type: ignore[arg-type]
            resolution_source="declaration_only",
            declared_form=EquationForm.CONSERVATIVE,
            provenance_form=None,
        )


# --------------------------------------------------------------------------
# The benchmark consumes one object for both the spec and the report
# --------------------------------------------------------------------------


def test_the_benchmark_reports_the_resolution_source() -> None:
    from pdelie.benchmarks import run_admissibility_benchmark

    run = run_admissibility_benchmark(phase="pilot", seeds=[13])
    measured = [r for r in run["measurements"] if r["outcome"] == "measured"]
    assert measured
    for row in measured:
        assert row["operator_resolution_source"] in RESOLUTION_SOURCES
        assert row["operator_agreement_status"] in {
            "agreed",
            "declaration_only",
            "provenance_only",
        }
        assert row["equation_form"] in {"conservative", "nonconservative"}


def test_the_spec_and_the_report_describe_the_same_operator() -> None:
    """The structural claim: one object, two consumers, no second derivation."""
    from pdelie.benchmarks.parameter_equivariant import (
        BENCHMARK_CASES,
        _build_field,
        _resolve_operator,
        build_coefficient_field,
    )

    case = BENCHMARK_CASES["C-3"]
    field = _build_field(case.equation_family, 13, 16, 16)
    x = np.asarray(field.coords["x"], dtype=float)
    coefficient = build_coefficient_field(case.profile_id, 0.4, x)

    resolved = _resolve_operator(case, field, coefficient)
    assert isinstance(resolved, ResolvedResidualOperator)
    # The value the ProblemInstanceSpec is built from and the value the report
    # publishes are the same attribute of the same object.
    assert resolved.equation_form.value == resolved.as_dict()["resolved_form"]


def test_a_blocked_row_carries_no_operator_claim() -> None:
    """C-8 never executes, so it must not describe an operator it did not use."""
    from pdelie.benchmarks import run_admissibility_benchmark

    run = run_admissibility_benchmark(phase="pilot", seeds=[13])
    for row in run["measurements"]:
        if row["outcome"] != "measured":
            assert row["equation_form"] is None
            assert row["operator_resolution_source"] is None
            assert row["operator_agreement_status"] is None
