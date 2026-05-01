# pdelie

Numerical discovery and verification of Lie symmetries for PDE data.

The current repository implements the frozen V0.16 external symmetry-candidate validation slice for the existing Heat/Burgers/weak-report/KdV engine:

- synthetic 1D heat equation
- synthetic 1D Burgers equation
- synthetic normalized periodic short-horizon KdV
- strict external structured ingestion into canonical `FieldBatch`
- deterministic window-indexed weak residual reports under `pdelie.residuals`
- JSON-compatible runtime supportability summaries under `pdelie.reporting`
- generator-fit diagnostic summaries under `pdelie.reporting.summarize_generator_fit_diagnostics`
- uniform periodic grid
- `spectral_fd` derivatives through `u_xxxx`
- normalized KdV strong residuals under `pdelie.residuals.KdVResidualEvaluator`
- internal Kuramoto-Sivashinsky diagnostic sweep evidence with stable runtime promotion deferred
- public orbit/coverage diagnostics under `pdelie.invariants`
- invariant workflow summaries under `pdelie.reporting.summarize_invariant_workflow`
- read-only uniform translation orbit reports under `pdelie.invariants.summarize_uniform_translation_orbit`
- materialized uniform translation orbit batches under `pdelie.invariants.build_uniform_translation_orbit_batch`
- empirical external symmetry-candidate validation reports under `pdelie.symmetry.validate_symmetry_candidate`
- `FieldBatch -> DerivativeBatch -> ResidualBatch -> GeneratorFamily -> InvariantMapSpec -> VerificationReport`
- one stable derivative backend: `spectral_fd`
- family-shaped `GeneratorFamily` with explicit `basis_spec`
- runtime-only symbolic helpers under `pdelie.symmetry`
- runtime-only span and closure diagnostics under `pdelie.symmetry`
- optional `pdelie.viz` visualization layer
- one stable invariant canonical object: `InvariantMapSpec`
- one runtime-only invariant path retained from V0.3: `pdelie.invariants.InvariantApplier`
- one runtime-only backend-specific downstream bridge retained from V0.3: `pdelie.discovery.to_pysindy_trajectories`
- one runtime-only portability layer retained from V0.5: `pdelie.portability`
- one runtime-only discovery metrics layer under `pdelie.discovery`
- one runtime-only thin PySINDy discovery adapter under `pdelie.discovery`
- one runtime-only translation-canonical discovery-input helper under `pdelie.discovery`
- one runtime-only robustness helper layer under `pdelie.data`
- one compact current `v0_16-release-gate` CI job plus full editable tests and package smoke

## Setup

### Conda environment

From the repo root:

```bash
conda env create -f environment.yml
conda activate pdelie
```

### Editable install

Core install from the repo root:

```bash
python -m pip install -e .
```

### Optional dependencies

- `.[viz]` adds the optional Matplotlib visualization layer exposed under `pdelie.viz`
- `.[downstream]` adds the optional narrow PySINDy bridge path exposed under `pdelie.discovery`
- `.[xarray]` adds the optional `xarray.DataArray` ingestion path exposed under `pdelie.data.from_xarray`
- `.[test]` installs the test environment used in CI and includes the current viz/downstream/xarray test dependencies
- `sympy` is an optional runtime dependency for `pdelie.symmetry.to_sympy_component_expressions`; it is not required for the core install

The downstream path is still intentionally narrow: it is currently validated on the PySINDy 1.x / scikit-learn 1.2.x line under Python `<3.12`, matching the policy in `pyproject.toml`.

## Run Tests

From the repo root:

```bash
python -m pytest
```

## Repository Docs

- specifications and contracts: `docs/specs/`
- planning and frozen scope docs: `docs/planning/`
- release-readiness history: `docs/releases/`
- non-normative strategy notes: `docs/strategy/`
- exploratory notebooks and usage guides: `notebooks/`

## Tutorial Notebooks

The repository includes exploratory notebooks under `notebooks/` for the shipped symmetry/discovery runtime surface retained through `v0.16`:

- `00_how_to_use_pdelie_v0_6.ipynb`
- `01_raw_vs_translation_canonical_discovery.ipynb`
- `02_robustness_sweeps.ipynb`
- `03_portability_round_trips.ipynb`
- `04_discovered_vs_known_translation_generators.ipynb`
- `05_closure_algebra_diagnostics.ipynb`
- `06_orbit_coverage_diagnostics.ipynb`

These notebooks are non-normative tutorials, not stability contracts.
Most discovery notebooks require the downstream extras (`.[downstream]` or `.[test]`).

## Minimal End-To-End Example

Run the packaged example modules from the repo root:

```bash
python -m pdelie.examples.heat_vertical_slice
python -m pdelie.examples.kdv_vertical_slice
python -m pdelie.examples.orbit_coverage_diagnostics
python -m pdelie.examples.invariant_workflow_summary
python -m pdelie.examples.translation_orbit_batch
python -m pdelie.examples.symmetry_candidate_validation
```

Those commands are validated in CI after editable install.
The built-wheel packaging smoke keeps a smaller import/residual check for KdV.

The Heat example demonstrates:

1. generate synthetic heat-equation data
2. compute `spectral_fd` derivatives
3. evaluate the analytic heat residual
4. fit the polynomial spatial-translation baseline
5. verify the generator on held-out heat batches

The KdV example demonstrates the frozen normalized periodic short-horizon KdV strong path:

1. generate synthetic KdV data
2. split train/heldout batches
3. compute `spectral_fd` derivatives through `u_xxx`
4. evaluate the normalized KdV residual
5. fit and verify the polynomial spatial-translation baseline

The orbit/coverage diagnostics example demonstrates:

1. grid-point coverage for periodic half-open windows under uniform shifts
2. the frozen field-shift-then-fixed-window convention
3. uniform-translation consistency checks on stable Heat and KdV fixtures
4. residual RMS stability checks under the existing residual evaluators

The invariant workflow summary example demonstrates:

1. read-only uniform translation orbit reports for Heat and KdV fixtures
2. coverage and consistency diagnostics nested into one workflow summary
3. generator fit diagnostics and finite-transform verification summaries
4. report-only provenance through optional `source_field_id` values

The translation orbit batch example demonstrates:

1. materialized uniform translation orbit batches for Heat and KdV fixtures
2. shift-major batch growth with duplicate shifts preserved
3. source/shift provenance in a JSON-compatible report
4. residual sanity on the materialized `FieldBatch` outputs

The symmetry candidate validation example demonstrates:

1. externally supplied `GeneratorFamily` and `InvariantMapSpec` payload validation
2. Heat and KdV configured empirical validation reports
3. a failed candidate for contrast
4. the v0.16 interpretation that `validated` means configured empirical validation, not a mathematical proof

You can also call the examples programmatically.
They return JSON-compatible runtime summaries, not canonical artifact schemas.
The Heat and KdV examples return nested `vertical_slice` summaries; the invariant examples return diagnostic/workflow summaries:

```python
from pdelie.examples import (
    run_heat_vertical_slice_example,
    run_invariant_workflow_summary_example,
    run_kdv_vertical_slice_example,
    run_orbit_coverage_diagnostics_example,
    run_symmetry_candidate_validation_example,
    run_translation_orbit_batch_example,
)

result = run_kdv_vertical_slice_example()
print(result["verification"]["classification"])

coverage = run_orbit_coverage_diagnostics_example()
print(coverage["coverage_cases"][0]["coverage_fraction"])

workflow = run_invariant_workflow_summary_example()
print(workflow["workflows"][0]["summary_type"])

orbit_batch = run_translation_orbit_batch_example()
print(orbit_batch["cases"][0]["orbit_report"]["output_batch_size"])

candidate_validation = run_symmetry_candidate_validation_example()
print(candidate_validation["cases"][0]["report"]["conclusion"])
```

## Current Scope

Included in the current stable core:

- stable canonical objects and typed validation errors, including `InvariantMapSpec`
- synthetic heat, Burgers, and normalized periodic short-horizon KdV data
- strict structured external-data ingestion into canonical `FieldBatch` via `from_numpy(...)` and `from_xarray(...)`
- stable weak residual report APIs under `pdelie.residuals` for Heat and Burgers
- stable normalized KdV strong residual evaluator under `pdelie.residuals`
- stable supportability reporting helpers under `pdelie.reporting`, including generator-fit diagnostic summaries
- polynomial translation baseline for the stable PDE slice
- finite-transform verification for the stable PDE slice
- family-shaped `GeneratorFamily` serialization and narrow translation compatibility migration
- manifest export/import for canonical `GeneratorFamily` portability
- strict external-family normalization for canonical payloads, manifests, and the narrow legacy translation payload
- single-generator invariant map support
- runtime-only discovery recovery metrics, backend-native PySINDy discovery fits, translation-canonical discovery inputs, robustness utilities, and structured-ingestion parity coverage for the current Heat/Burgers slice
- matched Heat/Burgers benchmark and release-gate checks in the test layer
- consolidated current release-gate CI visibility while retaining historical gate tests in the full test suite
- KdV is stable only for the normalized periodic short-horizon strong path; weak KdV remains explicitly deferred
- KS remains internal feasibility/no-go evidence from `v0.11` plus internal diagnostic sweep evidence in `v0.12`; no stable KS runtime API is promoted
- orbit/coverage diagnostics from `v0.13` are public under `pdelie.invariants`; they report coverage and consistency but do not construct augmented datasets
- invariant workflow summaries and uniform translation orbit reports in `v0.14` are read-only runtime reports; they do not construct augmented datasets, orbit datasets, or transformed `FieldBatch` collections
- materialized uniform translation orbit batches in `v0.15` are conservative data utilities; they append along batch and record provenance, but do not manage train/test splits or leakage policy
- external symmetry-candidate validation in `v0.16` accepts `GeneratorFamily` and `InvariantMapSpec` objects or strict payload mappings and returns empirical configured validation reports; it does not train detectors or accept callables

Runtime-level public APIs in the frozen V0.16 slice:

- `pdelie.data.from_numpy` for strict runtime conversion of explicit NumPy/array-like 1D uniform rectilinear trajectory data into canonical `FieldBatch`
- `pdelie.data.from_xarray` for strict runtime conversion of explicit `xarray.DataArray` 1D uniform rectilinear trajectory data into canonical `FieldBatch` when the optional `xarray` dependency is installed
- `pdelie.derivatives.compute_spectral_fd_derivatives(..., max_spatial_order=4)` for `u_xxxx` on the existing uniform periodic `spectral_fd` backend; the default `max_spatial_order=2` behavior remains preserved
- `pdelie.data.generate_kdv_1d_field_batch` for normalized periodic short-horizon synthetic KdV under the frozen v0.9 generator regime
- `pdelie.residuals.KdVResidualEvaluator` for the normalized strong-form residual `u_t + 6*u*u_x + u_xxx = 0`
- `pdelie.examples.run_kdv_vertical_slice_example` for a runtime smoke example, not a canonical report schema
- `pdelie.residuals.evaluate_weak_heat_residual` for deterministic window-indexed weak residual report dicts over canonical scalar 1D uniform periodic Heat `FieldBatch` data
- `pdelie.residuals.evaluate_weak_burgers_residual` for deterministic window-indexed weak residual report dicts over canonical scalar 1D uniform periodic Burgers `FieldBatch` data
- `pdelie.reporting.summarize_residual_batch` for JSON-compatible runtime summaries of `ResidualBatch` outputs
- `pdelie.reporting.summarize_weak_residual_report` for JSON-compatible summaries of frozen weak residual report dicts
- `pdelie.reporting.summarize_generator_family` for JSON-compatible summaries of `GeneratorFamily` coefficients and diagnostics
- `pdelie.reporting.summarize_generator_fit_diagnostics` for JSON-compatible summaries of generator-fit diagnostics, singular values, condition number, selected/SVD span distances, fallback status, and evidence labels
- `pdelie.reporting.summarize_verification_report` for JSON-compatible summaries of finite-transform verification sweeps
- `pdelie.reporting.summarize_vertical_slice` for nested derivative/residual/generator/verification runtime summaries
- `pdelie.reporting.summarize_invariant_workflow` for nested coverage, consistency, orbit, generator, fit-diagnostic, verification, and extra-metric runtime summaries
- `pdelie.invariants.InvariantApplier` for single-generator periodic `x` uniform translation only
- `pdelie.invariants.compute_periodic_window_coverage` for JSON-compatible grid-point coverage diagnostics over endpoint-excluded periodic 1D grids, half-open windows, and uniform translation shifts
- `pdelie.invariants.diagnose_uniform_translation_consistency` for JSON-compatible diagnostics of uniform-translation structure, inverse/period-wrap consistency, provenance, and optional residual stability
- `pdelie.invariants.summarize_uniform_translation_orbit` for read-only uniform `x`-translation orbit reports over canonical scalar 1D periodic `FieldBatch` inputs
- `pdelie.invariants.build_uniform_translation_orbit_batch` for materialized uniform `x`-translation orbit batches with provenance reports
- `pdelie.invariants.OrbitBatchResult` as a runtime-only structured result containing the materialized `FieldBatch` and report
- `pdelie.examples.run_orbit_coverage_diagnostics_example` for a runtime smoke example of the public orbit/coverage diagnostics, not a canonical report schema
- `pdelie.examples.run_invariant_workflow_summary_example` for a runtime smoke example combining Heat, KdV, coverage, orbit, fit, and verification summaries
- `pdelie.examples.run_translation_orbit_batch_example` for a runtime smoke example of materialized orbit batches, not a canonical report schema
- `pdelie.symmetry.validate_symmetry_candidate` for empirical configured validation reports over externally supplied `GeneratorFamily` and `InvariantMapSpec` candidates
- `pdelie.examples.run_symmetry_candidate_validation_example` for a runtime smoke example of external symmetry-candidate validation, not a canonical report schema
- `pdelie.discovery.to_pysindy_trajectories` for the narrow backend-specific PySINDy bridge
- `pdelie.discovery.evaluate_discovery_recovery` for runtime-only support/coefficient recovery metrics over caller-supplied canonical term strings
- `pdelie.discovery.fit_pysindy_discovery` for a runtime-only backend-native PySINDy fit adapter
- `pdelie.discovery.build_translation_canonical_discovery_inputs` for runtime-only heuristic translation-canonical discovery inputs
- `pdelie.discovery.summarize_recovery_grid` for runtime-only grouped recovery summaries
- `pdelie.data.add_gaussian_noise`, `subsample_time`, `subsample_x`, and `split_batch_train_heldout` for deterministic `FieldBatch` robustness workflows
- `pdelie.portability.export_generator_family_manifest` and `pdelie.portability.import_generator_family_manifest` for manifest-level generator-family portability
- `pdelie.portability.coerce_generator_family` for strict normalization of canonical, manifest, and narrow legacy translation inputs
- `pdelie.symmetry.render_generator_family` for deterministic symbolic display
- `pdelie.symmetry.to_sympy_component_expressions` when `sympy` is installed at runtime
- `pdelie.symmetry.compare_generator_spans` for runtime span diagnostics
- `pdelie.symmetry.diagnose_generator_family_closure` for runtime closure diagnostics
- `pdelie.viz.plot_generator_coefficients`, `plot_generator_symbolic_summary`, `plot_verification_curve`, `plot_span_diagnostics`, and `plot_closure_diagnostics` when `matplotlib` is installed

The degraded weak-path release wins in `v0.8` are frozen as representative contract-stability signals. They are fallback-backed release checks, not a general weak-superiority claim.

The KdV support retained through `v0.15` is normalized, periodic, scalar, 1D, and short-horizon. Accepted generator parameters outside the release-guaranteed regime are user-risk and are not general KdV stability guarantees.

The `v0.10` reporting helpers are supportability APIs. They produce JSON-compatible runtime summaries, not canonical objects, manuscript tables, or artifact schemas.

The `v0.11` KS feasibility track does not promote stable KS runtime support. Internal feasibility evidence passes residual, mass, and canonical held-out verification checks, but translation fitting is reference-fallback-backed rather than direct SVD in-tolerance recovery.

The `v0.12` diagnostics work hardens supportability without changing numerical scope. The public addition is the submodule-only `summarize_generator_fit_diagnostics(...)` helper. The internal KS diagnostic sweep and orbit/coverage feasibility helpers remain test-only evidence, not public runtime APIs.

The `v0.13` diagnostics work promotes only the reusable orbit/coverage reporting layer under `pdelie.invariants`. These diagnostics support invariant and finite-transform workflows but do not construct augmented datasets, orbit views, train branches, or manuscript artifacts.

The `v0.14` workflow work adds read-only orbit reports and combined invariant workflow summaries. These helpers combine existing reports and canonical objects into JSON-compatible runtime summaries; they do not construct augmented datasets, orbit datasets, transformed `FieldBatch` collections, or time-translation APIs.

The `v0.15` data-utility work adds materialized uniform translation orbit batches. This is the first conservative user-facing data utility beyond diagnostics: it returns a `FieldBatch` plus provenance report, preserves duplicate shifts, and records source/shift indices when requested. It still does not manage train/test splits, leakage policy, or downstream experiment design.

The `v0.15` orbit-batch helper constructs orbit-expanded data. It does not decide train/heldout policy or leakage safety. Serious workflows should keep source and shift indices enabled so materialized samples remain auditable.

The `v0.16` candidate-validation work adds detector interop through strict payload validation and empirical reports. `validated` means the configured checks passed under the supplied field, residual evaluator, epsilons, and optional reference; it is not a mathematical proof. Callable descriptors, learned detector training, formula-backed generators, KS promotion, and operator-facing APIs remain deferred.

Explicitly deferred:
- stable multi-generator PDE fitting
- multi-generator invariant machinery
- broad downstream discovery contracts
- `xarray.Dataset` support
- file-based dataset loaders
- multidimensional or nonuniform-grid ingestion
- metadata inference
- operator symmetry
- weak derivatives and broader weak-form methods beyond the frozen `v0.8` weak residual report slice
- weak KdV APIs
- custom KdV initial conditions or configurable KdV coefficients
- general KdV support outside the frozen normalized periodic short-horizon regime
- stable KS data generator, residual evaluator, vertical-slice example, imported parity, weak KS API, or root KS export
- public orbit-view builders beyond the frozen materialized uniform translation orbit batch helper
- train/test split management, heldout-leakage detection, or downstream augmentation policy
- transformed `FieldBatch` collections from reporting helpers
- time-translation APIs or `axis="time"` support
- broad adapters and interoperability work
