# v0.37c — Confirmatory Freeze

**Status: SIGNED.**

Signed only because PS-1, PS-2 and PS-3 all passed on pilot run 3. Two earlier
pilot runs blocked; both are retained in
[`v0_37c_pilot_report.md`](v0_37c_pilot_report.md).

**v0.37d opens.**

---

## 1. Scope

Five cases on the amended registry. C-4 was retired at pilot 2 and is not
reinstated here; the reason is recorded in §2 of
[`v0_37c_hypothesis_freeze.md`](v0_37c_hypothesis_freeze.md).

| | |
|---|---|
| Cases | C-1, C-2, C-3, C-5, C-6 |
| Profiles | `constant`, `sinusoidal`, `localized_bump`, `higher_frequency` |
| Confirmatory α grid | `0.025, 0.075, 0.15, 0.3, 0.6` |
| Seeds | `2, 3, 5, 7, 11` |
| Measurements | 125 = 5 cases × 5 α × 5 seeds |
| Norm | `‖·‖∞`, reported as `absolute_error_linf` |

**The confirmatory grid was disjoint from every grid measured before this run.**
Reconnaissance and all three pilots used `{0.0, 0.05, 0.1, 0.2, 0.4, 0.8}`. The
numbers below are the first measurements ever taken at these α.

---

## 2. Confirmatory measurements

Worst over seeds.

| alpha | `C-1` | `C-2` | `C-3` | `C-5` | `C-6` |
|---|---|---|---|---|---|
| `0.025` | `1.1990e-14` | `1.1546e-14` | `2.4463e-02` | `3.9902e-01` | `5.6995e-03` |
| `0.075` | `1.1990e-14` | `1.2101e-14` | `7.3390e-02` | `3.9902e-01` | `1.7098e-02` |
| `0.15` | `1.1990e-14` | `1.2212e-14` | `1.4678e-01` | `3.9902e-01` | `3.4197e-02` |
| `0.3` | `1.1990e-14` | `1.1990e-14` | `2.9356e-01` | `3.9902e-01` | `6.8394e-02` |
| `0.6` | `1.1990e-14` | `1.3323e-14` | `5.8712e-01` | `3.9902e-01` | `1.3679e-01` |

Separation holds at every unlooked-at point:

| alpha | `0.025` | `0.075` | `0.15` | `0.3` | `0.6` |
|---|---|---|---|---|---|
| margin | `1.041e+11` | `3.093e+11` | `6.130e+11` | `1.249e+12` | `2.248e+12` |

C-5 is α-independent at `3.9902e-01`, as expected: it uses the `constant`
profile and its obstruction is the nonlinearity.

---

## 3. Frozen tolerances

### How these were chosen, and why that is not tuning

PS-1 established that a separating threshold **exists** with a margin of
`1.04e+11` at worst. That means the admissible interval for a decision boundary
is enormous, and **any** value inside it produces the same classification on
every case, every seed, every α.

So the frozen values are stated as **an interval with traceable endpoints, plus
a chosen point inside it**. The endpoints are the quantities PS-2 requires to
trace:

- the **lower** endpoint is the measured spectral floor of the valid cases —
  §6's named reference, "that floor, measured on the same grid, not a fitted
  number";
- the **upper** endpoint is the smallest obstruction magnitude, which traces to
  the §6 analytical bound for its case.

The point chosen inside is a round number. It is inconsequential by
construction: PS-1's margin means no case's classification is sensitive to it.
Had the interval been narrow, this reasoning would not be available and the
freeze could not have been signed.

### Decision boundary

| | value | traces to |
|---|---|---|
| Lower endpoint | `1.3323e-14` | measured spectral floor, worst valid case over all seeds and α |
| **Frozen boundary `T`** | **`1.0e-06`** | chosen inside the interval |
| Upper endpoint | `1.2476e-03` | smallest obstruction magnitude (C-6 at `α = 0.025`), which traces to its §6 bound |

`T` sits `7.5e+07`× above the floor and `1.2e+03`× below the smallest
obstruction.

### Per-case tolerances

**Valid cases — ceiling. The error must stay below.**

| case | ceiling | worst observed | margin | reference |
|---|---|---|---|---|
| C-1 | `1.0e-06` | `1.1990e-14` | `8.3e+07`× | exact permutation; §6 floor |
| C-2 | `1.0e-06` | `1.3323e-14` | `7.5e+07`× | exact permutation, both sides; §6 floor |

**Obstruction cases — floor. The error must stay above.**

| case | floor | smallest observed | margin | reference |
|---|---|---|---|---|
| C-3 | `1.0e-06` | `1.3167e-02` | `1.3e+04`× | §6 bound, `a₀·α·(‖Δf‖∞‖u_xx‖∞ + ‖Δf'‖∞‖u_x‖∞)` |
| C-5 | `1.0e-06` | `6.1899e-02` | `6.2e+04`× | §6 identity, `\|c²−c\|·‖u·u_x‖∞` |
| C-6 | `1.0e-06` | `1.2476e-03` | `1.2e+03`× | §6 bound, as C-3 |

A single value serves as both ceiling and floor because the two populations are
eleven orders apart. Splitting them would imply a precision the measurement does
not have.

---

## 4. Expected status per case

Frozen. A v0.37d run that reports anything else is a regression.

| case | `expected_case` | `observed_relation_status` | `benchmark_outcome` |
|---|---|---|---|
| C-1 | `valid_relation` | `confirmed` | `expected_result_observed` |
| C-2 | `valid_relation` | `confirmed` | `expected_result_observed` |
| C-3 | `deliberate_obstruction` | `violated` | `expected_result_observed` |
| C-5 | `deliberate_obstruction` | `violated` | `expected_result_observed` |
| C-6 | `deliberate_obstruction` | `violated` | `expected_result_observed` |

Every case's `benchmark_outcome` is `expected_result_observed`. Three of the
five *failed*, and that is the result the benchmark wanted — the distinction the
three-field split exists to express.

---

## 5. Seed invariance

Observed spread across the five seeds, on the confirmatory grid:

| case | min | max | ratio |
|---|---|---|---|
| C-1 / C-2 | `1.1546e-14` | `1.3323e-14` | `1.15`× |
| C-3 | `1.3167e-02` | `5.8712e-01` | `44.6`× |
| C-5 | `6.1899e-02` | `3.9902e-01` | `6.4`× |
| C-6 | `1.2476e-03` | `1.3679e-01` | `110`× |

The obstruction spreads are wide because they scale with `‖u_xx‖∞`, which varies
with the random initial condition, **and across the α grid**. Both remain many
orders from the boundary, so seed choice does not affect any classification.

---

## 6. What this freeze does not establish

- **Nothing about monotone coefficients.** C-4 was retired; that axis is absent
  until a nonperiodic action family exists.
- **Nothing about nonperiodic domains.** All five cases are
  `periodic_uniform`, and `execute_state_action` now refuses anything else.
- **Nothing about `linear_combination_of_derivatives`.** No case selects it, so
  v0.37b's decision not to synthesise it is untested here and remains open.
- **Nothing measured on Linux.** Every number here was produced on
  macOS/arm64. The margins are eleven orders, so a cross-platform difference
  cannot plausibly change a classification — but that is an argument, not a
  measurement, and it should be recorded as such before any of these values is
  cited outside this repository.

---

## 7. Signature

PS-1 **PASS** · PS-2 **PASS** · PS-3 **PASS** — pilot run 3, five-case registry.

Signed 2026-08-01. **v0.37d opens.**
