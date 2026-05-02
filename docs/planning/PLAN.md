# PDELie - Execution Plan (V0.16)

## Current Release Status

**V0.16 is complete as external symmetry-candidate validation**

This file is the completed execution record for the `v0.16` release series.

Committed release theme:

`canonical scalar 1D periodic FieldBatch + external candidate payload + residual evaluator -> empirical configured validation report`

Important release boundary:

> v0.16 adds one submodule-only validation/reporting helper for externally supplied `GeneratorFamily` and `InvariantMapSpec` candidates. It does not train detectors, accept callables, add formula-backed generators, add new PDEs, promote KS, add weak KS, broaden adapters, add operator APIs, or add root exports.

Contracts and stable behavior belong in:

- `docs/specs/SPEC.md`
- `docs/specs/CONTRACTS_AND_DEFAULTS.md`
- `docs/specs/API_STABILITY.md`
- `docs/planning/ROADMAP.md`
- `docs/planning/V0_16_SCOPE.md`

`API_STABILITY.md` was updated when the public `v0.16` helper landed.

---

## V0.15 Closeout

`v0.15` is complete as materialized uniform translation orbit batches.

Carried-forward guardrails:

- orbit batches construct orbit-expanded data
- orbit batches do not decide train/heldout policy or leakage safety
- serious workflows should keep source and shift indices enabled for auditability

`v0.16` builds on the provenance/reporting direction without adding split policy or augmentation recipes.

---

## Milestone 0 - Scope Freeze

**Status:** COMPLETE

### Goal

Freeze `v0.16` as external symmetry-candidate validation.

### Completed Outcome

- added `docs/planning/V0_16_SCOPE.md`
- reset `PLAN.md` as the active `v0.16` execution record
- updated `ROADMAP.md` to record `v0.16` as the current completed interoperability release
- kept `API_STABILITY.md` unchanged until implementation landed
- recorded explicit non-goals:
  - no callable descriptors
  - no neural detector training
  - no formula-backed generator families
  - no KS promotion
  - no new PDE
  - no broad adapters
  - no operator APIs
  - no root export expansion

---

## Milestone 1 - API Semantics Freeze

**Status:** COMPLETE

### Goal

Freeze the public helper semantics before implementation.

### Completed Outcome

M1 froze:

- public submodule-only helper:
  - `pdelie.symmetry.validate_symmetry_candidate(...)`
- accepted candidate kinds:
  - `GeneratorFamily`
  - canonical `GeneratorFamily` payload mapping
  - `InvariantMapSpec`
  - canonical `InvariantMapSpec` payload mapping
- strict payload policy:
  - ambiguous mappings raise `SchemaValidationError`
  - callable descriptors are rejected
- report schema:
  - `summary_schema_version = "0.1"`
  - `summary_type = "symmetry_candidate_validation"`
  - `candidate_kind`
  - `source_candidate_id`
  - configured validation checks
  - check reports
  - thresholds
  - conclusion
- conclusion labels:
  - `validated`
  - `partially_validated`
  - `failed`
- interpretation:
  - `validated` means empirical configured validation, not a mathematical proof
- thresholds:
  - generator verification requires `classification != "failed"`
  - invariant-map residual stability uses `absolute_delta <= 1e-8 or relative_delta <= 1e-6`
  - inverse consistency uses relative L2 `<= 1e-8`
  - span and closure diagnostics use `1e-8` thresholds

---

## Milestone 2 - GeneratorFamily Candidate Validation

**Status:** COMPLETE

### Goal

Implement validation for `GeneratorFamily` objects and strict payload mappings.

### Completed Outcome

- implemented `pdelie.symmetry.validate_symmetry_candidate(...)`
- accepted canonical `GeneratorFamily` objects and payload mappings
- reused existing:
  - `verify_translation_generator(...)`
  - `compare_generator_spans(...)`
  - `diagnose_generator_family_closure(...)`
  - reporting summaries
- single-row translation-compatible candidates run finite-transform verification
- wrong-span candidates return `conclusion = "failed"` rather than raising
- multi-generator families run closure diagnostics and do not force single-translation verification
- optional `reference_generator` enables span comparison
- documented the new API in `docs/specs/API_STABILITY.md`

---

## Milestone 3 - InvariantMapSpec Candidate Validation

**Status:** COMPLETE

### Goal

Extend the same helper to validate `InvariantMapSpec` objects and strict payload mappings.

### Completed Outcome

- accepted canonical `InvariantMapSpec` objects and payload mappings
- supported only global `uniform_translation` specs over canonical scalar 1D periodic fields
- reused existing `InvariantApplier`
- reported:
  - residual RMS before and after transform
  - absolute and relative residual RMS deltas
  - inverse consistency when `inverse_available` is true
  - preprocess/provenance fields
- rejected unsupported maps with typed validation errors:
  - non-global specs
  - approximate specs
  - non-translation specs
  - missing or nonfinite shifts
  - unsupported axes

---

## Milestone 4 - Example

**Status:** COMPLETE

### Goal

Add a compact JSON-only example for external symmetry-candidate validation.

### Completed Outcome

- added `python -m pdelie.examples.symmetry_candidate_validation`
- added `pdelie.examples.run_symmetry_candidate_validation_example(...)`
- example demonstrates:
  - valid Heat `GeneratorFamily` candidate
  - valid KdV `GeneratorFamily` candidate
  - valid uniform-translation `InvariantMapSpec` payload candidate
  - failed wrong-span generator candidate
- example output remains runtime smoke/reporting, not a canonical artifact schema
- root `pdelie` remains unchanged

---

## Milestone 5 - API / Public-surface Audit

**Status:** COMPLETE

### Goal

Verify public surface and documentation match the frozen `v0.16` scope.

### Completed Outcome

- confirmed `pdelie.symmetry.validate_symmetry_candidate(...)` is submodule-only
- confirmed root `pdelie` exports remain unchanged
- confirmed `API_STABILITY.md` documents only the v0.16 validation helper
- confirmed no callable descriptor API landed
- confirmed no formula-backed generator object landed
- confirmed no neural detector API landed
- confirmed no public KS generator/residual/example APIs landed
- confirmed weak KS remains absent
- confirmed broad adapters, split policy, operator APIs, and root runtime exports remain absent

---

## Milestone 6 - Release Gate and Readiness

**Status:** COMPLETE

### Goal

Close the release with compact gate coverage, metadata, docs, and direct Git-tag readiness.

### Completed Outcome

- added compact `tests/test_v0_16_release_gate.py`
- updated CI so the current explicit release gate is `v0_16-release-gate`
- retained full editable tests and package smoke
- added compact package-smoke coverage for symmetry-candidate validation
- bumped package metadata to `0.16.0`
- updated README and changelog for `v0.16`
- added `docs/releases/V0_16_RELEASE_READINESS.md`
- updated publishing docs to keep `v0.16.0` Git-tag-only
- moved `v0.16` into completed release context in `ROADMAP.md`
- kept PyPI/TestPyPI deferred until `v1.0` or later

### Direct Tag Path

Before tagging `v0.16.0`:

- run full local tests
- build sdist and wheel
- run clean wheel smoke
- run Heat, KdV, orbit/coverage, invariant-workflow, translation-orbit-batch, and symmetry-candidate-validation example modules
- confirm CI checks pass:
  - `v0_16-release-gate`
  - `editable-tests`
  - `package-smoke`
- tag the merged main commit as `v0.16.0`
- do not publish to TestPyPI
- do not publish to PyPI

---

## Explicit Non-goals Preserved

`v0.16` did not add:

- callable transform descriptors
- arbitrary external executable candidate objects
- neural symmetry-detector training
- learned-generator classes
- formula-backed or non-polynomial generator families
- train/test policy
- split management
- heldout-leakage detection
- sparse-discovery branch policy
- private-paper augmentation recipes
- time-translation APIs
- new PDE support
- stable KS runtime support
- weak KS
- broad adapters
- PDEBench or The Well support
- multidimensional, multivariable, or nonuniform-grid expansion
- operator-facing APIs
- root runtime exports

---

## Status Checklist

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE
