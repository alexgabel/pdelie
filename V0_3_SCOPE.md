# V0.3 Scope

## Summary

`v0.3` is the smallest next release that expands PDELie in a disciplined way after the two-PDE stable core established in `v0.2`.

It does **not** introduce a new numerical regime.  
It does **not** widen the ecosystem surface broadly.  
It does **not** bring operator methods into the stable library.

Instead, it asks a narrower and more important question:

> Can the current stable symmetry pipeline support one minimal invariant/downstream utility path without widening stable scope beyond what is necessary?

`v0.3` is therefore the first **downstream utility** release, not the first **broad ecosystem** release.

The downstream target for `v0.3` is frozen as:

- a **single-generator** invariant workflow only
- a **thin downstream bridge** only
- one **controlled benchmark layer** only
- Heat and Burgers remain the only stable PDEs
- the current stable derivative backend remains `spectral_fd`

---

## Must Implement

### Stable scope for `v0.3`

- uniform rectilinear grids only
- synthetic PDE data only
- polynomial generators only
- single-generator invariant workflows only
- one thin downstream bridge only
- verification-first development
- Heat and Burgers remain supported
- no new numerical backend is required for the stable path

### Stable canonical objects for `v0.3`

The stable canonical object set grows only where necessary for the first invariant/downstream utility release.

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
- one runtime `InvariantApplier` that applies the frozen single-generator invariant transform to a `FieldBatch`
- one thin PySINDy bridge or equivalent downstream export path
- one controlled benchmark comparing:
  - vanilla downstream path
  - known-invariant downstream path
  - discovered-invariant downstream path
  - one nuisance / conditioning baseline
- one release-gate layer that keeps all settings matched across benchmark branches

### Required scientific result

- the known-invariant and discovered-invariant downstream paths both run end to end under the stable contracts
- the benchmark is reproducible and matched
- the discovered-invariant path is at least meaningfully distinguishable from a nuisance baseline under matched controls
- Heat and Burgers remain regression-free under the existing stable symmetry pipeline

`v0.3` is a utility release, not yet a “strong superiority claim” release.

---

## Frozen Decisions

For the stable `v0.3` path:

- only the **single-generator** case is supported
- the stable downstream bridge is **thin**, not a new discovery framework
- benchmark logic may live in an internal helper / test-oriented layer unless and until a public API is justified
- known-invariant and discovered-invariant paths must be compared under the same feature budget, regularization budget, and split policy
- one nuisance baseline is mandatory

If a broader invariant representation or richer downstream result object becomes necessary, that belongs to a later release unless the need is minimal and unavoidable.

---

## Development Order

1. freeze `v0.3` scope
2. define and implement `InvariantMapSpec` for the single-generator case
3. add runtime `InvariantApplier`
4. add one thin downstream bridge
5. add the controlled downstream benchmark layer
6. add nuisance/conditioning control baseline
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
- genuine symmetry-related benefit

---

## Release Gate

`v0.3` is releasable only if:

- the `v0.2` Heat path still passes cleanly
- the `v0.2` Burgers path still passes cleanly
- the single-generator `InvariantMapSpec` and `InvariantApplier` work end to end on the frozen stable path
- the downstream bridge works for the frozen stable task
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