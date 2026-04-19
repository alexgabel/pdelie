# PDELie — Execution Plan (V0.4)

## Current Active Milestone

**V0.4 Milestone 1 — GeneratorFamily family semantics and migration policy**

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

## Milestone 1 — GeneratorFamily Representation Semantics

### Goal

Freeze `GeneratorFamily` family semantics and migration policy before any symbolic display, span diagnostics, closure diagnostics, or visualization work is added.

This milestone is representation-only.

### Frozen Decisions

- `GeneratorFamily` remains the stable canonical object
- canonical `schema_version` for family output is `0.2`
- canonical `coefficients` shape is 2D
- canonical `basis_spec` is required in `v0.4` output
- legacy 1D translation payloads remain accepted as backward-compatible input
- canonical core is `parameterization + coefficients + basis_spec + normalization + optional generator_names`
- `to_dict()` always emits canonical `0.2` output
- `from_dict()` performs legacy translation upgrade only in the explicit supported case
- diagnostics are non-authoritative
- no fitting in M1
- no symbolic display in M1
- no span metrics in M1
- no closure diagnostics in M1
- no visualization in M1

### Deliverables

- `GeneratorFamily` contract update with `basis_spec`
- explicit schema-version policy note prepared for `CONTRACTS_AND_DEFAULTS.md`
- validation rules for canonical family-shaped coefficients
- explicit legacy translation upgrade path
- deterministic basis ordering rules
- explicit component/term interpretation rules
- regression protection for current translation-based uses

### Acceptance Criteria

Milestone 1 is complete only if:

- existing Heat/Burgers stable paths still pass unchanged
- existing single-generator translation workflows still validate
- canonical family serialization is defined and tested
- legacy input upgrades cleanly to canonical family output
- missing or invalid `basis_spec` fails with typed validation errors
- diagnostics remain non-authoritative
- no new canonical object is introduced
- no public downstream or invariant semantics are broadened

### Test Plan

Run at minimum:

- legacy 1D translation payload tests
- legacy input -> canonical output round-trip tests
- canonical 2D family payload tests
- missing `basis_spec` tests
- incompatible coefficient shape vs `basis_spec` tests
- invalid component or term ordering tests
- existing Heat/Burgers regression tests
- full `pytest`

---

## Later Milestones

Strict sequencing for `v0.4`:

- Milestone 2: symbolic normalization and display
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
- Milestone 1: **ACTIVE**
- Milestone 2: **PLANNED**
- Milestone 3: **PLANNED**
- Milestone 4: **PLANNED**
- Milestone 5: **PLANNED**
- Milestone 6: **PLANNED**
