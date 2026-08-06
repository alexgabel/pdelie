# v0.38 — Gates A–F

**Measured on `Darwin/arm64`, CPython 3.12.13, NumPy 2.5.1, PySINDy 2.1.0.**

Run after the v0.38 feature arc (v0.38e, a, b, c, d) and the public API freeze.

**Five gates pass. Gate F does not, and that is why the next tag is `b1` and not
`rc1`.**

---

## Gate A — identity and environment

| | |
|---|---|
| Python | 3.12.13 |
| Platform | `Darwin/arm64` |
| NumPy | 2.5.1 |
| PySINDy | 2.1.0 |
| pdelie | 0.38.0a1 |

**PASS.** Matches the modern-runtime line and reproduces the CI mypy fingerprint
of 147 errors in 29 files.

---

## Gate B — contract semantics

Every sub-phase followed hypothesis freeze → pilot → confirmatory freeze, with
the freeze written before any runtime code.

| sub-phase | hypothesis | pilot | confirmatory | blocked runs |
|---|---|---|---|---:|
| v0.38e | ✓ | ✓ | signed | **1** |
| v0.38a | ✓ | ✓ | signed | 0 |
| v0.38b | ✓ | ✓ | signed | **1** |
| v0.38c | ✓ | ✓ | signed | 0 |
| v0.38d | ✓ | ✓ | signed | **2** |

**PASS.** All five confirmatory freezes signed; all blocked runs retained
unedited.

**Four pilot blocks across the arc**, each catching a specification defect
before it shipped:

- **v0.38e** — a legal-pairs table advertising an outcome nothing could produce.
- **v0.38b** — FN-12 requiring exact `1.0` from a grid whose spacings are not
  bitwise constant.
- **v0.38d ×2** — the error-reporting layer committing the error-reporting
  defect it was written to prevent, twice, on the same criterion.

---

## Gate C — adversarial values

Nine refusals probed directly; **9/9 fired**.

| input | outcome |
|---|---|
| duplicate coordinates | refused |
| unsorted coordinates | refused |
| NaN coordinate | refused |
| stencil smaller than `derivative_order + 1` | refused |
| stencil over the piloted cap | refused |
| unrecognised quadrature rule | refused |
| weights that cannot integrate `1` | refused |
| single-point comparison with no declared scale | refused |
| reference supplied under `reference_kind = none` | refused |

**PASS.** Every one is a refusal rather than a repair or an approximation.

---

## Gate D — manufactured / analytical oracles

| | |
|---|---|
| Fornberg accuracy oracle | 28 passed, 1 skipped |
| Operator-form identity oracle | included above |
| Oracle-marker registry | 14 passed |
| `load_bearing_analytical` population | **6 tests** (was **0** before v0.38) |

**PASS.** The registry was empty and every check over it vacuous at v0.38
day-zero; it now has two genuine consumers, each with a declared
`manufactured_solution` oracle whose write-up exists on disk and is asserted to.

---

## Gate E — released numbers unmoved

**125 / 125 bitwise identical.**

Every v0.37c confirmatory measurement (C-1, C-2, C-3, C-5, C-6 × 5 α × 5 seeds)
recomputed on HEAD and compared against pre-v0.38 `main`. Not "agree to
tolerance" — bitwise.

**PASS.** v0.38 corrected two declaration defects and moved no released number.

---

## Gate F — cross-platform replay: **NOT MET**

The only replay run recorded is at `30a5e1b`, the v0.37.1 replay-lane commit —
**17 commits before HEAD**. No v0.38 code has ever been replayed.

### What is owed

| freeze | `exact_discrete` | `tolerance_numeric` | replay owed |
|---|:--:|:--:|:--:|
| v0.38a | ✓ | — | no |
| v0.38b | ✓ | **✓** | **yes** |
| v0.38c | ✓ | **✓** | **yes** |
| v0.38d | — | — | yes (timing is `platform_specific_diagnostic`) |
| v0.38e | ✓ | — | **yes** |

v0.38b's conditioning numbers and v0.38c's quadrature errors are
`tolerance_numeric` and are the ones a replay must actually check. The
`exact_discrete` parts — refusals, vocabulary membership, identity namespacing,
reason classification — are *expected* to agree exactly, which is an argument
and not a measurement.

### A replay has now been dispatched — and closes only part of this gate

Run `30930069491` was dispatched against `10f8a13` (main, post-API-freeze). It is
the first time any v0.38 code has been replayed.

**What it covers.** `benchmark_platform_replay.yml` runs
`run_admissibility_benchmark`, which now includes **C-7 and C-8** alongside the
v0.37c cases. So it replays the v0.38e benchmark additions and re-checks the 125
released measurements on a second platform.

**Result: passed, and the numbers agree.** 175 paired measurements. All seven
`exact_discrete` fields identical across platforms, zero mismatches; C-8 blocked
on both, all 25 rows. In the signal regime the worst relative gap is
**`4.485e-15`**. Fifty measurements sit at the spectral floor and their relative
gaps are deliberately **not** computed — quoting one would reproduce the defect
the v0.38d pilot blocked on twice. Full record:
[`v0_38_platform_replay.md`](../design/v0_38_platform_replay.md).

**What it does not cover.** v0.38b's conditioning numbers and v0.38c's quadrature
errors are not produced by the benchmark, so this lane never touches them — and
they are the `tolerance_numeric` values most in need of a replay, since both were
frozen from single-platform pilots. Closing Gate F fully requires extending the
lane to exercise them.

Recorded here rather than left for a reader to infer from a green check: a lane
passing is not the same as a gate closing, and the difference is exactly the kind
of thing this arc has been catching.

### Why this is not a defect

Gate F failing is the reason the next tag is **`v0.38.0b1`** rather than
`rc1`. Your own sequencing puts `b1` at "after v0.38a–d land and the public API
is frozen, **if broader integration testing remains**" — and broader integration
testing is precisely what remains.

`rc1` requires all of A–F. It is not cut until a replay runs.

---

## Summary

| Gate | Result |
|---|---|
| A — identity / environment | **PASS** |
| B — contract semantics | **PASS** (4 pilot blocks, all caught defects) |
| C — adversarial values | **PASS** (9/9) |
| D — analytical oracles | **PASS** (registry 0 → 6) |
| E — released numbers | **PASS** (125/125 bitwise) |
| F — cross-platform replay | **NOT MET** — no v0.38 replay has run |

**Next tag: `v0.38.0b1`.** `rc1` after Gate F.
