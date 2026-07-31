# v0.36d — Hypothesis Freeze

**Phase:** hypothesis. Written before implementation, per `docs/design/DESIGN_FREEZE_PROCESS.md`.

**Status:** thresholds unset. The confirmatory freeze below is empty until the pilot runs.

---

## Question

For a given design matrix and a given candidate support, do the assumptions that sparse-recovery theorems require actually hold — and can each be computed reliably enough to report, or does it degenerate?

## Quantities measured

Three, each with a named implementation:

| Quantity | Definition | Theorem |
|---|---|---|
| `rho_signed` | `max_j∉S \|G_ScS G_SS⁻¹ s\|` for a given sign pattern `s` | Zhao & Yu 2006, Wainwright 2009 — Lasso **sign** consistency |
| `rho_uniform` | `‖G_ScS G_SS⁻¹‖_∞` (matrix infinity norm) | the sign-free worst case over all sign patterns |
| `active_support_min_singular_value` | `σ_min(A_S)²/n` | the support-restricted quantity v0.35a already reports |

`G_SS = A_Sᵀ A_S / n` and `G_ScS = A_Scᵀ A_S / n`, computed on the column-normalized matrix.

## Inputs

Enumerated:

1. `I₄` — identity, support `[0, 1]`. Orthogonal columns; both constants are analytically **0**.
2. Orthonormal `Q` from `qr(default_rng(20350).standard_normal((8, 4)))`, support `[0, 1]`. Columns outside the support are orthogonal to it; both constants **0**.
3. A 4×2 correlated matrix with a known off-support correlation, support `[0]` — the only case where signed and uniform can differ.
4. `tests/fixtures/v0_35a_canonical_design_matrix.npz` at `seed=20340`, every 2-element support — the realistic case.
5. A rank-deficient support (duplicate columns) — the degenerate case.

## Decision rule

- `rho_signed < 1` → `lasso_sign_consistency_condition_satisfied`; otherwise `..._violated`.
- `rho_uniform < 1` → `uniform_irrepresentability_bound_satisfied`; otherwise `..._violated`.
- Singular or ill-conditioned `G_SS` → the constant is `None` with `undefined_singular_support`.
- `sign_patterns=None` → `sign_pattern_unavailable`; **uniform is the only actionable statistic**.

**The `< 1` threshold is not tunable.** It is the threshold the theorems are stated against, carried from `pdelie.diagnostics.irrepresentability_constant`. It is not a pilot output.

## Thresholds

**DELIBERATELY UNSET.**

| Threshold | Set by |
|---|---|
| `G_SS` conditioning cutoff above which the constant is refused | ⟨PLACEHOLDER — pilot⟩ |
| Hand-computed reference agreement tolerance | ⟨PLACEHOLDER — pilot⟩ |

The plan proposes `cond(G_SS) > 1e12` and `rtol=1e-12`. Both are recorded as **candidates with no authority** until measurement supports them.

## Invalidation

This hypothesis is **wrong**, not merely unmet, if:

1. **Signed and uniform never differ on any input.** Then the `sign_patterns` parameter is decorative, the two statuses are one status, and the report should say so rather than carrying a distinction it cannot exhibit. This is the v0.35b failure mode — a vocabulary whose branches are unreachable is a constant.
2. **The pseudoinverse question is not actually a choice.** If `np.linalg.solve` never raises on a rank-deficient support — returning garbage instead — then "no pseudoinverse fallback" protects nothing and the degenerate case needs a rank check, exactly as v0.35a's irrepresentability constant did after `lstsq` silently returned `0.4956551696` from a singular system.
3. **Every candidate support on real data is degenerate.** Then the report has no non-degenerate branch to exercise and the diagnostic describes nothing.

## Non-goals

No global ℓ1 recovery claim. No p-value from stability without a predeclared multiple-testing correction. No dependency on a specific external Lasso implementation. No redefinition of the shipped v0.35a `restricted_eigenvalue`.

## Vocabulary that must not appear

`recoverable`, `not_recoverable`, `recovery_guaranteed`, `recovery_impossible`, `ell1_recoverable`, `ell1_not_recoverable` — in neither source nor emitted JSON. Theorem-specific status names only. A diagnostic that says "recoverable" has made a claim the diagnostic cannot support.

---

# Confirmatory Freeze

**Run:** 2026-07-31, before implementation.

## Hypothesis status: **survived**

Neither invalidation clause fired. Both were checked directly rather than assumed.

## Measured values

### Hand-computed references, two independent routes

| matrix | support | `rho_signed` loop | `rho_signed` vectorized | route agreement | analytic |
|---|---|---|---|---|---|
| `I₄` | `[0,1]` | `0` | `0` | `0.000e+00` | **0** ✓ |
| orthonormal 8×4 | `[0,1]` | `1.38777878078145e-16` | `9.10000351991825e-17` | `4.778e-17` | **0** ✓ |
| correlated 4×3 | `[0]` | `0.6` | `0.6` | `0.000e+00` | **0.6** ✓ |

`rho_uniform` was computed two ways as well — by matrix infinity norm, and by brute-force maximization of `rho_signed` over all `2^|S|` sign patterns. They agree to `0.000e+00` on every case, which is the relationship the two definitions are supposed to have.

The correlated case is the useful reference: `0.6` exactly, hand-computable as the off-support column's correlation with the support after normalization. It is not a number read off an implementation.

### Invalidation 1 — signed and uniform **do** differ

Decisively, on a 4×3 correlated matrix with support `[0,1]`:

| sign pattern | `rho_signed` |
|---|---|
| `s = [+, +]` | **1.56197280263** — condition violated |
| `s = [+, −]` | **1.11022302463e-16** — condition satisfied |
| `rho_uniform` | **1.56197280263** = max over sign patterns |

The sign pattern moves the constant across the threshold. `sign_patterns` is not decorative, the two statuses are genuinely two statuses, and `rho_uniform ≥ max(rho_signed)` holds as it must.

### Invalidation 2 — `solve` **does** raise, but only on exact singularity

On a duplicate-column support, `G_SS = [[0.25, 0.25], [0.25, 0.25]]`, `rank(A_S) = 1`, `cond(G_SS) = 1.393789e+17`:

```
np.linalg.solve RAISED LinAlgError: Singular matrix
```

So "no pseudoinverse fallback" protects where `lstsq` did not — v0.35a measured `lstsq` silently returning `0.4956551696` from exactly this situation.

**But the protection is partial, and that is the finding.** `solve` raises on *exact* singularity. A support at `cond ≈ 1e13` does not raise and returns numerical noise dressed as an answer. The conditioning cutoff is therefore not redundant with the raise — it covers the near-singular gap the raise leaves open.

### Conditioning on real data

`cond(G_SS)` across every 2-element support of the v0.35a canonical weak matrix:

| statistic | value |
|---|---|
| minimum | **1.478** |
| maximum | **20.85** (support `(1, 2)`) |

## Thresholds, now set

| Threshold | Value | Justified by |
|---|---|---|
| Hand-computed reference agreement | **`atol=1e-12`** | worst deviation from analytic is `1.388e-16` — four orders of margin. `rtol` alone is meaningless here: two of the three references are analytically **0**, and every relative tolerance passes against zero. |
| `G_SS` conditioning cutoff | **`1e12`** | real supports reach `20.85`, ten orders below; exact singularity sits at `1.39e17`, five orders above. The cutoff sits in an empty gap, so it can only fire on genuinely degenerate input. |

The plan proposed both values as candidates. Both survive, and are now recorded with the spread that earns them rather than as round numbers.

## Amendments

**One, to the plan's test code.** The specified forbidden-vocabulary test iterates `Path("src/pdelie/diagnostics/sparse_recovery.py").iterdir()` — `iterdir()` on a file raises `NotADirectoryError`, so the loop body would never execute and the test would pass vacuously while asserting nothing. Implemented as a direct read of the file.

## Reachability

Every status in the frozen vocabulary is reached by a real input:

| status | reached by |
|---|---|
| `lasso_sign_consistency_condition_satisfied` | correlated 4×3, `s = [+, −]` → `1.11e-16` |
| `lasso_sign_consistency_condition_violated` | correlated 4×3, `s = [+, +]` → `1.562` |
| `uniform_irrepresentability_bound_satisfied` | `I₄` → `0` |
| `uniform_irrepresentability_bound_violated` | correlated 4×3 → `1.562` |
| `undefined_singular_support` | duplicate-column support, `rank(A_S) = 1` |
| `sign_pattern_unavailable` | `sign_patterns=None` |
| `insufficient_assumptions_for_recovery_claim` | support covering every column — no off-support column exists |

