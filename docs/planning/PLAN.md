# PDELie - Execution Plan (V0.10)

## Current Release Status

**V0.10 complete; ready for direct `v0.10.0` tag after release PR CI**

This file is the active execution record for the `v0.10` release series.

`v0.10` is a supportability and `v1.0` readiness release.
It hardens the existing Heat/Burgers/weak-report/KdV engine before any new numerical scope is added.

Stable release definition:

`existing stable Heat/Burgers/weak-report/KdV surfaces -> compact supportability reports -> consistent examples/release gates/docs -> v1.0 readiness`

This file should not redefine package contracts.
Contracts and stable behavior belong in:

- `docs/specs/SPEC.md`
- `docs/specs/CONTRACTS_AND_DEFAULTS.md`
- `docs/specs/API_STABILITY.md`
- `docs/planning/ROADMAP.md`
- `docs/planning/V0_10_SCOPE.md`

`API_STABILITY.md` was audited in M0 and remains unchanged because no new `v0.10` public API has landed yet.
It must be updated in the same milestone where any public reporting helper or other public API lands.

---

## V0.9 Closeout

`v0.9` is complete as the stable normalized periodic short-horizon KdV strong-path release.

Completed outcome:

- `compute_spectral_fd_derivatives(..., max_spatial_order=3)` with `u_xxx`
- `pdelie.data.generate_kdv_1d_field_batch(...)`
- `pdelie.residuals.KdVResidualEvaluator`
- KdV vertical-slice example and release-gate coverage
- mandatory representative `from_numpy` parity and optional `from_xarray` parity
- explicit deferral of weak KdV, configurable KdV coefficients, custom KdV initial conditions, general KdV support, and broad adapter work

`v0.10` begins from the frozen `v0.9` surface.
It does not reopen KdV numerics or weak-form scope.

---

## Milestone 0 - Supportability Scope Reset

**Status:** COMPLETE

### Goal

Promote `v0.10` to the next committed release target, create `V0_10_SCOPE.md`, reset `PLAN.md`, and audit `API_STABILITY.md` without changing it.

### Completed Outcome

- promoted `v0.10` to committed supportability / `v1.0` readiness scope in `ROADMAP.md`
- created `docs/planning/V0_10_SCOPE.md`
- reset `docs/planning/PLAN.md` as the active `v0.10` execution record
- recorded `v0.9` as completed
- recorded `v0.11` as conditional next strong-path PDE feasibility or promotion
- recorded `v0.12+` as later PDE/dataset coverage only after separate scope freezes
- audited `docs/specs/API_STABILITY.md`
- left `docs/specs/API_STABILITY.md` unchanged because no new `v0.10` public API has landed
- left `.github/workflows/ci.yml`, `README.md`, `CHANGELOG.md`, and `docs/releases/V0_10_RELEASE_READINESS.md` for later milestones

### Acceptance Criteria

M0 is complete only if:

- `ROADMAP.md`, `PLAN.md`, and `V0_10_SCOPE.md` are internally consistent
- `v0.9` is consistently described as completed
- `v0.10` is consistently described as the next committed release
- `v0.10` is described as supportability and `v1.0` readiness, not new numerical scope
- `v0.11` is conditional and not committed
- `v0.12+` remains planned only after separate scope freezes
- `API_STABILITY.md` remains unchanged during M0
- no runtime code, tests, package metadata, CI, README, changelog, or release-readiness docs are edited in M0

---

## Milestone 1 - Reporting Semantics Freeze

**Status:** COMPLETE

### Goal

Freeze exactly what `v0.10` supportability reporting means before runtime implementation.

### Completed Outcome

- chose a new public runtime submodule for M2: `pdelie.reporting`
- froze no root `pdelie` exports for reporting helpers
- froze reporting helpers as runtime-level public APIs, not canonical objects
- froze future M2 helper names:
  - `summarize_residual_batch(...)`
  - `summarize_weak_residual_report(...)`
  - `summarize_generator_family(...)`
  - `summarize_verification_report(...)`
  - `summarize_vertical_slice(...)`
- froze common reporting rules:
  - JSON-compatible plain Python dict outputs
  - NumPy arrays convert to lists
  - NumPy scalars convert to Python scalars
  - existing typed validation errors for invalid inputs
  - no input mutation
  - no canonical object creation or schema changes
  - no manuscript-specific table, figure, threshold, or label logic
- froze summary schemas:
  - residual batch summaries
  - weak residual report summaries
  - generator family summaries
  - verification report summaries
  - vertical-slice summaries
- left `API_STABILITY.md` unchanged because the public APIs are frozen for M2 but not implemented in M1
- left runtime code, tests, README, changelog, release-readiness docs, package metadata, and CI unchanged

### Acceptance Criteria

- exact reporting semantics are frozen before implementation
- no manuscript-specific reporting logic is introduced
- example outputs remain runtime smoke summaries, not canonical artifacts
- `API_STABILITY.md` remains unchanged until `pdelie.reporting` lands in M2

---

## Milestone 2 - Reporting Helper Implementation

**Status:** COMPLETE

### Goal

Implement the frozen supportability reporting helpers from M1.

### Completed Outcome

- added public runtime submodule `pdelie.reporting`
- exported the five M1-frozen helpers from `pdelie.reporting` only:
  - `summarize_residual_batch(...)`
  - `summarize_weak_residual_report(...)`
  - `summarize_generator_family(...)`
  - `summarize_verification_report(...)`
  - `summarize_vertical_slice(...)`
- kept root `pdelie` exports unchanged
- implemented JSON-compatible summary conversion:
  - NumPy arrays convert to lists
  - NumPy scalars convert to Python scalars
  - mappings and sequences convert recursively
- implemented typed validation errors for wrong object types, malformed weak reports, non-finite metric arrays, and malformed extra metrics
- kept helpers deterministic and scoped to existing stable runtime surfaces
- added focused reporting tests for schemas, JSON serialization, summary metrics, non-mutation, and validation failures
- updated public API tests for the new submodule and root-export guards
- updated `docs/specs/API_STABILITY.md` for the landed `pdelie.reporting` APIs
- did not change canonical object schemas, examples, CI, README, changelog, package metadata, or release-readiness docs

### Acceptance Criteria

- reporting helpers pass focused tests
- no existing canonical object schema changes
- no new PDE, weak KdV, broad adapter, or operator scope lands
- public helper APIs are documented in `API_STABILITY.md`

---

## Milestone 3 - Example Consistency

**Status:** COMPLETE

### Goal

Make existing examples easier to compare, smoke-test, and support without turning example outputs into canonical schemas.

### Completed Outcome

- refactored `run_heat_vertical_slice_example()` to return `pdelie.reporting.summarize_vertical_slice(...)`
- refactored `run_kdv_vertical_slice_example()` to return `pdelie.reporting.summarize_vertical_slice(...)`
- kept command entrypoints unchanged:
  - `python -m pdelie.examples.heat_vertical_slice`
  - `python -m pdelie.examples.kdv_vertical_slice`
- kept root `pdelie` exports unchanged
- moved example-specific context into `extra_metrics`:
  - Heat records example name, equation, training/heldout seeds, and batch sizes
  - KdV records example name, equation, generator/split seeds, train size, mass drift, and relative L2 drift
- kept example outputs JSON-only on stdout with no logging noise
- intentionally did not preserve the old flat top-level example keys
- recorded that example outputs are runtime smoke summaries, not canonical artifact schemas
- updated example tests for:
  - nested `vertical_slice` summary shape
  - JSON serialization
  - deterministic repeated output
  - Heat and KdV subprocess JSON-only execution
  - root-export guards
- updated the representative `v0.9` release-gate example assertion to read the nested summary without preserving the old example schema
- did not change fitting, verification, residual, derivative, data-generation, or reporting-helper behavior
- left `API_STABILITY.md`, README, changelog, release-readiness docs, package metadata, and CI unchanged

### Acceptance Criteria

- examples remain deterministic runtime smokes
- example summaries are not documented as canonical artifact schemas
- Heat/Burgers/KdV stable runtime behavior remains unchanged

---

## Milestone 4 - API Stability Audit and Public-Surface Guards

**Status:** COMPLETE

### Goal

Bring public-surface tests and `API_STABILITY.md` into a clean pre-`v1.0` posture.

### Completed Outcome

- added a focused API stability audit test
- verified `docs/specs/API_STABILITY.md` documents:
  - the `v0.10` `pdelie.reporting` helpers
  - the frozen `v0.8` weak residual report APIs
  - the frozen `v0.9` KdV strong-path APIs
  - deferred weak derivatives, broader weak methods, and operator symmetry as non-stable surfaces
- verified root `pdelie` remains limited to canonical objects, base evaluator, and typed errors
- verified runtime helpers remain submodule-only:
  - data generators/adapters and robustness utilities
  - derivative backend helper
  - residual evaluators and weak report functions
  - reporting helpers
  - examples
  - discovery, portability, symmetry, and visualization helpers
- verified deferred/private names remain absent from public modules:
  - weak KdV APIs
  - `compute_weak_derivatives`
  - public KdV coefficient helpers
  - broad dataset adapter aliases
  - operator-facing names
- kept public-surface tests specific-name based rather than freezing entire module contents
- did not change `API_STABILITY.md`; the audit found no mismatch
- did not add runtime APIs, canonical objects, numerical scope, CI changes, README/changelog updates, release-readiness docs, or package metadata changes

### Acceptance Criteria

- public-surface tests assert specific required/forbidden names without over-freezing unrelated module contents
- stable APIs through `v0.10` are documented
- deferred surfaces remain absent:
  - weak KdV
  - weak derivatives beyond the `v0.8` report functions
  - broad adapters
  - operator-facing APIs

---

## Milestone 5 - CI Cleanup and Release-Gate Consolidation

**Status:** COMPLETE

### Goal

Reduce CI release-gate sprawl while keeping historical release-gate tests runnable locally.

### Completed Outcome

- added a compact `tests/test_v0_10_release_gate.py`
- consolidated explicit release-gate CI visibility to one current job:
  - `v0_10-release-gate`
- removed historical explicit CI jobs:
  - `v0_4-release-gate`
  - `v0_5-release-gate`
  - `v0_6-release-gate`
  - `v0_7-release-gate`
  - `v0_8-release-gate`
  - `v0_9-release-gate`
- kept all historical release-gate test modules in the repo
- kept historical release-gate tests covered by the full `editable-tests` job
- kept `editable-tests` running full `python -m pytest`
- kept `package-smoke`
- updated package-smoke example assertions for the nested `vertical_slice` summary shape introduced in M3
- did not change historical release-gate test semantics
- did not change runtime APIs, canonical objects, numerical behavior, README/changelog docs, release-readiness docs, package metadata, or package-index publishing behavior

### Acceptance Criteria

- CI remains release-useful
- historical gate tests remain runnable locally
- current release gate remains visible in CI
- package smoke remains compact and representative

---

## Milestone 6 - Release Readiness and Documentation Alignment

**Status:** COMPLETE

### Goal

Close `v0.10` with aligned release-facing docs, package metadata, release gate, and final tag checklist.

### Completed Outcome

- updated package metadata to `0.10.0`
- updated README framing from `v0.9` to `v0.10`
- documented `pdelie.reporting` supportability helpers and nested example summaries
- added `CHANGELOG.md` entry for `0.10.0`
- created `docs/releases/V0_10_RELEASE_READINESS.md`
- updated `docs/releases/PUBLISHING.md` to include `v0.10.0` in the Git-tag-only `v0.x` release policy
- updated `docs/planning/ROADMAP.md` so `v0.10` is the current completed release and `v0.11` remains conditional/planned
- audited `docs/specs/API_STABILITY.md`; no changes were required
- recorded final release checks:
  - full pytest
  - source/wheel build
  - clean wheel smoke using `dist/pdelie-0.10.0-py3-none-any.whl`
  - Heat and KdV example module execution
  - `git diff --check`
- recorded required release PR CI checks:
  - `v0_10-release-gate`
  - `editable-tests`
  - `package-smoke`
- recorded direct final Git tag path:
  - merge release PR after CI is green
  - tag merged `main` commit as `v0.10.0`
  - do not publish to TestPyPI
  - do not publish to PyPI
  - defer package-index publishing until `v1.0` or later
- verified no new PDE, weak KdV, weak derivative API, broad adapter, operator API, root runtime export, or canonical reporting object landed

### Acceptance Criteria

- full test suite passes
- build and clean wheel smoke pass
- current release gate passes
- release-facing docs describe supportability / `v1.0` readiness, not new PDE support
- package-index publishing decision is explicit

---

## Executed Milestone Sequence

Locked sequence:

Milestone 0 -> supportability scope reset
Milestone 1 -> reporting semantics freeze
Milestone 2 -> reporting helper implementation
Milestone 3 -> example consistency
Milestone 4 -> API stability audit and public-surface guards
Milestone 5 -> CI cleanup and release-gate consolidation
Milestone 6 -> release readiness and documentation alignment

---

## Rules

- DO NOT add a new PDE in `v0.10`
- DO NOT promote weak KdV in `v0.10`
- DO NOT add a new weak derivative API in `v0.10`
- DO NOT broaden `v0.10` into PDEBench, The Well, multidimensional, multivariable, nonuniform-grid, operator, or broad adapter work
- DO NOT add manuscript-specific reporting logic
- DO NOT add a new canonical object unless M1 proves runtime helpers cannot solve the supportability problem
- DO NOT update `API_STABILITY.md` until a public `v0.10` API actually lands or an audit finds a real omission
- DO preserve existing Heat/Burgers, v0.8 weak-report, and v0.9 KdV behavior
- DO keep historical release-gate tests runnable locally through any CI cleanup

---

## Status

- `v0.9`: COMPLETE
- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE
