# v0.38a — Pilot Report

**Append-only.** Blocked runs are retained unedited.

Pre-registered in [`v0_38a_hypothesis_freeze.md`](v0_38a_hypothesis_freeze.md)
§4, including the artifact location and criteria B-1…B-6.

Platform: `Darwin/arm64`, CPython 3.12, NumPy 2.5.1.

---

## Run 1 — passed

v0.38a introduces no numerical measurement. It is a contract layer: identities,
a closed reason vocabulary, derived provenance, and composition. The criteria
are therefore structural, and every one is a standing test rather than a
recorded number.

| Criterion | Result |
|---|---|
| **B-1** every frozen reason constructible | **PASS** — all five |
| **B-2** mask refuses a row set it does not describe | **PASS** — truncated and extended sets both refused |
| **B-3** availability unobtainable from a constructor argument | **PASS** — asserted absent from the signature |
| **B-4** composition commutative on the admitted set | **PASS** |
| **B-5** every excluded row carries exactly one primary reason | **PASS** — 1 excluded, 1 primary, 1 secondary recorded |
| **B-6** norms consistent | **not applicable** — no measurement, no norm |

B-6 is recorded as *not applicable* rather than *passed*. A criterion with
nothing to check has not been satisfied; it has not been exercised, and the two
must not read the same.

---

## A distinction this pilot records rather than glosses

**Every reason is constructible. None is yet produced by shipped detection
logic.**

`build_row_mask` takes its exclusions from the caller, so v0.38a supplies the
vocabulary and the type while the conditions that trigger them arrive with the
layer that can detect them:

| Reason | Producer owed by |
|---|---|
| `stencil_does_not_fit` | v0.38b |
| `coordinate_missing` | v0.38b |
| `derivative_unavailable` | v0.38b |
| `observation_masked` | v0.38a (upstream field mask) |
| `duplicate_coordinate` | v0.38b |

Criterion B-1 says "constructible", and it passes on that reading. Reading it as
"in use" would overstate what this sub-phase established — the same overstatement
the v0.38e reserved-pair block was about. `test_no_shipped_logic_produces_a_reason_yet_and_that_is_stated`
carries the table, so the gap is visible rather than inferred from an absence.

---

## Amendments

None. Run 1 met every applicable criterion on the first attempt.

That is worth stating plainly rather than presenting as a virtue: v0.38a is the
smallest sub-phase of the arc and introduces no measurement, so there was less
for a pilot to catch. A block count is diagnostic, not a score — see
`docs/planning/LEADERSHIP_METRICS.md`.
