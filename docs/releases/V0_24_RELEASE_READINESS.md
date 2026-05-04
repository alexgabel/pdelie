# V0.24 Release Readiness

## Summary

`v0.24.0` is the weak-form supportability reset release.

Release definition:

```text
existing Heat/Burgers weak residual reports
+ explicit weak contract summaries
+ strong residual / fit / verification evidence
+ noisy/coarse/imported parity diagnostics
+ internal identity-first Fisher-KPP feasibility
-> JSON-compatible weak-form supportability report
-> explicit supportability conclusion
```

package version: `0.24.0`  
git tag: `v0.24.0`

## Public API Notes

New submodule-only APIs:

- `pdelie.reporting.summarize_weak_form_supportability(...)`
- `pdelie.examples.run_weak_form_supportability_example(...)`

No root `pdelie` exports were added.

## What This Release Does

- reports weak-form supportability over existing Heat/Burgers weak residual report slices
- normalizes weak contract metadata including quadrature, patch shape/stride, operator order, and row/skipped-patch counts
- records quadrature in every weak supportability report
- combines optional strong residual, robustness, imported-parity, and feasibility evidence
- adds deterministic labels: `supported_existing_slice`, `diagnostic_only`, `failed`, and `insufficient_evidence`
- adds test-only, identity-first Fisher-KPP weak feasibility diagnostics
- adds a compact JSON-only example module that does not import `tests/_helpers`

## What This Release Does Not Do

- no WSINDy
- no weak design matrices
- no weak sparse recovery
- no public weak derivative backend
- no `DerivativeBatch.backend = "weak"` promotion
- no weak KdV APIs
- no weak KS APIs
- no public weak reaction-diffusion API
- no weak residual evaluator subclasses
- no new PDEs
- no KS runtime promotion
- no broad adapters or file loaders
- no train/test policy or leakage prevention
- no time-translation APIs
- no neural or callable generator APIs
- no operator-facing APIs
- no root export expansion

## CI Expectations

The current explicit release gate is:

- `v0_24-release-gate`

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
python -m pdelie.examples.weak_form_supportability
python scripts/check_notebooks.py
git diff --check
```

## Direct Tag Checklist

`v0.24.0` remains a direct Git-tag release.

1. Confirm CI is green on the release commit.
2. Confirm package metadata says `0.24.0`.
3. Confirm `CHANGELOG.md` contains `0.24.0`.
4. Confirm `docs/specs/API_STABILITY.md` documents the new submodule-only helper.
5. Confirm `docs/planning/PLAN.md` and `docs/planning/V0_24_SCOPE.md` mark Milestone 6 complete.
6. Create the tag:

```bash
git tag v0.24.0
```

Do not publish to TestPyPI or PyPI for `v0.24.0`. Package-index publishing remains deferred until `v1.0` or later.
