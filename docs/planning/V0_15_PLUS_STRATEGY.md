# V0.15+ Strategy

This document records the planned post-`v0.14` direction.
It is a strategy note, not an active scope freeze and not an API contract.

The active execution record remains `PLAN.md`.
Stable contracts remain in `docs/specs/API_STABILITY.md` only after APIs land.

## Summary

After `v0.14`, the highest-ROI path is to move from read-only invariant diagnostics toward conservative user-facing data utilities, then external symmetry-candidate validation, then non-polynomial generator support, then carefully scoped PDE expansion.

Planned sequence:

- `v0.15`: materialized uniform translation orbit batches
- `v0.16`: external symmetry-candidate interop and validation
- `v0.17`: formula-backed and non-polynomial generator families
- `v0.18+`: scoped PDE expansion

PDELie should remain a reusable library and validation/reporting substrate.
It should not become a neural symmetry-detector training framework.

---

## V0.15 - Materialized Uniform Translation Orbit Batches

Planned theme:

> promote the first conservative user-facing data utility for materializing finite uniform translation orbits from canonical `FieldBatch` inputs.

Candidate API direction:

```python
pdelie.invariants.build_uniform_translation_orbit_batch(
    field,
    *,
    shifts,
    keep_source_index=True,
    keep_shift_index=True,
    copy=True,
)
```

`build_uniform_translation_orbit_batch(...)` is the preferred candidate name because it says the helper returns a batch-oriented data product.
The exact name and return type must still be frozen in `v0.15` M1.

Semantics to freeze before implementation:

- augmentation appends along the batch dimension
- output ordering is deterministic and preserves duplicate shifts
- source indices and shift indices are recorded as provenance/report metadata
- duplicate shifts are preserved rather than deduplicated
- masks are transformed and concatenated consistently with existing `InvariantApplier` behavior
- preprocess logs append one orbit-materialization entry
- output metadata records group/action parameters, normalized shifts, and duplicate-shift policy
- no train/test policy is applied
- no split management or heldout-leakage detection is attempted
- source IDs may be recorded, but the helper does not manage experimental partitions

Return-shape policy to freeze:

- prefer an explicit structured return such as `(FieldBatch, report)` or a named structured pair
- avoid a silent `FieldBatch`-only return because users need source/shift provenance
- avoid returning transformed fields inside a JSON report

Explicit non-goals:

- no sparse-discovery branch policy
- no train/heldout split management
- no paper-specific augmentation recipe
- no time translation
- no new PDE
- no root exports unless separately accepted

This would be useful beyond PDELie itself: users could feed the materialized orbit batch into PySINDy, a neural solver, PDE-FIND-style code, or their own model while keeping provenance explicit.

---

## V0.16 - External Symmetry-candidate Interop

Planned theme:

> validate external symmetry candidates without training the detectors that produced them.

Candidate API direction:

```python
pdelie.symmetry.validate_generator_candidate(
    field,
    candidate,
    *,
    residual_evaluator,
    finite_transform_epsilons=None,
) -> dict[str, Any]
```

External methods may provide:

- an existing `GeneratorFamily`
- a finite-transform specification
- a callable transform descriptor
- a JSON-compatible symmetry-candidate report

PDELie should validate candidates using:

- finite-transform consistency
- residual preservation
- span or closure diagnostics when applicable
- provenance checks
- optional fit and verification summaries

Design boundary:

- this is detector interop, not sparse-discovery reporting
- this is validation/reporting, not neural-generator training
- learned-generator methods may slot in by exporting candidates, but PDELie does not train those models
- callable descriptors should remain less stable than JSON-compatible candidate records unless accompanied by diagnostic reports

This keeps PDELie compatible with learned-generator or Lie-algebra-aware methods without becoming a neural symmetry-discovery framework.

---

## V0.17 - Formula-backed And Non-polynomial Generators

Planned theme:

> support richer generator descriptions without jumping directly to neural generator classes.

Phase 1 should focus on formula-backed generator records for:

- affine generators
- trigonometric generators
- rational or simple analytic forms
- externally supplied symbolic references

Required semantics to freeze:

- JSON-serializable formula metadata
- evaluation policy on canonical fields
- finite-transform availability, or explicit `infinitesimal_only` status
- validation diagnostics
- compatibility with existing reporting helpers

Phase 2 may allow callable or external generators, but those should be treated as less stable unless paired with diagnostic reports.

Phase 3 may allow learned-generator interop through accepted outputs only.
PDELie should validate such outputs; it should not train learned generators.

Key design decision for `v0.17`:

- decide whether formula-backed generators require a new canonical object such as `FormulaGeneratorFamily`
- or whether a runtime metadata record is enough for the first stable slice

The conservative default is a runtime formula-backed record first, with no change to existing polynomial `GeneratorFamily` semantics until the compatibility story is proven.

---

## V0.18+ - Scoped PDE Expansion

Planned theme:

> add another stable numerical axis only after the invariant/data-utility surface remains supportable.

Preferred stable expansion:

- advection-diffusion or reaction-diffusion, because they are likely to fit the current scalar/structured-data contracts with less ambiguity than KS promotion

Alternative scoped expansion:

- KS residual-only, but only if the public claim explicitly excludes direct residual-based fitting recovery

Deferred until separately frozen:

- broad PDE zoo expansion
- PDEBench or The Well adapters
- multidimensional grids
- nonuniform grids
- operator-facing APIs
- weak KS
- learned-generator training

Each PDE expansion requires its own scope freeze and release-gate evidence.

---

## Relationship To V1.0

These releases should move PDELie toward `v1.0` by improving supportability, provenance, and interoperability before increasing scientific scope too aggressively.

The preferred sequence is:

1. materialize finite translation orbits safely
2. validate external symmetry candidates
3. represent non-polynomial formulas
4. only then widen stable PDE coverage

Package-index publishing, broad adapters, and stable v1 API commitments remain deferred until a dedicated `v1.0` readiness milestone.
