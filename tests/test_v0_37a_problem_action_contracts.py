"""v0.37a contract tests: problem specs, action bundles, and the rule table.

Contracts only -- nothing here executes an action, because nothing at v0.37a
can. What is asserted is that a malformed declaration is impossible to
construct, and that a self-contradictory one is impossible to validate.

Two properties are worth stating up front because they are easy to lose.

**Every rule has a violating example.** A rule nobody can trip is a rule nobody
has tested, and the rule count is frozen so that adding one requires adding its
example in the same change.

**R-A9 is absent, deliberately.** It existed to couple ``boundary_action`` back
to a collapsed ``relation_type``. With five independent axes there is nothing to
couple, and the number is not reused -- a table that recycles numbers cannot be
cited in a review six months later.
"""

from __future__ import annotations

import json

import pytest

from pdelie.actions import (
    BUNDLE_RULE_COUNT,
    BUNDLE_RULE_IDS,
    BUNDLE_RULES,
    COEFFICIENT_TREATMENTS,
    COORDINATE_FIELD_ACTION_FAMILIES,
    DERIVATIVE_NAMES,
    EXPECTED_OPERATOR_FAMILIES,
    OBSERVED_RELATION_STATUSES,
    ActionExecutionConfig,
    ActionRef,
    CoefficientFieldRef,
    CoordinateFieldAction,
    ExpectedResidualOperator,
    ExpectedResidualRelation,
    InconsistentBundleError,
    ProblemActionBundle,
    ProblemInstanceSpec,
    validate_action_bundle,
)
from pdelie.errors import ScopeValidationError

IDENTITY = CoordinateFieldAction(family="identity")
SHIFT = CoordinateFieldAction(family="shift", parameters={"offset": 0.25})


def _ref(name: str = "nu", *, treatment: str = "fixed_background", **kwargs) -> CoefficientFieldRef:
    kwargs.setdefault("coordinate_dependency", ("x",))
    if treatment == "co_transformable_background":
        kwargs.setdefault("analytical_spec", {"profile": "sinusoidal"})
    return CoefficientFieldRef(field_name=name, treatment=treatment, **kwargs)


def _problem(**kwargs) -> ProblemInstanceSpec:
    kwargs.setdefault("equation_family", "heat_1d")
    kwargs.setdefault("equation_form", "nonconservative")
    kwargs.setdefault("parameters", {"nu_baseline": 0.1})
    kwargs.setdefault("coefficient_fields", {"nu": _ref()})
    kwargs.setdefault("spatial_axis_name", "x")
    kwargs.setdefault("time_axis_name", "t")
    kwargs.setdefault("domain_type", "periodic_uniform")
    return ProblemInstanceSpec(**kwargs)


def _action(target: str, family: str = "identity") -> ActionRef:
    return ActionRef(
        action_target=target, action_family=family, action_parameter_id=f"{family}_{target}"
    )


def _relation(**kwargs) -> ExpectedResidualRelation:
    kwargs.setdefault("equation_relation", "same_equation")
    kwargs.setdefault("parameter_relation", "preserved")
    kwargs.setdefault("coefficient_relation", "fixed")
    kwargs.setdefault("domain_relation", "preserved")
    kwargs.setdefault("boundary_relation", "preserved")
    kwargs.setdefault("expected_operator", ExpectedResidualOperator(family="identity"))
    return ExpectedResidualRelation(**kwargs)


def _bundle(**kwargs) -> ProblemActionBundle:
    problem = kwargs.pop("problem_instance", None) or _problem()
    kwargs.setdefault("problem_instance", problem)
    kwargs.setdefault("state_action", _action("state"))
    kwargs.setdefault("domain_action", _action("domain"))
    kwargs.setdefault("boundary_action", _action("domain"))
    kwargs.setdefault(
        "coefficient_field_actions", {name: IDENTITY for name in problem.coefficient_fields}
    )
    kwargs.setdefault("expected_residual_relation", _relation())
    return ProblemActionBundle(**kwargs)


# --- the seed hard cut ------------------------------------------------------


def test_the_bundle_carries_no_seed() -> None:
    """C-1. A mathematical action has no seed; the execution config does.

    Every v0.37 action family is deterministic, so a seed on the bundle would
    make deterministic actions read as stochastic and would give two
    mathematically identical bundles different semantic hashes.
    """
    import dataclasses

    assert "seed" not in {f.name for f in dataclasses.fields(ProblemActionBundle)}


def test_missing_seed_on_the_execution_config_is_a_type_error() -> None:
    """The hard cut moved layer; it was not weakened."""
    with pytest.raises(TypeError):
        ActionExecutionConfig(  # type: ignore[call-arg]
            interpolation_backend="exact_grid_shift",
            numerical_tolerances={"rtol": 1e-6},
            deterministic_expected=True,
        )


@pytest.mark.parametrize("bad", ["20370", 1.5, True])
def test_non_integer_seed_is_refused(bad: object) -> None:
    with pytest.raises(ScopeValidationError, match="seed"):
        ActionExecutionConfig(
            interpolation_backend="exact_grid_shift",
            numerical_tolerances={"rtol": 1e-6},
            seed=bad,  # type: ignore[arg-type]
            deterministic_expected=False,
        )


def test_seed_none_is_a_declaration_not_an_omission() -> None:
    config = ActionExecutionConfig(
        interpolation_backend="exact_grid_shift",
        numerical_tolerances={"rtol": 1e-6},
        seed=None,
        deterministic_expected=True,
    )
    assert config.seed is None
    assert config.as_dict()["seed"] is None


def test_deterministic_with_a_seed_is_contradictory() -> None:
    with pytest.raises(ScopeValidationError, match="contradictory"):
        ActionExecutionConfig(
            interpolation_backend="exact_grid_shift",
            numerical_tolerances={"rtol": 1e-6},
            seed=1,
            deterministic_expected=True,
        )


def test_nondeterministic_without_a_seed_is_irreproducible() -> None:
    with pytest.raises(ScopeValidationError, match="cannot be reproduced"):
        ActionExecutionConfig(
            interpolation_backend="exact_grid_shift",
            numerical_tolerances={"rtol": 1e-6},
            seed=None,
            deterministic_expected=False,
        )


# --- strict JSON and identity ----------------------------------------------


@pytest.mark.parametrize(
    "obj",
    [
        _ref(),
        CoordinateFieldAction(family="shift", parameters={"offset": 1.0}),
        ExpectedResidualOperator(family="scalar_multiplier", parameters={"multiplier": 2.0}),
    ],
)
def test_every_contract_round_trips_through_strict_json(obj: object) -> None:
    payload = obj.as_dict()  # type: ignore[attr-defined]
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload


def test_bundle_round_trips_and_hashes() -> None:
    bundle = _bundle()
    payload = bundle.as_dict()
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload
    assert bundle.identity() == _bundle().identity()


def test_identity_is_insensitive_to_key_order() -> None:
    a = _problem(parameters={"nu_baseline": 0.1, "alpha": 0.2})
    b = _problem(parameters={"alpha": 0.2, "nu_baseline": 0.1})
    assert a.identity() == b.identity()


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_parameters_are_refused(bad: float) -> None:
    with pytest.raises(ScopeValidationError):
        _problem(parameters={"nu_baseline": bad})


# --- R-A12a..e: per-family operator parameter shapes ------------------------


def test_identity_declares_no_parameters() -> None:
    assert ExpectedResidualOperator(family="identity").parameters == {}
    with pytest.raises(ScopeValidationError, match="identity declares no parameters"):
        ExpectedResidualOperator(family="identity", parameters={"multiplier": 1.0})


@pytest.mark.parametrize("bad", [{}, {"multiplier": 1.0, "offset": 0.0}, {"factor": 1.0}])
def test_scalar_multiplier_declares_exactly_multiplier(bad: dict) -> None:
    with pytest.raises(ScopeValidationError, match="scalar_multiplier"):
        ExpectedResidualOperator(family="scalar_multiplier", parameters=bad)


def test_affine_declares_multiplier_and_offset() -> None:
    op = ExpectedResidualOperator(
        family="affine", parameters={"multiplier": 2.0, "offset": 0.5}
    )
    assert op.parameters == {"multiplier": 2.0, "offset": 0.5}
    with pytest.raises(ScopeValidationError, match="affine"):
        ExpectedResidualOperator(family="affine", parameters={"multiplier": 2.0})


def test_affine_with_zero_offset_is_allowed_and_does_not_canonicalise() -> None:
    """A degenerate-but-valid value must not break a sweep through zero.

    ``affine`` with ``offset == 0.0`` expresses what ``scalar_multiplier``
    expresses, so the two spell one relation two ways and hash differently. That
    is a stated non-canonicalisation, not an oversight: rejecting it would break
    any dose-response sweep passing through zero, and silently rewriting the
    family would make the spec record something other than what was declared.
    """
    affine = ExpectedResidualOperator(
        family="affine", parameters={"multiplier": 2.0, "offset": 0.0}
    )
    scalar = ExpectedResidualOperator(
        family="scalar_multiplier", parameters={"multiplier": 2.0}
    )
    assert affine.family != scalar.family
    assert affine.as_dict() != scalar.as_dict()


def test_linear_combination_keys_come_from_the_frozen_derivative_vocabulary() -> None:
    op = ExpectedResidualOperator(
        family="linear_combination_of_derivatives",
        parameters={"coefficients": {"u_xx": 0.1, "u_x": -0.2}},
    )
    assert op.parameters["coefficients"] == {"u_xx": 0.1, "u_x": -0.2}
    with pytest.raises(ScopeValidationError, match="derivative vocabulary"):
        ExpectedResidualOperator(
            family="linear_combination_of_derivatives",
            parameters={"coefficients": {"uxx": 0.1}},
        )


def test_linear_combination_rejects_an_empty_coefficient_mapping() -> None:
    with pytest.raises(ScopeValidationError, match="non-empty"):
        ExpectedResidualOperator(
            family="linear_combination_of_derivatives", parameters={"coefficients": {}}
        )


def test_diagnostic_fitted_declares_nothing() -> None:
    """Parameters are what you declare, not what you fit."""
    assert ExpectedResidualOperator(family="diagnostic_fitted").parameters == {}
    with pytest.raises(ScopeValidationError, match="diagnostic_fitted declares no parameters"):
        ExpectedResidualOperator(
            family="diagnostic_fitted", parameters={"coefficients": {"u_x": 1.0}}
        )


def test_the_derivative_vocabulary_matches_the_residual_evaluator_union() -> None:
    """Growth-only, like the forbidden-language table.

    The vocabulary is the measured union of ``_REQUIRED_DERIVATIVES`` across the
    residual modules. If a new PDE introduces ``u_xxxx``, this fails until the
    v0.37a vocabulary is extended deliberately rather than by accident.
    """
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "src/pdelie/residuals"
    union: set[str] = set()
    modules = 0
    for path in sorted(root.glob("*.py")):
        match = re.search(r"_REQUIRED_DERIVATIVES[^=]*=\s*\(([^)]*)\)", path.read_text())
        if match:
            modules += 1
            union.update(re.findall(r'"([^"]+)"', match.group(1)))
    assert modules >= 5, f"expected the hoisted constant on every evaluator; found {modules}"
    assert union == set(DERIVATIVE_NAMES), (
        f"residual evaluators use {sorted(union)}; the frozen vocabulary is "
        f"{sorted(DERIVATIVE_NAMES)}. Extend DERIVATIVE_NAMES deliberately."
    )


# --- R-A13 and the observed-status vocabulary -------------------------------


def test_diagnostic_fitted_can_only_report_no_relation_declared() -> None:
    """R-A13. Nothing was declared, so nothing can be confirmed or violated."""
    relation = _relation(
        coefficient_relation="unknown",
        expected_operator=ExpectedResidualOperator(family="diagnostic_fitted"),
    )
    assert relation.permits_confirmation is False
    assert relation.allowed_observed_statuses() == ("no_relation_declared", "blocked")
    assert "confirmed" not in relation.allowed_observed_statuses()


@pytest.mark.parametrize(
    "family", ["identity", "scalar_multiplier", "affine", "linear_combination_of_derivatives"]
)
def test_declared_families_can_be_confirmed_or_violated(family: str) -> None:
    parameters: dict = {
        "identity": {},
        "scalar_multiplier": {"multiplier": 1.0},
        "affine": {"multiplier": 1.0, "offset": 0.0},
        "linear_combination_of_derivatives": {"coefficients": {"u_xx": 1.0}},
    }[family]
    relation = _relation(
        expected_operator=ExpectedResidualOperator(family=family, parameters=parameters)
    )
    assert relation.permits_confirmation is True
    assert set(relation.allowed_observed_statuses()) == {
        "confirmed",
        "violated",
        "inconclusive",
        "blocked",
    }


def test_no_relation_declared_is_not_spelled_diagnostic_only() -> None:
    """``diagnostic_only`` is a boolean payload flag in 24 emissions already."""
    assert "no_relation_declared" in OBSERVED_RELATION_STATUSES
    assert "diagnostic_only" not in OBSERVED_RELATION_STATUSES


def test_observed_statuses_extend_the_c4_set_by_exactly_one() -> None:
    assert set(OBSERVED_RELATION_STATUSES) - {"confirmed", "violated", "inconclusive", "blocked"} == {
        "no_relation_declared"
    }


# --- vocabularies -----------------------------------------------------------


def test_co_transforming_is_not_a_declarative_treatment() -> None:
    """The -ing form is the v0.34b measured-outcome label; different layer."""
    assert "co_transformable_background" in COEFFICIENT_TREATMENTS
    assert "co_transforming_background" not in COEFFICIENT_TREATMENTS
    with pytest.raises(ScopeValidationError, match="measured outcome"):
        _ref(treatment="co_transforming_background")


def test_fixed_background_is_carried_over_from_the_v0_33d_tag() -> None:
    """C-2 resolves to generalise the shipped tag, not fork a new vocabulary."""
    from pathlib import Path

    assert "fixed_background" in COEFFICIENT_TREATMENTS
    generators = Path(__file__).resolve().parents[1] / "src/pdelie/data"
    emitting = [p.name for p in generators.glob("*.py") if "nu_treatment_policy" in p.read_text()]
    assert len(emitting) >= 3, emitting


@pytest.mark.parametrize("family", COORDINATE_FIELD_ACTION_FAMILIES)
def test_every_action_family_has_a_declared_parameter_shape(family: str) -> None:
    parameters = {"identity": {}, "shift": {"offset": 1.0}, "scalar_rescale": {"factor": 2.0}}[
        family
    ]
    action = CoordinateFieldAction(family=family, parameters=parameters)
    assert action.family == family
    with pytest.raises(ScopeValidationError, match="parameter set is closed"):
        CoordinateFieldAction(family=family, parameters={**parameters, "extra": 1.0})


@pytest.mark.parametrize("family", EXPECTED_OPERATOR_FAMILIES)
def test_every_operator_family_is_constructible(family: str) -> None:
    parameters: dict = {
        "identity": {},
        "scalar_multiplier": {"multiplier": 1.0},
        "affine": {"multiplier": 1.0, "offset": 0.0},
        "linear_combination_of_derivatives": {"coefficients": {"u_t": 1.0}},
        "diagnostic_fitted": {},
    }[family]
    assert ExpectedResidualOperator(family=family, parameters=parameters).family == family


# --- problem instance -------------------------------------------------------


def test_coefficient_field_key_must_match_its_name() -> None:
    with pytest.raises(ScopeValidationError, match="two answers for one field"):
        _problem(coefficient_fields={"kappa": _ref("nu")})


def test_coefficient_field_cannot_depend_on_an_unknown_axis() -> None:
    with pytest.raises(ScopeValidationError, match="not this problem's axes"):
        _problem(coefficient_fields={"nu": _ref(coordinate_dependency=("y",))})


def test_spatial_and_time_axis_must_differ() -> None:
    with pytest.raises(ScopeValidationError, match="cannot be both"):
        _problem(spatial_axis_name="x", time_axis_name="x")


def test_coefficient_dependency_rejects_a_bare_string() -> None:
    with pytest.raises(ScopeValidationError, match="not a bare string"):
        _ref(coordinate_dependency="x")


# --- bundle wiring ----------------------------------------------------------


def test_every_declared_field_needs_an_action() -> None:
    """Silence and 'left alone' are different claims."""
    problem = _problem(coefficient_fields={"nu": _ref(), "kappa": _ref("kappa")})
    with pytest.raises(ScopeValidationError, match="omits"):
        _bundle(problem_instance=problem, coefficient_field_actions={"nu": IDENTITY})


def test_an_action_for_an_undeclared_field_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="does not declare"):
        _bundle(coefficient_field_actions={"nu": IDENTITY, "ghost": IDENTITY})


def test_operator_family_and_parameters_cannot_be_supplied_apart() -> None:
    with pytest.raises(ScopeValidationError, match="validated as a pair"):
        _relation(expected_operator="scalar_multiplier")  # type: ignore[arg-type]


# --- the rule table ---------------------------------------------------------


def test_rule_count_is_frozen_and_r_a9_is_absent() -> None:
    assert BUNDLE_RULE_COUNT == 12
    assert len(BUNDLE_RULES) == BUNDLE_RULE_COUNT
    assert "R-A9" not in BUNDLE_RULE_IDS, (
        "R-A9 patched a coupling that only existed because the axes were merged; "
        "with independent axes it has nothing to do and the number is not reused"
    )
    assert len(set(BUNDLE_RULE_IDS)) == len(BUNDLE_RULE_IDS)


def _violating_bundles() -> dict[str, ProblemActionBundle]:
    """One bundle per rule, each tripping exactly the rule it is keyed by."""
    co_transformable = _problem(
        coefficient_fields={"nu": _ref(treatment="co_transformable_background")}
    )
    unknown_treatment = _problem(coefficient_fields={"nu": _ref(treatment="unknown")})
    return {
        "R-A1": _bundle(
            problem_instance=co_transformable,
            coefficient_field_actions={"nu": SHIFT},
            expected_residual_relation=_relation(
                equation_relation="same_equation", coefficient_relation="fixed"
            ),
        ),
        "R-A2": _bundle(
            expected_residual_relation=_relation(parameter_relation="transformed"),
            parameter_action=None,
        ),
        "R-A3": _bundle(
            problem_instance=co_transformable,
            coefficient_field_actions={"nu": IDENTITY},
            expected_residual_relation=_relation(coefficient_relation="co_transformed"),
        ),
        "R-A4": _bundle(
            problem_instance=co_transformable,
            coefficient_field_actions={"nu": IDENTITY},
            expected_residual_relation=_relation(coefficient_relation="fixed"),
        ),
        "R-A5": _bundle(
            coefficient_field_actions={"nu": SHIFT},
            expected_residual_relation=_relation(coefficient_relation="co_transformed"),
        ),
        "R-A6": _bundle(
            problem_instance=unknown_treatment,
            expected_residual_relation=_relation(),
        ),
        "R-A7": _bundle(
            state_action=_action("state", "spatial_translation"),
            parameter_action=_action("parameter", "scalar_rescale"),
            expected_residual_relation=_relation(parameter_relation="transformed"),
        ),
        "R-A8": _bundle(
            problem_instance=_problem(equation_form="conservative"),
            expected_residual_relation=_relation(
                expected_operator=ExpectedResidualOperator(
                    family="affine", parameters={"multiplier": 1.0, "offset": 0.1}
                )
            ),
        ),
        "R-A10": _bundle(
            expected_residual_relation=_relation(
                domain_relation="overlap_crop", boundary_relation="preserved"
            )
        ),
        "R-A11": _bundle(
            problem_instance=_problem(
                coefficient_fields={
                    "nu": CoefficientFieldRef(
                        field_name="nu",
                        coordinate_dependency=("x",),
                        treatment="co_transformable_background",
                    )
                }
            ),
            coefficient_field_actions={"nu": SHIFT},
            expected_residual_relation=_relation(coefficient_relation="co_transformed"),
        ),
        "R-A12": _bundle(
            expected_residual_relation=_relation(
                equation_relation="equation_invalid", domain_relation="not_preserved"
            )
        ),
        "R-A13": _bundle(
            problem_instance=unknown_treatment,
            expected_residual_relation=_relation(
                coefficient_relation="unknown",
                expected_operator=ExpectedResidualOperator(family="diagnostic_fitted"),
                tolerance_declaration={"rtol": 1e-6},
            ),
        ),
    }


@pytest.mark.parametrize("rule_id", BUNDLE_RULE_IDS)
def test_every_rule_has_a_violating_example(rule_id: str) -> None:
    """A rule no example trips is a rule nobody has tested."""
    bundle = _violating_bundles()[rule_id]
    with pytest.raises(InconsistentBundleError) as excinfo:
        validate_action_bundle(bundle)
    # Exact prefix, not a substring: validate_action_bundle stops at the FIRST
    # rule that fires, so a loose match would let an example filed under one
    # rule actually trip an earlier one and still pass -- which would leave the
    # rule it claims to cover untested.
    assert str(excinfo.value).startswith(f"{rule_id}: "), (
        f"{rule_id}'s example tripped a different rule first: {excinfo.value}"
    )


def test_the_examples_cover_every_rule_exactly() -> None:
    assert set(_violating_bundles()) == set(BUNDLE_RULE_IDS)


def test_a_consistent_bundle_validates() -> None:
    validate_action_bundle(_bundle())


def test_a_co_transforming_bundle_validates() -> None:
    problem = _problem(coefficient_fields={"nu": _ref(treatment="co_transformable_background")})
    validate_action_bundle(
        _bundle(
            problem_instance=problem,
            state_action=_action("state", "spatial_translation"),
            coefficient_field_actions={"nu": SHIFT},
            expected_residual_relation=_relation(
                equation_relation="equivalence_transformation",
                coefficient_relation="co_transformed",
            ),
        )
    )


def test_validate_refuses_a_non_bundle() -> None:
    with pytest.raises(ScopeValidationError, match="requires a ProblemActionBundle"):
        validate_action_bundle({"seed": 1})  # type: ignore[arg-type]


# --- scope ------------------------------------------------------------------


def test_v0_37a_adds_no_root_export() -> None:
    import pdelie

    for name in ("ProblemActionBundle", "CoefficientFieldRef", "ExpectedResidualRelation"):
        assert name not in pdelie.__all__


def test_the_contract_layer_stays_declarative() -> None:
    """v0.37a shipped contracts only, and they must stay contracts.

    This was originally a file-existence check -- that ``execute.py`` did not
    exist. v0.37b shipped it, so that assertion expired. What did not expire is
    the invariant it was protecting: the contract modules describe actions and
    never perform them. Asserted by checking they import no array library and
    define no execution entry point, which stays true as v0.37b and later grow.
    """
    import ast
    from pathlib import Path

    actions = Path(__file__).resolve().parents[1] / "src/pdelie/actions"
    for name in ("problem_spec.py", "action_bundle.py", "validate.py"):
        tree = ast.parse((actions / name).read_text())
        imported: set[str] = set()
        functions: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            elif isinstance(node, ast.FunctionDef):
                functions.add(node.name)
        assert "numpy" not in imported, (
            f"{name} imports numpy; a contract module describes actions and does "
            f"not perform them"
        )
        assert not {f for f in functions if f.startswith("execute")}, (
            f"{name} defines an execute* function; execution belongs in execute.py"
        )
