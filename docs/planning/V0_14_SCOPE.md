# V0.14 Scope Freeze

## Summary

`v0.14` is the invariant workflow summary and read-only translation orbit report release.

Stable release theme:

> combine existing coverage, consistency, fit, and verification diagnostics into reusable runtime summaries while keeping orbit handling report-only.

Stable path:

`FieldBatch + uniform x-translation shifts + optional windows + residual/fit/verification outputs -> read-only orbit report + combined invariant workflow summary`

These helpers support invariant and finite-transform workflows.
They are read-only runtime reports, not augmented datasets, transformed `FieldBatch` collections, orbit datasets, or canonical objects.

---

## Stable Scope

`v0.14` adds two runtime public APIs under submodules only:

```python
pdelie.invariants.summarize_uniform_translation_orbit(
    field,
    *,
    shifts,
    windows=None,
    residual_evaluator=None,
    source_field_id=None,
) -> dict[str, Any]

pdelie.reporting.summarize_invariant_workflow(
    *,
    orbit=None,
    coverage=None,
    consistency=None,
    generator=None,
    verification=None,
    fit_diagnostics=None,
    extra_metrics=None,
) -> dict[str, Any]
```

Both helpers:

- return JSON-compatible runtime report dicts
- mutate no inputs
- create no canonical objects
- have no root `pdelie` exports
- are supportability diagnostics, not manuscript schemas or sparse-discovery policy

`source_field_id` is optional JSON-compatible provenance metadata only.
It is not a canonical identity system.

`v0.14` also adds:

- `python -m pdelie.examples.invariant_workflow_summary`
- `pdelie.examples.run_invariant_workflow_summary_example(...)`
- compact `v0_14-release-gate` coverage

The example output is a runtime smoke summary, not a canonical artifact schema.

---

## `summarize_uniform_translation_orbit(...)` Semantics

Supported inputs:

- canonical scalar 1D uniform periodic `FieldBatch`
- non-empty finite uniform `x` shifts
- optional periodic windows using the frozen `v0.13` coverage semantics
- optional residual evaluator using the frozen `v0.13` consistency semantics
- optional JSON-compatible `source_field_id`

Report semantics:

- uses existing `InvariantApplier` and uniform `x` translation
- preserves raw shift order and duplicate shifts
- includes normalized shifts
- includes one transform spec and provenance summary per shift
- includes optional coverage diagnostics when windows are supplied
- includes uniform-translation consistency diagnostics for every shift
- returns no transformed `FieldBatch` objects
- constructs no augmented dataset or orbit dataset

---

## `summarize_invariant_workflow(...)` Semantics

Supported inputs:

- `periodic_window_coverage` reports
- `uniform_translation_consistency` reports
- `uniform_translation_orbit` reports
- `GeneratorFamily` objects or `generator_family` summaries
- `VerificationReport` objects or `verification_report` summaries
- `GeneratorFamily` objects or `generator_fit_diagnostics` summaries for fit diagnostics
- optional JSON-compatible extra metrics

The helper nests existing summaries where canonical objects are supplied.
It does not change the existing `v0.10` or `v0.12` reporting schemas.

---

## Non-goals

`v0.14` explicitly does not include:

- a new PDE
- stable KS generator promotion
- stable KS residual evaluator promotion
- KS example or imported parity
- weak KS
- broad adapters
- PDEBench or The Well support
- multidimensional grids
- nonuniform grids
- multivariable systems
- operator-facing symmetry APIs
- public augmentation utilities
- orbit dataset builders
- transformed `FieldBatch` collections as reports
- train-augmentation policy
- sparse-discovery branch policy
- private-paper experiment logic
- manuscript-specific thresholds, tables, figures, or labels
- root `pdelie` export expansion
- time-translation APIs
- `axis="time"` support in `InvariantApplier`
- time-shift consistency diagnostics

There is no time-translation API in `v0.14`.
Time-translation diagnostics remain deferred until a separate semantics freeze decides finite-time boundary behavior, interpolation policy, and residual-invariance expectations.

---

## Milestones

### Milestone 0 - Scope Freeze

Freeze `v0.14` as invariant workflow summaries plus read-only uniform translation orbit reports.

### Milestone 1 - API Semantics Freeze

Freeze report schemas, `source_field_id` provenance behavior, and report-only orbit semantics.

### Milestone 2 - Combined Invariant Workflow Summary

Implement `pdelie.reporting.summarize_invariant_workflow(...)` and document it in `API_STABILITY.md`.

### Milestone 3 - Uniform Translation Orbit Report

Implement `pdelie.invariants.summarize_uniform_translation_orbit(...)` and document it in `API_STABILITY.md`.

### Milestone 4 - Useful End-to-end Example

Add `python -m pdelie.examples.invariant_workflow_summary` and `pdelie.examples.run_invariant_workflow_summary_example(...)`.

### Milestone 5 - API / Public-surface Audit

Confirm the new APIs are submodule-only and no augmentation, orbit dataset, time-translation, KS, weak KS, broad adapter, or operator API landed.

### Milestone 6 - Release Gate and Readiness

Add `tests/test_v0_14_release_gate.py`, update CI, bump package metadata to `0.14.0`, and align release-facing docs.

---

## Release-gate Expectations

Expected gate coverage:

- `summarize_invariant_workflow(...)` is documented and submodule-only
- `summarize_uniform_translation_orbit(...)` is documented and submodule-only
- representative Heat and KdV invariant workflow summaries are JSON-compatible
- orbit reports return no transformed `FieldBatch` objects
- root `pdelie` remains unchanged
- no public augmentation, orbit dataset, time-translation, KS, weak KS, broad adapter, or operator API lands
- current CI uses `v0_14-release-gate` plus full editable tests and package smoke

---

## Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE
