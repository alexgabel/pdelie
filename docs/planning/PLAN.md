# PDELie - Execution Plan (V0.11)

## Current Release Status

**V0.11 committed as Kuramoto-Sivashinsky feasibility-first**

This file is the active execution record for the `v0.11` release series.

`v0.11` is a feasibility-first release.
It evaluates whether normalized scalar 1D periodic Kuramoto-Sivashinsky can be promoted safely into the stable strong-path runtime surface.

Candidate stable path:

`canonical scalar 1D uniform periodic FieldBatch -> spectral_fd higher spatial derivatives -> normalized KS residual evaluator -> translation fit/verification`

Stable runtime promotion is conditional.
`v0.11` may close either as stable KS promotion or as an explicit no-go/defer feasibility release.

This file should not redefine package contracts.
Contracts and stable behavior belong in:

- `docs/specs/SPEC.md`
- `docs/specs/CONTRACTS_AND_DEFAULTS.md`
- `docs/specs/API_STABILITY.md`
- `docs/planning/ROADMAP.md`
- `docs/planning/V0_11_SCOPE.md`

`API_STABILITY.md` was audited in M0/M1 and remains unchanged because no new `v0.11` public API has landed yet.
It must be updated in the same milestone where any public KS API or other public API lands.

---

## V0.10 Closeout

`v0.10` is complete as the supportability and `v1.0` readiness release.

Completed outcome:

- public runtime reporting helpers under `pdelie.reporting`
- consistent nested Heat/KdV example summaries
- API stability and public-surface audit coverage
- one current release-gate CI job plus full editable tests and package smoke
- package/readiness documentation cleanup for eventual `v1.0` publishing decisions
- explicit deferral of new PDE scope, weak KdV, broad adapters, operator work, and manuscript-specific reporting logic

`v0.11` begins from the frozen `v0.10` surface.
It does not reopen Heat/Burgers, weak-report, KdV, reporting, CI cleanup, or publishing decisions.

---

## Milestone 0 - KS Feasibility Scope Reset

**Status:** COMPLETE

### Goal

Promote `v0.11` to the next committed release target, create `V0_11_SCOPE.md`, reset `PLAN.md`, and audit `API_STABILITY.md` without changing it.

### Completed Outcome

- promoted `v0.11` to committed feasibility-first scope in `ROADMAP.md`
- created `docs/planning/V0_11_SCOPE.md`
- reset `docs/planning/PLAN.md` as the active `v0.11` execution record
- recorded `v0.10` as completed
- recorded Kuramoto-Sivashinsky as the feasibility candidate
- recorded stable KS promotion as conditional on later numerical evidence
- recorded that `v0.11` may close as either stable KS promotion or no-go/defer
- audited `docs/specs/API_STABILITY.md`
- left `docs/specs/API_STABILITY.md` unchanged because no new `v0.11` public API landed in M0
- left runtime code, tests, package metadata, CI, README, changelog, and release-readiness docs unchanged

### Acceptance Criteria

M0 is complete only if:

- `ROADMAP.md`, `PLAN.md`, and `V0_11_SCOPE.md` are internally consistent
- `v0.10` is consistently described as completed
- `v0.11` is consistently described as committed and feasibility-first
- `v0.11` is not described as unconditional stable KS support
- exact KS equation normalization and numerical thresholds remain deferred to M1
- public KS APIs remain uncommitted until later milestones
- `API_STABILITY.md` remains unchanged during M0
- no runtime code, tests, package metadata, CI, README, changelog, or release-readiness docs are edited in M0

---

## Milestone 1 - KS Equation and Numerical Semantics Freeze

**Status:** COMPLETE

### Goal

Freeze the exact normalized KS equation and numerical semantics before any runtime prototype or public API is considered.

### Completed Outcome

- froze normalized nonconservative strong-form KS:
  - `u_t + u*u_x + u_xx + u_xxxx = 0`
- froze residual form:
  - `u_t + u*u_x + u_xx + u_xxxx`
- recorded the equivalent conservative nonlinear term `1/2*(u^2)_x` as explanatory only
- froze required KS residual derivatives:
  - `u_t`
  - `u_x`
  - `u_xx`
  - `u_xxxx`
- recorded that `u_xxx` is not required by the KS residual evaluator
- froze future derivative-backend strategy:
  - later `compute_spectral_fd_derivatives(..., max_spatial_order=4)` emits `u_t`, `u_x`, `u_xx`, `u_xxx`, and `u_xxxx`
  - default `max_spatial_order=2` must preserve current behavior, arrays, config, and diagnostics
  - `u_xxxx` must use the same FFT wavenumber convention as existing `u_x`, `u_xx`, and `u_xxx`
  - unsupported orders still raise `ScopeValidationError`
- froze coordinate and fixture conventions:
  - dims exactly `("batch", "time", "x", "var")`
  - scalar finite unmasked values only
  - `x = linspace(0, domain_length, num_points, endpoint=False)`
  - `time = linspace(0, max_time, num_times)`
  - strictly increasing uniform `time`
  - uniform periodic `x`
  - zero-mean Fourier-mode initial conditions for synthetic feasibility fixtures
  - two-thirds dealiasing
  - periodic RK-style rollout unless M2 proves unsuitable
- froze feasibility diagnostics:
  - residual `max_abs_residual`
  - residual `rms_residual`
  - mass drift as the conserved diagnostic
  - relative L2 drift as diagnostic-only
  - translation span distance
  - first-epsilon held-out verification error
  - verification classification with acceptance requiring only `classification != "failed"`
- froze preliminary feasibility targets:
  - residual max `< 5e-2`
  - residual RMS `< 1e-2`
  - mass drift `<= 1e-8`
  - translation span distance `<= 1e-1`
  - first-epsilon held-out verification error `< 5e-4`
  - verification classification is not `failed`
- recorded that these are feasibility targets, not release gates
- recorded that M4 must replace or confirm them with observed-margin thresholds before stable KS promotion
- kept public API names and stable promotion conditional
- left `docs/specs/API_STABILITY.md` unchanged because no public API landed in M1
- left runtime code, tests, package metadata, CI, README, changelog, and release-readiness docs unchanged

### Acceptance Criteria

- `V0_11_SCOPE.md` and `PLAN.md` agree on KS equation, derivative requirements, coordinate conventions, diagnostics, and preliminary targets
- `ROADMAP.md` still describes `v0.11` as feasibility-first, not stable KS support
- `API_STABILITY.md` remains unchanged during M1
- no runtime code, tests, package metadata, CI, README, changelog, or release-readiness docs are edited in M1

---

## Milestone 2 - KS Feasibility Generator / Prototype

**Status:** PENDING

### Goal

Create or adapt a deterministic KS feasibility generator/prototype under the frozen M1 semantics.

### Planned Outcome

- evaluate short-horizon rollout stability
- record supported fixture sizes, seeds, and numerical margins
- keep any prototype internal unless the milestone explicitly freezes a public API
- avoid custom initial-condition APIs and configurable coefficient families

---

## Milestone 3 - KS Residual Feasibility Prototype

**Status:** PENDING

### Goal

Evaluate the strong-form KS residual path under the frozen semantics.

### Planned Outcome

- test derivative requirements and residual diagnostics
- verify typed validation behavior
- measure residual thresholds on frozen feasibility fixtures
- keep public residual evaluator promotion conditional

---

## Milestone 4 - KS Vertical-Slice Feasibility

**Status:** PENDING

### Goal

Run the candidate KS path through the existing strong-path fitting and verification stack.

### Planned Outcome

- build a deterministic KS vertical-slice fixture
- run derivative computation, residual evaluation, translation fitting, and held-out verification
- record span-distance and verification margins
- decide whether the evidence is strong enough to continue toward promotion

---

## Milestone 5 - Promotion Decision and Imported-Parity / Non-goal Guards

**Status:** PENDING

### Goal

Make the explicit stable-promotion versus no-go decision.

### Planned Outcome

- if KS promotion is justified, freeze public API names and representative imported parity
- if KS promotion is not justified, close the branch as no-go/defer without runtime API expansion
- keep weak KS, broad adapters, operator APIs, and root exports absent

---

## Milestone 6 - Release Gate / Readiness or No-go Closeout

**Status:** PENDING

### Goal

Close `v0.11` according to the M5 decision.

### Planned Outcome

- if promoted, add a compact release gate and release-facing docs
- if not promoted, document the no-go/defer evidence and leave the stable public surface unchanged
- keep package-index publishing policy unchanged unless separately scoped

---

## Executed Milestone Sequence

Locked sequence:

Milestone 0 -> KS feasibility scope reset
Milestone 1 -> KS equation and numerical semantics freeze
Milestone 2 -> KS feasibility generator / prototype
Milestone 3 -> KS residual feasibility prototype
Milestone 4 -> KS vertical-slice feasibility
Milestone 5 -> promotion decision and imported-parity / non-goal guards
Milestone 6 -> release gate / readiness or no-go closeout

---

## Rules

- DO NOT add public KS APIs in M0.
- DO NOT update `API_STABILITY.md` until a public `v0.11` API actually lands or an audit finds a real omission.
- DO NOT describe `v0.11` as unconditional stable KS support before M5.
- DO NOT treat preliminary M1 feasibility targets as final release gates without observed M4 margin.
- DO NOT promote weak KS in `v0.11`.
- DO NOT add a new weak derivative API in `v0.11`.
- DO NOT broaden `v0.11` into broad adapters, multidimensional grids, nonuniform grids, multivariable systems, or operator-facing work.
- DO NOT add custom KS initial-condition APIs or configurable KS coefficient families unless a later milestone explicitly freezes them.
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
