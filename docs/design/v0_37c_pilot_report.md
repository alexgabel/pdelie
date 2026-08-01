# v0.37c — Pilot Report (run 2)

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
