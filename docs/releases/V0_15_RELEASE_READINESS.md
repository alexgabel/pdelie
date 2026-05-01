# V0.15 Release Readiness

## Summary

- package version: `0.15.0`
- git tag: `v0.15.0`
- package-index publication: deferred until `v1.0` or later

`v0.15.0` is a Git-tag-only release.
Do not run TestPyPI or PyPI publishing for `v0.15`.

Release claim:

> materialized uniform translation orbit batches with explicit provenance, without train/test policy or new numerical scope.

---

## M0-M6 Outcome

- M0 froze `v0.15` as materialized uniform translation orbit batches.
- M1 froze API name, `OrbitBatchResult` status, batch ordering, provenance, mask behavior, metadata/preprocess composition, and copy semantics.
- M2 added `pdelie.invariants.build_uniform_translation_orbit_batch(...)` and `pdelie.invariants.OrbitBatchResult`.
- M3 verified Heat and KdV compatibility with derivatives, residual evaluators, and provenance tracing.
- M4 added `python -m pdelie.examples.translation_orbit_batch`.
- M5 audited public exports and deferred surfaces.
- M6 aligned release gate, CI, docs, metadata, and direct tag readiness.

## Public API Notes

New public submodule APIs:

- `pdelie.invariants.build_uniform_translation_orbit_batch(...)`
- `pdelie.invariants.OrbitBatchResult`
- `pdelie.examples.run_translation_orbit_batch_example(...)`

No root `pdelie` exports were added.

`OrbitBatchResult` is runtime-only.
It is not a canonical object, has no schema migration policy, and does not change the `FieldBatch` contract.

## Representative Diagnostics

Orbit batch checks:

- output appends along batch in shift-major order
- output batch size equals `source_batch_size * len(shifts)`
- duplicate shifts are preserved
- source and shift indices are recorded when requested
- optional `source_field_id` is preserved as JSON-compatible provenance metadata
- output metadata records `orbit_materialization`
- output preprocess log appends one aggregate `materialize_uniform_translation_orbit_batch` entry
- `mask=None` remains `None`
- non-`None` masks concatenate along batch consistently with transformed fields
- Heat and KdV materialized batches validate as `FieldBatch` objects
- derivatives and residual evaluators run on representative materialized Heat and KdV batches

## Explicit Deferrals

`v0.15` does not add:

- train/test policy
- split management
- heldout-leakage detection
- sparse-discovery branch policy
- private-paper augmentation recipes
- time-translation APIs
- a new PDE
- stable KS generator/residual/example APIs
- weak KS
- broad dataset adapters
- PDEBench or The Well support
- multidimensional, multivariable, or nonuniform-grid support
- operator-facing APIs
- root runtime exports

## CI Expectations

Required checks before tagging:

- `v0_15-release-gate`
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
python -m pdelie.examples.translation_orbit_batch
git diff --check
```

Clean wheel smoke should verify:

- stable root imports
- `pdelie.invariants.build_uniform_translation_orbit_batch`
- `pdelie.invariants.OrbitBatchResult`
- one tiny materialized Heat orbit batch
- one tiny weak Heat report
- one tiny KdV strong-path residual
- one tiny order-4 derivative smoke
- one tiny generator-fit diagnostic summary
- no root KS, train/test policy, split-management, time-translation, or weak KS exports

## Direct Tag Checklist

1. Create the release PR from the `v0.15` branch.
2. Run the local validation checklist.
3. Wait for required CI checks to pass.
4. Merge only after CI is green.
5. Tag the merged `main` commit as `v0.15.0`.
6. Do not publish to TestPyPI.
7. Do not publish to PyPI.
8. Record package-index publishing as deferred until `v1.0` or later.
