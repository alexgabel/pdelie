# Notebooks

This directory contains tutorial notebooks for the shipped `v0.17` runtime surface.

The tutorial promise is:

```text
PDE time series
-> canonical FieldBatch
-> residual target
-> fitted or supplied generator candidate
-> empirical confidence report
-> optional orbit materialization / downstream task
```

These notebooks are:

- progressive teaching material
- non-normative
- not part of the package stability contract
- intended to be run from the repo root after an editable install

Recommended environment:

```bash
python -m pip install -e .[test]
```

That installs the optional PySINDy, xarray, and Matplotlib dependencies used across the tutorial set.
If you only want the core library, install `python -m pip install -e .` and skip PySINDy-specific cells.

Jupyter itself is not a runtime dependency of `pdelie`; install notebook tooling separately in your environment.

## Recommended Learning Path

1. PDE time series to generators
2. confidence diagnostics under perturbation
3. invariant/orbit reports
4. materialized orbit batches with provenance
5. external and formula-backed symmetry candidates
6. downstream discovery templates

## Notebook Index

- `00_pde_timeseries_to_generators.ipynb`
  - quickstart for the current `v0.17` surface
  - canonical fields, derivatives, residuals, fitted generators, held-out verification, and confidence cards
- `01_raw_vs_translation_canonical_discovery.ipynb`
  - raw versus translation-canonical Heat discovery inputs
  - coverage diagnostics and `v0.15` orbit batches as auditable data utilities
- `02_robustness_sweeps.ipynb`
  - noise/subsampling/fit-epsilon sweeps using confidence-card metrics
  - residual RMS, conditioning, span distance, and verification error side by side
- `03_portability_round_trips.ipynb`
  - generator-family manifest export/import/coercion
  - empirical revalidation with `validate_symmetry_candidate(...)`
- `04_discovered_vs_known_translation_generators.ipynb`
  - compares fitted `GeneratorFamily`, finite `InvariantMapSpec`, formula-backed `FormulaGeneratorFamily`, and failed candidates under one validation language
- `05_closure_algebra_diagnostics.ipynb`
  - algebraic closure diagnostics for polynomial families
  - formula-backed metadata and the distinction between empirical validation and proof
- `06_orbit_coverage_diagnostics.ipynb`
  - public coverage diagnostics, translation-consistency reports, read-only orbit reports, and materialized orbit batches
- `07_external_symmetry_candidates.ipynb`
  - dedicated `v0.16-v0.17` candidate-validation tutorial
  - validates fitted, finite-map, formula-backed, and deliberately failed candidates
- `08_downstream_task_template.ipynb`
  - paper-agnostic downstream workflow template
  - optional orbit materialization, PySINDy bridge inputs, generator validation, and recovery metrics

## Running From VS Code

1. open the repo root
2. select the environment where `pdelie` is installed
3. open a notebook from this directory
4. run cells from top to bottom

## Notes

- confidence cards are a notebook teaching pattern, not a package API
- discovery notebooks intentionally work with backend-native PySINDy outputs
- reporting helpers produce runtime summaries, not canonical artifact schemas
- orbit/coverage reports do not construct augmented datasets
- materialized orbit batches construct orbit-expanded data but do not decide train/heldout policy, split management, or leakage safety
- keep source and shift indices enabled when using orbit batches in serious workflows
- `FormulaGeneratorFamily` stores safe JSON expression metadata; it does not parse executable strings, accept callables, or train learned generators
- KS remains internal feasibility/no-go evidence; no notebook promotes a public KS runtime API
- these notebooks should stay paper-agnostic and reusable for tutorials
