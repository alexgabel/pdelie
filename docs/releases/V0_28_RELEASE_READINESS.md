# V0.28.0 Release Readiness

## Decision

`v0.28.0` is ready as a Git-tag-only release.

Release conclusion:

```text
xarray_dataset_scalar_slice_supported_file_loaders_deferred
```

## Package Metadata

- package version: `0.28.0`
- git tag: `v0.28.0`
- PyPI/TestPyPI: deferred until `v1.0` or later

Do not publish to TestPyPI or PyPI for `v0.28.0`.

## Public Surface

Added submodule-only APIs:

- `pdelie.data.from_xarray_dataset(...)`
- `pdelie.reporting.summarize_xarray_dataset_readiness(...)`
- `pdelie.examples.run_data_ecosystem_feasibility_example(...)`

No root exports were added.

## Deferred Scope Confirmed

- no file loaders
- no NetCDF/Zarr readers
- no PDEBench/The Well adapters
- no broad adapter registry
- no metadata inference engine
- no resampling API
- no multidimensional or nonuniform stable API
- no train/test or leakage policy
- no KS runtime promotion

## Validation Checklist

Expected release validation:

```bash
python -m pytest tests/test_v0_28_release_gate.py
python -m pytest
python scripts/check_notebooks.py
python -m build --sdist --wheel
python -m pdelie.examples.data_ecosystem_feasibility
git diff --check
```
