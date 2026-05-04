# V0.25 Release Readiness

## Summary

`v0.25.0` is the KdV scope decision release.

Release definition:

```text
frozen normalized KdV strong path
+ diagnostic broader-regime KdV evidence
+ weak KdV identity checks
-> explicit KdV scope decision
```

package version: `0.25.0`  
git tag: `v0.25.0`

## Public API Notes

New submodule-only example API:

- `pdelie.examples.run_kdv_scope_decision_example(...)`

Command module:

- `python -m pdelie.examples.kdv_scope_decision`

No root `pdelie` exports were added.

No new core KdV generator, residual evaluator, custom initial-condition, configurable-coefficient, or weak KdV API was added.

## What This Release Does

- records the KdV decision `keep_public_kdv_surface_frozen`
- keeps the normalized scalar 1D periodic short-horizon KdV strong path stable
- adds a JSON-only example reporting readiness, residual, fit diagnostics, verification, candidate validation, confidence, and deferred KdV decisions
- adds test-only broader-regime diagnostics for longer horizons, larger amplitudes, and more modes
- adds test-only deterministic custom-initial-condition rollout feasibility
- adds test-only configurable-coefficient sign/scaling checks for `u_t + alpha*u*u_x + beta*u_xxx = 0`
- adds test-only weak KdV identity checks for a stronger boundary-regular profile
- preserves no-public-export guards for broader KdV and weak KdV names

## What This Release Does Not Do

- no custom KdV initial-condition public API
- no configurable KdV coefficient public API
- no general KdV regime support
- no weak KdV API
- no weak derivative backend
- no WSINDy implementation
- no weak sparse recovery
- no KS runtime promotion
- no broad adapters or file loaders
- no multidimensional or nonuniform stable support
- no time-translation APIs
- no neural or callable generator APIs
- no operator-facing APIs
- no root export expansion

## CI Expectations

The current explicit release gate is:

- `v0_25-release-gate`

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

`v0.25.0` remains a direct Git-tag release.

1. Confirm CI is green on the release commit.
2. Confirm package metadata says `0.25.0`.
3. Confirm `CHANGELOG.md` contains `0.25.0`.
4. Confirm `docs/specs/API_STABILITY.md` documents the new submodule-only example and the frozen KdV decision.
5. Confirm `docs/planning/PLAN.md` and `docs/planning/V0_25_SCOPE.md` mark Milestone 6 complete.
6. Create the tag:

```bash
git tag v0.25.0
```

Do not publish to TestPyPI or PyPI for `v0.25.0`. Package-index publishing remains deferred until `v1.0` or later.
