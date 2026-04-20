# PDELie — Execution Plan (V0.4)

## Current Active Milestone

**V0.4 Milestone 5 — Minimal visualization suite**

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

## Milestone 5 — Minimal Visualization Suite

### Goal

Add a minimal report-first optional visualization layer over existing canonical objects and frozen runtime reports without changing scientific semantics or the Heat/Burgers stable paths.

### Frozen Decisions

- visualization is runtime-only and must not mutate stored coefficients, normalization, or diagnostics
- `pdelie.viz` is an optional package and must not be exported from root `pdelie`
- Matplotlib is the only M5 visualization dependency
- renderers must consume existing canonical objects or frozen runtime report dicts only
- no new visualization-specific contracts or canonical objects are introduced
- no field rollout heatmaps, transformed-field plots, animation, or interactive backends are part of M5
- no fitting, verification, span, or closure semantics change in M5

### Deliverables

- optional `pdelie.viz` runtime package
- coefficient-bar renderer for `GeneratorFamily`
- symbolic summary renderer using M2 symbolic display
- verification-curve renderer for `VerificationReport`
- span-diagnostics renderer over the frozen M3 report schema
- closure-diagnostics renderer over the frozen M4 report schema

### Acceptance Criteria

Milestone 5 is complete only if:

- existing Heat/Burgers stable paths still pass unchanged
- canonical objects and runtime scientific report semantics remain unchanged
- `pdelie.viz` is importable only through the optional visualization package path
- each M5 renderer returns a Matplotlib `Figure`
- malformed runtime report dicts fail with typed validation errors
- no new canonical object is introduced
- no public fitting, invariant, span, closure, or canonical semantics are broadened

### Test Plan

Run at minimum:

- runtime visualization tests
- runtime public API import tests
- coefficient-bar structural tests
- symbolic-summary text tests
- verification-curve log-scale tests
- span-plot report-shape tests
- closure-plot report-shape tests
- malformed-report validation tests
- existing Heat/Burgers regression tests
- full `pytest`

---

## Later Milestones

Strict sequencing for `v0.4`:

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
- Milestone 4: **COMPLETE**
- Milestone 5: **ACTIVE**
- Milestone 6: **PLANNED**
