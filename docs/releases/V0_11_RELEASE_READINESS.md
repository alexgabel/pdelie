# V0.11 Release Readiness

## Release Target

- package version: `0.11.0`
- git tag: `v0.11.0`
- package-index publication: deferred until `v1.0` or later

`v0.11.0` is a Git-tag-only release.
Do not run TestPyPI or PyPI publishing for `v0.11`.

## Done

- M0 is complete:
  - `v0.11` was frozen as a Kuramoto-Sivashinsky feasibility-first release
  - `v0.10` was recorded as complete
  - stable KS promotion was made conditional on evidence
- M1 is complete:
  - normalized KS semantics were frozen as `u_t + u*u_x + u_xx + u_xxxx = 0`
  - fourth-derivative requirements and feasibility diagnostics were scoped
- M2 is complete:
  - `compute_spectral_fd_derivatives(..., max_spatial_order=4)` landed as the only public v0.11 API change
  - internal KS feasibility generator helpers were added under tests only
  - `API_STABILITY.md` documents the public order-4 derivative extension
- M3 is complete:
  - internal KS residual feasibility was validated under the frozen equation
  - no public KS residual evaluator landed
- M4 is complete:
  - internal KS vertical-slice feasibility was run through fitting and held-out verification
  - evidence was recorded as reference-fallback-backed, not direct SVD in-tolerance recovery
- M5 is complete:
  - stable KS runtime promotion was explicitly deferred for `v0.11`
  - public KS generator, residual, example, weak, and root exports remain absent
- M6 is complete:
  - package metadata and release-facing docs are aligned with `0.11.0`
  - this readiness note is current
  - the compact `v0_11-release-gate` is the current explicit release-gate CI job

## Public API Notes

New stable runtime API behavior in `v0.11`:

- `pdelie.derivatives.compute_spectral_fd_derivatives(..., max_spatial_order=4)` emits:
  - `u_t`
  - `u_x`
  - `u_xx`
  - `u_xxx`
  - `u_xxxx`

The default `max_spatial_order=2` behavior, config, diagnostics, and derivative outputs remain preserved.

Stable KS runtime promotion is deferred:

- no `pdelie.data.generate_ks_1d_field_batch`
- no `pdelie.residuals.KSResidualEvaluator`
- no `pdelie.examples.run_ks_vertical_slice_example`
- no root `pdelie` KS exports
- no weak KS API
- no KS imported parity

Retained stable surfaces include:

- Heat and Burgers strong paths
- `v0.8` weak Heat/Burgers residual report APIs
- `v0.9` normalized periodic short-horizon KdV strong path
- `v0.10` reporting helpers and nested Heat/KdV example summaries
- structured `from_numpy(...)` and optional `from_xarray(...)` ingestion
- existing discovery, portability, symmetry, and visualization runtime helpers

## KS Feasibility Evidence

The frozen internal KS fixture shows strong feasibility evidence:

- residual max absolute value: `2.276047466221332e-09`
- residual RMS value: `3.450580898077348e-10`
- mass drift: `4.686823294199099e-16`
- relative L2 drift: `0.0070894859776733715` as diagnostic-only
- selected span distance: `0.0`
- SVD span distance: `0.4178159498317849`
- fit mode: `reference_fallback`
- reference fallback used: `True`
- fallback reason: `svd_translation_span_drift`
- first-epsilon held-out verification error: `2.533384127588474e-13`
- verification classification: `exact`
- evidence label: `reference_fallback`

Interpretation:

- residual evaluation passes with large margin
- mass conservation passes with large margin
- held-out canonical translation verification passes
- selected span passes because the canonical reference fallback is used
- direct residual-based SVD fitting is out of tolerance
- therefore stable KS runtime promotion is deferred for `v0.11`

## Explicitly Deferred

- stable KS data generator
- stable KS residual evaluator
- KS vertical-slice example
- KS imported parity
- weak KS APIs
- root `pdelie` exports for KS runtime APIs
- broad dataset adapters
- multidimensional, multivariable, or nonuniform-grid support
- operator-facing APIs
- manuscript-specific experiment logic
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## CI Expectations

Before tagging `v0.11.0`, the release PR should have these CI jobs green:

- `v0_11-release-gate`
- `editable-tests`
- `package-smoke`

Historical release-gate test modules remain runnable locally and are covered by `editable-tests`.

## Local Release Checklist

Before tagging `v0.11.0`:

1. Inspect consistency across:
   - `pyproject.toml`
   - `README.md`
   - `CHANGELOG.md`
   - `docs/releases/V0_11_RELEASE_READINESS.md`
   - `docs/releases/PUBLISHING.md`
   - `docs/specs/API_STABILITY.md`
2. Run the full test suite:
   - `python -m pytest`
3. Build the package:
   - `python -m build --sdist --wheel`
4. Install `dist/pdelie-0.11.0-py3-none-any.whl` into a clean environment and verify:
   - stable root imports
   - `pdelie.reporting` helper imports from the submodule
   - one tiny weak Heat report
   - one tiny KdV strong-path residual
   - one tiny order-4 derivative smoke
   - root `pdelie` does not export KS runtime APIs
5. Run examples:
   - `python -m pdelie.examples.heat_vertical_slice`
   - `python -m pdelie.examples.kdv_vertical_slice`
6. Run:
   - `git diff --check`

## Direct Final Tag Checklist

After local checks and CI pass:

- merge the release PR into `main`
- tag the merged `main` commit as `v0.11.0`
- do not publish to TestPyPI
- do not publish to PyPI
- record package-index publishing as deferred until `v1.0` or later

## Final Release View

`v0.11.0` is ready when the local release checklist and the current CI jobs pass.

The stable release claim is intentionally narrow:

`existing Heat/Burgers/weak-report/KdV/reporting surfaces -> order-4 spectral derivatives -> internal KS feasibility evidence -> explicit stable-KS no-go/defer closeout`

There is no stable public KS runtime surface in `v0.11`.
