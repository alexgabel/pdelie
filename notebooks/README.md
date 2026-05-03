# PDELie Tutorial Notebooks

This directory is the recommended entry point for new PDELie users on the shipped `v0.20` surface.

Tutorial promise:

```text
PDE time series
-> canonical FieldBatch
-> derivatives/residuals
-> generator or symmetry candidate
-> empirical validation/reporting
-> optional orbit materialization
-> optional downstream sparse-discovery task
```

These notebooks are tutorials, not API contracts. Example outputs are runtime summaries, not canonical paper artifacts.

## Who These Notebooks Are For

- ML/PDE researchers evaluating whether PDELie fits their workflow.
- Graduate students learning how Lie-symmetry diagnostics connect to numerical PDE data.
- Users with scalar 1D periodic PDE time series who want a responsible path from data to generator candidates.
- Developers extending PDELie while keeping public API and experimental boundaries clear.

## What PDELie Is Good For

- Converting supported arrays into canonical `FieldBatch` objects.
- Computing `spectral_fd` derivatives on uniform periodic 1D grids.
- Evaluating strong residuals for the stable Heat, Burgers, KdV, Fisher-KPP, and advection-diffusion paths.
- Fitting and validating polynomial translation generators in the stable slice.
- Producing JSON-compatible residual, fit, verification, invariant, orbit, candidate, and formula summaries.
- Producing categorical generator confidence reports with `summarize_generator_confidence(...)`.
- Auditing finite uniform x-translation workflows with coverage, consistency, and provenance reports.
- Materializing uniform translation orbit batches while preserving source/shift provenance.
- Validating externally supplied `GeneratorFamily`, `InvariantMapSpec`, and `FormulaGeneratorFamily` candidates empirically.

## What PDELie Is Not

- Not a mathematical proof engine.
- Not a neural symmetry-detector training framework.
- Not a broad PDEBench/The Well adapter layer.
- Not a train/test split manager or leakage detector.
- Not an operator-learning framework.
- Not a paper-specific experiment pipeline.
- Not a general nonuniform or multidimensional PDE framework in `v0.20`.

KS remains internal feasibility/no-go evidence. `v0.19` advection-diffusion is implemented only as a frozen scalar 1D periodic constant-coefficient strong path.

## Installation

Core editable install:

```bash
python -m pip install -e .
```

Test/tutorial environment used by CI:

```bash
python -m pip install -e .[test]
```

Optional focused extras:

```bash
python -m pip install -e .[downstream]  # PySINDy bridge path
python -m pip install -e .[xarray]      # from_xarray ingestion
python -m pip install -e .[viz]         # Matplotlib plotting helpers
```

Jupyter itself is not a core runtime dependency. Install notebook tooling in your environment separately.

## Recommended Learning Path

1. `00_pde_timeseries_to_generators.ipynb` - quickstart from PDE time series to generator evidence.
2. `02_robustness_sweeps.ipynb` - confidence diagnostics under perturbation.
3. `06_orbit_coverage_diagnostics.ipynb` - invariant/orbit reports and materialized orbit batches.
4. `03_portability_round_trips.ipynb` - generator export/import plus revalidation.
5. `07_external_symmetry_candidates.ipynb` - external and formula-backed candidate validation.
6. `08_downstream_task_template.ipynb` - paper-agnostic downstream sparse-discovery template.

## Notebook Index

| Notebook | Main concept | Required extras | Est. runtime | Stable APIs used | Out-of-scope warnings |
| --- | --- | --- | --- | --- | --- |
| `00_pde_timeseries_to_generators.ipynb` | Heat, Fisher-KPP, and advection-diffusion quickstart: field, derivatives, residual, fit, verify, confidence card | `.[viz]` or `.[test]` for plots | 1-2 min | `FieldBatch`, `compute_spectral_fd_derivatives`, Heat/Fisher-KPP/advection-diffusion residuals, `summarize_vertical_slice` | no proof, no KS, no weak form |
| `01_raw_vs_translation_canonical_discovery.ipynb` | Raw vs translation-canonical discovery inputs plus orbit-batch contrast | `.[downstream]` or `.[test]` | ~1 min | discovery bridge, coverage diagnostics, orbit batch builder | not a benchmark, no split/leakage policy |
| `02_robustness_sweeps.ipynb` | Noise/subsampling/fit-epsilon diagnostics | `.[viz]` or `.[test]` | 1-2 min | robustness helpers, fit diagnostics, verification summaries | no robustness guarantee |
| `03_portability_round_trips.ipynb` | Generator manifest export/import and empirical revalidation | core | <1 min | portability helpers, `validate_symmetry_candidate` | serialization is not scientific validity |
| `04_discovered_vs_known_translation_generators.ipynb` | Compare fitted, finite-map, formula-backed, and failed candidates | core | <1 min | `GeneratorFamily`, `InvariantMapSpec`, `FormulaGeneratorFamily`, candidate validation | no learned detector, no proof |
| `05_closure_algebra_diagnostics.ipynb` | Closure, span, symbolic/formula metadata distinction | core | <1 min | closure/span diagnostics, formula summaries | closure is not residual invariance |
| `06_orbit_coverage_diagnostics.ipynb` | Coverage, consistency, read-only orbit reports, materialized orbit batches | `.[viz]` optional | ~1 min | `compute_periodic_window_coverage`, `diagnose_uniform_translation_consistency`, orbit reports/batches | no train/test policy, grid-point coverage only |
| `07_external_symmetry_candidates.ipynb` | Interop dashboard for external/formula candidates | core | <1 min | `validate_symmetry_candidate`, formula records | no callables, no neural training |
| `08_downstream_task_template.ipynb` | External data and downstream sparse-discovery workflow template | `.[downstream]` or `.[test]` for PySINDy smoke | ~1 min | `from_numpy`, orbit batches, PySINDy bridge, recovery metrics | no paper policy, no threshold policy |

## Running From VS Code Or Jupyter

1. Open the repo root.
2. Select the Python environment where `pdelie` is installed.
3. Open a notebook from `notebooks/`.
4. Run cells from top to bottom.

Run from the repo root so imports like `notebooks._tutorial_utils` resolve cleanly.

## Using External Data

For your own scalar 1D periodic data:

1. arrange values so they can be interpreted as `batch/time/x/var`
2. use `pdelie.data.from_numpy(...)` or optional `pdelie.data.from_xarray(...)`
3. ensure `x` is uniform, periodic, and endpoint-excluded before using spectral/invariant tools
4. provide metadata tags that match the residual evaluator you plan to use
5. validate finite, unmasked scalar values before fitting or verification

Nonuniform, multidimensional, PDEBench/The Well, and operator-learning data are deferred scope.

## Adapting To Downstream Tasks

The notebooks show where to plug in your own model, loss, optimizer, or sparse-regression backend.

PDELie can prepare canonical data, materialize translation orbits, validate generator candidates, and export backend-native arrays. It does not decide:

- train/test split policy
- leakage safety
- threshold policy
- benchmark success criteria
- manuscript claims

Orbit batches construct orbit-expanded data. They do not manage train/heldout splits or leakage. Keep source and shift indices enabled for serious workflows.

## Interpretation Notes

- `summarize_generator_confidence(...)` is the package API for categorical confidence reports; notebook display helpers remain tutorial glue.
- Reporting helpers produce runtime summaries, not canonical artifact schemas.
- `validate_symmetry_candidate(...)` reports empirical configured validation, not proof.
- `FormulaGeneratorFamily` stores safe JSON AST metadata; it does not execute strings or callables.
- Materialized orbit batches are useful data utilities, not an augmentation policy.
- Examples stay paper-agnostic and lightweight by design.
