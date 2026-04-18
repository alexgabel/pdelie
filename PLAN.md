# PDELie — Execution Plan (V0.3)

## Current Active Milestone

**V0.3 Milestone 2 — Thin downstream bridge**

This file is the active execution plan for the current `v0.3` release series.

It should contain:

- a short record of completed milestones
- the frozen plan for the current active milestone
- milestone-specific rules and gates

It should **not** redefine package contracts or roadmap commitments. Those belong in:

- `SPEC.md`
- `CONTRACTS_AND_DEFAULTS.md`
- `API_STABILITY.md`
- `ROADMAP.md`
- `V0_3_SCOPE.md`

---

## Milestone 1 — Invariant layer

### Goal

Add the first stable invariant layer in the narrowest possible form:

`FieldBatch -> DerivativeBatch -> ResidualBatch -> GeneratorFamily -> InvariantMapSpec -> InvariantApplier`

for the **single-generator case only**, while preserving the current stable Heat and Burgers paths with no regressions.

### Status

**COMPLETE**

### Implemented

- `InvariantMapSpec` as a stable canonical object for the single-generator case
- runtime `InvariantApplier`
- one frozen invariant application path for the current stable symmetry slice
- regression protection ensuring Heat and Burgers still pass the current stable symmetry pipeline
- explicit typed scope-guard failures for unsupported invariant applications

### Milestone 1 Gate

Milestone 1 passed because:

- `InvariantMapSpec` exists as a stable canonical object
- `InvariantApplier` works end to end on the frozen single-generator path
- transformed outputs remain valid `FieldBatch` objects
- transform provenance is recorded
- Heat and Burgers still pass the current stable symmetry pipeline
- no downstream bridge was required
- no deferred or experimental feature was required

---

## Milestone 2 — Thin downstream bridge

### Goal

Add the smallest downstream utility path that proves the new invariant layer can feed one downstream workflow without expanding scope beyond the frozen `v0.3` axis.

This milestone does **not** add the full downstream benchmark layer yet.  
It adds only the minimum bridge required for the later controlled benchmark/release-gate milestone.

### Status

**COMPLETE**

### Frozen Decisions

- one thin downstream bridge only
- no new numerical backend
- no weak-form methods
- no operator methods
- no broad adapters
- no broad benchmark expansion
- no new stable canonical object unless absolutely required
- stable PDEs remain:
  - Heat
  - Burgers
- stable derivative backend remains:
  - `spectral_fd`
- stable symmetry/invariant path remains the current single-generator translation-oriented path
- the downstream bridge is runtime-only, backend-specific, and exposed only as `pdelie.discovery.to_pysindy_trajectories`
- the flattened trajectory format is a bridge format only, not a PDELie canonical downstream representation
- the downstream bridge remains as thin as possible, using PySINDy only for a fit smoke path

### Milestone 2

Implement:

- one thin runtime-only PySINDy bridge for the current invariant-transformed stable path
- one minimal end-to-end downstream fit smoke path using the existing invariant layer
- regression protection ensuring Heat and Burgers stable symmetry paths remain unchanged
- explicit documentation of what the bridge does and does not guarantee

This milestone is complete only if the downstream bridge is:

- contract-compliant
- minimal in scope
- non-disruptive to the existing stable core
- sufficient for one later controlled benchmark path

---

## Required Components

### 1. Thin downstream bridge

Add one narrow bridge that consumes the current transformed data path.

The bridge must:

- work with the current single-generator invariant layer
- avoid becoming a general discovery framework
- avoid introducing a new stable canonical result object unless absolutely necessary
- avoid widening stable scope beyond one backend and one path
- remain out of root `pdelie` imports
- stay runtime-level only
- use a flattened-trajectory bridge format only for PySINDy

### 2. One frozen utility path

Implement one minimal supported downstream path for the current stable symmetry slice.

That path must:

- work on the existing stable Heat/Burgers setting
- preserve current contracts
- remain provenance-aware where applicable
- avoid introducing a new numerical regime
- avoid implying broad downstream support that does not yet exist

### 3. Regression protection

Keep the existing stable core intact:

- Heat path still works
- Burgers path still works
- no regression in symmetry verification
- no regression in invariant application
- no new canonical stable objects unless absolutely necessary

---

## Exact Files Created Or Modified

Created:

- `src/pdelie/discovery/__init__.py`
- `src/pdelie/discovery/pysindy_bridge.py`
- `tests/test_pysindy_bridge.py`

Modified:

- `pyproject.toml`
- `tests/test_public_api.py`
- `API_STABILITY.md`
- `V0_3_SCOPE.md`
- `PLAN.md`

Do **not** modify:

- data generation modules
- derivative backend modules
- residual evaluators
- translation fitter logic
- verification core
- broad benchmark harness code
- operator code
- weak-form code

unless a minimal contract-consistency fix is required.

---

## Minimal Test Plan

### 1. Bridge smoke tests

Add tests showing:

- the downstream bridge can consume the current invariant-transformed path
- the bridge behaves reproducibly under fixed inputs
- invalid or unsupported uses fail with typed errors or explicit scope errors
- the optional PySINDy dependency fails with a clear install hint when unavailable

### 2. Stable-path compatibility tests

Add tests showing:

- Heat still passes existing stable path unchanged
- Burgers still passes existing stable path unchanged
- invariant application still behaves as before
- the bridge does not corrupt the current stable data model

### 3. Narrow end-to-end utility test

Add one narrow test showing:

- stable symmetry path
- stable invariant path
- thin downstream bridge path

work together end to end for the frozen single-generator case

### 4. Full regression check

At milestone completion, run:

- the narrow bridge tests
- invariant tests
- current Heat/Burgers stable tests
- full `pytest`

---

## Milestone 2 Gate

Milestone 2 is complete only if:

- one thin downstream bridge exists for the frozen stable path
- the bridge works end to end on the single-generator invariant workflow
- Heat and Burgers still pass the current stable symmetry pipeline
- invariant application still passes unchanged
- no broad benchmark layer is required yet
- no deferred or experimental feature is required
- no new stable canonical object was added unless unavoidable and explicitly documented

If these are not satisfied, Milestone 2 is not complete.

### Milestone 2 Completion Gate

Milestone 2 passed because:

- one thin runtime-only downstream bridge exists for the frozen stable path
- the bridge works end to end on the single-generator invariant workflow
- the bridge remains out of root `pdelie` imports
- no new stable canonical object was added
- Heat and Burgers still pass the current stable symmetry pipeline
- invariant application still passes unchanged
- no full benchmark layer was required
- no deferred or experimental feature was required

---

## Rules

- DO NOT add weak-form methods
- DO NOT add operator methods
- DO NOT add broad adapters
- DO NOT add multi-generator invariant machinery
- DO NOT add the full downstream benchmark layer in this milestone
- DO NOT add a broad downstream public API
- DO NOT change the current stable Heat/Burgers symmetry path unless required by a minimal contract-consistency fix

---

## Status

- Milestone 1: **COMPLETE**
- Milestone 2: **COMPLETE**
- Milestone 3: **NOT STARTED**
