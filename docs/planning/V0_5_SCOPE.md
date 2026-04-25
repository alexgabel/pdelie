# V0.5 Scope

## Summary

`v0.5` is the first **generator-family portability and external-family compatibility** release for PDELie.

It does **not** introduce a new numerical regime.  
It does **not** make weak-form methods, operator methods, neural generators, or broad dataset adapters part of the stable library.  
It does **not** commit to a broad PDE benchmark zoo.

Instead, it asks:

> Can learned or externally supplied polynomial Lie generator families be exported, imported, validated, inspected, and used in controlled downstream workflows without losing their semantics?

`v0.5` is therefore a portability release, not a broader numerics or PDE-zoo release.
Prediction-facing utility remains deferred unless it is narrowed later with a precise fixed task.

---

## Stable Scope

Stable scope for `v0.5`:

- uniform rectilinear grids only
- synthetic PDE data only
- polynomial Lie point generator families only
- Heat/Burgers stable paths remain regression-protected
- generator-family export/import manifest
- external-family validation and compatibility
- controlled portability benchmark
- current symbolic/span/closure/viz helpers remain available
- no new stable canonical object unless absolutely necessary

Gated / feasibility-only:

- KdV feasibility as a higher-derivative stress test

Deferred:

- stable KdV release path unless feasibility passes
- prediction-facing utility task unless explicitly narrowed
- weak-form methods
- operator methods
- broad numerics expansion beyond the current stable regime
- broad adapters
- broad PDE zoo

---

## Core User Story

`v0.5` should support four forms of generator-family input:

1. an in-memory canonical `GeneratorFamily`
2. a canonical `GeneratorFamily.to_dict()` payload
3. a `pdelie.generator_family_export` manifest containing a canonical generator family
4. the existing narrow legacy `0.1` translation payload via the already-defined compatibility path

Unsupported in stable `v0.5`:

- arbitrary symbolic generator strings
- arbitrary handwritten equations without `basis_spec`
- non-polynomial generators
- neural generators
- unsupported component or basis conventions
- stable multi-generator PDE fitting

---

## Export Manifest Policy

The export manifest is a **stable artifact schema**, not a new canonical object.

Required fields:

- `manifest_schema_version`
- `manifest_type`
- `generator_family`

Optional fields:

- `pdelie_version`
- `symbolic`
- `diagnostics`
- `provenance`
- downstream compatibility hints

Top-level manifest field policy in stable `v0.5`:

- required fields must exist
- known optional fields may exist
- unknown top-level manifest fields are rejected

The mathematical content of the manifest is the canonical `GeneratorFamily`.

Symbolic summaries, span diagnostics, closure diagnostics, visualization hints, and provenance are optional metadata. They are not canonical meaning.

Stable `v0.5` scope is the manifest schema plus runtime dict-level export/import over JSON-compatible payloads.

Dedicated JSON file read/write is not required for stable M1 scope. Users may serialize manifests with the standard-library `json` module. Thin file helpers may be added later without changing manifest semantics.

---

## KdV Policy

KdV is a candidate stable PDE path, but it is not automatically part of the `v0.5` stable release.

KdV first enters as a **feasibility milestone**.

It may be promoted only if:

- spectral third-derivative accuracy tests pass on clean periodic functions
- synthetic KdV data generation is reproducible
- a KdV residual evaluator gives near-zero residual on trusted data
- no redesign of `FieldBatch`, `DerivativeBatch`, or residual ontology is required
- Heat/Burgers regressions remain unchanged

If KdV fails this feasibility gate, it moves to `v0.6+`.

Weak-form methods are not required for the clean synthetic feasibility pass, but they remain the likely long-term route for noisy/high-derivative PDE discovery.

---

## Prediction Utility Policy

Prediction utility is not committed as stable `v0.5` scope unless narrowed later.

If included later, it must be defined as:

- a fixed lightweight predictor
- a fixed input representation
- a fixed target metric
- a fixed comparison against raw / canonicalized / nuisance features
- no neural operators
- no broad forecasting framework

Until that is frozen, prediction utility remains `v0.6+` planning.

---

## Frozen Milestones

### Milestone 1 — Generator-family export/import manifest
**Status:** Complete

- define manifest schema
- export canonical `GeneratorFamily`
- import/validate manifest
- no new canonical object unless unavoidable

### Milestone 2 — External-family compatibility
**Status:** Complete

- validate externally supplied canonical generator families
- support runtime dict/object ingestion
- run symbolic/span/closure/viz helpers on imported families
- typed failures for unsupported families

### Milestone 3 — Portability benchmark
**Status:** Complete

Compare:

- in-memory family
- canonical payload normalized through `coerce_generator_family(...)`
- exported/imported manifest family normalized through `coerce_generator_family(...)`
- nuisance / malformed control

The goal is semantic preservation after export/import, not a repeat of the `v0.3` downstream benchmark.
Legacy `0.1` translation compatibility remains a narrow smoke path only, not a first-class benchmark branch.

### Milestone 4 — KdV feasibility
**Status:** Complete / gated

- spectral third-derivative stress tests
- synthetic KdV data feasibility
- KdV residual feasibility
- short-horizon conservation sanity
- promotion decision: stable path or defer to `v0.6+`

M4 remains tests-first and feasibility-only:

- no stable KdV API yet
- no root exports
- no broad numerics expansion
- no prediction/downstream broadening

Current kickoff outcome:

- normalized periodic KdV feasibility passes in the tests-first slice
- stable KdV promotion remains deferred to the release gate

### Milestone 5 — V0.5 release gate
**Status:** Active

- compact, high-signal release-gate aggregation only
- manifest export/import stability on representative canonical families
- coercion and frozen input-form stability on representative external-family inputs
- portability benchmark reproducibility on a representative slice
- Heat/Burgers regression protection on a representative slice
- KdV feasibility outcome explicitly recorded as:
  - feasibility proven in tests-first scope
  - stable promotion deferred
  - no stable KdV API in `v0.5`
- no new public API
- no new canonical object
- no new numerics work
- no prediction/downstream expansion

---

## Release Gate

`v0.5` is releasable only if:

- Heat/Burgers stable paths still pass unchanged
- generator-family manifests export/import deterministically
- external canonical families can be validated and inspected
- malformed or unsupported external families fail with typed errors
- portability benchmark shows no semantic drift between in-memory and imported families
- KdV feasibility outcome is explicitly recorded while no stable KdV surface is added in `v0.5`
- no weak-form, operator, neural, broad-adapter, or manuscript-facing feature is required

---

## Explicit Non-goals

- weak-form methods
- operator symmetry
- neural generators as stable API
- representative-loss or research-loss code
- broad dataset adapters
- broad PDE zoo
- stable wave-equation pipeline
- stable KdV path without feasibility gate
- vague prediction utility
- arbitrary symbolic-string import
- paper-specific or manuscript-facing logic
