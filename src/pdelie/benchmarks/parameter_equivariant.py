"""v0.37c: registries and dispatch for the six-case admissibility benchmark.

Scaffolding only. This module declares *what* the benchmark is -- the six cases,
the five coefficient profiles, the two alpha grids -- and can build a coefficient
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

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from pdelie.errors import ScopeValidationError

__all__ = [
    "CONFIRMATORY_ALPHA_GRID",
    "EXPECTED_CLASSIFICATIONS",
    "PILOT_ALPHA_GRID",
    "PROFILE_REGISTRY",
    "SIX_BENCHMARK_CASES",
    "BenchmarkCase",
    "CoefficientProfile",
    "alpha_grid",
    "build_coefficient_field",
    "resolve_case",
]

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
    "invalid_state_only_with_monotone_coefficient",
    "invalid_parameter_only_without_state",
    "invalid_state_only_with_localized_coefficient",
)


def _constant(x: np.ndarray) -> np.ndarray:
    return np.zeros_like(x)


def _sinusoidal(k: float) -> Callable[[np.ndarray], np.ndarray]:
    def shape(x: np.ndarray) -> np.ndarray:
        return np.sin(k * x)

    return shape


def _monotone_smooth(width_fraction: float) -> Callable[[np.ndarray], np.ndarray]:
    def shape(x: np.ndarray) -> np.ndarray:
        span = float(x[-1] - x[0])
        return np.asarray(np.tanh((x - 0.5 * (x[0] + x[-1])) / (width_fraction * span)))

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
    "monotone_smooth": CoefficientProfile(
        profile_id="monotone_smooth",
        baseline=0.1,
        shape=_monotone_smooth(0.1),
        description="a(x) = a0*(1 + alpha*tanh((x - x0)/w))",
        parameters={"w_fraction": 0.1},
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
        }


SIX_BENCHMARK_CASES: dict[str, BenchmarkCase] = {
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
    "C-4": BenchmarkCase(
        case_id="C-4",
        equation_family="heat_1d",
        profile_id="monotone_smooth",
        coefficient_treatment="fixed_background",
        coefficient_relation="fixed",
        state_action_family="spatial_translation",
        parameter_action_family=None,
        expected_operator_family="identity",
        expected_classification="invalid_state_only_with_monotone_coefficient",
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
    if case_id not in SIX_BENCHMARK_CASES:
        raise ScopeValidationError(
            f"unknown benchmark case {case_id!r}; the six are "
            f"{sorted(SIX_BENCHMARK_CASES)}."
        )
    return SIX_BENCHMARK_CASES[case_id]


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
