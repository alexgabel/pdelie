# Notebooks

This directory contains tutorial notebooks for the shipped `v0.13` runtime surface.

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
If you only want the core library, install `python -m pip install -e .` and skip PySINDy-specific notebooks.

Jupyter itself is not a runtime dependency of `pdelie`; install notebook tooling separately in your environment.

## Curriculum Shape

The notebooks are intentionally orthogonal:

1. end-to-end tour
2. discovery-input canonicalization
3. robustness diagnostics
4. portability
5. fitted-vs-known generators
6. algebra diagnostics
7. orbit/coverage diagnostics

The ordering is progressive, but each notebook has a distinct theme.

## Notebook Index

- `00_how_to_use_pdelie_v0_6.ipynb`
  - current `v0.13` tour despite the historical filename
  - fields, derivatives, residuals, nested reports, KdV, weak reports, and invariant diagnostics
- `01_raw_vs_translation_canonical_discovery.ipynb`
  - raw versus translation-canonical Heat discovery inputs
  - visualizes batch-alignment effects and connects them to coverage diagnostics
- `02_robustness_sweeps.ipynb`
  - noise/subsampling robustness with strong residuals, weak reports, fit diagnostics, and recovery summaries
- `03_portability_round_trips.ipynb`
  - generator-family manifest export/import/coercion and post-round-trip diagnostics
- `04_discovered_vs_known_translation_generators.ipynb`
  - compares fitted Heat/Burgers/KdV translation generators against the known translation span
- `05_closure_algebra_diagnostics.ipynb`
  - algebraic closure and span diagnostics on small hand-built polynomial families
- `06_orbit_coverage_diagnostics.ipynb`
  - dedicated `v0.13` feature notebook for public orbit/coverage diagnostics under `pdelie.invariants`

## Running From VS Code

1. open the repo root
2. select the environment where `pdelie` is installed
3. open a notebook from this directory
4. run cells from top to bottom

## Notes

- discovery notebooks intentionally work with backend-native PySINDy outputs
- reporting helpers produce runtime summaries, not canonical artifact schemas
- orbit/coverage diagnostics do not construct augmented datasets
- KS remains internal feasibility/no-go evidence; no notebook promotes a public KS runtime API
- these notebooks should stay paper-agnostic and reusable for tutorials
