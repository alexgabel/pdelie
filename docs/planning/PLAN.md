# PDELie - Execution Plan (V0.26)

**Status:** COMPLETE

**V0.26 is complete as the KS revisit decision release**

This file is the completed execution record for the `v0.26` release series.

## Release Theme

`v0.26` revisits the Kuramoto-Sivashinsky no-go with modern confidence diagnostics while keeping public KS runtime promotion out of scope.

Decision label:

```text
current_no_go_reference_fallback
```

Stable investigation path:

```text
internal normalized KS fixture
-> spectral_fd derivatives through u_xxxx
-> internal KS residual feasibility
-> translation fit / verification / confidence report
-> explicit v0.26 decision label
```

The release adds no public KS data generator, residual evaluator, vertical-slice example, status example, weak KS API, residual-only API, or root export.

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

Authoritative scope:

- `docs/planning/V0_26_SCOPE.md`

`API_STABILITY.md` records the decision-only status but does not add a stable KS runtime contract.

## Milestone 0 - Scope Freeze

Freeze `v0.26` as a KS revisit decision release.

Closeout:

- added `docs/planning/V0_26_SCOPE.md`
- reset `PLAN.md` as the active `v0.26` execution record
- updated `ROADMAP.md` to record `v0.26` as the current completed release
- reserved `v0.26b` as the follow-up KS promotion release name
- explicitly kept KS runtime APIs out of `v0.26`

## Milestone 1 - Decision Criteria Freeze

Frozen decision labels:

- `current_no_go_reference_fallback`
- `residual_feasible_fit_not_promotable`
- `direct_strong_candidate_for_v0_26b_promotion`
- `deferred_no_go`

Frozen promotion-candidate thresholds:

- residual max `< 5e-2`
- residual RMS `< 1e-2`
- first verification error `< 5e-4`
- verification classification not `failed`
- fit evidence label `direct_svd_in_tolerance`
- `reference_fallback_used is False`

Promotion evidence must come from the frozen primary fixture. Diagnostic variants cannot define promotion.

## Milestone 2 - Minimal KS No-Go Reproduction Matrix

Implemented test-only diagnostic coverage for:

- frozen primary fixture
- seed sweep
- fit-epsilon sweep
- one resolution variant
- fit/fallback diagnostics
- verification diagnostics
- generator confidence report

No helper was exported from `pdelie.data`, `pdelie.residuals`, `pdelie.examples`, or root `pdelie`.

## Milestone 3 - Primary Fixture Strong-Path Re-Evaluation

The frozen primary fixture remains:

- residual-feasible
- verification-feasible
- reference-fallback-backed for translation fitting

The direct SVD path is not promotable in `v0.26`.

## Milestone 4 - Optional Variant Diagnostics

Variant diagnostics remain test-only and diagnostic-only.

Closeout:

- no best-of-sweep promotion path was added
- variants may inform future work only
- `v0.26b` remains a separate scope decision if future evidence justifies promotion

## Milestone 5 - Decision Docs

Docs now state:

- KS remains deferred in `v0.26`
- residual feasibility is not enough for public PDELie support
- public KS promotion requires a separate `v0.26b` scope freeze
- weak KS remains deferred

No packaged KS runtime/status example was added.

## Milestone 6 - Release Gate And Readiness

Implemented:

- added compact `tests/test_v0_26_release_gate.py`
- updated CI so the current explicit release gate is `v0_26-release-gate`
- kept full editable `python -m pytest`
- kept package smoke
- bumped package metadata to `0.26.0`
- updated README, changelog, publishing notes, roadmap, and release readiness docs
- documented direct `v0.26.0` Git-tag release path

Required checks before tagging:

- `v0_26-release-gate`
- `editable-tests`
- `package-smoke`

Local validation checklist:

- `python -m pytest`
- `python -m build --sdist --wheel`
- all packaged examples
- `python scripts/check_notebooks.py`
- `git diff --check`
