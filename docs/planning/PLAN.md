# PDELie — Execution Plan (V0.6)

## Current Active Milestone

**V0.6 Milestone 1 — Discovery recovery metrics**

This file is the active execution plan for the current `v0.6` release series.

It should contain:

- a short record of the completed `v0.5` release
- the frozen plan for the current active milestone
- milestone-specific rules and gates

It should not redefine package contracts or roadmap commitments. Those belong in:

- `docs/specs/SPEC.md`
- `docs/specs/CONTRACTS_AND_DEFAULTS.md`
- `docs/specs/API_STABILITY.md`
- `docs/planning/ROADMAP.md`
- `docs/planning/V0_6_SCOPE.md`

---

## V0.5 Closeout

`v0.5` is complete as the generator-family portability and external-family compatibility release.

Completed outcome:

- manifest export/import for canonical `GeneratorFamily`
- strict external-family coercion into canonical `GeneratorFamily`
- compact portability benchmark
- compact `v0.5` release gate
- KdV feasibility recorded as passed in a tests-first slice, with stable KdV promotion deferred

`v0.6` begins from that frozen release surface.

This release series is discovery-utility first.
It does not broaden the stable numerics regime beyond the current Heat/Burgers canonical slice.

---

## Milestone 1 — Discovery Recovery Metrics

**Status:** Active

### Goal

Add a small, generic recovery-metrics layer for sparse PDE discovery outputs without introducing a new canonical equation object.

### Frozen Decisions

- add `pdelie.discovery.evaluate_discovery_recovery(...)`
- `target_terms` and `discovered_terms` are mappings of canonical term string to scalar coefficient
- exact string equality defines support identity
- aliases, symbolic simplification, and term normalization are out of scope
- term keys must be non-empty strings
- coefficients must be finite
- support is `abs(coef) > support_epsilon`
- empty target + empty discovered = `exact`
- empty target + non-empty discovered = `failed`
- non-empty target + empty discovered = `failed`
- classification is support-based only:
  - `exact`
  - `partial`
  - `failed`
- no PySINDy adapter work in M1
- no translation-canonical input builder in M1
- no robustness utilities in M1
- no KdV work in M1

### Acceptance Criteria

M1 is complete only if:

- support identity is deterministic under exact string equality
- invalid term keys or non-finite coefficients fail with typed errors
- support threshold behavior is explicit and deterministic
- exact / partial / failed classification is stable for representative edge cases
- coefficient and residual summary fields are returned in one plain runtime dict
- no new canonical object is introduced

### Test Plan

Run at minimum:

- discovery recovery metrics tests
- representative edge-case tests
- full `pytest`

---

## Milestone 2 — Thin PySINDy Discovery Adapter

**Status:** Pending

### Goal

Add one narrow PySINDy-only discovery adapter for the existing scalar periodic trajectory bridge without creating a general discovery-backend framework.

### Frozen Decisions

- add `pdelie.discovery.fit_pysindy_discovery(...)`
- PySINDy only
- continuous-time only
- target derivative is exactly `"u_t"`
- accept only the current trajectory shape from `to_pysindy_trajectories(...)`
- `feature_names` are the input trajectory columns
- return:
  - `library_feature_names`
  - dense `coefficients`
  - sparse `equation_terms`
- default coefficient threshold is `1e-8`
- backend fitting failures return `status="failed"`
- missing dependency remains `ImportError`
- do not generalize into a backend framework

---

## Milestone 3 — Translation-Canonical Discovery Inputs

**Status:** Pending

### Goal

Bridge the current translation/invariant path into discovery-ready canonical inputs without implying full differential-invariant generation.

### Frozen Decisions

- add `pdelie.discovery.build_translation_canonical_discovery_inputs(...)`
- translation/canonical path only
- scalar variable only
- periodic `x` only
- per-sample initial-time peak alignment
- first-index tie-breaking
- deterministic reported shifts in batch order
- no general invariant-theory engine
- no full differential-invariant generation

---

## Milestone 4 — Robustness Utilities

**Status:** Pending

### Goal

Add plain, deterministic robustness helpers that keep `FieldBatch` semantics intact.

### Frozen Decisions

- `FieldBatch` in / `FieldBatch` out only
- deterministic noise, subsampling, and splitting
- coords are copied
- masks are preserved
- `NaN` values remain `NaN`
- noise applies only to finite unmasked values
- stride-only subsampling
- train/heldout split is deterministic and preserves original order within each split
- `preprocess_log` gets exactly one new plain-dict entry with `operation` and `parameters`
- no dataframe, plotting, or report-rendering layer

---

## Milestone 5 — V0.6 Release Gate

**Status:** Pending

### Goal

Add one compact, representative `v0.6` release gate without making discovery-performance claims.

### Frozen Decisions

- compact representative aggregation only
- raw/vanilla input slice
- oracle/known translation family input slice
- imported/coerced translation family input slice
- no discovery superiority claim
- no exact PySINDy model-string assertions
- no stable KdV surface addition
- Heat/Burgers stable paths remain unchanged

### Test Plan

Run at minimum:

- `tests/test_v0_6_release_gate.py`
- full `pytest`

---

## Later Milestones

Locked sequence:

Milestone 1 -> discovery recovery metrics  
Milestone 2 -> thin PySINDy discovery adapter  
Milestone 3 -> translation-canonical discovery inputs  
Milestone 4 -> robustness utilities  
Milestone 5 -> V0.6 release gate

Hard sequencing rules:

- do not broaden discovery metrics into a new canonical equation object
- do not turn the PySINDy adapter into a general backend framework
- do not broaden translation-canonical inputs into full invariant generation
- do not turn robustness utilities into a dataframe or plotting layer
- do not promote KdV in `v0.6`

---

## Rules

- DO NOT add new canonical objects in `v0.6`
- DO NOT add root exports from `pdelie.__init__`
- DO NOT add KdV as a stable `v0.6` surface
- DO NOT add external dataset-ingestion scope in `v0.6`
- DO NOT add weak-form methods
- DO NOT add operator methods
- DO NOT add broad adapters
- DO NOT add paper-specific experiment matrices, thresholds, figures, or manuscript logic

---

## Status

- `v0.5`: COMPLETE
- Milestone 1: ACTIVE
- Milestone 2: PENDING
- Milestone 3: PENDING
- Milestone 4: PENDING
- Milestone 5: PENDING
