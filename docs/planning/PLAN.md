# PDELie — Execution Plan (V0.8)

## Current Release Status

**V0.8 M0 complete**

This file is the execution record for the active `v0.8` release series.

It should contain:

- a short closeout record for the completed `v0.7` release
- the active `v0.8` milestone sequence
- milestone-specific rules and gates

It should not redefine package contracts or roadmap commitments. Those belong in:

- `docs/specs/SPEC.md`
- `docs/specs/CONTRACTS_AND_DEFAULTS.md`
- `docs/specs/API_STABILITY.md`
- `docs/planning/ROADMAP.md`
- `docs/planning/V0_8_SCOPE.md`

`API_STABILITY.md` must remain unchanged during `v0.8 M0`.

---

## V0.7 Closeout

`v0.7` is complete as the structured external-data ingestion release.

Completed outcome:

- strict `pdelie.data.from_numpy(...)` ingestion into canonical `FieldBatch`
- strict runtime-optional `pdelie.data.from_xarray(...)` ingestion for `xarray.DataArray`
- parity protection proving imported Heat/Burgers-like data behaves like the native `FieldBatch` path
- a compact `v0.7` release gate and dedicated CI visibility job

`v0.8` begins from that frozen Heat/Burgers plus structured-ingestion surface.

This release series is weak-residual first.
It does not broaden the stable canonical object set, PDE coverage, or adapter surface.

---

## Milestone 0 — Roadmap Reset

**Status:** Complete

### Goal

Promote `v0.8` to the next committed release target, create `V0_8_SCOPE.md`, reset `PLAN.md`, and keep `API_STABILITY.md` unchanged.

### Completed Outcome

- promoted `v0.8` to committed in `ROADMAP.md`
- created `V0_8_SCOPE.md`
- reset `PLAN.md` as the active `v0.8` execution record
- left `API_STABILITY.md` unchanged

### Acceptance Criteria

M0 is complete only if:

- `ROADMAP.md`, `PLAN.md`, and `V0_8_SCOPE.md` are internally consistent
- `v0.7` is consistently described as completed
- `v0.8` is consistently described as the next committed release
- `v0.9` remains planned
- `API_STABILITY.md` remains unchanged during M0

---

## Milestone 1 — Weak Semantics Freeze

**Status:** Pending

### Goal

Freeze the exact weak residual formulas, test-function details, report schema, and benchmark fixtures before runtime implementation.

### Planned Outcome

- exact weak residual formulas for Heat and Burgers
- exact test-function family details
- exact report schema
- deterministic clean/noisy/coarse benchmark fixtures
- explicit deferral of `ResidualBatch` / `ResidualEvaluator` integration unless later experimental work justifies it

---

## Milestone 2 — Weak Residual Report Implementation

**Status:** Pending

### Goal

Implement report-style weak Heat/Burgers residual APIs only.

### Planned Outcome

- `evaluate_weak_heat_residual(...)`
- `evaluate_weak_burgers_residual(...)`
- `nu` derived from `field.metadata["parameter_tags"]["nu"]` when not provided
- typed rejection of unsupported inputs

---

## Milestone 3 — Optional Contract-Integration Exploration

**Status:** Pending

### Goal

Allow optional non-critical exploration of contract integration without making it part of the committed stable `v0.8` surface.

### Planned Outcome

- optional exploration only
- no stable `ResidualBatch` / `ResidualEvaluator` integration commitment

---

## Milestone 4 — Robustness Comparison Layer

**Status:** Pending

### Goal

Add deterministic robustness comparisons against the current spectral/analytic path.

### Planned Outcome

- deterministic clean/noisy/coarse Heat comparisons
- deterministic clean/noisy/coarse Burgers comparisons
- documented robustness signal rather than brittle hard superiority claims

---

## Milestone 5 — Optional KdV Stress

**Status:** Pending

### Goal

Keep KdV as optional non-blocking exploratory stress coverage only.

### Planned Outcome

- optional test-only KdV stress
- explicit record if skipped or deferred
- no stable KdV API/export

---

## Milestone 6 — Release Gate

**Status:** Pending

### Goal

Add a compact release gate and align docs once runtime weak APIs land.

### Planned Outcome

- compact `v0_8-release-gate`
- doc alignment after runtime API landing
- release gate covering deterministic reports, typed rejections, clean-data behavior, robustness signal, and absence of stable weak-derivative / KdV APIs

---

## Executed Milestone Sequence

Locked sequence:

Milestone 0 -> roadmap reset  
Milestone 1 -> weak semantics freeze  
Milestone 2 -> weak residual report implementation  
Milestone 3 -> optional contract-integration exploration  
Milestone 4 -> robustness comparison layer  
Milestone 5 -> optional KdV stress  
Milestone 6 -> release gate

---

## Rules

- DO NOT update `docs/specs/API_STABILITY.md` until runtime weak APIs actually land
- DO NOT add a stable weak derivative API in `v0.8 M0`
- DO NOT force weak outputs into `DerivativeBatch` or `ResidualBatch` in `v0.8 M0`
- DO NOT promote KdV to stable scope in `v0.8`
- DO NOT broaden `v0.8` into nonuniform-grid, multidimensional, multivariable, operator, or adapter work

---

## Status

- `v0.7`: COMPLETE
- Milestone 0: COMPLETE
- Milestone 1: PENDING
- Milestone 2: PENDING
- Milestone 3: PENDING
- Milestone 4: PENDING
- Milestone 5: PENDING
- Milestone 6: PENDING
