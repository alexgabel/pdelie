# PDELie — Execution Plan (V0.7)

## Current Release Status

**V0.7 release complete**

This file is the execution record for the completed `v0.7` release series.

It should contain:

- a short closeout record for the completed `v0.6` release
- the completed `v0.7` milestone sequence
- milestone-specific rules and gates

It should not redefine package contracts or roadmap commitments. Those belong in:

- `docs/specs/SPEC.md`
- `docs/specs/CONTRACTS_AND_DEFAULTS.md`
- `docs/specs/API_STABILITY.md`
- `docs/planning/ROADMAP.md`
- `docs/planning/V0_7_SCOPE.md`

`API_STABILITY.md` should not change during `v0.7 M0`, because the importer APIs are not implemented yet.

---

## V0.6 Closeout

`v0.6` is complete as the symmetry-guided PDE discovery utilities release.

Completed outcome:

- discovery recovery metrics
- one thin PySINDy discovery adapter
- one translation-canonical discovery-input builder
- simple robustness utilities
- one compact `v0.6` release gate

`v0.7` begins from that frozen Heat/Burgers discovery-utility surface.

This release series is structured-ingestion first.
It does not broaden the stable numerics regime or the current scalar periodic discovery stack.

---

## Milestone 0 — External Ingestion Contract Freeze

**Status:** Complete

### Goal

Freeze the exact `v0.7` importer contracts before writing runtime ingestion code.

### Frozen Decisions

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

Stable `v0.7` importers preserve missing-data signals rather than normalizing them.

Frozen rules:

- preserve both explicit masks and existing `NaN` / non-finite values
- do not normalize `NaN` values into masks
- do not normalize masks into `NaN` values
- if `mask` is provided and `var` is injected, inject the singleton `var` axis into the mask too
- `from_numpy(...)` accepts array-like `mask`
- `from_xarray(...)` accepts `xarray.DataArray` `mask` only
- mask must align with the pre-normalized input layout and the resulting post-injection shape

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

Stable dependency behavior:

- `from_numpy(...)` is core-only
- `from_xarray(...)` is a runtime-optional path
- `xarray` must be imported lazily inside the function / module path
- if `xarray` is unavailable, calling `from_xarray(...)` raises `ImportError` with an install message
- do not add an optional dependency extra in `v0.7 M0`
- the packaging extra name for `xarray` support will be finalized when `from_xarray(...)` is implemented
- `v0.7 M0` freezes only the runtime behavior and placeholder packaging note, not the final extra name

### Acceptance Criteria

M0 is complete only if:

- `ROADMAP.md`, `PLAN.md`, and `V0_7_SCOPE.md` are internally consistent
- `v0.6` is consistently described as completed
- `v0.7` is consistently described as the next committed release
- the importer contract bullets are identical between `PLAN.md` and `V0_7_SCOPE.md`
- `API_STABILITY.md` remains unchanged during M0

---

## Milestone 1 — `from_numpy(...)`

**Status:** Complete

### Goal

Implement `from_numpy(...)` exactly as frozen in M0.

### Completed Outcome

- added `pdelie.data.from_numpy(...)`
- accepted only the four frozen scalar 1D structured layouts
- canonicalized output to `("batch", "time", "x", "var")`
- preserved explicit `NaN` values and optional masks without normalization
- deep-copied values, coordinates, metadata, masks, and preprocess provenance
- appended one deterministic `from_numpy` provenance entry

---

## Milestone 2 — `from_xarray(...)`

**Status:** Complete

### Goal

Implement `from_xarray(...)` exactly as frozen in M0, including lazy optional-dependency behavior.

### Completed Outcome

- added `pdelie.data.from_xarray(...)`
- accepted only the four frozen scalar 1D `xarray.DataArray` layouts
- canonicalized output to `("batch", "time", "x", "var")`
- preserved explicit `NaN` values and optional `xarray.DataArray` masks without normalization
- deep-copied values, coordinates, metadata, masks, and preprocess provenance
- finalized the optional dependency extra name as `xarray`

---

## Milestone 3 — Parity Tests and V0.7 Release Gate

**Status:** Complete

### Goal

Prove that imported structured data behaves like the current native Heat/Burgers `FieldBatch` path and add a compact `v0.7` release gate.

### Completed Outcome

- added native-vs-imported parity coverage for `from_numpy(...)` and `from_xarray(...)`
- proved parity through the current derivative, residual, symmetry-fit, verification, and discovery-bridge layers
- added a compact `v0_7-release-gate` test module and dedicated CI job
- kept the downstream fit assertion structural-only and avoided any new public API

---

## V0.7 Closeout

`v0.7` is complete as the structured external-data ingestion release.

Completed release outcome:

- strict `pdelie.data.from_numpy(...)` ingestion into canonical `FieldBatch`
- strict runtime-optional `pdelie.data.from_xarray(...)` ingestion for `xarray.DataArray`
- parity protection proving imported Heat/Burgers-like data behaves like the native `FieldBatch` path
- a compact `v0.7` release gate and dedicated CI visibility job

This release extends the library into structured external ingestion without broadening the stable numerics regime, adding file loaders, or changing the existing Heat/Burgers symmetry and discovery contracts.

---

## Executed Milestone Sequence

Locked sequence:

Milestone 0 -> external ingestion contract freeze  
Milestone 1 -> `from_numpy(...)`  
Milestone 2 -> `from_xarray(...)`  
Milestone 3 -> parity tests and compact `v0.7` release gate

Hard sequencing rules:

- do not turn `v0.7` into a broad dataset-adapter release
- do not add multidimensional stable ingestion
- do not add metadata inference as stable behavior
- do not broaden ingestion work into weak-form or operator-method expansion
- do not use `v0.7` to promote KdV

---

## Rules

- DO NOT update `docs/specs/API_STABILITY.md` until importer APIs actually land
- DO NOT add `xarray.Dataset` stable support in `v0.7`
- DO NOT add dim aliases in `v0.7`
- DO NOT add static-field ingestion in `v0.7`
- DO NOT add multidimensional stable ingestion in `v0.7`
- DO NOT add nonuniform-grid support in `v0.7`
- DO NOT add broad metadata inference
- DO NOT add weak-form methods
- DO NOT add operator methods
- DO NOT add paper-specific experiment logic

---

## Status

- `v0.6`: COMPLETE
- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
