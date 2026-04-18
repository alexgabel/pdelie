# V0.3 Scope

## Summary

`v0.3` is the first downstream-utility release for PDELie.

It does **not** introduce a new numerical regime.  
It does **not** widen the ecosystem surface broadly.  
It does **not** bring operator methods into the stable library.

Instead, it asks a narrower and more important question:

> Can the current stable symmetry pipeline support one minimal invariant/downstream utility path under controlled benchmark conditions?

`v0.3` is therefore the first **invariant/downstream utility** release, not the first **broad ecosystem** or **operator** release.

The downstream target for `v0.3` is frozen as:

- a **single-generator** invariant workflow only
- a **thin downstream bridge** only
- one **controlled benchmark layer** only
- Heat and Burgers remain the only stable PDEs
- the current stable derivative backend remains `spectral_fd`

---

## Current State

### Milestone 1 — Complete

`v0.3` Milestone 1 is complete.

Completed scope:

- stable `InvariantMapSpec`
- runtime-only `InvariantApplier`
- one frozen invariant application path for the current stable symmetry slice
- regression protection showing Heat and Burgers still pass the existing stable pipeline

This milestone introduced the first stable invariant-layer contract without broadening the public API beyond the narrow single-generator path.

### Milestone 2 — Complete

`v0.3` Milestone 2 is complete.

Completed scope:

- runtime-only `pdelie.discovery.to_pysindy_trajectories`
- one narrow flattened-trajectory bridge for PySINDy only
- one minimal downstream fit smoke path for the current invariant-transformed stable slice
- no new stable canonical object

This milestone added a backend-specific runtime bridge, not a canonical PDE-discovery representation.

### Milestone 3 — Complete

`v0.3` Milestone 3 is complete.

Completed scope:

- one internal four-branch downstream benchmark:
  - vanilla
  - known_invariant
  - discovered_invariant
  - nuisance
- one frozen benchmark-local alignment rule for the current single-generator translation slice
- one explicit frozen PySINDy configuration for the downstream release gate
- reproducibility, matched-settings, and release-gate tests
- no new public API and no new stable canonical object

This milestone proves a controlled downstream utility signal for the current invariant/downstream path relative to a nuisance baseline. It does not claim broader discovery-quality superiority.

---

## Must Implement

### Stable scope for `v0.3`

- uniform rectilinear grids only
- synthetic PDE data only
- polynomial generators only
- single-generator invariant workflows only
- one thin downstream bridge only
- one controlled benchmark layer only
- verification-first development
- Heat and Burgers remain supported
- no new numerical backend is required for the stable path

### Stable canonical objects for `v0.3`

Stable in `v0.3`:

- `FieldBatch`
- `DerivativeBatch`
- `ResidualBatch`
- `ResidualEvaluator`
- `GeneratorFamily`
- `VerificationReport`
- `InvariantMapSpec`

Runtime-only, not canonical:

- `InvariantApplier`

Still not stable in `v0.3`:

- `InvariantLibrary`
- `DiscoveryResult`

No other canonical objects should become stable in `v0.3` unless absolutely necessary to support the frozen invariant/downstream path.

---

## Concrete `v0.3` Target

Add one minimal end-to-end stable downstream path on top of the existing stable symmetry core.

The stable conceptual path becomes:

`FieldBatch -> DerivativeBatch -> ResidualBatch -> GeneratorFamily -> InvariantMapSpec -> InvariantApplier -> downstream bridge -> VerificationReport`

for Heat and Burgers under the current stable translation-targeted symmetry slice.

### Required components

- one stable `InvariantMapSpec` for the single-generator case
- one runtime `InvariantApplier`
- one thin downstream bridge, likely PySINDy
- one controlled benchmark comparing:
  - vanilla downstream path
  - known-invariant downstream path
  - discovered-invariant downstream path
  - one nuisance / conditioning baseline
- one release-gate layer that keeps all settings matched across benchmark branches

### Required scientific result

- the known-invariant and discovered-invariant downstream paths both run end to end under the stable contracts
- the benchmark is reproducible and matched
- the invariant-aware downstream path is at least meaningfully distinguishable from a nuisance baseline under matched controls
- Heat and Burgers remain regression-free under the existing stable symmetry pipeline

`v0.3` is a utility release, not yet a broad superiority-claim release.

---

## Frozen Milestones

### Milestone 1 — Invariant layer
**Status:** Complete

Frozen scope:
- stable `InvariantMapSpec`
- runtime-only `InvariantApplier`
- one narrow application path
- no downstream bridge yet
- no benchmark expansion yet

### Milestone 2 — Thin downstream bridge
**Status:** Complete

Frozen scope:
- one thin downstream bridge only
- no broad system-identification framework
- no new canonical stable object unless absolutely required
- no benchmark expansion yet beyond the minimal bridge smoke path
- no weak-form methods
- no operator methods
- no broad adapters

Completed outcome:
- transformed data from the current single-generator invariant path can feed one downstream workflow cleanly under stable contracts

### Milestone 3 — Controlled downstream benchmark / release-gate layer
**Status:** Complete

Frozen scope:
- one controlled benchmark comparing:
  - vanilla
  - known-invariant
  - discovered-invariant
  - nuisance baseline
- matched feature budget
- matched regularization budget
- matched split policy
- reproducible benchmark outputs
- no broad benchmark zoo
- no new public benchmark API unless clearly justified

Completed outcome:
- `v0.3` release gate can be stated in terms of a reproducible downstream utility benchmark, not just symmetry recovery
- known_invariant and discovered_invariant are expected to be numerically equivalent in the frozen Milestone 3 slice
- the nuisance baseline is the actual utility comparison branch for this release gate

---

## Development Order

1. freeze `v0.3` scope
2. implement `InvariantMapSpec`
3. implement `InvariantApplier`
4. add one thin downstream bridge
5. add the controlled downstream benchmark layer
6. add nuisance / conditioning control baseline
7. add release-gate tests and documentation

---

## Explicitly Deferred

The following are **not** part of stable `v0.3` scope:

- weak-form derivatives as a stable backend
- multi-generator invariant charts
- `InvariantLibrary` as a stable contract
- `DiscoveryResult` as a stable contract
- broad system-identification framework work beyond one thin bridge
- broad adapters (PDEBench, The Well, etc.) as release-defining work
- operator symmetry
- NeuralOperator integration
- nonuniform rectilinear support in stable derivative code
- multiple downstream backends
- broad benchmark zoo
- manuscript-specific experiment logic

These may be explored experimentally, but they do not define `v0.3`.

---

## Benchmark Rules for `v0.3`

`v0.3` should benchmark the first stable downstream utility path, not yet claim broad downstream dominance.

Required controls:

- fixed train/test split conventions
- fixed verification defaults
- fixed noise condition where applicable
- fixed feature budget
- fixed regularization budget
- fixed derivative backend assumptions
- identical benchmark settings across:
  - vanilla
  - known-invariant
  - discovered-invariant
  - nuisance baseline

Required outputs:

- downstream result for vanilla path
- downstream result for known-invariant path
- downstream result for discovered-invariant path
- downstream result for one nuisance baseline
- held-out evaluation under matched settings
- reproducible benchmark outputs
- no regression in the existing Heat/Burgers symmetry paths

The benchmark must distinguish:
- correctness of the invariant/downstream mechanism
- conditioning effects
- a controlled downstream utility signal relative to the nuisance baseline

---

## Release Gate

`v0.3` is releasable only if:

- the `v0.2` Heat path still passes cleanly
- the `v0.2` Burgers path still passes cleanly
- the single-generator `InvariantMapSpec` and `InvariantApplier` work end to end on the frozen stable path
- the thin downstream bridge works for the frozen stable task
- the controlled benchmark runs reproducibly under matched settings
- the nuisance baseline is included
- no deferred or experimental feature is required for the stable release path
- the current stable contracts remain coherent after adding the first invariant/downstream layer

If these conditions are not met, `v0.3` is not complete.

---

## Non-goals

`v0.3` is **not**:

- the release where weak-form methods become stable
- the release where PDELie becomes a broad ecosystem hub
- the release where operator methods become part of the stable library
- the release where full invariant machinery becomes stable
- the release where downstream discovery becomes a broad multi-backend framework

It is the release where PDELie proves that its current stable symmetry core can support one disciplined invariant/downstream utility path.

---

## Next Expansion After `v0.3`

If `v0.3` succeeds, the next credible stable step is one of:

- broader invariant machinery
- broader downstream semantics
- broader numerics

but still **not automatically** operator methods or broad ecosystem expansion.

Those decisions belong to `v0.4+`, not `v0.3`.
