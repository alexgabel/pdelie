# V0.2 Release Readiness

## Release Target

- package version: `0.2.0rc1`
- git tag: `v0.2.0rc1`

## Done

- the stable canonical object set remains unchanged:
  `FieldBatch`, `DerivativeBatch`, `ResidualBatch`, `ResidualEvaluator`,
  `GeneratorFamily`, `VerificationReport`
- Heat remains supported under the existing stable path
- synthetic 1D Burgers is implemented as the second stable PDE
- the stable derivative backend remains `spectral_fd`
- analytic Heat and Burgers residual evaluators are implemented
- the polynomial spatial-translation fitting path works across Heat and Burgers
- the finite-transform verification path works across Heat and Burgers
- the matched cross-PDE benchmark / release-gate layer is implemented in the test surface
- the full test suite passes from the repo root
- packaging, editable install, built-wheel smoke validation, and the packaged example path remain in place

## Explicitly Deferred

- invariant pipelines as a stable feature
- weak-form methods beyond reserved interface surface
- operator methods
- broad dataset adapters or interoperability work
- new canonical stable objects beyond the current slice
- paper-specific experiment logic

## Release-Candidate View

The current repository is ready for the `0.2.0rc1` release candidate for the frozen V0.2 stable core, subject to the release-path checks passing on the release branch and CI passing on the release PR.

There are no known scientific-scope blockers inside the current V0.2 slice.

## Benchmark And Release-Gate Notes

- Heat and Burgers are both required to pass the same stable pipeline.
- Clean matched benchmark checks must classify as `exact` on both PDEs.
- Matched noisy held-out benchmark checks must classify as `exact` or `approximate` on both PDEs.
- The benchmark/release-gate layer remains internal to the test surface and is not a public API.

## RC Tag Checklist

Before tagging `v0.2.0rc1`:

- run `python -m pytest` from the repo root
- run `python -m build --sdist --wheel`
- install the built wheel into a clean environment and verify stable imports
- run `python -m pdelie.examples.heat_vertical_slice`
- confirm GitHub Actions jobs `editable-tests` and `package-smoke` pass on the release PR commit
- merge the release PR into `main`
- tag the merged `main` commit as `v0.2.0rc1`
