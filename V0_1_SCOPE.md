# V0.1 Scope

## Must Implement

V0.1 is the smallest vertical slice that proves the library's central claim: numerical recovery and verification of a Lie symmetry from PDE data through a clean, reproducible pipeline.

Stable scope for V0.1:

- uniform rectilinear grids only
- synthetic PDE data only
- polynomial generators only
- verification-first development

Canonical contracts to freeze for this slice only:

- `FieldBatch`
- `DerivativeBatch`
- `ResidualBatch`
- `ResidualEvaluator`
- `GeneratorFamily`
- `VerificationReport`

Development order:

1. freeze contracts
2. synthetic data
3. derivatives
4. residuals
5. generator fitting
6. verification

Concrete V0.1 target:

- synthetic heat equation only
- one `FieldBatch` implementation
- one derivative backend: `spectral_fd` (spectral in space, finite in time)
- one analytic heat `ResidualEvaluator`
- one polynomial generator fitter
- one finite-transform verifier
- one `VerificationReport`
- one controlled benchmark task

Documentation rules for V0.1:

- one authoritative spec for contracts and defaults
- consistent `ResidualEvaluator` and `ResidualBatch` definitions everywhere
- one default verification norm
- one default epsilon sweep
- clear statement that normalization is restricted for symmetry recovery
- clear statement that nonuniform rectilinear grids are not part of stable derivative support

## Explicitly Deferred

The following are not part of V0.1 stable scope:

- The Well adapter
- broad interoperability work beyond the MVP path
- NeuralOperator integration
- operator symmetry
- weak-form backend beyond an interface placeholder
- broad benchmark zoo
- nuisance baselines beyond one mandatory control
- lazy or out-of-core semantics
- full schema richness for unused objects
- serialization of every artifact if it slows implementation of the first proven path
- nonuniform rectilinear support in stable code
- `InvariantMap` as a stable contract
- `InvariantLibrary` as a stable contract
- `DiscoveryResult` as a stable contract
- downstream discovery tooling beyond what is needed later
- duplicate or near-duplicate spec text across multiple docs

These items may exist conceptually or as experimental placeholders, but they are not release-defining for V0.1.

## Release Gate

V0.1 is releasable only if the heat-equation vertical slice works cleanly and reproducibly end to end.

Minimum gate:

- recover spatial translation on the heat equation from synthetic data
- pass the default epsilon sweep
- pass held-out evaluation
- remain stable under a defined small-noise condition
- produce a `VerificationReport` with reproducible classification across runs
- keep all work within the frozen V0.1 contracts
- avoid broadening stable scope beyond the listed slice

If this path is not yet working, V0.1 is not complete. The next expansion after a successful release gate is Burgers as the second PDE, not broader adapters or downstream ecosystem tooling.
