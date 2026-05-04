# V0.26 Scope - KS Revisit Decision, Promotion Deferred to V0.26b

**Status:** COMPLETE

## Summary

`v0.26` is a Kuramoto-Sivashinsky revisit decision release.

It revisits the `v0.11`/`v0.12` KS no-go with modern confidence diagnostics, but does not promote public KS runtime APIs.

Stable investigation path:

```text
internal normalized KS fixture
-> spectral_fd derivatives through u_xxxx
-> internal KS residual feasibility
-> translation fit / verification / confidence report
-> explicit v0.26 decision label
```

Release conclusion:

```text
current_no_go_reference_fallback
```

KS remains deferred because the primary frozen fixture still relies on reference-fallback translation fitting. Public KS promotion, if justified later, is reserved for a separate `v0.26b` scope freeze.

## Decision Labels

- `current_no_go_reference_fallback`: residual and verification evidence are feasible, but direct residual-based SVD fitting still drifts and requires reference fallback.
- `residual_feasible_fit_not_promotable`: residual and verification evidence pass, but fit evidence is not promotable.
- `direct_strong_candidate_for_v0_26b_promotion`: the frozen primary fixture passes direct-SVD/no-fallback criteria and may justify opening `v0.26b`.
- `deferred_no_go`: core evidence is not sufficient for either residual feasibility or future promotion candidacy.

## Frozen Decision Criteria

Promotion candidacy in `v0.26` requires all of:

- residual max `< 5e-2`
- residual RMS `< 1e-2`
- first verification error `< 5e-4`
- verification classification not `failed`
- selected/SVD span distance within frozen tolerance
- fit evidence label `direct_svd_in_tolerance`
- `reference_fallback_used is False`

`confidence_label == "strong"` is necessary but not sufficient for future promotion. Direct SVD in tolerance and `reference_fallback_used is False` are required.

## Minimal KS Reproduction Matrix

`v0.26` records test-only evidence for:

- frozen primary fixture
- one seed sweep
- one fit-epsilon sweep
- one resolution variant
- fit/fallback diagnostics
- verification diagnostics
- generator confidence report

All matrix variants are diagnostic-only. Promotion evidence must come from the frozen primary fixture, not from the best-performing variant in a sweep.

## V0.26b Follow-Up Contract

`v0.26b` is reserved for the actual KS promotion release if a future scope freeze accepts the `direct_strong_candidate_for_v0_26b_promotion` evidence.

Candidate `v0.26b` surface, if opened later:

- KS data generator under `pdelie.data`
- KS residual evaluator under `pdelie.residuals`
- KS vertical-slice example under `pdelie.examples`

No weak KS, custom KS coefficients, custom KS initial conditions, broad KS regimes, or root exports are included unless explicitly frozen in `v0.26b`.

## Explicit Non-goals

- no public KS data generator
- no public KS residual evaluator
- no public KS vertical-slice example
- no public KS status example
- no residual-only KS API
- no weak KS API
- no custom KS initial-condition API
- no configurable KS coefficient API
- no broad KS regime support
- no root KS export
- no broad adapters or file loaders
- no multidimensional or nonuniform stable support
- no time-translation APIs
- no neural or callable generator APIs
- no operator-facing APIs

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

## Release Gate

`v0.26` is complete only if:

- the primary KS fixture records `current_no_go_reference_fallback`
- residual and verification evidence remain feasible but fit evidence remains fallback-backed
- the confidence report is included and does not override the direct-SVD/no-fallback rule
- minimal matrix evidence remains diagnostic-only
- no best-of-sweep promotion path exists
- no public KS runtime API, weak KS API, status example, or root KS export lands
- `API_STABILITY.md` records the decision-only status without adding stable KS runtime contracts
- CI uses one compact current release gate plus full editable tests and package smoke
- package-index publishing remains deferred until `v1.0` or later
