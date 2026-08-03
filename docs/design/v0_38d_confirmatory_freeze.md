# v0.38d — Confirmatory Freeze

**Status: SIGNED.**

Signed after [`v0_38d_pilot_report.md`](v0_38d_pilot_report.md) run 3. Runs 1
and 2 both blocked on B-1 and are retained unedited.

## 1. What is frozen

**Signal versus floor is reported, always.** A relative error exists only in the
`signal` regime; at the floor it is `None`, and the regime is on every payload
so a reader never has to infer which number they are looking at.

**The floor boundary is `sqrt(eps) · reference_scale`** — a **stated convention
with a rationale**, not a derivation. A quantity computed to relative accuracy
`eps` carries absolute noise `eps · scale` and is distinguishable from it beyond
a margin; `sqrt(eps)` is the conventional choice. Labelled honestly because runs
1 and 2 are what asserting a false derivation produces.

**`reference_scale` is declared for a single-point comparison**, with no
default. It is the quantity's characteristic magnitude, not the pointwise value —
at the floor the pointwise value *is* the floor.

**`reference_kind = none` is a first-class outcome**, with every error field
present and `None`. Never `0.0`, which reads as a perfect measurement; never
omitted, which reads as a question that was answered.

**The kind is derived from what was supplied.** Declaring `analytical` with no
reference is refused, as is supplying a reference under `none`.

**Every error carries an `ErrorMetricSpec`**, and comparison against a bound goes
through `require_matching_metric` — the v0.37c pilot-1 defect made impossible
rather than discouraged.

**Timing reports median and IQR, never a mean**, with warmup and measured counts,
refuses fewer than two runs, and declares itself
`platform_specific_diagnostic`.

## 2. What this freeze does **not** establish

- **No accuracy guarantee.** Measured error against a stated reference; no bound
  for unseen inputs.
- **No cross-platform timing claim.** DE-14 — timing is never compared across
  platforms.
- **No claim that the floor boundary is optimal.** It is conventional, and its
  rationale is stated so a later sub-phase can revisit it deliberately.
- **No discovery claim**, no unstructured meshes, no arbitrary geometry.

## 3. Signature

Signed. Changes to §1 are amendments with dated entries.
