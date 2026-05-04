# V0.25 Scope - KdV Scope Decision and Guardrail Hardening

**Status:** COMPLETE

## Summary

`v0.25` is a KdV scope decision release.

Stable path retained:

```text
canonical scalar 1D periodic FieldBatch
-> spectral_fd derivatives with u_xxx
-> KdVResidualEvaluator for u_t + 6*u*u_x + u_xxx = 0
-> translation fit / verification / confidence reports
```

Release conclusion:

```text
keep_public_kdv_surface_frozen
```

The normalized scalar 1D periodic short-horizon KdV strong path remains stable.

Decision closeout:

- custom KdV initial conditions remain deferred
- configurable KdV coefficients remain deferred
- general KdV support outside the frozen normalized periodic short-horizon regime remains deferred
- weak KdV remains deferred

## Public API Notes

New submodule-only runtime example:

- `pdelie.examples.run_kdv_scope_decision_example(...)`
- `python -m pdelie.examples.kdv_scope_decision`

No new core KdV APIs were added.

No root `pdelie` exports were added.

## Frozen Evidence Categories

- `current_frozen_supported`: the current public normalized short-horizon KdV strong path passes configured public evidence.
- `diagnostic_only`: internal feasibility evidence that may inform future scope, but does not define a public API.
- `deferred_no_go`: evidence or scope is not sufficient for public promotion in `v0.25`.

## Frozen Promotion Evidence

The retained public KdV path is expected to show:

- generated fields are deterministic and canonical
- residual max `< 1e-2`
- residual RMS `< 2e-3`
- translation fit evidence label `direct_svd_in_tolerance`
- `reference_fallback_used is False`
- selected span distance `<= 5e-2`
- first held-out verification error `< 1e-4`
- verification classification is not `failed`
- configured generator confidence is `strong`

## Internal Diagnostic Matrix

`v0.25` records test-only evidence for:

- current frozen fixture behavior
- longer horizons
- larger amplitudes
- more Fourier modes
- custom initial-condition rollout determinism
- configurable-coefficient sign/scaling checks for `u_t + alpha*u*u_x + beta*u_xxx = 0`
- imported parity through existing ingestion APIs
- orbit/translation consistency and confidence-report stability

This evidence is diagnostic-only unless a later release explicitly opens a narrower promotion path.

## Weak KdV Decision

Weak KdV remains deferred.

The existing quartic bump remains invalid for an honest third-order weak KdV identity because `phi_xx` does not vanish at patch boundaries. `v0.25` adds test-only identity checks for a stronger boundary-regular candidate profile, but does not promote weak KdV.

Third-order weak KdV needs stronger weak contracts and broader weak machinery. It is not a small extension of the frozen Heat/Burgers weak residual report slice.

## Explicit Non-goals

- no custom KdV initial-condition public API
- no configurable KdV coefficient public API
- no general KdV regime support
- no weak KdV API
- no weak derivative backend
- no WSINDy implementation
- no weak sparse recovery
- no KS runtime promotion
- no broad adapters or file loaders
- no multidimensional or nonuniform stable support
- no time-translation APIs
- no neural or callable generator APIs
- no operator-facing APIs
- no root export expansion

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

## Release Gate

`v0.25` is complete only if:

- the current KdV strong path remains direct-SVD-backed
- broader-regime KdV evidence remains diagnostic-only
- custom initial-condition and configurable-coefficient evidence stays test-only
- weak KdV remains absent from public APIs
- the KdV scope-decision example emits strict JSON
- `API_STABILITY.md` documents only the new example runner and decision, not a broadened KdV surface
- root `pdelie` remains unchanged
- CI uses one compact current release gate plus full editable tests and package smoke
- package-index publishing remains deferred until `v1.0` or later
