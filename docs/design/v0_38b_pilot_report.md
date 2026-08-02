# v0.38b — Pilot Report

**Append-only.** Blocked runs retained unedited.

Pre-registered in [`v0_38b_hypothesis_freeze.md`](v0_38b_hypothesis_freeze.md)
§5. The freeze contains **no threshold value**; measuring them is what this
pilot is for.

Platform: `Darwin/arm64`, CPython 3.12, NumPy 2.5.1.

---

## Run 1 — **BLOCKED** on B-4

**Outcome:** `blocked_pilot_criteria_not_met`.

### What blocked

B-4: *"A uniform grid reporting `spacing_ratio != 1.0` (FN-12)."*

FN-12 as frozen required a uniform grid to report **exactly** `1.0`. Measured:

| `n` | `spacing_ratio − 1` |
|---:|---:|
| 8 | `0.000e+00` |
| 33 | `4.663e-15` |
| 129 | `1.821e-14` |
| 1024 | `1.448e-13` |
| 4096 | `5.791e-13` |

`np.linspace` does not produce bitwise-constant spacings. Only the smallest grid
passed.

### Resolution (amendment A-1)

The freeze anticipated this: *"If it cannot be made exact, FN-12 is amended with
the measured deviation rather than loosened silently."*

The deviation was measured across three domain spans (`2π`, `1.0`, `1000.0`) and
ten node counts. It is **linear in `n`**:

```
spacing_ratio − 1  ≈  0.637 · n · eps        (stable across all three spans)
```

Linear accumulation is what floating-point arithmetic predicts here, so the
*form* of the bound is derived and the measurement only establishes that the
constant is below one. The frozen bound is **`n · eps`**, which covers the worst
observed case (`0.647 · n · eps`) with **1.5× margin**.

**This is a derived bound, not a fitted one.** A fitted bound would have taken
`0.647` and added a safety factor; this takes the analytically-predicted form and
uses measurement only to confirm the constant is bounded.

**It does not swallow real non-uniformity.** A 129-node grid with one node moved
by `1e-9` reports `spacing_ratio − 1 = 2.560e-07` against a tolerance of
`2.864e-14` — seven orders of margin.

---

## Run 2 — passed

### A measurement error caught inside the pilot

The first attempt at the accuracy sweep reported a **uniform** grid as the
*worst* case — errors of `1e-2` to `3e-1` while strongly non-uniform grids
converged to `1e-14`. That is backwards, and it was the measurement, not the
code.

The sweep evaluated at `x = π` where `sin(4x) = 0`, and divided by
`max(|exact|, 1e-12)`. It was reporting an absolute error of `~1e-14` against an
artificial `1e-12` floor.

**Relative error is meaningless at a zero crossing.** Re-measured against the
derivative's own scale (`max|u^(d)|`), the uniform grid is the best case, as it
should be. Recorded because the wrong number would have produced a wrong G-5
threshold, and nothing downstream would have flagged it.

### B-1 — polynomial exactness (the oracle)

**PASS.** Exact for every degree `≤ n−1` across stencils 3–8 and derivative
orders 1–3, on irregular nodes with spacing ratio `> 10`, evaluated off-node.
Exactness **stops** at degree `n`, which pins the order rather than bounding it.

### Conditioning versus spacing ratio → the G-5 threshold

Weight magnitude grows steeply with the ratio:

| spacing ratio | `max|w|` (d=1) | `max|w|` (d=2) |
|---:|---:|---:|
| 1.0 | `6.40e+00` | `1.82e+02` |
| 31.9 | `9.49e+01` | `1.45e+03` |
| 199.9 | `1.93e+03` | `6.71e+04` |
| 342.6 | `4.59e+03` | `1.97e+05` |

**The achieved error floor does not follow it.** Over 3 functions × 2 grid sizes
× 2 stretching families (power-law and random-jitter):

| target ratio | worst floor, d=1 | worst floor, d=2 |
|---:|---:|---:|
| 1 | `2.79e-15` | `3.29e-12` |
| 10 | `2.53e-14` | `2.26e-12` |
| 100 | `7.27e-14` | `3.36e-12` |
| 1000 | `3.10e-14` | `3.21e-11` |
| 10000 | `2.39e-13` | `2.23e-11` |

A ~400× growth in weight magnitude produces roughly **one order of magnitude** of
floor degradation. The amplified weights multiply function values that are
correspondingly closer together, and the errors largely cancel.

**Consequence for G-5: it is a reporting threshold, not a refusal boundary.**
The evidence does not support a ratio at which Fornberg differentiation becomes
unusable for `d ≤ 3`. It does support telling a caller when the floor has
measurably degraded.

**Frozen value: `10.0`** — the lowest ratio at which any measured derivative
order shows ≥10× floor degradation from uniform (`d=1`: `2.79e-15 → 2.53e-14`).

### Returns versus stencil size → the cap

Absolute error / derivative scale, `d=2`, `N=201`:

| stencil | r=1 | r=10 | r=100 | r=1000 |
|---:|---:|---:|---:|---:|
| 5 | `3.47e-07` | `6.24e-07` | `6.30e-07` | `1.53e-07` |
| 7 | `8.79e-10` | `1.09e-10` | `7.95e-10` | `9.50e-11` |
| 9 | `2.45e-12` | `2.29e-12` | `1.16e-12` | `5.28e-13` |
| **11** | `2.30e-15` | `1.55e-13` | `1.97e-14` | `9.83e-13` |
| 13 | `1.30e-14` | `1.55e-13` | `2.08e-13` | `6.09e-13` |
| 21 | `9.41e-15` | `1.55e-13` | `2.47e-13` | `7.55e-13` |
| 25 | `8.35e-15` | `5.53e-13` | `3.21e-13` | `1.54e-13` |

Truncation error reaches the roundoff floor at **n = 11**. Past it, additional
nodes buy no accuracy and cost admissible rows — a stencil of `n` excludes `n−1`
rows at the boundaries.

**Frozen cap: `13`** — one step past the measured saturation point, so the cap
is a guard against unbounded growth rather than a performance optimum.

**The cap's evidence is thinner than G-5's** and is recorded as such: saturation
was measured at one grid size for `d ≤ 3`. It is justified by *diminishing
returns plus row cost*, not by instability — no instability was observed at any
stencil size tested.

### B-3 — the four owed exclusion reasons

**PASS.** `stencil_does_not_fit`, `coordinate_missing`, `duplicate_coordinate`
and `derivative_unavailable` are produced by shipped logic, closing the gap
v0.38a's pilot report recorded.

### B-5 — degenerate coordinates

**PASS.** Duplicates and unsorted input are refused, never repaired.

### B-6 — norms

**PASS**, and see the correction above: every floor is now an absolute error
normalised by the derivative's own scale, stated as such, and no number is
reported as a relative error against a near-zero denominator.

### B-7 — no threshold in shipped code before the freeze

**PASS.** `g5_verdict` read `threshold_not_yet_frozen` throughout the pilot.

---

## Evidence base, stated narrowly

The frozen values rest on: **3 functions** (`sin 4x`, `exp(x/3)`, a Gaussian),
**2 node counts** (101, 301, plus 201 for the stencil sweep), **2 stretching
families** (power-law, random-jitter), **derivative orders 1–3**, **one
platform**.

That is broader than one curve and narrower than a proof. Both thresholds are
diagnostics rather than correctness boundaries, which is what makes an evidence
base of this size proportionate.
