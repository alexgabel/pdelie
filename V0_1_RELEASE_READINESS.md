# V0.1 Release Readiness

## Release Target

- package version: `0.1.0rc1`
- git tag: `v0.1.0rc1`

## Done

- canonical V0.1 objects implemented with validation and serialization
- typed validation errors exported and documented
- synthetic 1D heat-equation `FieldBatch` generator implemented
- stable `spectral_fd` derivative backend implemented
- analytic heat `ResidualEvaluator` implemented
- polynomial spatial-translation baseline implemented
- finite-transform verification path implemented
- test suite passing from repo root
- environment setup, README, MVP example module, and CI workflow added
- RC validation covers editable install, built wheel install, stable imports, and the packaged example path

## Explicitly Deferred

- Burgers or any second PDE
- operator methods
- weak-form features beyond reserved interface surface
- `InvariantMap`, `InvariantLibrary`, or `DiscoveryResult` as stable implemented contracts
- broad dataset adapters or interoperability work
- paper-specific experiment logic

## Release Candidate View

The current repository is release-candidate ready for the documented V0.1 MVP slice, subject to CI passing on the default branch.

There are no known code or contract blockers for tagging a V0.1 release candidate inside the current scope.

## Packaging And Public API Notes

- `build` is now part of the test extra so RC validation can build artifacts from the project config.
- The stable public API is smoke-tested explicitly.
- The example module path documented in the README is now part of CI validation, including deterministic repeated output checks.
- `conda env create -f environment.yml` remains a manual RC checklist item outside CI.

## Tag Checklist

Before tagging `v0.1.0rc1`:

- run `python -m pytest` from the repo root
- run `python -m build --sdist --wheel`
- install the built wheel into a clean environment and verify stable imports
- run `python -m pdelie.examples.heat_vertical_slice`
- confirm GitHub Actions jobs `editable-tests` and `package-smoke` pass on the release commit
- tag the release commit as `v0.1.0rc1`
