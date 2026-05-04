# V0.27 Release Readiness

## Summary

`v0.27.0` is the multi-generator diagnostics decision release.

Release definition:

```text
supplied multi-row GeneratorFamily
+ algebraic diagnostics
+ PDE-context diagnostic labels
+ internal-only fit-probe status
-> explicit multi-generator promotion decision
```

package version: `0.27.0`  
git tag: `v0.27.0`

## Public API Notes

New submodule-only runtime example:

- `pdelie.examples.run_multi_generator_diagnostics_example(...)`
- `python -m pdelie.examples.multi_generator_diagnostics`

Existing public diagnostic behavior updates:

- `diagnose_generator_family_closure(...)` reports well-formed rank-deficient families diagnostically.
- `compare_generator_spans(...)` reports rank-deficient/zero-rank comparisons as warning/failed reports.
- `validate_symmetry_candidate(...)` accepts `closure_required=True|False`.

No root `pdelie` exports were added.

## What This Release Does

- records `multi_generator_diagnostics_feasible_fitting_deferred`
- freezes the bracket convention and structure-constant orientation
- reports expected structure-constant error for known closed families
- separates algebraic diagnostics from PDE-context validation
- keeps multi-generator fit probes internal and diagnostic-only
- adds a JSON-only diagnostic example over supplied families

## What This Release Does Not Do

- no public multi-generator PDE fitting
- no finite multi-generator flows
- no BCH composition
- no exponential-map finite-flow integration
- no multi-generator invariant charts
- no multi-parameter orbit charts
- no group-action atlas
- no operator-facing APIs
- no neural or callable generator APIs
- no root export expansion

## CI Expectations

The current explicit release gate is:

- `v0_27-release-gate`

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
python -m pdelie.examples.multi_generator_diagnostics
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

`v0.27.0` remains a direct Git-tag release.

1. Confirm CI is green on the release commit.
2. Confirm package metadata says `0.27.0`.
3. Confirm `CHANGELOG.md` contains `0.27.0`.
4. Confirm `docs/specs/API_STABILITY.md` documents only the diagnostic example and behavior updates, not multi-generator fitting.
5. Confirm `docs/planning/PLAN.md` and `docs/planning/V0_27_SCOPE.md` mark Milestone 6 complete.
6. Create the tag:

```bash
git tag v0.27.0
```

Do not publish to TestPyPI or PyPI for `v0.27.0`. Package-index publishing remains deferred until `v1.0` or later.
