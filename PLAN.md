# PDELie — Execution Plan (V0.3 Milestone 1)

## Goal

Add the first stable invariant layer in the narrowest possible form:

`FieldBatch -> DerivativeBatch -> ResidualBatch -> GeneratorFamily -> InvariantMapSpec -> InvariantApplier`

for the **single-generator case only**, while preserving the current stable Heat and Burgers paths with no regressions.

This milestone does **not** add downstream benchmarking yet.  
It only adds the minimum invariant representation and runtime application layer required for the later `v0.3` downstream utility release.

---

## Frozen Decisions

- single-generator case only
- no new numerical backend
- no weak-form methods
- no operator methods
- no broad adapters
- no new public downstream API
- `InvariantMapSpec` becomes stable in `v0.3`
- `InvariantApplier` remains runtime-only
- stable PDEs remain:
  - Heat
  - Burgers
- stable derivative backend remains:
  - `spectral_fd`
- stable symmetry target remains translation-oriented for the first invariant path unless a minimal extension is explicitly required

---

## Milestone 1

Implement:

- `InvariantMapSpec` as a stable canonical object for the single-generator case
- runtime `InvariantApplier`
- one simple invariant application path for the current stable symmetry slice
- regression protection ensuring Heat and Burgers still pass the current stable symmetry pipeline

This milestone is complete only if the invariant layer is:

- contract-compliant
- provenance-preserving
- numerically stable enough for the frozen single-generator path
- non-disruptive to the existing stable core

---

## Required Components

### 1. Stable `InvariantMapSpec`

Add a stable canonical object with at least:

- `schema_version`
- generator reference / generator metadata
- construction method
- parameters
- domain validity (`local` / `global` / `unknown`)
- inverse availability flag
- diagnostics
- serialization support:
  - `.to_dict()`
  - `.from_dict()`

This object must remain narrow and must not assume multi-generator charts.

---

### 2. Runtime `InvariantApplier`

Add a runtime utility that:

- accepts an `InvariantMapSpec`
- applies the transform to a `FieldBatch`
- returns a transformed `FieldBatch`
- appends the transform to `preprocess_log`

`InvariantApplier` is not a canonical stable artifact; it is a runtime interface.

---

### 3. One frozen application path

Implement one minimal supported transform path for the current stable symmetry slice.

That path must:

- work on the existing stable Heat/Burgers setting
- preserve `FieldBatch` contract compliance
- preserve provenance
- avoid introducing a new numerical regime
- avoid pretending that global invariant charts are available when they are not

If the transform is only valid locally or approximately, that must be explicit in diagnostics.

---

### 4. Regression protection

Keep the existing stable core intact:

- Heat path still works
- Burgers path still works
- no regression in symmetry verification
- no new canonical stable objects beyond what `v0.3` froze

---

## Exact Files To Create Or Modify

Create:

- `src/pdelie/invariants/__init__.py`
- `src/pdelie/invariants/spec.py`
- `src/pdelie/invariants/apply.py`
- `tests/test_invariant_map_spec.py`
- `tests/test_invariant_applier.py`

Modify only if required:

- `src/pdelie/contracts.py`
- `src/pdelie/__init__.py`
- `SPEC.md`
- `CONTRACTS_AND_DEFAULTS.md`
- `API_STABILITY.md`
- `ROADMAP.md`
- `PLAN.md`

Do **not** modify:

- data generation modules
- derivative backend modules
- residual evaluators
- translation fitter logic
- verification core
- downstream bridge code
- benchmark harness code

unless a minimal contract-consistency fix is required.

---

## Minimal Test Plan

### 1. Contract tests

Add tests for `InvariantMapSpec`:

- valid construction
- required fields enforced
- invalid domain-validity rejected
- serialization round-trip

### 2. Runtime application tests

Add tests for `InvariantApplier`:

- transformed object remains a valid `FieldBatch`
- `preprocess_log` is appended correctly
- metadata / dims / coords stay contract-compliant
- invalid input raises typed validation error

### 3. Stable-path compatibility tests

Add tests showing:

- Heat still passes existing stable path unchanged
- Burgers still passes existing stable path unchanged
- invariant application does not corrupt the current stable data model

### 4. Reproducibility / diagnostics tests

Add tests ensuring:

- invariant application diagnostics are deterministic for fixed input
- local/global validity is explicitly recorded
- transform provenance is retained in the output `FieldBatch`

---

## Milestone 1 Gate

Milestone 1 is complete only if:

- `InvariantMapSpec` exists as a stable canonical object
- `InvariantApplier` works end to end on the frozen single-generator path
- transformed outputs remain valid `FieldBatch` objects
- transform provenance is recorded
- Heat and Burgers still pass the current stable symmetry pipeline
- no downstream bridge is required yet
- no deferred or experimental feature is required

If these are not satisfied, Milestone 1 is not complete.

---

## Rules

- DO NOT add weak-form methods
- DO NOT add operator methods
- DO NOT add broad adapters
- DO NOT add multi-generator invariant machinery
- DO NOT add downstream benchmark logic
- DO NOT add a broad invariant public API
- DO NOT change the current stable Heat/Burgers symmetry path unless required by a minimal contract-consistency fix

---

## Status

Status: COMPLETE
