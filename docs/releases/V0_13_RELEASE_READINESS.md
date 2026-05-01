# V0.13 Release Readiness

## Summary

- package version: `0.13.0`
- git tag: `v0.13.0`
- package-index publication: deferred until `v1.0` or later

`v0.13.0` is a Git-tag-only release.
Do not run TestPyPI or PyPI publishing for `v0.13`.

Release claim:

> public orbit and coverage diagnostics under `pdelie.invariants`, without public augmentation utilities or new numerical scope.

---

## M0-M6 Outcome

- M0 froze `v0.13` as public orbit/coverage diagnostics.
- M1 froze coverage and translation-consistency semantics.
- M2 added `pdelie.invariants.compute_periodic_window_coverage(...)`.
- M3 added `pdelie.invariants.diagnose_uniform_translation_consistency(...)`.
- M4 added `python -m pdelie.examples.orbit_coverage_diagnostics`.
- M5 audited public exports and deferred surfaces.
- M6 aligned release gate, CI, docs, metadata, and direct tag readiness.

## Public API Notes

New public submodule APIs:

- `pdelie.invariants.compute_periodic_window_coverage(...)`
- `pdelie.invariants.diagnose_uniform_translation_consistency(...)`
- `pdelie.examples.run_orbit_coverage_diagnostics_example(...)`

No root `pdelie` exports were added.

These APIs return runtime JSON-compatible reports.
They do not create canonical objects, transformed `FieldBatch` objects, augmented datasets, orbit views, train branches, figures, or manuscript artifacts.

## Representative Diagnostics

Coverage checks:

- half-coverage quarter-shift case covers `32 / 64` grid points
- full-coverage quarter-shift case covers `64 / 64` grid points
- positive shift follows the frozen field-shift-then-fixed-window convention
- inferred domain length is `len(x) * dx`

Translation consistency checks:

- stable Heat and KdV fixtures preserve dims, shape, coords, metadata, var names, and mask content
- inverse and period-wrap errors are at floating-point noise levels
- residual RMS stability passes by the frozen absolute-or-relative delta rule
- appended provenance records `invariant_apply` and `uniform_translation`

## Explicit Deferrals

`v0.13` does not add:

- a new PDE
- stable KS generator/residual/example APIs
- weak KS
- public augmentation utilities
- public orbit-view builders
- broad dataset adapters
- PDEBench or The Well support
- multidimensional, multivariable, or nonuniform-grid support
- operator-facing APIs
- private-paper experiment policy
- manuscript-specific thresholds, tables, figures, or labels
- root runtime exports

## CI Expectations

Required checks before tagging:

- `v0_13-release-gate`
- `editable-tests`
- `package-smoke`

The explicit release gate is compact and representative.
The full editable suite remains responsible for historical release gates and broader regression coverage.

## Local Validation Checklist

Before tagging:

```bash
python -m pytest
python -m build --sdist --wheel
python -m pdelie.examples.heat_vertical_slice
python -m pdelie.examples.kdv_vertical_slice
python -m pdelie.examples.orbit_coverage_diagnostics
git diff --check
```

Clean wheel smoke should verify:

- stable root imports
- `pdelie.reporting` imports
- `pdelie.invariants.compute_periodic_window_coverage`
- `pdelie.invariants.diagnose_uniform_translation_consistency`
- one tiny weak Heat report
- one tiny KdV strong-path residual
- one tiny order-4 derivative smoke
- one tiny generator-fit diagnostic summary
- no root KS, orbit/coverage, augmentation, or weak KS exports

## Direct Tag Checklist

1. Create the release PR from the `v0.13` branch.
2. Run the local validation checklist.
3. Wait for required CI checks to pass.
4. Merge only after CI is green.
5. Tag the merged `main` commit as `v0.13.0`.
6. Do not publish to TestPyPI.
7. Do not publish to PyPI.
8. Record package-index publishing as deferred until `v1.0` or later.
