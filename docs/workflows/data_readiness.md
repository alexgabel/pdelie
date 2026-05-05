# Data Readiness Workflow

This is a V0.29 recipe page over existing public APIs; it adds no runtime surface.

Use this path when you have PDE time-series data and want to know whether it can enter the stable PDELie stack.

```text
xarray.Dataset or array-like data
-> readiness report
-> explicit scalar FieldBatch conversion
-> optional residual preflight
```

## Recipe

1. Inspect the source container before conversion.
2. Select one scalar data variable explicitly when the input is an `xarray.Dataset`.
3. Provide canonical metadata yourself; Dataset attrs are report metadata, not trusted PDE identity.
4. Convert to `FieldBatch` only after the readiness report is acceptable.
5. Run `summarize_field_batch_readiness(...)` with the residual evaluator you intend to use.

## Primary APIs

- `pdelie.reporting.summarize_xarray_dataset_readiness(...)`
- `pdelie.data.from_xarray_dataset(...)`
- `pdelie.data.from_numpy(...)`
- `pdelie.data.from_xarray(...)`
- `pdelie.reporting.summarize_field_batch_readiness(...)`

## Defensible Claim

A `ready` report means the configured checks passed for the current scalar 1D uniform periodic contract. It does not infer PDE identity, resample nonuniform grids, load files, or make broad external-data claims.

## Next Step

Continue to `end_to_end_dataset_to_downstream.md` for a full recipe that carries a Dataset through residual preflight, generator confidence, and downstream discovery summaries.
