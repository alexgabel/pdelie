# V0.12 Release Readiness

## Release Target

- package version: `0.12.0`
- git tag: `v0.12.0`
- package-index publication: deferred until `v1.0` or later

`v0.12.0` is a Git-tag-only release.
Do not run TestPyPI or PyPI publishing for `v0.12`.

## Done

- M0 is complete:
  - `v0.12` was frozen as diagnostics and supportability hardening
  - `v0.11` was recorded as a completed KS feasibility/no-go release
  - stable KS promotion remained closed as deferred
- M1 is complete:
  - generator-fit diagnostic semantics were frozen
  - evidence labels and fallback reason categories were fixed
- M2 is complete:
  - `pdelie.reporting.summarize_generator_fit_diagnostics(...)` landed as the only public `v0.12` API addition
  - `fit_translation_generator(...)` gained richer diagnostics without changing coefficient selection
  - `API_STABILITY.md` documents the new reporting helper
- M3 is complete:
  - internal KS fit diagnostic sweeps confirmed fallback-backed evidence across the frozen epsilon and fixture-variant matrix
  - no public KS API landed
- M4 is complete:
  - internal orbit/coverage feasibility diagnostics passed on stable Heat and KdV fixtures
  - no public orbit/coverage helper or augmentation utility landed
- M5 is complete:
  - API stability and public-surface guards confirmed the `v0.12` public surface
  - internal M3/M4 helpers remained test-only
- M6 is complete:
  - package metadata and release-facing docs are aligned with `0.12.0`
  - this readiness note is current
  - the compact `v0_12-release-gate` is the current explicit release-gate CI job

## Public API Notes

New stable runtime API in `v0.12`:

- `pdelie.reporting.summarize_generator_fit_diagnostics(generator)`

The helper returns a JSON-compatible runtime summary of `GeneratorFamily` fit diagnostics, including:

- singular values
- condition number
- selected coefficients
- selected span distance
- SVD coefficients
- SVD span distance
- fit mode
- fallback status and reason
- evidence label

The helper is submodule-only:

- import from `pdelie.reporting`
- no root `pdelie` export
- no new canonical object
- no fitting algorithm change
- no promotion gate

Retained stable surfaces include:

- Heat and Burgers strong paths
- `v0.8` weak Heat/Burgers residual report APIs
- `v0.9` normalized periodic short-horizon KdV strong path
- `v0.10` reporting helpers and nested Heat/KdV example summaries
- `v0.11` order-4 spectral derivative extension
- structured `from_numpy(...)` and optional `from_xarray(...)` ingestion
- existing discovery, portability, symmetry, and visualization runtime helpers

## Internal Diagnostic Evidence

### KS Diagnostic Sweep

The bounded internal KS sweep remained diagnostic-only.
All frozen variants concluded:

`fallback_stable_across_epsilons`

Default variant evidence:

- residual max absolute value: `2.276047466221332e-09`
- residual RMS value: `3.450580898077348e-10`
- mass drift: `4.686823294199099e-16`
- relative L2 drift: `0.0070894859776733715` as diagnostic-only
- condition-number median: `214513.53360977306`
- SVD span-distance median: `0.4178159498317849`
- direct SVD in tolerance: `False`
- fallback reason stable: `True`
- fallback reason: `svd_translation_span_drift`

Interpretation:

- KS residual and canonical held-out verification behavior remain healthy
- direct residual-based SVD fitting remains out of tolerance
- stable KS runtime promotion remains deferred

### Orbit / Coverage Feasibility

The internal orbit/coverage feasibility helper remained test-only.

Coverage cases:

- half-coverage quarter-shift case: `32 / 64` points, coverage fraction `0.5`
- full-coverage quarter-shift case: `64 / 64` points, coverage fraction `1.0`

Transform consistency:

- stable Heat and KdV fixtures preserved dims, coords, var names, metadata, and mask under uniform translations
- inverse-transform and period-wrap errors remained at floating-point noise levels
- residual RMS stayed stable under shifts
- provenance recorded `operation == "invariant_apply"` and `construction_method == "uniform_translation"`

Interpretation:

- paper-agnostic orbit/coverage diagnostics are feasible
- no public orbit/coverage helper landed
- no public augmentation utility landed

## Explicitly Deferred

- new PDE support
- stable KS data generator
- stable KS residual evaluator
- KS vertical-slice example
- KS imported parity
- weak KS APIs
- root `pdelie` exports for KS runtime APIs
- public orbit/coverage helpers
- public augmentation utilities
- broad dataset adapters
- PDEBench or The Well support
- multidimensional, multivariable, or nonuniform-grid support
- operator-facing APIs
- manuscript-specific experiment logic
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## CI Expectations

Before tagging `v0.12.0`, the release PR should have these CI jobs green:

- `v0_12-release-gate`
- `editable-tests`
- `package-smoke`

Historical release-gate test modules remain runnable locally and are covered by `editable-tests`.

## Local Release Checklist

Before tagging `v0.12.0`:

1. Inspect consistency across:
   - `pyproject.toml`
   - `README.md`
   - `CHANGELOG.md`
   - `docs/releases/V0_12_RELEASE_READINESS.md`
   - `docs/releases/PUBLISHING.md`
   - `docs/specs/API_STABILITY.md`
2. Run the full test suite:
   - `python -m pytest`
3. Build the package:
   - `python -m build --sdist --wheel`
4. Install `dist/pdelie-0.12.0-py3-none-any.whl` into a clean environment and verify:
   - stable root imports
   - `pdelie.reporting` helper imports from the submodule, including `summarize_generator_fit_diagnostics`
   - one tiny weak Heat report
   - one tiny KdV strong-path residual
   - one tiny order-4 derivative smoke
   - one tiny generator-fit diagnostic summary
   - root `pdelie` does not export KS, orbit/coverage, augmentation, or weak KS APIs
5. Run examples:
   - `python -m pdelie.examples.heat_vertical_slice`
   - `python -m pdelie.examples.kdv_vertical_slice`
6. Run:
   - `git diff --check`

## Direct Final Tag Checklist

After local checks and CI pass:

- merge the release PR into `main`
- tag the merged `main` commit as `v0.12.0`
- do not publish to TestPyPI
- do not publish to PyPI
- record package-index publishing as deferred until `v1.0` or later

## Final Release View

`v0.12.0` is ready when the local release checklist and the current CI jobs pass.

The stable release claim is intentionally narrow:

`existing Heat/Burgers/weak-report/KdV/reporting surfaces -> generator-fit diagnostic summaries -> internal KS diagnostic sweep evidence -> internal orbit/coverage feasibility -> release supportability`

M3 internal KS diagnostics and M4 orbit/coverage diagnostics remain internal.
The final release view is that no stable KS runtime API is promoted.
