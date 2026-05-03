# V0.23 Release Readiness

## Summary

`v0.23.0` is the split/leakage provenance diagnostics release.

Release definition:

```text
user-supplied partition labels + FieldBatch/orbit-batch provenance
-> JSON-compatible split provenance report
-> leakage-risk diagnostics
-> optional downstream workflow summary integration
```

package version: `0.23.0`  
git tag: `v0.23.0`

## Public API Notes

New submodule-only APIs:

- `pdelie.reporting.summarize_split_leakage_provenance(...)`
- `pdelie.examples.run_split_leakage_provenance_example(...)`

Updated existing API:

- `pdelie.reporting.summarize_downstream_discovery_workflow(..., split_provenance=None)`

No root `pdelie` exports were added.

## What This Release Does

- validates user-supplied partition labels and sample counts
- reports source overlap across partitions
- reports same-source/same-shift overlap across partitions
- reports identity-shift overlap for materialized orbit batches
- accepts `OrbitBatchResult` and `uniform_translation_orbit_batch` report mappings
- validates optional metadata with strict JSON compatibility
- nests split provenance reports into downstream discovery workflow summaries
- adds a compact JSON-only example module

## What This Release Does Not Do

- no split creation
- no train/test split management
- no leakage prevention
- no benchmark policy
- no downstream success criteria
- no automatic augmentation policy
- no file loaders
- no `xarray.Dataset` support
- no PDEBench or The Well adapters
- no new PDEs
- no KS runtime promotion
- no weak-form expansion
- no time-translation APIs
- no neural or callable generator APIs
- no operator-facing APIs
- no root export expansion

## CI Expectations

The current explicit release gate is:

- `v0_23-release-gate`

CI also keeps:

- full editable `python -m pytest`
- package build and clean-wheel smoke

## Local Validation Checklist

Run from the release commit:

```bash
python -m pytest
python -m build --sdist --wheel
python -m pdelie.examples.heat_vertical_slice
python -m pdelie.examples.kdv_vertical_slice
python -m pdelie.examples.reaction_diffusion_vertical_slice
python -m pdelie.examples.advection_diffusion_vertical_slice
python -m pdelie.examples.orbit_coverage_diagnostics
python -m pdelie.examples.invariant_workflow_summary
python -m pdelie.examples.translation_orbit_batch
python -m pdelie.examples.symmetry_candidate_validation
python -m pdelie.examples.formula_generator_validation
python -m pdelie.examples.generator_confidence_report
python -m pdelie.examples.external_data_readiness
python -m pdelie.examples.downstream_discovery_contracts
python -m pdelie.examples.split_leakage_provenance
python scripts/check_notebooks.py
git diff --check
```

## Direct Tag Checklist

`v0.23.0` remains a direct Git-tag release.

1. Confirm CI is green on the release commit.
2. Confirm package metadata says `0.23.0`.
3. Confirm `CHANGELOG.md` contains `0.23.0`.
4. Confirm `docs/specs/API_STABILITY.md` documents the new submodule-only helper.
5. Confirm `docs/planning/PLAN.md` and `docs/planning/V0_23_SCOPE.md` mark Milestone 6 complete.
6. Create the tag:

```bash
git tag v0.23.0
```

Do not publish to TestPyPI or PyPI for `v0.23.0`. Package-index publishing remains deferred until `v1.0` or later.
