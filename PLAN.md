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

Status: DONE

---

### Milestone 2 — Synthetic heat dataset

Implement:

- 1D heat equation generator
- uniform periodic grid

Tests:

- shape correctness
- reproducibility (fixed seed)
- no NaNs

Status: DONE

---

### Milestone 3 — Derivatives

Implement:

- spectral spatial derivative
- finite time derivative

Tests:

- analytic derivative (sin function)
- PDE residual sanity

Status: DONE

---

### Milestone 4 — Residual evaluator

Implement:

- analytic heat residual

Test:

- residual ≈ 0 on clean data

Status: DONE

---

### Milestone 5 — Generator fitting

Implement:

- polynomial generator basis
- simple regression-based fitting

Goal:

- recover spatial translation symmetry

Status: DONE

---

### Milestone 6 — Verification

Implement:

- finite ε transformation
- epsilon sweep
- VerificationReport

Test:

- symmetry holds for small ε
- stable across held-out ICs

Status: DONE

---

## Release Gate

V0.1 is complete if:

- one known heat-equation symmetry is recovered
- held-out validation passes on at least 3 unseen initial conditions
- epsilon sweep is stable
- noise robustness holds for small noise
- all outputs use canonical objects

Current status:

- spatial translation on the synthetic 1D heat equation is recovered
- held-out verification passes on 3 unseen initial conditions
- epsilon sweep is implemented with the default V0.1 settings
- all outputs use the current canonical V0.1 objects

---

## Rules

- DO NOT implement beyond current milestone
- DO NOT add experimental features
- DO NOT expand beyond the documented V0.1 stable scope
- STOP and report ambiguities instead of guessing
