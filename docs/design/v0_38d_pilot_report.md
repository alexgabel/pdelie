# v0.38d — Pilot Report

**Append-only.** Blocked runs retained unedited.

Pre-registered in [`v0_38d_hypothesis_freeze.md`](v0_38d_hypothesis_freeze.md) §4.

Platform: `Darwin/arm64`, CPython 3.12, NumPy 2.5.1.

**This pilot blocked twice, on the same criterion.** Both blocks are the
sub-phase's own subject matter turning up in its own implementation.

---

## Run 1 — **BLOCKED** on B-1

**Outcome:** `blocked_pilot_criteria_not_met`.

B-1: *"A relative error emitted in the `floor` regime."*

The pilot deliberately reproduces the v0.38b defect: evaluate `u'' = −16 sin(4x)`
at `x = π`, where the true value is zero, and see whether the layer built to
prevent a bogus relative error emits one.

It did.

```
regime = signal
absolute = 1.249e-13   relative = 6.070   ref_mag = 2.058e-14   floor = 2.317e-29
```

**A relative error of 6.07 at a point whose true value is zero** — the exact
shape of the v0.38b number, produced by the code written to prevent it.

**Cause.** The floor was `n · eps · scale` with `scale = max|computed|`. At a
zero crossing the computed value *is* ~0, so the threshold collapsed to
`2.3e-29`. The module docstring had warned that deriving the scale from the
quantity's own value "would make the threshold vanish exactly where it is
needed", and then did so.

---

## Run 2 — **BLOCKED** on B-1

**Outcome:** `blocked_pilot_criteria_not_met`.

**Amendment A-1** made `reference_scale` a required declared argument, so the
scale comes from the quantity rather than from the point. Floor became
`n · eps · scale` = `3.553e-15`.

Still blocked:

```
regime = signal   ref_mag = 2.058e-14   floor = 3.553e-15   relative = 6.070
```

The reference magnitude sits **six times above** the floor.

**Cause.** `n · eps · scale` bounds error in the **comparison arithmetic**. It
does not bound error in **producing the reference**. Evaluating `−16 sin(4x)`
near `x = π` inherits `x`'s own representation error amplified by
`|d/dx| = 64`, giving `~4e-14` — larger than the observed `2.06e-14`.

**This layer cannot derive that term**, because it cannot know how a caller
produced their reference. Run 2's amendment was directionally right and
insufficient, and recording it as a separate block rather than folding it into
run 1 keeps that visible.

---

## Run 3 — passed

**Amendment A-2:** a **relative** boundary at `sqrt(eps)`.

A quantity computed to relative accuracy `eps` carries absolute noise
`eps · scale`, and is distinguishable from that noise once it exceeds it by a
comfortable margin. `sqrt(eps) ≈ 1.5e-8` — the geometric mean of `eps` and 1 —
is the conventional margin.

**It is a stated convention with a rationale, not a quantity that falls out of
an equation.** Recorded that way rather than dressed up as a derivation, because
runs 1 and 2 are what happens when a boundary is asserted to be derived and is
not.

| case | reference / scale | regime | relative reported |
|---|---:|---|---|
| zero crossing (`x = π`) | `1.3e-15` | **floor** | `None` |
| away from it | `0.125` | signal | `2.451e-13` |
| small but real (`1e-6` of scale) | `1e-6` | signal | `1.000e-09` |

The third row matters: the boundary must not swallow real signal. A value at
`1e-6` of scale is small and genuine, and reads `signal`.

### Remaining criteria

| Criterion | Result |
|---|---|
| **B-2** no non-`None` field under `reference_kind = none` | **PASS** — enforced at construction |
| **B-3** metric-mismatched comparison refused | **PASS** — linf bound vs l2 measurement raises |
| **B-4** no mean in the timing payload | **PASS** |
| **B-5** fewer than two runs refused | **PASS** |
| **B-6** norms consistent | **PASS** — every error carries its `ErrorMetricSpec` |

### Timing spread

| | median | IQR |
|---|---:|---:|
| no warmup | `139.52 µs` | `0.94 µs` |
| 50 warmup runs | `144.65 µs` | `0.54 µs` |

Warmup halves the IQR. A mean alone would have shown neither, which is why
DE-12 refuses to report one.

---

## What two blocks on one criterion say

Not that the criterion was badly chosen — that it was well chosen. B-1 was
written to catch a defect this arc had already produced once, and it caught the
same defect twice more in the implementation meant to prevent it.

The general lesson is narrower than "be careful with relative errors": **a
boundary asserted to be derived, but actually depending on information the layer
does not have, will read as principled and behave arbitrarily.** Runs 1 and 2
both had a formula. Neither had the information the formula needed.
