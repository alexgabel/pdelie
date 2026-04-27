# V0.8 Release Readiness

## Release Target

- package version: `0.8.0`
- git tag: `v0.8.0`

## Done

- the canonical stable object set from `v0.7` remains in place, including `InvariantMapSpec`
- the stable derivative backend remains `spectral_fd`
- analytic Heat and Burgers residual evaluators remain in place unchanged
- the `v0.7` structured-ingestion runtime surface remains in place:
  - `pdelie.data.from_numpy(...)`
  - `pdelie.data.from_xarray(...)`
- M0 is complete:
  - `v0.8` was frozen as the next committed release before runtime implementation
  - the weak residual report shape, weak-profile family, and benchmark matrix were documented explicitly
- M1 is complete:
  - the quartic-bump weak profile, exact Heat/Burgers weak identities, and deterministic benchmark fixtures were frozen
- M2 is complete:
  - `pdelie.residuals.evaluate_weak_heat_residual(...)` is implemented
  - `pdelie.residuals.evaluate_weak_burgers_residual(...)` is implemented
  - both APIs return deterministic window-indexed weak residual report dicts rather than canonical `ResidualBatch`
- M3 is complete:
  - internal report-space fitting and verification feasibility landed under `tests/_helpers`
  - stable contract integration remains deferred
- M4 is complete:
  - the frozen representative robustness benchmark landed
  - the compact `v0_8-release-gate` test module and CI visibility job are implemented
  - required `from_numpy` imported parity landed for the frozen subset
- M5 is complete:
  - weak KdV stress was explicitly deferred because the frozen `v0.8` quartic-bump profile is not boundary-regular enough for an honest KdV weak form
- M6 is complete:
  - release metadata and release-facing docs are aligned with the implemented `v0.8` surface
  - wheel smoke covers a tiny weak Heat report path in addition to the existing example smoke

## Observed M4 Release Signal

The `v0.8` degraded release signal is intentionally narrow.
It is a frozen representative release signal, not a general claim of weak superiority.

Observed degraded winners on the current benchmark:

- Heat:
  - passing degraded condition: `noisy`
  - `robustness_signal_source = "contract_stability_signal"`
  - weak `contract_mode = "canonical_fallback"`
  - weak `fallback_reason = "svd_translation_span_drift"`
  - weak ratio: `17.93x`
  - strong ratio: `18.65x`
- Burgers:
  - passing degraded conditions: `noisy` and `coarse`
  - representative recorded case: `noisy`
  - `robustness_signal_source = "contract_stability_signal"`
  - weak `contract_mode = "canonical_fallback"`
  - weak `fallback_reason = "weak_report_contract_span_drift"`
  - weak ratio: `9.90x`
  - strong ratio: `60.39x`

Interpretation:

- degraded weak-path wins are fallback-backed contract-stability signals
- they are not direct in-tolerance weak-fit recoveries
- they are not separation-superiority claims over the strong path

## Explicitly Deferred

- weak derivatives
- weak `ResidualBatch` / `ResidualEvaluator` integration
- stable KdV runtime promotion
- multidimensional, multivariable, or nonuniform-grid weak paths
- broader PDE, grid, or adapter expansion
- paper-specific experiment logic

## Final Release View

The current repository is ready for the final `0.8.0` release for the frozen `v0.8` weak residual report slice, subject to release-path checks passing on the release branch and CI passing on the release PR.

There are no known scientific-scope blockers inside the frozen `v0.8` slice.

The stable `v0.8` claim remains narrow:

- stable weak residual report APIs landed under `pdelie.residuals`
- degraded release wins are representative fallback-backed contract-stability signals
- stable contract integration and weak derivatives remain deferred
- no stable KdV public surface is added

## Packaging And Public API Notes

- `pdelie.residuals.evaluate_weak_heat_residual` is a stable runtime public API in `v0.8`
- `pdelie.residuals.evaluate_weak_burgers_residual` is a stable runtime public API in `v0.8`
- both APIs are exposed under `pdelie.residuals`, not root `pdelie`
- the report shape and diagnostic surface are frozen by `docs/planning/V0_8_SCOPE.md`
- `pdelie.data.from_numpy` and `pdelie.data.from_xarray` remain stable runtime public APIs carried forward from `v0.7`
- the runtime discovery, portability, invariant, and visualization layers remain in place unchanged in stable scope
- KdV remains tests-first feasibility only and does not add a stable runtime API in `v0.8`
- the `v0_4-release-gate`, `v0_5-release-gate`, `v0_6-release-gate`, `v0_7-release-gate`, and `v0_8-release-gate` CI jobs are explicit visibility checks; post-`v0.8` CI consolidation is a follow-up item and is not part of this release

## Final Tag Checklist

Before tagging `v0.8.0`:

- inspect consistency across:
  - `pyproject.toml`
  - `README.md`
  - `CHANGELOG.md`
  - `docs/releases/V0_8_RELEASE_READINESS.md`
  - `docs/specs/API_STABILITY.md`
- run `python -m pytest` from the repo root
- run `python -m build --sdist --wheel`
- install the built wheel into a clean environment and verify:
  - stable root imports
  - weak residual runtime imports under `pdelie.residuals`
  - one tiny weak Heat report smoke
- run `python -m pdelie.examples.heat_vertical_slice`
- if TestPyPI trusted publishing is already available, run a packaging preflight on a temporary `v0.8.0rc1` tag via the existing publish workflow with:
  - `target=testpypi`
  - `git_ref=v0.8.0rc1`
  - then verify installation from TestPyPI
- if TestPyPI is not available/configured, record that explicitly and continue
- confirm GitHub Actions jobs `v0_4-release-gate`, `v0_5-release-gate`, `v0_6-release-gate`, `v0_7-release-gate`, `v0_8-release-gate`, `editable-tests`, and `package-smoke` pass on the release PR commit
- merge the release PR into `main`
- tag the merged `main` commit as `v0.8.0`
- run the publish workflow manually with:
  - `target=pypi`
  - `git_ref=v0.8.0`
  - `confirm_pypi=publish-to-pypi`
- verify installation from PyPI
