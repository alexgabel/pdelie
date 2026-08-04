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
