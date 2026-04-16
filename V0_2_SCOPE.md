# V0.2 Scope

## Summary

`v0.2` is the smallest next release that expands PDELie in a disciplined way.

It does **not** introduce a new major representation layer.  
It does **not** introduce a new numerical regime.  
It does **not** widen the ecosystem surface.

Instead, it asks a narrower and more important question:

> Do the current stable contracts and symmetry pipeline survive contact with a second PDE?

The second PDE for `v0.2` is **1D Burgers**.

---

## Must Implement

### Stable scope for `v0.2`

- uniform rectilinear grids only
- synthetic PDE data only
- polynomial generators only
- verification-first development
- Heat remains supported
- Burgers is added as the second stable PDE

### Stable canonical objects for `v0.2`

The stable contract set remains the current narrow slice unless a second-PDE requirement forces a minimal extension:

- `FieldBatch`
- `DerivativeBatch`
- `ResidualBatch`
- `ResidualEvaluator`
- `GeneratorFamily`
- `VerificationReport`

No other canonical objects should become stable in `v0.2` unless absolutely necessary to support the second-PDE vertical slice.

---

## Concrete `v0.2` Target

Add a second end-to-end stable path:

`FieldBatch -> DerivativeBatch -> ResidualBatch -> GeneratorFamily -> VerificationReport`

for synthetic 1D Burgers on a uniform grid.

### Required components

- one synthetic 1D Burgers dataset generator
- one trusted Burgers residual evaluator
- derivative support that works within the existing stable numerical assumptions
- one broadened polynomial fitting path that is not heat-translation-specific
- one finite-transform verification path suitable for the chosen Burgers symmetry target
- one controlled benchmark task comparing behavior on Heat and Burgers

### Required scientific result

- recover and verify at least one known Burgers symmetry target under the stable pipeline
- maintain the existing Heat result without regressions

---

## Development Order

1. freeze `v0.2` scope
2. add synthetic 1D Burgers data
3. add Burgers residual evaluator
4. broaden polynomial fitting just enough for the second PDE
5. add/adjust verification for the Burgers symmetry target
6. add cross-PDE tests and release-gate checks

---

## Explicitly Deferred

The following are **not** part of stable `v0.2` scope:

- weak-form derivatives as a stable backend
- invariant-coordinate pipelines as a stable feature
- `InvariantMap` as a stable contract
- `InvariantLibrary` as a stable contract
- `DiscoveryResult` as a stable contract
- downstream system-identification workflows as part of the stable API
- PySINDy integration as a release-defining stable feature
- operator symmetry
- NeuralOperator integration
- broader adapter work (PDEBench, The Well, etc.) as a release-defining goal
- nonuniform rectilinear support in stable derivative code
- multi-generator Lie algebra tooling beyond diagnostics
- broad benchmark zoo
- manuscript-specific experiment logic

These may be explored experimentally, but they do not define `v0.2`.

---

## Benchmark Rules for `v0.2`

`v0.2` should benchmark the current stable symmetry pipeline across two PDEs, not yet benchmark downstream utility claims.

Required controls:

- fixed train/test split conventions
- fixed verification defaults
- fixed noise condition
- fixed derivative backend assumptions
- comparable fitting and verification settings across Heat and Burgers where meaningful

Required outputs:

- symmetry recovery result on Heat
- symmetry recovery result on Burgers
- held-out verification on both
- reproducible `VerificationReport` on both
- no regression in the existing Heat path

---

## Release Gate

`v0.2` is releasable only if:

- the v0.1 Heat path still passes cleanly
- Burgers works end to end through the stable pipeline
- the chosen Burgers symmetry target is recovered and verified under held-out evaluation
- the current stable contracts remain coherent across both PDEs
- no deferred or experimental feature is required for the stable release path

If these conditions are not met, `v0.2` is not complete.

---

## Non-goals

`v0.2` is **not**:

- the release where invariants become a stable public feature
- the release where weak-form methods become stable
- the release where PDELie becomes a broad ecosystem hub
- the release where operator methods become part of the stable library

It is the release where the current stable core proves that it generalizes one step beyond the original heat-equation MVP.

---

## Next Expansion After `v0.2`

If `v0.2` succeeds, the next credible stable step is:

- a minimal invariant/downstream utility release

not:

- broad adapters
- broad numerics
- operator methods

That next step belongs to `v0.3`, not `v0.2`.