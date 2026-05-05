# V0.28.0 Scope - Narrow xarray Dataset Ingestion and Data Ecosystem Feasibility

**Status:** COMPLETE

## Summary

`v0.28.0` is a narrow data-ecosystem feasibility release.

Stable path:

```text
xarray.Dataset
-> dataset readiness report
-> explicit scalar data variable + explicit metadata
-> canonical scalar 1D periodic FieldBatch
-> existing FieldBatch readiness / residual preflight / confidence workflows
```

Release conclusion:

```text
xarray_dataset_scalar_slice_supported_file_loaders_deferred
```

## Public API

Submodule-only additions:

- `pdelie.data.from_xarray_dataset(...)`
- `pdelie.reporting.summarize_xarray_dataset_readiness(...)`
- `pdelie.examples.run_data_ecosystem_feasibility_example(...)`
- `python -m pdelie.examples.data_ecosystem_feasibility`

No root `pdelie` exports are added.

## Frozen Semantics

- `from_xarray_dataset(...)` accepts only `xarray.Dataset`.
- `xarray.DataArray` input remains handled by existing `from_xarray(...)`.
- exactly one scalar data variable is imported.
- omitted `data_var` is allowed only when exactly one compatible numeric non-mask variable exists.
- `mask_var`, when supplied, must match selected data-variable dims and shape.
- conversion delegates to existing `from_xarray(...)`.
- explicit metadata remains required for conversion.
- Dataset attrs are report metadata only and are never promoted into canonical `FieldBatch.metadata`.
- Dataset readiness reports are strict JSON-compatible runtime reports.
- metadata suggestions are conservative and report-only.

## Explicit Non-Goals

- no file loaders
- no NetCDF or Zarr readers
- no PDEBench or The Well adapters
- no broad adapter registry
- no implicit metadata inference or PDE identity inference
- no resampling API
- no multidimensional, multivariable, or nonuniform stable support
- no train/test policy or leakage prevention
- no KS runtime promotion
- no neural/callable/operator APIs
- no root export expansion

## Milestone Closeout

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE
