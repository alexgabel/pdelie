from __future__ import annotations

import json
from copy import deepcopy

from pdelie import FieldBatch
from pdelie.data import from_numpy, generate_heat_1d_field_batch
from pdelie.reporting import summarize_field_batch_readiness
from pdelie.residuals import HeatResidualEvaluator, KdVResidualEvaluator


def _metadata(*, equation: str | None = None) -> dict[str, object]:
    parameter_tags: dict[str, object] = {"nu": 0.1}
    if equation is not None:
        parameter_tags["equation"] = equation
    return {
        "boundary_conditions": {"x": "periodic"},
        "coordinate_system": "cartesian",
        "grid_regularity": "uniform",
        "grid_type": "rectilinear",
        "parameter_tags": parameter_tags,
    }


def _copy_field_with_metadata(field: FieldBatch, metadata: dict[str, object]) -> FieldBatch:
    copied = FieldBatch(
        values=field.values.copy(),
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=deepcopy(field.metadata),
        preprocess_log=deepcopy(field.preprocess_log),
        mask=None if field.mask is None else field.mask.copy(),
    )
    copied.metadata = deepcopy(metadata)
    return copied


def run_external_data_readiness_example() -> dict[str, object]:
    source = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=32, seed=21021)
    imported = from_numpy(
        source.values,
        dims=source.dims,
        coords=source.coords,
        var_name="u",
        metadata=_metadata(equation="heat_1d"),
        preprocess_log=[{"operation": "example_external_array"}],
    )

    incomplete_metadata = deepcopy(imported.metadata)
    incomplete_metadata.pop("parameter_tags", None)
    metadata_incomplete = _copy_field_with_metadata(imported, incomplete_metadata)

    mismatch_ready = summarize_field_batch_readiness(
        imported,
        residual_evaluator=KdVResidualEvaluator(),
        expected_equation="heat_1d",
    )
    ready = summarize_field_batch_readiness(
        imported,
        residual_evaluator=HeatResidualEvaluator(),
    )
    needs_metadata = summarize_field_batch_readiness(metadata_incomplete)

    return {
        "summary_schema_version": "0.1",
        "summary_type": "external_data_readiness_example",
        "cases": [
            {"case_name": "from_numpy_heat_ready", "readiness": ready},
            {"case_name": "metadata_incomplete", "readiness": needs_metadata},
            {"case_name": "residual_evaluator_mismatch", "readiness": mismatch_ready},
        ],
        "extra_metrics": {
            "example_name": "external_data_readiness",
            "source": "from_numpy",
            "readiness_labels": [
                ready["readiness_label"],
                needs_metadata["readiness_label"],
                mismatch_ready["readiness_label"],
            ],
        },
    }


def main() -> None:
    print(json.dumps(run_external_data_readiness_example(), indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
