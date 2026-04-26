# pdelie

Numerical discovery and verification of Lie symmetries for PDE data.

The current repository implements the frozen V0.7 structured external-data ingestion and symmetry/discovery utilities core on the scalar 1D Heat/Burgers slice:

- synthetic 1D heat equation
- synthetic 1D Burgers equation
- strict external structured ingestion into canonical `FieldBatch`
- uniform periodic grid
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

The repository includes exploratory notebooks under `notebooks/` for the shipped symmetry/discovery runtime surface that remains part of `v0.7`:

- `00_how_to_use_pdelie_v0_6.ipynb`
- `01_raw_vs_translation_canonical_discovery.ipynb`
- `02_robustness_sweeps.ipynb`
- `03_portability_round_trips.ipynb`
- `04_discovered_vs_known_translation_generators.ipynb`
- `05_closure_algebra_diagnostics.ipynb`

These notebooks are non-normative tutorials, not stability contracts.
Most discovery notebooks require the downstream extras (`.[downstream]` or `.[test]`).

## Minimal End-To-End Example

Run the packaged example module from the repo root:

```bash
python -m pdelie.examples.heat_vertical_slice
```

That exact command is validated in CI both after editable install and after built-wheel packaging smoke checks.

The packaged example currently demonstrates the stable Heat verification path only:

1. generate synthetic heat-equation data
2. compute `spectral_fd` derivatives
3. evaluate the analytic heat residual
4. fit the polynomial spatial-translation baseline
5. verify the generator on held-out heat batches

The packaged example remains Heat-only even though the frozen stable slice also covers Burgers.

You can also call the example programmatically:

```python
from pdelie.examples import run_heat_vertical_slice_example

result = run_heat_vertical_slice_example()
print(result["verification_classification"])
```

## Current Scope

Included in the current stable core:

- stable canonical objects and typed validation errors, including `InvariantMapSpec`
- synthetic heat and Burgers data
- strict structured external-data ingestion into canonical `FieldBatch` via `from_numpy(...)` and `from_xarray(...)`
- polynomial translation baseline for the stable PDE slice
- finite-transform verification for the stable PDE slice
- family-shaped `GeneratorFamily` serialization and narrow translation compatibility migration
- manifest export/import for canonical `GeneratorFamily` portability
- strict external-family normalization for canonical payloads, manifests, and the narrow legacy translation payload
- single-generator invariant map support
- runtime-only discovery recovery metrics, backend-native PySINDy discovery fits, translation-canonical discovery inputs, robustness utilities, and structured-ingestion parity coverage for the current Heat/Burgers slice
- matched Heat/Burgers benchmark and release-gate checks in the test layer
- KdV feasibility passed in a tests-first slice, but KdV remains non-stable in V0.7

Runtime-level public APIs in the frozen V0.7 slice:

- `pdelie.data.from_numpy` for strict runtime conversion of explicit NumPy/array-like 1D uniform rectilinear trajectory data into canonical `FieldBatch`
- `pdelie.data.from_xarray` for strict runtime conversion of explicit `xarray.DataArray` 1D uniform rectilinear trajectory data into canonical `FieldBatch` when the optional `xarray` dependency is installed
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

Explicitly deferred:
- stable multi-generator PDE fitting
- multi-generator invariant machinery
- broad downstream discovery contracts
- `xarray.Dataset` support
- file-based dataset loaders
- multidimensional or nonuniform-grid ingestion
- metadata inference
- operator symmetry
- weak-form features
- broad adapters and interoperability work
