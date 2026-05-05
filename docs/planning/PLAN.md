# PDELie - Execution Plan (V0.28)

**Status:** COMPLETE

**V0.28 is complete as the narrow xarray Dataset ingestion and data-ecosystem feasibility release**

This file is the completed execution record for the `v0.28` release series.

## Release Theme

`v0.28` adds one explicit scalar `xarray.Dataset` ingestion path and a Dataset readiness report without promoting file loaders, broad adapter machinery, metadata inference, resampling, multidimensional grids, or root exports.

Decision label:

```text
xarray_dataset_scalar_slice_supported_file_loaders_deferred
```

Stable path:

```text
xarray.Dataset
-> dataset readiness report
-> explicit scalar data variable + explicit metadata
-> canonical scalar 1D periodic FieldBatch
-> existing readiness / residual / confidence workflows
```

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

Authoritative scope:

- `docs/planning/V0_28_SCOPE.md`

## Milestone 0 - Scope Freeze

Closeout:

- added `docs/planning/V0_28_SCOPE.md`
- reset `PLAN.md` as the active `v0.28` execution record
- updated `ROADMAP.md` to record `v0.28` as the current completed release
- explicitly deferred file loaders, broad adapters, metadata inference engines, resampling, multidimensional/nonuniform support, and root exports

## Milestone 1 - Semantics Freeze

Frozen semantics:

- `from_xarray_dataset(...)` accepts `xarray.Dataset` only
- conversion imports exactly one scalar data variable
- omitted `data_var` auto-selects only when exactly one compatible numeric non-mask variable exists
- `mask_var`, when supplied, must match the selected data variable dims and shape
- conversion delegates to existing `from_xarray(...)`
- metadata is required for conversion and Dataset attrs are report-only

## Milestone 2 - Dataset Adapter

Implemented:

- `pdelie.data.from_xarray_dataset(...)`
- submodule-only export from `pdelie.data`
- parity coverage against direct `from_xarray(dataset[data_var], ...)`
- provenance entry `from_xarray_dataset` before the delegated `from_xarray` entry

## Milestone 3 - Dataset Readiness Reporting

Implemented:

- `pdelie.reporting.summarize_xarray_dataset_readiness(...)`
- strict JSON-compatible `summary_type = "xarray_dataset_readiness"` reports
- selected/candidate variable diagnostics
- coordinate, mask, metadata, expected-equation, and conversion-preflight diagnostics
- conservative report-only metadata suggestions

## Milestone 4 - Example and Docs

Implemented:

- `pdelie.examples.run_data_ecosystem_feasibility_example(...)`
- `python -m pdelie.examples.data_ecosystem_feasibility`
- README, docs index, changelog, API stability, spec, publishing, roadmap, and release-readiness updates

## Milestone 5 - API / Public-Surface Audit

Confirmed:

- new APIs are submodule-only
- root `pdelie` remains unchanged
- no `load_field_batch`, NetCDF/Zarr loader, PDEBench/The Well adapter, adapter registry, metadata inference engine, resampling API, multidimensional/nonuniform API, train/test policy, KS runtime API, neural/callable API, or operator API landed

## Milestone 6 - Release Gate and Readiness

Implemented:

- `tests/test_v0_28_release_gate.py`
- CI `v0_28-release-gate`
- package metadata bump to `0.28.0`
- Git-tag-only release-readiness docs; PyPI/TestPyPI remain deferred until `v1.0` or later
