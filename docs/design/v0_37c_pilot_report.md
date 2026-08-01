# v0.37c — Pilot Report

**Three pilot runs. Two blocked, the third passed.**

**Final status: PS-1, PS-2 and PS-3 all PASS on the amended five-case registry.
The confirmatory freeze is signed at
[`v0_37c_confirmatory_freeze.md`](v0_37c_confirmatory_freeze.md).**

Records are **additive**. Runs 1 and 2 are retained in full below, unedited. A
report that shows only the passing run is a selection-effect document, and the
two blocks are the substantive content of this phase — each caught a
specification defect that would otherwise have propagated into v0.37d.

| Run | Seeds | Outcome | Defect found |
|---|---|---|---|
| 1 | `7, 11, 13, 17, 19` | `blocked_pilot_criteria_not_met`, PS-2 | Report emitted `‖·‖₂`; freeze derived `‖·‖∞`. Norm mismatch, ratio 11.96. |
| 2 | `2, 3, 5, 7, 11` | `blocked_pilot_criteria_not_met`, PS-2, case C-4 | §6 bound dropped the `a'·u_x` term; and `monotone_smooth` is nonperiodic on a periodic domain. |
| 3 | `2, 3, 5, 7, 11` | **PASS** | — |

---

# Run 1 — BLOCKED on the norm mismatch

**Outcome at the time: `blocked_pilot_criteria_not_met`, criterion PS-2.**

Retained unedited. Superseded by runs 2 and 3; the defect it found (the norm
mismatch) was fixed by the amendment recorded in run 2.

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

---

# Run 2 — first five primes: BLOCKED on C-4

**Status: `blocked_pilot_criteria_not_met`.**
**Blocking criterion: PS-2 (traceable tolerances).**
**Blocking case: C-4.**
**Consequence: the confirmatory freeze is not signed, and v0.37d does not open.**

Supersedes run 1, which blocked on a norm mismatch now resolved. Governed by
[`v0_37c_hypothesis_freeze.md`](v0_37c_hypothesis_freeze.md), which
pre-registered this status and required the reason to name its criterion.

---

## 1. What changed since run 1

Run 1 blocked because the freeze derived bounds in `‖·‖∞` while the report
emitted `‖·‖₂`. Three amendments landed before this run:

| | |
|---|---|
| Norm | the report now emits `absolute_error_linf` beside `absolute_error_l2`, additively; PS-2 compares like with like |
| Frozen parameters | C-5's rescale factor (`2.0`) and each case's `shift_cells` (`3`) moved onto `BenchmarkCase`, so no action parameter is an implicit module constant |
| Domain gate | `execute_state_action` now refuses `spatial_translation` on any `domain_type` other than `periodic_uniform` — `np.roll` wraps, and that is only meaningful on a periodic domain |

## 2. What was run

Seeds `2, 3, 5, 7, 11` — the first five primes, chosen so no reader has to
wonder why those, and deliberately *not* the reconnaissance seeds. All five
retained; none dropped.

180 measurements: 6 cases × 6 α × 5 seeds, 32 × 32 grid, 3-cell translation,
through the shipped `execute_bundle` → `build_residual_commutation_report` path.
No threshold applied anywhere.

**Informed-pilot disclosure.** Reconnaissance measured on this same α grid. This
pilot is a code-and-seed replication at broader seed count, not a blind run. The
confirmatory grid remains disjoint and unlooked-at; that is where blindness
lives.

## 3. Measurements — `‖·‖∞`, worst over seeds

| alpha | `C-1` | `C-2` | `C-3` | `C-4` | `C-5` | `C-6` |
|---|---|---|---|---|---|---|
| `0.0` | `1.1990e-14` | `1.1990e-14` | `1.1990e-14` | `1.1990e-14` | `3.9902e-01` | `7.0777e-16` |
| `0.05` | `1.1990e-14` | `1.2490e-14` | `4.8927e-02` | `1.1037e-01` | `3.9902e-01` | `1.1399e-02` |
| `0.1` | `1.1990e-14` | `1.2212e-14` | `9.7854e-02` | `2.2074e-01` | `3.9902e-01` | `2.2798e-02` |
| `0.2` | `1.1990e-14` | `1.1879e-14` | `1.9571e-01` | `4.4149e-01` | `3.9902e-01` | `4.5596e-02` |
| `0.4` | `1.1990e-14` | `1.2212e-14` | `3.9141e-01` | `8.8298e-01` | `3.9902e-01` | `9.1192e-02` |
| `0.8` | `1.1990e-14` | `1.4211e-14` | `7.8283e-01` | `1.7660e+00` | `3.9902e-01` | `1.8238e-01` |

## 4. PS-1 — Decision margin: **PASS**

| alpha | max valid | min invalid | margin |
|---|---|---|---|
| `0.0` | `1.1990e-14` | `5.4123e-16` | `4.514e-02` — **control, correctly not separable** |
| `0.05` | `1.2490e-14` | `2.4953e-03` | **`1.998e+11`** |
| `0.1` | `1.2212e-14` | `4.9905e-03` | `4.086e+11` |
| `0.2` | `1.1990e-14` | `9.9811e-03` | `8.324e+11` |
| `0.4` | `1.2212e-14` | `1.9962e-02` | `1.635e+12` |
| `0.8` | `1.4211e-14` | `3.9924e-02` | `2.809e+12` |

A single threshold separates valid from invalid at every α > 0 over all five
seeds simultaneously. Binding margin `1.998e+11`.

At `α = 0` the obstruction cases are **bit-identical to C-1** on every seed. At
zero dose they are the same problem, and the pipeline reports them as one.

Dose-response exactly linear, `error/α` constant to seven significant figures.

## 5. PS-2 — Traceable tolerances: **FAIL on C-4**

Two derivation defects were found. One is fixed; one is a defect in a frozen
case and blocks.

### Fixed — the dropped product-rule term

The original §6 bound kept only `a·u_xx` and came in at `0.52`–`1.00` of the
observed error: not a bound. The diffusion operator is
`(a·u_x)_x = a'·u_x + a·u_xx`, and the `a'` term is the same order in α.
Dropping it was a derivation error. §6 is amended, and the corrected bound holds
with margin on the periodic profiles:

| case | profile | corrected bound / measured |
|---|---|---|
| C-3 | `sinusoidal` | `1.86` – `1.96` |
| C-6 | `localized_bump` | `1.81` – `9.02` |
| C-4 | `monotone_smooth` | **`0.65` – `1.76` — does not bound** |

### Blocking — `monotone_smooth` is not periodic

Every case declares `domain_type: periodic_uniform`. `monotone_smooth` is
`tanh((x−x₀)/w)`, which runs from `−0.9999` to `+0.9999`:

| profile | wrap jump | typical adjacent step | periodic |
|---|---|---|---|
| `constant` | `0.0000e+00` | `0.0000e+00` | yes |
| `sinusoidal` | `3.8268e-01` | `3.8268e-01` | yes |
| **`monotone_smooth`** | **`1.9998e+00`** | `3.1981e-01` | **NO — 6.25×** |
| `localized_bump` | `0.0000e+00` | `5.0918e-01` | yes |
| `higher_frequency` | `9.2388e-01` | `1.0898e+00` | yes |

Under `np.roll` that discontinuity travels through the interior. **C-4 therefore
measures a wrap artefact, not the monotone coefficient variation it is named
for**, and no smooth bound can trace it. The periodicity requirement was assumed
throughout and never written down; §3 now states it.

C-5 traces **exactly**: `|c²−c|·‖u·u_x‖∞` reproduces the measurement at ratio
`1.000000` on all five seeds.

## 6. PS-3 — Grid non-reuse: **PASS**

Grids disjoint; no confirmatory point measured or looked at.

## 7. Outcome

| Criterion | Result |
|---|---|
| PS-1 | **PASS** — binding margin `1.998e+11`, control bit-identical |
| PS-2 | **FAIL** — C-4's profile is non-periodic on a periodic domain |
| PS-3 | **PASS** |

**`blocked_pilot_criteria_not_met`. Blocking criterion: PS-2. Blocking case: C-4.**

Five of six cases would pass. Blocking on one is the pre-registered rule, and
partial credit is not an outcome the two-stage freeze offers.

### The decision that unblocks

C-4 tests "state-only translation against a monotone coefficient". A monotone
function is not periodic, so the case as frozen cannot be run on a periodic
domain without measuring the seam. Three routes, none of which this report
takes:

1. **Make the profile periodic** — e.g. a smooth periodic ramp with a single
   monotone stretch. Keeps C-4's intent; changes what it measures in detail.
2. **Run C-4 on a nonperiodic domain** — matches the profile's nature, but
   `exact_grid_shift` refuses non-periodic domains as of this amendment, so it
   needs a crop-based action that does not exist yet.
3. **Retire C-4** — five cases, and the monotone axis returns when nonperiodic
   actions land.

Route 1 keeps the six-case structure; route 2 is the most faithful and the most
work; route 3 is honest and smallest. The choice changes what the benchmark
claims, so it is not made here.


---

# Run 3 — five-case registry, corrected bound: **PASS**

## What changed since run 2

C-4 retired and `monotone_smooth` dropped from the registry, per the retirement
recorded in §2 of the hypothesis freeze. §6's bound corrected to include the
`a'·u_x` term. Nothing else.

## Measurements — `‖·‖∞`, worst over seeds `2, 3, 5, 7, 11`

| alpha | `C-1` | `C-2` | `C-3` | `C-5` | `C-6` |
|---|---|---|---|---|---|
| `0.0` | `1.1990e-14` | `1.1990e-14` | `1.1990e-14` | `3.9902e-01` | `7.0777e-16` |
| `0.05` | `1.1990e-14` | `1.2490e-14` | `4.8927e-02` | `3.9902e-01` | `1.1399e-02` |
| `0.1` | `1.1990e-14` | `1.2212e-14` | `9.7854e-02` | `3.9902e-01` | `2.2798e-02` |
| `0.2` | `1.1990e-14` | `1.1879e-14` | `1.9571e-01` | `3.9902e-01` | `4.5596e-02` |
| `0.4` | `1.1990e-14` | `1.2212e-14` | `3.9141e-01` | `3.9902e-01` | `9.1192e-02` |
| `0.8` | `1.1990e-14` | `1.4211e-14` | `7.8283e-01` | `3.9902e-01` | `1.8238e-01` |

150 measurements: 5 cases × 6 α × 5 seeds. All seeds retained.

## PS-1 — **PASS**

| alpha | max valid | min invalid | margin |
|---|---|---|---|
| `0.0` | `1.1990e-14` | `5.4123e-16` | `4.514e-02` — **control, correctly not separable** |
| `0.05` | `1.2490e-14` | `2.4953e-03` | **`1.998e+11`** |
| `0.1` | `1.2212e-14` | `4.9905e-03` | `4.086e+11` |
| `0.2` | `1.1990e-14` | `9.9811e-03` | `8.324e+11` |
| `0.4` | `1.2212e-14` | `1.9962e-02` | `1.635e+12` |
| `0.8` | `1.4211e-14` | `3.9924e-02` | `2.809e+12` |

Binding margin `1.998e+11`. At `α = 0` the obstruction cases are bit-identical
to C-1. Dose-response exactly linear.

## PS-2 — **PASS**

Every tolerance traces to a §6 derivation, and each derivation was verified to
bound the measurement across all seeds and all α:

| case | reference | bound / measured |
|---|---|---|
| C-1, C-2 | spectral floor, measured on the same grid (§6) | — floor-limited, `1.33e-14` worst |
| C-3 | `a₀·α·(‖Δf‖∞·‖u_xx‖∞ + ‖Δf'‖∞·‖u_x‖∞)` | `1.857` – `1.956` |
| C-6 | same | `1.810` – `9.020` |
| C-5 | `\|c²−c\|·‖u·u_x‖∞`, an identity | exact to `1.5e-16` |

No tolerance was fitted to a measurement.

## PS-3 — **PASS**

Grids disjoint; the confirmatory points were unmeasured at the time of this run.

## Outcome

**All three criteria pass.** The confirmatory freeze is signed.

---

# Appendix A — the C-5 semantic defect (v0.37.1)

**Appended 2026-08-02. Nothing above this line was edited.** The first
419 lines of this file hash to `78b7dae6eabc44c8...`, pinned by
`test_v0_37c_pilot_report_is_append_only`.

## What was found, after the tag

C-5's bundle declared a `scalar_rescale` on the **parameter**. The runner never
read it: `execute_bundle` computed `execution.transformed_parameters` correctly,
and the runner discarded that, built a `FieldBatch` by hand, and rescaled the
**state**.

Runs 1, 2 and 3 above all measured a state rescale under a parameter
declaration. Their C-5 numbers are internally consistent and describe the wrong
transformation.

## Why the three runs above did not catch it

Every check in this report asks whether the *declared* thing is coherent — do
the classifications separate, do the tolerances trace, are the grids disjoint.
C-5 passed all of them, because a state rescale really is a valid obstruction
with a valid derivation. It is simply not the obstruction C-5 names.

The missing question was *is the declared action the one the runner consumed?*

## The repair

The runner now reads `execution.transformed_parameters["nu_baseline"]` and
builds an evaluator from the rescaled parameter, leaving the state untouched.
`ProblemInstanceSpec` refuses a name owned by both `parameters` and
`coefficient_fields`, which C-5 had.

`tests/test_benchmark_action_semantics_guard.py` scans for the pattern and found
all three of C-5's constructs on its first run, having been written from the
class rather than this instance.

## Run 4 — repaired semantics, fresh seeds: **PASS**

Seeds `13, 17, 19, 23, 29`, disjoint from runs 2 and 3.

| alpha | `C-1` | `C-2` | `C-3` | `C-5` | `C-6` |
|---|---|---|---|---|---|
| `0.0` | `1.3101e-14` | `1.3101e-14` | `1.3101e-14` | `1.6286e-01` | `8.7430e-16` |
| `0.05` | `1.3101e-14` | `1.3711e-14` | `6.0205e-02` | `1.6286e-01` | `1.1108e-02` |
| `0.1` | `1.3101e-14` | `1.2823e-14` | `1.2041e-01` | `1.6286e-01` | `2.2217e-02` |
| `0.2` | `1.3101e-14` | `1.2990e-14` | `2.4082e-01` | `1.6286e-01` | `4.4434e-02` |
| `0.4` | `1.3101e-14` | `1.3101e-14` | `4.8164e-01` | `1.6286e-01` | `8.8867e-02` |
| `0.8` | `1.3101e-14` | `1.3711e-14` | `9.6327e-01` | `1.6286e-01` | `1.7773e-01` |

PS-1 **PASS**, binding margin `4.484e+11`; control holds at α = 0. PS-2 **PASS**
— C-5's repaired derivation `|c−1|·ν·‖u_xx‖∞` is exact at ratio `1.000000` on
every seed. PS-3 **PASS**.

C-5's value moved from `3.9902e-01` to `1.6286e-01` because it now measures a
different transformation. That the number changed is the point.

The confirmatory freeze is
[`v0_37c_confirmatory_freeze_v2.md`](v0_37c_confirmatory_freeze_v2.md); v1 is
retained unedited and invalidated for C-5 by
[`V0_37_C5_ERRATUM.md`](../releases/V0_37_C5_ERRATUM.md).
