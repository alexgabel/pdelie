# pdelie

Numerical discovery and verification of Lie symmetries for PDE data.

The current repository implements the frozen V0.10 supportability layer for the existing Heat/Burgers/weak-report/KdV engine:

- synthetic 1D heat equation
- synthetic 1D Burgers equation
- synthetic normalized periodic short-horizon KdV
- strict external structured ingestion into canonical `FieldBatch`
- deterministic window-indexed weak residual reports under `pdelie.residuals`
- JSON-compatible runtime supportability summaries under `pdelie.reporting`
- uniform periodic grid
- `spectral_fd` derivatives through `u_xxx`
- normalized KdV strong residuals under `pdelie.residuals.KdVResidualEvaluator`
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
- one compact current release-gate CI job plus full editable tests and package smoke

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

The repository includes exploratory notebooks under `notebooks/` for the shipped symmetry/discovery runtime surface retained through `v0.10`:

- `00_how_to_use_pdelie_v0_6.ipynb`
- `01_raw_vs_translation_canonical_discovery.ipynb`
- `02_robustness_sweeps.ipynb`
- `03_portability_round_trips.ipynb`
- `04_discovered_vs_known_translation_generators.ipynb`
- `05_closure_algebra_diagnostics.ipynb`

These notebooks are non-normative tutorials, not stability contracts.
Most discovery notebooks require the downstream extras (`.[downstream]` or `.[test]`).

## Minimal End-To-End Example

Run the packaged example modules from the repo root:

```bash
python -m pdelie.examples.heat_vertical_slice
python -m pdelie.examples.kdv_vertical_slice
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

You can also call the examples programmatically.
They return nested `pdelie.reporting.summarize_vertical_slice(...)` runtime summaries, not canonical artifact schemas:

```python
from pdelie.examples import run_heat_vertical_slice_example, run_kdv_vertical_slice_example

result = run_kdv_vertical_slice_example()
print(result["verification"]["classification"])
```

## Current Scope

Included in the current stable core:

- stable canonical objects and typed validation errors, including `InvariantMapSpec`
- synthetic heat, Burgers, and normalized periodic short-horizon KdV data
- strict structured external-data ingestion into canonical `FieldBatch` via `from_numpy(...)` and `from_xarray(...)`
- stable weak residual report APIs under `pdelie.residuals` for Heat and Burgers
- stable normalized KdV strong residual evaluator under `pdelie.residuals`
- stable supportability reporting helpers under `pdelie.reporting`
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

Runtime-level public APIs in the frozen V0.10 slice:

- `pdelie.data.from_numpy` for strict runtime conversion of explicit NumPy/array-like 1D uniform rectilinear trajectory data into canonical `FieldBatch`
- `pdelie.data.from_xarray` for strict runtime conversion of explicit `xarray.DataArray` 1D uniform rectilinear trajectory data into canonical `FieldBatch` when the optional `xarray` dependency is installed
- `pdelie.derivatives.compute_spectral_fd_derivatives(..., max_spatial_order=3)` for `u_xxx` on the existing uniform periodic `spectral_fd` backend
- `pdelie.data.generate_kdv_1d_field_batch` for normalized periodic short-horizon synthetic KdV under the frozen v0.9 generator regime
- `pdelie.residuals.KdVResidualEvaluator` for the normalized strong-form residual `u_t + 6*u*u_x + u_xxx = 0`
- `pdelie.examples.run_kdv_vertical_slice_example` for a runtime smoke example, not a canonical report schema
- `pdelie.residuals.evaluate_weak_heat_residual` for deterministic window-indexed weak residual report dicts over canonical scalar 1D uniform periodic Heat `FieldBatch` data
- `pdelie.residuals.evaluate_weak_burgers_residual` for deterministic window-indexed weak residual report dicts over canonical scalar 1D uniform periodic Burgers `FieldBatch` data
- `pdelie.reporting.summarize_residual_batch` for JSON-compatible runtime summaries of `ResidualBatch` outputs
- `pdelie.reporting.summarize_weak_residual_report` for JSON-compatible summaries of frozen weak residual report dicts
- `pdelie.reporting.summarize_generator_family` for JSON-compatible summaries of `GeneratorFamily` coefficients and diagnostics
- `pdelie.reporting.summarize_verification_report` for JSON-compatible summaries of finite-transform verification sweeps
- `pdelie.reporting.summarize_vertical_slice` for nested derivative/residual/generator/verification runtime summaries
- `pdelie.invariants.InvariantApplier` for single-generator periodic `x` uniform translation only
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

The KdV support retained through `v0.10` is normalized, periodic, scalar, 1D, and short-horizon. Accepted generator parameters outside the release-guaranteed regime are user-risk and are not general KdV stability guarantees.

The `v0.10` reporting helpers are supportability APIs. They produce JSON-compatible runtime summaries, not canonical objects, manuscript tables, or artifact schemas.

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
- broad adapters and interoperability work
