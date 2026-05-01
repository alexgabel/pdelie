# PDELie - Execution Plan (V0.13)

## Current Release Status

**V0.13 is complete as public orbit and coverage diagnostics**

This file is the completed execution record for the `v0.13` release series.

Committed release theme:

`canonical periodic 1D FieldBatch + uniform translation action -> grid-point coverage diagnostics + transform-consistency diagnostics -> compact example/release gate`

The important release boundary is:

> diagnostics support invariant/finite-transform workflows but do not construct augmented datasets.

This file should not redefine package contracts.
Contracts and stable behavior belong in:

- `docs/specs/SPEC.md`
- `docs/specs/CONTRACTS_AND_DEFAULTS.md`
- `docs/specs/API_STABILITY.md`
- `docs/planning/ROADMAP.md`
- `docs/planning/V0_13_SCOPE.md`

`API_STABILITY.md` was updated when the two public `pdelie.invariants` diagnostics landed.

---

## V0.12 Closeout

`v0.12` is complete as diagnostics and supportability hardening.

Completed outcome:

- public `pdelie.reporting.summarize_generator_fit_diagnostics(...)`
- richer translation-fit diagnostics without changing fitting behavior
- internal KS diagnostic sweep closeout with no stable KS promotion
- internal orbit/coverage feasibility evidence
- API/public-surface audit
- compact `v0_12-release-gate`

`v0.13` begins from that feasibility evidence and promotes only the reusable orbit/coverage diagnostics.
It does not promote augmentation policy or KS runtime APIs.

---

## Milestone 0 - Scope Freeze

**Status:** COMPLETE

### Goal

Freeze `v0.13` as a public diagnostics promotion release under `pdelie.invariants`.

### Completed Outcome

- added `docs/planning/V0_13_SCOPE.md`
- reset `PLAN.md` as the active `v0.13` execution record
- updated `ROADMAP.md` to record `v0.13` as the current completed diagnostics release
- recorded that the release adds diagnostics only:
  - no augmented datasets
  - no orbit-view builders
  - no KS promotion
  - no new PDE
  - no broad adapters
  - no private-paper experiment policy

---

## Milestone 1 - API Semantics Freeze

**Status:** COMPLETE

### Goal

Freeze the exact public semantics before implementation.

### Completed Outcome

For `compute_periodic_window_coverage(...)`, M1 froze:

- endpoint-excluded uniform periodic 1D grid convention
- inferred domain length as `len(x) * dx`
- endpoint-duplicated grid rejection
- grid-point coverage, not continuous interval measure
- `coverage_fraction = covered_grid_points / num_grid_points`
- half-open windows `[start, start + width)`
- modulo reduction for coordinates, starts, and shifts
- deterministic boundary tolerance `1e-12 * domain_length`
- duplicate shifts and repeated windows are allowed and counted
- repeated windows increase coverage counts but not covered point count
- max uncovered run is reported in grid points and physical length
- positive shift convention:
  - `coverage_convention = "preimage_of_fixed_window_under_translation"`
  - `shift_convention = "field_shift_then_fixed_window"`
  - point `x0` is covered when `(x0 + shift) mod domain_length` lies inside the fixed window

For `diagnose_uniform_translation_consistency(...)`, M1 froze:

- canonical scalar 1D uniform periodic `FieldBatch` scope
- use of `InvariantApplier` and uniform translation
- report-only behavior with no returned transformed `FieldBatch` objects
- no input mutation
- shift equal to domain length is identity-equivalent within tolerance
- dims, shape, coords, metadata, var names, and mask structure/content preservation checks
- preprocess-log equality is not required
- appended provenance checks for `operation == "invariant_apply"` and `construction_method == "uniform_translation"`
- inverse and period-wrap relative L2 error definitions
- residual RMS absolute/relative delta policy
- residual stability pass rule:
  - `absolute_delta <= 1e-8 or relative_delta <= 1e-6`
- evaluator failures are fatal typed validation errors when a residual evaluator is supplied

---

## Milestone 2 - Periodic Coverage Diagnostic

**Status:** COMPLETE

### Goal

Promote periodic-window coverage diagnostics from `v0.12` feasibility into runtime.

### Completed Outcome

- added public submodule-only helper:
  - `pdelie.invariants.compute_periodic_window_coverage(...)`
- returned JSON-compatible dicts with:
  - `summary_schema_version = "0.1"`
  - `summary_type = "periodic_window_coverage"`
  - domain length, inferred domain length, `dx`, grid point count
  - raw/normalized windows and shifts
  - coverage counts
  - covered point count and coverage fraction
  - min/max/mean coverage count
  - max uncovered run in grid points and physical length
- implemented typed validation for invalid grids, endpoint duplication, invalid windows, invalid shifts, and invalid domain lengths
- documented the API in `docs/specs/API_STABILITY.md`
- kept computation report-only:
  - no plotting
  - no augmentation
  - no `FieldBatch` mutation
  - no root export

---

## Milestone 3 - Translation Consistency Diagnostic

**Status:** COMPLETE

### Goal

Promote uniform-translation consistency diagnostics from `v0.12` feasibility into runtime.

### Completed Outcome

- added public submodule-only helper:
  - `pdelie.invariants.diagnose_uniform_translation_consistency(...)`
- validated canonical scalar 1D periodic `FieldBatch` inputs
- used existing `InvariantApplier` and `uniform_translation`
- returned JSON-compatible report dicts only
- returned no transformed `FieldBatch` objects
- did not mutate input fields
- supported optional residual evaluator behavior:
  - omitted residual evaluator leaves residual metrics as `None`
  - supplied residual evaluator failures remain fatal typed validation errors
- recorded structure flags, inverse/period-wrap errors, residual stability metrics, and appended provenance fields
- validated stable Heat and KdV fixtures
- documented the API in `docs/specs/API_STABILITY.md`
- kept KS out of the public diagnostics path

---

## Milestone 4 - Example and Reporting Alignment

**Status:** COMPLETE

### Goal

Add a compact runtime smoke example for the new diagnostics.

### Completed Outcome

- added `python -m pdelie.examples.orbit_coverage_diagnostics`
- added `pdelie.examples.run_orbit_coverage_diagnostics_example(...)`
- example output is JSON-only on stdout
- example demonstrates:
  - half-coverage and full-coverage periodic-window cases
  - uniform translation consistency on stable Heat and KdV fixtures
- example output remains a runtime smoke summary, not a canonical artifact schema
- root `pdelie` remains unchanged

---

## Milestone 5 - API / Public-surface Audit

**Status:** COMPLETE

### Goal

Verify public surface and documentation match the frozen `v0.13` scope.

### Completed Outcome

- confirmed `pdelie.invariants.compute_periodic_window_coverage(...)` is submodule-only
- confirmed `pdelie.invariants.diagnose_uniform_translation_consistency(...)` is submodule-only
- confirmed root `pdelie` exports remain unchanged
- confirmed no public augmentation utilities landed
- confirmed no public orbit-view builders landed
- confirmed public KS generator/residual/example APIs remain absent
- confirmed weak KS remains absent
- confirmed broad adapters remain absent
- confirmed `API_STABILITY.md` documents the new diagnostics and does not document augmentation or KS APIs

---

## Milestone 6 - Release Gate and Readiness

**Status:** COMPLETE

### Goal

Close the release with compact gate coverage, metadata, docs, and direct Git-tag readiness.

### Completed Outcome

- added compact `tests/test_v0_13_release_gate.py`
- updated CI so the current explicit release gate is `v0_13-release-gate`
- retained full editable tests and package smoke
- added compact package-smoke coverage for the new invariant diagnostics
- bumped package metadata to `0.13.0`
- updated README and changelog for `v0.13`
- added `docs/releases/V0_13_RELEASE_READINESS.md`
- updated publishing docs to keep `v0.13.0` Git-tag-only
- moved `v0.13` into completed release context in `ROADMAP.md`
- kept PyPI/TestPyPI deferred until `v1.0` or later

### Direct Tag Path

Before tagging `v0.13.0`:

- run full local tests
- build sdist and wheel
- run clean wheel smoke
- run Heat, KdV, and orbit/coverage example modules
- confirm CI checks pass:
  - `v0_13-release-gate`
  - `editable-tests`
  - `package-smoke`
- tag the merged main commit as `v0.13.0`
- do not publish to TestPyPI
- do not publish to PyPI

---

## Explicit Non-goals Preserved

`v0.13` did not add:

- a new PDE
- stable KS generator/residual/example APIs
- weak KS
- public augmentation utilities
- public orbit-view builders
- broad dataset adapters
- multidimensional or nonuniform grids
- operator-facing APIs
- private-paper experiment policy
- manuscript-specific thresholds, tables, figures, or labels
- root runtime exports

---

## Status

- `v0.12`: COMPLETE as diagnostics/supportability hardening
- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE
