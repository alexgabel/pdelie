# V0.15+ Strategy

This document records the staged post-`v0.14` direction.
It is a strategy note, not an active scope freeze and not an API contract.

The active execution record remains `PLAN.md`.
Stable contracts remain in `docs/specs/API_STABILITY.md` only after APIs land.

## Summary

After `v0.14`, the highest-ROI path has been to move from read-only invariant diagnostics toward conservative user-facing data utilities, then external symmetry-candidate validation, then formula-backed generator support, then carefully scoped PDE expansion.

After `v0.20`, the next planned path is to harden external-data readiness, downstream discovery contracts, and split/leakage provenance before considering more difficult axes such as weak forms, broader KdV/KS, multi-generator fitting, broad adapters, multidimensional/nonuniform grids, and time-translation actions.

Staged sequence:

- `v0.15`: materialized uniform translation orbit batches
- `v0.16`: external symmetry-candidate interop and validation
- `v0.17`: formula-backed generator families
- `v0.18`: stable Fisher-KPP reaction-diffusion strong path
- `v0.19`: stable advection-diffusion strong path
- `v0.20`: unified generator confidence reports
- `v0.21`: planned external data readiness reports
- `v0.22`: planned downstream discovery contracts
- `v0.23`: planned split/leakage provenance diagnostics
- `v0.24`: planned weak-form supportability reset
- `v0.25`: planned KdV scope decision
- `v0.26`: planned KS revisit
- `v0.27`: planned multi-generator feasibility
- `v0.28`: planned data ecosystem feasibility
- `v0.29`: planned grid-domain feasibility
- `v0.30`: planned orbit/action scope decision
- `v0.31`: planned `v1.0` readiness hardening

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

## V0.18 And V0.19 Completed PDE Expansion

`v0.18` completed the first scoped PDE expansion by adding the stable scalar 1D periodic Fisher-KPP reaction-diffusion strong path.

`v0.19` completed the second scoped PDE expansion:

> add one safe transport-plus-diffusion PDE under the same scalar 1D periodic order-2 derivative regime.

Completed stable path:

```text
canonical scalar 1D periodic FieldBatch
-> spectral_fd u_t/u_x/u_xx
-> constant-coefficient advection-diffusion residual
-> translation fit/verification
-> vertical-slice example
```

Frozen equation:

```text
u_t + c*u_x = nu*u_xx
residual = u_t + c*u_x - nu*u_xx
```

Deferred after `v0.19`:

- variable coefficients
- reaction-advection-diffusion
- weak advection-diffusion
- nonperiodic boundaries
- custom initial-condition APIs
- multidimensional grids
- nonuniform grids

Like `v0.18`, `v0.19` shipped only because direct residual-based fitting evidence was in tolerance.

---

## V0.20 - Unified Generator Confidence Reports

Completed theme:

> promote the notebook confidence-card pattern into a public supportability/reporting helper.

Implemented scope:

- residual health summaries
- fit conditioning and singular-value summaries
- selected/SVD span evidence
- finite-transform verification summaries
- candidate-validation conclusions
- orbit/coverage/consistency diagnostics
- configured threshold interpretation
- categorical confidence labels and component statuses

Explicit boundaries:

- no transformed `FieldBatch` collections from reporting helpers
- no train/test policy
- no downstream success policy
- no mathematical-proof claim
- no scalar confidence score

---

## V0.21 - External Data Readiness Reports

Planned theme:

> make user-owned scalar 1D periodic data safer to bring into the stable runtime before broad adapters land.

Candidate scope:

- stronger `FieldBatch` audit reports
- coordinate and grid diagnostics
- metadata completeness diagnostics
- finite-value, mask, scalar-var, and shape diagnostics
- residual-evaluator compatibility preflight
- conservative metadata inference for explicit, low-risk cases

Deferred:

- `xarray.Dataset` support
- file-based dataset loaders
- PDEBench and The Well adapters
- multidimensional or nonuniform-grid ingestion

---

## V0.22 - Downstream Discovery Contracts

Planned theme:

> standardize downstream discovery reporting without becoming a full experiment-policy framework.

Candidate scope:

- broad downstream discovery contracts for runtime reports
- recovery and provenance summary reports
- backend-native bridge-output summaries
- orbit-materialization provenance checks
- paper-agnostic downstream templates

Deferred:

- general discovery-backend framework
- manuscript thresholds
- automatic experiment policy
- backend lock-in beyond thin adapters

---

## V0.23 - Split/Leakage Provenance Diagnostics

Planned theme:

> reduce orbit-materialization misuse by reporting provenance risks across user-supplied partitions.

Candidate scope:

- train/heldout partition diagnostics
- source/shift overlap reports
- heldout-leakage risk reports

Explicit boundaries:

- no train/test split management
- no automatic split generation
- no downstream augmentation policy
- no benchmark success criteria

---

## V0.24 - Weak-Form Supportability Reset

Planned theme:

> decide whether weak derivatives and broader weak-form methods can be promoted beyond the frozen `v0.8` weak residual report slice.

Candidate scope:

- weak derivative backend feasibility
- broader weak-form residual contracts
- weak reaction-diffusion feasibility
- noisy/coarse-data supportability diagnostics

Deferred unless separately proven:

- weak KdV APIs
- weak KS APIs
- broad weak-form superiority claims

---

## V0.25 - KdV Scope Decision

Planned theme:

> decide whether KdV should remain frozen or expand beyond normalized periodic short-horizon support.

Candidate decisions:

- custom KdV initial conditions
- configurable KdV coefficients
- general KdV support outside the frozen normalized periodic short-horizon regime
- weak KdV APIs

Acceptable outcome:

- keep KdV frozen and document why if the broader regime is not supportable.

---

## V0.26 - KS Revisit

Planned theme:

> revisit the `v0.11`/`v0.12` KS no-go with better confidence diagnostics.

Candidate decisions:

- stable KS data generator
- stable KS residual evaluator
- KS vertical-slice example
- KS imported parity
- weak KS API
- root KS export
- continued no-go/defer

Default stance:

- no root KS export
- no weak KS
- no stable full KS path unless direct residual-based fitting evidence improves

---

## V0.27 - Multi-Generator Feasibility

Planned theme:

> test whether the single-generator-centered runtime can support stable multi-generator workflows.

Candidate scope:

- stable multi-generator PDE fitting feasibility
- multi-generator invariant machinery feasibility
- closure/span/verification interactions for fitted families

Boundary:

- this is high-risk core machinery and should not be mixed with a PDE, adapter, or weak-form release.

---

## V0.28 - Data Ecosystem Feasibility

Planned theme:

> decide whether external data ecosystem support can widen without weakening canonical contracts.

Candidate scope:

- `xarray.Dataset` support
- file-based dataset loaders
- narrow adapter feasibility
- metadata inference expansion

Deferred unless scope is frozen:

- PDEBench / The Well as stable APIs
- broad adapter framework
- implicit alias-based loaders

---

## V0.29 - Grid-Domain Feasibility

Planned theme:

> evaluate multidimensional and nonuniform-grid ingestion as a contract change.

Candidate scope:

- multidimensional ingestion feasibility
- nonuniform-grid ingestion feasibility
- resampling/reporting decisions
- derivative/residual compatibility diagnostics for unsupported grids

Default stance:

- unsupported until a dedicated scope freeze proves the contracts.

---

## V0.30 - Orbit/Action Scope Decision

Planned theme:

> decide whether invariant actions should expand beyond frozen uniform spatial translation materialization.

Candidate scope:

- public orbit-view builders beyond the frozen materialized uniform translation orbit batch helper
- transformed `FieldBatch` collection policy for explicit data/invariant APIs
- time-translation APIs
- `axis="time"` support

Boundary:

- reporting helpers remain report-only
- transformed collections must not be returned from reporting helpers

---

## V0.31 - V1.0 Readiness Hardening

Planned theme:

> freeze the public engine before `v1.0`.

Candidate scope:

- public/private API audit
- root export policy audit
- deprecation policy
- package publishing plan
- docs and notebook consistency audit
- release-gate consolidation
- support matrix for stable PDEs, grids, residuals, candidate types, and downstream paths

---

## Relationship To V1.0

These releases should move PDELie toward `v1.0` by improving supportability, provenance, interoperability, and scoped numerical coverage before freezing the public contract.

The preferred sequence is:

1. materialize finite translation orbits safely
2. validate external symmetry candidates
3. represent non-polynomial formulas
4. widen stable PDE coverage one axis at a time
5. consolidate confidence reporting
6. harden external data and downstream reporting
7. decide weak/KdV/KS/multi-generator/grid boundaries explicitly
8. run a dedicated `v1.0` readiness hardening release

Package-index publishing, broad adapters, and stable v1 API commitments remain deferred until a dedicated `v1.0` readiness milestone.
