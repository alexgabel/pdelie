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

`API_STABILITY.md` was audited in M0/M1, then updated in M2 when the public order-4 derivative API landed.
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

**Status:** COMPLETE

### Goal

Create or adapt a deterministic KS feasibility generator/prototype under the frozen M1 semantics.

### Completed Outcome

- extended public `compute_spectral_fd_derivatives(...)` to accept `max_spatial_order=4`
- preserved default `max_spatial_order=2` behavior, arrays, config, and diagnostics
- froze order-4 derivative output keys:
  - `u_t`
  - `u_x`
  - `u_xx`
  - `u_xxx`
  - `u_xxxx`
- computed `u_xxxx` with the same FFT wavenumber convention as the existing spectral derivatives
- kept invalid derivative orders rejected with typed `ScopeValidationError`
- updated `docs/specs/API_STABILITY.md` for the public order-4 derivative API
- added internal KS feasibility generator helpers under tests only
- froze internal KS generator defaults:
  - `seed = 11101`
  - `batch_size = 5`
  - `num_times = 33`
  - `num_points = 128`
  - `max_time = 0.2`
  - `num_modes = 6`
  - `amplitude = 0.08`
  - `num_substeps = 8`
  - `domain_length = 32*pi`
- froze KS rollout evolution:
  - `u_t = -u*u_x - u_xx - u_xxxx`
- froze nonlinear evaluation:
  - conservative spectral form `u*u_x = 0.5*(u^2)_x`
  - two-thirds dealiasing for nonlinear products
- froze ETDRK4 as the internal rollout scheme
- explicitly preserved the zero Fourier mode through rollout
- verified the internal generator is deterministic, canonical, finite, zero-mean, and mass-preserving within the M1 target
- verified exact Fourier `u_xxxx` sign convention through derivative tests
- verified no public KS generator, residual evaluator, root export, custom initial-condition API, or configurable KS coefficient family landed

### Acceptance Criteria

- order-4 derivative tests pass
- internal KS generator feasibility tests pass
- `API_STABILITY.md` documents only the public derivative extension, not KS generator/residual APIs
- public-surface tests keep KS generator and residual APIs absent
- no README, changelog, package metadata, release-readiness docs, or CI changes land in M2

---

## Milestone 3 - KS Residual Feasibility Prototype

**Status:** COMPLETE

### Goal

Evaluate the strong-form KS residual path under the frozen semantics.

### Completed Outcome

- added internal `KSFeasibilityResidualEvaluator` under test helpers only
- implemented frozen residual:
  - `u_t + u*u_x + u_xx + u_xxxx`
- implemented derivative contract:
  - omitted derivatives compute `compute_spectral_fd_derivatives(field, max_spatial_order=4)`
  - supplied derivatives must validate against the field
  - supplied derivatives must include `u_t`, `u_x`, `u_xx`, and `u_xxxx`
  - `u_xxx` may be present but is not used
- returned `ResidualBatch(definition_type="analytic", normalization="none")`
- froze diagnostics:
  - `equation`
  - `backend`
  - `max_abs_residual`
  - `rms_residual`
- verified local validation:
  - dims exactly `("batch", "time", "x", "var")`
  - scalar `var`
  - finite unmasked values
  - periodic `x`
  - `field.metadata["parameter_tags"]["equation"] == "ks_normalized"`
- verified valid-looking Heat and KdV fields are rejected by equation tag
- verified public KS generator/residual/root exports remain absent
- observed frozen-fixture residual diagnostics:
  - max absolute residual: `4.042559716230937e-09`
  - RMS residual: `3.756593955706264e-10`
- kept public residual evaluator promotion conditional
- left `docs/specs/API_STABILITY.md` unchanged because no public API landed in M3

### Acceptance Criteria

- internal and explicit order-4 derivative residual paths match
- order-3 derivatives fail clearly because `u_xxxx` is missing
- residual diagnostics satisfy M1 feasibility targets
- public-surface tests keep KS generator and residual APIs absent
- no README, changelog, package metadata, release-readiness docs, or CI changes land in M3

---

## Milestone 4 - KS Vertical-Slice Feasibility

**Status:** COMPLETE

### Goal

Run the candidate KS path through the existing strong-path fitting and verification stack.

### Completed Outcome

- added internal KS vertical-slice feasibility coverage under tests only
- used frozen KS fixture from `generate_ks_feasibility_field_batch()`
- split train/heldout with `train_size = 2` and `seed = 11102`
- computed train derivatives with `compute_spectral_fd_derivatives(..., max_spatial_order=4)`
- evaluated train residual with internal `KSFeasibilityResidualEvaluator`
- fit with `fit_translation_generator(..., epsilon=1e-4)`
- verified heldout data with `verify_translation_generator(...)`
- verified derivative keys:
  - `u_t`
  - `u_x`
  - `u_xx`
  - `u_xxx`
  - `u_xxxx`
- observed M4 feasibility metrics:
  - residual max absolute value: `2.276047466221332e-09`
  - residual RMS value: `3.450580898077348e-10`
  - mass drift: `4.686823294199099e-16`
  - relative L2 drift: `0.0070894859776733715`
  - selected span distance: `0.0`
  - SVD span distance: `0.4178159498317849`
  - fit mode: `reference_fallback`
  - reference fallback used: `True`
  - fallback reason: `svd_translation_span_drift`
  - first-epsilon heldout verification error: `2.533384127588474e-13`
  - verification classification: `exact`
  - transform mode: `uniform_translation`
  - evidence label: `reference_fallback`
- recorded that relative L2 drift is diagnostic-only for KS
- recorded that KS feasibility passed via reference fallback, not direct SVD in-tolerance recovery
- verified no public KS generator, residual evaluator, root export, example, broad adapter, or runtime surface landed

### Acceptance Criteria

- KS vertical slice passes M1 feasibility thresholds for residual, mass drift, selected span, first-epsilon verification error, and classification
- relative L2 drift is recorded but not used as a gate
- fallback-backed evidence records fallback reason and SVD span distance
- repeated vertical-slice summaries are deterministic within numerical tolerance
- public-surface tests keep KS generator and residual APIs absent

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
- DO NOT update `API_STABILITY.md` for KS generator or residual APIs until those public APIs actually land or an audit finds a real omission.
- DO NOT describe `v0.11` as unconditional stable KS support before M5.
- DO NOT treat the internal M2 KS generator helper as public API.
- DO NOT treat the internal M3 KS residual evaluator as public API.
- DO NOT treat M4 fallback-backed verification as direct KS residual-fit recovery.
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
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: PENDING
- Milestone 6: PENDING
