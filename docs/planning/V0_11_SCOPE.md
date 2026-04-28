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

M0 intentionally does not freeze:

- exact KS equation normalization
- derivative-order requirements
- generator rollout method
- generator stability regime
- residual evaluator contract
- residual, conservation, fitting, or verification thresholds
- imported-parity requirements
- public API names

Those decisions belong to later milestones after feasibility evidence exists.

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

Freeze exact normalized KS equation form, derivative requirements, coordinate conventions, candidate diagnostics, and preliminary feasibility thresholds.

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
- DO NOT broaden `v0.11` into broad adapters, multidimensional grids, nonuniform grids, multivariable systems, or operator-facing work.
- DO NOT add manuscript-specific logic.
- DO preserve existing Heat/Burgers, `v0.8` weak-report, `v0.9` KdV, and `v0.10` reporting behavior.

---

## Status

- `v0.10`: COMPLETE
- Milestone 0: COMPLETE
- Milestone 1: PENDING
- Milestone 2: PENDING
- Milestone 3: PENDING
- Milestone 4: PENDING
- Milestone 5: PENDING
- Milestone 6: PENDING
