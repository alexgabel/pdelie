"""v0.37a: the bundle rule table.

Twelve rules. They are numbered R-A1 through R-A13 with **R-A9 deliberately
absent**, and the gap is the point.

R-A9 existed to couple ``boundary_action`` back to a collapsed ``relation_type``
enum: if the boundary was acted on, the collapsed value had to be one of two
specific members. With five independent axes there is nothing to couple --
``boundary_relation`` says what happened to the boundary directly, and
``equation_relation`` says what happened to the equation, and neither constrains
the other. The rule was a patch for a coupling that only existed because the
axes had been merged.

The number is not reused. A rule table where numbers get recycled cannot be
cited in a review comment six months later.

Rules are pure predicates over a constructed bundle. Anything expressible as a
per-field shape check lives on the dataclass instead, because a malformed field
should be impossible to construct rather than merely detectable afterwards.
"""

from __future__ import annotations

from collections.abc import Callable

from pdelie.actions.action_bundle import ProblemActionBundle
from pdelie.errors import ScopeValidationError

__all__ = [
    "BUNDLE_RULES",
    "BUNDLE_RULE_COUNT",
    "BUNDLE_RULE_IDS",
    "BundleRule",
    "InconsistentBundleError",
    "validate_action_bundle",
]


class InconsistentBundleError(ScopeValidationError):
    """A bundle whose declared claims contradict each other or its actions."""


#: ``(rule_id, predicate, message)``. The predicate returns True when the rule
#: is *violated*.
BundleRule = tuple[str, Callable[[ProblemActionBundle], bool], str]


def _coefficient_actions_all_identity(bundle: ProblemActionBundle) -> bool:
    return all(action.is_identity for action in bundle.coefficient_field_actions.values())


def _any_coefficient_action_acts(bundle: ProblemActionBundle) -> bool:
    return any(not action.is_identity for action in bundle.coefficient_field_actions.values())


def _treatment_action_mismatch(bundle: ProblemActionBundle, treatment: str, *, identity: bool) -> bool:
    """True when a field declaring ``treatment`` carries the wrong kind of action."""
    for name, ref in bundle.problem_instance.coefficient_fields.items():
        if ref.treatment != treatment:
            continue
        action = bundle.coefficient_field_actions[name]
        if action.is_identity is identity:
            return True
    return False


def _spatial_translation_over_spatial_coefficient(bundle: ProblemActionBundle) -> bool:
    """R-A7's precondition: a spatial state translation over an x-dependent field."""
    if bundle.state_action.action_family != "spatial_translation":
        return False
    axis = bundle.problem_instance.spatial_axis_name
    relation = bundle.expected_residual_relation
    if relation.parameter_relation != "transformed":
        return False
    for ref in bundle.problem_instance.coefficient_fields.values():
        if axis in ref.coordinate_dependency and ref.treatment == "fixed_background":
            return True
    return False


def _analytical_field_without_values_or_closed_form(bundle: ProblemActionBundle) -> bool:
    """R-A11: a co-transformable field needs either stored values or a closed form."""
    for name, ref in bundle.problem_instance.coefficient_fields.items():
        if ref.treatment != "co_transformable_background":
            continue
        if ref.values_artifact is not None:
            continue
        action = bundle.coefficient_field_actions[name]
        if "closed_form" in action.parameters:
            continue
        if ref.analytical_spec:
            continue
        return True
    return False


BUNDLE_RULES: tuple[BundleRule, ...] = (
    (
        "R-A1",
        lambda b: (
            b.expected_residual_relation.equation_relation == "same_equation"
            and b.expected_residual_relation.coefficient_relation == "fixed"
            and _any_coefficient_action_acts(b)
        ),
        (
            "same_equation with a fixed coefficient relation cannot carry a "
            "non-identity coefficient action"
        ),
    ),
    (
        "R-A2",
        lambda b: (
            b.expected_residual_relation.parameter_relation == "transformed"
            and b.parameter_action is None
        ),
        "a transformed parameter relation requires a parameter_action",
    ),
    (
        "R-A3",
        lambda b: (
            b.expected_residual_relation.coefficient_relation == "co_transformed"
            and _coefficient_actions_all_identity(b)
        ),
        (
            "a co_transformed coefficient relation requires at least one "
            "non-identity coefficient action"
        ),
    ),
    (
        "R-A4",
        lambda b: _treatment_action_mismatch(b, "co_transformable_background", identity=True),
        (
            "a field declared co_transformable_background that is claimed to "
            "co-transform needs a non-identity action; declare it fixed_background "
            "instead if it does not move"
        ),
    ),
    (
        "R-A5",
        lambda b: _treatment_action_mismatch(b, "fixed_background", identity=False),
        (
            "a field declared fixed_background cannot carry a non-identity action; "
            "the declaration says it does not move"
        ),
    ),
    (
        "R-A6",
        lambda b: (
            any(
                ref.treatment == "unknown"
                for ref in b.problem_instance.coefficient_fields.values()
            )
            and b.expected_residual_relation.permits_confirmation
        ),
        (
            "a field with unknown treatment cannot support a declared operator "
            "relation; use expected_operator family 'diagnostic_fitted'"
        ),
    ),
    (
        "R-A7",
        _spatial_translation_over_spatial_coefficient,
        (
            "a spatial translation claiming transformed parameters over an "
            "x-dependent field cannot declare that field fixed_background -- this is "
            "the v0.34b non-equivalence case, measured at 77x to 15437x separation"
        ),
    ),
    (
        "R-A8",
        lambda b: (
            b.problem_instance.equation_form == "conservative"
            and b.expected_residual_relation.expected_operator.family == "affine"
        ),
        (
            "conservative form does not admit an affine residual relation: a "
            "constant offset is not expressible as a divergence"
        ),
    ),
    # R-A9 is deliberately absent. See the module docstring.
    (
        "R-A10",
        lambda b: b.expected_residual_relation.domain_relation == "overlap_crop"
        and b.expected_residual_relation.boundary_relation
        not in ("interior_only", "unknown"),
        (
            "an overlap_crop domain supports only interior_only or unknown boundary "
            "claims; the crop is what removes the boundary from scope"
        ),
    ),
    (
        "R-A11",
        _analytical_field_without_values_or_closed_form,
        (
            "a co_transformable_background field needs either a values_artifact, an "
            "analytical_spec, or a closed_form parameter on its action -- otherwise "
            "there is nothing to transform"
        ),
    ),
    (
        "R-A12",
        lambda b: (
            b.expected_residual_relation.equation_relation == "equation_invalid"
            and b.expected_residual_relation.permits_confirmation
        ),
        (
            "an equation_invalid claim cannot also declare a confirmable operator "
            "relation; there is no equation left for the operator to relate"
        ),
    ),
    (
        "R-A13",
        lambda b: (
            not b.expected_residual_relation.permits_confirmation
            and b.expected_residual_relation.tolerance_declaration is not None
        ),
        (
            "diagnostic_fitted declares no relation, so a tolerance has nothing to "
            "bound; what the fit produces belongs in the report's optional_evidence"
        ),
    ),
)

BUNDLE_RULE_IDS: tuple[str, ...] = tuple(rule_id for rule_id, _, _ in BUNDLE_RULES)

#: Frozen by test. Growth is deliberate: a new rule needs a PR raising this
#: number together with an example that trips it.
BUNDLE_RULE_COUNT = len(BUNDLE_RULES)


def validate_action_bundle(bundle: ProblemActionBundle) -> None:
    """Refuse a bundle whose claims contradict each other or its actions.

    Raises :class:`InconsistentBundleError` on the first rule that fires, naming
    the rule so a failure can be looked up rather than guessed at.
    """
    if not isinstance(bundle, ProblemActionBundle):
        raise ScopeValidationError("validate_action_bundle requires a ProblemActionBundle.")
    for rule_id, predicate, message in BUNDLE_RULES:
        if predicate(bundle):
            raise InconsistentBundleError(f"{rule_id}: {message}")
