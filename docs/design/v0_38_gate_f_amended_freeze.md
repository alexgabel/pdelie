# v0.38 Gate F — Amended Confirmatory Freeze

**Status:** frozen. Written **before** any further replay dispatch.

Supersedes the criteria in
[`v0_38_gate_f_closure_plan.md`](v0_38_gate_f_closure_plan.md) §3 and §6. The
plan itself is retained unedited; its §2 workload definitions stand except for
the scope restriction recorded below.

**Reconnaissance disclosure.** Run `31278210299` is treated as a **pilot**. It
may inform the *scale* of a tolerance. It may **not** both choose a threshold and
declare that threshold passed, and no number below was read off it as a pass
mark — see §4 for how the tolerance was actually derived.

---

## 1. Why an amendment was needed

The closure plan specified a gate that could not be executed as written. Three
defects, all found by running it:

| | defect |
|---|---|
| §3 | the 2×2 corner requires `macos-14 × CPython 3.12.13`, which **does not exist** — macOS/arm64 has no 3.12.11+ |
| §2 | the harness swept derivative order **4**, which the v0.38b freeze explicitly disclaims; 5 of 7 disagreements were there |
| §6 | criterion 2 required the gap to be within "the frozen bound" — **no cross-platform bound was ever frozen**, which is why Gate F is open |

None is a defect in PDELie. All three are defects in the gate.

---

## 2. Frozen scope

Machine-readable in [`configs/gate_f_replay_scope.json`](../../configs/gate_f_replay_scope.json),
consumed by **both** `replay_workloads.py` and `compare_replay.py`. Neither
keeps its own list; the harness inventing its own orders is what produced the
d=4 sweep.

| | |
|---|---|
| gate derivative orders | **1, 2, 3** — matching the v0.38b freeze verbatim |
| exploratory orders | **4** — emitted, labelled `outside_frozen_scope`, `not_used_for_gate_decision` |
| gate rows per runner | **239** (derived from the manifest, not asserted) |
| exploratory rows | 47 |

The d=4 rows are **retained**. Deleting a real measurement to make a gate pass is
the wrong repair; labelling it so it can never be mistaken for gate evidence is
the right one.

**The "286 rows" invariant is deliberately not preserved.** Removing d=4 from the
gate population changes the count, and an asserted count would have hidden that.

---

## 3. Frozen runner matrix

```yaml
- os: macos-14      python: 3.12.10   role: platform_comparison
- os: ubuntu-22.04  python: 3.12.10   role: platform_comparison
- os: ubuntu-22.04  python: 3.12.13   role: patch_comparison
```

Each pair isolates **one** variable, which the 2×2 did not:

| pair | isolates | criterion |
|---|---|---|
| macOS/3.12.10 vs Linux/3.12.10 | platform | cross-platform |
| Linux/3.12.10 vs Linux/3.12.13 | Python patch | patch drift |

**No floating aliases.** A confirmatory portability gate pins exact patches; a
floating `3.12` silently changes what was measured between runs.

`scripts/validate_runner_matrix.py` checks every tuple against the live
`actions/python-versions` manifest and fails **before** dispatch.

---

## 4. Frozen tolerances, and how they were derived

**Primary statistic:** `scaled_difference = |left − right| / reference_scale`,
where `reference_scale` is the characteristic magnitude of the quantity over its
domain — the definition v0.38d froze.

**Secondary, diagnostic only:** `|left − right| / max(|left|, |right|)`, labelled
`unstable_near_numerical_floor` and `not_used_for_gate_decision`. This produced
the `2.478e-01` headline from two absolute errors of `3.0e-06` and `4.0e-06`.

### Cross-platform tolerance: `1e-8`

**Derived, not fitted.** The quantities compared are `float64` results of a
Fornberg weight computation followed by a dot product over an `n`-node stencil.
Two IEEE-754 platforms differ only in summation order and FMA contraction, so
the difference is bounded by the accumulated rounding of that dot product:
`O(n · eps · scale)`. With the frozen cap of `n = 13`, that is
`13 × 2.22e-16 ≈ 2.9e-15` relative to scale.

The grids in scope reach spacing ratio `1e8`, where the weight magnitudes
amplify this by up to the condition number of the stencil. The v0.38b pilot
measured `max|w|` growth of ~`4e2` at ratio ~`3e2`; extrapolating
conservatively to `1e8` gives an amplification bound near `1e6`.

`2.9e-15 × 1e6 ≈ 2.9e-9`, rounded up to **`1e-8`**.

The pilot's in-scope worst was `1.014e-10`, i.e. **~100× inside** this bound.
That agreement is *corroboration*, not the derivation — the bound comes from the
arithmetic and would stand had the pilot never run.

### Patch-drift tolerance: `0.0` — exact

Same platform, same architecture, same libm, same BLAS. A CPython patch release
changes no floating-point semantics, so the correct expectation is **bitwise
identity**, not a tolerance.

The pilot measured exactly that: `0.000e+00` across 410 numeric comparisons.
Setting a nonzero tolerance here would accept a real regression.

---

## 5. Failure labels

`impossible_runner_cell`, `population_mismatch`, `out_of_scope_gate_row`,
`discrete_disagreement`, `cross_platform_tolerance_exceeded`,
`patch_drift_not_bitwise`, `nonfinite_metric`, `missing_provenance`,
`unlabelled_artifact`.

---

## 6. Pass criteria — all ten required

| | criterion |
|---|---|
| **F-1** | all requested runners initialize successfully |
| **F-2** | all expected artifacts are uploaded |
| **F-3** | all runners emit exactly the frozen row-key population |
| **F-4** | no gate row lies outside derivative orders 1–3 |
| **F-5** | every `exact_discrete` field agrees exactly |
| **F-6** | Linux 3.12.10 vs 3.12.13 is **bitwise identical** |
| **F-7** | macOS vs Linux `scaled_difference` ≤ `1e-8` |
| **F-8** | no non-finite metric, no missing provenance value |
| **F-9** | the full release gate passes **without** `--skip-build` |
| **F-10** | no threshold or workload definition changed after the run began |

---

## 7. Artifact paths

| | |
|---|---|
| per-runner | `gate_f_replay.json`, `replay.json` |
| comparison | appended to `v0_38_platform_replay.md` as **Appendix C** |
| scope | `configs/gate_f_replay_scope.json` |

Appendices A and B are **not** replaced. A record showing only the run that
passed is a selection-effect document.

---

## 8. The no-widening rule

**A threshold may not be widened after viewing a confirmatory replay.**

If a criterion fails, the record names the runner pair, workload, row key, field,
portability class, observed value and frozen bound — and the tolerance stays
where it is. Changing it requires another explicit amendment and another fresh
replay, in a separate PR.

---

## 9. Signature

Frozen before dispatch, with tolerances derived from the arithmetic rather than
read off the pilot, and with the pilot's numbers recorded as corroboration.
