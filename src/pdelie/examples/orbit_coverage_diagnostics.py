from __future__ import annotations

import json

import numpy as np

from pdelie.data import generate_heat_1d_field_batch, generate_kdv_1d_field_batch
from pdelie.invariants import compute_periodic_window_coverage, diagnose_uniform_translation_consistency
from pdelie.residuals import HeatResidualEvaluator, KdVResidualEvaluator

_SUMMARY_SCHEMA_VERSION = "0.1"
_DOMAIN_LENGTH = 2.0 * np.pi
_GRID_POINTS = 64
_COVERAGE_SHIFTS = (0.0, _DOMAIN_LENGTH / 4.0, _DOMAIN_LENGTH / 2.0, 3.0 * _DOMAIN_LENGTH / 4.0)
_TRANSFORM_SHIFTS = (0.0, _DOMAIN_LENGTH / _GRID_POINTS, _DOMAIN_LENGTH / 8.0, -_DOMAIN_LENGTH / 8.0, _DOMAIN_LENGTH)


def run_orbit_coverage_diagnostics_example() -> dict[str, object]:
    x = np.linspace(0.0, _DOMAIN_LENGTH, _GRID_POINTS, endpoint=False, dtype=float)
    heat = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=_GRID_POINTS, seed=1301)
    kdv = generate_kdv_1d_field_batch(batch_size=2, num_times=17, num_points=_GRID_POINTS, seed=1302)

    return {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": "orbit_coverage_diagnostics_example",
        "coverage_cases": [
            compute_periodic_window_coverage(
                x=x,
                windows=[{"start": 0.0, "width": _DOMAIN_LENGTH / 8.0}],
                shifts=_COVERAGE_SHIFTS,
                domain_length=_DOMAIN_LENGTH,
            ),
            compute_periodic_window_coverage(
                x=x,
                windows=[{"start": 0.0, "width": _DOMAIN_LENGTH / 4.0}],
                shifts=_COVERAGE_SHIFTS,
                domain_length=_DOMAIN_LENGTH,
            ),
        ],
        "transform_consistency_cases": [
            diagnose_uniform_translation_consistency(
                heat,
                shifts=_TRANSFORM_SHIFTS,
                residual_evaluator=HeatResidualEvaluator(),
            ),
            diagnose_uniform_translation_consistency(
                kdv,
                shifts=_TRANSFORM_SHIFTS,
                residual_evaluator=KdVResidualEvaluator(),
            ),
        ],
        "extra_metrics": {
            "example_name": "orbit_coverage_diagnostics",
            "coverage_fixture": "periodic_64_point_grid",
            "transform_fixtures": ["heat_1d", "kdv_normalized"],
        },
    }


def main() -> None:
    print(json.dumps(run_orbit_coverage_diagnostics_example(), indent=2))


if __name__ == "__main__":
    main()
