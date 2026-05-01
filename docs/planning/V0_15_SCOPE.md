# V0.15 Scope Freeze

## Summary

`v0.15` is the materialized uniform translation orbit batch release.

Stable release theme:

> promote the first conservative user-facing data utility for materializing finite uniform translation orbits from canonical `FieldBatch` inputs.

Stable path:

`canonical scalar 1D periodic FieldBatch + finite uniform x-shifts -> materialized orbit FieldBatch + JSON-compatible provenance report`

This release turns the `v0.13` and `v0.14` diagnostic evidence into one narrow data utility.
It remains paper-agnostic and does not add train/test policy, split management, time translation, new PDEs, KS promotion, weak KS, broad adapters, operator APIs, or root exports.

---

## Stable Scope

`v0.15` adds one runtime public API and one runtime-only structured return under `pdelie.invariants`:

```python
pdelie.invariants.build_uniform_translation_orbit_batch(
    field,
    *,
    shifts,
    keep_source_index=True,
    keep_shift_index=True,
    source_field_id=None,
    copy=True,
) -> OrbitBatchResult

pdelie.invariants.OrbitBatchResult(
    field: FieldBatch,
    report: dict[str, Any],
)
```

`OrbitBatchResult` is not a canonical object.
It has no schema migration policy and no `.to_dict()` / `.from_dict()` contract.

The helper:

- supports canonical scalar 1D uniform periodic `FieldBatch` inputs only
- uses existing `InvariantApplier` uniform `x` translation
- returns a materialized `FieldBatch` plus a JSON-compatible provenance report
- mutates no inputs
- has no root `pdelie` export

---

## Materialization Semantics

Shift semantics:

- `shifts` must be a non-empty sequence of finite floats
- raw shift order is preserved
- duplicate shifts are preserved
- normalized shifts are recorded modulo the inferred periodic domain length

Batch semantics:

- materialization appends along the `batch` dimension
- output ordering is `shift_major`
- for each raw shift in input order, all source batch rows appear in original source-batch order
- output batch size is `source_batch_size * len(shifts)`

Provenance semantics:

- optional `source_field_id` is JSON-compatible provenance metadata only
- `source_field_id` is not a canonical identity system
- source batch indices are included when `keep_source_index=True`
- shift indices are included when `keep_shift_index=True`
- duplicate shifts remain traceable through shift indices and batch records
- output metadata records an `orbit_materialization` entry
- output preprocess log appends one aggregate `materialize_uniform_translation_orbit_batch` entry

Mask and copy semantics:

- `mask=None` remains `None`
- non-`None` masks are taken from transformed fields and concatenated along batch
- transformed values are always newly computed through `InvariantApplier`
- `copy=True` is the conservative default
- `copy=False` may avoid extra coordinate or mask copies where safe, but the helper still mutates no inputs

---

## Non-goals

`v0.15` explicitly does not include:

- train/test policy
- train/heldout split management
- heldout-leakage detection
- sparse-discovery branch policy
- private-paper augmentation recipes
- time-translation APIs
- no time-translation APIs are included in this release
- `axis="time"` support in `InvariantApplier`
- new PDE support
- stable KS generator promotion
- stable KS residual evaluator promotion
- weak KS
- broad dataset adapters
- PDEBench or The Well support
- multidimensional grids
- nonuniform grids
- multivariable systems
- operator-facing symmetry APIs
- root `pdelie` export expansion

---

## Milestones

### Milestone 0 - Scope Freeze

Freeze `v0.15` as materialized uniform translation orbit batches.

### Milestone 1 - API Semantics Freeze

Freeze API name, `OrbitBatchResult` status, batch ordering, provenance fields, mask behavior, metadata/preprocess composition, and copy semantics.

### Milestone 2 - Orbit Batch Implementation

Implement `pdelie.invariants.build_uniform_translation_orbit_batch(...)` and `pdelie.invariants.OrbitBatchResult`.
Document both in `API_STABILITY.md`.

### Milestone 3 - Compatibility And Diagnostics

Verify materialized Heat and KdV orbit batches remain valid `FieldBatch` objects and remain compatible with derivatives, residual evaluators, and reporting helpers.

### Milestone 4 - Example

Add `python -m pdelie.examples.translation_orbit_batch` and `pdelie.examples.run_translation_orbit_batch_example(...)`.

### Milestone 5 - API / Public-surface Audit

Confirm the new API remains submodule-only and no train/test policy, time translation, KS runtime, weak KS, broad adapter, or operator API landed.

### Milestone 6 - Release Gate and Readiness

Add `tests/test_v0_15_release_gate.py`, update CI, bump package metadata to `0.15.0`, and align release-facing docs.

---

## Release-gate Expectations

Expected gate coverage:

- `build_uniform_translation_orbit_batch(...)` is documented and submodule-only
- `OrbitBatchResult` is documented and submodule-only
- representative Heat and KdV orbit batches validate as `FieldBatch` objects
- output batch shape follows shift-major ordering
- duplicate shifts are preserved
- source/shift provenance is traceable
- residual diagnostics remain finite on representative materialized batches
- root `pdelie` remains unchanged
- no train/test policy, time translation, KS runtime, weak KS, broad adapter, or operator API lands
- current CI uses `v0_15-release-gate` plus full editable tests and package smoke

---

## Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE
