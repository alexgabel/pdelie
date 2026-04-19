# PDELie — Execution Plan (V0.4)

## Current Active Milestone

**V0.4 Milestone 3 — Runtime span diagnostics**

This file is the active execution plan for the current `v0.4` release series.

It should contain:

- a short record of the completed `v0.3` release
- the frozen plan for the current active milestone
- milestone-specific rules and gates

It should **not** redefine package contracts or roadmap commitments. Those belong in:

- `SPEC.md`
- `CONTRACTS_AND_DEFAULTS.md`
- `API_STABILITY.md`
- `ROADMAP.md`
- `V0_4_SCOPE.md`

---

## V0.3 Closeout

`v0.3` is complete as the first invariant/downstream utility release.

Completed outcome:

- stable `InvariantMapSpec`
- runtime-only `InvariantApplier`
- runtime-only narrow PySINDy bridge
- internal controlled downstream benchmark / release gate
- Heat and Burgers regression protection preserved

`v0.4` begins from that frozen release surface.

---

## Milestone 3 — Runtime Span Diagnostics

### Goal

Add deterministic runtime-only algebraic span comparison for canonical `GeneratorFamily` objects without changing canonical storage, fitting behavior, or the Heat/Burgers stable paths.

### Frozen Decisions

- `GeneratorFamily` canonical core from Milestone 1 remains unchanged
- span diagnostics are runtime-only and must not mutate stored coefficients or normalization
- principal angles are the primary span metric
- projection residual is the paired derived diagnostic
- `normalized_polynomial_l2` is the only supported M3 inner-product mode
- exact polynomial comparison is frozen only for the current algebraic/runtime polynomial scope
- structurally equivalent `basis_spec` semantics are required; raw dictionary identity is not
- no fitting changes in M3
- no closure diagnostics in M3
- no visualization in M3

### Deliverables

- runtime-only span comparison helper under `pdelie.symmetry`
- deterministic principal-angle diagnostics for canonical polynomial generator families
- deterministic projection residual diagnostics under the frozen normalized polynomial inner product
- basis-spec structural-equivalence checks for span comparison
- regression protection for canonical translation families, legacy-upgraded translation payloads, and controlled algebraic fixtures

### Acceptance Criteria

Milestone 3 is complete only if:

- existing Heat/Burgers stable paths still pass unchanged
- canonical `GeneratorFamily` contracts remain unchanged
- identical spans compare with zero principal angles and zero projection residual summary
- same spans under basis change compare as equivalent
- structurally non-equivalent basis semantics fail with typed validation errors
- zero-rank effective spans fail with typed validation errors
- no new canonical object is introduced
- no public fitting, invariant, closure, or visualization semantics are broadened

### Test Plan

Run at minimum:

- runtime span comparison tests
- runtime public API import tests
- canonical single-row translation span tests
- legacy-upgraded translation span tests
- basis-change equivalence tests
- strict-containment residual tests
- basis-spec structural-equivalence and mismatch tests
- zero-rank span tests
- existing Heat/Burgers regression tests
- full `pytest`

---

## Later Milestones

Strict sequencing for `v0.4`:

- Milestone 4: closure diagnostics with exact bracket preferred
- Milestone 5: minimal visualization as renderers only and deferrable
- Milestone 6: algebra-span release gate

Hard sequencing rules:

- do not add fitting logic before representation and diagnostics semantics are frozen
- do not let visualization define new semantics or helper contracts

---

## Rules

- DO NOT add weak-form methods
- DO NOT add operator methods
- DO NOT add broad dataset adapters
- DO NOT add neural generators as stable API
- DO NOT add representative-loss or research-loss code
- DO NOT add stable 2D PDE pipeline work
- DO NOT add stable multi-generator PDE fitting in `v0.4`
- DO NOT add broad downstream benchmark expansion
- DO NOT add paper-specific or manuscript-facing language

---

## Status

- `v0.3`: **COMPLETE**
- Milestone 1: **COMPLETE**
- Milestone 2: **COMPLETE**
- Milestone 3: **ACTIVE**
- Milestone 4: **PLANNED**
- Milestone 5: **PLANNED**
- Milestone 6: **PLANNED**
