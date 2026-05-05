# End-to-End Dataset to Downstream Workflow

This is a V0.29 recipe page over existing public APIs; it adds no runtime surface.

This recipe is the complete data-readiness path for users starting from an `xarray.Dataset`.

```text
xarray.Dataset
-> Dataset readiness
-> FieldBatch conversion
-> FieldBatch readiness and residual preflight
-> generator confidence
-> downstream discovery workflow summary
```

## Minimal Recipe

1. Build or receive an `xarray.Dataset` with one scalar data variable such as `u`.
2. Run `summarize_xarray_dataset_readiness(dataset, data_var="u", metadata=..., expected_equation=...)`.
3. Convert with `from_xarray_dataset(dataset, data_var="u", metadata=...)`.
4. Run `summarize_field_batch_readiness(field, residual_evaluator=..., expected_equation=...)`.
5. Fit and verify the stable translation generator only inside the supported scalar 1D periodic scope.
6. Summarize confidence with `summarize_generator_confidence(...)`.
7. Summarize bridge arrays and backend-neutral discovery results.
8. Combine evidence with `summarize_downstream_discovery_workflow(...)`.

## Tutorial Page

The rendered notebook `12_dataset_to_downstream_workflow.ipynb` shows this recipe with saved outputs and a compact plot. It uses generated Heat data converted into a Dataset so that the example stays self-contained and reproducible.

## Boundaries

This workflow does not add file loaders, Zarr/NetCDF readers, PDEBench/The Well adapters, metadata inference, resampling, multidimensional data, nonuniform grids, or new PDE support.
