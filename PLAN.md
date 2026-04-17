# PDELie — Execution Plan (V0.2 Milestone 1)

## Goal

Add synthetic 1D Burgers as the second stable PDE under the existing pipeline:

FieldBatch → DerivativeBatch → ResidualBatch → GeneratorFamily → VerificationReport

while preserving the current Heat path with no regressions.

---

## Frozen Decisions

- Burgers form: viscous 1D Burgers with fixed `nu`
- grid: uniform periodic 1D grid
- first stable Burgers target: spatial translation
- derivative backend: keep `spectral_fd`
- stable canonical object set: unchanged from V0.1

---

## Milestone 1

Implement:

- synthetic 1D Burgers generator
- analytic Burgers residual evaluator
- minimal broadening of the current translation fitter / verifier to support Burgers
- cross-PDE tests that keep Heat exact and make Burgers exact under the same stable path

Status: DONE

Implemented:

- `generate_burgers_1d_field_batch(...)`
- `BurgersResidualEvaluator`
- translation-basis scope checks generalized from Heat-only wording to stable 1D periodic scalar inputs
- translation fitter fallback that preserves the spatial-translation target on Burgers without changing the public symmetry API
- Burgers unit tests, verification tests, and cross-PDE vertical-slice coverage

---

## Milestone 1 Gate

Milestone 1 is complete only if:

- Heat still verifies as `exact`
- Burgers verifies as `exact`
- both PDEs use the existing stable pipeline and contracts
- no invariant, weak-form, operator, or adapter work is required

Current status:

- Heat still passes the existing vertical slice
- Burgers now passes the same stable translation pipeline
- cross-PDE tests protect the Heat result and validate the Burgers result

---

## Rules

- DO NOT add invariants in this milestone
- DO NOT add weak-form methods
- DO NOT add operator methods
- DO NOT broaden adapters or ecosystem scope
- DO NOT add new canonical stable objects unless forced by a later milestone
