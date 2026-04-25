# V0.5 Release Readiness

## Release Target

- package version: `0.5.0`
- git tag: `v0.5.0`

## Done

- canonical `GeneratorFamily` family semantics from `v0.4` remain in place with `schema_version = "0.2"`, family-shaped coefficients, and explicit `basis_spec`
- the narrow legacy single-generator translation compatibility path remains in place via `GeneratorFamily.from_dict()`
- Heat remains supported under the existing stable path
- Burgers remains supported under the existing stable path
- the stable derivative backend remains `spectral_fd`
- analytic Heat and Burgers residual evaluators remain in place
- the polynomial spatial-translation fitting path remains the stable PDE fitting slice
- the finite-transform verification path remains the stable verification slice
- runtime-only symbolic generator rendering remains implemented under `pdelie.symmetry`
- optional runtime-only SymPy component expressions remain implemented under `pdelie.symmetry`
- runtime-only span diagnostics remain implemented under `pdelie.symmetry`
- runtime-only closure / structure-constant diagnostics remain implemented under `pdelie.symmetry`
- optional Matplotlib visualization remains implemented under `pdelie.viz`
- M1 is complete:
  - stable manifest export/import helpers are implemented under `pdelie.portability`
  - manifest payloads are JSON-compatible and round-trip to canonical `GeneratorFamily`
- M2 is complete:
  - strict external-family normalization is implemented under `pdelie.portability.coerce_generator_family(...)`
  - malformed, unsupported, and shape-invalid inputs fail with typed errors
- M3 is complete:
  - the portability benchmark proves semantic preservation across canonical payloads, manifest payloads, and the narrow legacy translation path
- M4 is complete / gated:
  - normalized periodic KdV feasibility passes in the tests-first slice
  - stable KdV promotion remains deferred
- M5 is complete:
  - the compact `v0.5` release gate is implemented
  - the `v0_5-release-gate` CI visibility job is implemented
- the full test suite passes from the repo root
- package metadata, changelog, milestone docs, and release-readiness docs can be aligned with the implemented `v0.5` surface

## Explicitly Deferred

- stable KdV API or stable KdV runtime module
- weak-form methods beyond the reserved interface surface
- operator methods
- neural generators as stable API
- broad dataset adapters or interoperability expansion
- prediction-facing utility work
- stable multi-generator PDE fitting
- new canonical stable objects beyond the current `v0.5` slice
- paper-specific experiment logic

## Final Release View

The current repository is ready for the final `0.5.0` release for the frozen `v0.5` portability and external-compatibility slice, subject to the release-path checks passing on the release branch and CI passing on the release PR.

There are no known scientific-scope blockers inside the current `v0.5` slice.

## Packaging And Public API Notes

- canonical `GeneratorFamily` output remains `schema_version = "0.2"` with explicit `basis_spec`
- the legacy translation compatibility path remains narrow and runtime-gated through `GeneratorFamily.from_dict()` only
- `pdelie.portability.export_generator_family_manifest` and `pdelie.portability.import_generator_family_manifest` are stable runtime public APIs for the frozen `v0.5` manifest artifact surface
- `pdelie.portability.coerce_generator_family` is the stable runtime public API for the frozen `v0.5` external-family normalization surface
- the manifest is a stable artifact schema, not a new canonical object
- the runtime downstream bridge remains optional via `pdelie[downstream]`
- `pdelie.viz` remains optional via `pdelie[viz]`
- SymPy support remains optional at runtime and is not part of the core install
- KdV remains tests-first feasibility only in `v0.5` and does not add a stable runtime API
- the `v0_4-release-gate` and `v0_5-release-gate` CI jobs are explicit visibility checks; if they should block merges, repository branch-protection settings must be updated separately

## Final Tag Checklist

Before tagging `v0.5.0`:

- run `python -m pytest` from the repo root
- run `python -m build --sdist --wheel`
- install the built wheel into a clean environment and verify stable imports
- run `python -m pdelie.examples.heat_vertical_slice`
- confirm GitHub Actions jobs `v0_4-release-gate`, `v0_5-release-gate`, `editable-tests`, and `package-smoke` pass on the release PR commit
- merge the release PR into `main`
- tag the merged `main` commit as `v0.5.0`
