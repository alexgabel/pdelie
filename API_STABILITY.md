# API Stability Policy

## Stable API (v0.x)

- FieldBatch
- DerivativeBatch
- `DerivativeBatch.backend="spectral_fd"`
- ResidualEvaluator
- GeneratorFamily (polynomial only)
- basic verification tools
- typed validation errors (`PDELieValidationError`, `SchemaValidationError`, `ShapeValidationError`, `ScopeValidationError`)

These must not change without version bump.

---

## Experimental API

- neural generators
- weak-form methods
- operator symmetry
- advanced invariant maps

These may change without warning.

---

## Internal / Private

- helper utilities
- intermediate representations

No stability guarantees.
