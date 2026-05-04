# PDELie - Execution Plan (V0.25)

**Status:** COMPLETE

**V0.25 is complete as the KdV scope decision release**

This file is the completed execution record for the `v0.25` release series.

## Release Theme

`v0.25` makes an explicit KdV scope decision:

> keep the public KdV APIs frozen to the normalized scalar 1D periodic short-horizon strong path, while recording diagnostic-only evidence for broader KdV directions.

Decision label:

```text
keep_public_kdv_surface_frozen
```

Stable public path retained:

```text
canonical scalar 1D periodic FieldBatch
-> spectral_fd derivatives with u_xxx
-> KdVResidualEvaluator for u_t + 6*u*u_x + u_xxx = 0
-> translation fit / verification / confidence reports
```

The release adds no new core KdV APIs. It adds one JSON example and test-only feasibility/guardrail evidence.

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

Authoritative scope:

- `docs/planning/V0_25_SCOPE.md`

`API_STABILITY.md` was updated when the public `v0.25` example runner landed.

## Milestone 0 - Scope Freeze

Freeze `v0.25` as a KdV scope decision release.

Closeout:

- added `docs/planning/V0_25_SCOPE.md`
- reset `PLAN.md` as the active `v0.25` execution record
- updated `ROADMAP.md` to record `v0.25` as the current completed release
- explicitly kept custom KdV initial conditions, configurable coefficients, general KdV, and weak KdV out of public scope

## Milestone 1 - Decision Criteria Freeze

Frozen evidence categories:

- `current_frozen_supported`
- `diagnostic_only`
- `deferred_no_go`

Frozen retained KdV thresholds:

- residual max `< 1e-2`
- residual RMS `< 2e-3`
- fit evidence label `direct_svd_in_tolerance`
- `reference_fallback_used is False`
- selected span distance `<= 5e-2`
- first held-out verification error `< 1e-4`
- verification classification not `failed`
- configured generator confidence label `strong`

## Milestone 2 - Internal KdV Scope Matrix

Implemented test-only diagnostic coverage for:

- current frozen fixture behavior
- longer horizons
- larger amplitudes
- more Fourier modes
- deterministic custom initial-condition rollout feasibility
- configurable-coefficient sign/scaling checks
- broader KdV regime evidence classified as diagnostic-only

No helper was exported from `pdelie.data`, `pdelie.residuals`, or root `pdelie`.

## Milestone 3 - Current KdV Surface Hardening

The existing public KdV path is hardened through tests for:

- deterministic generation and canonical fields
- `KdVResidualEvaluator` residual thresholds
- direct-SVD translation fitting
- held-out verification
- candidate validation
- generator confidence reports
- imported parity and invariant/orbit consistency

The frozen path remains direct-SVD-backed, not fallback-backed.

## Milestone 4 - Weak KdV Decision

Weak KdV remains deferred.

Closeout:

- preserved the existing proof that the frozen quartic bump is not valid for honest third-order weak KdV
- added identity-first checks for a stronger boundary-regular candidate profile
- kept all weak KdV evidence test-only and diagnostic-only
- preserved no-public-export guards for weak KdV names

## Milestone 5 - Example and Docs

Implemented:

- `pdelie.examples.run_kdv_scope_decision_example(...)`
- command module: `python -m pdelie.examples.kdv_scope_decision`

The example uses public APIs only. It reports readiness, residual, fit diagnostics, verification, candidate validation, confidence, and explicit deferred decisions.

Docs now state that custom KdV initial conditions, configurable coefficients, general KdV regimes, and weak KdV remain deferred.

## Milestone 6 - Release Gate And Readiness

Implemented:

- added compact `tests/test_v0_25_release_gate.py`
- updated CI so the current explicit release gate is `v0_25-release-gate`
- kept full editable `python -m pytest`
- kept package smoke and added KdV scope-decision smoke coverage
- bumped package metadata to `0.25.0`
- updated README, changelog, publishing notes, roadmap, and release readiness docs
- documented direct `v0.25.0` Git-tag release path

Required checks before tagging:

- `v0_25-release-gate`
- `editable-tests`
- `package-smoke`

Local validation checklist:

- `python -m pytest`
- `python -m build --sdist --wheel`
- `python -m pdelie.examples.heat_vertical_slice`
- `python -m pdelie.examples.kdv_vertical_slice`
- `python -m pdelie.examples.kdv_scope_decision`
- `python -m pdelie.examples.reaction_diffusion_vertical_slice`
- `python -m pdelie.examples.advection_diffusion_vertical_slice`
- `python -m pdelie.examples.orbit_coverage_diagnostics`
- `python -m pdelie.examples.invariant_workflow_summary`
- `python -m pdelie.examples.translation_orbit_batch`
- `python -m pdelie.examples.symmetry_candidate_validation`
- `python -m pdelie.examples.formula_generator_validation`
- `python -m pdelie.examples.generator_confidence_report`
- `python -m pdelie.examples.external_data_readiness`
- `python -m pdelie.examples.downstream_discovery_contracts`
- `python -m pdelie.examples.split_leakage_provenance`
- `python -m pdelie.examples.weak_form_supportability`
- `python scripts/check_notebooks.py`
- `git diff --check`
