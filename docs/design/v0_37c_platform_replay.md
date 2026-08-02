# v0.37c — Platform Replay: macOS vs Linux

**Run:** GitHub Actions `benchmark-platform-replay` #30724561952, 2026-08-02.
**Result: the qualitative separation is preserved cross-platform, and both
platforms fall within the v2 confirmatory tolerances.**

---

## 1. What was compared

| | macOS | Linux |
|---|---|---|
| Platform | `Darwin/arm64` | `Linux/x86_64` |
| Python | 3.12.10 | 3.12.13 |
| NumPy | 2.5.1 | 2.5.1 |
| Seeds | `13, 17, 19, 23, 29` | `13, 17, 19, 23, 29` |

**Both sides ran in the same lane**, rather than comparing Linux against stored
macOS numbers. A stored result carries the toolchain that produced it, and a
difference would then be unattributable between platform and drift.

The seed packet is v0.37.1's frozen one. A paired comparison needs the same
draws on both sides.

275 measurements per platform: 5 cases × (6 pilot + 5 confirmatory) α × 5 seeds.

---

## 2. Classification — the claim that matters

**Exact agreement, both phases, every case, every α, every seed.**

Each measurement is classified against the frozen boundary `T = 1.0e-06`: below
is *valid*, above is *invalid*. Not one measurement lands on a different side on
the two platforms, and every one matches its expected classification — including
the `α = 0` control, where the profile-dependent obstruction cases collapse to
the valid case as they must.

This is the property the benchmark exists to establish, and it is
platform-independent.

---

## 3. Numeric agreement — reported in two populations, not one

Collapsing these into a single number would mislead, so they are separate.

| Population | Points | Statistic | Pilot | Confirmatory |
|---|---:|---|---|---|
| **Signal** (> `1e-9`) | 80 / 75 | worst **relative** difference | `7.148e-14` | `1.618e-13` |
| **Floor** (≤ `1e-9`) | 70 / 50 | worst **absolute** difference | `1.554e-15` | `1.193e-15` |

**Why two populations.** C-1 and C-2 sit at the spectral floor — `1.31e-14` on
macOS against `1.38e-14` on Linux. Quoted as a *relative* difference that is
`5.5e-02`, which sounds alarming and means nothing: it is the difference between
two roundoff accumulations, both of which are numerically zero. The meaningful
statistic there is the **absolute** difference, which is `1.19e-15` — below the
floor itself.

The cases carrying actual signal — C-3, C-5, C-6 — agree to **1e-13 relative**,
which is machine precision through a spectral-derivative chain.

A single headline number for this comparison would have been `7.97e-02`, and it
would have been wrong about both populations at once.

---

## 4. Tolerance — both platforms against the frozen boundary

| Phase | | macOS | Linux | requirement |
|---|---|---|---|---|
| Pilot | max valid | `1.371e-14` | `1.460e-14` | `< 1e-06` ✓ |
| Pilot | min invalid | `6.148e-03` | `6.148e-03` | `> 1e-06` ✓ |
| Confirmatory | max valid | `1.329e-14` | `1.435e-14` | `< 1e-06` ✓ |
| Confirmatory | min invalid | `3.074e-03` | `3.074e-03` | `> 1e-06` ✓ |

Both platforms sit eleven orders clear of the boundary in both directions.

### The binding margin is Linux's

| Phase | macOS | Linux | **binding** |
|---|---|---|---|
| Pilot | `4.484e+11` | `4.211e+11` | **`4.211e+11`** |
| Confirmatory | `2.312e+11` | `2.142e+11` | **`2.142e+11`** |

Linux's margin is ~7% smaller because its valid-case floor is marginally higher.
**The binding number for the release is Linux's `2.142e+11`**, not the macOS
`2.312e+11` the v2 freeze quotes — the same discipline applied at v0.36, where
the binding residual margin moved from macOS's 22.1× to Linux's 19.6×.

The v2 freeze is not amended: its numbers were correct for the platform it
measured, and this document is the cross-platform record. Anyone quoting a
margin should quote the binding one.

---

## 5. Bit-identity is *not* claimed

**8 of 125 confirmatory measurements are bit-identical across platforms.**

That is expected and is not a defect. Spectral derivatives route through FFT and
BLAS, whose summation order is not fixed across architectures. Asserting
bit-equality here would be the v0.35a mistake — a claim that can only fail for
reasons unrelated to what it purports to test.

Per `docs/design/CROSS_PLATFORM_PORTABILITY_CLASSES.md`, the classification is
`qualitative_invariant` and the measurements are `tolerance_numeric`. Neither is
`exact_discrete`, and this document asserts neither as such.

`scientific_result_hash` is therefore **not** compared: it covers floating-point
content, so it differs wherever any measurement differs, and its disagreement
carries no information beyond what §3 already reports.

---

## 6. Gate 4

**PASS — measured.**

Upgraded from "PASS with a stated limit". The limit was that every v0.37c number
came from macOS/arm64 and the eleven-order margin argument was an argument
rather than a measurement. It is now a measurement:

- classifications agree exactly on both phases;
- signal-case numbers agree to `1.6e-13` relative;
- both platforms fall within the frozen tolerances with eleven orders to spare.

**No discrepancy exceeded a v2 tolerance**, so no v0.38-blocking finding is
recorded.

### What this does not establish

Two platforms, not all platforms. Both ran NumPy 2.5.1 and CPython 3.12; a
different BLAS, a different NumPy major, or a non-x86/arm architecture is
unmeasured. The lane is `workflow_dispatch` and can be pointed at any runner the
project adds.
