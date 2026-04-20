# Changelog

## 0.4.0rc1

First release candidate for the frozen V0.4 generator-family and algebra-diagnostics core.

- canonical `GeneratorFamily` family semantics finalized with `schema_version = "0.2"`, family-shaped coefficients, and explicit `basis_spec`
- runtime-only symbolic generator rendering added under `pdelie.symmetry`
- optional runtime-only SymPy component expressions added under `pdelie.symmetry`
- runtime-only span diagnostics added under `pdelie.symmetry`
- runtime-only closure / structure-constant diagnostics added under `pdelie.symmetry`
- optional Matplotlib visualization layer added under `pdelie.viz`
- explicit V0.4 release-gate pytest module and `v0_4-release-gate` CI visibility job added
- package metadata, README, milestone docs, and release-readiness docs aligned with the implemented V0.4 state

Explicitly deferred for this release candidate:

- weak-form methods
- operator methods
- broad adapters or interoperability expansion
- stable multi-generator PDE fitting
- broader downstream compatibility or prediction-facing workflows
- new canonical stable objects beyond the current V0.4 slice

## 0.3.0

First final release for the frozen V0.3 stable core.

- functionally identical to `0.3.0rc1` unless a release blocker required a minimal fix
- finalizes the `0.3.0rc1` release surface for the invariant/downstream utility slice

## 0.3.0rc1

First release candidate for the frozen V0.3 invariant/downstream utility core.

- stable canonical pipeline extended with `InvariantMapSpec`
- runtime-only `pdelie.invariants.InvariantApplier` added for the frozen single-generator periodic `x` uniform-translation path
- runtime-only `pdelie.discovery.to_pysindy_trajectories` added as the narrow backend-specific PySINDy bridge
- controlled four-branch downstream benchmark / release-gate layer added internally under frozen settings:
  `vanilla`, `known_invariant`, `discovered_invariant`, `nuisance`
- release metadata, package description, README, and release-readiness docs aligned with the implemented V0.3 state

Explicitly deferred for this release candidate:

- weak-form methods
- operator methods
- multi-generator invariant machinery
- broad adapters or interoperability expansion
- new canonical objects beyond the current V0.3 slice

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
