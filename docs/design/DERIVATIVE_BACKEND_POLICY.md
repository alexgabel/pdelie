# Derivative Backend Policy — Design Document

**Status:** DESIGN-FROZEN in v0.30a; **`finite_difference` v1 IMPLEMENTED in v0.30c** along with the `compute_derivatives(backend="auto")` dispatcher. Boundary-aware readiness warnings and the `residual_domain_policy` reporting field also land in v0.30c. **Residual evaluator auto-dispatch and interior-only diagnostics landed in v0.30d**: Heat, Burgers, advection-diffusion, and reaction-diffusion evaluators now route through `compute_derivatives(backend="auto")` and consume `recommended_residual_domain_policy` / `recommended_boundary_trim_width` from the `DerivativeBatch.config`. KdV and the weak evaluators remain periodic-only per v0.30 scope.

This document defines the policies governing PDELie's derivative backends after v0.30. The runtime in v0.30a is unchanged.

## Backends covered

After v0.30, two derivative backends exist:

- `spectral_fd` (existing): FFT-based spectral spatial derivatives + 2nd-order centered finite differences in time. Periodic-x only.
- `finite_difference` (new in v0.30 proper): centered finite differences with one-sided stencils at boundaries. Nonperiodic-x only.

A third name, `compute_derivatives(..., backend="auto")`, is a dispatcher, not a backend.

## `spectral_fd` policy

**Unchanged from current behavior.**

- Periodic-x is required. The check at `src/pdelie/derivatives/spectral_fd.py:32-33` stays in place.
- Spatial derivatives are computed via FFT phase factors `(ik)^n`. This is mathematically correct only for periodic data; loosening the check would silently produce garbage at the boundaries due to Gibbs ringing.
- Output is unchanged: `DerivativeBatch(backend="spectral_fd", ...)`.

After v0.30 the BC check reads `metadata["boundary_conditions"]["x"]["type"] == "periodic"` against the new structured spec, not the legacy string. The semantics are identical for callers.

## `finite_difference` policy (v0.30 proper)

A new module `src/pdelie/derivatives/finite_difference.py` will implement `compute_finite_difference_derivatives(field, *, max_spatial_order=2)`.

### Accepted BCs

- `"dirichlet"`
- `"neumann"`
- `"open_unknown"`

Periodic data passed to `finite_difference` raises `ScopeValidationError`. Periodic users must use `spectral_fd`. The dispatcher (below) handles the auto-routing.

### Order limits

The stable v0.30 surface supports:

- `u_t` via `np.gradient(values, dt, axis=t_axis, edge_order=2)` (unchanged from the time-derivative computation in `spectral_fd`)
- `u_x` via `np.gradient(values, dx, axis=x_axis, edge_order=2)`
- `u_xx` via `np.gradient(u_x, dx, axis=x_axis, edge_order=2)`

`u_xxx` and `u_xxxx` are **not** part of the stable v0.30 surface on nonperiodic data. Calling `compute_finite_difference_derivatives(field, max_spatial_order=3)` or higher raises `ScopeValidationError` unless an `experimental_high_order=True` flag is set, and even then the output is documented as advisory and may change.

#### Why no high-order FD on nonperiodic data

Repeated `np.gradient` propagates boundary error. The one-sided edge stencil at order 2 has the same asymptotic O(h²) interior accuracy as centered FD, but a larger constant. Each derivative step pulls the boundary error one stencil width into the interior. By `u_xxxx` on N≈64-point grids, the boundary-corrupted region dominates the interior region; the residual statistics become unreliable.

For periodic data the same chain works because FFT-based derivatives have no boundary problem at all. For nonperiodic data the right answer is a higher-order one-sided stencil family (Fornberg-style), or weak/Galerkin integration to bypass derivative estimation entirely. Neither is in scope for v0.30; both are candidates for later releases.

### `DerivativeBatch.config` requirements

The backend must populate:

```
{
    "spatial_method": "finite_difference_centered",
    "temporal_method": "finite_difference",
    "temporal_edge_order": 2,
    "spatial_edge_order": 2,
    "spatial_max_order": <int>,
    "boundary_handling": "dirichlet" | "neumann" | "open_unknown",
    "boundary_left_specified": <bool>,
    "boundary_right_specified": <bool>,
}
```

`boundary_left_specified` and `boundary_right_specified` read directly from the structured `BoundaryConditionSpec` faces. They allow downstream consumers (residual evaluators, readiness reports) to flag derivative results that depended on an unspecified boundary.

`DerivativeBatch.boundary_assumptions` records `"<bc_type> in x; finite differences in time"` for human inspection.

## Dispatcher: `compute_derivatives(field, *, backend="auto", max_spatial_order=2)`

A new helper, exported from `pdelie.derivatives`, selects the right backend based on the field's BC.

### Dispatch table

- `field.metadata["boundary_conditions"]["x"]["type"] == "periodic"` → `spectral_fd`
- `field.metadata["boundary_conditions"]["x"]["type"] in {"dirichlet", "neumann", "open_unknown"}` → `finite_difference`

### Explicit backend selection

- `backend="spectral_fd"` on nonperiodic data → `ScopeValidationError`
- `backend="finite_difference"` on periodic data → `ScopeValidationError`
- `backend="auto"` always succeeds for any supported BC type

### Never silent

The dispatcher must record its selection in `DerivativeBatch.config`:

```
{
    ...,
    "backend_selected_by_boundary_condition": True,
    "backend_selection_reason": "periodic_x_boundary" | "nonperiodic_x_boundary",
}
```

This is non-negotiable. A user reading a `DerivativeBatch` from disk must be able to tell which backend produced it without re-deriving the choice from `boundary_conditions`.

### Order capping under dispatch

When `backend="auto"` resolves to `finite_difference`, requesting `max_spatial_order > 2` raises `ScopeValidationError` with the same message as the direct path. The dispatcher does not silently downgrade orders.

## Residual evaluation domain policy

The existing residual evaluators (`HeatResidualEvaluator`, `BurgersResidualEvaluator`, `AdvectionDiffusionResidualEvaluator`, etc.) currently compute residuals over the full grid. On nonperiodic FD-derived data, near-boundary residuals are dominated by one-sided-stencil error and are not representative of interior residual quality.

### New summary field

`summarize_residual_batch` (in `src/pdelie/reporting/summaries.py`) gains a new field `"residual_domain_policy"` with vocabulary:

- `"full_grid"` — RMS / max over all grid points (the historical behavior for periodic data)
- `"interior_only"` — RMS / max over the interior excluding a boundary band
- `"drop_boundary_width_k"` — explicit boundary width `k` dropped from both ends

### Default policy

- Periodic data: `"full_grid"`. No boundary problem exists for spectral derivatives, so no need to trim.
- Nonperiodic FD-derived data: `"interior_only"` with default boundary width `k = 4`. The choice of `k = 4` matches the effective stencil width of `u_xx` computed as `np.gradient(np.gradient(u))`: centered second derivative consumes a 5-point stencil, edge-order-2 handling at each boundary consumes up to 3 extra points of error propagation; `k = 4` provides a safe margin.

### Reporting both

When a residual is computed on nonperiodic data, the summary SHOULD include both `"residual_domain_policy": "interior_only"` (the primary statistic) and a nested `"full_grid_diagnostic"` block with the same metrics computed over the full grid, so users can see the boundary contamination explicitly. This is recommended, not required, in v0.30 proper.

## Translation finite-transform policy on nonperiodic data

`verify_translation_generator` at `src/pdelie/verification/finite_transform.py:64` and `_apply_uniform_translation` at `:21` remain **periodic-only**. The FFT phase-shift method requires periodicity; there is no correct alternative on a finite domain without a domain policy.

### What is explicitly rejected

A `_apply_uniform_translation_open` that uses `np.roll` + extrapolation is **not approved**. `np.roll` does not translate a non-periodic function — it wraps values that have no physical meaning at the wrap point, and any extrapolation scheme (constant, linear, reflective) introduces O(1) artifacts in the residual.

### What is deferred

The correct approach for nonperiodic translation is overlap-crop:

1. Apply translation `ε`: shift the coordinate axis by `ε`.
2. Crop the field to the overlap interval `[a + |ε|, b − |ε|]` where `[a, b]` is the original domain.
3. Compute the residual on the cropped interior only.

This requires a domain policy (how to handle multiple overlapping translations, what minimum overlap is acceptable, how to compare orbits of different lengths). The full design is deferred to **v0.31.5 — Nonperiodic Orbit/Action Scope Decision** in the roadmap.

## Numerical sanity tests required for v0.30 proper

These are not implemented in v0.30a (it ships no runtime code). They are specified here so v0.30 proper has a clear acceptance contract.

### Manufactured analytic functions

For each backend × order combination, test against closed-form derivatives of:

- `u(t, x) = sin(k·x − ω·t)` on `[0, 2π]` (periodic check for spectral; reflected to `[0, π]` for FD where periodicity does not apply)
- `u(t, x) = tanh(α·x − v·t)` on `[−5, 5]` (smooth, non-periodic, Dirichlet boundaries known)
- `u(t, x) = x³ − 3xt²` on `[−1, 1]` (polynomial, exact closed-form derivatives at all orders)

For each test:
- Compare `compute_finite_difference_derivatives` outputs against the closed-form `u_t`, `u_x`, `u_xx` evaluated at the grid points.
- Assert max-absolute error in the interior decreases at rate O(h²) as the grid is refined.
- Assert max-absolute error in the **boundary band** (first/last `k` points for `k = 4`) is bounded but does **not** assert O(h²) — boundary stencils have a larger error constant.

### What not to test

**Do not test against `np.gradient`.** The new backend is built on `np.gradient` internally; testing it against itself is meaningless. Tests must use closed-form analytic derivatives.

### Convergence study

For at least one manufactured solution, run the backend at `N = 32, 64, 128, 256` and assert the interior-only max error halves to within 10% per grid doubling (the expected O(h²) order). The boundary-band max error must not blow up — a coarse bound like `< 10× interior_max` is sufficient.

## Implementation pointer (for v0.30 proper)

The most surgical path:

1. Add `src/pdelie/derivatives/finite_difference.py` with `compute_finite_difference_derivatives` mirroring the structure of `src/pdelie/derivatives/spectral_fd.py`.
2. Add `compute_derivatives` to `src/pdelie/derivatives/__init__.py` as a thin dispatcher.
3. Update `src/pdelie/residuals/heat_1d.py`, `burgers_1d.py`, `advection_diffusion_1d.py`, `reaction_diffusion_1d.py` to call `compute_derivatives(..., backend="auto")` instead of `compute_spectral_fd_derivatives(...)` when no derivatives are supplied. KdV stays periodic-only (its evaluator already requires `equation == "kdv_normalized"`, which only the periodic generator produces).
4. Update `summarize_residual_batch` to surface `residual_domain_policy`.
5. Add `compute_finite_difference_derivatives` to `tests/test_public_api.py::test_runtime_package_api_is_importable` and `tests/test_api_stability_audit.py::_ROOT_RUNTIME_NAMES`-style negative checks (it must not be a root export).
6. Update `docs/specs/API_STABILITY.md` with a "Runtime public API for the frozen `v0.30` Milestone 2 slice" subsection describing `compute_finite_difference_derivatives` and `compute_derivatives`.

The lazy-import pattern at `src/pdelie/discovery/pysindy_adapter.py:12-20` does not apply: `finite_difference` uses only `numpy`, which is already a core dependency.
