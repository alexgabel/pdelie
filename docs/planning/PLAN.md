# PDELie — Execution Plan (V0.5)

## Current Active Milestone

**V0.5 Milestone 5 — V0.5 release gate**

This file is the active execution plan for the current `v0.5` release series.

It should contain:

- a short record of the completed `v0.4` release
- the frozen plan for the current active milestone
- milestone-specific rules and gates

It should not redefine package contracts or roadmap commitments. Those belong in:

- `docs/specs/SPEC.md`
- `docs/specs/CONTRACTS_AND_DEFAULTS.md`
- `docs/specs/API_STABILITY.md`
- `docs/planning/ROADMAP.md`
- `docs/planning/V0_5_SCOPE.md`

---

## V0.4 Closeout

`v0.4` is complete as the first generator-family and algebra-inspection release.

Completed outcome:

- `GeneratorFamily` family semantics and migration policy
- runtime symbolic display
- runtime span diagnostics
- runtime closure diagnostics
- minimal optional visualization
- explicit algebra-span release gate
- Heat/Burgers regression protection preserved

`v0.5` begins from that frozen release surface.

This release series is portability / external compatibility first.
It does not broaden numerics beyond the current Heat/Burgers stable regime.

---

## Milestone 1 — Generator-family Export/Import Manifest

**Status:** Complete

### Goal

Define a stable artifact schema that lets learned or externally supplied generator families be exported, imported, validated, and reused without losing canonical meaning.

This milestone is portability-only.

### Frozen Decisions

- the manifest is a stable artifact schema, not a new canonical object
- the canonical mathematical content is `GeneratorFamily`
- optional symbolic / diagnostic / provenance fields are non-authoritative
- runtime dict export/import is in scope
- manifest payloads must be JSON-compatible
- dedicated JSON file read/write is deferred from M1; standard-library `json` over the manifest payload is sufficient
- no KdV work in M1
- no prediction utility in M1
- no downstream benchmark expansion in M1
- no broad numerics expansion in M1

### Deliverables

- manifest schema definition
- dict-level export helper
- dict-level import/validation helper
- deterministic round-trip tests
- typed errors for malformed or unsupported manifests
- documentation of required vs optional fields

### Acceptance Criteria

M1 is complete only if:

- manifests contain canonical `GeneratorFamily` payloads
- export/import round-trips preserve canonical meaning
- manifest payloads are JSON-compatible without extra normalization
- optional fields remain non-authoritative
- malformed manifests fail with typed errors
- current Heat/Burgers stable paths remain unchanged
- no new stable canonical object is introduced

### Test Plan

Run at minimum:

- manifest export/import tests
- malformed manifest tests
- external-family validation tests
- current release-gate tests
- full `pytest`

---

## Milestone 2 — External-family Compatibility

**Status:** Complete

### Goal

Normalize the frozen `v0.5` input forms into canonical `GeneratorFamily` objects without widening the existing symbolic/span/closure/viz helper signatures.

### Frozen Decisions

- add `pdelie.portability.coerce_generator_family(...)`
- accept only:
  - canonical in-memory `GeneratorFamily`
  - canonical `GeneratorFamily.to_dict()` payloads
  - frozen manifest payloads
  - the existing legacy `0.1` translation payload
- canonical in-memory input returns as-is after validation
- malformed structure -> schema error
- unsupported external conventions -> scope error
- shape mismatch -> shape error
- unknown top-level manifest fields are rejected
- no downstream smoke in M2
- no KdV work in M2
- no prediction work in M2

---

## Milestone 3 — Portability Benchmark

**Status:** Complete

### Goal

Prove that the frozen `v0.5` portability inputs preserve the behavior of the existing symbolic/span/closure/viz helpers and the existing narrow downstream bridge.

### Frozen Decisions

- M3 is docs/tests only; no new runtime public API
- benchmark semantic preservation only
- positive branches are:
  - in-memory canonical family
  - canonical payload via `coerce_generator_family(...)`
  - manifest payload via `coerce_generator_family(...)`
- legacy `0.1` translation payload is included only as a narrow compatibility smoke
- downstream coverage is limited to:
  - `InvariantMapSpec`
  - `InvariantApplier`
  - `to_pysindy_trajectories`
- do not fit or score PySINDy models in M3
- negative controls remain typed:
  - malformed manifest -> schema error
  - unsupported non-polynomial family -> scope error
- no KdV work in M3
- no prediction work in M3
- no broad numerics expansion in M3

### Acceptance Criteria

M3 is complete only if:

- positive branches show no semantic drift in symbolic rendering
- positive branches show no semantic drift in span diagnostics
- positive branches show no semantic drift in closure diagnostics
- translation branches produce identical downstream transformed fields and bridge trajectories
- legacy translation remains compatible in the narrow smoke path
- malformed and unsupported controls fail with typed errors

### Test Plan

Run at minimum:

- portability benchmark reproducibility tests
- portability manifest/coercion regression tests
- narrow downstream bridge tests
- full `pytest`

---

## Milestone 4 — KdV Feasibility

**Status:** Complete / gated

### Goal

Assess whether clean periodic KdV is a comfortable fit for the current uniform-grid, synthetic-data, `spectral_fd` regime without introducing a stable KdV runtime API.

### Frozen Decisions

- M4 remains feasibility only; no stable KdV API yet
- no root exports
- no broad numerics expansion
- no prediction/downstream broadening
- normalized periodic KdV form only:
  - `u_t + 6*u*u_x + u_xxx = 0`
- tests-first implementation only in `tests/_helpers/` and test-local helpers
- fixed rollout numerics:
  - periodic spectral spatial derivatives
  - two-thirds dealiasing for the nonlinear term
  - explicit RK4 time stepping
  - short-horizon only
- no contract changes unless feasibility proves impossible otherwise

### Acceptance Criteria

M4 is complete only if:

- third-derivative Fourier-mode accuracy passes
- synthetic KdV rollout is reproducible
- KdV residual is near zero within the frozen tolerance
- short-horizon mass and `L2` conservation look sane
- Heat/Burgers regressions remain unchanged
- the outcome is recorded explicitly as:
  - feasibility passed, stable promotion deferred
  - or deferred to `v0.6+` with rationale

Current kickoff outcome:

- tests-first normalized periodic KdV feasibility passes under the frozen short-horizon numerics
- stable promotion remains deferred to the `v0.5` release-gate review

---

## Milestone 5 — V0.5 Release Gate

**Status:** Active

### Goal

Aggregate the frozen `v0.5` guarantees from M1-M4 into one compact release-gate slice without adding new runtime functionality.

### Frozen Decisions

- M5 is release-gate aggregation only, not a new feature milestone
- no new public API
- no new canonical object
- no new numerics work
- no prediction/downstream expansion beyond the existing narrow bridge
- no KdV promotion-by-accident
- KdV outcome for `v0.5` is recorded as:
  - feasibility proven in tests-first scope
  - stable promotion deferred
  - no stable KdV API in `v0.5`
- the release gate must stay compact and high-signal
- do not duplicate the full lower-level M1-M4 test matrices

### Acceptance Criteria

M5 is complete only if:

- manifest export/import remains deterministic for representative canonical families
- coercion across the frozen input forms remains stable and typed
- the portability benchmark remains reproducible on its compact representative slice
- Heat/Burgers stable regression slices remain exact
- the KdV feasibility outcome is explicitly recorded while the stable surface remains unchanged
- the release gate introduces no new runtime API or stable KdV surface

### Test Plan

Run at minimum:

- `tests/test_v0_5_release_gate.py`
- full `pytest`

### Follow-on CI Hygiene Notes

These are not M5 blockers, but they should be revisited after the `v0.5` release gate lands:

- release-specific CI jobs are accumulating:
  - `v0_4-release-gate`
  - `v0_5-release-gate`
  - `editable-tests`
  - `package-smoke`
- this is acceptable during `v0.5` stabilization, but future CI cleanup should prefer either:
  - one current release-gate job
  - or only the latest release gate as a required branch-protection check
- `package-smoke` currently installs `dist/*.whl`
- this is acceptable in clean CI checkouts, but future hardening may prefer resolving and installing the exact built wheel path explicitly
- the `v0.5` release gate is intentionally compact and high-signal
- future release gates should continue to prefer representative integration slices over duplicating full lower-level test modules

## Later Milestones

Locked sequence:

Milestone 1 -> manifest export/import portability  
Milestone 2 -> external-family compatibility  
Milestone 3 -> portability benchmark  
Milestone 4 -> KdV feasibility  
Milestone 5 -> V0.5 release gate

- Milestone 2: external-family compatibility
- Milestone 3: portability benchmark
- Milestone 4: KdV feasibility
- Milestone 5: V0.5 release gate

Hard sequencing rules:

- do not promote KdV before the feasibility gate
- do not add prediction utility until it has a precise task definition
- do not broaden numerics during `v0.5` without an explicit scope reset
- do not introduce weak-form methods inside `v0.5`
- do not turn the manifest into a new canonical object without explicit review

---

## Rules

- DO NOT add weak-form methods
- DO NOT add operator methods
- DO NOT add broad dataset adapters
- DO NOT add neural generators as stable API
- DO NOT add representative-loss or research-loss code
- DO NOT add broad PDE-zoo scope
- DO NOT add paper-specific or manuscript-facing language

---

## Status

- `v0.4`: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE / GATED
- Milestone 5: ACTIVE
