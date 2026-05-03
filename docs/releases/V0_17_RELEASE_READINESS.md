# V0.17 Release Readiness

- package version: `0.17.0`
- git tag: `v0.17.0`
- package-index publication: deferred until `v1.0` or later

`v0.17.0` is a Git-tag-only release.
Do not run TestPyPI or PyPI publishing for `v0.17`.

## Summary

`v0.17` closes as the formula-backed generator interoperability release.

Stable claim:

`canonical scalar 1D periodic FieldBatch + formula-backed generator candidate -> safe formula metadata/evaluation diagnostics -> empirical configured validation report`

The public additions are:

- `pdelie.symmetry.FormulaGeneratorFamily`
- `pdelie.reporting.summarize_formula_generator_family(...)`
- `pdelie.symmetry.validate_symmetry_candidate(...)` support for `candidate_kind = "formula_generator_family"`

Formula expressions use a safe JSON AST.
They are not executable Python strings or callables.

`validated` still means configured empirical validation under supplied inputs and thresholds.
It is not a mathematical proof of symmetry.

## M0-M6 Outcome

- M0: froze scope as formula-backed generator interoperability
- M1: froze the formula record, safe AST, reporting, and validation semantics
- M2: implemented `FormulaGeneratorFamily` and formula-family summaries
- M3: extended candidate validation for formula-backed families
- M4: added JSON-only formula-generator validation example
- M5: audited public surface and non-goals
- M6: aligned metadata, docs, CI, release gate, and readiness notes

## Public API Notes

New or extended submodule-only APIs:

- `pdelie.symmetry.FormulaGeneratorFamily`
- `pdelie.reporting.summarize_formula_generator_family`
- `pdelie.symmetry.validate_symmetry_candidate`

No root exports are added.

`FormulaGeneratorFamily` is runtime-only.
It is not a canonical object and does not change polynomial `GeneratorFamily` semantics.

## Explicit Deferrals

`v0.17` does not add:

- callable generator APIs
- arbitrary executable formula-string parsing
- neural symmetry-detector training
- learned-generator classes
- formula-derived finite-flow integration for arbitrary infinitesimal formulas
- canonical `GeneratorFamily` schema changes
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

- `v0_17-release-gate`
- `editable-tests`
- `package-smoke`

Historical release-gate test files remain in the repository and are covered by the full editable test suite.

## Local Validation Checklist

Before tagging `v0.17.0`, run:

```bash
python -m pytest
python -m build --sdist --wheel
python -m pdelie.examples.heat_vertical_slice
python -m pdelie.examples.kdv_vertical_slice
python -m pdelie.examples.orbit_coverage_diagnostics
python -m pdelie.examples.invariant_workflow_summary
python -m pdelie.examples.translation_orbit_batch
python -m pdelie.examples.symmetry_candidate_validation
python -m pdelie.examples.formula_generator_validation
git diff --check
```

Clean wheel smoke should verify:

- stable root imports
- `pdelie.symmetry.FormulaGeneratorFamily` imports from the submodule
- `pdelie.reporting.summarize_formula_generator_family` imports from the submodule
- root `pdelie.FormulaGeneratorFamily` remains absent
- one formula-backed candidate validates or partially validates
- one formula-backed finite-transform candidate validates
- one denominator-floor formula candidate returns `conclusion = "failed"`
- weak Heat report smoke remains green
- KdV strong-path residual smoke remains green
- order-4 derivative smoke remains green

## Direct Tag Checklist

- create and merge the release PR
- wait for required CI checks to pass
- tag the merged `main` commit as `v0.17.0`
- do not publish to TestPyPI
- do not publish to PyPI
- record package-index publishing as deferred until `v1.0` or later
