# V0.21 Release Readiness

- package version: `0.21.0`
- git tag: `v0.21.0`
- release type: direct final Git tag

`v0.21.0` is a Git-tag-only release.
Do not run TestPyPI or PyPI publishing for `v0.21`.

## Summary

`v0.21` closes as the external data readiness report release.

Public runtime additions:

- `pdelie.reporting.summarize_field_batch_readiness(...)`
- `pdelie.examples.run_external_data_readiness_example(...)`

The release helps users inspect canonical `FieldBatch` inputs before residual, confidence, and downstream workflows. It does not add new ingestion APIs.

## Public API Notes

The readiness helper returns JSON-compatible runtime reports with:

- `summary_type = "field_batch_readiness"`
- `summary_schema_version = "0.1"`
- `readiness_label` in `ready`, `needs_attention`, or `not_ready`
- component statuses in `passed`, `warning`, `failed`, `not_configured`, or `unavailable`
- optional residual-evaluator preflight

No root `pdelie` exports are added.

## Explicit Non-goals

`v0.21` does not add:

- file loaders
- `xarray.Dataset` support
- PDEBench or The Well adapters
- broad dataset adapter framework
- multidimensional or nonuniform-grid stable support
- resampling APIs
- metadata mutation APIs
- PDE identity inference
- train/test split or heldout-leakage policy
- downstream discovery contracts
- new PDEs
- KS runtime promotion
- weak-form expansion
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs

## CI Expectations

Required checks before tagging:

- `v0_21-release-gate`
- `editable-tests`
- `package-smoke`

The current explicit release gate is:

```bash
python -m pytest tests/test_v0_21_release_gate.py
```

## Local Validation Checklist

Before tagging `v0.21.0`, run:

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
git diff --check
```

Clean wheel smoke should verify:

- stable root imports
- `pdelie.reporting.summarize_field_batch_readiness`
- `pdelie.examples.run_external_data_readiness_example`
- one valid `from_numpy(...)` readiness report
- one residual-preflight mismatch report
- absence of root readiness, file-loader, Dataset, broad-adapter, KS, weak-KS, split-policy, and operator exports

Expected distribution artifacts:

- `dist/pdelie-0.21.0.tar.gz`
- `dist/pdelie-0.21.0-py3-none-any.whl`

## Direct Tag Procedure

From the release commit:

```bash
git tag v0.21.0
git push origin v0.21.0
```

Do not publish to TestPyPI or PyPI for `v0.21.0`.
