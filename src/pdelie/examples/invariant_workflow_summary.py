from __future__ import annotations

import json

import numpy as np

from pdelie.data import generate_heat_1d_field_batch, generate_kdv_1d_field_batch, split_batch_train_heldout
from pdelie.invariants import summarize_uniform_translation_orbit
from pdelie.reporting import summarize_invariant_workflow
from pdelie.residuals import HeatResidualEvaluator, KdVResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import verify_translation_generator

_SUMMARY_SCHEMA_VERSION = "0.1"
_DOMAIN_LENGTH = 2.0 * np.pi
_GRID_POINTS = 64
_SHIFTS = (0.0, _DOMAIN_LENGTH / _GRID_POINTS, _DOMAIN_LENGTH / 8.0, -_DOMAIN_LENGTH / 8.0, _DOMAIN_LENGTH)
_WINDOWS = ({"start": 0.0, "width": _DOMAIN_LENGTH / 4.0},)


def _heat_workflow() -> dict[str, object]:
    training = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=_GRID_POINTS, seed=1401)
    heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=_GRID_POINTS, seed=1402)
    evaluator = HeatResidualEvaluator()
    generator = fit_translation_generator(training, evaluator, epsilon=1e-4)
    verification = verify_translation_generator(heldout, generator, evaluator)
    orbit = summarize_uniform_translation_orbit(
        training,
        shifts=_SHIFTS,
        windows=_WINDOWS,
        residual_evaluator=evaluator,
        source_field_id="heat_training_seed_1401",
    )
    return summarize_invariant_workflow(
        orbit=orbit,
        coverage=orbit["coverage"],
        consistency=orbit["consistency"],
        generator=generator,
        verification=verification,
        extra_metrics={"case_name": "heat", "equation": "heat_1d"},
    )


def _kdv_workflow() -> dict[str, object]:
    field = generate_kdv_1d_field_batch(seed=9001, batch_size=5)
    training, heldout = split_batch_train_heldout(field, train_size=2, seed=9002)
    evaluator = KdVResidualEvaluator()
    generator = fit_translation_generator(training, evaluator, epsilon=1e-4)
    verification = verify_translation_generator(heldout, generator, evaluator)
    orbit = summarize_uniform_translation_orbit(
        training,
        shifts=_SHIFTS,
        windows=_WINDOWS,
        residual_evaluator=evaluator,
        source_field_id="kdv_training_seed_9001_split_9002",
    )
    return summarize_invariant_workflow(
        orbit=orbit,
        coverage=orbit["coverage"],
        consistency=orbit["consistency"],
        generator=generator,
        verification=verification,
        extra_metrics={"case_name": "kdv", "equation": "kdv_normalized"},
    )


def run_invariant_workflow_summary_example() -> dict[str, object]:
    return {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": "invariant_workflow_summary_example",
        "workflows": [_heat_workflow(), _kdv_workflow()],
        "extra_metrics": {
            "example_name": "invariant_workflow_summary",
            "shifts": list(_SHIFTS),
            "windows": list(_WINDOWS),
        },
    }


def main() -> None:
    print(json.dumps(run_invariant_workflow_summary_example(), indent=2))


if __name__ == "__main__":
    main()
