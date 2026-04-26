# V0.7 Scope Freeze

## Summary

`v0.7` is the first structured external-data ingestion release for `pdelie`.

Its purpose is:

> ingest external structured 1D uniform rectilinear PDE data into canonical `FieldBatch`, so the existing stable scalar Heat/Burgers symmetry and discovery stack can run on imported data rather than only internally generated synthetic fixtures.

`v0.7` is intentionally narrow.
It is not a broad dataset-adapter release.

---

## Stable Scope

Stable `v0.7` scope is limited to:

- `pdelie.data.from_numpy(...)`
- `pdelie.data.from_xarray(...)`
- strict conversion into canonical `FieldBatch`
- structured 1D uniform rectilinear trajectory data only
- scalar-variable stable slice only
- explicit dims, coords, metadata, mask, and provenance validation
- parity with the existing Heat/Burgers symmetry and discovery pipeline

Stable `v0.7` release definition:

`external structured arrays -> canonical FieldBatch -> existing PDELie pipeline`

---

## Exact Public API Contracts

Planned stable public APIs:

- `pdelie.data.from_numpy(values, *, dims, coords, var_name, metadata, mask=None, preprocess_log=None) -> FieldBatch`
- `pdelie.data.from_xarray(data_array, *, var_name=None, metadata, mask=None, preprocess_log=None) -> FieldBatch`

`from_xarray(...)` is frozen to `xarray.DataArray` only in `v0.7`.
`xarray.Dataset` support is out of scope for the stable slice.

Variable-name rules:

- `from_numpy(...)` always requires explicit `var_name`
- `from_xarray(...)` resolves `var_name` by:
  - explicit `var_name` argument first
  - otherwise the single `var` coordinate value when explicit `var` axis exists
  - otherwise `DataArray.name`
  - otherwise validation failure

---

## Accepted Layouts

Stable accepted source layouts are:

- `("time", "x")`
- `("batch", "time", "x")`
- `("time", "x", "var")`
- `("batch", "time", "x", "var")`

Frozen axis/layout rules:

- `time` is required
- `x` is required
- `var` may be omitted only for the scalar stable slice
- if `var` is omitted, the importer injects a trailing singleton `var` axis
- if `var` is present, its length must be exactly `1`
- no static / no-time layouts in stable `v0.7`
- no dim aliases in stable `v0.7`
- no `y` / `z` ingestion in stable `v0.7`

---

## Coordinate and Metadata Validation

Coordinate validation:

- `time` and `x` coordinates are required
- both must be 1D finite numeric arrays
- `time` must be strictly increasing, uniform, and length `>= 3`
- `x` must be strictly increasing, uniform, and length `>= 4`
- `x` uniformity uses the current `FieldBatch` spatial tolerance policy
- `time` uniformity is required because stable `v0.7` imports target the current trajectory / discovery pipeline
- no coordinate inference beyond extracting `time` / `x` from the provided inputs
- no normalization, sorting, or repair of malformed coordinates

Metadata requirements:

- the caller must supply the full required `FieldBatch` metadata mapping
- there is no stable metadata inference in `v0.7`
- required keys remain:
  - `boundary_conditions`
  - `grid_type`
  - `coordinate_system`
  - `grid_regularity`
  - `parameter_tags`
- stable `v0.7` imported fields must validate as:
  - `grid_type == "rectilinear"`
  - `grid_regularity == "uniform"`
  - `coordinate_system == "cartesian"`
  - `boundary_conditions["x"] == "periodic"`
- `parameter_tags` must be a mapping but may be empty
- `xarray` attrs are not used as stable metadata inference

---

## Mask / NaN Policy

Stable `v0.7` importers preserve missing-data signals rather than normalizing them.

Frozen rules:

- preserve both explicit masks and existing `NaN` / non-finite values
- do not normalize `NaN` values into masks
- do not normalize masks into `NaN` values
- if `mask` is provided and `var` is injected, inject the singleton `var` axis into the mask too
- `from_numpy(...)` accepts array-like `mask`
- `from_xarray(...)` accepts `xarray.DataArray` `mask` only
- mask must align with the pre-normalized input layout and the resulting post-injection shape

---

## Copy / Provenance Semantics

Stable importers always materialize owned canonical data.

Frozen copy rules:

- always materialize and copy imported values
- always copy coordinates
- always copy masks when present
- deep-copy `metadata`
- if `preprocess_log` is omitted, start from `[]`
- if `preprocess_log` is provided, deep-copy it and then append exactly one new entry

Frozen provenance rule:

- append exactly one provenance entry:
  - `operation = "from_numpy"` or `"from_xarray"`
  - `parameters` includes at least:
    - `source_layout`
    - `imported_shape`
    - `injected_var_axis`
    - `mask_provided`

No broader provenance schema is introduced in `v0.7 M0`.

---

## Optional `xarray` Dependency Policy

Stable dependency behavior:

- `from_numpy(...)` is core-only
- `from_xarray(...)` is a runtime-optional path
- `xarray` must be imported lazily inside the function / module path
- if `xarray` is unavailable, calling `from_xarray(...)` raises `ImportError` with an install message
- do not add an optional dependency extra in `v0.7 M0`
- the packaging extra name for `xarray` support will be finalized when `from_xarray(...)` is implemented
- `v0.7 M0` freezes only the runtime behavior and placeholder packaging note, not the final extra name

---

## Explicit Non-goals

Out of stable `v0.7` scope:

- no `xarray.Dataset` stable support
- no dim aliases
- no static-field ingestion
- no multidimensional ingestion
- no `y` / `z` ingestion
- no nonuniform-grid support
- no metadata inference layer
- no PDEBench-specific loader
- no The Well adapter
- no HDF5, netCDF, or Zarr stable loader
- no weak-form methods
- no operator methods
- no stable KdV promotion piggybacked into ingestion work
- no paper-specific experiment logic

---

## Milestones

Planned `v0.7` sequence:

- Milestone 0 — external ingestion contract freeze
- Milestone 1 — `from_numpy(...)`
- Milestone 2 — `from_xarray(...)`
- Milestone 3 — parity tests and compact `v0.7` release gate
