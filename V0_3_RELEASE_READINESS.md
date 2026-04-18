# V0.3 Release Readiness

## Release Target

- package version: `0.3.0rc1`
- git tag: `v0.3.0rc1`

## Done

- the stable canonical object set now includes `InvariantMapSpec`
- Heat remains supported under the existing stable path
- Burgers remains supported under the existing stable path
- the stable derivative backend remains `spectral_fd`
- analytic Heat and Burgers residual evaluators remain in place
- the polynomial spatial-translation fitting path remains the stable fitting slice
- the finite-transform verification path remains the stable verification slice
- runtime-only `InvariantApplier` is implemented for the frozen single-generator periodic `x` uniform-translation path
- runtime-only `pdelie.discovery.to_pysindy_trajectories` is implemented as the narrow backend-specific PySINDy bridge
- the internal four-branch downstream benchmark / release-gate layer is implemented under frozen settings
- the full test suite passes from the repo root
- packaging metadata, editable install, built-wheel smoke validation, and the packaged example path remain in place

## Explicitly Deferred

- weak-form methods beyond reserved interface surface
- operator methods
- multi-generator invariant machinery
- broad dataset adapters or interoperability work
- broad downstream discovery contracts beyond the current slice
- new canonical stable objects beyond the current V0.3 slice
- paper-specific experiment logic

## RC View

The current repository is ready for the first `0.3.0rc1` release candidate for the frozen V0.3 stable core, subject to the release-path checks passing on the release branch and CI passing on the release PR.

There are no known scientific-scope blockers inside the current V0.3 slice.

## Packaging And Public API Notes

- `InvariantMapSpec` is the only new stable canonical object in `v0.3`.
- `InvariantApplier` and `to_pysindy_trajectories` are runtime-level public APIs, not canonical objects.
- the optional PySINDy bridge path is currently validated on the PySINDy 1.x / scikit-learn 1.2.x line under Python `<3.12`
- the four-branch downstream benchmark / release-gate layer remains internal to the test surface and is not a public API

## RC Tag Checklist

Before tagging `v0.3.0rc1`:

- run `python -m pytest` from the repo root
- run `python -m build --sdist --wheel`
- install the built wheel into a clean environment and verify stable imports
- run `python -m pdelie.examples.heat_vertical_slice`
- confirm GitHub Actions jobs `editable-tests` and `package-smoke` pass on the release PR commit
- merge the release PR into `main`
- tag the merged `main` commit as `v0.3.0rc1`
