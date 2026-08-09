# v0.38 — Cross-Platform Replay

**Run `30930069491`**, dispatched against `10f8a13` (main, post-API-freeze).
**The first replay of any v0.38 code.**

| | macOS | Linux |
|---|---|---|
| platform | `Darwin/arm64` | `Linux/x86_64` |
| Python | 3.12.10 | 3.12.13 |
| NumPy | 2.5.1 | 2.5.1 |

The two Python patch versions differ. That is disclosed rather than corrected:
agreement across two patch releases is a slightly **stronger** result than
agreement on one, and pretending the environments were identical would misstate
what was compared.

Confirmatory grid, seeds `{13, 17, 19, 23, 29}`, **175 paired measurements**.

## `exact_discrete` — all agree exactly

Seven fields, 175 measurements each, **zero mismatches**:

`outcome`, `runtime_path`, `expected_operator_family`,
`coaction_consistency_status`, `coaction_diagnosis`, `equation_form`,
`is_deliberate_obstruction`.

Every classification, every diagnosis, every derived equation form is identical
across platforms. **C-8 is blocked on both, all 25 rows** — the ambiguous
parameter target is refused identically.

## `tolerance_numeric` — agreement to `4.5e-15`

| | |
|---|---:|
| numeric measurements | 150 |
| **at the spectral floor** (`< 1e-12`) | **50** |
| in the signal regime | 100 |
| **worst relative gap (signal regime)** | **`4.485e-15`** — at C-6, α=0.025, seed 23 |
| bitwise identical | 25 / 150 |

**Relative gaps are not computed for the 50 floor measurements.** A relative
difference between two numbers that are both `~1e-14` is meaningless, and
quoting one would reproduce exactly the defect the v0.38d pilot blocked on twice.
This is the signal-versus-floor discipline applied to the replay itself.

**Bit-identity is neither claimed nor achieved** — 25 of 150 match bitwise, which
is what a spectral-derivative chain through FFT and BLAS should produce on two
different architectures.

## What this closes, and what it does not

**Closes:** the benchmark half of Gate F. The v0.37c cases and the v0.38e
additions (C-7, C-8) are now replayed, and the eleven-order margins in the
v0.37c confirmatory freeze are confirmed on a second platform rather than argued
from.

**Does not close:** `benchmark_platform_replay.yml` runs
`run_admissibility_benchmark` only. **v0.38b's conditioning numbers and v0.38c's
quadrature errors are never touched by it** — and those are the
`tolerance_numeric` values most in need of a replay, since both were frozen from
single-platform pilots.

Gate F remains **NOT MET**. A lane passing is not the same as a gate closing.
Extending the lane to exercise the v0.38b/c numerics is the remaining work
before `rc1`.

---

# Appendix B — Extended lane, run `31278210299`

Dispatched against `7c78abc` (main, at the `v0.38.0b1` tag). Four runners
requested; **three completed**. 286 rows each.

## Outcome: **Gate F does not close.**

Three reasons, none of which is a defect in the library. All three are defects in
the closure plan or in the harness built from it.

## 1. The 2×2 Python-patch corner is not constructible

`macos-14 py3.12.13` failed at `actions/setup-python`:

```
The version '3.12.13' with architecture 'arm64' was not found for macOS 14.8.7.
```

Checked against the upstream manifest: **macOS/arm64 stops at 3.12.10.**
3.12.11, 3.12.12 and 3.12.13 are Linux-only.

| | 3.12.10 | 3.12.13 |
|---|:-:|:-:|
| macOS/arm64 | available | **does not exist** |
| Linux/x86_64 | available | available |

Closure-plan §3 specified a cell that cannot exist on hosted runners, and no
re-run will produce it.

**The three runners that did complete are a better design than the 2×2 was.**
They isolate one variable each:

- `macOS/3.12.10` vs `Linux/3.12.10` — matched patch, **platform isolated**
- `Linux/3.12.10` vs `Linux/3.12.13` — matched platform, **patch isolated**

The original 2×2 had two mixed cells and would have answered the patch-drift
question less cleanly.

## 2. Python patch drift is **not** load-bearing — established

| pair | paired | discrete | signal | bitwise | worst rel gap |
|---|---:|---:|---:|---:|---:|
| Linux/3.12.10 vs Linux/3.12.13 | 286 | 0 | 105 | **410** | **`0.000e+00`** |

Same platform, different patch: **every value bitwise identical**. This settles
§3's question definitively, and more cleanly than the specified corner could
have.

**Every `exact_discrete` field agrees across all three runners** — zero
mismatches across 286 rows × 3 pairs.

## 3. The workloads probe outside the frozen scope

`scripts/replay_workloads.py` sweeps `_ORDERS = (1, 2, 3, 4)`. The v0.38b
confirmatory freeze states, verbatim:

> **No claim beyond derivative orders 1–3**, 1-D, on a declared axis.

**Five of the seven cross-platform disagreements above `1e-9` are at `d = 4`** —
a regime for which nothing was ever frozen. Measuring there and reading the
result as a Gate F signal compares against a bound that does not exist.

| scope | signal comparisons | worst rel-between-errors | worst difference / scale |
|---|---:|---:|---:|
| all orders, as run | 99 | `2.478e-01` | `2.691e-06` |
| **frozen scope, `d ≤ 3`** | 70 | `3.579e-03` | **`1.014e-10`** |

## 4. The comparison statistic is unstable, and criterion 2 cites a bound that does not exist

`compare_replay.py` computes the **relative difference between two error
magnitudes**. When both are tiny truncation errors, that ratio is unstable — it
is the floor problem one level up, and it is what produces the `2.478e-01`
headline from two absolute errors of `3.0e-06` and `4.0e-06`.

The stable statistic is the difference measured against the **quantity's scale**,
which is what v0.38d froze for exactly this reason. Under it, the worst
in-scope disagreement is `1.014e-10`.

Separately, closure-plan §6 criterion 2 requires the gap to be within "the frozen
bound × safety factor". **No cross-platform bound was ever frozen for Fornberg
conditioning** — the v0.38b pilot was single-platform, which is the entire reason
Gate F is open. The criterion refers to a number that does not exist.

## 5. What this run does establish

- Patch drift is not load-bearing (§2 above) — a real result, and the harder half
  of what §3 was designed to answer.
- All `exact_discrete` classifications agree across platforms, 286 rows × 3 pairs.
- Inside the frozen `d ≤ 3` scope, cross-platform agreement is `1.014e-10` by the
  stable statistic, at spacing ratio `1e8` — the most extreme corner measured.

## 6. Amendments required before a re-run can close Gate F

1. **§2** — restrict the workload orders to `d ≤ 3`, matching the frozen scope.
   Probing `d = 4` is legitimate research and is not evidence for a gate.
2. **§3** — replace the 2×2 with the three-runner design above, and record that
   macOS/arm64 has no 3.12.11+.
3. **§6 criterion 2** — name a bound that exists. Either freeze a cross-platform
   tolerance from this run's in-scope numbers, or state the criterion in terms of
   the `difference / reference_scale` statistic with a bound derived from it.
4. **`compare_replay.py`** — report `difference / reference_scale` as the primary
   statistic, keeping relative-between-errors as a secondary diagnostic clearly
   labelled as unstable near the floor.

Gate F remains **NOT MET**. It is not met for reasons that were discoverable only
by running the lane, which is what the lane is for.
