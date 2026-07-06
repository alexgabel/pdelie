from __future__ import annotations

import json

from pdelie.data import generate_heat_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.reporting import summarize_generator_confidence
from pdelie.residuals import HeatResidualEvaluator
from pdelie.symmetry import FormulaGeneratorFamily, validate_symmetry_candidate
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import verify_translation_generator

_SUMMARY_SCHEMA_VERSION = "0.1"


def _formula_translation() -> FormulaGeneratorFamily:
    return FormulaGeneratorFamily(
        formula_generators=[
            {
                "name": "formula_translation",
                "components": {
                    "tau": {"node": "const", "value": 0.0},
                    "xi": {"node": "const", "value": 1.0},
                    "phi": {"node": "const", "value": 0.0},
                },
            }
        ],
    )


def run_generator_confidence_report_example() -> dict[str, object]:
    training = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=20001)
    heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=20002)
    evaluator = HeatResidualEvaluator()
    derivatives = compute_spectral_fd_derivatives(training)
    residual = evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, evaluator, epsilon=1e-4)
    verification = verify_translation_generator(heldout, generator, evaluator)

    strong_confidence = summarize_generator_confidence(
        residual=residual,
        generator=generator,
        verification=verification,
        thresholds={
            "residual_max_abs": 1e-3,
            "residual_rms": 1e-4,
            "verification_first_error": 1e-5,
            "verification_max_error": 1e-4,
        },
        extra_metrics={"case_name": "heat_direct_svd"},
    )
    partial_validation = validate_symmetry_candidate(
        training,
        _formula_translation(),
        residual_evaluator=evaluator,
        source_candidate_id="formula_translation_no_finite_transform",
    )
    qualified_confidence = summarize_generator_confidence(
        candidate_validation=partial_validation,
        extra_metrics={"case_name": "formula_candidate_partial_validation"},
    )

    return {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": "generator_confidence_report_example",
        "cases": [
            {"case_name": "heat_direct_svd", "confidence": strong_confidence},
            {
                "case_name": "formula_candidate_partial_validation",
                "confidence": qualified_confidence,
            },
        ],
        "extra_metrics": {
            "example_name": "generator_confidence_report",
            "confidence_labels": [
                strong_confidence["confidence_label"],
                qualified_confidence["confidence_label"],
            ],
            "interpretation": "categorical_empirical_evidence_not_scalar_score",
        },
    }


def main() -> None:
    print(json.dumps(run_generator_confidence_report_example(), indent=2))


if __name__ == "__main__":
    main()
