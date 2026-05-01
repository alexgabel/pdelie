# V0.14 Release Readiness

## Summary

- package version: `0.14.0`
- git tag: `v0.14.0`
- package-index publication: deferred until `v1.0` or later

`v0.14.0` is a Git-tag-only release.
Do not run TestPyPI or PyPI publishing for `v0.14`.

Release claim:

> invariant workflow summaries and read-only uniform translation orbit reports, without augmentation or new numerical scope.

---

## M0-M6 Outcome

- M0 froze `v0.14` as invariant workflow summaries plus read-only translation orbit reports.
- M1 froze report schemas, `source_field_id` provenance behavior, and report-only orbit semantics.
- M2 added `pdelie.reporting.summarize_invariant_workflow(...)`.
- M3 added `pdelie.invariants.summarize_uniform_translation_orbit(...)`.
- M4 added `python -m pdelie.examples.invariant_workflow_summary`.
- M5 audited public exports and deferred surfaces.
- M6 aligned release gate, CI, docs, metadata, and direct tag readiness.

## Public API Notes

New public submodule APIs:

- `pdelie.reporting.summarize_invariant_workflow(...)`
- `pdelie.invariants.summarize_uniform_translation_orbit(...)`
- `pdelie.examples.run_invariant_workflow_summary_example(...)`

No root `pdelie` exports were added.

These APIs return runtime JSON-compatible reports.
They do not create canonical objects, transformed `FieldBatch` objects, augmented datasets, orbit datasets, figures, or manuscript artifacts.

## Representative Diagnostics

Invariant workflow summary checks:

- Heat and KdV examples include orbit, coverage, consistency, generator, fit-diagnostic, and verification summaries
- summaries are JSON-compatible and use `summary_schema_version = "0.1"`
- supplied `source_field_id` values are preserved as provenance metadata only

Uniform translation orbit checks:

- raw shift order and duplicate shifts are preserved
- optional coverage diagnostics reuse the `v0.13` field-shift-then-fixed-window convention
- optional residual evaluators reuse the `v0.13` consistency diagnostics
- no transformed `FieldBatch` objects are returned
- input fields are not mutated

## Explicit Deferrals

`v0.14` does not add:

- a new PDE
- stable KS generator/residual/example APIs
- weak KS
- public augmentation utilities
- orbit dataset builders
- transformed `FieldBatch` collections from reporting helpers
- time-translation APIs
- broad dataset adapters
- PDEBench or The Well support
- multidimensional, multivariable, or nonuniform-grid support
- operator-facing APIs
- private-paper experiment policy
- manuscript-specific thresholds, tables, figures, or labels
- root runtime exports

## CI Expectations

Required checks before tagging:

- `v0_14-release-gate`
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
python -m pdelie.examples.invariant_workflow_summary
git diff --check
```

Clean wheel smoke should verify:

- stable root imports
- `pdelie.reporting.summarize_invariant_workflow`
- `pdelie.invariants.summarize_uniform_translation_orbit`
- one tiny weak Heat report
- one tiny KdV strong-path residual
- one tiny order-4 derivative smoke
- one tiny generator-fit diagnostic summary
- no root KS, orbit dataset, augmentation, time-translation, or weak KS exports

## Direct Tag Checklist

1. Create the release PR from the `v0.14` branch.
2. Run the local validation checklist.
3. Wait for required CI checks to pass.
4. Merge only after CI is green.
5. Tag the merged `main` commit as `v0.14.0`.
6. Do not publish to TestPyPI.
7. Do not publish to PyPI.
8. Record package-index publishing as deferred until `v1.0` or later.
