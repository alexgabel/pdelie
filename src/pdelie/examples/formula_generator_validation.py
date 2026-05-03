from __future__ import annotations

import json

import numpy as np

from pdelie import GeneratorFamily, InvariantMapSpec
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.data import generate_heat_1d_field_batch
from pdelie.residuals import HeatResidualEvaluator
from pdelie.symmetry import FormulaGeneratorFamily, validate_symmetry_candidate


_SUMMARY_SCHEMA_VERSION = "0.1"
_DOMAIN_LENGTH = 2.0 * np.pi


def _const(value: float) -> dict[str, object]:
    return {"node": "const", "value": float(value)}


def _var(name: str) -> dict[str, object]:
    return {"node": "var", "name": name}


def _translation_generator() -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.asarray([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )


def _translation_spec_payload() -> dict[str, object]:
    return InvariantMapSpec(
        generator_metadata=_translation_generator().to_dict(),
        construction_method="uniform_translation",
        parameters={"axis": "x", "shift": _DOMAIN_LENGTH / 8.0},
        domain_validity="global",
        inverse_available=True,
        diagnostics={},
    ).to_dict()


def _formula(name: str, *, tau: dict[str, object], xi: dict[str, object], phi: dict[str, object], **kwargs: object) -> FormulaGeneratorFamily:
    return FormulaGeneratorFamily(
        formula_generators=[
            {
                "name": name,
                "components": {"tau": tau, "xi": xi, "phi": phi},
            }
        ],
        **kwargs,
    )


def run_formula_generator_validation_example() -> dict[str, object]:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=9, num_points=32, seed=17001)
    evaluator = HeatResidualEvaluator()

    cases = [
        {
            "case_name": "affine_formula",
            "report": validate_symmetry_candidate(
                field,
                _formula("affine_formula", tau=_const(0.0), xi=_var("x"), phi=_var("u")),
                residual_evaluator=evaluator,
                source_candidate_id="affine_formula",
            ),
        },
        {
            "case_name": "trigonometric_formula",
            "report": validate_symmetry_candidate(
                field,
                _formula(
                    "trigonometric_formula",
                    tau=_const(0.0),
                    xi={"node": "sin", "arg": _var("x")},
                    phi={"node": "cos", "arg": _var("u")},
                ),
                residual_evaluator=evaluator,
                source_candidate_id="trigonometric_formula",
            ),
        },
        {
            "case_name": "rational_formula",
            "report": validate_symmetry_candidate(
                field,
                _formula(
                    "rational_formula",
                    tau=_const(0.0),
                    xi={
                        "node": "reciprocal",
                        "arg": {
                            "node": "add",
                            "terms": [
                                _const(1.0),
                                {"node": "pow", "base": _var("u"), "exponent": 2},
                            ],
                        },
                    },
                    phi=_const(0.0),
                ),
                residual_evaluator=evaluator,
                source_candidate_id="rational_formula",
            ),
        },
        {
            "case_name": "formula_with_uniform_translation_transform",
            "report": validate_symmetry_candidate(
                field,
                _formula(
                    "formula_translation",
                    tau=_const(0.0),
                    xi=_const(1.0),
                    phi=_const(0.0),
                    finite_transform_spec=_translation_spec_payload(),
                ),
                residual_evaluator=evaluator,
                source_candidate_id="formula_translation_with_finite_transform",
            ),
        },
        {
            "case_name": "failed_nonfinite_formula",
            "report": validate_symmetry_candidate(
                field,
                _formula(
                    "failed_nonfinite_formula",
                    tau=_const(0.0),
                    xi={"node": "reciprocal", "arg": _const(0.0)},
                    phi=_const(0.0),
                ),
                residual_evaluator=evaluator,
                source_candidate_id="failed_nonfinite_formula",
            ),
        },
    ]

    return {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": "formula_generator_validation_example",
        "cases": cases,
        "extra_metrics": {
            "example_name": "formula_generator_validation",
            "candidate_kinds": sorted({case["report"]["candidate_kind"] for case in cases}),
            "conclusions": [case["report"]["conclusion"] for case in cases],
            "expression_policy": "safe_json_ast_no_callables_no_executable_strings",
            "interpretation": "configured_empirical_validation_not_mathematical_proof",
        },
    }


def main() -> None:
    print(json.dumps(run_formula_generator_validation_example(), indent=2))


if __name__ == "__main__":
    main()
