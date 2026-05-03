# PDELie - Execution Plan (V0.19)

**Status:** COMPLETE

**V0.19 is complete as the stable advection-diffusion strong path**

This file is the completed execution record for the `v0.19` release series.

## Release Theme

`v0.19` adds one scoped PDE expansion:

> canonical scalar 1D periodic FieldBatch -> spectral_fd derivatives -> advection-diffusion residual -> translation fit/verification -> vertical-slice summary/example

The public claim is intentionally narrow. The release adds a stable synthetic constant-coefficient advection-diffusion generator, a strong-form residual evaluator, and a JSON-only vertical-slice smoke example. It does not add variable-coefficient advection-diffusion, reaction-advection-diffusion, weak advection-diffusion, KS promotion, custom initial-condition APIs, broad adapters, multidimensional or nonuniform support, time translation, neural/callable generator APIs, operator APIs, split policy, or root exports.

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

Authoritative scope:

- `docs/planning/V0_19_SCOPE.md`

`API_STABILITY.md` was updated when the public `v0.19` advection-diffusion APIs landed.

## Milestone 0 - Scope Freeze

Freeze `v0.19` as a stable constant-coefficient advection-diffusion strong-path release.

Closeout:

- added `docs/planning/V0_19_SCOPE.md`
- reset `PLAN.md` as the active `v0.19` execution record
- updated `ROADMAP.md` to record `v0.19` as the current completed release
- kept the stable scope to scalar 1D uniform periodic synthetic data

## Milestone 1 - Equation And Numerical Semantics Freeze

Frozen equation:

```text
u_t + c*u_x = nu*u_xx
residual = u_t + c*u_x - nu*u_xx
```

Frozen metadata:

- `field.metadata["parameter_tags"]["equation"] == "advection_diffusion_constant_coefficient"`
- `field.metadata["parameter_tags"]["c"]`
- `field.metadata["parameter_tags"]["nu"]`

Frozen defaults:

- `c = 0.75`
- `nu = 0.05`
- zero-mean smooth Fourier-mode initial perturbations
- exact periodic Fourier evolution

Mean drift is diagnostic-only. Periodic constant-coefficient advection-diffusion preserves the mean analytically, but the release gate treats the diagnostic as supportability evidence, not a separate public invariant contract.

## Milestone 2 - Synthetic Data Generator

Implemented:

- `pdelie.data.generate_advection_diffusion_1d_field_batch(...)`

The generator returns canonical scalar 1D periodic `FieldBatch` objects with finite unmasked values and the frozen advection-diffusion equation tag. It has no public custom initial-condition API.

Validation added:

- deterministic same-seed output and seed sensitivity
- canonical dims, coords, metadata, scalar var, finite values, no mask by default
- exact Fourier phase/diffusion sanity against the frozen multiplier
- `from_numpy` ingestion parity
- invalid size, parameter, mode, amplitude, and domain inputs raise typed validation errors

## Milestone 3 - Residual Evaluator

Implemented:

- `pdelie.residuals.AdvectionDiffusionResidualEvaluator`

Residual contract:

- evaluates `u_t + c*u_x - nu*u_xx`
- computes `compute_spectral_fd_derivatives(field)` when derivatives are omitted
- supplied derivatives must include `u_t`, `u_x`, and `u_xx`
- validates scalar 1D periodic finite unmasked fields and the frozen equation tag
- reads `c` and `nu` from metadata when constructor parameters are omitted
- allows finite signed `c`
- requires finite positive `nu`

Observed frozen-fixture residual evidence:

- residual max: approximately `5.51e-5`
- residual RMS: approximately `8.44e-6`

## Milestone 4 - Vertical Slice And Example

Implemented:

- `pdelie.examples.run_advection_diffusion_vertical_slice_example(...)`
- command module: `python -m pdelie.examples.advection_diffusion_vertical_slice`

The example emits the existing nested `summarize_vertical_slice(...)` runtime summary shape.

Observed frozen vertical-slice evidence:

- derivative keys: `u_t`, `u_x`, `u_xx`
- residual max: approximately `5.51e-5`
- residual RMS: approximately `8.44e-6`
- fit mode: `svd`
- evidence label: `direct_svd_in_tolerance`
- reference fallback: `false`
- selected/SVD span distance: approximately `7.87e-4`
- verification classification: `exact`
- first held-out verification error: approximately `7.87e-8`

This satisfies the stable promotion condition. No fallback-backed advection-diffusion claim landed.

## Milestone 5 - API / Public-surface Audit

Audit result:

- new APIs are importable only from owning submodules
- root `pdelie` remains unchanged
- `API_STABILITY.md` documents the new advection-diffusion generator, residual evaluator, and example runner
- no variable-coefficient advection-diffusion, reaction-advection-diffusion, weak advection-diffusion, KS promotion, custom IC API, broad adapter, multidimensional/nonuniform support, time-translation API, operator API, neural/callable generator API, or split policy landed

## Milestone 6 - Release Gate And Readiness

Implemented:

- added compact `tests/test_v0_19_release_gate.py`
- updated CI so the current explicit release gate is `v0_19-release-gate`
- kept full editable `python -m pytest`
- kept package smoke and added advection-diffusion smoke coverage
- bumped package metadata to `0.19.0`
- updated README, changelog, publishing notes, roadmap, and release readiness docs
- documented direct `v0.19.0` Git-tag release path

Required checks before tagging:

- `v0_19-release-gate`
- `editable-tests`
- `package-smoke`

Local validation checklist:

- `python -m pytest`
- `python -m build --sdist --wheel`
- clean wheel smoke from `dist/pdelie-0.19.0-py3-none-any.whl`
- `python -m pdelie.examples.heat_vertical_slice`
- `python -m pdelie.examples.kdv_vertical_slice`
- `python -m pdelie.examples.reaction_diffusion_vertical_slice`
- `python -m pdelie.examples.advection_diffusion_vertical_slice`
- `python -m pdelie.examples.orbit_coverage_diagnostics`
- `python -m pdelie.examples.invariant_workflow_summary`
- `python -m pdelie.examples.translation_orbit_batch`
- `python -m pdelie.examples.symmetry_candidate_validation`
- `python -m pdelie.examples.formula_generator_validation`
- `git diff --check`
