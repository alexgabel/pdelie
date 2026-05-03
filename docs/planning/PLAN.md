# PDELie - Execution Plan (V0.17)

## Current Release Status

**V0.17 is complete as formula-backed generator interoperability**

This file is the completed execution record for the `v0.17` release series.

Committed release theme:

`canonical scalar 1D periodic FieldBatch + formula-backed generator candidate -> safe formula metadata/evaluation diagnostics -> empirical configured validation report`

Important release boundary:

> v0.17 adds runtime-only formula-backed generator records, reporting, and candidate validation. It does not change canonical polynomial `GeneratorFamily` semantics, train learned generators, accept Python callables, parse executable formula strings, add a new PDE, promote KS, add weak KS, broaden adapters, add operator APIs, or add root exports.

Contracts and stable behavior belong in:

- `docs/specs/SPEC.md`
- `docs/specs/CONTRACTS_AND_DEFAULTS.md`
- `docs/specs/API_STABILITY.md`
- `docs/planning/ROADMAP.md`
- `docs/planning/V0_17_SCOPE.md`

`API_STABILITY.md` was updated when the public `v0.17` formula-backed APIs landed.

Milestone status summary:

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

---

## V0.16 Closeout

`v0.16` is complete as external symmetry-candidate validation.

Carried-forward guardrails:

- `validated` means empirical configured validation, not a mathematical proof
- candidate validation is reporting/interop, not detector training
- callable descriptors and learned generators remain out of scope

`v0.17` extends that interop surface to safe formula metadata without opening executable or learned-generator scope.

---

## Milestone 0 - Scope Freeze

**Status:** COMPLETE

### Goal

Freeze `v0.17` as formula-backed generator interoperability.

### Completed Outcome

- added `docs/planning/V0_17_SCOPE.md`
- reset `PLAN.md` as the active `v0.17` execution record
- updated `ROADMAP.md` to record `v0.17` as the current completed release
- kept `API_STABILITY.md` unchanged until implementation landed
- recorded explicit non-goals:
  - no callable generator API
  - no arbitrary formula-string evaluator
  - no neural detector or learned-generator training
  - no canonical `GeneratorFamily` semantic change
  - no KS promotion
  - no new PDE
  - no weak KS
  - no broad adapters
  - no operator APIs
  - no root export expansion

---

## Milestone 1 - Formula Schema and Validation Semantics Freeze

**Status:** COMPLETE

### Goal

Freeze the formula record, expression policy, and candidate-validation semantics before implementation.

### Completed Outcome

M1 froze:

- runtime-only public record:
  - `pdelie.symmetry.FormulaGeneratorFamily`
- runtime reporting helper:
  - `pdelie.reporting.summarize_formula_generator_family(...)`
- candidate-validation extension:
  - `pdelie.symmetry.validate_symmetry_candidate(...)` accepts formula objects and strict current formula payloads
- report discriminator:
  - `candidate_kind = "formula_generator_family"`
- supported formula components:
  - `tau`
  - `xi`
  - `phi`
- supported variables:
  - `t`
  - `x`
  - `u`
- safe JSON expression AST nodes:
  - `const`
  - `var`
  - `add`
  - `mul`
  - integer `pow`
  - `sin`
  - `cos`
  - `reciprocal`
  - metadata-only `symbolic_reference`
- formula validation interpretation:
  - malformed formulas raise typed validation errors
  - finite formula-evaluation failures return `conclusion = "failed"`
  - symbolic-reference-only formulas remain reporting/schema results and do not pretend to evaluate
  - formulas without finite transforms may be only partially validated
  - formulas with supported passing finite-transform checks may be validated

---

## Milestone 2 - Formula Record and Reporting Implementation

**Status:** COMPLETE

### Goal

Implement the runtime-only formula record and reporting helper.

### Completed Outcome

- implemented `pdelie.symmetry.FormulaGeneratorFamily`
- implemented strict `.to_dict()` / `.from_dict()` JSON payload round trips
- implemented safe expression normalization for the frozen AST
- rejected invalid variables, components, expression nodes, nonfinite constants, arbitrary strings, and callables with typed validation errors
- supported symbolic references as metadata-only expressions
- supported optional `finite_transform_spec` as a canonical `InvariantMapSpec` payload
- implemented `pdelie.reporting.summarize_formula_generator_family(...)`
- documented the new APIs in `docs/specs/API_STABILITY.md`

---

## Milestone 3 - Formula Candidate Validation

**Status:** COMPLETE

### Goal

Extend empirical configured candidate validation to formula-backed generator families.

### Completed Outcome

- extended `validate_symmetry_candidate(...)` for:
  - `FormulaGeneratorFamily` objects
  - strict current formula payload mappings
- added `candidate_kind = "formula_generator_family"`
- added formula-evaluation diagnostics over canonical scalar 1D periodic `FieldBatch` inputs
- reported component-level value shapes, max absolute values, RMS values, symbolic-reference unavailability, and denominator-floor failures
- kept denominator-floor violations as failed empirical reports, not untyped exceptions
- reused the existing invariant-map residual and inverse validation path when a supported finite-transform spec is attached
- preserved existing `GeneratorFamily` and `InvariantMapSpec` validation behavior

---

## Milestone 4 - Example

**Status:** COMPLETE

### Goal

Add a compact JSON-only example for formula-backed candidate validation.

### Completed Outcome

- added `python -m pdelie.examples.formula_generator_validation`
- added `pdelie.examples.run_formula_generator_validation_example(...)`
- example demonstrates:
  - affine formula candidate
  - trigonometric formula candidate
  - rational formula candidate with finite diagnostics
  - formula candidate with supported uniform-translation finite transform
  - failed nonfinite formula candidate for contrast
- example output remains runtime smoke/reporting, not a canonical artifact schema
- root `pdelie` remains unchanged

---

## Milestone 5 - API / Public-surface Audit

**Status:** COMPLETE

### Goal

Verify public surface and documentation match the frozen `v0.17` scope.

### Completed Outcome

- confirmed `pdelie.symmetry.FormulaGeneratorFamily` is submodule-only
- confirmed `pdelie.reporting.summarize_formula_generator_family(...)` is submodule-only
- confirmed `validate_symmetry_candidate(...)` documents and reports formula candidates
- confirmed root `pdelie` exports remain unchanged
- confirmed no callable generator API landed
- confirmed no arbitrary executable formula-string path landed
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

- added compact `tests/test_v0_17_release_gate.py`
- updated CI so the current explicit release gate is `v0_17-release-gate`
- kept full editable tests and package smoke
- bumped package metadata to `0.17.0`
- updated README, changelog, release readiness, publishing docs, roadmap, and plan
- documented direct `v0.17.0` Git-tag release path
- kept PyPI/TestPyPI publishing deferred until `v1.0` or later

---

## Final Validation Checklist

Required before tagging:

- `python -m pytest`
- `python -m build --sdist --wheel`
- clean wheel smoke from `dist/pdelie-0.17.0-py3-none-any.whl`
- `python -m pdelie.examples.heat_vertical_slice`
- `python -m pdelie.examples.kdv_vertical_slice`
- `python -m pdelie.examples.orbit_coverage_diagnostics`
- `python -m pdelie.examples.invariant_workflow_summary`
- `python -m pdelie.examples.translation_orbit_batch`
- `python -m pdelie.examples.symmetry_candidate_validation`
- `python -m pdelie.examples.formula_generator_validation`
- `git diff --check`

Required CI checks before tagging:

- `v0_17-release-gate`
- `editable-tests`
- `package-smoke`
