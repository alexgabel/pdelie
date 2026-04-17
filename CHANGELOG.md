# Changelog

## 0.2.0

First final release for the frozen V0.2 stable core.

- scientifically/functionally identical to `0.2.0rc1`
- final release metadata and release-readiness docs updated for `0.2.0`

## 0.2.0rc1

First release candidate for the frozen V0.2 stable core.

- extends the stable core from Heat-only to matched Heat and Burgers coverage
- stable pipeline remains:
  `FieldBatch -> DerivativeBatch -> ResidualBatch -> GeneratorFamily -> VerificationReport`
- synthetic 1D Burgers added as the second stable PDE under the existing contracts
- current translation fitting and finite-transform verification paths hardened across Heat and Burgers
- matched cross-PDE benchmark / release-gate layer added in the test surface under shared defaults and shared low-noise held-out conditions
- release metadata, packaging text, and user-facing docs aligned with the implemented V0.2 state

Explicitly deferred for this release candidate:

- invariant pipelines as a stable feature
- weak-form methods
- operator methods
- broad adapters or interoperability expansion
- new canonical objects beyond the current stable slice

## 0.1.0

First final release for the frozen V0.1 MVP slice.

- scientifically identical to `0.1.0rc1`
- final release metadata and release-readiness docs updated for `0.1.0`

## 0.1.0rc1

First release candidate for the frozen V0.1 MVP slice.

- stable V0.1 canonical objects implemented:
  `FieldBatch`, `DerivativeBatch`, `ResidualBatch`, `ResidualEvaluator`,
  `GeneratorFamily`, `VerificationReport`
- synthetic 1D heat-equation vertical slice implemented on a uniform periodic grid
- stable derivative backend `spectral_fd` implemented
- analytic heat residual evaluator implemented
- polynomial spatial-translation baseline implemented
- finite-transform verification path implemented
- README, packaged example module, editable-install path, and built-wheel smoke path aligned for release validation

Explicitly deferred for this release candidate:

- Burgers or any second PDE
- operator methods
- weak-form features
- broad adapters or interoperability expansion
- new canonical objects beyond the current V0.1 slice
