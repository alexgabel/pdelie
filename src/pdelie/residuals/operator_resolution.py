"""v0.38: one authoritative answer to "which operator is being evaluated?"

The defect this replaces
========================

Two sources described the equation form and nothing reconciled them:

* ``ProblemInstanceSpec.equation_form`` -- what the problem *declared*;
* ``parameter_tags["nu_form"]`` -- what the data was *generated* with, and what
  the residual evaluators actually dispatch on.

The v0.38e benchmark declared ``"nonconservative"`` as a literal on every case
while the evaluators took the conservative branch on every variable-coefficient
case. The numbers were valid -- for the conservative operator. The declaration,
and the semantic hash computed from it, described a different one.

v0.38e fixed the symptom by deriving the declaration from provenance inside the
benchmark. That is better than a literal and still not right: it leaves two
fields, one computed from the other, in one consumer. A second consumer deriving
it slightly differently reintroduces the same class of defect.

The end state, and what this module is
======================================

One enum, one resolver, one resolved object consumed by everything:

* :class:`EquationForm` -- the vocabulary, closed;
* :class:`ResolvedResidualOperator` -- the answer, carrying how it was reached;
* :func:`resolve_residual_operator` -- the only place the answer is decided.

**Disagreement blocks.** If a declaration and the data's provenance name
different operators, no choice is made. Silently preferring either is how a
report comes to describe an operator that produced none of its numbers, and
preferring the declaration would have kept the v0.38e defect invisible.

A note on when the disagreement is observable
=============================================

The two forms differ by exactly ``nu' * u_x``. For a constant coefficient that
term is identically zero, so the operators coincide and a wrong label changes no
number. That is *why* the mislabel survived a release -- three of the five
v0.37c cases could not have detected it.

It still blocks. A declaration that is wrong-but-currently-harmless is wrong,
and the harm arrives with the first variable coefficient. The refusal message
says whether the coefficient is constant, so a reader can tell whether numbers
are affected, without that fact licensing the mismatch.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pdelie.errors import ScopeValidationError

__all__ = [
    "COEFFICIENT_FORM_TO_EQUATION_FORM",
    "RESOLUTION_SOURCES",
    "EquationForm",
    "ResolvedResidualOperator",
    "resolve_residual_operator",
]


class EquationForm(StrEnum):
    """Which spatial operator a residual is evaluated under.

    ``StrEnum`` (the package requires 3.12) so it serialises to its value with
    no custom encoder, and so an existing consumer comparing against the plain
    string keeps working.
    """

    CONSERVATIVE = "conservative"
    NONCONSERVATIVE = "nonconservative"


#: The single mapping from a generator's coefficient-form tag onto the equation
#: form. It lived in two places at v0.38e -- the benchmark and the evaluator
#: dispatch -- which is the duplication this module exists to remove.
COEFFICIENT_FORM_TO_EQUATION_FORM: dict[str, EquationForm] = {
    "conservative_divergence": EquationForm.CONSERVATIVE,
    "nonconservative_nu_uxx": EquationForm.NONCONSERVATIVE,
}

#: How the resolved answer was reached. Recorded, because "both agreed" and
#: "only one source existed" are different evidentiary situations and a reader
#: of a report should not have to guess which one produced the label.
RESOLUTION_SOURCES: tuple[str, ...] = (
    "declaration_and_provenance_agree",
    "provenance_only",
    "declaration_only",
)


@dataclass(frozen=True)
class ResolvedResidualOperator:
    """The operator actually being evaluated, and how that was decided."""

    family: str
    equation_form: EquationForm
    resolution_source: str
    declared_form: EquationForm | None
    provenance_form: EquationForm | None

    def __post_init__(self) -> None:
        if not isinstance(self.family, str) or not self.family.strip():
            raise ScopeValidationError("family must be a non-empty string.")
        if not isinstance(self.equation_form, EquationForm):
            raise ScopeValidationError(
                f"equation_form must be an EquationForm, not "
                f"{type(self.equation_form).__name__}. A bare string here would "
                f"let an unvalidated label through."
            )
        if self.resolution_source not in RESOLUTION_SOURCES:
            raise ScopeValidationError(
                f"resolution_source {self.resolution_source!r} is not one of "
                f"{list(RESOLUTION_SOURCES)}."
            )

    @property
    def agreement_status(self) -> str:
        """``agreed`` / ``declaration_only`` / ``provenance_only``.

        There is deliberately no ``disagreed`` value: a disagreement raises, so
        no resolved object can carry one. A status that could report a conflict
        would imply a caller might proceed past it.
        """
        if self.declared_form is not None and self.provenance_form is not None:
            return "agreed"
        return "declaration_only" if self.declared_form is not None else "provenance_only"

    def as_dict(self) -> dict[str, Any]:
        """The five fields a report exposes."""
        return {
            "family": self.family,
            "declared_form": None if self.declared_form is None else self.declared_form.value,
            "provenance_form": (
                None if self.provenance_form is None else self.provenance_form.value
            ),
            "resolved_form": self.equation_form.value,
            "resolution_source": self.resolution_source,
            "agreement_status": self.agreement_status,
        }


def _coerce(value: object, *, where: str) -> EquationForm | None:
    if value is None:
        return None
    if isinstance(value, EquationForm):
        return value
    if isinstance(value, str):
        try:
            return EquationForm(value)
        except ValueError:
            raise ScopeValidationError(
                f"{where} is {value!r}, which is not an equation form. Known "
                f"forms: {[form.value for form in EquationForm]}."
            ) from None
    raise ScopeValidationError(f"{where} is {type(value).__name__}, not an equation form.")


def provenance_equation_form(
    field_provenance: Mapping[str, Any], *, form_tag: str = "nu_form"
) -> EquationForm | None:
    """Read the form the data was generated with, or ``None`` if untagged.

    Fields predating v0.33d carry no form tag. That is an absence, not a
    default -- returning one here would manufacture a second opinion out of
    nothing and then reconcile against it.
    """
    if not isinstance(field_provenance, Mapping):
        raise ScopeValidationError("field_provenance must be a mapping.")
    tags = field_provenance.get("parameter_tags") or {}
    if not isinstance(tags, Mapping):
        raise ScopeValidationError("parameter_tags must be a mapping.")
    raw = tags.get(form_tag)
    if raw is None:
        return None
    if raw not in COEFFICIENT_FORM_TO_EQUATION_FORM:
        raise ScopeValidationError(
            f"parameter_tags[{form_tag!r}] is {raw!r}, which maps to no equation "
            f"form. Guessing one would put a label on the report that no "
            f"operator produced. Known: {sorted(COEFFICIENT_FORM_TO_EQUATION_FORM)}."
        )
    return COEFFICIENT_FORM_TO_EQUATION_FORM[raw]


def resolve_residual_operator(
    *,
    family: str,
    declared_form: object = None,
    field_provenance: Mapping[str, Any] | None = None,
    form_tag: str = "nu_form",
    coefficient_is_constant: bool | None = None,
) -> ResolvedResidualOperator:
    """Decide, once, which operator is being evaluated.

    ``declared_form`` is what a :class:`ProblemInstanceSpec` says;
    ``field_provenance`` is the field's ``metadata``. Either may be absent. If
    both are present they must agree.

    ``coefficient_is_constant`` only enriches the refusal message -- it never
    permits a mismatch. The two forms coincide for a constant coefficient, so a
    reader needs to know whether numbers are affected; that they are not does
    not make the declaration right.
    """
    declared = _coerce(declared_form, where="declared_form")
    provenance = (
        None
        if field_provenance is None
        else provenance_equation_form(field_provenance, form_tag=form_tag)
    )

    if declared is not None and provenance is not None:
        if declared is not provenance:
            observability = (
                ""
                if coefficient_is_constant is None
                else (
                    " The coefficient is constant here, so the two operators "
                    "coincide numerically and no measured value is affected -- "
                    "the declaration is still wrong, and stops being harmless at "
                    "the first variable coefficient."
                    if coefficient_is_constant
                    else " The coefficient is not constant, so the two operators "
                    "differ by nu' * u_x and the measured values ARE affected."
                )
            )
            raise ScopeValidationError(
                f"equation form disagreement for {family!r}: the problem declares "
                f"{declared.value!r} and the data's provenance says "
                f"{provenance.value!r}. Neither is chosen. Silently preferring "
                f"one is how a report comes to describe an operator that produced "
                f"none of its numbers.{observability}"
            )
        return ResolvedResidualOperator(
            family=family,
            equation_form=declared,
            resolution_source="declaration_and_provenance_agree",
            declared_form=declared,
            provenance_form=provenance,
        )

    if provenance is not None:
        return ResolvedResidualOperator(
            family=family,
            equation_form=provenance,
            resolution_source="provenance_only",
            declared_form=None,
            provenance_form=provenance,
        )
    if declared is not None:
        return ResolvedResidualOperator(
            family=family,
            equation_form=declared,
            resolution_source="declaration_only",
            declared_form=declared,
            provenance_form=None,
        )
    raise ScopeValidationError(
        f"no equation form is available for {family!r}: the problem declares none "
        f"and the field carries no {form_tag!r} tag. A default here would be an "
        f"unsourced claim about which operator was evaluated."
    )
