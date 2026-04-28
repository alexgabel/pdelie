# PDELie - Execution Plan (V0.9)

## Current Release Status

**V0.9 committed; Milestone 4 complete**

This file is the active execution record for the `v0.9` release series.

`v0.9` promotes the existing tests-first KdV feasibility slice into a narrow stable normalized periodic short-horizon KdV strong path.

Stable release definition:

`canonical scalar 1D uniform periodic FieldBatch -> spectral_fd with u_xxx -> normalized KdV residual evaluator -> translation fit/verification`

This file should not redefine package contracts.
Contracts and stable behavior belong in:

- `docs/specs/SPEC.md`
- `docs/specs/CONTRACTS_AND_DEFAULTS.md`
- `docs/specs/API_STABILITY.md`
- `docs/planning/ROADMAP.md`
- `docs/planning/V0_9_SCOPE.md`

`API_STABILITY.md` remains unchanged in M0.
It is updated in the milestone where each public runtime API actually lands.

---

## V0.8 Closeout

`v0.8` is complete as the window-indexed weak residual report release.

Completed outcome:

- stable `pdelie.residuals.evaluate_weak_heat_residual(...)`
- stable `pdelie.residuals.evaluate_weak_burgers_residual(...)`
- deterministic window-indexed weak residual reports for scalar 1D Heat/Burgers
- fallback-backed representative robustness comparisons against the existing strong path
- compact `v0_8-release-gate`
- explicit deferral of weak derivatives, weak `ResidualBatch` integration, and stable KdV runtime promotion

`v0.9` begins from the frozen `v0.8` surface.
It does not reopen weak-form numerics.

---

## Milestone 0 - KdV Strong-Path Scope Freeze

**Status:** COMPLETE

### Goal

Promote `v0.9` to the next committed release target, create `V0_9_SCOPE.md`, reset `PLAN.md`, and keep `API_STABILITY.md` unchanged.

### Completed Outcome

- promoted `v0.9` to committed KdV strong-path scope in `ROADMAP.md`
- created `docs/planning/V0_9_SCOPE.md`
- reset `docs/planning/PLAN.md` as the active `v0.9` execution record
- froze exact planned public API signatures
- froze derivative order behavior for `max_spatial_order`
- froze KdV generator validation and release-guaranteed parameter regime
- froze KdV residual evaluator semantics
- froze KdV vertical-slice fixture and release-gate thresholds
- left `docs/specs/API_STABILITY.md` unchanged

### Acceptance Criteria

M0 is complete only if:

- `ROADMAP.md`, `PLAN.md`, and `V0_9_SCOPE.md` are internally consistent
- `v0.8` is consistently described as completed
- `v0.9` is consistently described as the next committed release
- `v0.9` is described as stable normalized periodic short-horizon KdV, not general KdV support
- `API_STABILITY.md` remains unchanged during M0
- no runtime code, tests, or package metadata are edited

---

## Milestone 1 - Spectral `u_xxx`

**Status:** COMPLETE

### Goal

Extend the existing `spectral_fd` derivative backend through third spatial order without breaking default Heat/Burgers behavior.

### Completed Outcome

- implemented `compute_spectral_fd_derivatives(field, *, max_spatial_order: int = 2)`
- froze derivative key behavior:
  - `1` -> `u_t`, `u_x`
  - `2` -> `u_t`, `u_x`, `u_xx`
  - `3` -> `u_t`, `u_x`, `u_xx`, `u_xxx`
- accepted Python integer and NumPy integer scalar orders while rejecting bools and unsupported values
- preserved default `max_spatial_order=2` derivative arrays, derivative-key set, config, and diagnostics
- kept `spatial_max_order` out of the default config and recorded it only for non-default orders
- computed `u_xxx` using the same spectral wavenumber convention as `u_x` and `u_xx`
- added exact Fourier `u_xxx` accuracy tests
- added default-regression tests proving existing default derivative arrays and metadata remain behavior-compatible
- updated `API_STABILITY.md` for the derivative API change

### Acceptance Criteria

- Heat/Burgers derivative tests pass under default `max_spatial_order=2`
- `u_xxx` matches exact Fourier fixtures within frozen tolerance
- invalid derivative orders raise typed errors
- `API_STABILITY.md` documents the landed derivative API change

---

## Milestone 2 - KdV Generator

**Status:** COMPLETE

### Goal

Promote the tests-first KdV synthetic data generator into runtime as a narrow stable short-horizon normalized periodic generator.

### Completed Outcome

- implemented `pdelie.data.generate_kdv_1d_field_batch(...)`
- kept the exact M0 signature and defaults:
  - `batch_size=2`
  - `num_times=17`
  - `num_points=64`
  - `max_time=0.03`
  - `num_modes=3`
  - `amplitude=0.08`
  - `seed=0`
  - `num_substeps=8`
  - `domain_length=DEFAULT_DOMAIN_LENGTH`
- kept no `dtype` parameter and no custom initial-condition API
- froze coordinate conventions:
  - `x = np.linspace(0.0, domain_length, num_points, endpoint=False)`
  - `x` spans `[0, domain_length)`
  - `time = np.linspace(0.0, max_time, num_times)`
  - `time` spans `[0, max_time]`
  - values shape is `(batch_size, num_times, num_points, 1)`
- preserved canonical metadata:
  - `boundary_conditions["x"] == "periodic"`
  - `grid_type == "rectilinear"`
  - `grid_regularity == "uniform"`
  - `coordinate_system == "cartesian"`
  - `parameter_tags == {"equation": "kdv_normalized"}`
- validated:
  - positive integer `batch_size`
  - `num_times >= 3`
  - `num_points >= 16`
  - finite positive `max_time`
  - integer `num_modes >= 1`
  - `num_modes <= floor(num_points / 3)`
  - finite nonnegative `amplitude`
  - integer `seed`
  - positive integer `num_substeps`
  - finite positive `domain_length`
- accepted Python integer and NumPy integer scalar parameters while rejecting bools
- accepted `amplitude=0.0` as a valid zero-field case without using it for relative-L2 release assertions
- refactored the test-only KdV feasibility helper to call the runtime generator while keeping residual/derivative feasibility helpers test-only
- updated public-surface guards so `pdelie.data.generate_kdv_1d_field_batch` is public, root KdV exports remain absent, public coefficient-sampling helpers remain absent, and `KdVResidualEvaluator` remains pending for M3
- updated `API_STABILITY.md` for the generator API

### Acceptance Criteria

- generated KdV fields are reproducible
- generated fields validate as canonical `FieldBatch`
- default fixture mass drift is `<= 1e-8`
- default fixture relative L2 drift is `<= 5e-3`
- invalid generator parameters raise typed errors
- `API_STABILITY.md` documents the landed generator API

---

## Milestone 3 - KdV Residual Evaluator

**Status:** COMPLETE

### Goal

Promote normalized KdV strong-form residual evaluation into runtime.

### Completed Outcome

- implemented `pdelie.residuals.KdVResidualEvaluator`
- froze the normalized KdV strong-form equation `u_t + 6*u*u_x + u_xxx = 0`
- compute derivatives internally with `compute_spectral_fd_derivatives(field, max_spatial_order=3)` when derivatives are omitted
- require supplied derivatives to validate against the field and include `u_t`, `u_x`, and `u_xxx`
- reject missing `u_xxx` with a typed validation error before residual construction
- keep supplied derivative backend compatibility field-based rather than requiring `backend == "spectral_fd"`
- validate the normalized KdV stable scope:
  - canonical dims `("batch", "time", "x", "var")`
  - scalar `var`
  - periodic `x`
  - finite, unmasked values
  - `field.metadata["parameter_tags"]["equation"] == "kdv_normalized"`
- return `ResidualBatch(definition_type="analytic", normalization="none")`
- include diagnostics:
  - `equation`
  - `backend`
  - `max_abs_residual`
  - `rms_residual`
- expose the evaluator only from `pdelie.residuals`, not root `pdelie`
- keep weak KdV and configurable KdV coefficients absent
- updated `API_STABILITY.md` for the residual evaluator API

### Acceptance Criteria

- clean default KdV residual max absolute value is `< 1e-2`
- clean default KdV residual RMS value is `< 2e-3`
- missing required derivatives raise typed errors
- unsupported fields raise typed errors
- non-periodic or non-canonical inputs are rejected
- `API_STABILITY.md` documents the landed residual evaluator API

---

## Milestone 4 - KdV Vertical Slice

**Status:** COMPLETE

### Goal

Prove KdV works through the existing translation fitting and held-out verification stack.

### Completed Outcome

- added KdV fit/verification coverage using the frozen fixture:
  - generator seed `9001`
  - `batch_size = 5`
  - `train_size = 2`
  - split seed `9002`
  - all other generator settings default
- added `python -m pdelie.examples.kdv_vertical_slice`
- added lazy `pdelie.examples.run_kdv_vertical_slice_example`
- kept root `pdelie` exports unchanged
- kept the vertical slice on the normalized periodic short-horizon strong path only
- computed conservation diagnostics on the full generated fixture before train/heldout splitting
- kept the example output as a JSON-serializable runtime smoke summary, not a stable canonical artifact schema
- observed frozen-fixture values:
  - max absolute residual: `0.0029755398453998883`
  - RMS residual: `0.0005530662104030956`
  - mass drift: `1.529348589458863e-16`
  - relative L2 drift: `4.353026792731057e-14`
  - translation span distance: `0.007441277120177836`
  - first-epsilon held-out verification error: `3.7632323492784305e-06`
  - verification classification: `approximate`
  - fit mode: `svd`
  - reference fallback used: `False`

### Acceptance Criteria

- translation span distance is `<= 5e-2`
- first-epsilon held-out verification error is `< 1e-4`
- verification classification is not `failed`
- observed `approximate` classification is acceptable because the M4 gate requires only non-failed verification
- example smoke runs without changing the existing Heat example

---

## Milestone 5 - Imported Parity and Non-goal Guards

**Status:** PENDING

### Goal

Prove KdV remains compatible with the existing structured-ingestion path while protecting v0.9 scope boundaries.

### Planned Work

- add mandatory `from_numpy` parity for representative KdV data
- add optional `from_xarray` parity with `pytest.importorskip`
- compare derivative keys, residual diagnostics, fitted span distance, and verification classification with tolerances
- assert no weak KdV API
- assert no root `pdelie` exports for KdV APIs
- assert v0.8 weak report APIs remain stable
- assert no broad adapter expansion

### Acceptance Criteria

- native and imported KdV paths agree within frozen tolerances
- optional xarray parity skips cleanly when xarray is unavailable
- weak KdV remains absent
- root exports remain unchanged
- v0.8 weak report API tests remain green

---

## Milestone 6 - Release Gate and Release Readiness

**Status:** PENDING

### Goal

Add the compact `v0_9-release-gate`, align release-facing docs, and cut an RC-first release path.

### Planned Work

- add `tests/test_v0_9_release_gate.py`
- add `v0_9-release-gate` CI visibility job
- update README, changelog, release readiness, package version, and final release docs
- include KdV wheel-smoke coverage after build
- cut `v0.9.0rc1` first for TestPyPI/preflight if publishing is configured
- tag final `v0.9.0` only after full tests, build, smoke, historical gates, and `v0_9-release-gate` are green

### Acceptance Criteria

- historical release gates remain green
- `v0_9-release-gate` is green
- full test suite passes
- source and wheel build passes
- clean wheel smoke passes
- KdV vertical slice passes
- release-facing docs describe stable short-horizon normalized periodic KdV, not general KdV support

---

## Executed Milestone Sequence

Locked sequence:

Milestone 0 -> KdV strong-path scope freeze
Milestone 1 -> spectral `u_xxx`
Milestone 2 -> KdV generator
Milestone 3 -> KdV residual evaluator
Milestone 4 -> KdV vertical slice
Milestone 5 -> imported parity and non-goal guards
Milestone 6 -> release gate and release readiness

---

## Rules

- DO NOT promote weak KdV in `v0.9`
- DO NOT add root `pdelie` exports for KdV runtime APIs
- DO NOT add custom KdV initial-condition APIs in `v0.9`
- DO NOT broaden `v0.9` into general KdV support
- DO NOT broaden `v0.9` into PDEBench, The Well, multidimensional, multivariable, nonuniform-grid, operator, or broad adapter work
- DO NOT update `API_STABILITY.md` in M0
- DO update `API_STABILITY.md` in the same milestone where each public API lands
- DO preserve existing Heat/Burgers and v0.8 weak-report behavior

---

## Status

- `v0.8`: COMPLETE
- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: PENDING
- Milestone 6: PENDING
