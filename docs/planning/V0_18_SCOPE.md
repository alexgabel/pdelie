# V0.18 Scope - Stable Fisher-KPP Reaction-Diffusion Strong Path

## Summary

`v0.18` is a narrow PDE-expansion release.

Stable path:

`canonical scalar 1D periodic FieldBatch -> spectral_fd derivatives -> Fisher-KPP residual -> translation fit/verification -> vertical-slice summary/example`

Chosen equation:

```text
u_t = nu*u_xx + rho*u*(1 - u)
residual = u_t - nu*u_xx - rho*u*(1 - u)
```

The release intentionally chooses a safer PDE expansion than the deferred KS path: no derivatives beyond the existing default order-2 backend, no fallback-backed public claim, and no new grid or adapter axis.

## Public Surface

`v0.18` adds submodule-only runtime APIs:

- `pdelie.data.generate_reaction_diffusion_1d_field_batch(...)`
- `pdelie.residuals.ReactionDiffusionResidualEvaluator`
- `pdelie.examples.run_reaction_diffusion_vertical_slice_example(...)`

These APIs have no root `pdelie` exports.

## Equation And Numerical Semantics

- Equation tag: `reaction_diffusion_fisher_kpp`
- Strong form: `u_t = nu*u_xx + rho*u*(1 - u)`
- Residual form: `u_t - nu*u_xx - rho*u*(1 - u)`
- Default parameters: `nu = 0.05`, `rho = 1.0`
- Default coordinates: canonical dims `("batch", "time", "x", "var")`
- Stable coordinate convention: scalar 1D uniform periodic `x`, endpoint excluded
- Frozen synthetic generator: deterministic pseudo-spectral periodic RK4 with smooth bounded Fourier-mode initial conditions
- No public custom initial-condition API lands in `v0.18`

Mass and mean drift are diagnostic-only for reaction-diffusion because Fisher-KPP reaction terms are not mass conserving.

## Feasibility Thresholds

The frozen vertical slice must satisfy:

- residual max `< 5e-4`
- residual RMS `< 5e-5`
- selected translation span distance `<= 5e-2`
- direct SVD evidence label `direct_svd_in_tolerance`
- no reference fallback
- first held-out verification error `< 5e-4`
- verification classification not `failed`

Observed M4 fixture evidence:

- residual max: approximately `1.07e-5`
- residual RMS: approximately `1.22e-6`
- selected/SVD span distance: approximately `4.12e-3`
- fit mode: `svd`
- reference fallback: `false`
- verification classification: `exact`
- first held-out verification error: approximately `1.73e-9`

## Non-goals

`v0.18` does not add:

- advection-diffusion
- KS runtime promotion
- weak reaction-diffusion
- public custom initial-condition APIs
- broad dataset adapters
- PDEBench / The Well loaders
- multidimensional grids
- nonuniform grids
- neural or callable generator APIs
- operator-facing APIs
- train/test policy or split-management utilities
- root exports

## Milestones

- Milestone 0: COMPLETE - scope freeze
- Milestone 1: COMPLETE - equation and numerical semantics freeze
- Milestone 2: COMPLETE - synthetic data generator
- Milestone 3: COMPLETE - residual evaluator
- Milestone 4: COMPLETE - vertical slice and example
- Milestone 5: COMPLETE - API/public-surface audit
- Milestone 6: COMPLETE - release gate and readiness

## Release Gate Expectations

The current explicit CI release gate is `v0_18-release-gate`.

Before tagging `v0.18.0`, required checks are:

- `v0_18-release-gate`
- full editable `python -m pytest`
- package smoke
- reaction-diffusion vertical-slice example
- `git diff --check`
