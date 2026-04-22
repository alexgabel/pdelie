# PDELie — Execution Plan (V0.5)

## Current Active Milestone

**V0.5 Milestone 2 — External-family compatibility**

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

**Status:** Active

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
- Milestone 2: ACTIVE
- Milestone 3: PLANNED
- Milestone 4: PLANNED / GATED
- Milestone 5: PLANNED
