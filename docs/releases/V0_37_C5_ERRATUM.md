# Erratum — v0.37.0 benchmark case C-5

**Issued:** 2026-08-02, with `v0.37.1`.
**Scope:** benchmark case C-5 only. Cases C-1, C-2, C-3 and C-6 are unaffected.

---

## What was wrong

**v0.37.0 did not test parameter-only obstruction correctly.**

C-5's bundle declared a `scalar_rescale` action on the **parameter**. The
benchmark runner never read it. `execute_bundle` computed the rescaled parameter
into `execution.transformed_parameters` — correctly — and the runner discarded
that, constructed a `FieldBatch` by hand, and rescaled the **state** instead.

So the case measured `R(cu)` versus `c·R(u)` — a state rescale — while declaring
a parameter rescale. Those are different transformations, and the one under test
was not the one performed.

## What was *not* wrong

The arithmetic. The v0.37.0 record states C-5's derivation
`|c² − c|·‖u·u_x‖∞` reproduced the measurement at ratio `1.000000` on every
seed, and it did. That derivation is exactly right **for a state rescale**. The
defect is that a state rescale is not what C-5 declared.

The executor was also correct throughout. `execute_bundle` computed the right
thing; the benchmark walked around it.

## Why nothing caught it

Every v0.37 gate — the hypothesis freeze, three pilots, the confirmatory freeze,
the release close, the tag — checked that a **declared** thing was internally
coherent. None checked that the declared thing was the thing **executed**.

That whole category of gate was missing. It now exists as
`tests/test_benchmark_action_semantics_guard.py`, which was written from the
pattern rather than from this defect and flagged all three of its constructs on
first run.

## What is invalidated

| Artifact | Status |
|---|---|
| `docs/design/v0_37c_confirmatory_freeze.md` (v1) | **Invalidated for C-5 only.** Retained unedited. Its C-5 tolerance describes a measurement nobody asked for. |
| v1's C-5 §6 derivation | Superseded. Correct arithmetic, wrong transformation. |
| v1's other four cases | **Unaffected**, but superseded as a *set* by v2 — a confirmatory freeze is a paired comparison at a fixed seed packet, and mixing runs would make the margins incomparable. |
| The v0.37.0 tag and release notes | **Not retracted.** They describe what shipped. This erratum is the correction, and both remain readable. |

## What replaces it

[`docs/design/v0_37c_confirmatory_freeze_v2.md`](../design/v0_37c_confirmatory_freeze_v2.md)
— all five cases rerun on a **fresh seed packet** (`13, 17, 19, 23, 29`,
disjoint from v1's), with C-5's semantics repaired.

The repaired C-5 measures `R_{c·ν}(u)` against `R_ν(u)`, with the rescaled
parameter read from `execution.transformed_parameters`. Its derivation is
`|c − 1|·ν·‖u_xx‖∞`, exact at ratio `1.000000` on every seed.

## Consequences beyond the numbers

**C-5's declared operator family changed** from `scalar_multiplier` to
`identity`. The claim under test is that rescaling `ν` leaves the residual
unchanged; measurement violates it. **No benchmark case now exercises
`scalar_multiplier` end to end** — a coverage loss recorded rather than hidden.

**A structural rule was added.** `ProblemInstanceSpec` now refuses a name
appearing in both `parameters` and `coefficient_fields`. C-5 had `nu` in both,
which is two declarations of one quantity with no rule about which an executor
should read. The scalar is now `nu_baseline`.

## Historical record

Every artifact is retained: the v0.37.0 tag, its release notes, the readiness
doc, v1 of the confirmatory freeze, and all three pilot runs including the two
that blocked. Nothing was edited to make the record look cleaner.

An erratum is the correction. Deleting the thing it corrects would leave nothing
for it to be about.
