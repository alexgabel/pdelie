# V0.18 Release Readiness

- package version: `0.18.0`
- git tag: `v0.18.0`
- publishing mode: Git tag only

`v0.18.0` is a Git-tag-only release.
Do not run TestPyPI or PyPI publishing for `v0.18`.

## Release Summary

`v0.18` closes as the stable Fisher-KPP reaction-diffusion strong-path release.

Public submodule-only APIs:

- `pdelie.data.generate_reaction_diffusion_1d_field_batch(...)`
- `pdelie.residuals.ReactionDiffusionResidualEvaluator`
- `pdelie.examples.run_reaction_diffusion_vertical_slice_example(...)`

Frozen equation:

```text
u_t = nu*u_xx + rho*u*(1 - u)
residual = u_t - nu*u_xx - rho*u*(1 - u)
```

Frozen metadata tag:

- `field.metadata["parameter_tags"]["equation"] == "reaction_diffusion_fisher_kpp"`

## Milestone Summary

- M0: scope freeze for the Fisher-KPP reaction-diffusion path
- M1: equation, defaults, metadata, diagnostics, and thresholds frozen
- M2: deterministic synthetic generator implemented
- M3: strong-form residual evaluator implemented
- M4: direct-SVD vertical slice and JSON-only example implemented
- M5: API/public-surface audit completed
- M6: release gate, metadata, docs, and readiness aligned

## Observed Vertical-slice Evidence

Frozen fixture:

- residual max: approximately `1.07e-5`
- residual RMS: approximately `1.22e-6`
- fit mode: `svd`
- evidence label: `direct_svd_in_tolerance`
- reference fallback: `false`
- selected/SVD span distance: approximately `4.12e-3`
- held-out verification classification: `exact`
- first held-out verification error: approximately `1.73e-9`

Mean and L2 drift are diagnostic-only for Fisher-KPP reaction-diffusion because the reaction term is not a conservation law.

## Explicit Non-goals

`v0.18` does not add:

- advection-diffusion
- KS runtime promotion
- weak reaction-diffusion
- public custom initial-condition APIs
- broad dataset adapters
- PDEBench / The Well loaders
- multidimensional or nonuniform support
- neural or callable generator APIs
- operator-facing APIs
- train/test policy or split-management utilities
- root exports

## Required CI Checks

Before tagging, require:

- `v0_18-release-gate`
- `editable-tests`
- `package-smoke`

## Local Validation Checklist

Before tagging `v0.18.0`, run:

```bash
python -m pytest
python -m build --sdist --wheel
python -m pdelie.examples.heat_vertical_slice
python -m pdelie.examples.kdv_vertical_slice
python -m pdelie.examples.reaction_diffusion_vertical_slice
python -m pdelie.examples.orbit_coverage_diagnostics
python -m pdelie.examples.invariant_workflow_summary
python -m pdelie.examples.translation_orbit_batch
python -m pdelie.examples.symmetry_candidate_validation
python -m pdelie.examples.formula_generator_validation
git diff --check
```

Clean wheel smoke should install:

- `dist/pdelie-0.18.0-py3-none-any.whl`

and verify:

- stable root imports
- retained reporting, invariant, orbit-batch, candidate-validation, and formula-backed APIs
- `pdelie.data.generate_reaction_diffusion_1d_field_batch`
- `pdelie.residuals.ReactionDiffusionResidualEvaluator`
- `pdelie.examples.run_reaction_diffusion_vertical_slice_example`
- one tiny Fisher-KPP residual smoke
- no root reaction-diffusion exports
- no KS, weak reaction-diffusion, advection-diffusion, broad adapter, custom-IC, or operator surface

## Direct Tag Procedure

After the PR merges and required checks are green:

```bash
git checkout main
git pull --ff-only
git tag v0.18.0
git push origin v0.18.0
```

Do not publish to TestPyPI or PyPI for `v0.18.0`.
