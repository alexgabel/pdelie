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

---

# Appendix C — Confirmatory replay, run `31326189317`

**Outcome: Gate F remains open because the confirmatory replay's gate population
violated the frozen derivative-order scope.**

Dispatched against `5929c10e` (main, post-`#174`). Three runners, all initialized.

## 1. What succeeded

**All three requested runners initialized and emitted artifacts.** The
pre-dispatch matrix validator passed in CI for the first time, confirming every
cell exists before any runner started.

| runner | role |
|---|---|
| `macos-14` py3.12.10 | platform_comparison |
| `ubuntu-22.04` py3.12.10 | platform_comparison |
| `ubuntu-22.04` py3.12.13 | patch_comparison |

**Linux 3.12.10 vs 3.12.13 was bitwise identical on all 345 compared numeric
values.** Zero differing bits. Python patch drift is not load-bearing, now
measured on the corrected harness rather than the superseded one.

**Exact-discrete fields agreed across all three runner pairs.** Zero mismatches.

**F-10 held.** All four frozen files — the scope artifact, the amended freeze,
and both scripts — were SHA-256 verified unchanged after execution. The run was
evaluated against the specification it began with.

## 2. Why the gate does not close

**Ten `d = 4` rows were incorrectly labelled `gate_evidence`.**

The `order=` metadata was threaded into the `deriv_ref_*` row constructors by
pattern substitution. It matched the `floor_regime` and `none_kind` call sites
and **missed the `signal_regime` ones**, which therefore emit
`derivative_order: None`.

F-4 then accepted them. Its check was effectively
`derivative_order in {None, 1, 2, 3}`, and `None` was read as *"not
order-parameterised, therefore in scope"* — true for the `weak_*` family, false
here.

**The worst cross-platform discrepancy landed on one of the leaked rows**:
`deriv_ref_signal_regime_analytical/expx3_d4.relative_error` at `3.199e-09`.

That is not a coincidence to argue past. It is the frozen scope's exclusion of
`d = 4` doing exactly what it was written to do, on a row that should never have
been in the population.

## 3. The post-hoc in-scope figure is diagnostic only

Excluding the leaked rows gives a worst scaled difference of `1.014e-10` at
`fornberg_pathological_spacing_ratio_10_to_1e8/d3_g7.absolute_error`.

**This cannot close the gate.** Both figures sit inside the `1e-8` bound, and
that is irrelevant: the gate certifies a *population*, and this population
contained rows the v0.38b freeze explicitly disclaims. Accepting the run because
the number happens to pass would be redefining the population after seeing the
data.

## 4. A second, smaller defect — in the comparator

`compare_replay.py` displayed **`339/345`** bitwise for the Linux pair. An
independent pass over the same artifacts found **`345/345`**.

The counter is wrong: rows short-circuited by the numerical-floor branch return
before reaching it, so floor-classified values are silently excluded from the
bitwise denominator. A floor-classified value may legitimately be excluded from
F-7's scaled-difference statistic, but it still counts toward F-6 bitwise
identity.

**Not repaired during evaluation.** `compare_replay.py` is one of the four
F-10-fingerprinted files, and altering the instrument while reading it is what
F-10 exists to prevent.

## 5. Criteria as reported, and what that reporting was worth

| | reported | actual standing |
|---|---|---|
| F-1 runners initialized | PASS | PASS |
| F-2 artifacts uploaded | PASS | PASS |
| F-3 row-key population | PASS | population *identical across runners*, but not the frozen one |
| **F-4 no gate row outside d 1–3** | **PASS** | **VACUOUS — 10 leaked rows** |
| F-5 exact_discrete agrees | PASS | PASS |
| F-6 patch drift bitwise | PASS | PASS (345/345, independently verified) |
| F-7 cross-platform ≤ 1e-8 | PASS | measured on a wrong population |
| F-8 no nonfinite / missing | PASS | PASS |
| F-9 full release gate | PASS | PASS |
| F-10 nothing changed | PASS | PASS (4/4 hashes) |

Ten criteria reported PASS. One was vacuous, and it invalidated two others.

## 6. The engineering lesson

This is the **second** appearance of one defect class: scope metadata repaired
by pattern matching rather than originating in typed data.

The first was `_ORDERS = (1, 2, 3, 4)` swept on the harness's own authority. The
repair threaded `order=` through call sites with a regex — and a regex that
matches most call sites is a repair that works most of the time.

> "By construction" must mean semantics originate in typed workload data, not
> that they are reconstructed more carefully from strings.

Deriving the order from the row key would repeat the mistake in a new costume: a
display identifier is not a data contract.

Appendices A and B are unchanged. A successful replacement replay belongs in
**Appendix D**.

---

# Appendix D — replacement confirmatory replay (run `31328966332`)

**Outcome: Gate F CLOSES.** All thirteen criteria pass on measurements, with one
post-run correction to analysis code disclosed in §D6.

Appendices A, B and C are unchanged. C records why the previous attempt failed;
it is not revised, and this appendix does not replace it.

## D1. Provenance

| | |
|---|---|
| run | [`31328966332`](https://github.com/alexgabel/pdelie/actions/runs/31328966332) |
| commit | `8195c5f` — PR #175 merged to `main` |
| dispatched | 2026-08-09T18:24:55Z |
| seeds | `13,17,19,23,29` — the frozen packet, **unchanged** |
| phase | `confirmatory` |
| runners | the three frozen cells; `validate-matrix` passed before dispatch |
| runs dispatched | **one** |

Seeds were deliberately not resampled. The correction between C and D was an
instrumentation and population-classification fix, not a new statistical
sample-selection exercise, so changing the packet would have confounded the two.

## D2. Population — the criterion that failed in Appendix C

| runner | rows | gate | exploratory | gate rows by order |
|---|---:|---:|---:|---|
| `Darwin/arm64-py3.12.10` | 286 | 229 | 57 | `{1: 57, 2: 57, 3: 57, None: 58}` |
| `Linux/x86_64-py3.12.10` | 286 | 229 | 57 | `{1: 57, 2: 57, 3: 57, None: 58}` |
| `Linux/x86_64-py3.12.13` | 286 | 229 | 57 | `{1: 57, 2: 57, 3: 57, None: 58}` |

Every runner matches [`gate_f_expected_rows.json`](../../configs/gate_f_expected_rows.json)
by **set equality**, not by count. The 58 `null`-order gate rows are exactly the
`weak` (39), `grid` (15) and `reference_kind` (4) workloads — families *declared*
order-free, which is what makes F-4a a real check rather than a restatement of
F-4's blind spot.

The ten `deriv_ref_signal_regime_*` rows at `d = 4` that leaked into run
`31326189317`'s gate population now classify as exploratory. They are still
emitted and still retained.

## D3. Results

| pair | isolates | gate rows | discrete | metric | signal | floor | bitwise | **worst scaled diff** |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| macOS/3.12.10 vs Linux/3.12.10 | platform | 229 | 0 | 0 | 76 | 249 | 122/325 | **`4.168e-10`** |
| macOS/3.12.10 vs Linux/3.12.13 | platform + patch | 229 | 0 | 0 | 76 | 249 | 122/325 | **`4.168e-10`** |
| Linux/3.12.10 vs Linux/3.12.13 | Python patch | 229 | 0 | 0 | 76 | 249 | **325/325** | **`0.000e+00`** |

Worst cross-platform value: `4.168e-10` on
`fornberg_pathological_spacing_ratio_10_to_1e8/g7_d3:absolute_error` — the
pathological grid at spacing ratio `1e8`, which is where the derivation in the
freeze §4 predicted the largest amplification. It is **24× inside** the `1e-8`
bound and lands on an in-scope `d = 3` row, not a leaked one.

Patch drift is **exactly zero** across all 325 numeric comparisons, with zero
bitwise differences — the bitwise identity the freeze requires, not a tolerance.

## D4. Criteria

| | criterion | result |
|---|---|---|
| F-1 | all runners initialize | PASS — 4/4 jobs |
| F-2 | artifacts uploaded | PASS — 3/3 |
| F-3 | row set **equals** the frozen manifest | PASS — set equality, all runners |
| F-3a | partition equals the frozen partition | PASS — 229/57, all runners |
| F-4 | no gate row outside orders 1–3 | PASS — **non-vacuously**; 171 gate rows carry an order |
| F-4a | every `null` order in a declared order-free family | PASS — 58/58 |
| F-5 | `exact_discrete` fields agree exactly | PASS — 0 mismatches |
| F-6 | patch pair bitwise identical | PASS — 325/325, 0 different |
| F-7 | cross-platform ≤ `1e-8` | PASS — `4.168e-10` |
| F-8 | no non-finite metric, no missing provenance | PASS — 0 and 0 |
| F-9 | full release gate, no `--skip-build` | PASS — all six sub-gates |
| F-10 | no threshold or workload definition changed after dispatch | PASS — see §D6 |
| F-11 | independent audit passes | PASS — on-runner and locally |

**Why F-4 is non-vacuous here.** In Appendix C it passed over a population where
the rows it targeted carried `null`. Here 171 of 229 gate rows carry an explicit
order in `{1, 2, 3}`, and the 57 `d = 4` rows are classified exploratory *by
construction* — a `ReplayRowSpec` with `derivative_order=4` and
`gate_use="gate_evidence"` cannot be built. The criterion now has a population it
could fail on.

## D5. Tolerances — unchanged

`1e-8` and `0.0`, exactly as derived in the amended freeze §4. **No tolerance was
widened, narrowed, or reinterpreted.** The observed values sit inside the bounds
rather than the bounds having been fitted to them.

## D6. Disclosure — one post-run correction to analysis code

After the run, verifying the reported accounting revealed that
`compare_replay.py` counted `not_comparable = 1049` where
`signal + floor + not_comparable` should equal the 325 comparisons made. The
counter was incrementing once per *row/field slot that held no value* — 229 gate
rows × 6 numeric fields − 325 = 1049 — conflating "we could not compare these two
values" with "there were no two values". That is the conflation defect, inside
the counter set introduced in PR #175 to end conflation.

It was corrected by splitting `fields_absent` out of `not_comparable`, and both
accounting identities are now **executed** rather than described.

**This is disclosed rather than absorbed**, because it is a change to analysis
code made after seeing results. Three things bound it:

1. It touches **no threshold and no workload definition**, so F-10 holds.
2. The raw measurement artifacts were **not regenerated**. The comparator was
   re-run over the same three uploaded JSON files.
3. Every gate-relevant statistic was compared before and after and is
   **bit-identical** — `paired_rows`, both mismatch lists, all bitwise counters,
   `signal`, `floor`, `worst_scaled_difference` and its location. The corrected
   counter is diagnostic and appears in no criterion.

A reader who distrusts the correction can reach the same verdict from the
Appendix C-era comparator: the numbers deciding F-5 through F-8 are unchanged.

## D7. What closes, and what does not

Gate F closes. That licenses `v0.38.0rc1`, and no more:

* The four-class portability taxonomy is **corroborated on three platform/patch
  cells**, not established in general.
* `d = 4` remains **outside** the supported scope. The 57 exploratory rows are
  evidence about future work, not about this release.
* macOS/arm64 at CPython 3.12.11+ remains an **impossible cell**; the 2×2 corner
  was never measured and is not claimed.
* The `1e-8` bound is derived for the workloads in scope. It is not a general
  claim about PDELie's cross-platform reproducibility.
