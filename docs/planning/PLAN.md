# PDELie - Execution Plan (V0.15)

## Current Release Status

**V0.15 is complete as materialized uniform translation orbit batches**

This file is the completed execution record for the `v0.15` release series.

Committed release theme:

`canonical scalar 1D periodic FieldBatch + finite uniform x-shifts -> materialized orbit FieldBatch + JSON-compatible provenance report`

The important release boundary is:

> v0.15 adds one conservative data utility for materializing uniform translation orbit batches. It does not add train/test policy, split management, time translation, new PDEs, KS promotion, weak KS, broad adapters, operator APIs, or root exports.

This file should not redefine package contracts.
Contracts and stable behavior belong in:

- `docs/specs/SPEC.md`
- `docs/specs/CONTRACTS_AND_DEFAULTS.md`
- `docs/specs/API_STABILITY.md`
- `docs/planning/ROADMAP.md`
- `docs/planning/V0_15_SCOPE.md`

`API_STABILITY.md` was updated when the public `v0.15` orbit-batch helper landed.

---

## V0.14 Closeout

`v0.14` is complete as invariant workflow summaries and read-only uniform translation orbit reports.

Completed outcome:

- public `pdelie.reporting.summarize_invariant_workflow(...)`
- public `pdelie.invariants.summarize_uniform_translation_orbit(...)`
- JSON-only invariant workflow summary example
- no augmented datasets or transformed `FieldBatch` collections from reporting helpers
- compact `v0_14-release-gate`

`v0.15` begins from that read-only diagnostic/reporting surface and promotes only a narrow, provenance-rich materialization helper.
It does not promote train/test policy, split management, time translation, or KS runtime APIs.

---

## Milestone 0 - Scope Freeze

**Status:** COMPLETE

### Goal

Freeze `v0.15` as materialized uniform translation orbit batches.

### Completed Outcome

- added `docs/planning/V0_15_SCOPE.md`
- reset `PLAN.md` as the active `v0.15` execution record
- updated `ROADMAP.md` to record `v0.15` as the current completed data-utility release
- recorded explicit non-goals:
  - no train/test policy
  - no split management
  - no heldout-leakage detection
  - no time-translation API
  - no KS promotion
  - no new PDE
  - no broad adapters
  - no root export expansion

---

## Milestone 1 - API Semantics Freeze

**Status:** COMPLETE

### Goal

Freeze materialization semantics before implementation.

### Completed Outcome

M1 froze:

- public submodule-only API name:
  - `pdelie.invariants.build_uniform_translation_orbit_batch(...)`
- runtime-only structured return:
  - `pdelie.invariants.OrbitBatchResult`
- `OrbitBatchResult` is not a canonical object and has no schema migration policy
- canonical scalar 1D uniform periodic `FieldBatch` scope
- non-empty finite shift sequence
- shift-major output ordering
- duplicate-shift preservation
- output batch size equals `source_batch_size * len(shifts)`
- optional `source_field_id` as JSON-compatible provenance metadata only
- optional source and shift index recording
- mask concatenation along batch
- one aggregate `materialize_uniform_translation_orbit_batch` preprocess entry
- `orbit_materialization` metadata on the output field
- `copy=False` may avoid extra coordinate or mask copies where safe, but inputs are never mutated

---

## Milestone 2 - Orbit Batch Implementation

**Status:** COMPLETE

### Goal

Add the materialized uniform translation orbit batch helper under `pdelie.invariants`.

### Completed Outcome

- added public submodule-only helper:
  - `pdelie.invariants.build_uniform_translation_orbit_batch(...)`
- added runtime-only structured return:
  - `pdelie.invariants.OrbitBatchResult`
- implementation reuses existing `InvariantApplier`
- output `FieldBatch` appends along batch in shift-major order
- report records:
  - source/output shapes
  - raw and normalized shifts
  - source/shift indices when requested
  - batch records
  - transform specs
  - metadata/preprocess provenance
- documented the API in `docs/specs/API_STABILITY.md`

---

## Milestone 3 - Compatibility And Diagnostics

**Status:** COMPLETE

### Goal

Verify materialized orbit batches remain compatible with existing stable numerical paths.

### Completed Outcome

- verified materialized Heat orbit batches validate as `FieldBatch` objects
- verified materialized KdV orbit batches validate as `FieldBatch` objects
- verified derivatives run on representative materialized Heat and KdV batches
- verified Heat and KdV residual diagnostics remain finite
- verified duplicate shifts remain traceable through provenance
- verified input fields are not mutated
- verified masks are concatenated consistently with transformed fields

---

## Milestone 4 - Example

**Status:** COMPLETE

### Goal

Add a compact JSON-only example for materialized orbit batches.

### Completed Outcome

- added `python -m pdelie.examples.translation_orbit_batch`
- added `pdelie.examples.run_translation_orbit_batch_example(...)`
- example demonstrates:
  - Heat orbit batch materialization
  - KdV orbit batch materialization
  - source/output shape growth
  - duplicate-shift preservation
  - source/shift provenance
  - residual sanity on the materialized batches
- example output remains a runtime smoke summary, not a canonical artifact schema
- root `pdelie` remains unchanged

---

## Milestone 5 - API / Public-surface Audit

**Status:** COMPLETE

### Goal

Verify public surface and documentation match the frozen `v0.15` scope.

### Completed Outcome

- confirmed `pdelie.invariants.build_uniform_translation_orbit_batch(...)` is submodule-only
- confirmed `pdelie.invariants.OrbitBatchResult` is submodule-only
- confirmed root `pdelie` exports remain unchanged
- confirmed no train/test policy landed
- confirmed no split-management or leakage-detection helper landed
- confirmed no time-translation API landed
- confirmed public KS generator/residual/example APIs remain absent
- confirmed weak KS remains absent
- confirmed broad adapters remain absent
- confirmed `API_STABILITY.md` documents the new helper and does not document deferred surfaces

---

## Milestone 6 - Release Gate and Readiness

**Status:** COMPLETE

### Goal

Close the release with compact gate coverage, metadata, docs, and direct Git-tag readiness.

### Completed Outcome

- added compact `tests/test_v0_15_release_gate.py`
- updated CI so the current explicit release gate is `v0_15-release-gate`
- retained full editable tests and package smoke
- added compact package-smoke coverage for the new orbit-batch helper
- bumped package metadata to `0.15.0`
- updated README and changelog for `v0.15`
- added `docs/releases/V0_15_RELEASE_READINESS.md`
- updated publishing docs to keep `v0.15.0` Git-tag-only
- moved `v0.15` into completed release context in `ROADMAP.md`
- kept PyPI/TestPyPI deferred until `v1.0` or later

### Direct Tag Path

Before tagging `v0.15.0`:

- run full local tests
- build sdist and wheel
- run clean wheel smoke
- run Heat, KdV, orbit/coverage, invariant-workflow, and translation-orbit-batch example modules
- confirm CI checks pass:
  - `v0_15-release-gate`
  - `editable-tests`
  - `package-smoke`
- tag the merged main commit as `v0.15.0`
- do not publish to TestPyPI
- do not publish to PyPI

---

## Explicit Non-goals Preserved

`v0.15` did not add:

- train/test policy
- split management
- heldout-leakage detection
- sparse-discovery branch policy
- private-paper augmentation recipes
- time-translation APIs
- new PDE support
- stable KS runtime support
- weak KS
- broad adapters
- PDEBench or The Well support
- multidimensional, multivariable, or nonuniform-grid expansion
- operator-facing APIs
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
