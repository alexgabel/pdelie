# V0.11 Scope Freeze

## Summary

`v0.11` is the Kuramoto-Sivashinsky feasibility-first release for `pdelie`.

Its purpose is:

> evaluate whether a normalized scalar 1D periodic Kuramoto-Sivashinsky strong path can be promoted safely into the stable runtime surface.

Stable runtime promotion is conditional.
M0 does not commit a public KS generator, residual evaluator, vertical slice, imported parity path, or release gate.

Candidate stable path:

`canonical scalar 1D uniform periodic FieldBatch -> spectral_fd higher spatial derivatives -> normalized KS residual evaluator -> translation fit/verification`

`v0.11` may close in one of two ways:

- stable KS promotion, if later milestones show enough numerical margin and supportability
- explicit no-go/defer closeout, if the feasibility evidence is not strong enough for a stable `v0.x` surface

---

## Feasibility Scope

The `v0.11` feasibility scope is limited to:

- scalar 1D uniform periodic fields
- canonical `FieldBatch` inputs
- spectral finite-difference derivative backends already in the stable engine
- normalized Kuramoto-Sivashinsky strong-form feasibility
- polynomial translation fitting and held-out verification through existing runtime paths
- deterministic synthetic feasibility fixtures
- eventual imported parity only through existing structured ingestion APIs if promotion remains plausible

M1 freezes the equation and numerical semantics below.
Generator implementation details, promotion status, imported-parity requirements, and public API names remain conditional until later milestones.

---

## KS Equation and Numerical Semantics

Frozen normalized strong form:

```text
u_t + u*u_x + u_xx + u_xxxx = 0
```

Frozen residual form:

```text
u_t + u*u_x + u_xx + u_xxxx
```

Equation form:

- normalized
- nonconservative
- strong-form residual
- scalar `u`
- one periodic spatial dimension `x`

The equivalent conservative nonlinear term may be written as `1/2*(u^2)_x` in explanatory text, but runtime residual semantics use `u*u_x`.

Required derivatives for KS residual feasibility:

- `u_t`
- `u_x`
- `u_xx`
- `u_xxxx`

`u_xxx` is not required by the KS residual evaluator.
If the derivative backend emits it as part of an order-4 derivative batch, the KS residual must not depend on it.

Periodic boundary terms are assumed through canonical periodic `x`.

---

## Future Derivative Backend Semantics

If KS feasibility proceeds to runtime implementation, the planned derivative extension is:

```python
compute_spectral_fd_derivatives(
    field: FieldBatch,
    *,
    max_spatial_order: int = 4,
) -> DerivativeBatch
```

Frozen order-4 behavior:

- `max_spatial_order=4` emits `u_t`, `u_x`, `u_xx`, `u_xxx`, and `u_xxxx`
- `max_spatial_order=2` remains the default and preserves current behavior, arrays, config, and diagnostics
- `u_xxxx` uses the same FFT wavenumber convention already used for `u_x`, `u_xx`, and `u_xxx`
- unsupported orders raise `ScopeValidationError`

`API_STABILITY.md` is updated only when the order-4 public derivative API actually lands.

---

## Coordinate and Fixture Conventions

Frozen feasibility conventions:

- canonical dims are exactly `("batch", "time", "x", "var")`
- scalar `var` only
- finite unmasked values only
- `x = linspace(0, domain_length, num_points, endpoint=False)`
- `time = linspace(0, max_time, num_times)`
- `time` is strictly increasing and uniform
- `x` is uniform and periodic
- synthetic feasibility fixtures should use zero-mean Fourier-mode initial conditions
- synthetic feasibility fixtures should use two-thirds dealiasing
- synthetic feasibility fixtures should use periodic RK-style rollout unless M2 proves this unsuitable

---

## Feasibility Diagnostics and Preliminary Targets

Frozen feasibility diagnostics:

- residual `max_abs_residual`
- residual `rms_residual`
- mass drift as the conserved diagnostic
- relative L2 drift as diagnostic-only, not a conservation gate
- translation span distance
- first-epsilon held-out verification error
- verification classification, with acceptance requiring only `classification != "failed"`

Preliminary feasibility targets:

- residual max `< 5e-2`
- residual RMS `< 1e-2`
- mass drift `<= 1e-8`
- translation span distance `<= 1e-1`
- first-epsilon held-out verification error `< 5e-4`
- verification classification is not `failed`

These are feasibility targets, not release gates.
M4 must replace or confirm them with observed-margin thresholds before stable KS promotion.

---

## Candidate Public Surface

If promotion succeeds, the likely public runtime surface is:

- a KS synthetic data generator under `pdelie.data`
- a KS strong-form residual evaluator under `pdelie.residuals`
- a KS vertical-slice example under `pdelie.examples`

All candidate APIs remain uncommitted in M0.
No `API_STABILITY.md` update is made until an actual public `v0.11` API lands.

Candidate KS APIs must remain submodule-only unless a later milestone explicitly freezes otherwise.
No root `pdelie` exports are part of M0.

---

## Promotion Gate

Stable KS promotion requires later milestones to establish:

- exact equation normalization
- derivative accuracy and order requirements
- deterministic generator behavior
- controlled short-horizon rollout stability
- residual thresholds with observed margin
- conservation or diagnostic metrics appropriate to the chosen normalized equation
- translation fit and held-out verification thresholds with observed margin
- imported parity expectations, if the runtime surface is promoted
- explicit public API and non-goal guards

If these are not established, `v0.11` should close as an explicit feasibility no-go/defer release rather than landing a weak stable surface.

---

## Explicit Non-goals

M0 explicitly forbids:

- weak KS
- weak derivative expansion
- broad dataset adapters
- multidimensional grids
- nonuniform grids
- multivariable systems
- custom KS initial-condition APIs
- configurable KS coefficient families
- operator-facing symmetry work
- root `pdelie` exports for KS
- package metadata changes
- README/changelog/release-readiness updates
- manuscript-specific thresholds, reports, figures, or experiment logic

---

## Milestones

### Milestone 0 - KS Feasibility Scope Reset

Promote `v0.11` to committed feasibility-first status, add this scope freeze, reset `PLAN.md`, and audit `API_STABILITY.md` without changing it.

### Milestone 1 - KS Equation and Numerical Semantics Freeze

Freeze the normalized KS equation as `u_t + u*u_x + u_xx + u_xxxx = 0`, freeze order-4 derivative semantics, coordinate conventions, candidate diagnostics, and preliminary feasibility targets.

### Milestone 2 - KS Feasibility Generator / Prototype

Build or adapt an internal deterministic KS feasibility generator/prototype without committing a stable runtime API unless the milestone explicitly freezes one.

### Milestone 3 - KS Residual Feasibility Prototype

Evaluate the strong-form KS residual path with typed validation and diagnostics, while keeping public API promotion conditional.

### Milestone 4 - KS Vertical-Slice Feasibility

Run the candidate KS path through derivative computation, residual evaluation, translation fitting, and held-out verification on frozen feasibility fixtures.

### Milestone 5 - Promotion Decision and Imported-Parity / Non-goal Guards

Make the explicit stable-promotion versus no-go decision.
If promotion proceeds, add representative imported parity and public-surface guards.
If not, close KS as deferred without runtime API expansion.

### Milestone 6 - Release Gate / Readiness or No-go Closeout

If promoted, add the compact release gate and release-facing docs.
If not promoted, document the no-go/defer evidence and leave the stable public surface unchanged.

---

## Rules

- DO NOT add public KS APIs in M0.
- DO NOT update `API_STABILITY.md` until a public `v0.11` API actually lands.
- DO NOT promote weak KS in `v0.11`.
- DO NOT treat preliminary M1 feasibility targets as final release gates without observed M4 margin.
- DO NOT broaden `v0.11` into broad adapters, multidimensional grids, nonuniform grids, multivariable systems, or operator-facing work.
- DO NOT add manuscript-specific logic.
- DO preserve existing Heat/Burgers, `v0.8` weak-report, `v0.9` KdV, and `v0.10` reporting behavior.

---

## Status

- `v0.10`: COMPLETE
- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: PENDING
- Milestone 3: PENDING
- Milestone 4: PENDING
- Milestone 5: PENDING
- Milestone 6: PENDING
