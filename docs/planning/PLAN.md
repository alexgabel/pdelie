# PDELie - Execution Plan (V0.14)

## Current Release Status

**V0.14 is complete as invariant workflow summaries and read-only translation orbit reports**

This file is the completed execution record for the `v0.14` release series.

Committed release theme:

`FieldBatch + uniform x-translation shifts + optional windows + residual/fit/verification outputs -> read-only orbit report + combined invariant workflow summary`

The important release boundary is:

> v0.14 adds read-only runtime reports, not augmented datasets, transformed FieldBatch collections, orbit datasets, or time-translation support.

This file should not redefine package contracts.
Contracts and stable behavior belong in:

- `docs/specs/SPEC.md`
- `docs/specs/CONTRACTS_AND_DEFAULTS.md`
- `docs/specs/API_STABILITY.md`
- `docs/planning/ROADMAP.md`
- `docs/planning/V0_14_SCOPE.md`

`API_STABILITY.md` was updated when the two public `v0.14` reporting/invariant helpers landed.

---

## V0.13 Closeout

`v0.12` is complete as diagnostics and supportability hardening.

`v0.13` is complete as public orbit and coverage diagnostics.

Completed outcome:

- public `pdelie.invariants.compute_periodic_window_coverage(...)`
- public `pdelie.invariants.diagnose_uniform_translation_consistency(...)`
- JSON-only orbit/coverage diagnostics example
- no public augmentation utilities or orbit-view builders
- compact `v0_13-release-gate`

`v0.14` begins from that diagnostic evidence and promotes only read-only workflow summaries and orbit reports.
It does not promote augmentation policy, transformed datasets, time translation, or KS runtime APIs.

---

## Milestone 0 - Scope Freeze

**Status:** COMPLETE

### Goal

Freeze `v0.14` as invariant workflow summaries plus read-only uniform translation orbit reports.

### Completed Outcome

- added `docs/planning/V0_14_SCOPE.md`
- reset `PLAN.md` as the active `v0.14` execution record
- updated `ROADMAP.md` to record `v0.14` as the current completed supportability release
- recorded explicit non-goals:
  - no augmented datasets
  - no transformed `FieldBatch` collections
  - no orbit dataset builders
  - no time-translation API
  - no KS promotion
  - no new PDE
  - no broad adapters
  - no root export expansion

---

## Milestone 1 - API Semantics Freeze

**Status:** COMPLETE

### Goal

Freeze report schemas and semantics before implementation.

### Completed Outcome

For `summarize_uniform_translation_orbit(...)`, M1 froze:

- canonical scalar 1D uniform periodic `FieldBatch` scope
- read-only report output
- no returned transformed `FieldBatch` objects
- no input mutation
- raw shift order and duplicate shifts are preserved
- optional `source_field_id` is JSON-compatible provenance metadata only
- optional windows reuse `v0.13` periodic-window coverage semantics
- optional residual evaluator reuses `v0.13` translation-consistency semantics
- per-shift transform spec and provenance summaries are reported

For `summarize_invariant_workflow(...)`, M1 froze:

- JSON-compatible runtime summary output
- nested coverage, consistency, orbit, generator, fit, and verification summaries
- canonical `GeneratorFamily` and `VerificationReport` inputs are summarized through existing reporting helpers
- existing `v0.10` and `v0.12` reporting schemas remain unchanged

Time translation remains deferred.

---

## Milestone 2 - Combined Invariant Workflow Summary

**Status:** COMPLETE

### Goal

Add the combined workflow report helper under `pdelie.reporting`.

### Completed Outcome

- added public submodule-only helper:
  - `pdelie.reporting.summarize_invariant_workflow(...)`
- supports:
  - `periodic_window_coverage` reports
  - `uniform_translation_consistency` reports
  - `uniform_translation_orbit` reports
  - `GeneratorFamily` objects or `generator_family` summaries
  - `VerificationReport` objects or `verification_report` summaries
  - `GeneratorFamily` objects or `generator_fit_diagnostics` summaries for fit diagnostics
  - optional extra metrics
- returns `summary_type = "invariant_workflow"`
- creates no canonical object and mutates no inputs
- documented the API in `docs/specs/API_STABILITY.md`

---

## Milestone 3 - Uniform Translation Orbit Report

**Status:** COMPLETE

### Goal

Add the read-only uniform translation orbit report under `pdelie.invariants`.

### Completed Outcome

- added public submodule-only helper:
  - `pdelie.invariants.summarize_uniform_translation_orbit(...)`
- returns `summary_type = "uniform_translation_orbit"`
- includes:
  - optional `source_field_id`
  - field shape and equation metadata
  - raw and normalized shifts
  - one transform spec and provenance summary per shift
  - optional coverage diagnostics
  - translation consistency diagnostics
  - orbit-level pass flags
- returns no transformed `FieldBatch` objects
- constructs no augmented dataset or orbit dataset
- documented the API in `docs/specs/API_STABILITY.md`

---

## Milestone 4 - Useful End-to-end Example

**Status:** COMPLETE

### Goal

Add a compact JSON-only example that combines the new report surfaces.

### Completed Outcome

- added `python -m pdelie.examples.invariant_workflow_summary`
- added `pdelie.examples.run_invariant_workflow_summary_example(...)`
- example combines:
  - Heat orbit/coverage/consistency diagnostics
  - KdV orbit/coverage/consistency diagnostics
  - generator fit diagnostics
  - verification summaries
  - combined invariant workflow summaries
- example output remains a runtime smoke summary, not a canonical artifact schema
- root `pdelie` remains unchanged

---

## Milestone 5 - API / Public-surface Audit

**Status:** COMPLETE

### Goal

Verify public surface and documentation match the frozen `v0.14` scope.

### Completed Outcome

- confirmed `pdelie.reporting.summarize_invariant_workflow(...)` is submodule-only
- confirmed `pdelie.invariants.summarize_uniform_translation_orbit(...)` is submodule-only
- confirmed root `pdelie` exports remain unchanged
- confirmed no public augmentation utilities landed
- confirmed no orbit dataset builder landed
- confirmed no time-translation API landed
- confirmed public KS generator/residual/example APIs remain absent
- confirmed weak KS remains absent
- confirmed broad adapters remain absent
- confirmed `API_STABILITY.md` documents the new helpers and does not document augmentation or time-translation APIs

---

## Milestone 6 - Release Gate and Readiness

**Status:** COMPLETE

### Goal

Close the release with compact gate coverage, metadata, docs, and direct Git-tag readiness.

### Completed Outcome

- added compact `tests/test_v0_14_release_gate.py`
- updated CI so the current explicit release gate is `v0_14-release-gate`
- retained full editable tests and package smoke
- added compact package-smoke coverage for the new workflow/orbit reports
- bumped package metadata to `0.14.0`
- updated README and changelog for `v0.14`
- added `docs/releases/V0_14_RELEASE_READINESS.md`
- updated publishing docs to keep `v0.14.0` Git-tag-only
- moved `v0.14` into completed release context in `ROADMAP.md`
- kept PyPI/TestPyPI deferred until `v1.0` or later

### Direct Tag Path

Before tagging `v0.14.0`:

- run full local tests
- build sdist and wheel
- run clean wheel smoke
- run Heat, KdV, orbit/coverage, and invariant-workflow example modules
- confirm CI checks pass:
  - `v0_14-release-gate`
  - `editable-tests`
  - `package-smoke`
- tag the merged main commit as `v0.14.0`
- do not publish to TestPyPI
- do not publish to PyPI

---

## Explicit Non-goals Preserved

`v0.14` did not add:

- new PDE support
- stable KS runtime support
- weak KS
- broad adapters
- PDEBench or The Well support
- multidimensional, multivariable, or nonuniform-grid expansion
- operator-facing APIs
- public augmentation utilities
- orbit dataset builders
- transformed `FieldBatch` collections from reporting helpers
- train-augmentation policy
- time-translation APIs
- root runtime exports

---

## Status Checklist

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE
