from __future__ import annotations

import json
from copy import deepcopy
import importlib

from pdelie.data import from_xarray_dataset, generate_heat_1d_field_batch
from pdelie.reporting import summarize_field_batch_readiness, summarize_xarray_dataset_readiness
from pdelie.residuals import HeatResidualEvaluator


def _require_xarray_for_example():
    try:
        return importlib.import_module("xarray")
    except ModuleNotFoundError as exc:
        raise ImportError(
            "xarray is required for pdelie.examples.data_ecosystem_feasibility; install pdelie[xarray]."
        ) from exc


def run_data_ecosystem_feasibility_example() -> dict[str, object]:
    xr = _require_xarray_for_example()
    source = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=32, seed=28028)
    metadata = deepcopy(source.metadata)
    metadata["parameter_tags"]["equation"] = "heat_1d"
    dataset = xr.Dataset(
        {"u": (source.dims, source.values)},
        coords={"time": source.coords["time"], "x": source.coords["x"]},
        attrs={"source": "pdelie_example", "note": "attrs are reported, not canonical metadata"},
    )

    dataset_readiness = summarize_xarray_dataset_readiness(
        dataset,
        data_var="u",
        metadata=metadata,
        expected_equation="heat_1d",
    )
    imported = from_xarray_dataset(
        dataset,
        data_var="u",
        var_name="u",
        metadata=metadata,
        preprocess_log=[{"operation": "example_dataset_source"}],
    )
    field_readiness = summarize_field_batch_readiness(
        imported,
        residual_evaluator=HeatResidualEvaluator(),
        expected_equation="heat_1d",
    )

    return {
        "summary_schema_version": "0.1",
        "summary_type": "data_ecosystem_feasibility_example",
        "release_decision": "xarray_dataset_scalar_slice_supported_file_loaders_deferred",
        "dataset_readiness": dataset_readiness,
        "field_readiness": field_readiness,
        "imported_field": {
            "dims": list(imported.dims),
            "shape": list(imported.values.shape),
            "var_names": list(imported.var_names),
            "preprocess_operations": [entry["operation"] for entry in imported.preprocess_log],
        },
        "deferred_scope": {
            "file_loaders": False,
            "broad_adapter_registry": False,
            "metadata_inference_engine": False,
            "multidimensional_or_nonuniform_stable_api": False,
        },
    }


def main() -> None:
    print(json.dumps(run_data_ecosystem_feasibility_example(), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
