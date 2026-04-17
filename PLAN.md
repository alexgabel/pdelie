# PDELie — Execution Plan (V0.2 Milestone 2)

## Goal

Harden the current stable Heat and Burgers symmetry pipeline with a controlled internal benchmark / release-gate layer under matched settings.

---

## Frozen Decisions

- no new canonical stable objects
- no new public API
- benchmark logic stays in the test layer
- reuse `spectral_fd`, current translation fitting, and current verification defaults
- fixed low additive Gaussian noise (`noise_std_fraction = 2e-4`) applies to held-out data only

---

## Milestone 2

Implement:

- internal cross-PDE benchmark helper for Heat and Burgers
- matched clean benchmark checks across both PDEs
- matched noisy held-out benchmark checks across both PDEs
- explicit release-gate tests for config reuse and reproducibility

Status: DONE

Implemented:

- test-only benchmark helper with one frozen benchmark config shared by Heat and Burgers
- clean cross-PDE benchmark gate (`exact` on Heat and Burgers)
- noisy held-out cross-PDE benchmark gate (`exact` or `approximate` on Heat and Burgers)
- reproducibility and config-drift protection around the matched benchmark layer

---

## Milestone 2 Gate

Milestone 2 is complete only if:

- Heat still verifies as `exact`
- Burgers verifies as `exact`
- clean matched benchmark checks are `exact` for both PDEs
- noisy held-out matched benchmark checks are `exact` or `approximate` for both PDEs
- both PDEs use the same fixed verification defaults and fixed noise condition
- no invariant, weak-form, operator, or adapter work is required

Current status:

- Heat still passes the existing vertical slice
- Burgers still passes the same stable translation pipeline
- the matched benchmark / release-gate layer now checks both PDEs under shared settings

---

## Rules

- DO NOT add invariants in this milestone
- DO NOT add weak-form methods
- DO NOT add operator methods
- DO NOT broaden adapters or ecosystem scope
- DO NOT add new canonical stable objects unless forced by a later milestone
