from __future__ import annotations

import json

import numpy as np

from pdelie.data import generate_heat_1d_field_batch, generate_kdv_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.invariants import build_uniform_translation_orbit_batch
from pdelie.reporting import summarize_residual_batch
from pdelie.residuals import HeatResidualEvaluator, KdVResidualEvaluator

_SUMMARY_SCHEMA_VERSION = "0.1"
_DOMAIN_LENGTH = 2.0 * np.pi
_SHIFTS = (0.0, _DOMAIN_LENGTH / 32.0, _DOMAIN_LENGTH / 8.0, _DOMAIN_LENGTH / 8.0, _DOMAIN_LENGTH)


def _heat_case() -> dict[str, object]:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=9, num_points=32, seed=15011)
    result = build_uniform_translation_orbit_batch(
        field,
        shifts=_SHIFTS,
        source_field_id="heat_seed_15011",
    )
    residual = HeatResidualEvaluator().evaluate(
        result.field,
        compute_spectral_fd_derivatives(result.field),
    )
    return {
        "case_name": "heat",
        "equation": "heat_1d",
        "source_shape": list(field.values.shape),
        "orbit_shape": list(result.field.values.shape),
        "orbit_report": result.report,
        "residual": summarize_residual_batch(residual),
    }


def _kdv_case() -> dict[str, object]:
    field = generate_kdv_1d_field_batch(batch_size=2, num_times=9, num_points=32, num_modes=1, seed=15012)
    result = build_uniform_translation_orbit_batch(
        field,
        shifts=_SHIFTS,
        source_field_id="kdv_seed_15012",
    )
    residual = KdVResidualEvaluator().evaluate(
        result.field,
        compute_spectral_fd_derivatives(result.field, max_spatial_order=3),
    )
    return {
        "case_name": "kdv",
        "equation": "kdv_normalized",
        "source_shape": list(field.values.shape),
        "orbit_shape": list(result.field.values.shape),
        "orbit_report": result.report,
        "residual": summarize_residual_batch(residual),
    }


def run_translation_orbit_batch_example() -> dict[str, object]:
    return {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": "translation_orbit_batch_example",
        "cases": [_heat_case(), _kdv_case()],
        "extra_metrics": {
            "example_name": "translation_orbit_batch",
            "shifts": list(_SHIFTS),
            "duplicate_shifts_preserved": True,
            "ordering": "shift_major",
        },
    }


def main() -> None:
    print(json.dumps(run_translation_orbit_batch_example(), indent=2))


if __name__ == "__main__":
    main()
