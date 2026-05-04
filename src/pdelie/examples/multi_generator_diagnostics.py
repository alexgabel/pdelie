from __future__ import annotations

import json

import numpy as np

from pdelie import GeneratorFamily
from pdelie.data import generate_heat_1d_field_batch
from pdelie.reporting import summarize_generator_confidence
from pdelie.residuals import HeatResidualEvaluator
from pdelie.symmetry import compare_generator_spans, diagnose_generator_family_closure, validate_symmetry_candidate


_SUMMARY_SCHEMA_VERSION = "0.1"


def _x_basis_spec(labels: list[str] | None = None, powers: list[list[int]] | None = None) -> dict[str, object]:
    powers = [[0], [1]] if powers is None else powers
    if labels is None:
        labels = ["1", "x"] if powers == [[0], [1]] else [("1" if item == [0] else f"x^{item[0]}") for item in powers]
    return {
        "variables": ["x"],
        "component_names": ["xi"],
        "basis_terms": [
            {"label": label, "powers": power}
            for label, power in zip(labels, powers)
        ],
        "component_ordering": ["xi"],
        "term_ordering": list(labels),
        "layout": "component_major",
    }


def _generator(
    coefficients: list[list[float]],
    *,
    basis_spec: dict[str, object] | None = None,
    name: str,
) -> GeneratorFamily:
    coefficients_array = np.asarray(coefficients, dtype=float)
    return GeneratorFamily(
        parameterization="algebraic_diagnostic_fixture",
        coefficients=coefficients_array,
        basis_spec=_x_basis_spec() if basis_spec is None else basis_spec,
        normalization="runtime_fixture",
        generator_names=[f"{name}_{index}" for index in range(coefficients_array.shape[0])],
        diagnostics={"fixture_name": name},
    )


def _expected_affine_x_structure_constants() -> list[list[list[float]]]:
    expected = np.zeros((2, 2, 2), dtype=float)
    expected[0, 1, 0] = 1.0
    expected[1, 0, 0] = -1.0
    return expected.tolist()


def run_multi_generator_diagnostics_example() -> dict[str, object]:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=9, num_points=32, seed=27027)
    evaluator = HeatResidualEvaluator()

    closed_affine = _generator([[1.0, 0.0], [0.0, 1.0]], name="affine_x")
    nonclosed = _generator(
        [[1.0, 0.0], [0.0, 1.0]],
        basis_spec=_x_basis_spec(labels=["1", "x^2"], powers=[[0], [2]]),
        name="nonclosed_polynomial",
    )
    rank_deficient = _generator([[1.0, 0.0], [2.0, 0.0]], name="rank_deficient_affine")

    closed_closure = diagnose_generator_family_closure(
        closed_affine,
        expected_structure_constants=_expected_affine_x_structure_constants(),
    )
    nonclosed_closure = diagnose_generator_family_closure(nonclosed)
    rank_deficient_closure = diagnose_generator_family_closure(rank_deficient)
    rank_deficient_span = compare_generator_spans(closed_affine, rank_deficient)

    closed_validation = validate_symmetry_candidate(
        field,
        closed_affine,
        residual_evaluator=evaluator,
        source_candidate_id="example_affine_x_closed_supplied_family",
    )
    nonclosed_required_validation = validate_symmetry_candidate(
        field,
        nonclosed,
        residual_evaluator=evaluator,
        source_candidate_id="example_nonclosed_required",
    )
    nonclosed_optional_validation = validate_symmetry_candidate(
        field,
        nonclosed,
        residual_evaluator=evaluator,
        source_candidate_id="example_nonclosed_optional",
        closure_required=False,
    )

    confidence = summarize_generator_confidence(
        candidate_validation=closed_validation,
        extra_metrics={
            "diagnostic_only": True,
            "public_multi_generator_fitting_promoted": False,
            "finite_multi_generator_action_available": False,
        },
    )

    return {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": "multi_generator_diagnostics_example",
        "decision": {
            "release": "v0.27.0",
            "conclusion": "multi_generator_diagnostics_feasible_fitting_deferred",
            "public_promotion_decision": "no_public_multi_generator_fitting_or_invariant_action",
        },
        "algebraic_diagnostics": {
            "closed_affine_x": closed_closure,
            "nonclosed_polynomial": nonclosed_closure,
            "rank_deficient_affine": rank_deficient_closure,
            "rank_deficient_span_comparison": rank_deficient_span,
        },
        "pde_context_diagnostics": {
            "closed_affine_x": closed_validation,
            "nonclosed_required": nonclosed_required_validation,
            "nonclosed_optional": nonclosed_optional_validation,
        },
        "fit_probe_diagnostics": {
            "label": "fit_probe_diagnostic_only",
            "runtime_example_runs_fit_probe": False,
            "public_fitting_api_promoted": False,
        },
        "confidence": confidence,
        "extra_metrics": {
            "example_name": "multi_generator_diagnostics",
            "field_equation": "heat_1d",
            "generator_source": "supplied_generator_family_objects",
            "closure_does_not_imply_pde_symmetry": True,
            "no_bch_composition": True,
            "no_exponential_flow_integration": True,
            "no_multi_parameter_orbit_chart": True,
        },
    }


def main() -> None:
    print(json.dumps(run_multi_generator_diagnostics_example(), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
