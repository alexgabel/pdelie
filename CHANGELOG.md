# Changelog

## 0.7.0

First final release for the frozen V0.7 structured external-data ingestion core.

- adds `pdelie.data.from_numpy(...)` for strict runtime conversion of explicit NumPy/array-like 1D uniform rectilinear trajectory data into canonical `FieldBatch`
- adds `pdelie.data.from_xarray(...)` for strict runtime conversion of explicit `xarray.DataArray` 1D uniform rectilinear trajectory data into canonical `FieldBatch`
- adds native-vs-imported parity coverage across the current derivative, residual, symmetry-fit, verification, and discovery-bridge layers
- adds a compact `v0_7-release-gate` CI visibility job and representative release-gate pytest module
- preserves the frozen Heat/Burgers symmetry and discovery-utility surface from `v0.6` while extending the library to structured external ingestion

Explicitly deferred for this final release:

- `xarray.Dataset` support
- dim aliases
- static-field ingestion
- multidimensional external-data ingestion
- nonuniform-grid support
- metadata inference
- PDEBench-specific loaders
- The Well adapters
- HDF5, netCDF, or Zarr stable loaders
- weak-form methods
- operator methods
- stable KdV promotion
- paper-specific experiment logic

## 0.6.0

First final release for the frozen V0.6 symmetry-guided PDE discovery utilities core.

- adds runtime-only discovery recovery metrics under `pdelie.discovery.evaluate_discovery_recovery(...)`
- adds a thin runtime-only PySINDy backend-fit adapter under `pdelie.discovery.fit_pysindy_discovery(...)`
- adds runtime-only heuristic translation-canonical discovery inputs under `pdelie.discovery.build_translation_canonical_discovery_inputs(...)`
- adds deterministic robustness helpers under `pdelie.data` plus grouped recovery-grid summaries under `pdelie.discovery`
- adds a compact `v0_6-release-gate` CI visibility job and representative release-gate pytest module
- finalizes the frozen `v0.6` Heat/Burgers discovery-utility surface without promoting KdV

Explicitly deferred for this final release:

- stable KdV API or stable KdV runtime module
- external structured dataset ingestion
- weak-form methods
- operator methods
- broad discovery adapters or backend frameworks
- paper-specific experiment logic, figures, or manuscript tables

## 0.5.0

First final release for the frozen V0.5 portability and external-compatibility core.

- functionally identical to `0.5.0rc1` unless a release blocker required a minimal fix
- finalizes the `0.5.0rc1` release surface for the V0.5 portability slice

## 0.5.0rc1

First release candidate for the frozen V0.5 generator-family portability and external-compatibility core.

- stable manifest export/import helpers added under `pdelie.portability`
- strict external-family normalization added under `pdelie.portability.coerce_generator_family(...)`
- compact portability benchmark / semantic-preservation layer added for canonical, manifest, and narrow legacy translation inputs
- compact V0.5 release-gate layer and `v0_5-release-gate` CI visibility job added
- normalized periodic KdV feasibility passes in the tests-first slice, but KdV remains non-stable in `v0.5`
- package metadata, milestone docs, and release-readiness docs aligned with the implemented V0.5 state

Explicitly deferred for this release candidate:

- stable KdV API or stable KdV runtime module
- weak-form methods
- operator methods
- broad dataset adapters or interoperability expansion
- prediction-facing utility work
- new canonical stable objects beyond the current V0.5 slice

## 0.4.0

First final release for the frozen V0.4 stable core.

- finalizes the frozen V0.4 generator-family, algebra-diagnostics, and optional-visualization release surface

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
