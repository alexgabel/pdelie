"""v0.37c: registries and dispatch for the parameter-equivariant admissibility benchmark.

Scaffolding only. This module declares *what* the benchmark is -- the cases,
the coefficient profiles, the two alpha grids -- and can build a coefficient
field for a given (profile, alpha). It runs nothing and writes no pilot data.

Everything here is frozen by ``docs/design/v0_37c_hypothesis_freeze.md``, and
``tests/test_v0_37c_benchmark_scaffolding.py`` parses that document and asserts
the registries match it. A registry that drifts from its freeze is a registry
nobody can trust, so the two are checked against each other rather than
maintained in parallel by hand.

**No tolerance appears in this module.** Thresholds are set by the confirmatory
freeze, after a pilot measures them, and a tolerance living here would let the
benchmark quietly define its own pass mark.

Positivity
==========

Every profile has the form ``a(x) = a0*(1 + alpha*f(x))`` with ``max|f| <= 1`` and
``0 <= alpha < 1``, so ``(1 + alpha*f) > 0`` and the diffusivity is strictly positive
everywhere. An additive ``a0 + alpha*f(x)`` would go negative for ``alpha > a0``, which
is not a more demanding test but a different and ill-posed equation.
:func:`build_coefficient_field` asserts positivity rather than trusting the
algebra.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from pdelie.errors import ScopeValidationError

__all__ = [
    "BENCHMARK_CASES",
    "CONFIRMATORY_ALPHA_GRID",
    "EXPECTED_CLASSIFICATIONS",
    "PILOT_ALPHA_GRID",
    "PROFILE_REGISTRY",
    "BenchmarkCase",
    "CoefficientProfile",
    "alpha_grid",
    "build_coefficient_field",
    "resolve_case",
    "run_admissibility_benchmark",
]

#: Default whole-cell translation, used by any case that does not override it.
#: Whole cells so the shift is exact under ``exact_grid_shift``.
DEFAULT_TRANSLATION_CELLS = 3

#: Frozen. ``0.0`` is a control: at zero dose every profile degenerates to
#: ``constant``, so the obstruction cases must become indistinguishable from C-1.
PILOT_ALPHA_GRID: tuple[float, ...] = (0.0, 0.05, 0.1, 0.2, 0.4, 0.8)

#: Frozen, and disjoint from the pilot grid by construction and by test.
CONFIRMATORY_ALPHA_GRID: tuple[float, ...] = (0.025, 0.075, 0.15, 0.3, 0.6)

#: The classification each case is expected to receive. The benchmark is not
#: "pass all six" -- it is "distinguish all six".
EXPECTED_CLASSIFICATIONS: tuple[str, ...] = (
    "valid_same_target",
    "valid_equivalence",
    "invalid_fixed_background_obstruction",
    "invalid_parameter_only_without_state",
    "invalid_state_only_with_localized_coefficient",
)


def _constant(x: np.ndarray) -> np.ndarray:
    return np.zeros_like(x)


def _sinusoidal(k: float) -> Callable[[np.ndarray], np.ndarray]:
    def shape(x: np.ndarray) -> np.ndarray:
        return np.sin(k * x)

    return shape



def _localized_bump(width_fraction: float) -> Callable[[np.ndarray], np.ndarray]:
    def shape(x: np.ndarray) -> np.ndarray:
        span = float(x[-1] - x[0])
        return np.asarray(
            np.exp(-(((x - 0.5 * (x[0] + x[-1])) / (width_fraction * span)) ** 2))
        )

    return shape


@dataclass(frozen=True)
class CoefficientProfile:
    """``a(x) = a0*(1 + alpha*f(x))`` with ``max|f| <= 1``."""

    profile_id: str
    baseline: float
    shape: Callable[[np.ndarray], np.ndarray]
    description: str
    parameters: dict[str, float]

    def __post_init__(self) -> None:
        if self.baseline <= 0.0:
            raise ScopeValidationError(
                f"profile {self.profile_id!r} has baseline {self.baseline!r}; a "
                f"non-positive baseline is not a parabolic problem."
            )

    def as_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "baseline": self.baseline,
            "description": self.description,
            "parameters": dict(self.parameters),
        }


PROFILE_REGISTRY: dict[str, CoefficientProfile] = {
    "constant": CoefficientProfile(
        profile_id="constant",
        baseline=0.1,
        shape=_constant,
        description="a(x) = a0; the alpha knob has no effect and this is the control",
        parameters={},
    ),
    "sinusoidal": CoefficientProfile(
        profile_id="sinusoidal",
        baseline=0.1,
        shape=_sinusoidal(2.0),
        description="a(x) = a0*(1 + alpha*sin(k x))",
        parameters={"k": 2.0},
    ),
    "localized_bump": CoefficientProfile(
        profile_id="localized_bump",
        baseline=0.1,
        shape=_localized_bump(0.05),
        description="a(x) = a0*(1 + alpha*exp(-((x - x0)/w)^2))",
        parameters={"w_fraction": 0.05},
    ),
    "higher_frequency": CoefficientProfile(
        profile_id="higher_frequency",
        baseline=0.1,
        shape=_sinusoidal(6.0),
        description="a(x) = a0*(1 + alpha*sin(k x)) with k = 6",
        parameters={"k": 6.0},
    ),
}


@dataclass(frozen=True)
class BenchmarkCase:
    """One frozen case. Declares the claim; does not evaluate it."""

    case_id: str
    equation_family: str
    profile_id: str
    coefficient_treatment: str
    coefficient_relation: str
    state_action_family: str
    parameter_action_family: str | None
    expected_operator_family: str
    expected_classification: str
    is_deliberate_obstruction: bool
    #: Parameters of the state action. ``shift_cells`` is a whole number of grid
    #: cells; the physical offset is that times ``dx``, computed at run time.
    state_action_parameters: Mapping[str, Any] = field(
        default_factory=lambda: {"shift_cells": DEFAULT_TRANSLATION_CELLS}
    )
    #: Parameters of the parameter action, or ``None`` when there is none.
    #: Frozen here rather than left to the runner, so the case is fully
    #: self-describing and the value cannot become an implicit constant.
    parameter_action_parameters: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.profile_id not in PROFILE_REGISTRY:
            raise ScopeValidationError(
                f"case {self.case_id!r} names profile {self.profile_id!r}, which is "
                f"not registered: {sorted(PROFILE_REGISTRY)}."
            )
        if self.expected_classification not in EXPECTED_CLASSIFICATIONS:
            raise ScopeValidationError(
                f"case {self.case_id!r} expects {self.expected_classification!r}, "
                f"which is not a frozen classification."
            )
        if (self.parameter_action_family is None) != (self.parameter_action_parameters is None):
            raise ScopeValidationError(
                f"case {self.case_id!r} declares parameter_action_family="
                f"{self.parameter_action_family!r} and parameter_action_parameters="
                f"{self.parameter_action_parameters!r}. A family without its "
                f"parameters cannot be executed, and parameters without a family "
                f"cannot be interpreted."
            )
        if self.state_action_family == "spatial_translation":
            cells = dict(self.state_action_parameters).get("shift_cells")
            if not isinstance(cells, int) or isinstance(cells, bool) or cells == 0:
                raise ScopeValidationError(
                    f"case {self.case_id!r} translates but declares shift_cells="
                    f"{cells!r}; it must be a non-zero integer number of cells."
                )

    def as_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "equation_family": self.equation_family,
            "profile_id": self.profile_id,
            "coefficient_treatment": self.coefficient_treatment,
            "coefficient_relation": self.coefficient_relation,
            "state_action_family": self.state_action_family,
            "parameter_action_family": self.parameter_action_family,
            "expected_operator_family": self.expected_operator_family,
            "expected_classification": self.expected_classification,
            "is_deliberate_obstruction": self.is_deliberate_obstruction,
            "state_action_parameters": dict(self.state_action_parameters),
            "parameter_action_parameters": (
                None
                if self.parameter_action_parameters is None
                else dict(self.parameter_action_parameters)
            ),
        }


BENCHMARK_CASES: dict[str, BenchmarkCase] = {
    "C-1": BenchmarkCase(
        case_id="C-1",
        equation_family="heat_1d",
        profile_id="constant",
        coefficient_treatment="fixed_background",
        coefficient_relation="not_applicable",
        state_action_family="spatial_translation",
        parameter_action_family=None,
        expected_operator_family="identity",
        expected_classification="valid_same_target",
        is_deliberate_obstruction=False,
    ),
    "C-2": BenchmarkCase(
        case_id="C-2",
        equation_family="heat_1d",
        profile_id="sinusoidal",
        coefficient_treatment="co_transformable_background",
        coefficient_relation="co_transformed",
        state_action_family="spatial_translation",
        parameter_action_family=None,
        expected_operator_family="identity",
        expected_classification="valid_equivalence",
        is_deliberate_obstruction=False,
    ),
    "C-3": BenchmarkCase(
        case_id="C-3",
        equation_family="heat_1d",
        profile_id="sinusoidal",
        coefficient_treatment="fixed_background",
        coefficient_relation="fixed",
        state_action_family="spatial_translation",
        parameter_action_family=None,
        expected_operator_family="identity",
        expected_classification="invalid_fixed_background_obstruction",
        is_deliberate_obstruction=True,
    ),
    "C-5": BenchmarkCase(
        case_id="C-5",
        equation_family="burgers_1d",
        profile_id="constant",
        coefficient_treatment="fixed_background",
        coefficient_relation="not_applicable",
        state_action_family="identity",
        parameter_action_family="scalar_rescale",
        parameter_action_parameters={"factor": 2.0},
        state_action_parameters={},
        expected_operator_family="scalar_multiplier",
        expected_classification="invalid_parameter_only_without_state",
        is_deliberate_obstruction=True,
    ),
    "C-6": BenchmarkCase(
        case_id="C-6",
        equation_family="advection_diffusion_1d",
        profile_id="localized_bump",
        coefficient_treatment="fixed_background",
        coefficient_relation="fixed",
        state_action_family="spatial_translation",
        parameter_action_family=None,
        expected_operator_family="identity",
        expected_classification="invalid_state_only_with_localized_coefficient",
        is_deliberate_obstruction=True,
    ),
}


def resolve_case(case_id: str) -> BenchmarkCase:
    if case_id not in BENCHMARK_CASES:
        raise ScopeValidationError(
            f"unknown benchmark case {case_id!r}; the six are "
            f"{sorted(BENCHMARK_CASES)}."
        )
    return BENCHMARK_CASES[case_id]


def alpha_grid(phase: str) -> tuple[float, ...]:
    """The frozen alpha grid for ``'pilot'`` or ``'confirmatory'``."""
    if phase == "pilot":
        return PILOT_ALPHA_GRID
    if phase == "confirmatory":
        return CONFIRMATORY_ALPHA_GRID
    raise ScopeValidationError(
        f"phase {phase!r} is not one of ('pilot', 'confirmatory'). The grids are "
        f"disjoint by design and there is no third phase."
    )


def build_coefficient_field(
    profile_id: str, alpha: float, x: Sequence[float] | np.ndarray
) -> np.ndarray:
    """``a₀·(1 + alpha·f(x))`` for a registered profile, with positivity asserted."""
    if profile_id not in PROFILE_REGISTRY:
        raise ScopeValidationError(
            f"unknown profile {profile_id!r}; registered: {sorted(PROFILE_REGISTRY)}."
        )
    if isinstance(alpha, bool) or not isinstance(alpha, (int, float)):
        raise ScopeValidationError("alpha must be a real number.")
    if not 0.0 <= float(alpha) < 1.0:
        raise ScopeValidationError(
            f"alpha={alpha!r} is outside [0, 1). The bound is what keeps "
            f"(1 + alpha*f) positive given |f|inf <= 1; outside it the problem "
            f"is not parabolic."
        )

    profile = PROFILE_REGISTRY[profile_id]
    grid = np.asarray(x, dtype=float)
    shape = np.asarray(profile.shape(grid), dtype=float)

    magnitude = float(np.abs(shape).max()) if shape.size else 0.0
    if magnitude > 1.0 + 1e-12:
        raise ScopeValidationError(
            f"profile {profile_id!r} has |f|inf = {magnitude!r} > 1, which breaks "
            f"the positivity guarantee the a0*(1 + alpha*f) form rests on."
        )

    values = profile.baseline * (1.0 + float(alpha) * shape)
    if values.min() <= 0.0:
        raise ScopeValidationError(
            f"profile {profile_id!r} at alpha={alpha!r} produced a non-positive "
            f"diffusivity (min {values.min()!r}); positivity is asserted rather "
            f"than assumed."
        )
    return values


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
#
# The runner builds a real ProblemActionBundle, executes it through
# pdelie.actions.execute, and reads the measured error out of a real
# commutation report. It deliberately does not compute the comparison itself:
# a benchmark that measures with its own arithmetic is not measuring what
# ships, and a discrepancy between the two would be invisible.
#
# It reports MAGNITUDES, never verdicts. No threshold is applied here, because
# no threshold exists yet -- that is what the pilot is for.

_GENERATORS: dict[str, str] = {
    "heat_1d": "generate_heat_1d_field_batch",
    "burgers_1d": "generate_burgers_1d_field_batch",
    "advection_diffusion_1d": "generate_advection_diffusion_1d_field_batch",
}


def _build_field(
    equation_family: str, seed: int, num_times: int, num_points: int
) -> Any:
    from pdelie import data

    generator = getattr(data, _GENERATORS[equation_family])
    return generator(
        batch_size=1, num_times=num_times, num_points=num_points, seed=seed
    )


def _evaluator(equation_family: str, coefficient: np.ndarray | float) -> Any:
    from pdelie.residuals import (
        AdvectionDiffusionResidualEvaluator,
        BurgersResidualEvaluator,
        HeatResidualEvaluator,
    )

    if equation_family == "heat_1d":
        return HeatResidualEvaluator(diffusivity=coefficient)
    if equation_family == "burgers_1d":
        return BurgersResidualEvaluator(diffusivity=coefficient)
    return AdvectionDiffusionResidualEvaluator(
        advection_speed=1.0, diffusivity=coefficient
    )


def _measure_case(
    case: BenchmarkCase, alpha: float, seed: int, num_times: int, num_points: int
) -> dict[str, Any]:
    """One (case, alpha, seed) measurement, through the shipped machinery."""
    import numpy as np

    from pdelie.actions import (
        ActionExecutionConfig,
        ActionRef,
        CoefficientFieldRef,
        CoordinateFieldAction,
        ExpectedResidualOperator,
        ExpectedResidualRelation,
        ProblemActionBundle,
        ProblemInstanceSpec,
        build_residual_commutation_report,
        execute_bundle,
        validate_action_bundle,
    )
    from pdelie.contracts import FieldBatch

    field = _build_field(case.equation_family, seed, num_times, num_points)
    axis = field.dims.index("x")
    x = np.asarray(field.coords["x"], dtype=float)
    spacing = float(np.diff(x)[0])
    coefficient = build_coefficient_field(case.profile_id, alpha, x)

    translating = case.state_action_family == "spatial_translation"
    cells = int(dict(case.state_action_parameters).get("shift_cells", 0))
    offset = cells * spacing if translating else 0.0
    co_moves = case.coefficient_relation == "co_transformed"

    reference = CoefficientFieldRef(
        field_name="nu",
        coordinate_dependency=("x",),
        treatment=case.coefficient_treatment,
        analytical_spec={"profile_id": case.profile_id, "alpha": float(alpha)},
    )
    problem = ProblemInstanceSpec(
        equation_family=case.equation_family,
        equation_form="nonconservative",
        parameters={"nu": PROFILE_REGISTRY[case.profile_id].baseline},
        coefficient_fields={"nu": reference},
        spatial_axis_name="x",
        time_axis_name="t",
        domain_type="periodic_uniform",
    )
    rescale_factor = float(
        dict(case.parameter_action_parameters or {}).get("factor", 1.0)
    )
    operator = (
        ExpectedResidualOperator(
            family="scalar_multiplier", parameters={"multiplier": rescale_factor}
        )
        if case.expected_operator_family == "scalar_multiplier"
        else ExpectedResidualOperator(family="identity")
    )
    relation = ExpectedResidualRelation(
        equation_relation=(
            "equivalence_transformation" if co_moves else "same_equation"
        ),
        parameter_relation=(
            "transformed" if case.parameter_action_family else "preserved"
        ),
        coefficient_relation=case.coefficient_relation,
        domain_relation="preserved",
        boundary_relation="preserved",
        expected_operator=operator,
    )
    bundle = ProblemActionBundle(
        problem_instance=problem,
        state_action=ActionRef(
            action_target="state",
            action_family=case.state_action_family,
            action_parameter_id=f"{case.case_id}_state",
            parameters={"offset": offset} if translating else {},
        ),
        domain_action=ActionRef(
            action_target="domain", action_family="identity", action_parameter_id="id"
        ),
        boundary_action=ActionRef(
            action_target="domain", action_family="identity", action_parameter_id="id"
        ),
        coefficient_field_actions={
            "nu": CoordinateFieldAction(family="shift", parameters={"offset": offset})
            if co_moves
            else CoordinateFieldAction(family="identity")
        },
        expected_residual_relation=relation,
        parameter_action=(
            ActionRef(
                action_target="parameter",
                action_family="scalar_rescale",
                action_parameter_id=f"{case.case_id}_param",
                parameters={"factor": rescale_factor},
            )
            if case.parameter_action_family
            else None
        ),
    )
    validate_action_bundle(bundle)

    config = ActionExecutionConfig(
        interpolation_backend="exact_grid_shift",
        numerical_tolerances={"rtol": 0.0, "atol": 0.0},
        seed=None,
        deterministic_expected=True,
    )
    execution = execute_bundle(
        bundle, field, config, coefficient_values={"nu": coefficient}
    )

    base_evaluator = _evaluator(case.equation_family, coefficient)
    original = base_evaluator.evaluate(field).residual

    if case.parameter_action_family == "scalar_rescale":
        # C-5 rescales the state itself; the transformed residual is R(cu).
        rescaled = FieldBatch(
            schema_version=field.schema_version,
            values=np.asarray(field.values) * rescale_factor,
            dims=field.dims,
            coords=dict(field.coords),
            var_names=field.var_names,
            metadata=dict(field.metadata),
            preprocess_log=list(field.preprocess_log),
            mask=None,
        )
        transformed = base_evaluator.evaluate(rescaled).residual
        expected = original
    else:
        moved_coefficient = (
            execution.transformed_coefficients["nu"] if co_moves else coefficient
        )
        transformed = _evaluator(case.equation_family, moved_coefficient).evaluate(
            execution.transformed_field
        ).residual
        expected = np.roll(original, execution.state_shift_cells, axis=axis)

    report = build_residual_commutation_report(
        bundle, execution, config, expected, transformed, runtime_seconds=0.0
    )
    payload = report["scientific_payload"]
    return {
        "case_id": case.case_id,
        "alpha": float(alpha),
        "seed": int(seed),
        "runtime_path": payload["runtime_path"],
        "expected_operator_family": payload["expected_operator_family"],
        "absolute_error_l2": float(payload["analytical_detail"]["absolute_error_l2"]),
        "absolute_error_linf": float(payload["analytical_detail"]["absolute_error_linf"]),
        "comparison_scale": float(payload["analytical_detail"]["comparison_scale"]),
        "shift_cells": cells if translating else 0,
        "rescale_factor": rescale_factor if case.parameter_action_family else None,
        "is_deliberate_obstruction": case.is_deliberate_obstruction,
    }


def run_admissibility_benchmark(
    *,
    phase: str,
    seeds: Sequence[int],
    num_times: int = 32,
    num_points: int = 32,
) -> dict[str, Any]:
    """Measure every case at every alpha for every seed. Reports magnitudes only.

    No verdict is computed and no threshold applied: the whole point of the
    pilot is to find out what the magnitudes are before anyone picks one.
    """
    grid = alpha_grid(phase)
    if not seeds:
        raise ScopeValidationError("seeds must be non-empty; a run with no seed is not a run.")
    measurements = [
        _measure_case(case, alpha, seed, num_times, num_points)
        for case in BENCHMARK_CASES.values()
        for alpha in grid
        for seed in seeds
    ]
    return {
        "summary_type": "pdelie_parameter_equivariant_benchmark_run",
        "summary_schema_version": "0.1",
        "phase": phase,
        "alpha_grid": list(grid),
        "seeds": [int(s) for s in seeds],
        "grid_shape": {"num_times": num_times, "num_points": num_points},
        "measurement_count": len(measurements),
        "measurements": measurements,
        "diagnostic_only": True,
    }
