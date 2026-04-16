# PDELie — Execution Plan (V0.1)

## Goal

Prove the vertical slice:

FieldBatch → DerivativeBatch → Residual → Generator → Verification

on the 1D heat equation.

---

## Milestones

### Milestone 1 — Canonical objects

Implement:

- FieldBatch
- DerivativeBatch
- ResidualBatch
- GeneratorFamily
- VerificationReport

Requirements:

- validation rules
- to_dict / from_dict
- tests:
  - schema validation
  - shape validation
  - round-trip serialization

Status: TODO

---

### Milestone 2 — Synthetic heat dataset

Implement:

- 1D heat equation generator
- uniform periodic grid

Tests:

- shape correctness
- reproducibility (fixed seed)
- no NaNs

Status: TODO

---

### Milestone 3 — Derivatives

Implement:

- spectral spatial derivative
- finite time derivative

Tests:

- analytic derivative (sin function)
- PDE residual sanity

Status: TODO

---

### Milestone 4 — Residual evaluator

Implement:

- analytic heat residual

Test:

- residual ≈ 0 on clean data

Status: TODO

---

### Milestone 5 — Generator fitting

Implement:

- polynomial generator basis
- simple regression-based fitting

Goal:

- recover spatial translation symmetry

Status: TODO

---

### Milestone 6 — Verification

Implement:

- finite ε transformation
- epsilon sweep
- VerificationReport

Test:

- symmetry holds for small ε
- stable across held-out ICs

Status: TODO

---

## Release Gate

V0.1 is complete if:

- one known heat-equation symmetry is recovered
- held-out validation passes
- epsilon sweep is stable
- noise robustness holds for small noise
- all outputs use canonical objects

---

## Rules

- DO NOT implement beyond current milestone
- DO NOT add experimental features
- DO NOT modify SPEC.md during implementation
- STOP and report ambiguities instead of guessing