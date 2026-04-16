# PDELie Roadmap

This file is the authoritative release-planning document for `pdelie`.

It defines:

- the current release series
- the next committed release target
- the medium-term planned direction
- the experimental horizon

It does **not** define package contracts.  
All contracts and stable behavior are defined in:

- `SPEC.md`
- `CONTRACTS_AND_DEFAULTS.md`
- `API_STABILITY.md`

It does **not** define active task execution.  
Execution state belongs in:

- `PLAN.md`

---

## Planning Status Labels

Every roadmap item must be one of:

- **Committed** — planned for the next release series
- **Planned** — intended for a later release, but not yet frozen
- **Experimental** — active research direction, not stable API
- **Deferred** — intentionally postponed

Only **Committed** items may define the next stable release.

---

## Release Philosophy

PDELie advances by **one stable axis at a time**.

Rules:

1. one release should expand at most one major scientific or numerical axis
2. stable scope should only grow after the previous scope is proven end to end
3. experimental work may inform future releases, but does not define them
4. long-term ambition must not be confused with a committed roadmap item

---

## Current State

### `v0.1.x` — Stabilization
**Status:** Committed

`v0.1.x` is the release series for the first proven vertical slice:

`FieldBatch -> DerivativeBatch -> ResidualBatch -> GeneratorFamily -> VerificationReport`

on the synthetic 1D heat equation with:

- uniform periodic grid
- `spectral_fd`
- analytic heat residual
- polynomial spatial-translation baseline
- finite-transform verification

### Goals for `v0.1.x`

- stabilize packaging
- stabilize public API
- fix bugs
- improve docs
- preserve exact current stable scope

### Non-goals for `v0.1.x`

- no second PDE
- no invariant pipeline
- no weak-form implementation
- no operator methods
- no broad adapters
- no benchmark expansion beyond the MVP path

---

## Next Release Target

### `v0.2` — Second PDE under the current pipeline
**Status:** Committed

`v0.2` is the next stable release target.

Its purpose is:

> prove that the current stable contracts and symmetry pipeline survive contact with a second PDE.

### In scope for `v0.2`

- add Burgers as the second stable PDE benchmark
- keep the same canonical stable object set as the v0.1 slice where possible
- harden fitting and verification against a second known case
- broaden polynomial fitting just enough to support the second PDE cleanly
- preserve strict stable/experimental boundaries
- keep all comparisons and validation under controlled benchmark settings

### Out of scope for `v0.2`

- no stable invariant pipeline
- no stable weak-form implementation
- no operator symmetry
- no NeuralOperator integration
- no broad ecosystem adapters
- no large benchmark zoo
- no major scope increase in canonical stable objects unless required by the second-PDE path

### Release Gate for `v0.2`

`v0.2` is complete only if:

- Heat still passes the existing stable release gate
- Burgers works cleanly end to end through the current stable pipeline
- fitting and verification remain contract-compliant on both PDEs
- no experimental feature is required for the stable path

---

## Planned Next Step

### `v0.3` — First downstream utility release
**Status:** Planned

`v0.3` is the first release where PDELie should demonstrate stable downstream usefulness, not just symmetry recovery.

### Candidate scope for `v0.3`

- minimal single-generator invariant map support
- one downstream bridge, likely PySINDy
- one controlled benchmark:
  - vanilla downstream method
  - known-invariant downstream method
  - discovered-invariant downstream method
- one nuisance / conditioning control baseline

### Why this is not `v0.2`

Because this release expands a new axis:

- representation layer
- invariant semantics
- downstream benchmark meaning

That should happen only after the current pipeline is proven across more than one PDE.

---

## Medium-Term Horizon

### `v0.4+`
**Status:** Experimental / Deferred

The following are promising directions, but not yet committed stable roadmap items:

- weak-form derivatives / weak residual workflows
- broader invariant machinery
- multiple-generator Lie algebra tooling
- broader interoperability
- larger external datasets
- nonuniform grid support in practice
- operator-level symmetry discovery
- neural generator fields as public stable methods

These may exist in experimental namespaces or downstream repos before they enter the stable roadmap.

---

## Relationship Between Roadmap and Strategy Documents

### Authoritative for scheduling
- `ROADMAP.md`
- `V0_1_SCOPE.md`
- `V0_2_SCOPE.md` once frozen
- `PLAN.md` for current execution only

### Non-authoritative for scheduling
- `INTEROPERABILITY_AND_BENCHMARKING.md`
- `LLM_CONTEXT.md`

These may describe strategic horizons or research directions, but they do **not** commit a feature to a release.

---

## Change Policy

This roadmap should only be updated:

- at release boundaries
- when a new release scope is frozen
- when a committed item is explicitly deferred

It should **not** be edited every time a new idea appears.

---

## Short Version

- `v0.1.x` = stabilize the proven heat-equation vertical slice
- `v0.2` = add Burgers under the same stable pipeline
- `v0.3` = first stable downstream utility via invariants
- `v0.4+` = broader numerics, broader data, operator methods, and other experimental directions