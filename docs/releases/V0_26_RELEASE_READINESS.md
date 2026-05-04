# V0.26 Release Readiness

## Summary

`v0.26.0` is the KS revisit decision release.

Release definition:

```text
internal normalized KS fixture
+ order-4 spectral_fd residual feasibility
+ translation fit / verification / confidence diagnostics
+ minimal no-go reproduction matrix
-> explicit KS decision
```

package version: `0.26.0`  
git tag: `v0.26.0`

## Public API Notes

No new public runtime API was added.

No root `pdelie` exports were added.

No public KS data generator, residual evaluator, vertical-slice example, status example, residual-only API, weak KS API, or root KS export was added.

## What This Release Does

- records the KS decision `current_no_go_reference_fallback`
- confirms the primary KS fixture remains residual-feasible and verification-feasible
- records that translation fitting remains reference-fallback-backed and therefore not promotable
- adds a test-only `ks_revisit_decision` report with a generator confidence summary
- adds a minimal test-only matrix with seed, fit-epsilon, and resolution diagnostics
- reserves `v0.26b` as the follow-up KS promotion release name if future direct-SVD/no-fallback evidence justifies it
- keeps all KS feasibility helpers internal/test-only

## What This Release Does Not Do

- no public KS data generator
- no public KS residual evaluator
- no public KS vertical-slice example
- no public KS status example
- no residual-only KS public API
- no weak KS API
- no custom KS initial-condition API
- no configurable KS coefficient API
- no broad KS regime support
- no root KS export
- no broad adapters or file loaders
- no multidimensional or nonuniform stable support
- no time-translation APIs
- no neural or callable generator APIs
- no operator-facing APIs

## CI Expectations

The current explicit release gate is:

- `v0_26-release-gate`

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
python -m pdelie.examples.kdv_scope_decision
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
python -m pdelie.examples.weak_form_supportability
python scripts/check_notebooks.py
git diff --check
```

## Direct Tag Checklist

`v0.26.0` remains a direct Git-tag release.

1. Confirm CI is green on the release commit.
2. Confirm package metadata says `0.26.0`.
3. Confirm `CHANGELOG.md` contains `0.26.0`.
4. Confirm `docs/specs/API_STABILITY.md` records the no-public-KS decision status without adding KS runtime contracts.
5. Confirm `docs/planning/PLAN.md` and `docs/planning/V0_26_SCOPE.md` mark Milestone 6 complete.
6. Create the tag:

```bash
git tag v0.26.0
```

Do not publish to TestPyPI or PyPI for `v0.26.0`. Package-index publishing remains deferred until `v1.0` or later.
