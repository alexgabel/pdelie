from __future__ import annotations

import json

import numpy as np

from pdelie import GeneratorFamily, InvariantMapSpec
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.data import generate_heat_1d_field_batch, generate_kdv_1d_field_batch
from pdelie.residuals import HeatResidualEvaluator, KdVResidualEvaluator
from pdelie.symmetry import validate_symmetry_candidate

_SUMMARY_SCHEMA_VERSION = "0.1"
_DOMAIN_LENGTH = 2.0 * np.pi


def _translation_generator(coefficients: list[float] | None = None) -> GeneratorFamily:
    coefficients = [1.0, 0.0, 0.0, 0.0] if coefficients is None else coefficients
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.asarray([coefficients], dtype=float),
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


def run_symmetry_candidate_validation_example() -> dict[str, object]:
    heat = generate_heat_1d_field_batch(batch_size=3, num_times=9, num_points=32, seed=16001)
    kdv = generate_kdv_1d_field_batch(batch_size=3, num_times=9, num_points=32, num_modes=1, seed=16002)
    translation = _translation_generator()

    cases = [
        {
            "case_name": "heat_generator_family",
            "report": validate_symmetry_candidate(
                heat,
                translation,
                residual_evaluator=HeatResidualEvaluator(),
                reference_generator=translation,
                source_candidate_id="heat_translation_generator",
            ),
        },
        {
            "case_name": "kdv_generator_family",
            "report": validate_symmetry_candidate(
                kdv,
                translation.to_dict(),
                residual_evaluator=KdVResidualEvaluator(),
                source_candidate_id="kdv_translation_generator_payload",
            ),
        },
        {
            "case_name": "heat_invariant_map_spec_payload",
            "report": validate_symmetry_candidate(
                heat,
                _translation_spec_payload(),
                residual_evaluator=HeatResidualEvaluator(),
                source_candidate_id="heat_uniform_translation_spec_payload",
            ),
        },
        {
            "case_name": "failed_wrong_span_generator",
            "report": validate_symmetry_candidate(
                heat,
                _translation_generator([0.0, 0.0, 1.0, 0.0]),
                residual_evaluator=HeatResidualEvaluator(),
                source_candidate_id="wrong_span_generator",
            ),
        },
    ]

    return {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": "symmetry_candidate_validation_example",
        "cases": cases,
        "extra_metrics": {
            "example_name": "symmetry_candidate_validation",
            "candidate_kinds": sorted({case["report"]["candidate_kind"] for case in cases}),
            "conclusions": [case["report"]["conclusion"] for case in cases],
            "interpretation": "configured_empirical_validation_not_mathematical_proof",
        },
    }


def main() -> None:
    print(json.dumps(run_symmetry_candidate_validation_example(), indent=2))


if __name__ == "__main__":
    main()
