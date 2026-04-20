# V0.4 Release Readiness

## Release Target

- package version: `0.4.0rc1`
- git tag: `v0.4.0rc1`

## Done

- canonical `GeneratorFamily` family semantics are implemented with `schema_version = "0.2"`, family-shaped coefficients, and explicit `basis_spec`
- the narrow legacy single-generator translation compatibility path remains in place via `GeneratorFamily.from_dict()`
- Heat remains supported under the existing stable path
- Burgers remains supported under the existing stable path
- the stable derivative backend remains `spectral_fd`
- analytic Heat and Burgers residual evaluators remain in place
- the polynomial spatial-translation fitting path remains the stable PDE fitting slice
- the finite-transform verification path remains the stable verification slice
- runtime-only symbolic generator rendering is implemented under `pdelie.symmetry`
- optional runtime-only SymPy component expressions are implemented under `pdelie.symmetry`
- runtime-only span diagnostics are implemented under `pdelie.symmetry`
- runtime-only closure / structure-constant diagnostics are implemented under `pdelie.symmetry`
- optional Matplotlib visualization is implemented under `pdelie.viz`
- the V0.4 release-gate module and `v0_4-release-gate` CI visibility job are implemented
- the full test suite passes from the repo root
- package metadata, README, changelog, milestone docs, and release-readiness docs are aligned with the implemented V0.4 surface

## Explicitly Deferred

- weak-form methods beyond the reserved interface surface
- operator methods
- neural generators as stable API
- broad dataset adapters or interoperability expansion
- stable multi-generator PDE fitting
- broader downstream compatibility or prediction-facing workflows
- new canonical stable objects beyond the current V0.4 slice
- paper-specific experiment logic

## Release Candidate View

The current repository is ready for the first `0.4.0rc1` release candidate for the frozen V0.4 stable core, subject to the release-path checks passing on the release branch and CI passing on the release PR.

There are no known scientific-scope blockers inside the current V0.4 slice.

`0.4.0rc1` is the first release candidate for the completed V0.4 milestone line. Any post-rc changes should be minimal blocker fixes only.

## Packaging And Public API Notes

- canonical `GeneratorFamily` output now uses `schema_version = "0.2"` and explicit `basis_spec`
- the legacy translation compatibility path remains narrow and runtime-gated through `GeneratorFamily.from_dict()` only
- `InvariantMapSpec` remains the only stable canonical object added in the V0.3 era; V0.4 adds runtime-level symbolic/span/closure/viz APIs without adding a new canonical object
- `pdelie.viz` is optional via `pdelie[viz]`
- the runtime downstream bridge remains optional via `pdelie[downstream]`
- the downstream path is still intentionally narrow and currently validated on the PySINDy 1.x / scikit-learn 1.2.x line under Python `<3.12`
- SymPy support is optional at runtime and is not part of the core install
- the `v0_4-release-gate` CI job is an explicit visibility check; if it should block merges, repository branch-protection settings must be updated separately

## Final Tag Checklist

Before tagging `v0.4.0rc1`:

- run `python -m pytest` from the repo root
- run `python -m build --sdist --wheel`
- install the built wheel into a clean environment and verify stable imports
- run `python -m pdelie.examples.heat_vertical_slice`
- confirm GitHub Actions jobs `v0_4-release-gate`, `editable-tests`, and `package-smoke` pass on the release PR commit
- merge the release PR into `main`
- tag the merged `main` commit as `v0.4.0rc1`
