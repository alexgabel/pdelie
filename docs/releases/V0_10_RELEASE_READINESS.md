# V0.10 Release Readiness

## Release Target

- package version: `0.10.0`
- git tag: `v0.10.0`
- package-index publication: deferred until `v1.0` or later

`v0.10.0` is a Git-tag-only release.
Do not run TestPyPI or PyPI publishing for `v0.10`.

## Done

- M0 is complete:
  - `v0.10` was frozen as a supportability and `v1.0` readiness release
  - `v0.9` was recorded as complete
  - `v0.11` remains conditional, not committed
- M1 is complete:
  - `pdelie.reporting` was chosen as a public runtime submodule
  - reporting helpers were frozen as JSON-compatible supportability summaries, not canonical objects
- M2 is complete:
  - `pdelie.reporting.summarize_residual_batch(...)` is implemented
  - `pdelie.reporting.summarize_weak_residual_report(...)` is implemented
  - `pdelie.reporting.summarize_generator_family(...)` is implemented
  - `pdelie.reporting.summarize_verification_report(...)` is implemented
  - `pdelie.reporting.summarize_vertical_slice(...)` is implemented
  - `API_STABILITY.md` documents the new runtime public APIs
- M3 is complete:
  - Heat and KdV vertical-slice examples return nested `vertical_slice` summaries
  - example command entrypoints remain unchanged
  - example outputs remain runtime smoke summaries, not canonical artifact schemas
- M4 is complete:
  - API stability audit coverage was added
  - root exports, submodule APIs, and deferred surfaces are guarded by tests
  - `API_STABILITY.md` needed no further changes
- M5 is complete:
  - CI release-gate visibility was consolidated to one current `v0_10-release-gate` job
  - historical release-gate test modules remain in the repo
  - historical gates remain covered by full editable tests
- M6 is complete:
  - package metadata and release-facing docs are aligned with `0.10.0`
  - this readiness note is current
  - final release checks are documented for local execution and release PR CI

## Public API Notes

New stable runtime APIs in `v0.10`:

- `pdelie.reporting.summarize_residual_batch`
- `pdelie.reporting.summarize_weak_residual_report`
- `pdelie.reporting.summarize_generator_family`
- `pdelie.reporting.summarize_verification_report`
- `pdelie.reporting.summarize_vertical_slice`

These helpers:

- are exported from `pdelie.reporting` only
- have no root `pdelie` exports
- return JSON-compatible runtime dicts
- are supportability helpers, not canonical objects
- do not define manuscript tables, figures, labels, or artifact schemas

Retained stable surfaces include:

- Heat and Burgers strong paths
- `v0.8` weak Heat/Burgers residual report APIs
- `v0.9` normalized periodic short-horizon KdV strong path
- structured `from_numpy(...)` and optional `from_xarray(...)` ingestion
- polynomial translation fitting and held-out verification
- existing discovery, portability, symmetry, and visualization runtime helpers

## Explicitly Deferred

- new PDE support
- weak KdV APIs
- weak derivative APIs or broader weak-form expansion
- PDEBench, The Well, or other broad dataset adapters
- multidimensional, multivariable, or nonuniform-grid support
- operator-facing APIs
- manuscript-specific reporting logic
- new canonical reporting objects
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## CI Expectations

Before tagging `v0.10.0`, the release PR should have these CI jobs green:

- `v0_10-release-gate`
- `editable-tests`
- `package-smoke`

Historical release-gate test modules remain runnable locally and are covered by `editable-tests`.
They are no longer separate named CI jobs in `v0.10`.

## Local Release Checklist

Before tagging `v0.10.0`:

1. Inspect consistency across:
   - `pyproject.toml`
   - `README.md`
   - `CHANGELOG.md`
   - `docs/releases/V0_10_RELEASE_READINESS.md`
   - `docs/releases/PUBLISHING.md`
   - `docs/specs/API_STABILITY.md`
2. Run the full test suite:
   - `python -m pytest`
3. Build the package:
   - `python -m build --sdist --wheel`
4. Install `dist/pdelie-0.10.0-py3-none-any.whl` into a clean environment and verify:
   - stable root imports
   - `pdelie.reporting` helper imports from the submodule
   - root `pdelie` does not export reporting helpers
   - one tiny weak Heat report
   - one tiny KdV strong-path residual
   - one nested `vertical_slice` example summary shape check
5. Run examples:
   - `python -m pdelie.examples.heat_vertical_slice`
   - `python -m pdelie.examples.kdv_vertical_slice`
6. Run:
   - `git diff --check`

## Direct Final Tag Checklist

After local checks and CI pass:

- merge the release PR into `main`
- tag the merged `main` commit as `v0.10.0`
- do not publish to TestPyPI
- do not publish to PyPI
- record package-index publishing as deferred until `v1.0` or later

## Final Release View

`v0.10.0` is ready when the local release checklist and the current CI jobs pass.

The stable release claim is intentionally narrow:

`existing stable Heat/Burgers/weak-report/KdV surfaces -> compact supportability reports -> consistent examples/release gates/docs -> v1.0 readiness`

There are no new numerical claims in `v0.10`.
