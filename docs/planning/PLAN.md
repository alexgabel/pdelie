# PDELie - Execution Plan (V0.18)

**Status:** COMPLETE

**V0.18 is complete as the stable Fisher-KPP reaction-diffusion strong path**

This file is the completed execution record for the `v0.18` release series.

## Release Theme

`v0.18` adds one scoped PDE expansion:

> canonical scalar 1D periodic FieldBatch -> spectral_fd derivatives -> Fisher-KPP residual -> translation fit/verification -> vertical-slice summary/example

The public claim is intentionally narrow. The release adds a stable synthetic Fisher-KPP generator, a strong-form residual evaluator, and a JSON-only vertical-slice smoke example. It does not add advection-diffusion, KS promotion, weak reaction-diffusion, custom initial-condition APIs, broad adapters, multidimensional or nonuniform support, neural/callable generator APIs, operator APIs, split policy, or root exports.

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

Authoritative scope:

- `docs/planning/V0_18_SCOPE.md`

`API_STABILITY.md` was updated when the public `v0.18` reaction-diffusion APIs landed.

## Milestone 0 - Scope Freeze

Freeze `v0.18` as a stable Fisher-KPP reaction-diffusion strong-path release.

Closeout:

- added `docs/planning/V0_18_SCOPE.md`
- reset `PLAN.md` as the active `v0.18` execution record
- updated `ROADMAP.md` to record `v0.18` as the current completed release
- kept the stable scope to scalar 1D uniform periodic synthetic data

## Milestone 1 - Equation And Numerical Semantics Freeze

Frozen equation:

```text
u_t = nu*u_xx + rho*u*(1 - u)
residual = u_t - nu*u_xx - rho*u*(1 - u)
```

Frozen metadata:

- `field.metadata["parameter_tags"]["equation"] == "reaction_diffusion_fisher_kpp"`
- `field.metadata["parameter_tags"]["nu"]`
- `field.metadata["parameter_tags"]["rho"]`

Frozen defaults:

- `nu = 0.05`
- `rho = 1.0`
- smooth bounded Fourier-mode initial conditions
- deterministic pseudo-spectral periodic RK4 rollout

Mass and mean drift are diagnostic-only because Fisher-KPP reaction terms are not mass conserving.

## Milestone 2 - Synthetic Data Generator

Implemented:

- `pdelie.data.generate_reaction_diffusion_1d_field_batch(...)`

The generator returns canonical scalar 1D periodic `FieldBatch` objects with finite unmasked values and the frozen Fisher-KPP equation tag. It has no public custom initial-condition API.

Validation added:

- deterministic same-seed output and seed sensitivity
- canonical dims, coords, metadata, scalar var, finite values, no mask by default
- `from_numpy` ingestion parity
- invalid size, parameter, mode, amplitude, substep, and domain inputs raise typed validation errors

## Milestone 3 - Residual Evaluator

Implemented:

- `pdelie.residuals.ReactionDiffusionResidualEvaluator`

Residual contract:

- evaluates `u_t - nu*u_xx - rho*u*(1-u)`
- computes `compute_spectral_fd_derivatives(field)` when derivatives are omitted
- supplied derivatives must include `u_t` and `u_xx`
- validates scalar 1D periodic finite unmasked fields and the frozen equation tag

Observed frozen-fixture residual evidence:

- residual max: approximately `1.07e-5`
- residual RMS: approximately `1.22e-6`

## Milestone 4 - Vertical Slice And Example

Implemented:

- `pdelie.examples.run_reaction_diffusion_vertical_slice_example(...)`
- command module: `python -m pdelie.examples.reaction_diffusion_vertical_slice`

The example emits the existing nested `summarize_vertical_slice(...)` runtime summary shape.

Observed frozen vertical-slice evidence:

- derivative keys: `u_t`, `u_x`, `u_xx`
- residual max: approximately `1.07e-5`
- residual RMS: approximately `1.22e-6`
- fit mode: `svd`
- evidence label: `direct_svd_in_tolerance`
- reference fallback: `false`
- selected/SVD span distance: approximately `4.12e-3`
- verification classification: `exact`
- first held-out verification error: approximately `1.73e-9`

This satisfies the stable promotion condition. No fallback-backed reaction-diffusion claim landed.

## Milestone 5 - API / Public-surface Audit

Audit result:

- new APIs are importable only from owning submodules
- root `pdelie` remains unchanged
- `API_STABILITY.md` documents the new reaction-diffusion generator, residual evaluator, and example runner
- no advection-diffusion, KS promotion, weak reaction-diffusion, custom IC API, broad adapter, multidimensional/nonuniform support, operator API, neural/callable generator API, or split policy landed

## Milestone 6 - Release Gate And Readiness

Implemented:

- added compact `tests/test_v0_18_release_gate.py`
- updated CI so the current explicit release gate is `v0_18-release-gate`
- kept full editable `python -m pytest`
- kept package smoke and added reaction-diffusion smoke coverage
- bumped package metadata to `0.18.0`
- updated README, changelog, publishing notes, roadmap, and release readiness docs
- documented direct `v0.18.0` Git-tag release path

Required checks before tagging:

- `v0_18-release-gate`
- `editable-tests`
- `package-smoke`

Local validation checklist:

- `python -m pytest`
- `python -m build --sdist --wheel`
- clean wheel smoke from `dist/pdelie-0.18.0-py3-none-any.whl`
- `python -m pdelie.examples.heat_vertical_slice`
- `python -m pdelie.examples.kdv_vertical_slice`
- `python -m pdelie.examples.reaction_diffusion_vertical_slice`
- `python -m pdelie.examples.orbit_coverage_diagnostics`
- `python -m pdelie.examples.invariant_workflow_summary`
- `python -m pdelie.examples.translation_orbit_batch`
- `python -m pdelie.examples.symmetry_candidate_validation`
- `python -m pdelie.examples.formula_generator_validation`
- `git diff --check`
