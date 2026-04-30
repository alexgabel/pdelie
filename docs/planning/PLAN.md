# PDELie - Execution Plan (V0.12)

## Current Release Status

**V0.12 is active as diagnostics and supportability hardening**

This file is the active execution record for the `v0.12` release series.

`v0.12` is not a new numerics release. It is a supportability release focused on:

- generator-fit diagnostics
- verification diagnostics
- reporting helper hardening
- internal KS diagnostic sweeps
- orbit/coverage diagnostic feasibility
- API/public-surface audit
- compact release-gate readiness

Committed release theme:

`existing stable Heat/Burgers/weak-report/KdV/reporting surfaces -> fit and verification diagnostics -> orbit/coverage reporting feasibility -> release supportability`

This file should not redefine package contracts.
Contracts and stable behavior belong in:

- `docs/specs/SPEC.md`
- `docs/specs/CONTRACTS_AND_DEFAULTS.md`
- `docs/specs/API_STABILITY.md`
- `docs/planning/ROADMAP.md`
- `docs/planning/V0_12_SCOPE.md`

`API_STABILITY.md` was audited in M0 and M1 and remains unchanged because no new `v0.12` public API lands in either milestone.
It should change in M2 if the frozen public reporting helper lands.

---

## V0.11 Closeout

`v0.11` is complete as a Kuramoto-Sivashinsky feasibility/no-go release.

Completed outcome:

- public `compute_spectral_fd_derivatives(..., max_spatial_order=4)` order-4 derivative extension
- internal KS generator feasibility helper under tests only
- internal KS residual feasibility helper under tests only
- internal KS vertical-slice feasibility coverage
- explicit no-go/defer decision for stable KS runtime promotion
- compact `v0_11-release-gate` CI visibility

The important `v0.11` conclusion is unchanged:

- KS residual feasibility passed with large margin
- mass drift passed with large margin
- held-out canonical translation verification passed
- direct residual-based SVD fitting was out of tolerance
- vertical-slice evidence was reference-fallback-backed
- stable KS generator/residual/example promotion was deferred

`v0.12` begins from that closeout.
It does not reopen KS promotion.

---

## Milestone 0 - Scope Freeze

**Status:** COMPLETE

### Goal

Freeze `v0.12` as diagnostics and supportability hardening, not a numerical expansion release.

### Completed Outcome

- added `docs/planning/V0_12_SCOPE.md`
- kept `docs/planning/V0_12_OPTIONS.md` as the supporting diagnosis/options document
- reset `docs/planning/PLAN.md` as the active `v0.12` execution record
- updated `docs/planning/ROADMAP.md` to make `v0.12` the next committed release target
- recorded `v0.11` as completed/no-go feasibility history
- recorded that KS remains internal feasibility/no-go evidence from `v0.11`
- recorded that `v0.12` does not add a new PDE, weak KS, stable KS runtime APIs, broad adapters, multidimensional grids, or private-paper policy
- recorded that any public `v0.12` API must be a reporting/diagnostic helper frozen in M1 before implementation
- audited `docs/specs/API_STABILITY.md`
- left `docs/specs/API_STABILITY.md` unchanged because no public API landed in M0
- left runtime source, tests, README, changelog, package metadata, release readiness, and CI unchanged

### Acceptance Criteria

M0 is complete only if:

- `V0_12_SCOPE.md`, `PLAN.md`, and `ROADMAP.md` agree on the committed `v0.12` scope
- `v0.11` remains described as a completed KS feasibility/no-go release
- `v0.12` is described as diagnostics and supportability hardening
- no stable KS generator, residual evaluator, example, imported parity, weak API, or root export is promoted
- no new PDE or broad adapter scope is introduced
- `API_STABILITY.md` remains unchanged
- no runtime source files change

---

## Milestone 1 - Fit / Verification Diagnostic Semantics Freeze

**Status:** COMPLETE

### Goal

Freeze diagnostic semantics before implementation.

### Completed Outcome

- froze one future M2 public reporting helper:
  - `pdelie.reporting.summarize_generator_fit_diagnostics(generator: GeneratorFamily) -> dict[str, Any]`
- froze public helper policy:
  - submodule-only under `pdelie.reporting`
  - no root `pdelie` export
  - JSON-compatible plain dict output
  - input is `GeneratorFamily`
  - wrong input type raises the existing typed schema validation error in M2
  - helper summarizes `GeneratorFamily.diagnostics`
  - helper does not create a canonical object or mutate inputs
- froze summary metadata:
  - `summary_schema_version = "0.1"`
  - `summary_type = "generator_fit_diagnostics"`
- froze fit diagnostic fields:
  - `parameterization`
  - `fit_mode`
  - `training_epsilon`
  - `basis`
  - `basis_delta_norms`
  - `design_column_norms`
  - `singular_values`
  - `condition_number`
  - `fit_residual`
  - `min_delta_basis`
  - `selected_coefficients`
  - `svd_coefficients`
  - `selected_span_distance`
  - `svd_span_distance`
  - `reference_fallback_used`
  - `fallback_reason`
  - `evidence_label`
- froze condition-number policy:
  - `condition_number = largest_singular_value / smallest_singular_value`
  - if the denominator is zero or nonfinite, report `condition_number = None`
- froze fallback reason policy:
  - `fallback_reason` is a stable category string, not prose
  - current stable fallback category remains `svd_translation_span_drift`
- froze evidence labels:
  - `direct_svd_in_tolerance`
  - `direct_svd_out_of_tolerance`
  - `reference_fallback`
  - `mixed`
  - `unavailable`
- froze verification diagnostic semantics:
  - keep `pdelie.reporting.summarize_verification_report(...)` as the verification summary surface
  - M2 may harden its top-level summary fields for transform, span, and batch-error diagnostics if needed
  - M1/M2 do not change verification classification rules or finite-transform behavior
- froze M3 internal KS sweep semantics:
  - sweeps record epsilon, fit mode, fallback status/reason, selected span, SVD span, first verification error, classification, singular values, and condition number
  - sweeps are diagnostic artifacts, not promotion gates
- left `docs/specs/API_STABILITY.md` unchanged because no public API landed in M1

### Acceptance Criteria

- `V0_12_SCOPE.md` and `PLAN.md` agree on the future public helper name and diagnostic fields
- `ROADMAP.md` still describes `v0.12` as diagnostics/supportability, not new numerical scope
- `API_STABILITY.md` remains unchanged during M1
- no runtime source, tests, README, changelog, release docs, package metadata, or CI files change in M1

---

## Milestone 2 - Diagnostic / Reporting Helper Implementation

**Status:** PENDING

### Goal

Implement the M1-frozen diagnostic/reporting helper.

### Planned Scope

- add `pdelie.reporting.summarize_generator_fit_diagnostics(...)`
- update `pdelie.reporting.summarize_generator_family(...)` only if needed to share internal formatting or include the fit summary without changing canonical objects
- keep outputs JSON-compatible and supportability-oriented
- add missing fit diagnostics to `fit_translation_generator(...)` if required for the frozen summary:
  - singular values
  - condition number
  - design column norms
  - selected coefficients
  - selected span distance
  - evidence label
- preserve existing canonical object schemas
- preserve fitting selection behavior unless a deterministic blocker appears
- update `API_STABILITY.md` when the public reporting helper lands

### Explicit Non-goals

- no new canonical object unless M1 proves it is necessary
- no fitting algorithm change
- no KS generator/residual promotion
- no weak KS
- no private-paper reporting policy
- no root export expansion unless explicitly frozen

---

## Milestone 3 - Internal KS Diagnostic Sweep Harness

**Status:** PENDING

### Goal

Keep KS internal and add bounded diagnostics for the `v0.11` no-go failure mode.

### Planned Scope

- bounded epsilon sweeps
- selected span distance
- SVD span distance
- fallback status and reason
- first verification error
- singular values and condition number if M2 exposes them
- cheap fixture variants only if they remain internal and non-gated
- no promotion gate

### Explicit Non-goals

- no stable KS data generator
- no stable KS residual evaluator
- no KS vertical-slice example
- no KS imported parity
- no API stability entry for KS generator/residual APIs

---

## Milestone 4 - Orbit / Coverage Diagnostic Feasibility

**Status:** PENDING

### Goal

Evaluate paper-agnostic orbit and coverage diagnostics without implementing downstream experiment policy.

### Planned Scope

- read-only finite-transform or orbit views if scoped tightly
- periodic `x` coverage diagnostics
- augmentation provenance summaries
- finite-transform consistency checks
- reporting-only coverage summaries before any mutation or augmentation API

### Explicit Non-goals

- no private sparse-discovery branch logic
- no manuscript-specific thresholds, labels, tables, or figures
- no train-augmentation recipes
- no PDEBench or The Well
- no multidimensional, nonuniform, or multivariable expansion

---

## Milestone 5 - API / Public-surface Audit

**Status:** PENDING

### Goal

Audit API stability and public exports after M2/M4 helper decisions.

### Planned Scope

- verify `API_STABILITY.md` matches any public reporting/diagnostic helpers that landed
- verify root exports remain narrow
- verify public KS generator/residual/example APIs remain absent
- verify weak KS remains absent
- verify broad adapters remain absent
- update public-surface guards only for real scope changes

### Explicit Non-goals

- no new numerical scope
- no CI restructuring beyond release-gate hygiene
- no release-facing metadata changes before M6

---

## Milestone 6 - Release Gate and Readiness

**Status:** PENDING

### Goal

Close `v0.12` with compact release-gate coverage, docs alignment, package metadata, and direct Git-tag readiness.

### Planned Scope

- add compact `v0_12-release-gate`
- keep full editable tests as historical gate coverage
- keep package smoke small
- update README, changelog, release readiness, roadmap, and package metadata
- audit `API_STABILITY.md`
- document final release path

### Explicit Non-goals

- no package-index publishing before the `v1.0` policy is accepted
- no KS promotion unless a prior milestone explicitly changes the no-go decision with evidence
- no new PDE or broad adapter scope

---

## Locked Milestone Sequence

Milestone 0 -> scope freeze
Milestone 1 -> fit / verification diagnostic semantics freeze
Milestone 2 -> diagnostic / reporting helper implementation
Milestone 3 -> internal KS diagnostic sweep harness
Milestone 4 -> orbit / coverage diagnostic feasibility
Milestone 5 -> API / public-surface audit
Milestone 6 -> release gate and readiness

---

## Rules

- DO NOT add a new PDE in `v0.12`.
- DO NOT promote public KS generator, residual evaluator, example, imported parity, weak API, or root exports.
- DO NOT implement weak KS.
- DO NOT add broad dataset adapters, PDEBench, The Well, multidimensional grids, nonuniform grids, or multivariable systems.
- DO NOT implement private-paper experiment policy.
- DO NOT implement orbit augmentation utilities before M4 scope is frozen.
- DO NOT implement reporting helpers before M1 freezes exact semantics and M2 accepts implementation.
- DO NOT update `API_STABILITY.md` unless a public API lands or an audit finds a real mismatch.
- DO preserve existing Heat/Burgers, `v0.8` weak-report, `v0.9` KdV, `v0.10` reporting, and `v0.11` order-4 derivative behavior.

---

## Status

- `v0.11`: COMPLETE
- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: PENDING
- Milestone 3: PENDING
- Milestone 4: PENDING
- Milestone 5: PENDING
- Milestone 6: PENDING
