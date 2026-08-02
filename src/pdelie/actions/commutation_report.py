"""v0.37b: does the residual commute with the declared action?

Emits ``pdelie_problem_action_residual_relation``.

Three status fields, not one
============================

What the benchmark *expected*, what measurement *observed*, and whether the run
*met expectations* are three different facts, and collapsing them produces
statuses like ``wrong_direction_expected`` that are simultaneously an
expectation and a verdict.

=============================  ==========================================================
Field                          Vocabulary
=============================  ==========================================================
``expected_case``              ``valid_relation``, ``deliberate_obstruction``,
                               ``diagnostic_unknown``
``observed_relation_status``   ``confirmed``, ``violated``, ``inconclusive``, ``blocked``,
                               ``no_relation_declared``
``benchmark_outcome``          ``expected_result_observed``, ``unexpected_result_observed``,
                               ``not_evaluated``
=============================  ==========================================================

The deliberate-obstruction path (P-4) then reads without contradiction:
``expected_case=deliberate_obstruction``, ``observed_relation_status=violated``,
``benchmark_outcome=expected_result_observed``. The transformation failed, and
that is the result the benchmark wanted -- two facts, stated separately.

Determinism, and what can honestly claim it
===========================================

A report containing a wall-clock duration cannot be byte-for-byte reproducible,
so the payload is split. ``scientific_payload`` holds everything derived from
the data and is hashed into ``scientific_result_hash``; ``execution_metadata``
holds runtime and provenance and is hashed by nothing. The determinism test
asserts the *scientific payload* reproduces exactly and that the metadata's
*schema* is stable -- never whole-dictionary equality, which could only pass by
excluding the timing it claims to include.

Optional evidence is nested
===========================

Four ``<name>_available`` booleans beside four payloads is eight top-level
fields pretending to be four. ``optional_evidence`` is one stable field and
absence is a key being absent.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np

from pdelie.actions.action_bundle import ProblemActionBundle
from pdelie.actions.diagnostic_fit import FittedOperatorDiagnostic, fit_diagnostic_operator
from pdelie.actions.execute import BundleExecutionResult
from pdelie.actions.execution_config import ActionExecutionConfig
from pdelie.artifact.semantic_hash import semantic_hash
from pdelie.errors import ScopeValidationError, ShapeValidationError
from pdelie.residuals.operator_resolution import ResolvedResidualOperator

__all__ = [
    "BENCHMARK_OUTCOMES",
    "COMMUTATION_REPORT_SUMMARY_TYPE",
    "EXPECTED_CASES",
    "FITTED_OPERATOR_FAMILIES",
    "build_residual_commutation_report",
]

COMMUTATION_REPORT_SUMMARY_TYPE = "pdelie_problem_action_residual_relation"

#: What the bundle's author expected before anything ran.
EXPECTED_CASES: tuple[str, ...] = (
    "valid_relation",
    "deliberate_obstruction",
    "diagnostic_unknown",
)

#: Whether the run met that expectation. Independent of whether it succeeded.
BENCHMARK_OUTCOMES: tuple[str, ...] = (
    "expected_result_observed",
    "unexpected_result_observed",
    "not_evaluated",
)

#: Operator families for which a diagnostic fit is attempted at all.
FITTED_OPERATOR_FAMILIES: frozenset[str] = frozenset(
    {"linear_combination_of_derivatives", "affine", "diagnostic_fitted"}
)


def _l2(array: np.ndarray) -> float:
    flat = np.asarray(array, dtype=float).ravel()
    return float(np.sqrt(float(flat @ flat)))


def _linf(array: np.ndarray) -> float:
    flat = np.asarray(array, dtype=float).ravel()
    return 0.0 if flat.size == 0 else float(np.abs(flat).max())


def _expected_case(bundle: ProblemActionBundle, runtime_path: str) -> str:
    """What the bundle declared it expected, before measurement."""
    if not bundle.expected_residual_relation.permits_confirmation:
        return "diagnostic_unknown"
    if runtime_path == "P-4":
        return "deliberate_obstruction"
    return "valid_relation"


def _analytical_status(
    bundle: ProblemActionBundle,
    original: np.ndarray,
    transformed: np.ndarray,
    *,
    rtol: float,
    atol: float,
) -> tuple[str, dict[str, Any]]:
    """Decide the relation from the numbers alone. No fit is consulted."""
    relation = bundle.expected_residual_relation
    operator = relation.expected_operator

    if not relation.permits_confirmation:
        # R-A13: nothing was declared, so nothing can be confirmed or violated.
        return "no_relation_declared", {}

    original_l2 = _l2(original)
    if operator.family == "identity":
        predicted = np.asarray(original, dtype=float)
    elif operator.family == "scalar_multiplier":
        predicted = float(operator.parameters["multiplier"]) * np.asarray(original, dtype=float)
    elif operator.family == "affine":
        predicted = float(operator.parameters["multiplier"]) * np.asarray(
            original, dtype=float
        ) + float(operator.parameters["offset"])
    else:
        # linear_combination_of_derivatives declares a relation between derivative
        # terms rather than between the two residuals directly. v0.37b measures
        # the residual difference and reports it; it does not synthesise the
        # combination, which would need the derivative batch this function is not
        # given. Reported as inconclusive rather than guessed.
        difference = _l2(np.asarray(transformed, dtype=float) - np.asarray(original, dtype=float))
        return "inconclusive", {
            "reason": "linear_combination_of_derivatives is declared but v0.37b "
            "does not synthesise the combination; the raw difference is reported",
            "absolute_difference_l2": difference,
        }

    difference = np.asarray(transformed, dtype=float) - predicted
    absolute_error = _l2(difference)
    scale = max(_l2(predicted), original_l2)
    relative_error = absolute_error / scale if scale > 0.0 else None

    tolerance = atol + rtol * scale
    holds = absolute_error <= tolerance
    detail = {
        "absolute_error": absolute_error,
        # Both norms, named. `absolute_error` alone is ambiguous in a report that
        # gets cited: an L2 measurement compared against an Linf-derived bound is
        # a comparison between different quantities, and the v0.37c pilot blocked
        # on exactly that. Additive -- `absolute_error` keeps its meaning.
        "absolute_error_l2": absolute_error,
        "absolute_error_linf": _linf(difference),
        "relative_error": relative_error,
        "tolerance_applied": tolerance,
        "comparison_scale": scale,
        "comparison_scale_linf": _linf(predicted),
    }
    return ("confirmed" if holds else "violated"), detail


def _benchmark_outcome(expected_case: str, observed: str) -> str:
    if expected_case == "diagnostic_unknown":
        return "not_evaluated"
    if expected_case == "deliberate_obstruction":
        return (
            "expected_result_observed"
            if observed == "violated"
            else "unexpected_result_observed"
        )
    return "expected_result_observed" if observed == "confirmed" else "unexpected_result_observed"


def build_residual_commutation_report(
    bundle: ProblemActionBundle,
    execution: BundleExecutionResult,
    config: ActionExecutionConfig,
    original_residual: np.ndarray,
    transformed_residual: np.ndarray,
    *,
    runtime_seconds: float,
    provenance: Mapping[str, Any] | None = None,
    resolved_operator: ResolvedResidualOperator | None = None,
) -> dict[str, Any]:
    """Compare two residuals against the bundle's declared relation.

    The analytical decision is made first and is never revised by the diagnostic
    fit. The fit is attached as evidence when the operator family calls for one,
    and a ``violated`` verdict stays ``violated`` however well it fits.
    """
    if not isinstance(bundle, ProblemActionBundle):
        raise ScopeValidationError("bundle must be a ProblemActionBundle.")
    if not isinstance(execution, BundleExecutionResult):
        raise ScopeValidationError("execution must be a BundleExecutionResult.")
    if not isinstance(config, ActionExecutionConfig):
        raise ScopeValidationError("config must be an ActionExecutionConfig.")

    original = np.asarray(original_residual, dtype=float)
    transformed = np.asarray(transformed_residual, dtype=float)
    if original.shape != transformed.shape:
        raise ShapeValidationError(
            f"residuals have shapes {original.shape} and {transformed.shape}; a "
            f"commutation comparison between different shapes is not defined."
        )

    tolerances = dict(config.numerical_tolerances)
    rtol = float(tolerances.get("rtol", 0.0))
    atol = float(tolerances.get("atol", 0.0))

    # --- analytical first, and alone ---------------------------------------
    observed_status, detail = _analytical_status(
        bundle, original, transformed, rtol=rtol, atol=atol
    )
    expected_case = _expected_case(bundle, execution.runtime_path)
    outcome = _benchmark_outcome(expected_case, observed_status)

    # --- evidence, gathered after the decision and unable to alter it -------
    optional_evidence: dict[str, Any] = {}
    relation = bundle.expected_residual_relation
    if relation.expected_operator.family in FITTED_OPERATOR_FAMILIES:
        fitted: FittedOperatorDiagnostic = fit_diagnostic_operator(original, transformed)
        optional_evidence["fitted_operator_diagnostic"] = fitted.as_dict()
    if execution.transformed_parameters:
        declared = {
            key: float(value)
            for key, value in bundle.problem_instance.parameters.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        }
        deltas = {
            key: execution.transformed_parameters[key] - declared[key]
            for key in sorted(set(declared) & set(execution.transformed_parameters))
        }
        if any(delta != 0.0 for delta in deltas.values()):
            optional_evidence["parameter_deltas"] = deltas
    if execution.coefficient_shift_cells:
        moved = {
            name: cells
            for name, cells in execution.coefficient_shift_cells.items()
            if cells != 0
        }
        if moved:
            optional_evidence["coefficient_field_shift_cells"] = moved
    if relation.expected_operator.family == "scalar_multiplier":
        optional_evidence["expected_multiplier"] = float(
            relation.expected_operator.parameters["multiplier"]
        )

    # v0.38: the resolved operator, if the caller resolved one. Inside the
    # scientific payload -- and so inside the scientific hash -- because which
    # operator produced a number is part of what the number means. The v0.38e
    # defect was a hash computed over a declaration that named a different
    # operator than the one evaluated, and a hash that excluded this field would
    # be unable to tell those two runs apart.
    operator_block: dict[str, Any] = (
        {"resolved_operator": None}
        if resolved_operator is None
        else {"resolved_operator": resolved_operator.as_dict()}
    )

    scientific_payload: dict[str, Any] = {
        "bundle_hash": bundle.identity(),
        **operator_block,
        "runtime_path": execution.runtime_path,
        "expected_case": expected_case,
        "observed_relation_status": observed_status,
        "benchmark_outcome": outcome,
        "expected_operator_family": relation.expected_operator.family,
        "relation_axes": {
            "equation_relation": relation.equation_relation,
            "parameter_relation": relation.parameter_relation,
            "coefficient_relation": relation.coefficient_relation,
            "domain_relation": relation.domain_relation,
            "boundary_relation": relation.boundary_relation,
        },
        "comparison_metric": "l2",
        "residual_shape": list(original.shape),
        "original_residual_l2": _l2(original),
        "transformed_residual_l2": _l2(transformed),
        "state_shift_cells": execution.state_shift_cells,
        "tolerances_applied": {"rtol": rtol, "atol": atol},
        "analytical_detail": detail,
        "optional_evidence": optional_evidence,
        "diagnostic_only": True,
    }

    execution_metadata: dict[str, Any] = {
        "runtime_seconds": float(runtime_seconds),
        "interpolation_backend": config.interpolation_backend,
        "seed": config.seed,
        "deterministic_expected": config.deterministic_expected,
        "provenance": dict(provenance or {}),
    }

    return {
        "summary_type": COMMUTATION_REPORT_SUMMARY_TYPE,
        "summary_schema_version": "0.1",
        "scientific_payload": scientific_payload,
        # Hashes the science, never the run. runtime_seconds cannot be
        # byte-reproducible, so it is excluded from what claims to be.
        "scientific_result_hash": semantic_hash(scientific_payload),
        "execution_metadata": execution_metadata,
    }
