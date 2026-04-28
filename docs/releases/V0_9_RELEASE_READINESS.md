# V0.9 Release Readiness

## Release Target

- package version: `0.9.0`
- git tag: `v0.9.0`
- package-index publication: deferred until `v1.0` or later

`v0.9.0` is a Git-tag-only release.
Do not run TestPyPI or PyPI publishing for `v0.9`.

## Done

- M0 is complete:
  - `v0.9` was frozen as the stable normalized periodic KdV strong-path release
  - exact derivative, generator, residual, vertical-slice, and imported-parity scope was documented
- M1 is complete:
  - `compute_spectral_fd_derivatives(..., max_spatial_order=3)` adds `u_xxx`
  - default `max_spatial_order=2` behavior remains compatible with `v0.8`
- M2 is complete:
  - `pdelie.data.generate_kdv_1d_field_batch(...)` is implemented
  - generated data is canonical scalar 1D uniform periodic `FieldBatch` data
- M3 is complete:
  - `pdelie.residuals.KdVResidualEvaluator` is implemented
  - normalized residual form is `u_t + 6*u*u_x + u_xxx = 0`
- M4 is complete:
  - KdV translation fitting and held-out verification pass the frozen vertical slice
  - `python -m pdelie.examples.kdv_vertical_slice` is available as a runtime smoke
- M5 is complete:
  - mandatory `from_numpy` KdV imported parity passes
  - optional `from_xarray` KdV parity skips cleanly when xarray is unavailable
  - weak KdV, root KdV exports, and broad adapter expansion remain absent
- M6 is complete:
  - compact `v0_9-release-gate` is implemented
  - CI visibility includes `v0_9-release-gate`
  - package metadata and release-facing docs are aligned with `0.9.0`
  - wheel smoke includes a tiny KdV strong-path check

## Observed KdV Release Fixture

Frozen fixture:

- generator seed: `9001`
- `batch_size = 5`
- `train_size = 2`
- split seed: `9002`
- all other generator settings default

Observed values:

- max absolute residual: `0.0029755398453998883`
- RMS residual: `0.0005530662104030956`
- mass drift: `1.529348589458863e-16`
- relative L2 drift: `4.353026792731057e-14`
- translation span distance: `0.007441277120177836`
- first-epsilon held-out verification error: `3.7632323492784305e-06`
- verification classification: `approximate`
- fit mode: `svd`
- reference fallback used: `False`

The release gate requires non-failed verification, not exact classification.
The observed `approximate` classification is acceptable under the frozen `v0.9` criteria.

## Explicitly Deferred

- weak KdV APIs
- weak derivative APIs or broader weak-form expansion
- root `pdelie` exports for KdV runtime APIs
- custom KdV initial conditions
- configurable KdV coefficients
- general KdV stability guarantees outside the frozen short-horizon release fixtures
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## Final Release View

The current repository is ready for the final `0.9.0` Git tag for the frozen `v0.9` normalized periodic KdV strong path, subject to release-path checks passing on the release branch and CI passing on the release PR.

There are no known scientific-scope blockers inside the frozen `v0.9` slice.

The stable `v0.9` claim remains narrow:

- normalized periodic short-horizon KdV generator
- `spectral_fd` third spatial derivative support
- normalized KdV strong-form residual evaluator
- KdV translation fitting and held-out verification on the frozen fixture
- mandatory `from_numpy` imported parity for representative KdV data
- no weak KdV
- no general KdV support

## Packaging And Public API Notes

- `pdelie.derivatives.compute_spectral_fd_derivatives(..., max_spatial_order=3)` is stable for `u_xxx`
- `pdelie.data.generate_kdv_1d_field_batch` is stable under the frozen v0.9 normalized periodic short-horizon regime
- `pdelie.residuals.KdVResidualEvaluator` is stable for the normalized strong-form KdV residual
- `pdelie.examples.run_kdv_vertical_slice_example` is a runtime smoke example, not a canonical report schema
- KdV runtime APIs are exposed from submodules only, not root `pdelie`
- `pdelie.residuals.evaluate_weak_heat_residual` and `pdelie.residuals.evaluate_weak_burgers_residual` remain stable runtime APIs from `v0.8`
- `pdelie.data.from_numpy` and `pdelie.data.from_xarray` remain stable runtime public APIs from `v0.7`
- the `v0_4-release-gate`, `v0_5-release-gate`, `v0_6-release-gate`, `v0_7-release-gate`, `v0_8-release-gate`, and `v0_9-release-gate` CI jobs are explicit visibility checks
- post-`v0.9` CI consolidation is a follow-up item and is not part of this release

## Direct Final Tag Checklist

Before tagging `v0.9.0`:

- inspect consistency across:
  - `pyproject.toml`
  - `README.md`
  - `CHANGELOG.md`
  - `docs/releases/V0_9_RELEASE_READINESS.md`
  - `docs/releases/PUBLISHING.md`
  - `docs/specs/API_STABILITY.md`
- run `python -m pytest` from the repo root
- run `python -m build --sdist --wheel`
- install the built wheel into a clean environment and verify:
  - stable root imports
  - weak residual runtime imports under `pdelie.residuals`
  - one tiny weak Heat report smoke
  - one tiny KdV strong-path smoke
- run `python -m pdelie.examples.heat_vertical_slice`
- run `python -m pdelie.examples.kdv_vertical_slice`
- confirm GitHub Actions jobs `v0_4-release-gate`, `v0_5-release-gate`, `v0_6-release-gate`, `v0_7-release-gate`, `v0_8-release-gate`, `v0_9-release-gate`, `editable-tests`, and `package-smoke` pass on the release PR commit
- merge the release PR into `main`
- tag the merged `main` commit as `v0.9.0`
- do not publish to TestPyPI
- do not publish to PyPI
- record package-index publishing as deferred until `v1.0` or later
