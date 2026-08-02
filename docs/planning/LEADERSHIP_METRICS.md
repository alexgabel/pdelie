# Leadership Metrics

What to track per release arc, and what deliberately not to.

## Not a productivity KPI: block count

A two-stage freeze that blocks is doing its job; one that never blocks might be
doing its job, or might be measuring nothing. **Block count on its own says
neither.** Tracking it as a target invites the two failure modes that matter —
manufacturing blocks to look rigorous, and avoiding them to look fast.

The metrics below are diagnostic rather than evaluative. They are recorded so a
later reader can see what a release actually cost and what it actually caught.

## Metrics

| Metric | What it tells you |
|---|---|
| **New defect classes** | Failure modes seen for the first time. High is fine early, and should fall as guards accumulate. |
| **Repeat defect classes** | A class that recurred despite a guard existing. This is the one to act on — it means the guard was scoped wrongly, not that people were careless. |
| **Escaped specification defects** | Defects that reached a *later* sub-phase before detection. Cost scales with how far they travelled. |
| **Invalidated artifacts** | Frozen documents or measurements retracted after signing. Non-zero is honest; trending up means freezes are being signed too early. |
| **Time to diagnosis** | From symptom to named cause. Long times usually mean the symptom was reported in the wrong vocabulary. |
| **Cross-platform discrepancies** | Measured, not argued. An unrun platform is a discrepancy of unknown size. |
| **Failed-run retention rate** | Fraction of blocked/failed runs still present in the record. Below 100% means the record is a selection-effect document. |
| **Public claims narrowed or retired** | Claims the evidence stopped supporting. Healthy; a release that only ever widens claims is not checking them. |
| **Private-API promotion decisions** | Promoted, held, or reversed — with the reason. |

## v0.37 (retrofit)

Populated retroactively from the arc.

| Metric | v0.37 |
|---|---|
| New defect classes | **3** — norm mismatch between a derivation and its measurement; a frozen profile violating an unstated domain requirement; execution-vs-declaration mismatch in a benchmark runner (C-5) |
| Repeat defect classes | **2** — disclaim-vs-claim text scanning (5th and 6th occurrences); production `assert` under `-O` (2nd) |
| Escaped specification defects | **1** — the C-5 semantic mismatch escaped the entire arc and was found after the v0.37.0 tag |
| Invalidated artifacts | **1** — `v0_37c_confirmatory_freeze.md` (v1), invalidated for C-5 by the v0.37.1 erratum; retained unedited |
| Time to diagnosis | Norm mismatch: same session, ~3 measurements. Nonperiodic profile: same session, after one wrong hypothesis (constant-array dispatch) was measured and rejected. C-5: post-release, external review. |
| Cross-platform discrepancies | **0, measured** (v0.37.1). Replayed on `Darwin/arm64` and `Linux/x86_64`: classifications agree exactly, signal-case numbers to `1.6e-13` relative. Recorded as unknown until measured. |
| Failed-run retention rate | **100%** — all three pilot runs retained unedited, enforced by test |
| Public claims narrowed or retired | **2** — C-4 retired from the benchmark; the v0.37c taxonomy narrowed from six cases to five |
| Private-API promotion decisions | **1** — point-symmetry registry held private, on the narrowed evidentiary base plus the unchanged v0.35b reason |

### What the v0.37 row says

The **repeat** column is the actionable one. Disclaim-vs-claim recurred twice
more in a single arc despite being documented at length in
`tests/test_forbidden_language.py`. The guard existed; it just was not reused —
each new scan was written fresh with `in text`. The durable fix is not more
documentation but a shared helper, and every such scan is now `ast`-based.

The **escaped** column is the expensive one. C-5 survived a hypothesis freeze,
three pilots, a confirmatory freeze, a release close and a tag. Every one of
those gates checked that the *declared* thing was coherent; none checked that
the declared thing was the thing *executed*. That is a whole category of gate
the arc did not have, and `tests/test_benchmark_action_semantics_guard.py` is
the first instance of it.

**Cross-platform was recorded as unknown rather than as passing**, and then
measured at v0.37.1. The argument that eleven-order margins cannot flip a
classification was sound; it was still not a measurement, and the row said so
until one existed. The measurement agreed with the argument, which is the
outcome that makes the distinction easy to stop drawing.
