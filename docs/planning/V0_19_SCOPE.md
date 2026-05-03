# V0.19 Scope - Stable Advection-Diffusion Strong Path

**Status:** COMPLETE

`v0.19` is a narrow PDE-expansion release for one stable scalar 1D periodic constant-coefficient advection-diffusion path.

Stable path:

```text
canonical scalar 1D periodic FieldBatch
-> spectral_fd derivatives
-> advection-diffusion residual
-> translation fit/verification
-> vertical-slice summary/example
```

## Summary

`v0.19` adds a deterministic synthetic advection-diffusion generator, a strong-form residual evaluator, and a compact JSON-only vertical-slice example.

Chosen equation:

```text
u_t + c*u_x = nu*u_xx
residual = u_t + c*u_x - nu*u_xx
```

This release stays inside the existing safe numerical regime:

- scalar 1D uniform periodic fields
- synthetic data only
- default order-2 `spectral_fd` derivatives
- polynomial translation generator fitting
- finite uniform translation verification
- no root export expansion

## Public APIs

Submodule-only APIs added:

- `pdelie.data.generate_advection_diffusion_1d_field_batch(...)`
- `pdelie.residuals.AdvectionDiffusionResidualEvaluator`
- `pdelie.examples.run_advection_diffusion_vertical_slice_example(...)`

Command example:

```bash
python -m pdelie.examples.advection_diffusion_vertical_slice
```

No root `pdelie` exports were added.

## Frozen Semantics

Generated fields are canonical `FieldBatch` objects with:

- dims `("batch", "time", "x", "var")`
- scalar variable name `u`
- endpoint-excluded uniform periodic `x`
- uniformly increasing `time`
- finite unmasked values
- `field.metadata["parameter_tags"]["equation"] == "advection_diffusion_constant_coefficient"`
- `field.metadata["parameter_tags"]["c"]`
- `field.metadata["parameter_tags"]["nu"]`

Frozen defaults:

- `batch_size = 5`
- `num_times = 65`
- `num_points = 64`
- `max_time = 0.4`
- `advection_speed = 0.75`
- `diffusivity = 0.05`
- `num_modes = 6`
- `amplitude = 0.2`
- `domain_length = 2*pi`
- `seed = 0`

Generator rollout is exact periodic Fourier evolution with multiplier:

```text
exp((-nu*k**2 - 1j*c*k) * t)
```

The residual evaluator:

- evaluates `u_t + c*u_x - nu*u_xx`
- computes `compute_spectral_fd_derivatives(field)` when derivatives are omitted
- requires supplied derivatives to include `u_t`, `u_x`, and `u_xx`
- accepts finite signed `c`
- requires finite positive `nu`
- validates scalar 1D periodic finite unmasked fields and the frozen equation tag

Mean drift is diagnostic-only. Periodic constant-coefficient advection-diffusion preserves the mean analytically, while numerical summaries use it only as a smoke diagnostic.

## Promotion Evidence

Frozen vertical-slice configuration:

- generator seed: `19018`
- train/heldout split: `split_batch_train_heldout(field, train_size=2, seed=19019)`
- fit epsilon: `1e-4`

Observed evidence:

- residual max: approximately `5.51e-5`
- residual RMS: approximately `8.44e-6`
- fit mode: `svd`
- evidence label: `direct_svd_in_tolerance`
- reference fallback: `false`
- selected/SVD span distance: approximately `7.87e-4`
- verification classification: `exact`
- first held-out verification error: approximately `7.87e-8`

This satisfies the promotion gate. No fallback-backed advection-diffusion claim landed.

## Non-goals

`v0.19` explicitly does not add:

- variable-coefficient advection-diffusion
- reaction-advection-diffusion
- weak advection-diffusion
- custom advection-diffusion initial-condition APIs
- multidimensional or nonuniform-grid ingestion
- broad PDEBench / The Well adapters
- time-translation APIs or `axis="time"` support
- stable KS data generator, residual evaluator, vertical-slice example, imported parity, weak KS API, or root KS export
- neural or callable generator APIs
- operator-facing symmetry APIs
- train/test split management, heldout-leakage detection, or downstream augmentation policy
- transformed `FieldBatch` collections from reporting helpers
- root export expansion

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

## Release Gate Expectations

The current explicit CI release gate is `v0_19-release-gate`.

Required checks before tagging:

- `v0_19-release-gate`
- `editable-tests`
- `package-smoke`

Local validation should include:

- `python -m pytest`
- `python -m build --sdist --wheel`
- clean wheel smoke from `dist/pdelie-0.19.0-py3-none-any.whl`
- packaged examples, including `python -m pdelie.examples.advection_diffusion_vertical_slice`
- `git diff --check`
