# v0.38e — Pilot Report

**Append-only.** Blocked runs are retained unedited. A report showing only the
passing run is a selection-effect document.

Pre-registered in [`v0_38e_hypothesis_freeze.md`](v0_38e_hypothesis_freeze.md)
§3, including the artifact location, the block criteria B-1…B-6, and
`blocked_pilot_criteria_not_met` as a first-class outcome.

Platform for every run below: `Darwin/arm64`, CPython 3.12, NumPy 2.5.1.
Pilot grid: α ∈ {0.0, 0.05, 0.1, 0.2, 0.4, 0.8}, seeds {13, 17, 19}, 126
measurements across 7 cases.

---

## Run 1 — **BLOCKED** on B-1

**Outcome:** `blocked_pilot_criteria_not_met`.

### What blocked

B-1: *"Any status × diagnosis pair declared reachable in §2.3 that no
constructed case produces."*

`LEGAL_STATUS_DIAGNOSIS_PAIRS` declares five pairs. Four are produced:

| Pair | Produced by |
|---|---|
| `not_applicable` / `declaration_and_execution_agree` | C-1, C-2, C-3, C-6 |
| `consistent` / `declaration_and_execution_agree` | C-5, C-7 |
| `indeterminate` / `target_ambiguous` | C-8 |
| `inconsistent` / `declared_not_executed` | unit test (a parameter action on a problem with no numeric parameter) |

The fifth, **`inconsistent` / `executed_not_declared`, is produced by nothing.**

### Why this is a specification defect and not a missing test

The pair sits in a table named `LEGAL_STATUS_DIAGNOSIS_PAIRS`, which reads as a
claim that it can occur. It cannot: `summarize_coaction_consistency` has five
branches and none of them assigns it, and the executor now refuses the
divergence it would describe.

So the table contains an entry that *looks* load-bearing and is not — the same
class as the subsumed forbidden term caught at v0.38 day-zero, and the same
class as a guard that can only pass. Anyone reading the vocabulary would
conclude the report distinguishes a case it has never distinguished.

### Why the entry is not simply deleted

`executed_not_declared` names the **pre-v0.38e behaviour exactly**: the executor
applied a rescale to `advection_speed` that no declaration mentioned. If a
future executor path reintroduces that divergence, the report must have a name
for it. Deleting the vocabulary would leave a future defect unnameable.

### Resolution (amendment A-1)

Additive, and it converts an unchecked claim into a checked one:

1. `RESERVED_UNREACHABLE_PAIRS` names the pair explicitly, with its reason.
2. A test proves the unreachability by parsing the summariser's branches with
   `ast` and asserting the set of pairs it can literally emit equals
   `LEGAL_STATUS_DIAGNOSIS_PAIRS - RESERVED_UNREACHABLE_PAIRS`. If a future
   branch emits the reserved pair, the test fails and the reservation must be
   lifted deliberately.
3. B-1 is read against reachable pairs, with the reserved set excluded *by
   name* rather than by silence.

Nothing about the measured numbers changes; no threshold moves.

### Measurements retained from run 1

Unchanged by the amendment — the block was in the specification, not the data.
The C-7/C-8 rows are reproduced in run 2 below and are bit-identical.

---

## Run 2 — passed

**Outcome:** all criteria met, after amendment A-1.

### B-1 — reachable pairs

| Pair | Produced |
|---|---|
| `not_applicable` / `declaration_and_execution_agree` | yes |
| `consistent` / `declaration_and_execution_agree` | yes |
| `indeterminate` / `target_ambiguous` | yes |
| `inconsistent` / `declared_not_executed` | yes |
| `inconsistent` / `executed_not_declared` | **reserved**, proven unreachable |

### B-2 — C-8 blocked everywhere

18 rows (6 α × 3 seeds). Every one reports
`indeterminate` / `target_ambiguous`, outcome
`blocked_ambiguous_parameter_target`. No row carries a residual.

### B-3 — C-7's second parameter untouched

18 rows. `advection_speed` reads `2.0` in every one; `nu_baseline` reads `0.2`,
the declared `0.1 × 2.0`. Zero rows show a moved `advection_speed`.

This is the assertion that would have caught the original defect. Before
v0.38e the same declaration produced `advection_speed = 4.0`.

### B-4 — scientific identity never decided without a declared metric

No call site passes a defaulted metric; `scientific_identity` has no default to
pass. Asserted structurally by signature inspection, not by absence of failure.

### B-5 — schema

16 keys, matching the frozen list in order.

### B-6 — norms

Every row carries `absolute_error_l2` **and** `absolute_error_linf` as separate
named keys. No number is reported under an unqualified "error".

### C-7 measured magnitudes (α sweep, seed 13)

| α | `absolute_error_l2` |
|---:|---:|
| 0.0 | 1.1123e+00 |
| 0.05 | 1.1235e+00 |
| 0.1 | 1.1369e+00 |
| 0.2 | 1.1703e+00 |
| 0.4 | 1.2600e+00 |
| 0.8 | 1.5100e+00 |

C-1's control floor over the same grid is `9.283e-14`, flat. C-7's minimum sits
**thirteen orders above it**, so the confirming case is not at the floor.

### Separation across all seven cases (seed 13)

| case | α=0 | α=0.8 | behaviour |
|---|---:|---:|---|
| C-1 | 9.283e-14 | 9.283e-14 | flat control |
| C-2 | 9.283e-14 | 1.053e-13 | stays at floor — valid equivalence |
| C-3 | 9.283e-14 | 1.391e+01 | grows — fixed-background obstruction |
| C-5 | 2.440e+00 | 2.440e+00 | flat, off floor — parameter without state |
| C-6 | 9.146e-15 | 1.041e+00 | grows — localized coefficient |
| C-7 | 1.1123e+00 | 1.5100e+00 | off floor — named target |
| C-8 | blocked | blocked | refused before execution |

---

## Regression check against the released v0.37c numbers

The `equation_form` correction (see the confirmatory freeze §2) changes a
declaration and a bundle identity hash. It must change no measured number.

All **125** v0.37c-case confirmatory measurements (C-1, C-2, C-3, C-5, C-6 × 5 α
× 5 seeds) were recomputed on this branch and compared against `main`:

```
bitwise identical : 125/125
worst relative gap: 0.000e+00
```

Not "agree to tolerance" — **bitwise identical**.

---

## Corrections made during the pilot

**The form-difference figure was wrong, and the test that produced it was
wrong in a familiar way.** An early note recorded the two equation forms as
differing by 13.8% in relative L2 on C-3's profile. That number came from
differencing a **spectral** `u_xx` against `np.gradient(nu * u_x)`, which
measures the gap between two discretizations, not the gap between two forms. On
a *constant* coefficient — where the forms are provably identical — the same
method reported `1.9e+03`.

The forms differ by exactly `nu' · u_x`, analytically. Recomputed that way:

| profile | max&nbsp;\|nu'\| | ‖nu'·u_x‖ / ‖residual‖ |
|---|---:|---:|
| `constant` | 0.000e+00 | **0.0000** (exactly) |
| `sinusoidal` | 9.745e-02 | **1.0353** |

So the difference does not merely perturb the operator on a variable
coefficient — it exceeds the residual itself. The earlier figure understated it
by roughly an order of magnitude.

This is the v0.37c §6 error repeating: a quantity obtained by subtracting two
numbers instead of by deriving the term. It was caught by the constant-profile
test, which had a right answer known in advance (zero) rather than one taken
from the measurement.
