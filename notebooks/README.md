# Notebooks

This directory contains exploratory notebooks for the shipped `v0.6` runtime surface.

These notebooks are:

- tutorials and evaluation aids
- non-normative
- not part of the package stability contract
- intended to be run from the repo root after an editable install

Recommended environment for the discovery notebooks:

```bash
python -m pip install -e .[test]
```

That gives you the current downstream dependencies used by the PySINDy-related notebooks.

If you want to open the notebooks in JupyterLab or classic Jupyter, install notebook tooling separately in your environment.
The library itself does not treat Jupyter as a required runtime dependency.

## Notebook Index

- `00_how_to_use_pdelie_v0_6.ipynb`
  - quick tour of the shipped `v0.6` surface
- `01_raw_vs_translation_canonical_discovery.ipynb`
  - compares raw and translation-canonical discovery fits on Heat data
- `02_robustness_sweeps.ipynb`
  - explores noise/subsampling robustness and grouped recovery summaries
- `03_portability_round_trips.ipynb`
  - checks manifest export/import/coercion round-trips for `GeneratorFamily`
- `04_discovered_vs_known_translation_generators.ipynb`
  - compares discovered and known generators on Heat and Burgers
- `05_closure_algebra_diagnostics.ipynb`
  - probes closure diagnostics on small hand-built polynomial families

## Running From VS Code

1. open the repo root
2. select the environment where `pdelie` is installed
3. open a notebook from this directory
4. run cells from top to bottom

## Notes

- discovery notebooks intentionally work with backend-native PySINDy outputs
- when a notebook uses `evaluate_discovery_recovery(...)`, it explains the local basis being compared
- these notebooks are a good baseline for `v0.7` development because they exercise the shipped `v0.6` surfaces without adding new scope
