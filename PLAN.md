# PDELie — Execution Plan (V0.4)

## Current Active Milestone

**V0.4 Milestone 4 — Runtime closure diagnostics**

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

## Milestone 4 — Runtime Closure Diagnostics

### Goal

Add deterministic runtime-only closure diagnostics for canonical polynomial `GeneratorFamily` objects without changing canonical storage, fitting behavior, or the Heat/Burgers stable paths.

### Frozen Decisions

- `GeneratorFamily` canonical core from Milestone 1 remains unchanged
- closure diagnostics are runtime-only and must not mutate stored coefficients or normalization
- closure remains secondary to dynamical validity and supplied verification evidence
- `normalized_polynomial_l2` is the only supported M4 inner-product mode
- exact polynomial closure is frozen only for the current monomial algebraic/runtime polynomial scope
- exact brackets may use an internal expanded polynomial representation, but that representation is not canonical
- structure constants are estimated from projected brackets onto the stored family span
- antisymmetry and Jacobi diagnostics are structure-constant diagnostics, not raw vector-field Jacobi claims
- sampled fallback is minimal and deterministic, and only a compatibility path
- no fitting changes in M4
- no visualization in M4

### Deliverables

- runtime-only closure diagnostic helper under `pdelie.symmetry`
- exact polynomial Lie-bracket diagnostics for canonical monomial polynomial generator families
- projected structure-constant diagnostics and closure residuals
- structure-constant antisymmetry and Jacobi diagnostics
- family-aware interpretation labels based on supplied verification evidence
- minimal deterministic sampled fallback coverage on one controlled fixture

### Acceptance Criteria

Milestone 4 is complete only if:

- existing Heat/Burgers stable paths still pass unchanged
- canonical `GeneratorFamily` contracts remain unchanged
- commuting closed families report zero closure, antisymmetry, and Jacobi summaries
- closed nontrivial affine families report the expected structure constants
- unresolved component-target semantics fail with typed validation errors
- rank-deficient families fail with typed validation errors under the runtime metric policy
- no new canonical object is introduced
- no public fitting, invariant, visualization, or canonical semantics are broadened

### Test Plan

Run at minimum:

- runtime closure diagnostic tests
- runtime public API import tests
- commuting-family closure tests
- affine structure-constant tests
- structure-constant Jacobi tests on a closed three-generator family
- exact-bracket projection tests when brackets leave the stored basis
- explicit component-target override and unresolved-target failure tests
- minimal sampled fallback determinism tests
- family-aware interpretation-label tests
- rank-deficient family tests
- existing Heat/Burgers regression tests
- full `pytest`

---

## Later Milestones

Strict sequencing for `v0.4`:

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
- Milestone 3: **COMPLETE**
- Milestone 4: **ACTIVE**
- Milestone 5: **PLANNED**
- Milestone 6: **PLANNED**
