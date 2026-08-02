# V0.37.1 Release Readiness

## 1. Release Target

- package version: `0.37.1`
- git tag: `v0.37.1`
- release decision: `v0_37_1_c5_semantic_repair`
- support matrix: unchanged from
  [`support_matrix.v0_37.json`](../specs/support_matrix.v0_37.json) except the
  C-5 entries noted below

**Git-tag-only.** Do not publish to TestPyPI or PyPI for `v0.37`. Publication
remains deferred to `v1.0`.

A patch release: no new feature, no new `summary_type`, no schema change.

## 2. What it fixes

See [`V0_37_C5_ERRATUM.md`](V0_37_C5_ERRATUM.md) for the full account.

**v0.37.0 did not test parameter-only obstruction correctly.** Benchmark case
C-5 declared a rescale of the *parameter* and its runner performed a rescale of
the *state*. `execute_bundle` computed the declared result correctly; the
benchmark discarded it.

| | v0.37.0 | v0.37.1 |
|---|---|---|
| What C-5 measured | `R(cu)` vs `c·R(u)` — a state rescale | `R_{c·ν}(u)` vs `R_ν(u)` — a parameter rescale |
| Derivation | `\|c²−c\|·‖u·u_x‖∞` | `\|c−1\|·ν·‖u_xx‖∞` |
| Agreement | exact — **for the wrong transformation** | exact, ratio `1.000000` every seed |
| Declared operator | `scalar_multiplier` | `identity` |

## 3. Gates

| Gate | Status |
|---|---|
| 1 — C-5 consumes its declared action | **PASS.** Reads `execution.transformed_parameters`; a test asserts it still does, so a repair that deleted the manual rescale without wiring the executor would not pass. |
| 2 — `parameters ∩ coefficient_fields = ∅` | **PASS.** Enforced in `ProblemInstanceSpec.__post_init__`. |
| 3 — Confirmatory freeze v2, fresh seeds, five cases | **PASS.** Seeds `13, 17, 19, 23, 29`; PS-1/2/3 evaluated de novo. |
| 4 — Portable claims pass Linux + macOS | **PASS — measured.** Replayed on `ubuntu-22.04` and `macos-14` with this release's seed packet: classifications agree exactly, signal-case numbers to `1.6e-13` relative, both platforms within the frozen tolerances. Binding margin is Linux's `2.142e+11`. See [`v0_37c_platform_replay.md`](../design/v0_37c_platform_replay.md). |
| 5 — Historical record retained | **PASS.** v1 of the confirmatory freeze, all v0.37.0 artifacts, and pilot runs 1–3 are unedited; the pilot report's frozen prefix is SHA-256 pinned. |

## 4. Known limitations carried forward

Unchanged from v0.37.0, plus:

- **No benchmark case exercises `scalar_multiplier` end to end.** C-5 declared it
  until this release. The family remains contract-tested in the v0.37a suite.
- **Two platforms, not all platforms.** The replay covers `Darwin/arm64` and
  `Linux/x86_64`, both on NumPy 2.5.1 and CPython 3.12. A different BLAS, NumPy
  major, or architecture is unmeasured.
- **Bit-identity is not claimed and is not achieved** — 8 of 125 confirmatory
  measurements match bitwise, which is what a spectral-derivative chain through
  FFT and BLAS should produce. The classification is the invariant; the numbers
  are `tolerance_numeric`.

## 5. Process note

The defect escaped every gate the arc had because every gate asked whether a
*declaration* was coherent, and none asked whether the declaration matched the
*execution*. Both questions are necessary; only one was being asked.

`tests/test_benchmark_action_semantics_guard.py` asks the second. It was written
from the pattern rather than from this instance, and flagged all three of C-5's
constructs on its first run — which is the evidence that the gap was structural
rather than a one-off.

## 6. Verification

| Gate | Result |
|---|---|
| test suite | 2665 passed, 3 skipped |
| mypy | 147 errors in 29 files — baseline unchanged |
| ruff | clean |
| docs | `sphinx-build -W` clean |
| C-5 derivation | exact, ratio `1.000000` on all five seeds |
| confirmatory margin | `2.312e+11` binding |
