# Changelog

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
