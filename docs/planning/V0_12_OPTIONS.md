# V0.12 Options and KS No-go Diagnosis

## Summary

`v0.12` should not add another PDE, promote stable KS runtime APIs, or broaden adapters.
The best next release target is supportability for fitting, verification, reporting, and orbit
coverage diagnostics.

Recommended theme:

> Diagnostics and supportability hardening for generator fitting, verification, and
> translation-orbit coverage, with KS remaining internal feasibility evidence.

This keeps the library on a v1.0-readiness path while directly addressing the `v0.11`
KS no-go result.

## KS No-go Diagnosis

`v0.11` showed that the KS residual path is healthy, but the residual-based generator
fit is not direct-fit stable on the frozen fixture.

Observed status:

- KS equation under test: `u_t + u*u_x + u_xx + u_xxxx = 0`
- derivative backend: `compute_spectral_fd_derivatives(..., max_spatial_order=4)`
- residual feasibility: healthy, with large margin against the M1 targets
- vertical-slice verification: passes only after reference fallback selects the canonical
  translation generator
- stable KS public promotion: deferred

The failure is localized to residual-based generator fitting, not to the KS residual
definition, derivative sign convention, or finite-transform verification stack.

### Current Fit Diagnostics

The current translation fitter records these high-level diagnostics:

- `basis`
- `basis_delta_norms`
- `fallback_reason`
- `fit_mode`
- `fit_residual`
- `min_delta_basis`
- `reference_fallback_used`
- `svd_coefficients`
- `svd_span_distance`
- `training_epsilon`

These are enough to identify the no-go outcome:

- `reference_fallback_used == True`
- `fallback_reason == "svd_translation_span_drift"`
- direct SVD span distance is out of tolerance, around `0.418`
- selected span distance passes only because the fallback generator is used

They are not enough to fully diagnose conditioning:

- full singular values are not recorded
- condition number is not recorded
- column scaling diagnostics are limited to `basis_delta_norms`
- epsilon sensitivity is available only through ad hoc sweeps, not a standard report

### Bounded Diagnostic Sweep

A bounded local sweep was run for planning only. No release gate or tracked artifact was
created from it.

Sweep dimensions:

- fit epsilon values: `1e-5`, `3e-5`, `1e-4`, `3e-4`, `1e-3`
- default fixture: `amplitude=0.08`, `max_time=0.2`
- cheap variants:
  - lower amplitude: `amplitude=0.04`, `max_time=0.2`
  - shorter time: `amplitude=0.08`, `max_time=0.1`

Results:

| Variant | Residual Max | Residual RMS | Mass Drift | SVD Span Range | Fit Outcome |
| --- | ---: | ---: | ---: | ---: | --- |
| default | `2.28e-9` | `3.45e-10` | `4.69e-16` | `0.4173` to `0.4179` | reference fallback for all epsilons |
| lower amplitude | `6.36e-10` | `1.06e-10` | `2.40e-16` | `0.4227` to `0.4233` | reference fallback for all epsilons |
| shorter time | `5.56e-10` | `8.54e-11` | `4.35e-16` | `0.4174` to `0.4179` | reference fallback for all epsilons |

The epsilon sweep did not rescue direct SVD fitting. Lower amplitude and shorter horizon
did not rescue it either.

The default fixture's basis delta norms are highly imbalanced:

- `x`: about `309`
- `t`: about `1.12`
- `u`: about `4.7e-3`
- `1`: about `2.5e-3`

That imbalance points to conditioning and basis/objective design as the highest-probability
failure mode. The direct SVD vector mixes the constant and `u` directions instead of
recovering the canonical translation direction, while fallback verification succeeds.

Likely causes, in priority order:

1. Fit conditioning and basis scaling.
2. Residual-delta objective design for stiff fourth-order KS dynamics.
3. Frozen fixture geometry, though cheap amplitude/time variants did not fix the issue.
4. Epsilon sensitivity, currently unlikely based on the sweep.
5. Implementation ambiguity in how direct residual-based fitting should identify a
   translation generator for KS.

Not supported by current evidence:

- a broken KS residual equation
- a derivative sign error for `u_xxxx`
- a verification-stack failure
- a missing fallback reason

The fallback reason is stable and explicit: `svd_translation_span_drift`.

## V0.12 Theme Options

### Ranking

| Rank | Theme | ROI | Risk | V1.0 Relevance | Recommendation |
| ---: | --- | --- | --- | --- | --- |
| 1 | A. Stable diagnostics/reporting hardening | High | Low to medium | High | Primary v0.12 theme |
| 2 | D. CI/release/API supportability | Medium to high | Low | High | Include as release hardening |
| 3 | C. KS fit stabilization diagnostics | Medium | Medium | Medium | Keep internal and diagnostic-only |
| 4 | B. Generic orbit/coverage augmentation utilities | Medium | Medium to high | Medium to high | Scope carefully; defer mutation-heavy APIs |

### A. Stable Diagnostics and Reporting Hardening

This has the best ROI because it addresses the KS no-go without expanding numerical scope.
It also improves supportability for Heat, Burgers, KdV, and downstream sparse-discovery
workflows.

Candidate work:

- summarize residual diagnostics more consistently
- summarize generator fit diagnostics, including singular values and condition numbers
- summarize verification reports and branch-level outcomes
- make examples and release gates less ad hoc
- keep summaries JSON-compatible and supportability-oriented
- avoid new canonical objects unless a narrow need is proven

Recommended for `v0.12`.

### B. Generic Orbit and Coverage Augmentation Utilities

This could be valuable, but it has a higher boundary risk. It can easily become downstream
experiment orchestration if the scope is not frozen tightly.

Candidate work:

- read-only finite-transform or orbit views over `FieldBatch`
- periodic `x` window coverage diagnostics
- augmentation provenance summaries
- finite-transform consistency checks
- train-only augmentation utilities only if kept generic and paper-agnostic

Recommended as a secondary track only after diagnostics semantics are frozen. Mutating
augmentation utilities should remain downstream unless a small reusable API is clearly
identified.

### C. KS Fit Stabilization Diagnostics

KS should stay internal in `v0.12`. The useful work is diagnostic, not promotion.

Candidate work:

- standard epsilon sweep summaries for generator fitting
- full singular-value and condition-number diagnostics
- basis column scaling diagnostics
- KS fixture variants as non-gated evidence
- explicit classification of direct SVD, reference fallback, and mixed evidence

Recommended as an internal diagnostic track feeding future promotion decisions.

### D. CI, Release, and API Supportability

`v0.10` already consolidated release-gate CI, but this remains important for v1.0 readiness.

Candidate work:

- keep one current release gate
- keep package smoke compact and representative
- continue API stability audit tests
- maintain root/submodule export guards
- keep package-index publishing deferred until the project is ready for v1.0 policy

Recommended as M6 release hardening, not as the primary feature theme.

## Paper-agnostic Utilities for Orbit Augmentation Work

The private downstream result suggests that coverage-mediated translation-orbit augmentation
can improve sparse PDE recovery under localized observations. The reusable pieces that may
belong in `pdelie` are the generic mechanics, not the experiment policy.

Good candidates for `pdelie`:

- `FieldBatch` finite-transform views that expose transformed data without changing the
  original canonical object.
- Translation-orbit coverage diagnostics for periodic `x` windows.
- Generic augmentation provenance helpers that record operation type, parameters, and
  source batch identity.
- Standard runtime summaries for branch-level residual, fit, verification, and coverage
  results.
- Finite-transform consistency checks that verify shape, coordinates, metadata, and
  residual behavior after a transform.

Likely downstream-only:

- branch naming tied to a private experiment
- manuscript-specific success labels or thresholds
- sparse-regression policy decisions
- train/test split policy for a particular benchmark
- automatic augmentation recipes tuned to one dataset

`v0.12` should consider only the reusable diagnostics and read-only orbit views first.
Train-only augmentation APIs should wait until the boundary between reusable library logic
and downstream experiment policy is clearer.

## Recommended V0.12 Milestone Sequence

### M0: Scope Freeze for Diagnostics and Orbit Supportability

Public API changes: none.

Tests:

- docs consistency checks
- no runtime tests required

Docs:

- add `V0_12_SCOPE.md`
- reset `PLAN.md`
- update `ROADMAP.md` to make `v0.12` committed only after scope is frozen

Out of scope:

- stable KS generator/residual promotion
- new PDEs
- weak KS
- broad adapters
- public augmentation policy APIs

### M1: Fit and Verification Diagnostic Semantics Freeze

Public API changes: none.

Tests:

- docs-only validation

Docs:

- freeze summary fields for fit diagnostics:
  - singular values
  - condition number
  - basis delta norms
  - column norms or scaling diagnostics
  - selected span distance
  - SVD span distance
  - fallback status and stable fallback category
  - epsilon sweep structure
- decide whether later APIs live under `pdelie.reporting` or remain internal summaries

Out of scope:

- algorithm changes to fitting
- KS promotion
- manuscript-specific tables or labels

### M2: Fit Diagnostic Implementation

Public API changes: possible, only if M1 freezes a narrow `pdelie.reporting` helper.

Candidate API:

- `pdelie.reporting.summarize_generator_fit_diagnostics(...)`

Tests:

- Heat, Burgers, KdV fit summaries remain JSON-compatible
- KS internal fit diagnostics expose singular values and condition number
- fallback reasons remain stable categories
- no input mutation

Docs:

- update `API_STABILITY.md` only if a public reporting helper lands
- update `PLAN.md`

Out of scope:

- changing fitter selection behavior
- adding KS runtime APIs

### M3: KS Diagnostic Sweep Harness

Public API changes: none.

Tests:

- internal KS epsilon sweep remains bounded and deterministic
- sweep records selected span distance, SVD span distance, fallback status, first
  verification error, singular values, and condition number when available
- sweep is not a release gate for promotion

Docs:

- record whether conditioning evidence explains the no-go
- keep KS public promotion deferred unless direct evidence changes

Out of scope:

- stable KS generator/residual APIs
- making KS fixture variants public

### M4: Orbit Coverage Diagnostic Feasibility

Public API changes: possible only if M1/M2 show a stable, paper-agnostic shape.

Candidate API direction:

- reporting-only coverage summaries before mutation or augmentation APIs

Tests:

- periodic `x` window coverage metrics on canonical `FieldBatch`
- finite-transform consistency diagnostics on Heat/KdV fixtures
- provenance summaries are JSON-compatible

Docs:

- define what is reusable library behavior versus downstream experiment policy

Out of scope:

- PDEBench/The Well
- multidimensional grids
- private sparse-discovery branch logic
- automatic train augmentation recipes

### M5: Public-surface and API Stability Audit

Public API changes: none unless M2/M4 landed public reporting helpers.

Tests:

- API stability audit
- public export guards
- no KS public generator/residual/example exports
- no weak KS or weak derivative expansion

Docs:

- update `API_STABILITY.md` for any reporting APIs that landed
- record no new PDE scope

Out of scope:

- CI restructuring beyond current release-gate hygiene

### M6: Release Gate and Readiness

Public API changes: none.

Tests:

- compact `v0_12-release-gate`
- full suite
- build
- clean wheel smoke
- Heat and KdV example smokes

Docs:

- README, changelog, release readiness, roadmap, package metadata
- direct Git-tag release path

Out of scope:

- package-index publishing before v1.0 policy is finalized
- stable KS promotion unless a separate M5 decision changes the scope

## Docs Consistency Audit

Audit result:

- `ROADMAP.md` does not imply stable KS promotion after the `v0.11` no-go. It keeps
  future work conditional.
- `API_STABILITY.md` documents the `max_spatial_order=4` derivative extension and does
  not document stable KS generator or residual APIs.
- `README.md`, `CHANGELOG.md`, and `docs/releases/V0_11_RELEASE_READINESS.md` describe
  `v0.11` as KS feasibility/no-go evidence, not stable KS runtime support.
- public KS generator, residual, example, and root exports remain absent.
- `v0.12+` planning remains conditional before M0.

No consistency fixes were required during this audit.
