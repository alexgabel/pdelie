# V0.7 Release Readiness

## Release Target

- package version: `0.7.0`
- git tag: `v0.7.0`

## Done

- the canonical stable object set from `v0.6` remains in place, including `InvariantMapSpec`
- Heat remains supported under the existing stable path
- Burgers remains supported under the existing stable path
- the stable derivative backend remains `spectral_fd`
- analytic Heat and Burgers residual evaluators remain in place
- the polynomial spatial-translation fitting path remains the stable PDE fitting slice
- the finite-transform verification path remains the stable verification slice
- the runtime-only discovery utilities from `v0.6` remain in place unchanged in scope
- M0 is complete:
  - the exact `v0.7` structured-ingestion contract was frozen before runtime implementation
  - accepted layouts, coordinate rules, metadata requirements, mask semantics, and provenance behavior were documented explicitly
- M1 is complete:
  - `pdelie.data.from_numpy(...)` is implemented for the frozen scalar 1D uniform-rectilinear structured layouts
  - imported arrays are canonicalized to `("batch", "time", "x", "var")`
  - explicit `NaN` values and optional masks are preserved without normalization
- M2 is complete:
  - `pdelie.data.from_xarray(...)` is implemented for the frozen `xarray.DataArray`-only slice
  - lazy optional dependency behavior is in place
  - the optional dependency extra name is finalized as `xarray`
- M3 is complete:
  - native-vs-imported parity coverage is implemented for `from_numpy(...)` and `from_xarray(...)`
  - imported Heat/Burgers-like data matches native `FieldBatch` behavior through the current derivative, residual, symmetry-fit, verification, and discovery-bridge layers
  - the compact `v0_7-release-gate` test module and CI visibility job are implemented
- the full test suite passes from the repo root
- package metadata, changelog, README, roadmap, execution plan, and release-readiness docs can be aligned with the implemented `v0.7` surface

## Explicitly Deferred

- `xarray.Dataset` support
- dim aliases
- static-field ingestion
- multidimensional external-data ingestion
- nonuniform-grid support
- metadata inference
- PDEBench-specific loaders
- The Well adapters
- HDF5, netCDF, or Zarr stable loaders
- weak-form methods
- operator methods
- stable KdV promotion piggybacked into ingestion work
- paper-specific experiment logic

## Final Release View

The current repository is ready for the final `0.7.0` release for the frozen `v0.7` structured external-data ingestion slice, subject to release-path checks passing on the release branch and CI passing on the release PR.

There are no known scientific-scope blockers inside the current `v0.7` slice.

## Packaging And Public API Notes

- `pdelie.data.from_numpy` is a stable runtime public API in `v0.7`
- `pdelie.data.from_xarray` is a stable runtime public API in `v0.7` when the optional `xarray` dependency is installed
- the importers are exposed under `pdelie.data`, not root `pdelie`
- `pdelie[xarray]` is the finalized optional extra for the `xarray.DataArray` ingestion path
- the runtime discovery utilities from `v0.6` remain runtime-level APIs rather than new canonical objects
- the runtime downstream bridge remains optional via `pdelie[downstream]`
- `pdelie.viz` remains optional via `pdelie[viz]`
- SymPy support remains optional at runtime and is not part of the core install
- KdV remains tests-first feasibility only and does not add a stable runtime API in `v0.7`
- the `v0_4-release-gate`, `v0_5-release-gate`, `v0_6-release-gate`, and `v0_7-release-gate` CI jobs are explicit visibility checks; if they should block merges, repository branch-protection settings must be updated separately

## Final Tag Checklist

Before tagging `v0.7.0`:

- run `python -m pytest` from the repo root
- run `python -m build --sdist --wheel`
- install the built wheel into a clean environment and verify stable imports
- run `python -m pdelie.examples.heat_vertical_slice`
- confirm GitHub Actions jobs `v0_4-release-gate`, `v0_5-release-gate`, `v0_6-release-gate`, `v0_7-release-gate`, `editable-tests`, and `package-smoke` pass on the release PR commit
- merge the release PR into `main`
- tag the merged `main` commit as `v0.7.0`
