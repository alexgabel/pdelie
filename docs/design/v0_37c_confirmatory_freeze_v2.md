# v0.37c — Confirmatory Freeze (v2)

**Status: SIGNED.**

Supersedes [`v0_37c_confirmatory_freeze.md`](v0_37c_confirmatory_freeze.md) (v1),
which **remains unedited** and is invalidated for C-5 only. See
[`V0_37_C5_ERRATUM.md`](../releases/V0_37_C5_ERRATUM.md).

---

## 1. Why a v2 exists

v1 signed a C-5 result produced by a runner that rescaled the **state** while its
bundle declared a rescale of the **parameter**. The arithmetic was correct for
what it computed; it computed the wrong transformation. v1's C-5 tolerance
therefore describes a measurement nobody asked for.

**All five cases were rerun, not just C-5.** A confirmatory freeze is a paired
comparison across a case set at a fixed seed packet; substituting one case's
numbers from a different run would make the margins incomparable.

## 2. Fresh seed packet

| | v1 | **v2** |
|---|---|---|
| Seeds | `2, 3, 5, 7, 11` | **`13, 17, 19, 23, 29`** |

Disjoint from v1 on purpose. Reusing v1's seeds would make v2 a re-presentation
of the same draws rather than an independent confirmation, and the repaired C-5
has never been measured on any of these.

The α grids are unchanged and remain disjoint between pilot and confirmatory.

## 3. Confirmatory measurements

`‖·‖∞`, worst over seeds. 125 measurements = 5 cases × 5 α × 5 seeds.

| alpha | `C-1` | `C-2` | `C-3` | `C-5` | `C-6` |
|---|---|---|---|---|---|
| `0.025` | `1.3101e-14` | `1.3295e-14` | `3.0102e-02` | `1.6286e-01` | `5.5542e-03` |
| `0.075` | `1.3101e-14` | `1.3212e-14` | `9.0307e-02` | `1.6286e-01` | `1.6663e-02` |
| `0.15` | `1.3101e-14` | `1.2934e-14` | `1.8061e-01` | `1.6286e-01` | `3.3325e-02` |
| `0.3` | `1.3101e-14` | `1.3239e-14` | `3.6123e-01` | `1.6286e-01` | `6.6651e-02` |
| `0.6` | `1.3101e-14` | `1.2990e-14` | `7.2245e-01` | `1.6286e-01` | `1.3330e-01` |

Separation at every point:

| alpha | `0.025` | `0.075` | `0.15` | `0.3` | `0.6` |
|---|---|---|---|---|---|
| margin | `2.312e+11` | `6.981e+11` | `1.408e+12` | `1.587e+12` | `1.604e+12` |

C-5 remains α-independent, at a **new value** (`1.6286e-01`, was `3.9902e-01`)
because it now measures a different transformation.

## 4. PS criteria, evaluated de novo

**PS-1 — PASS.** A single threshold separates valid from invalid at every α > 0
across all five seeds. Binding margin **`2.312e+11`**. At α = 0 the
profile-dependent obstruction cases are bit-identical to C-1 (`1.3101e-14`).

**PS-2 — PASS.** Every tolerance traces to a §6 derivation, and C-5's is now
the derivation for the transformation actually performed:

| case | reference | agreement |
|---|---|---|
| C-1, C-2 | spectral floor, measured on the same grid | floor-limited, `1.3711e-14` worst |
| C-3, C-6 | `a₀·α·(‖Δf‖∞‖u_xx‖∞ + ‖Δf'‖∞‖u_x‖∞)` | bounds on every seed and α |
| **C-5** | **`\|c−1\|·ν·‖u_xx‖∞`** | **exact, ratio `1.000000` on every seed** |

**PS-3 — PASS.** Grids disjoint; and the seed packet is disjoint from v1's.

## 5. Frozen tolerances

Same construction as v1 — an interval with traceable endpoints plus a chosen
point inside, inconsequential because the margin is eleven orders.

| | value | traces to |
|---|---|---|
| Lower endpoint | `1.3711e-14` | measured spectral floor, worst valid case |
| **Frozen boundary `T`** | **`1.0e-06`** | chosen inside the interval |
| Upper endpoint | `1.4595e-03` | smallest obstruction (C-6 at `α = 0.025`, worst seed) |

Unchanged from v1 at `1.0e-06`. That it did not move is a result, not an
assumption: the interval shifted and the chosen point remains comfortably inside
it.

## 6. Expected status per case

| case | `expected_case` | `observed_relation_status` | `benchmark_outcome` |
|---|---|---|---|
| C-1 | `valid_relation` | `confirmed` | `expected_result_observed` |
| C-2 | `valid_relation` | `confirmed` | `expected_result_observed` |
| C-3 | `deliberate_obstruction` | `violated` | `expected_result_observed` |
| C-5 | `deliberate_obstruction` | `violated` | `expected_result_observed` |
| C-6 | `deliberate_obstruction` | `violated` | `expected_result_observed` |

## 7. What this freeze does not establish

Unchanged from v1, plus one addition:

- Nothing about monotone coefficients, nonperiodic domains, or
  `linear_combination_of_derivatives`.
- **Nothing about `scalar_multiplier` end to end.** C-5 declared that family
  until v0.37.1; with the semantics repaired no case exercises it, and the
  coverage loss is recorded rather than hidden.
- Nothing measured on Linux. The replay is Phase 2 and uses this seed packet.

## 8. Signature

PS-1 **PASS** · PS-2 **PASS** · PS-3 **PASS** — five cases, seeds `13, 17, 19,
23, 29`, repaired C-5 semantics.

Signed 2026-08-02.
