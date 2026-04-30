# V0.12 Scope Freeze

## Summary

`v0.12` is the diagnostics and supportability hardening release for `pdelie`.

Its purpose is:

> harden diagnostics and reporting around generator fitting, verification, and orbit/coverage supportability without adding new numerical scope.

Committed release theme:

`existing stable Heat/Burgers/weak-report/KdV/reporting surfaces -> fit and verification diagnostics -> orbit/coverage reporting feasibility -> release supportability`

`v0.12` does not add a new PDE and does not promote Kuramoto-Sivashinsky runtime APIs.
The `v0.11` KS evidence remains internal feasibility/no-go evidence.

---

## Motivation From V0.11 KS No-go

`v0.11` added the public order-4 derivative backend extension:

```python
compute_spectral_fd_derivatives(field, *, max_spatial_order=4)
```

It also evaluated normalized scalar 1D periodic Kuramoto-Sivashinsky internally.
The result was useful but not strong enough for public runtime promotion:

- KS residual feasibility passed with large margin
- mass drift passed with large margin
- held-out canonical translation verification passed
- vertical-slice evidence passed through `reference_fallback`
- direct residual-based SVD fitting was out of tolerance
- direct SVD span distance was around `0.418`
- stable KS generator/residual/example promotion was deferred

The main supportability gap is diagnostic, not PDE coverage:

- fit diagnostics do not expose full singular values
- fit diagnostics do not expose condition number
- epsilon sensitivity is not standardized
- fallback-backed versus direct-fit evidence needs clearer reporting
- orbit/coverage diagnostics are not yet reusable library utilities

`v0.12` should address those supportability gaps before any further numerical expansion.

---

## Stable Scope

The stable scope carried into `v0.12` remains:

- canonical `FieldBatch`, `DerivativeBatch`, `ResidualBatch`, `GeneratorFamily`, `InvariantMapSpec`, and `VerificationReport`
- uniform rectilinear scalar 1D stable paths
- Heat and Burgers strong-form paths
- frozen `v0.8` weak Heat/Burgers residual report APIs
- frozen `v0.9` normalized periodic short-horizon KdV strong path
- frozen `v0.10` supportability reporting helpers under `pdelie.reporting`
- frozen `v0.11` order-4 spectral derivative extension
- existing polynomial translation fitting and finite-transform verification

The new `v0.12` scope is supportability around those existing surfaces:

- generator-fit diagnostic semantics
- verification diagnostic semantics
- reporting helper hardening, if public helper names are frozen in M1/M2
- internal KS diagnostic sweep reporting, without promotion
- orbit/coverage diagnostic feasibility, without augmentation APIs in M0
- API/public-surface audit and compact release-gate coverage

---

## Non-goals

`v0.12` explicitly does not include:

- a new PDE
- stable KS generator promotion
- stable KS residual evaluator promotion
- stable KS vertical-slice example promotion
- KS imported parity
- weak KS
- weak derivative expansion
- broad dataset adapters
- PDEBench or The Well support
- multidimensional grids
- nonuniform grids
- multivariable systems
- custom KS initial-condition APIs
- configurable KS coefficient families
- neural generators
- operator-facing symmetry work
- manuscript-specific experiment policy
- private-paper branch logic
- private-paper thresholds, tables, figures, or labels
- public orbit augmentation utilities in M0
- public reporting helpers in M0
- root `pdelie` export expansion unless a later milestone explicitly accepts it

---

## Candidate Public API Policy

M0 lands no public API.

If `v0.12` lands public APIs later, they must be reporting or diagnostic helpers only.
Candidate public APIs must be frozen in M1 before implementation in M2 or M4.

Likely allowed API direction:

- submodule-only helpers under `pdelie.reporting`
- JSON-compatible runtime summaries
- diagnostic reports over existing canonical objects and runtime reports
- no new canonical object unless a later milestone proves it is necessary

Likely rejected API direction:

- root `pdelie` exports
- stable KS generator/residual APIs
- broad adapter APIs
- manuscript-table or figure APIs
- mutation-heavy augmentation APIs
- downstream sparse-discovery experiment policy

`docs/specs/API_STABILITY.md` remains unchanged in M0.
It should change only if M2 or M4 actually lands a public reporting/diagnostic API.

---

## M1 Fit and Verification Diagnostic Semantics Freeze

M1 freezes one future M2 public reporting helper:

```python
pdelie.reporting.summarize_generator_fit_diagnostics(
    generator: GeneratorFamily,
) -> dict[str, Any]
```

Public helper policy:

- helper lives under `pdelie.reporting` only
- no root `pdelie` export
- input is a `GeneratorFamily`
- output is a JSON-compatible plain Python dict
- summary type is `generator_fit_diagnostics`
- summary schema version is `"0.1"`
- wrong input type raises the existing typed schema validation error in M2
- helper summarizes existing and future `GeneratorFamily.diagnostics`
- helper does not create a canonical object
- helper does not mutate inputs

Frozen generator-fit diagnostic fields for M2:

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

Diagnostic conventions:

- `condition_number = largest_singular_value / smallest_singular_value`
- if the denominator is zero or nonfinite, report `condition_number = None`
- `fallback_reason` is a stable category string, not prose
- current stable fallback category remains `svd_translation_span_drift`
- `evidence_label` categories are:
  - `direct_svd_in_tolerance`
  - `direct_svd_out_of_tolerance`
  - `reference_fallback`
  - `mixed`
  - `unavailable`

Verification diagnostic semantics:

- `pdelie.reporting.summarize_verification_report(...)` remains the verification summary surface
- M2 may harden top-level verification summary fields for transform, span, and batch-error diagnostics if needed
- M1 and M2 do not change verification classification rules
- M1 and M2 do not change finite-transform behavior

M3 internal KS sweep semantics:

- internal KS sweeps record epsilon, fit mode, fallback status/reason, selected span, SVD span, first verification error, classification, singular values, and condition number
- sweeps are diagnostic artifacts, not promotion gates

`API_STABILITY.md` remains unchanged in M1.
It should be updated in M2 only if `summarize_generator_fit_diagnostics(...)` lands as public runtime API.

---

## Milestones

### Milestone 0 - Scope Freeze

Freeze `v0.12` as diagnostics and supportability hardening, add this scope document, reset `PLAN.md`, and update `ROADMAP.md`.

M0 is docs-only.
It does not change runtime code, tests, package metadata, README, changelog, release readiness, or API stability docs.

### Milestone 1 - Fit / Verification Diagnostic Semantics Freeze

Freeze diagnostic semantics before implementation.

Completed decisions:

- future M2 helper is `pdelie.reporting.summarize_generator_fit_diagnostics(...)`
- helper is submodule-only and returns a JSON-compatible runtime dict
- summary type is `generator_fit_diagnostics`
- summary schema version is `"0.1"`
- fit diagnostic fields, condition-number policy, fallback category policy, and evidence labels are frozen above
- verification keeps `summarize_verification_report(...)` as its public summary surface
- M3 KS sweep semantics are diagnostic-only and not promotion gates

### Milestone 2 - Diagnostic / Reporting Helper Implementation

Implement the M1-frozen diagnostics.

Completed implementation:

- added `pdelie.reporting.summarize_generator_fit_diagnostics(...)`
- enriched translation-fit diagnostics with singular values, condition number, design column norms, selected coefficients, selected span distance, and evidence label
- updated `API_STABILITY.md` for the new public reporting helper
- kept fitting coefficient selection unchanged
- kept existing reporting summary shapes unchanged except for the new helper
- kept KS public runtime APIs absent

### Milestone 3 - Internal KS Diagnostic Sweep Harness

Keep KS internal and diagnostic-only.

Completed scope:

- bounded epsilon sweeps
- selected span distance
- SVD span distance
- fallback status and reason
- first verification error
- singular values and condition number from the M2 fit diagnostics
- no promotion gate

Completed sweep matrix:

- epsilons: `1e-5`, `3e-5`, `1e-4`, `3e-4`, `1e-3`
- variants:
  - `default`
  - `lower_amplitude` with `amplitude=0.04`
  - `shorter_time` with `max_time=0.1`

Completed diagnosis:

- all frozen variants concluded `fallback_stable_across_epsilons`
- no epsilon or cheap fixture variant recovered direct SVD in-tolerance behavior
- fallback reason was stable as `svd_translation_span_drift`
- residual and verification evidence remained healthy
- relative L2 drift remained diagnostic-only
- no public KS generator, residual evaluator, example, imported parity, weak API, or root export landed

### Milestone 4 - Orbit / Coverage Diagnostic Feasibility

Evaluate paper-agnostic orbit and coverage diagnostics.

Completed direction:

- internal test-only periodic `x` coverage diagnostics
- internal test-only finite-transform consistency diagnostics
- deterministic JSON-compatible summary output
- no artifact files by default
- no public API promotion

Completed evidence:

- half-coverage quarter-shift case covered `32 / 64` points with coverage fraction `0.5`
- full-coverage quarter-shift case covered `64 / 64` points with coverage fraction `1.0`
- stable Heat and KdV fixtures preserved dims, coords, var names, metadata, and mask under uniform translations
- inverse-transform and period-wrap errors remained at floating-point noise levels
- residual RMS was stable under shifts for both fixtures
- transform provenance recorded `invariant_apply` and `uniform_translation`

M4 did not implement private-paper policy, train-augmentation recipes, public orbit/coverage helpers, or API stability entries.

### Milestone 5 - API / Public-surface Audit

Audit API stability and public exports after any M2/M4 helper decisions.

Completed checks:

- `API_STABILITY.md` matches actual public helper surface
- root exports remain narrow
- KS generator/residual/example APIs remain absent
- weak KS remains absent
- broad adapters remain absent
- M4 orbit/coverage diagnostics remain internal test-only helpers
- no public augmentation utilities landed
- `API_STABILITY.md` required no update in M5

### Milestone 6 - Release Gate and Readiness

Add compact `v0_12-release-gate`, align release-facing docs and package metadata, and close the direct Git-tag release path.

Release-gate expectations stay representative:

- current release gate is compact
- full editable tests cover historical gates
- package smoke remains small
- no KS promotion claims
- no PyPI or TestPyPI publishing before the v1.0 publishing policy is accepted

Milestone 6: COMPLETE.

Completed closeout:

- package metadata is aligned with `0.12.0`
- release-facing docs are aligned with `v0.12.0`
- CI exposes one compact current `v0_12-release-gate`
- full editable tests remain the historical gate coverage
- package smoke remains compact and includes a tiny generator-fit diagnostic summary check
- `API_STABILITY.md` remains aligned and required no M6 change
- M3 internal KS diagnostics and M4 orbit/coverage diagnostics remain internal

---

## Relationship to Downstream Orbit-augmentation Work

Downstream work has shown that coverage-mediated translation-orbit augmentation can help sparse PDE recovery under localized observations.

The reusable `pdelie` candidates are the generic mechanics:

- finite-transform or orbit views over canonical `FieldBatch`
- periodic `x` window coverage diagnostics
- generic augmentation provenance summaries
- runtime summaries for residual, fit, verification, and coverage results
- finite-transform consistency checks

The downstream-only pieces remain outside `pdelie`:

- manuscript-specific branch naming
- sparse-regression policy decisions
- dataset-specific train/test policy
- paper-specific thresholds and labels
- automatic augmentation recipes tuned to one experiment

`v0.12` may evaluate reusable diagnostics for this direction.
It must not implement private-paper experiment policy.

---

## Release-gate Expectations

The eventual `v0_12-release-gate` should be compact and representative.
It should not duplicate full diagnostic, reporting, KS, or historical release-gate suites.

Expected release-gate shape:

- public reporting/diagnostic APIs exist only if frozen and implemented in M2/M4
- root export boundaries remain intact
- stable Heat/Burgers/weak-report/KdV surfaces remain importable
- order-4 derivative API remains documented and available
- public KS generator/residual/example APIs remain absent
- no weak KS API appears
- examples remain JSON-compatible runtime summaries
- package smoke remains small and avoids KS internal feasibility sweeps

Historical release-gate tests should remain runnable locally and covered by the full editable test suite.

---

## Status

- `v0.11`: COMPLETE as KS feasibility/no-go closeout
- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE
