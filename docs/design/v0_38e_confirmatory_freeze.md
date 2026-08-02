# v0.38e — Confirmatory Freeze

**Status: SIGNED.**

Signed after [`v0_38e_pilot_report.md`](v0_38e_pilot_report.md) run 2 met every
pre-registered criterion. Run 1 blocked on B-1 and is retained unedited.

Governed by [`v0_38e_hypothesis_freeze.md`](v0_38e_hypothesis_freeze.md), frozen
before any v0.38e code was written.

**Platform:** `Darwin/arm64`, CPython 3.12, NumPy 2.5.1. See §6 for what that
does and does not license.

---

## 1. Grid

**Confirmatory α:** {0.025, 0.075, 0.15, 0.3, 0.6}
**Pilot α:** {0.0, 0.05, 0.1, 0.2, 0.4, 0.8}
**Overlap: none.** The grids are disjoint, so no number signed here was seen
while the specification was still being amended.

Seeds {13, 17, 19, 23, 29}, frozen at the pilot report before any confirmatory
number existed. 175 measurements across 7 cases.

---

## 2. The `equation_form` correction

The benchmark declared `equation_form="nonconservative"` as a literal on every
case. The residual evaluators dispatch on the field's `nu_form` provenance tag,
and took the **conservative** branch on every variable-coefficient case. The
declaration named an operator that produced none of the numbers.

`equation_form` is not inert: `reporting/summaries.py` carries it into summary
payloads, and it is inside `ProblemInstanceSpec.identity()`'s semantic hash.

**Size of the difference.** The two forms differ by exactly `nu' · u_x` — the
same term the v0.37c §6 bound dropped:

| profile | max \|nu'\| | ‖nu'·u_x‖ / ‖residual‖ |
|---|---:|---:|
| `constant` | 0.000e+00 | **0.0000**, exactly |
| `sinusoidal` | 9.745e-02 | **1.0353** |

On a variable coefficient the difference **exceeds the residual itself**. On a
constant coefficient it is identically zero, which is why the mislabel was
invisible for the scalar path and why C-1 and C-5 were unaffected.

It is now **derived** from provenance, per C-1 of the v0.38 binding constraints.

**No measured number moved.** All 125 v0.37c-case confirmatory measurements were
recomputed and compared against `main`:

```
bitwise identical : 125/125
worst relative gap: 0.000e+00
```

Bitwise, not to tolerance. The correction changes a declaration and a bundle
identity hash, and nothing else.

---

## 3. C-7 / C-8 — the multi-parameter pair

The first cases with **two** numeric parameters. That population is the only one
on which the unnamed-rescale-target ambiguity is observable: with one parameter,
"rescale all" and "rescale the declared one" are the same set, which is exactly
why the v0.37c suite could not detect the defect.

The pair differs in **one declaration** — whether `target_parameters` is named —
so any difference in outcome is attributable to that and nothing else. Same
family, profile, factor, second parameter and value. Asserted by test.

### C-7 — named target, measured

| | |
|---|---|
| outcome | `measured`, all 25 rows |
| consistency | `consistent` / `declaration_and_execution_agree` |
| `nu_baseline` | `0.1 → 0.2` — the declared `× 2.0` |
| `advection_speed` | `2.0 → 2.0`, **unchanged in all 25 rows** |
| `absolute_error_l2` | `[1.1176e+00, 2.6799e+00]` |

The `advection_speed` row is the one that matters. Before v0.38e the identical
declaration produced `4.0`.

### C-8 — unnamed target, refused

| | |
|---|---|
| outcome | `blocked_ambiguous_parameter_target`, all 25 rows |
| consistency | `indeterminate` / `target_ambiguous` |
| residual | **none** — refused before any residual was computed |

`indeterminate`, not `inconsistent`: nothing disagreed, the question is
unanswerable from what the bundle carries. Every error field is `None` — never
`0.0`, which would read as a perfect measurement, and never `NaN`, which would
not survive strict JSON.

### Separation

| | |
|---|---:|
| C-1 control floor | `[1.7574e-14, 1.1457e-13]` |
| C-7 minimum | `1.1176e+00` |
| **C-7 min / C-1 max** | **9.755e+12** |

Nearly thirteen orders. The confirming case is not at the spectral floor, so it
is distinguishable from a control rather than merely non-zero.

---

## 4. Amendment A-1 (from pilot run 1)

Pilot run 1 **blocked** on criterion B-1: `LEGAL_STATUS_DIAGNOSIS_PAIRS`
declared `('inconsistent', 'executed_not_declared')`, and nothing could produce
it. A legal-pairs table containing an unreachable entry advertises a distinction
the report has never drawn.

It is **reserved, not deleted** — it names the pre-v0.38e behaviour exactly, and
deleting the vocabulary would leave a future recurrence unnameable.

The reservation is **proven, not asserted**: a test parses every literal
`(status, diagnosis)` assignment in the summariser with `ast` and fails if one
ever emits a reserved pair. Absence of a test that produces it is not evidence —
that absence is how the block arose.

Run 1 and run 2 numbers are identical. A-1 changed specification, not data.

---

## 5. What this freeze establishes

- A parameter action with an ambiguous target is **refused**, and the refusal is
  reported with a named diagnosis rather than raised as an opaque error.
- A named target rescales **only** what it names, measured through the executor
  across 25 rows rather than inferred from a declaration.
- The declared equation form is **derived from provenance** and now names the
  operator that produced the numbers.
- The two coefficient-array identities are separate, and their difference is
  demonstrated by fixtures — including a non-transitive triple and a case where
  they give opposite, both-correct answers.

## 6. What this freeze does **not** establish

- **Nothing about nonperiodic domains.** Still deferred to v0.41.
- **Nothing about irregular grids.** That is v0.38a–d, behind the
  `v0.38.0-rc1` gate.
- **Nothing about coefficient fields with more than one coordinate dependency.**
  Every v0.38e case is 1-D in space.
- **No claim that `target_ambiguous` detects every under-specification.** It
  detects the one the pilot identified. Others may exist and are not ruled out.
- **No claim that the reserved pair can never become reachable.** It asserts
  that no *current* code path emits it, checked by parsing.
- **No cross-platform claim.** Every number here is `Darwin/arm64`. The v0.38e
  report carries no floating-point threshold — the classifications are
  `exact_discrete` — so a replay is *expected* to agree exactly. That is an
  argument, not a measurement, and it is recorded as one until a replay runs.

---

## 7. Signature

Signed on the disjoint confirmatory grid, after one blocked pilot run and one
passing run, with the blocked run retained.

Any change to §2 or §3 after this point is an amendment with its own dated
entry, not an edit.
