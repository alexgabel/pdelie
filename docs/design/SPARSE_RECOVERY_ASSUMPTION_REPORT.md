# Sparse-Recovery Assumption Report — Definitions and Citations

**Status:** normative for `pdelie.diagnostics.sparse_recovery` (v0.36d).

## What this reports, and what it does not

The report evaluates whether the *assumptions* certain sparse-recovery theorems require are satisfied by a given design matrix and candidate support. **It does not report whether recovery succeeded, would succeed, or is possible.**

That distinction is enforced, not merely stated. The vocabulary `recoverable`, `not_recoverable`, `recovery_guaranteed`, `recovery_impossible`, `ell1_recoverable`, `ell1_not_recoverable` appears in neither the module's code surface nor any emitted payload, asserted by test. A status like `lasso_sign_consistency_condition_satisfied` names a condition from a specific theorem under specific assumptions — noise model, regularization path, sample size — none of which this module is given. Satisfying the condition is a necessary ingredient of a guarantee, not the guarantee.

## Definitions

Let `A` be the design matrix with `n` rows, column-normalized to unit L2 norm. Let `S` be a candidate support and `Sᶜ` its complement. Write

- `G_SS = A_Sᵀ A_S / n`
- `G_ScS = A_Scᵀ A_S / n`

### Signed irrepresentability constant

```
rho_signed(S, s) = max_{j ∈ Sᶜ} | (G_ScS G_SS⁻¹ s)_j |
```

for a sign pattern `s ∈ {−1, +1}^|S|` giving the sign of each active coefficient. `rho_signed < 1` is the **irrepresentable condition** of Zhao & Yu (2006), and is what Lasso *sign* consistency is stated against — see also Wainwright (2009) for the sharp threshold analysis.

### Uniform irrepresentability bound

```
rho_uniform(S) = ‖ G_ScS G_SS⁻¹ ‖_∞
```

the matrix infinity norm, equal to the maximum absolute row sum. This is exactly the worst case of `rho_signed` over all `2^|S|` sign patterns, which the implementation's tests verify by brute-force enumeration rather than assertion.

**The distinction is not academic.** Measured on a 4×3 correlated matrix with `S = [0, 1]`:

| sign pattern | `rho_signed` |
|---|---|
| `s = [+, +]` | **1.56197280263** — violated |
| `s = [+, −]` | **1.11022302463e-16** — satisfied |
| `rho_uniform` | **1.56197280263** |

The sign pattern moves the constant across the threshold. When the true signs are unknown, `rho_uniform` is the only statistic that can be acted on, and the report says `sign_pattern_unavailable` rather than computing a signed value against an assumed pattern.

### Active-support minimum singular value

```
active_support_min_singular_value(S) = σ_min(A_S)² / n
```

**This is not the restricted eigenvalue of Bickel, Ritov & Tsybakov (2009).** The BRT constant minimizes over every support of a given size *and* over a cone of vectors, which is combinatorial. This is the exact value for one given support, and an upper bound on the BRT constant.

The v0.35a report already carries this distinction under the name `support_restricted_min_gram_eigenvalue_over_n`. **v0.36d does not redefine it.** The new report uses `active_support_min_singular_value` as an explicitly-named alternative and declares which it used in `restricted_eigenvalue_definition`; the v0.35a function keeps its name and meaning unchanged.

`sampled_re_lower_bound` is reserved in the vocabulary and **raises if requested** — it needs a sampling procedure that has not been specified or measured, and returning a value from an unspecified procedure would be worse than refusing.

## Degeneracy handling

Two mechanisms, because one is not enough.

**`np.linalg.solve` raises on an exactly singular Gram matrix**, and there is deliberately no pseudoinverse fallback. v0.35a measured `lstsq` silently returning `0.4956551696` from precisely such a system — finite, plausible, below threshold, and describing nothing. A minimum-norm substitute for an underdetermined system is an answer to a question nobody asked.

**A conditioning limit covers what the raise does not.** `solve` raises on exact singularity; a Gram matrix at `cond ≈ 1e13` does not raise and returns numerical noise. `ACTIVE_SUPPORT_CONDITION_LIMIT = 1e12` closes that gap, and the value sits in a measured empty region:

| situation | `cond(G_SS)` |
|---|---|
| real 2-element supports of the canonical weak matrix | 1.478 – **20.85** |
| the limit | **1e12** |
| exactly-singular duplicate-column support | **1.39e17** |

Ten orders above anything real data reaches, five orders below the degenerate case. It can only fire on genuinely degenerate input.

## Empirical stability is a separate report

`empirical_support_stability_report` measures how often a selection method picks the same support under resampling. It is a different function emitting a different `summary_type`, because selection frequency is **not** evidence that a theoretical condition holds and the two must not be read as one number.

**Row-level resampling is refused with a typed error.** Rows of a PDE-derived design matrix are adjacent samples of a continuous field; resampling them independently destroys the correlation structure that makes the design what it is, and yields intervals describing a dataset nobody has. Only `trajectory` and `complementary_pair` units are offered.

No p-value is emitted. A frequency is not a test statistic without a predeclared multiple-testing correction, and none is declared.

## References

- Zhao, P. & Yu, B. (2006). On Model Selection Consistency of Lasso. *JMLR* 7, 2541–2563. — the irrepresentable condition.
- Wainwright, M. J. (2009). Sharp Thresholds for High-Dimensional and Noisy Sparsity Recovery Using ℓ₁-Constrained Quadratic Programming (Lasso). *IEEE Trans. Inform. Theory* 55(5), 2183–2202.
- Bickel, P. J., Ritov, Y. & Tsybakov, A. B. (2009). Simultaneous analysis of Lasso and Dantzig selector. *Annals of Statistics* 37(4), 1705–1732. — the restricted eigenvalue this report does **not** compute.

The measured values in this document come from the v0.36d pilot, recorded in `docs/planning/V0_36D_SPARSE_RECOVERY_FREEZE.md`.
