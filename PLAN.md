# PDELie — Execution Plan (V0.4)

## Current Active Milestone

**V0.4 Milestone 2 — Runtime symbolic normalization and display**

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

## Milestone 2 — Runtime Symbolic Normalization And Display

### Goal

Add deterministic runtime-only symbolic rendering for canonical `GeneratorFamily` objects without changing canonical storage, fitting behavior, or the Heat/Burgers stable paths.

### Frozen Decisions

- `GeneratorFamily` canonical core from Milestone 1 remains unchanged
- symbolic display is runtime-only and must not mutate stored coefficients or normalization
- default display normalization is `"anchor"`
- display normalization is separate from canonical numerical normalization
- rendering is deterministic for the given basis only
- optional SymPy support is lazy-imported and not part of the core install contract
- no heuristic basis simplification in this milestone
- no fitting changes in M2
- no span metrics in M2
- no closure diagnostics in M2
- no visualization in M2

### Deliverables

- runtime-only symbolic rendering helpers under `pdelie.symmetry`
- deterministic sign, component ordering, and term ordering from canonical `basis_spec`
- runtime-only display normalization modes `"anchor"` and `"none"`
- optional SymPy component-expression helper with clear missing-dependency error
- regression protection for canonical single-row translation families and legacy-upgraded translation payloads

### Acceptance Criteria

Milestone 2 is complete only if:

- existing Heat/Burgers stable paths still pass unchanged
- canonical `GeneratorFamily` contracts remain unchanged
- canonical single-row translation families render deterministically
- legacy translation payloads upgraded through `from_dict()` render identically to canonical family-shaped construction
- runtime display normalization does not mutate stored coefficients
- missing SymPy raises a clear runtime error for the SymPy helper only
- no new canonical object is introduced
- no public downstream, invariant, span, closure, or visualization semantics are broadened

### Test Plan

Run at minimum:

- runtime symbolic rendering tests
- runtime public API import tests
- canonical single-row translation rendering tests
- legacy-upgraded translation rendering tests
- deterministic sign / ordering / zero-tolerance tests
- optional SymPy missing-dependency and installed-path tests
- existing Heat/Burgers regression tests
- full `pytest`

---

## Later Milestones

Strict sequencing for `v0.4`:

- Milestone 3: span diagnostics under the frozen inner-product policy
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
- Milestone 2: **ACTIVE**
- Milestone 3: **PLANNED**
- Milestone 4: **PLANNED**
- Milestone 5: **PLANNED**
- Milestone 6: **PLANNED**
