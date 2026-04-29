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
- synthetic feasibility fixtures use zero-mean Fourier-mode initial conditions
- synthetic feasibility fixtures use two-thirds dealiasing
- synthetic feasibility rollout uses ETDRK4
- rollout evolution is `u_t = -u*u_x - u_xx - u_xxxx`
- nonlinear evaluation uses conservative spectral form `u*u_x = 0.5*(u^2)_x`
- nonlinear products are dealised with the two-thirds rule
- the zero Fourier mode is explicitly preserved through rollout

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
No KS generator or residual entry is added to `API_STABILITY.md` until an actual public KS API lands.

Candidate KS APIs must remain submodule-only unless a later milestone explicitly freezes otherwise.
No root `pdelie` exports are part of M0.

M2 adds only the public derivative-backend order-4 extension.
The KS generator remains an internal feasibility helper in M2 and does not become public API.

---

## M5 Promotion Decision

Stable KS promotion is deferred for `v0.11`.

M2-M4 produced useful feasibility evidence, but not enough to land a stable public KS strong path in this release.
The frozen KS fixture shows strong residual and canonical translation verification behavior:

- residual max absolute value: `2.276047466221332e-09`
- residual RMS value: `3.450580898077348e-10`
- mass drift: `4.686823294199099e-16`
- first-epsilon held-out verification error: `2.533384127588474e-13`
- verification classification: `exact`

The blocker for promotion is translation fitting evidence:

- selected span distance passes because canonical reference fallback is used: `0.0`
- direct SVD span distance is out of tolerance: `0.4178159498317849`
- fit mode is `reference_fallback`
- fallback reason is `svd_translation_span_drift`
- M4 evidence label is `reference_fallback`

Interpretation:

- KS remains internal feasibility evidence in `v0.11`
- no stable KS data generator lands in `v0.11`
- no stable KS residual evaluator lands in `v0.11`
- no KS vertical-slice example lands in `v0.11`
- no KS imported parity lands in `v0.11` because there is no stable public KS runtime surface to validate
- `compute_spectral_fd_derivatives(..., max_spatial_order=4)` remains the only public `v0.11` API change so far

M6 should close `v0.11` as a no-go/defer feasibility release unless a later explicit scope change reopens the promotion decision.

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

Extend the public derivative backend through `max_spatial_order=4`, then build an internal deterministic KS feasibility generator/prototype using ETDRK4, conservative spectral nonlinear evaluation, two-thirds dealiasing, and explicit zero-mode preservation.

### Milestone 3 - KS Residual Feasibility Prototype

Evaluate the strong-form KS residual path with typed validation and diagnostics, while keeping public API promotion conditional.

### Milestone 4 - KS Vertical-Slice Feasibility

Run the candidate KS path through derivative computation, residual evaluation, translation fitting, and held-out verification on frozen feasibility fixtures.

### Milestone 5 - Promotion Decision and Imported-Parity / Non-goal Guards

Complete the stable-promotion versus no-go decision.
M5 defers stable KS promotion for `v0.11`, records the reference-fallback evidence, and keeps KS runtime APIs absent.

### Milestone 6 - Release Gate / Readiness or No-go Closeout

Document the no-go/defer evidence and leave the stable public surface unchanged.

---

## Rules

- DO NOT add public KS APIs in M0.
- DO NOT update `API_STABILITY.md` for KS generator or residual APIs until those public APIs actually land.
- DO NOT treat the internal M2 KS generator helper as public API.
- DO NOT treat the internal M3 KS residual evaluator as public API.
- DO NOT treat M4 fallback-backed verification as direct KS residual-fit recovery.
- DO NOT add KS imported parity unless a stable public KS runtime surface is promoted.
- DO NOT promote a stable KS generator, residual evaluator, or example in `v0.11` after the M5 no-go/defer decision.
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
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: PENDING
