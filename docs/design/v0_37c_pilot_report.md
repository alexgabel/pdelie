# v0.37c — Pilot Report

**Status: `blocked_pilot_criteria_not_met`.**

**Blocking criterion: PS-2 (traceable tolerances).**

**Consequence: the confirmatory freeze is not signed, and v0.37d does not open.**

Governed by [`v0_37c_hypothesis_freeze.md`](v0_37c_hypothesis_freeze.md), which
pre-registered this status and required the block reason to name the specific
criterion violated.

---

## 1. What was run

| | |
|---|---|
| Phase | `pilot` |
| α grid | `0.0, 0.05, 0.1, 0.2, 0.4, 0.8` (frozen) |
| Seeds | `7, 11, 13, 17, 19` — **all five retained, none dropped** |
| Grid | 32 × 32, translation of 3 whole cells |
| Measurements | 180 = 6 cases × 6 α × 5 seeds |
| Machinery | the shipped path: `ProblemActionBundle` → `execute_bundle` → `build_residual_commutation_report` |

The runner computes nothing itself. It reads `absolute_error` out of a real
commutation report, so what the pilot measures is what ships. No threshold was
applied at any point — the pilot reports magnitudes, and a verdict would have
required a tolerance that does not yet exist.

Runtime paths observed: C-1/C-3/C-4/C-6 → `P-1`, C-2 → `P-3`, C-5 → `P-5`. Each
case exercised the path its declaration implies.

---

## 2. Measurements

Worst over all five seeds, `absolute_error` as the report emits it.

| alpha | `C-1` | `C-2` | `C-3` | `C-4` | `C-5` | `C-6` |
|---|---|---|---|---|---|---|
| `0.0` | `9.2834e-14` | `9.2834e-14` | `9.2834e-14` | `9.2834e-14` | `2.3224e+00` | `9.1462e-15` |
| `0.05` | `9.2834e-14` | `9.3536e-14` | `8.6906e-01` | `1.0155e+00` | `2.3224e+00` | `9.0213e-02` |
| `0.1` | `9.2834e-14` | `9.4348e-14` | `1.7381e+00` | `2.0311e+00` | `2.3224e+00` | `1.8043e-01` |
| `0.2` | `9.2834e-14` | `9.4413e-14` | `3.4763e+00` | `4.0621e+00` | `2.3224e+00` | `3.6085e-01` |
| `0.4` | `9.2834e-14` | `9.6665e-14` | `6.9525e+00` | `8.1242e+00` | `2.3224e+00` | `7.2171e-01` |
| `0.8` | `9.2834e-14` | `1.0532e-13` | `1.3905e+01` | `1.6248e+01` | `2.3224e+00` | `1.4434e+00` |

Per-seed at `α = 0.05`, so the spread is auditable rather than hidden behind a
maximum:

| seed | `C-1` | `C-2` | `C-3` | `C-4` | `C-5` | `C-6` |
|---|---|---|---|---|---|---|
| `7` | `3.5146e-14` | `3.4813e-14` | `3.3829e-01` | `7.2508e-01` | `2.7761e-01` | `5.8426e-02` |
| `11` | `3.1740e-14` | `3.2574e-14` | `4.6486e-01` | `6.8839e-01` | `4.2290e-01` | `9.0213e-02` |
| `13` | `9.2834e-14` | `9.3536e-14` | `8.6906e-01` | `6.6976e-01` | `2.3224e+00` | `6.5069e-02` |
| `17` | `8.0339e-14` | `8.0608e-14` | `5.6027e-01` | `1.0155e+00` | `1.1914e+00` | `4.7663e-02` |
| `19` | `3.6609e-14` | `3.6683e-14` | `4.8884e-01` | `5.3504e-01` | `4.8720e-01` | `7.9030e-02` |

Seed spread is 1.9× to 8.4× across cases. C-5 is widest, as its magnitude
depends on the field amplitude through the nonlinear term.

**C-5 does not vary with α**, at `2.3224e+00` across the whole grid. That is
correct and not a defect: C-5 uses the `constant` profile, so α has no effect on
it. Its obstruction is the nonlinearity, not the coefficient variation.

---

## 3. PS-1 — Decision margin: **PASS**

| alpha | max valid | min invalid | margin | separable |
|---|---|---|---|---|
| `0.0` | `9.2834e-14` | `4.9583e-15` | `5.341e-02` | no — **this is the control** |
| `0.05` | `9.3536e-14` | `4.7663e-02` | `5.096e+11` | **yes** |
| `0.1` | `9.4348e-14` | `9.5327e-02` | `1.010e+12` | **yes** |
| `0.2` | `9.4413e-14` | `1.9065e-01` | `2.019e+12` | **yes** |
| `0.4` | `9.6665e-14` | `2.7761e-01` | `2.872e+12` | **yes** |
| `0.8` | `1.0532e-13` | `2.7761e-01` | `2.636e+12` | **yes** |

A single threshold separates valid from invalid at **every α > 0**, over all
five seeds simultaneously. The binding margin is `5.096e+11` at `α = 0.05`.

**The control passes in the strongest available form.** At `α = 0`, C-3 and C-4
are not merely close to C-1 — they are **bit-identical to it on every seed**
(`3.173960e-14`, `3.514587e-14`, `3.660913e-14`, `8.033880e-14`, `9.283399e-14`
for all three cases). At zero dose they are the same problem, and the pipeline
reports them as the same problem.

C-6 has no same-equation valid partner, so its control is that its `α = 0` value
(`9.1462e-15`) sits at floor, 13 orders below its `α = 0.05` value
(`9.0213e-02`).

**Dose-response is exactly linear.** `error/α` is constant to seven significant
figures for every α on the grid: C-3 `1.738126e+01`, C-4 `2.031053e+01`, C-6
`1.804269e+00`. This is the analytical form the freeze predicted, confirmed.

---

## 4. PS-2 — Traceable tolerances: **FAIL**

This is the blocking criterion.

### The finding

The freeze's derivations are stated in **‖·‖∞**. The shipped report's
`absolute_error` is **‖·‖₂**, unnormalised over the whole array. They are
different quantities, so no tolerance derived from those bounds traces to what
is measured.

Verified directly on C-5, seed 7:

| Quantity | Value |
|---|---|
| `‖R(cu) − c·R(u)‖∞` — what the freeze's bound is in | `2.321210e-02` |
| `‖R(cu) − c·R(u)‖₂` — what the report emits | `2.776114e-01` |
| What the pilot recorded | `2.776114e-01` |
| Ratio | `11.9598` |

The same mismatch inflates every case, so the bounds under-predict by roughly an
order of magnitude throughout:

| case | seed | α | measured (‖·‖₂) | freeze bound (‖·‖∞) | bound/measured |
|---|---|---|---|---|---|
| C-3 | 7 | 0.05 | `3.3829e-01` | `2.5298e-02` | `0.075` |
| C-4 | 7 | 0.05 | `7.2508e-01` | `4.6420e-02` | `0.064` |
| C-6 | 7 | 0.05 | `5.8426e-02` | `1.1042e-02` | `0.189` |

### The algebra is correct; the norm is not

The C-5 identity `R(cu) − c·R(u) = (c² − c)·u·u_x` was verified **elementwise**
to `1.42e-14`, and `|c² − c|·‖u·u_x‖∞` reproduces `‖R(cu) − c·R(u)‖∞` to a ratio
of `1.0000`. The derivation is right. It is simply a derivation about a
different norm than the one the pipeline reports.

### One hypothesis tested and rejected

The near-constant ratio suggested a systematic factor, and the first candidate
was that a constant-valued *array* diffusivity routes through the v0.34a
variable-coefficient path while a *scalar* does not — which would make C-1 and
C-5 measure a different discretisation than the derivation assumed. **Measured
and rejected:** scalar `0.1` and `0.1·ones` produce identical residuals
(`2.321210e-02` for both) and identical `‖R(u)‖∞` on heat. Recorded because a
rejected hypothesis is part of the evidence.

### Why this blocks rather than being fixed in place

The remedy is small — restate the bounds in ‖·‖₂, or have the report emit both
norms. Either is a change to a **frozen** document, and amending a freeze is a
deliberate act taken in the open, not a correction folded into the run that
discovered the problem.

Proceeding instead would mean signing a confirmatory freeze whose tolerances
were fitted to ‖·‖₂ measurements while citing ‖·‖∞ derivations. That is exactly
the experimentally-tuned threshold PS-2 exists to forbid, wearing a derivation
as a citation.

**This is the two-stage freeze working.** Had the derivations been skipped and
thresholds fitted to the pilot numbers, they would have "worked" on every case,
and the freeze would have shipped citing bounds in a norm nobody had checked.

---

## 5. PS-3 — Grid non-reuse: **PASS**

`{0.0, 0.05, 0.1, 0.2, 0.4, 0.8}` and `{0.025, 0.075, 0.15, 0.3, 0.6}` are
disjoint, asserted by `test_the_alpha_grids_are_disjoint`. No confirmatory point
has been measured or looked at.

---

## 6. Outcome

| Criterion | Result |
|---|---|
| PS-1 — decision margin | **PASS** (binding margin `5.096e+11`; control holds bit-identically) |
| PS-2 — traceable tolerances | **FAIL** — norm mismatch, ‖·‖∞ derivations vs ‖·‖₂ measurement |
| PS-3 — grid non-reuse | **PASS** |

**Status: `blocked_pilot_criteria_not_met`. Blocking criterion: PS-2.**

`v0_37c_confirmatory_freeze.md` is not written. v0.37d does not open.

### What unblocking requires

1. An **amendment** to the hypothesis freeze restating the PS-2 derivations in
   the norm the report emits — or a change to the report to emit both, which is
   a v0.37b schema change and correspondingly larger.
2. Re-verification that the restated bounds bound the measurements.
3. A re-run of the pilot against the amended freeze.

None of that is done here, because the pilot's job was to find out whether the
criteria hold, and it found out that one does not.
