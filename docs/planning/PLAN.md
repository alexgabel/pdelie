# PDELie — Execution Plan (V0.6)

## Current Release Status

**V0.6 release complete**

This file is the execution record for the completed `v0.6` release series.

It should contain:

- a short record of the completed `v0.5` release
- the frozen plan for the completed `v0.6` milestone sequence
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

**Status:** Complete

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

**Status:** Complete

### Goal

Add one narrow PySINDy-only backend-fit adapter for the existing scalar periodic trajectory bridge without creating a general discovery-backend framework or claiming canonical PDE-level equation extraction.

### Frozen Decisions

- add `pdelie.discovery.fit_pysindy_discovery(...)`
- PySINDy only
- continuous-time only
- accept only the current trajectory shape from `to_pysindy_trajectories(...)`
- all trajectories must share identical shape as a frozen M2 simplification, not as a general PySINDy limitation
- `feature_names` are the input state-feature columns and must be unique non-empty strings
- runtime owns a private frozen deterministic PySINDy default profile
- `config` must be `None`
- return a runtime backend report dict, not a JSON-compatible artifact schema
- return:
  - `library_feature_names`
  - dense 2D `coefficients` as NumPy arrays
  - sparse backend-native `equation_terms`
  - backend-native debug `equation_strings`
- default coefficient threshold is `1e-8`
- backend fitting failures return `status="failed"`
- missing dependency remains `ImportError`
- `equation_terms` and `equation_strings` are backend-native and non-canonical
- `equation_terms` and `equation_strings` must not be fed directly into `evaluate_discovery_recovery(...)` without a later canonicalization step
- do not promise a true `u_t = ...` PDE equation in M2
- do not generalize into a backend framework

---

## Milestone 3 — Translation-Canonical Discovery Inputs

**Status:** Complete

### Goal

Bridge the current translation/invariant path into discovery-ready canonical inputs without implying full differential-invariant generation or mathematically intrinsic invariant construction.

### Frozen Decisions

- add `pdelie.discovery.build_translation_canonical_discovery_inputs(...)`
- use `invariant_spec_template`, not `invariant_spec`
- exactly one of `generator_family` or `invariant_spec_template`
- translation/canonical path only
- scalar variable only
- periodic `x` only
- reject masked fields
- accept only single-row translation generators within `DEFAULT_TRANSLATION_SPAN_TOLERANCE`
- `invariant_spec_template` is explicit template mode and must not include `shift`
- per-sample initial-time peak alignment
- first-index tie-breaking
- deterministic reported shifts in batch order
- peak alignment is a heuristic canonicalization policy, not a strong invariant-theoretic guarantee
- split/apply/reassemble through the existing `InvariantApplier`
- reassembled field appends exactly one batch-level preprocess entry
- return a runtime dict with:
  - `transformed_field`
  - `trajectories`
  - `time_values`
  - `feature_names`
  - `generator_metadata`
  - `construction_method`
  - `alignment_policy`
  - `alignment_shifts`
  - `provenance`
- no general invariant-theory engine
- no full differential-invariant generation

---

## Milestone 4 — Robustness Utilities

**Status:** Complete

### Goal

Add plain, deterministic robustness helpers that keep `FieldBatch` semantics intact.

### Frozen Decisions

- add `pdelie.data.add_gaussian_noise(...)`
- add `pdelie.data.subsample_time(...)`
- add `pdelie.data.subsample_x(...)`
- add `pdelie.data.split_batch_train_heldout(...)`
- add `pdelie.discovery.summarize_recovery_grid(...)`
- `FieldBatch` in / `FieldBatch` out only for the data-side helpers
- deep-copy metadata and existing preprocess-log entries before appending new entries
- copy coord arrays, copy `var_names`, and copy/slice masks when present
- deterministic noise, subsampling, and splitting only
- noise applies only to finite unmasked values
- `NaN` and other non-finite source values remain unchanged
- `subsample_time` may leave one time point
- `subsample_x` must leave at least two x-points
- `train_size` is an integer count only
- integer-like parameters allow Python `int` and NumPy integer types but reject `bool`
- train/heldout split is deterministic and preserves original batch order within each split
- `summarize_recovery_grid(...)` consumes nested `{"conditions": ..., "recovery": ...}` runtime records
- grouped summary rows use deterministic typed sort keys over condition values
- `summarize_recovery_grid(...)` is runtime convenience only, not a canonical artifact or manuscript-table schema
- `preprocess_log` gets exactly one new plain-dict entry with `operation` and `parameters`
- no dataframe, plotting, or report-rendering layer

---

## Milestone 5 — V0.6 Release Gate

**Status:** Complete

### Goal

Add one compact, representative `v0.6` release gate without making discovery-performance claims.

### Frozen Decisions

- compact representative aggregation only
- raw/vanilla input slice
- oracle/known translation family input slice
- imported/coerced translation family input slice
- dedicated `tests/test_v0_6_release_gate.py`
- dedicated `v0_6-release-gate` CI job
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
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
