# V0.15+ Strategy

This document records the staged post-`v0.14` direction.
It is a strategy note, not an active scope freeze and not an API contract.

The active execution record remains `PLAN.md`.
Stable contracts remain in `docs/specs/API_STABILITY.md` only after APIs land.

## Summary

After `v0.14`, the highest-ROI path has been to move from read-only invariant diagnostics toward conservative user-facing data utilities, then external symmetry-candidate validation, then formula-backed generator support, then carefully scoped PDE expansion.

Staged sequence:

- `v0.15`: materialized uniform translation orbit batches
- `v0.16`: external symmetry-candidate interop and validation
- `v0.17`: formula-backed generator families
- `v0.18+`: scoped PDE expansion

PDELie should remain a reusable library and validation/reporting substrate.
It should not become a neural symmetry-detector training framework.

---

## V0.15 - Materialized Uniform Translation Orbit Batches

Completed theme:

> promote the first conservative user-facing data utility for materializing finite uniform translation orbits from canonical `FieldBatch` inputs.

Implemented API direction:

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

`build_uniform_translation_orbit_batch(...)` is the selected public name because it says the helper returns a batch-oriented data product.
The completed scope freeze belongs in `V0_15_SCOPE.md`.

Completed semantics:

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

Return-shape policy:

- use `OrbitBatchResult(field, report)` as an explicit structured return
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

Completed theme:

> validate external symmetry candidates without training the detectors that produced them.

Implemented API direction:

```python
pdelie.symmetry.validate_symmetry_candidate(
    field,
    candidate,
    *,
    residual_evaluator,
    reference_generator=None,
    finite_transform_epsilons=None,
    source_candidate_id=None,
) -> dict[str, Any]
```

External methods may provide in `v0.16`:

- an existing `GeneratorFamily`
- a canonical `GeneratorFamily` payload mapping
- an existing `InvariantMapSpec`
- a canonical `InvariantMapSpec` payload mapping

PDELie validates candidates using:

- finite-transform verification where applicable
- residual preservation for supported invariant-map specs
- span or closure diagnostics when applicable
- provenance checks
- verification summaries

Design boundary:

- this is detector interop, not sparse-discovery reporting
- this is validation/reporting, not neural-generator training
- learned-generator methods may slot in by exporting candidates, but PDELie does not train those models
- callable descriptors and learned-generator APIs remain deferred beyond `v0.17`

This keeps PDELie compatible with learned-generator or Lie-algebra-aware methods without becoming a neural symmetry-discovery framework.

---

## V0.17 - Formula-backed Generator Families

Completed theme:

> support richer generator descriptions without jumping directly to neural generator classes.

Implemented API direction:

```python
pdelie.symmetry.FormulaGeneratorFamily
pdelie.reporting.summarize_formula_generator_family(...)
pdelie.symmetry.validate_symmetry_candidate(..., candidate=FormulaGeneratorFamily(...), ...)
```

The completed first phase focuses on formula-backed runtime records for:

- affine generators
- trigonometric generators
- rational or simple analytic forms
- externally supplied symbolic references

Completed semantics:

- JSON-compatible formula metadata and strict payload round trips
- safe JSON AST expressions rather than executable strings
- finite formula-evaluation diagnostics on canonical scalar 1D periodic fields
- optional finite-transform validation through attached `InvariantMapSpec` payloads
- symbolic references as metadata-only expressions
- compatibility with existing symmetry-candidate validation reports

Callable or external executable generators remain deferred and should be treated as less stable unless paired with diagnostic reports.

Later learned-generator interop should still work through accepted outputs only.
PDELie should validate such outputs; it should not train learned generators.

Selected design for `v0.17`:

- `FormulaGeneratorFamily` is a runtime-only structured record
- it is not a canonical object
- it does not change existing polynomial `GeneratorFamily` semantics

The completed scope freeze belongs in `V0_17_SCOPE.md`.

---

## V0.18 Completed And V0.19+ Scoped PDE Expansion

`v0.18` completed the first scoped PDE expansion by adding the stable scalar 1D periodic Fisher-KPP reaction-diffusion strong path.

Future planned theme:

> add another stable numerical axis only after the invariant/data-utility surface remains supportable.

Preferred stable expansion:

- advection-diffusion or another tightly scoped reaction-diffusion variant, because they are likely to fit the current scalar/structured-data contracts with less ambiguity than KS promotion

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
