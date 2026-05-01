# V0.16 Release Readiness

- package version: `0.16.0`
- git tag: `v0.16.0`
- package-index publication: deferred until `v1.0` or later

`v0.16.0` is a Git-tag-only release.
Do not run TestPyPI or PyPI publishing for `v0.16`.

## Summary

`v0.16` closes as the external symmetry-candidate validation release.

Stable claim:

`canonical scalar 1D periodic FieldBatch + external candidate payload + residual evaluator -> empirical configured validation report`

The public addition is:

- `pdelie.symmetry.validate_symmetry_candidate(...)`

The helper accepts:

- `GeneratorFamily`
- canonical `GeneratorFamily` payload mappings
- `InvariantMapSpec`
- canonical `InvariantMapSpec` payload mappings

`validated` means configured empirical validation under supplied inputs and thresholds.
It is not a mathematical proof of symmetry.

## M0-M6 Outcome

- M0: froze scope as detector interop through validation reports
- M1: froze API signature, accepted candidate kinds, strict payload policy, thresholds, conclusion labels, and failure behavior
- M2: implemented `GeneratorFamily` candidate validation
- M3: implemented `InvariantMapSpec` candidate validation
- M4: added JSON-only symmetry-candidate validation example
- M5: audited public surface and non-goals
- M6: aligned metadata, docs, CI, release gate, and readiness notes

## Public API Notes

New submodule-only API:

- `pdelie.symmetry.validate_symmetry_candidate`

No root export is added.

The API returns JSON-compatible runtime reports.
It does not return a canonical object and does not mutate inputs.

## Explicit Deferrals

`v0.16` does not add:

- callable transform descriptors
- arbitrary external executable candidate objects
- neural symmetry-detector training
- learned-generator classes
- formula-backed or non-polynomial generator families
- train/test policy
- split management
- heldout-leakage detection
- sparse-discovery branch policy
- time-translation APIs
- new PDE support
- stable KS runtime support
- weak KS
- broad adapters
- PDEBench or The Well support
- multidimensional, multivariable, or nonuniform-grid expansion
- operator-facing APIs
- root runtime exports

## CI Expectations

Required CI checks before tagging:

- `v0_16-release-gate`
- `editable-tests`
- `package-smoke`

Historical release-gate test files remain in the repository and are covered by the full editable test suite.

## Local Validation Checklist

Before tagging `v0.16.0`, run:

```bash
python -m pytest
python -m build --sdist --wheel
python -m pdelie.examples.heat_vertical_slice
python -m pdelie.examples.kdv_vertical_slice
python -m pdelie.examples.orbit_coverage_diagnostics
python -m pdelie.examples.invariant_workflow_summary
python -m pdelie.examples.translation_orbit_batch
python -m pdelie.examples.symmetry_candidate_validation
git diff --check
```

Clean wheel smoke should verify:

- stable root imports
- `pdelie.symmetry.validate_symmetry_candidate` imports from the submodule
- root `pdelie.validate_symmetry_candidate` remains absent
- one valid `GeneratorFamily` candidate validates
- one valid `InvariantMapSpec` payload validates
- one wrong-span generator returns `conclusion = "failed"`
- weak Heat report smoke remains green
- KdV strong-path residual smoke remains green
- order-4 derivative smoke remains green

## Direct Tag Checklist

- create and merge the release PR
- wait for required CI checks to pass
- tag the merged `main` commit as `v0.16.0`
- do not publish to TestPyPI
- do not publish to PyPI
- record package-index publishing as deferred until `v1.0` or later
