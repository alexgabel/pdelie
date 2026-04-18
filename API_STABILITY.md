# API Stability Policy

## Stable API (v0.x)

- FieldBatch
- DerivativeBatch
- `DerivativeBatch.backend="spectral_fd"`
- ResidualBatch
- ResidualEvaluator
- GeneratorFamily (polynomial only)
- InvariantMapSpec (single-generator only)
- VerificationReport
- basic verification tools
- typed validation errors (`PDELieValidationError`, `SchemaValidationError`, `ShapeValidationError`, `ScopeValidationError`)

Stable public import path for the invariant canonical object:

- `pdelie.InvariantMapSpec`

Runtime public API for the frozen `v0.3` Milestone 1 slice:

- `pdelie.invariants.InvariantApplier` for single-generator periodic `x` uniform translation only

These must not change without version bump.

---

## Experimental API

- neural generators
- weak-form methods
- operator symmetry
- advanced invariant maps
- multi-generator invariant machinery

These may change without warning.

---

## Internal / Private

- helper utilities
- intermediate representations

No stability guarantees.
