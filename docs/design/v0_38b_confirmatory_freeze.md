# v0.38b — Confirmatory Freeze

**Status: SIGNED.**

Signed after [`v0_38b_pilot_report.md`](v0_38b_pilot_report.md) run 2. Run 1
blocked on B-4 and is retained unedited. Governed by
[`v0_38b_hypothesis_freeze.md`](v0_38b_hypothesis_freeze.md), which was written
before any code and contained **no threshold value**.

## 1. Thresholds, measured

| Constant | Value | Justified by |
|---|---:|---|
| `G5_SPACING_RATIO_THRESHOLD` | **10.0** | lowest ratio at which any measured derivative order shows ≥10× floor degradation from uniform |
| `MAX_STENCIL_SIZE` | **13** | one step past the measured saturation of truncation error at 11 nodes |

Neither is a correctness boundary.

## 2. The pilot's substantive finding

**Weight magnitude is a poor proxy for achieved error.** Between a uniform grid
and a spacing ratio of ~340, `max|w|` grows ~400×. The achieved error floor moves
by about **one order of magnitude**.

The amplified weights multiply function values that are correspondingly closer
together, and the errors largely cancel. A threshold set from weight magnitude
would have been far too aggressive.

So **G-5 reports; it does not refuse.** The pilot measured no spacing ratio at
which Fornberg differentiation became unusable for derivative orders 1–3, up to
a ratio of `1.6e8`.

## 3. FN-12, amended

The freeze required a uniform grid to report `spacing_ratio` **exactly** `1.0`.
It does not: `np.linspace` spacings are not bitwise constant, and run 1 blocked.

The deviation is **linear in the node count** — `0.637 · n · eps`, stable across
three domain spans — which is what floating-point accumulation predicts. The
frozen bound is `n · eps`: the *form* is derived from the arithmetic and the
measurement establishes only that the constant is below one. Worst observed case
`0.647 · n · eps`, so 1.5× margin.

It does not swallow real non-uniformity: a 129-node grid with one node moved by
`1e-9` sits seven orders outside the tolerance.

## 4. What this freeze establishes

- Fornberg weights on arbitrary 1-D nodes, verified against textbook stencils
  and against polynomial exactness on irregular nodes, off-node.
- `formal_accuracy = n − d`, **derived** from the stencil used, with an
  independent manufactured-solution oracle that also asserts where exactness
  **stops** — pinning the order rather than bounding it below.
- Degenerate grids refused, never repaired.
- Four of v0.38a's five exclusion reasons now **produced** by shipped logic,
  closing the gap v0.38a's pilot report recorded. `observation_masked` comes from
  the upstream field mask and is not owed here.

## 5. What this freeze does **not** establish

- **No weak-form support on irregular samples.** v0.38c.
- **No derivative-error reporting.** v0.38b reports conditioning; quantified
  error reference is v0.38d.
- **No claim beyond derivative orders 1–3**, 1-D, on a declared axis.
- **No claim that the cap is a stability boundary.** No instability was observed
  at any stencil size tested; the cap rests on diminishing returns plus row
  cost, and its evidence is thinner than G-5's.
- **No cross-platform claim.** The conditioning numbers are `tolerance_numeric`
  and a replay is owed. The `exact_discrete` parts — refusals, reason
  classification, weight structure — are expected to agree exactly.

## 6. Evidence base

3 functions × 2–3 node counts × 2 stretching families × derivative orders 1–3,
on one platform. Broader than one curve, narrower than a proof — proportionate
because both thresholds are diagnostics.

## 7. Signature

Signed. Changes to §1 are amendments with dated entries.
