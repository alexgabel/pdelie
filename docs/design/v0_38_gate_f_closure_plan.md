# v0.38 Gate F — Closure Plan

**Status: frozen. Written before the extended replay lane runs.**

Gate F is `NOT MET` at `v0.38.0b1`. This document specifies what an extended
replay lane must exercise so that Gate F can be closed at `v0.38.0-rc1`. The
scope is deliberately narrow: reproduce the `tolerance_numeric` measurements
that v0.38b, v0.38c and v0.38d froze from single-platform pilots, on a second
platform, with the same signal-versus-floor discipline the existing replay
already applies.

The plan is closed to workload additions after signing. A new workload after
signing is a new plan.

## 1. What the existing replay closed, and what it did not

The lane at [`benchmark_platform_replay.yml`](../../.github/workflows/benchmark_platform_replay.yml)
runs `run_admissibility_benchmark` and produced run `30930069491` at `10f8a13`.
That lane covers v0.37c cases plus v0.38e's C-7 and C-8 — 175 paired
measurements, worst signal-regime gap `4.485e-15`.

It does **not** touch v0.38b conditioning numbers, v0.38c quadrature errors, or
v0.38d reference-vs-measured errors. Those are the `tolerance_numeric` values
most in need of a replay because both v0.38b's FN-12 amendment and v0.38c's
`n·eps·L` bound were measured on macOS/arm64 only.

## 2. Workloads owed, per sub-phase

Concrete measurement definitions from each signed confirmatory freeze.

### 2.1 v0.38b — Fornberg on nonuniform grids

Source: [`v0_38b_confirmatory_freeze.md`](v0_38b_confirmatory_freeze.md).

| Workload | Measurement | Populations |
|---|---|---|
| `fornberg_uniform_polynomial_exactness` | Off-node polynomial exactness on `formal_accuracy = n − d` stencils | 4 orders × 3 stencil sizes × 5 nodes = 60 rows |
| `fornberg_perturbed_uniform_spacing_ratio_1_to_10` | Achieved error at G-2 grids | 4 orders × 5 grids × 3 refinements = 60 rows |
| `fornberg_pathological_spacing_ratio_10_to_1e8` | Reported (not refused) error at G-5 grids | 4 orders × 8 grids = 32 rows |
| `fornberg_fn_12_uniform_spacing_ratio` | The `0.647 · n · eps` measurement — worst-observed constant across three domain spans | 5 node counts × 3 spans = 15 rows |
| `fornberg_boundary_stencils_second_order` | Boundary-adjacent stencil error against manufactured solution | 4 orders × 4 boundary positions = 16 rows |

**Total: 183 v0.38b measurements.**

Pass criterion for `tolerance_numeric`: median-of-paired-relative-error inside
signal regime under `sqrt(eps) · reference_scale` boundary; worst-paired-gap
below the frozen bound with margin ≥ 1.5× (matches the FN-12 margin the
confirmatory freeze established).

### 2.2 v0.38c — Irregular weak-form bridge

Source: [`v0_38c_confirmatory_freeze.md`](v0_38c_confirmatory_freeze.md).

| Workload | Measurement | Populations |
|---|---|---|
| `weak_constant_exactness_nonuniform_trapezoidal` | `∫₁ dx == interval_length` under trapezoidal on irregular nodes | 5 spacing ratios (1, 4, 16, 40, 79) × 3 node counts = 15 rows |
| `weak_user_supplied_validation` | Weight validation on user-supplied rules that pass/fail the constant test | 4 pass + 4 fail = 8 rows |
| `weak_linear_exactness_report` | Measured (not required) linear exactness | 5 spacing ratios × 2 window widths = 10 rows |
| `weak_overlap_declaration` | Overlap fraction on paired windows | 6 pairings = 6 rows |

**Total: 39 v0.38c measurements.**

Pass criterion for `tolerance_numeric`: constant exactness within
`n · eps · interval_length` with the confirmatory-freeze margin (50× at spacing
ratio 79); linear exactness reported but not gated.

### 2.3 v0.38d — Derivative error reference

Source: [`v0_38d_confirmatory_freeze.md`](v0_38d_confirmatory_freeze.md).

| Workload | Measurement | Populations |
|---|---|---|
| `deriv_ref_signal_regime_analytical` | `absolute_error` and `relative_error` for `analytical` reference kind, signal regime | 5 manufactured functions × 4 derivative orders = 20 rows |
| `deriv_ref_signal_regime_manufactured` | Same, `manufactured` reference kind | 5 × 4 = 20 rows |
| `deriv_ref_floor_regime` | `regime = "floor"`, error fields `None` for both kinds | 5 × 4 = 20 rows |
| `deriv_ref_none_kind` | `reference_kind = "none"`, `absolute_error = None`, present | 4 rows |

**Total: 64 v0.38d measurements.**

Timing measurements are **not** replayed. v0.38d froze
`platform_specific_diagnostic` for `runtime_seconds_median` — its variation
across platforms is a fact, not a defect, and asserting agreement would be the
v0.35a mistake.

### 2.4 v0.38a — no replay owed

The v0.38a row-mask sub-phase produces only `exact_discrete` fields per the
`V0_38_GATES_A_TO_F.md` table. Refusals, vocabulary membership, identity
namespacing, and reason classification are expected to agree exactly, which is
an argument and not a measurement. No `tolerance_numeric` workload.

### 2.5 v0.38e — covered by the existing lane

Already replayed by `benchmark_platform_replay.yml` run `30930069491`. No
additional workload needed.

## 3. Environment matrix

The existing replay used Python 3.12.10 on macOS and Python 3.12.13 on Linux.
That is legitimate end-to-end reproducibility, not a controlled platform check.
The extended lane runs a 2×2 corner sufficient to establish that Python patch
drift is not load-bearing:

| | Python 3.12.10 | Python 3.12.13 |
|---|:-:|:-:|
| macOS/arm64 | `existing_anchor` | `current_macos` |
| Linux/x86_64 | `current_linux` | `matched_diagonal` |

Two runners must be new: (a) Linux on 3.12.10 (matched diagonal to the existing
macOS anchor), and (b) macOS on 3.12.13 (matched diagonal to the existing Linux
runner). If both diagonals agree with their non-matched counterpart to the same
tolerance the current end-to-end replay already established, Python patch drift
is not load-bearing and the current end-to-end lane may remain end-to-end.

If either diagonal disagrees at a level larger than the current worst signal
gap (`4.485e-15` × safety factor of 10), the mixed-patch replay is confounded
and must be pinned to matched patches before Gate F is closed.

The 2×2 is a corner check, not a full factorial. Two additional runners, not
four.

## 4. Runtime budget

The existing lane executes 175 paired measurements in approximately 11 minutes
wall-clock per runner (from run `30930069491` metadata). The extended lane
adds 183 + 39 + 64 = 286 measurements per runner, plus the 2×2 Python patch
corner. Expected wall-clock:

| Runner | Measurement count | Est. wall-clock |
|---|---:|---:|
| existing macos-14 (Python 3.12.10) | 175 + 286 = 461 | ~29 min |
| existing ubuntu-22.04 (Python 3.12.13) | 175 + 286 = 461 | ~29 min |
| new ubuntu-22.04 (Python 3.12.10) | 461 | ~29 min |
| new macos-14 (Python 3.12.13) | 461 | ~29 min |

Total lane wall-clock: ~29 min per runner, parallel. Total added CI cost per
dispatch: ~1 hour of runner-time. Dispatched on demand via `workflow_dispatch`,
not on every push.

## 5. Reporting discipline

The extended lane emits the same JSON payload shape as the existing lane, with
one addition: every `tolerance_numeric` row carries an `error_metric_spec_id`
referencing the `ErrorMetricSpec` under which the frozen tolerance was
established. The paired-comparison downstream must call `require_matching_metric`
before quoting a relative gap — the v0.37c pilot-1 defect made impossible rather
than discouraged.

Signal versus floor is reported per measurement. A relative gap between two
floor measurements is not computed. The floor boundary is the same
`sqrt(eps) · reference_scale` v0.38d froze.

## 6. Pass criteria for Gate F closure

Gate F closes if **all** of the following hold across the extended lane:

1. **exact_discrete parity.** Every discrete-classification field (kind, regime,
   reason, refusal status, quadrature rule name, `error_metric_spec_id`,
   `reference_kind`) agrees exactly across every paired-platform row.
2. **v0.38b `tolerance_numeric` within the FN-12 margin.** Worst-paired-signal
   relative gap ≤ frozen bound × safety factor; the existing 1.5× margin holds.
3. **v0.38c `tolerance_numeric` within the `n·eps·L` margin.** Constant
   exactness on `nonuniform_trapezoidal` produces a worst-paired-signal absolute
   error below the confirmatory-freeze bound with the 50× margin the freeze
   established.
4. **v0.38d `tolerance_numeric` within the frozen floor.** Signal-regime
   errors agree to `sqrt(eps) · reference_scale`; floor-regime rows produce
   `None` on both platforms without one silently returning `0.0`.
5. **Python patch corner passes.** Both new diagonals agree with the existing
   runners at the same tolerance the current end-to-end lane already
   established.
6. **No unexplained regression.** Any row whose paired gap exceeds its
   frozen bound is either attributed to a documented mechanism (BLAS/FFT
   ordering, IEEE rounding-mode difference) or treated as a Gate F failure.

If any criterion fails, Gate F is **not** closed. The pilot report additive
appendix records the failure, and `rc1` does not cut.

## 7. What this closure plan is not

- **Not a re-freeze.** Every measurement, threshold and margin is inherited
  verbatim from the signed v0.38b/c/d confirmatory freezes. This plan schedules
  their replay; it does not restate them.
- **Not a scope expansion.** No new manufactured solutions, no new grid
  families, no new quadrature rules. The workloads listed in §2 are the
  workloads. Additions are amendments with dated entries.
- **Not a nonperiodic-action gate.** The retired C-4 axis remains retired.
- **Not a claim about untested platforms.** Pass criteria concern
  macOS/arm64 vs Linux/x86_64. Other platforms remain unassessed.

## 8. Sequence to rc1

1. This plan signed and merged.
2. `benchmark_platform_replay.yml` extended with the workloads in §2 (a
   companion PR).
3. Dispatched against `main` post-merge; run ID recorded in
   `v0_38_platform_replay.md`.
4. Additive appendix to `v0_38_platform_replay.md` records paired results with
   the accounting table below.
5. If all six pass criteria hold, `V0_38_GATES_A_TO_F.md` updates Gate F from
   `NOT MET` to `PASS`, and `v0.38.0-rc1` is cut from the same commit the
   extended lane executed against.
6. If any criterion fails, this plan is amended; the failing measurements
   surface in the appendix, and rc1 does not cut.

## 9. Accounting-table template for the replay appendix

Every replay report writes this table so a reader does not have to reconstruct
the partition from prose:

| Population | Count | Comparison statistic | Result |
|---|---:|---|---|
| signal-regime tolerance_numeric — v0.38b | ~150 | relative difference | *worst gap* |
| signal-regime tolerance_numeric — v0.38c | ~15 | absolute difference | *worst gap* |
| signal-regime tolerance_numeric — v0.38d | ~40 | relative difference | *worst gap* |
| floor-regime tolerance_numeric | ~80 | absolute difference | *distribution* |
| exact_discrete fields | ~286 × N_fields | exact equality | *all agree / N mismatches* |
| Python patch corner — matched diagonals | 2 × 461 | paired end-to-end | *agree within existing tolerance* |
| bit-identical numeric results | count / total | descriptive only | *decomposed by kind if requested* |

## 10. Signature

Written before the extended lane runs; frozen at signing. Changes are
amendments with dated entries.
