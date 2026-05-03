# V0.20 Release Readiness

- package version: `0.20.0`
- git tag: `v0.20.0`
- publishing mode: Git tag only

`v0.20.0` is a Git-tag-only release.
Do not run TestPyPI or PyPI publishing for `v0.20`.

## Release Summary

`v0.20` closes as the unified generator confidence report release.

Public submodule-only APIs:

- `pdelie.reporting.summarize_generator_confidence(...)`
- `pdelie.examples.run_generator_confidence_report_example(...)`

The release promotes the notebook confidence-card pattern into a JSON-compatible runtime helper with categorical evidence labels and component statuses.

## Milestone Summary

- M0: scope freeze for confidence reporting
- M1: helper signature, labels, statuses, thresholds, and missing-evidence semantics frozen
- M2: reporting helper implemented
- M3: JSON-only example and tutorial alignment completed
- M4: direct-SVD, fallback, partial-validation, failed, threshold-failure, and insufficient-evidence coverage added
- M5: API/public-surface audit completed
- M6: release gate, metadata, docs, and readiness aligned

## Confidence Semantics

Frozen confidence labels:

- `strong`
- `qualified`
- `failed`
- `insufficient_evidence`

Frozen component statuses:

- `passed`
- `warning`
- `failed`
- `not_configured`
- `unavailable`

Interpretation:

- confidence is empirical configured evidence, not a mathematical proof
- no scalar confidence score ships in `v0.20`
- thresholds are caller-configured for residual, verification, and coverage checks
- reports are runtime summaries, not canonical artifacts

## Explicit Non-goals

`v0.20` does not add:

- scalar confidence score
- benchmark success policy
- train/test split or heldout-leakage policy
- transformed `FieldBatch` collections from reporting helpers
- canonical confidence object
- new PDEs
- KS runtime promotion
- weak-form expansion
- broad dataset adapters
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- root exports

## Required CI Checks

Before tagging, require:

- `v0_20-release-gate`
- `editable-tests`
- `package-smoke`

## Local Validation Checklist

Before tagging `v0.20.0`, run:

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
git diff --check
```

Clean wheel smoke should install:

- `dist/pdelie-0.20.0-py3-none-any.whl`

and verify:

- stable root imports
- retained reporting, invariant, orbit-batch, candidate-validation, formula-backed, Fisher-KPP, and advection-diffusion APIs
- `pdelie.reporting.summarize_generator_confidence`
- `pdelie.examples.run_generator_confidence_report_example`
- one tiny generator confidence report smoke
- no root confidence-report export
- no scalar-score, train/test, KS, weak-form expansion, broad-adapter, time-translation, neural/callable, or operator surface

## Direct Tag Procedure

After the PR merges and required checks are green:

```bash
git checkout main
git pull --ff-only
git tag v0.20.0
git push origin v0.20.0
```

Do not publish to TestPyPI or PyPI for `v0.20.0`.
