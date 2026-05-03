# V0.19 Release Readiness

- package version: `0.19.0`
- git tag: `v0.19.0`
- publishing mode: Git tag only

`v0.19.0` is a Git-tag-only release.
Do not run TestPyPI or PyPI publishing for `v0.19`.

## Release Summary

`v0.19` closes as the stable constant-coefficient advection-diffusion strong-path release.

Public submodule-only APIs:

- `pdelie.data.generate_advection_diffusion_1d_field_batch(...)`
- `pdelie.residuals.AdvectionDiffusionResidualEvaluator`
- `pdelie.examples.run_advection_diffusion_vertical_slice_example(...)`

Frozen equation:

```text
u_t + c*u_x = nu*u_xx
residual = u_t + c*u_x - nu*u_xx
```

Frozen metadata tag:

- `field.metadata["parameter_tags"]["equation"] == "advection_diffusion_constant_coefficient"`

## Milestone Summary

- M0: scope freeze for the constant-coefficient advection-diffusion path
- M1: equation, exact Fourier rollout, defaults, metadata, diagnostics, and thresholds frozen
- M2: deterministic synthetic generator implemented
- M3: strong-form residual evaluator implemented
- M4: direct-SVD vertical slice and JSON-only example implemented
- M5: API/public-surface audit completed
- M6: release gate, metadata, docs, and readiness aligned

## Observed Vertical-slice Evidence

Frozen fixture:

- residual max: approximately `5.51e-5`
- residual RMS: approximately `8.44e-6`
- fit mode: `svd`
- evidence label: `direct_svd_in_tolerance`
- reference fallback: `false`
- selected/SVD span distance: approximately `7.87e-4`
- held-out verification classification: `exact`
- first held-out verification error: approximately `7.87e-8`

Mean drift is diagnostic-only. The equation preserves mean analytically under periodic constant coefficients, but release evidence does not promote a separate invariant API.

## Explicit Non-goals

`v0.19` does not add:

- variable-coefficient advection-diffusion
- reaction-advection-diffusion
- weak advection-diffusion
- public custom initial-condition APIs
- KS runtime promotion
- broad dataset adapters
- PDEBench / The Well loaders
- multidimensional or nonuniform support
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- train/test policy or split-management utilities
- root exports

## Required CI Checks

Before tagging, require:

- `v0_19-release-gate`
- `editable-tests`
- `package-smoke`

## Local Validation Checklist

Before tagging `v0.19.0`, run:

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
git diff --check
```

Clean wheel smoke should install:

- `dist/pdelie-0.19.0-py3-none-any.whl`

and verify:

- stable root imports
- retained reporting, invariant, orbit-batch, candidate-validation, formula-backed, and Fisher-KPP APIs
- `pdelie.data.generate_advection_diffusion_1d_field_batch`
- `pdelie.residuals.AdvectionDiffusionResidualEvaluator`
- `pdelie.examples.run_advection_diffusion_vertical_slice_example`
- one tiny advection-diffusion residual smoke
- no root advection-diffusion exports
- no weak advection-diffusion, variable-coefficient advection-diffusion, KS, broad adapter, custom-IC, time-translation, or operator surface

## Direct Tag Procedure

After the PR merges and required checks are green:

```bash
git checkout main
git pull --ff-only
git tag v0.19.0
git push origin v0.19.0
```

Do not publish to TestPyPI or PyPI for `v0.19.0`.
