# V0.35 Engineering Spec — Day-0 Gates, Repo Audit, and Execution Plan

**Status:** DRAFT for team review. Not a scope freeze — the freeze happens per sub-milestone, *after* the measurement gates in §5 pass.

**Audience:** engineers picking up v0.35a / v0.35c / v0.35b.

**Baseline:** `v0.34.0` (tag `v0.34.0`, merge commit `c0aa1e0`). All numbers in this document were measured against that commit on 2026-07-29, not copied from planning docs. Where a planning figure and a measured figure disagree, the measured one is used and the disagreement is called out.

---

## 1. Why this document exists

Across v0.33 and v0.34, **eight of nine frozen sub-milestone contracts required amendment on first contact with measurement.** Three would have shipped as silent defects:

| Milestone | What the freeze said | What measurement found |
|---|---|---|
| v0.33e | six PDEs; `atol` = float32 limit | five PDEs; float64 throughout; bit-exact comparison breaks on Linux BLAS |
| v0.33d | gate on `span_distance` | inverts to `0.0` — reports a *perfect* fit on a failing candidate |
| v0.33a | shave 1 interior row | leaves `span_distance` at its √2 ceiling; needs `boundary_trim_width` |
| v0.33b | `overlap_fraction = 1 − \|s\|/L` | two `L` conventions disagree; crop is a no-op at default epsilons |
| v0.33c | mask rows are spatial | rows are **time**; spatial masks zero the design matrix |
| v0.34a | residual is `ν(x)·u_xx` | generators default to divergence form; ~300× mismatch |
| v0.34c | 87× / 111.8 / 3.77 | **function is nondeterministic**; figures were one draw |
| v0.34b | (vocabulary unmeasured) | cleared its bar by 15×, and the freeze was sound |

The v0.34c case is the one that shapes this document. Measurement did not show the threshold was *wrong*; it showed the target function was **unmeasurable** — `pysindy.WeakPDELibrary` seeds domain centers from the global NumPy RNG with no seed parameter. No amount of document review finds that. Only running it does.

**Operating principle for v0.35:** a number may not enter a frozen contract until it has been produced twice by running code, on at least two inputs, with the variance reported. §5 makes that concrete per sub-milestone.

---

## 2. Measured repo state at `v0.34.0`

### 2.1 Scale

| Metric | Value |
|---|---|
| Source LOC (`src/pdelie`) | **22,097** across 13 packages |
| Test LOC | **33,573** across 124 files |
| Test:source ratio | **1.52 : 1** |
| Tests | **1727 passed, 2 skipped** (py3.12 and py3.13) |
| Line+branch coverage | **84.36%** |
| mypy errors | **147** in 29 files |
| `TODO` / `FIXME` / `XXX` / `HACK` in `src` | **0** |
| Suppressions in `src` | 46 total — 26 `type: ignore`, 6 `pragma: no cover`, ~14 `noqa` |

Zero debt markers in `src` is unusual and worth preserving. It means the codebase carries no *undocumented* known-bad regions: everything questionable is either a typed suppression with a comment or an explicit `ScopeValidationError`.

### 2.2 CI gate status — **three of ten jobs are advisory**

Measured from `.github/workflows/ci.yml`:

| Job | Status |
|---|---|
| `v0_34_0-release-gate` (3.12, 3.13) | **BLOCKING** |
| `lint` (ruff) | **BLOCKING** |
| `docs-build` (sphinx `-W`) | **BLOCKING** |
| `editable-tests` (3.12, 3.13) | **BLOCKING** |
| `package-smoke` | **BLOCKING** |
| `typecheck` (mypy) | *advisory* (`continue-on-error: true`) |
| `coverage` | *advisory* (`continue-on-error: true`) |
| `py314-core-only-advisory` | *advisory* (by design) |

> **Finding G-1.** `pyproject.toml:220` sets `fail_under = 80` and the suite measures **84.36%** — comfortably above. But `coverage` is `continue-on-error: true`, so **the floor is configured and not enforced.** A PR dropping coverage to 60% goes green today. This is a latent regression channel, not a hypothetical: v0.35 adds three greenfield packages, and greenfield code is exactly where coverage silently slips.

> **Finding G-2.** `typecheck` is advisory with 147 standing errors. That number has been held at delta-zero by convention across four release closes — a discipline enforced by reviewer habit, not by CI. It has held so far, but it is one distracted PR away from drifting.

> **Finding G-3 — the blocking `lint` job is not reproducible.** `pyproject.toml:77` specifies `ruff>=0.6`: an unpinned *floor*, not a pin. CI runs `pip install -e .[test]`, so the blocking linter is whatever ruff is newest at the moment the job runs. Measured against `v0.34.0`, unchanged source:
>
> | ruff | result on the same tree |
> |---|---|
> | 0.9.10 | **102 errors** |
> | 0.14.5 – 0.15.20 | **5 errors** (`RUF100`, unused `noqa: BLE001` in `discovery/pysindy_adapter.py`) |
> | **0.16.0** — what CI resolved on 2026-07-29 | **0 errors — "All checks passed!"** |
>
> Main is genuinely green; this is not a live breakage. But the gate that decides green is a moving target in both directions. A future ruff that enables one new rule by default fails `main` with **no code change** and blocks whoever pushes next, and the same spread runs backwards: a developer whose venv is one minor version behind sees five failures CI does not have. That is not hypothetical — it happened while auditing this document, and cost a bisect to resolve.
>
> Same class of defect as the v0.34c finding: a result that looks deterministic, is not, and whose variance is invisible until measured. **Recommendation:** pin `ruff~=0.16.0` in `[test]` and bump deliberately in its own PR, so a lint-rule change arrives as a reviewable diff rather than as a surprise red build on someone else's work. `mypy` (`mypy>=1.11`) has the same unpinned shape and the same exposure — it is merely advisory today, which is the only reason it has not bitten.

### 2.3 Load-bearing modules (by internal import count)

| Module | Imports | Coverage | Assessment |
|---|---|---|---|
| `pdelie.data` | 106 | 88–97% | **Trustworthy.** Every generator pinned by v0.33e goldens. |
| `pdelie.contracts` | 91 | 81% | **Trustworthy but under-covered.** The schema spine; see W-3. |
| `pdelie.errors` | 87 | 100% | **Trustworthy.** 4 statements, fully exercised. |
| `pdelie.residuals` | 75 | 86–97% | **Trustworthy.** Rewritten in v0.34a; goldens hold. |
| `pdelie.derivatives` | 51 | 88–90% | **Trustworthy.** Pinned by 8 golden entries across both backends. |
| `pdelie.reporting` | 36 | see W-1 | **Weak.** Largest module, largest mypy debt. |
| `pdelie.verification` | 35 | 97% | **Trustworthy.** Rewritten in v0.33b. |
| `pdelie.symmetry.fitting` | 34 | 98% | **Trustworthy.** Rewritten in v0.33a. |
| `pdelie._boundary` | 27 | 87% | **Trustworthy.** Survived v0.30d + v0.33a dispatch rewrites. |

---

## 3. Trustworthy, stress-tested subroutines — build on these

These have survived at least one milestone-scale rewrite *and* are pinned by a cross-platform fixture. Reuse them rather than reimplementing.

| Subroutine | Location | Evidence |
|---|---|---|
| `compute_derivatives(field, backend="auto")` | `derivatives/__init__.py:14` | Backend dispatch pinned by 8 golden entries (5 periodic + 3 nonperiodic) at `rtol=1e-6` across macOS and Linux BLAS. Survived v0.30d, v0.33a. |
| `build_residual_diagnostics_from_derivatives` | `residuals/base.py:24` | The interior-only trim policy. Load-bearing for v0.33a's shave width and v0.33b's comparison row-set. 86%. |
| `fit_translation_generator` | `symmetry/fitting/translation_baseline.py` | **98% coverage.** Rewritten in v0.33a with measured shave width and fallback suppression. |
| `verify_translation_generator` | `verification/finite_transform.py` | **97% coverage.** Rewritten in v0.33b with the measured `N·dx` domain-length convention. |
| `broadcast_coefficient_over_x` | `residuals/_variable_coefficient.py:62` | **97%.** Exists specifically to prevent a silent `(batch,time,x,x)` broadcast that cost two invalid measurements in v0.34a. **Use this for any coefficient shaping in v0.35.** |
| `summarize_column_normalization` | `discovery/column_normalize.py:111` | 92%. Pure NumPy, no backend import. Good template for v0.35a/c report shape. |
| `score_against_reference` | `symmetry/admissibility.py:98` | 92%. Scale- and sign-invariant, bounded by √2. |
| `_validate_strict_json_compatible` | `reporting/summaries.py` | Used at every composition boundary. The single reason no NaN has ever escaped a payload. |
| Golden-fixture regeneration CLI | `tests/_helpers/regenerate_golden_fixture.py` | Named-cause regeneration, targeted `--pde`, carry-over verified. **Copy this pattern for v0.35 fixtures.** |

### 3.1 Fixture assets already proven cross-platform

| Fixture | Entries | Tolerance |
|---|---|---|
| `tests/fixtures/v0_33e_golden_numbers.json` | 8 (5 periodic, 3 nonperiodic) + 3 variable-coefficient | `rtol=1e-6`, `atol=1e-12` |
| `tests/fixtures/v0_33d_admissibility_dose_response.json` | 3 PDEs × 5 α values | `rtol=1e-6` |
| `tests/fixtures/v0_34c_conditioning_ratios.json` | 6 fixtures, seeded | `rtol=1e-6` |

All three reproduce macOS → Linux. Worst observed cross-platform deviation anywhere: **1.5e-9** against a `1e-6` tolerance (~650× headroom). **Do not tighten below `rtol=1e-6`** and **never compare a pinned metric with `==`** — v0.33e shipped that mistake and CI caught it.

---

## 4. Weaknesses — know these before you touch them

### W-1 · `reporting/summaries.py` — 3,813 LOC, 40 mypy errors

The largest module in the repo and the largest single concentration of type debt (27% of all mypy errors). Every summary type routes through it. **v0.35 adds two new `summary_type` values** (`pdelie_design_diagnostic`, `pdelie_row_selection`) plus registry reports.

**Mitigation:** add new summarizers as *new functions* in the new packages, calling `_validate_strict_json_compatible` at the boundary. Do not extend `summaries.py` itself. v0.34c set this precedent — `column_normalize.py` is a standalone pure-NumPy module.

### W-2 · `symmetry/symbolic.py` — 67% coverage, 13 mypy errors

**The weakest module in the repo on both axes.** Lines 197–226 are entirely uncovered.

**Relevance to v0.35b:** `FormulaGeneratorFamily` (`symmetry/formula.py:265`) is a hard input to `PointSymmetryEntry.generator_formula`. `formula.py` is at 79%; `symbolic.py` backs it. **Day-0 gate B-1 (§5.3) requires a coverage probe of the exact `FormulaGeneratorFamily` construction path v0.35b will use, before the registry schema freezes.**

### W-3 · `contracts.py` — 81% coverage on the schema spine

91 internal imports; 66 uncovered statements are mostly validation branches. Under-tested validation is the failure mode where a malformed payload passes silently.

**Mitigation:** any v0.35 dataclass (e.g. `PointSymmetryEntry`) must have explicit negative tests per validation branch, not just happy-path round-trips.

### W-4 · `tasks/weak_pde_library.py` — nondeterministic by default

`inspect_pysindy_weak_pde_library(seed=None)` — the default — remains nondeterministic, because `pysindy.WeakPDELibrary` draws domain centers from the global NumPy RNG. v0.34c added an opt-in `seed`; the default was deliberately left alone to avoid changing a shipped surface.

**Consequence for v0.35a:** the spec names *"one from the v0.34c weak-form column-normalization fixture"* as a canonical design matrix. **That matrix does not exist as a fixed artifact.** It must be regenerated with `seed=20340` (`tests/_helpers/conditioning_ratios.py:CONDITIONING_SEED`), or v0.35a's reference numbers will not reproduce. See gate A-2.

### W-5 · `tasks/discovery.py` — 71% coverage, 1,038 LOC

Second-largest module, lowest coverage among load-bearing code. Not on v0.35's critical path, but any v0.35 work touching the discovery bridge inherits this risk.

### W-6 · The README/release alignment guard is weaker than it looks

Confirmed at `tests/test_current_release_gate.py:63-69`. The team's diagnosis is correct. See §6.2 — this is a **day-0 blocking fix**.

---

## 5. Day-0 gates — the flowchart

No sub-milestone may freeze its contract until its gates pass. Gates produce **numbers written into the freeze**, not go/no-go booleans.

```text
                        ( v0.34.0 shipped )
                                 |
  =============================== DAY 0 ===============================
  |  BLOCKING - must land on main before any v0.35 branch is cut      |
  |                                                                    |
  |   [H-0] Delete 5 stale locals ...................... DONE          |
  |         content-verified by patch identity, not merge status       |
  |                          |                                         |
  |                          v                                         |
  |   [H-1] Tighten README/release guard ............... BLOCKING      |
  |         tests/test_current_release_gate.py                         |
  |         derive from pyproject; assert prose AND pip pins           |
  |                          |                                         |
  |                          v                                         |
  |   [H-2] Pin the blocking toolchain ................. BLOCKING      |
  |         ruff~=0.16.0, mypy~=2.3.0  (Finding G-3)                   |
  |         an unpinned linter = a merge gate that moves               |
  |                          |                                         |
  |                          v                                         |
  |   [H-3] Advisory-job promotion ......... DEFERRED to v0.36 close   |
  |         coverage 84.36% vs floor 80 -> not currently at risk       |
  ======================================================================
                                 |
                                 v
  ------------------------- v0.35a GATES -------------------------------
  |  measure BEFORE freeze - each gate emits a NUMBER, not a boolean   |
  |                                                                    |
  |   [A-1] Hand-compute rho_IR, leverage, coherence, RE               |
  |         on 5 canonical matrices -- BY HAND, not from the library   |
  |            |                                                       |
  |   [A-2] Regenerate the v0.34c weak matrix at seed=20340            |
  |         (W-4: it is NOT a stored artifact -- scalars only)         |
  |            |                                                       |
  |   [A-3] Freeze ONE definition per metric; cite the RE constant     |
  |            |                                                       |
  |   [A-4] Probe degenerate cases: support=all, zero column,          |
  |         near-singular  ->  documented sentinel, never NaN          |
  ----------------------------------------------------------------------
                                 |
                    < all A gates produced numbers? >
                                 |
                                 v
                    /  FREEZE v0.35a contract  /
                                 |
                    [[ implement v0.35a + PR + CI green ]]
                                 |
                                 v
  ------------------------- v0.35c GATES -------------------------------
  |                                                                    |
  |   [C-1] *** BLOCKER *** scipy is NOT a core dependency             |
  |         np.linalg.qr has no pivoting; scipy.linalg.qr does         |
  |         DECIDE QR-pivot strategy before any code -- see 5.2        |
  |            |                                                       |
  |   [C-2] D-optimal exchange: 3 matrices x 5 seeds x 2 repeats       |
  |         prove determinism; report variance (the v0.34c lesson)     |
  |            |                                                       |
  |   [C-3] Condition-number reduction vs >=20 random baselines        |
  |         freeze a percentile, not a single draw                     |
  |            |                                                       |
  |   [C-4] Tall-matrix scaling probe: n_rows >> k, max_iter behaviour |
  ----------------------------------------------------------------------
                                 |
                    < all C gates produced numbers? >
                                 |
                                 v
                    /  FREEZE v0.35c contract  /
                                 |
                    [[ implement v0.35c + PR + CI green ]]
                                 |
                                 v
  ------------------------- v0.35b GATES -------------------------------
  |                                                                    |
  |   [B-1] Coverage probe of the FormulaGeneratorFamily path          |
  |         (W-2: symbolic.py at 67%, lines 197-226 uncovered)         |
  |            |                                                       |
  |   [B-2] *** PUBLIC WRITE-UP CHECK ***                              |
  |         absent or unknown -> underscore-private is the DEFAULT,    |
  |         not a close-time fallback                                  |
  |            |                                                       |
  |   [B-3] Verify a + c outputs actually compose into a               |
  |         classification (integration, not unit)                     |
  |            |                                                       |
  |   [B-4] Resolve: do registry entries REGISTER as SymmetryMethod    |
  |         adapters, or are they catalogue data?  (criterion 4)       |
  ----------------------------------------------------------------------
                                 |
                    < all B gates produced numbers? >
                                 |
                                 v
                    /  FREEZE v0.35b contract  /
                                 |
                    [[ implement v0.35b + PR + CI green ]]
                                 |
                                 v
                      ( v0.35.0 release close )


  LEGEND
    [X-n]  gate, must emit a measured number before the freeze it guards
    / ... /  scope freeze - contract text written with measured values
    [[ ... ]]  implementation, gated behind the freeze above it
    < ... >  checkpoint; a failed gate sends the sub-milestone back to
             measurement, it does NOT get waived
```

### 5.1a v0.35a gate results — **all four passed, three changed the contract** ✅

Run 2026-07-29 before any implementation. Recorded here because the numbers are the contract.

| Gate | Outcome |
|---|---|
| **A-1** | Four metrics computed by two independent routes on five canonical matrices. Agreement ≤ 6e-15 everywhere **except leverage** — see below. Closed forms confirmed: `coherence(I₄) = 0`, `leverage(I₄) = 1` everywhere, `RE(I₄, S={0,1}) = 1/4`, `Σhᵢ = rank` on all five. |
| **A-2** | Canonical matrix built at `seed=20340`: **16×5, rank 5, cond 5232.86**. Bit-identical across two builds; `seed+1` gives cond 5945.46, confirming the seed is load-bearing. `.npz` round-trips bit-identically. Landed as `tests/fixtures/v0_35a_canonical_design_matrix.npz`. |
| **A-3** | **Two of the four metrics are scale-dependent, and the verdict moves with them.** See below. |
| **A-4** | Four degenerate cases found that returned well-formed wrong answers. See below. |

**A-1 finding — the hat-matrix route for leverage is not merely imprecise, it is wrong.** On a square full-rank matrix every leverage is exactly 1.0. Measured error against that analytic value:

| matrix | cond(A) | `diag(A(AᵀA)⁻¹Aᵀ)` | thin-SVD route |
|---|---|---|---|
| Hilbert(5) | 4.766e+05 | 1.387e-06 | 8.882e-16 |
| Hilbert(8) | 1.526e+10 | **5.634e-01** | 6.661e-16 |
| Hilbert(10) | 1.603e+13 | **6.258e-01** | 4.441e-16 |

An error of 0.56 on a quantity bounded in `[0,1]`. Forming `AᵀA` squares the condition number. **Frozen: thin SVD, never the hat matrix**, with a parametrized regression test over all three sizes.

**A-3 finding — the scale-dependence flips the science.** On the canonical matrix, whose column norms span 1158×:

| metric | raw | column-normalized | arbitrary rescale |
|---|---|---|---|
| mutual coherence | 0.9084512121 | 0.9084512121 | 0.9084512121 |
| max leverage | 0.9640848878 | 0.9640848878 | 0.9640848878 |
| irrepresentability | 1.129160013 | 2.742717168 | **0.2955377896** |
| restricted eigenvalue | 8.556977e-10 | 6.509027e-03 | 6.899429e-08 |

Coherence and leverage are scale-invariant. The other two are not — and an arbitrary but perfectly legitimate rescaling carries the irrepresentability constant **across the 1.0 threshold**, turning "recovery not guaranteed" into "recovery guaranteed" on identical data. A diagnostic whose conclusion depends on an unstated scaling is worse than none.

**Frozen: every metric is computed on the column-normalized matrix (`‖aⱼ‖₂ = 1`), reported in every payload as `column_scaling`.** Implemented by reusing v0.34c's `column_normalize_design_matrix`, verified **bit-identical** (0.000e+00) to a hand-written normalization. The `‖aⱼ‖₂ = √n` convention differs by exactly `n`; the payload carries `sqrt_n_convention_multiplier` rather than auto-dispatching.

**A-4 findings — four silent-wrong-answer paths, now sentinels:**

| Case | Measured behaviour | Resolution |
|---|---|---|
| support = ∅ | summed over an empty axis → **0.0**, reads as "perfectly recoverable" | `ScopeValidationError` — there is no condition to report |
| support = all columns | no columns outside the support | `metric_value = None` + `irrepresentability_support_covers_all_columns` |
| rank-deficient support | `lstsq` silently returned the minimum-norm solution → **0.4956551696**, reads as "recovery guaranteed" from a singular system | `metric_value = None` + `irrepresentability_support_is_rank_deficient` |
| degenerate vs merely ill-conditioned RE | both near zero (0.0 vs 2.162100e-12) — indistinguishable by value | rank check emits `restricted_eigenvalue_support_is_rank_deficient` |

The third is the dangerous one: a finite, plausible, sub-threshold number from a system that determines nothing.

**Scientific note.** On the canonical weak-form matrix the irrepresentability constant is **2.74 > 1** — Lasso support recovery is *not* guaranteed on that design. That is a property of the matrix worth reporting, not a defect.

### 5.1 v0.35a gates — detail

**A-1 · Hand-computation is the gate, not library agreement.** The team's instruction is right and the reason is worth stating: freezing against library output means a NumPy release can silently move the "reference." Compute ρ_IR, leverage, coherence, and RE **by hand** (or by an independent symbolic route) on:

| Matrix | Purpose | Expected property |
|---|---|---|
| `I₄` | identity | leverage = 1 everywhere; coherence = 0 |
| orthogonal `Q` from QR of a random matrix | near-orthogonal | coherence ≈ 0; ρ_IR well below 1 |
| Hilbert(5) | ill-conditioned | cond ≈ 4.8e5; RE small |
| rank-deficient (duplicate column) | near-singular | must warn, must not `NaN` |
| v0.34c weak matrix @ `seed=20340` | realistic | see A-2 |

**A-2 · The v0.34c matrix is not a stored artifact — v0.35a must land it.** `tests/fixtures/v0_34c_conditioning_ratios.json` stores *scalars*, not the matrix, so the v0.35 spec's "canonical matrix from the v0.34c fixture" refers to something that does not exist on disk.

**Spec amendment (accepted):** v0.35a's file list gains a **new artifact**, regenerated at `seed = 20340` from v0.34c's canonical fixture parameters:

| New artifact | Produced by | Notes |
|---|---|---|
| `tests/fixtures/v0_35a_canonical_design_matrix.npz` | new `tests/_helpers/regenerate_v0_35a_design_matrix.py` | `.npz` not `.npy` — carries the matrix **plus** its provenance (seed, fixture name, pysindy version, feature names) in one file |

Regenerate via `_build_weak_library` under `_seeded_global_numpy_random(20340)` (`tasks/weak_pde_library.py:171`), with a named-cause CLI modelled on `tests/_helpers/regenerate_golden_fixture.py`.

Two reasons this is v0.35a's own work rather than a borrowed input:

1. **It decouples the diagnostics from PySINDy.** Once stored, `pdelie.diagnostics` tests never re-run a nondeterministic third-party library to obtain their input — they load an array. That is the whole point of W-4.
2. **v0.35c consumes it too.** Gate C-3 needs a realistic design matrix for the condition-number comparison. Landing it in v0.35a means v0.35c inherits a pinned input rather than regenerating one and silently getting a different draw.

**Sequencing consequence:** verify this fixture lands and reloads byte-identically **before** v0.35c consumes it. Added to the gate chain as a dependency edge, not just a task.

**A-3 · Freeze one RE definition.** The restricted-eigenvalue constant has several inequivalent definitions in the literature. Pick one, cite it precisely in `docs/design/PDELIE_DIAGNOSTICS_CONTRACT.md`, and **refuse to auto-dispatch**. Precedent: v0.33b froze the `N·dx` domain-length convention with the measurement that forced it.

**A-4 · Degenerate cases return documented sentinels.** Precedent for the shape: `column_normalize_design_matrix` sets zero-norm column scale to `1.0` and *reports* `scaling_zero_column_count` rather than dividing by zero. `ρ_IR` with `support = all indices` must return a documented sentinel with a warning — never `NaN`, never a silent `inf`.

### 5.2a v0.35c gate results — **all four passed; C-2 and C-3 changed the contract** ✅

Run 2026-07-29 before implementation.

| Gate | Outcome |
|---|---|
| **C-1** | Hand-rolled Householder pivoted QR matches `scipy.linalg.qr(pivoting=True)` **exactly on the 4 matrices whose pivot sequence is determined**, and matches on **selection quality (conditioning, R-diagonal) on all 8**. Deterministic across 5 repeat runs on every case — which SciPy is not, across platforms. See the correction below. |
| **C-2** | Exchange is **repeat-stable** (no hidden RNG) but **start-dependent**: 5 random starts reached **4–5 distinct optima** on all three matrices. |
| **C-3** | QR-pivot and D-optimal each beat **100%** of 40 random draws. **Leverage beat 8%** — worse than random. |
| **C-4** | Exchange converges in **0–1 iterations** from the QR start at n_rows = 50/200/800. The iteration cap is not load-bearing. |

**C-1 finding — the norm-downdate safeguard is load-bearing, not boilerplate.** Across twelve adversarial matrices (Kahan, high-order Hilbert, near-dependent blocks) it changed the permutation in **eight**, and in every one the *guarded* result matched the oracle while the unguarded result did not. Requirement #2 in the C-1 resolution is now empirically justified rather than cited from a textbook.

**C-1 finding — "matches SciPy's permutation" is not a well-posed guarantee, and the first version of this section got it wrong.** The macOS measurement showed agreement on all eight canonical matrices, and that was recorded here as the contract. CI then failed on Linux for two of them. The cause is not a defect in either implementation: **the pivot sequence is only determined where competing column norms are separated by more than rounding.** Measured minimum relative gap between the best and runner-up norm at every step:

| matrix | min relative gap | determined? |
|---|---|---|
| graded_scales_12x6 | 9.821e-01 | **yes** |
| weak_matrix_transpose | 8.897e-02 | **yes** |
| hilbert_7 | 6.666e-02 | **yes** |
| wide_5x14 | 3.042e-02 | **yes** |
| orthonormal_8x4 | 1.110e-16 | no |
| identity_6 / tied_norms_4x4 / rank_deficient_10x5 | 0.000e+00 | no |

On the undetermined four every tie-break is a valid pivoted QR, and **SciPy's own choice is not portable** — it pivots `orthonormal_8x4` as `[1 0 2 3]` under one LAPACK and `[0 1 2 3]` under another. Asserting permutation equality there was asserting that two platforms' LAPACK agree, which is not a property of this package.

**Corrected contract, split three ways:**

1. **exact permutation** — asserted only on the four determined matrices, with the separation itself verified as a test precondition so a future near-tie fails with a clear cause;
2. **selection quality** — asserted on all eight: R-diagonal magnitudes and resulting condition number match the oracle, which is what actually matters;
3. **our determinism** — asserted on all eight, and it is stronger than SciPy's.

The Kahan matrix is the extreme of the same effect (every column norm exactly 1.0): it agrees through order 28 and diverges at 30, with condition number identical at 1.4008e+05. Its test now asserts equal *quality* at every order rather than equal permutation.

**C-2 finding — the starting set is part of the contract.** The exchange has no RNG and is repeat-stable, so it *looks* deterministic. But it is a local search, and measured across three matrices × five random starts it reached four to five distinct optima depending only on where it began:

| matrix | distinct optima from 5 random starts |
|---|---|
| canonical weak matrix (16×5) | **4** |
| random 40×6 | **5** |
| Hilbert(12) | **5** |

**Frozen:** `initial_rows` defaults to the deterministic `qr_pivot` selection, never a random subset, and the resolved start is reported as `initial_row_indices` / `initial_rows_source` so any result can be reproduced. This is the same class of finding as v0.34c — a function that looks deterministic and whose output silently depends on something unstated.

**C-3 finding — one of the three methods is not a conditioning method.** Against 40 random draws per matrix:

| method | canonical weak matrix | random 40×6 |
|---|---|---|
| `qr_pivot` | cond 5513 — beats **100%** | cond 3.201 — beats **100%** |
| `d_optimal_exchange` | cond 5513 — beats **100%** | cond 3.201 — beats **100%** |
| `leverage` | cond 2.52e+05 — beats **8%** | cond 5.334 — beats 98% |

Random median on the weak matrix is 4.52e+04, so leverage selection is **worse than a coin flip** there. It answers a different question — which rows individually carry the most influence — and the report now carries `leverage_selection_does_not_target_conditioning` so a reader cannot assume all three methods share an objective.

**Frozen threshold:** `qr_pivot` and `d_optimal_exchange` must beat the **random median** over ≥40 draws — a distributional claim, not a fixed ratio and not a single draw. A fixed "≥20× reduction" would have been unmeetable on the weak matrix and trivially met on others, exactly the v0.34c trap.

**C-4 finding — maximizing the determinant is not minimizing the condition number.** On a 200×5 matrix the exchange improved log-det while leaving a slightly *worse* condition number (2.499) than its QR starting point (2.384). Expected — the objectives differ — and now documented rather than left for a user to discover.

### 5.2 v0.35c gates — detail

> ### C-1 — **RESOLVED at day 0: hand-roll the pivoted QR** ✅
>
> The original v0.35c spec named `scipy.linalg.qr(pivoting=True)` as the implementation. That is not available to a core module. Measured:
>
> - core deps are `["numpy>=2,<3"]` only; scipy appears in `[downstream]` and `[test]`;
> - `np.linalg.qr` has signature `(a, mode='reduced')` — **no `pivoting` parameter**;
> - **no core module imports scipy today**, so `pdelie.design` would be the first, breaking the core-only install that `package-smoke` and `py314-core-only-advisory` both verify.
>
> **Accepted resolution.** Implement `qr_pivot_row_selection` as a **hand-rolled Householder QR with column pivoting, per Golub & Van Loan §5.4**, in pure NumPy (~40 LOC). Deterministic under an explicit tie-break policy. `scipy.linalg.qr(pivoting=True)` is retained **only as a test-side reference oracle**, where scipy is already available through the `[test]` extra.
>
> This preserves the spec's "matches SciPy's QR-pivot output" test verbatim — that test lives on the test side, so it never constrained the core implementation in the first place. The stratification is the point: **core stays numpy-only; the test side gets scipy as an independent oracle.** A hand-rolled numerical routine checked against a mature library implementation is strictly better evidence than either alone.
>
> Rejected: a lazy scipy import (the function would exist but fail at runtime on a core install, contradicting "three selection methods functional"), and promoting scipy to core (widens the core surface for one function).
>
> **Implementation requirements**, so the tie-break is a contract rather than an accident:
>
> 1. Pivot on the largest remaining column norm; on an exact tie, select the **lowest column index**. Document it; test it with a deliberately tied matrix.
> 2. Downdate column norms incrementally, but **recompute from scratch** when a downdated norm falls below `~1e-8 ×` its original — the standard LINPACK-style safeguard against catastrophic cancellation. Without it, pivots on ill-conditioned input drift from the reference.
> 3. Test against `scipy.linalg.qr(pivoting=True)` on ≥5 matrices including one rank-deficient and one tied-norm case. Compare the **permutation**, not just `Q`/`R` — sign conventions differ between implementations and are not a defect.

**C-2 · Exchange-method determinism.** The spec flags this as a risk. Measure it: 3 canonical matrices × 5 seeds × 2 repeat runs. Report whether `selected_indices` is seed-stable *and* run-stable. Precedent for the finding you might get: v0.34c's target function looked deterministic and was not.

**C-3 · Freeze the reduction threshold from data.** The spec says "strictly reduces condition number vs a random-selection baseline." Measure the *distribution* over ≥20 random baselines per matrix and freeze against a percentile, not a single draw — the v0.34c lesson.

### 5.3a v0.35b gate results — **B-3 and B-4 changed the contract** ✅

Run 2026-07-29 before implementation.

| Gate | Outcome |
|---|---|
| **B-1** | **Risk W-2 does not materialize.** All 13 catalogue entries construct, validate, and strict-JSON round-trip, executing 5267 lines of `formula.py` and **zero lines of `symbolic.py`**. |
| **B-2** | **No public write-up exists** — no arXiv/DOI/Zenodo/preprint reference anywhere in the repo. Private-by-default applies. |
| **B-3** | The proposed a+c composition **does not classify symmetries**. See below. |
| **B-4** | **Catalogue data, not `SymmetryMethod` adapters** — and the v0.36 precondition had to be amended. See below. |

**B-1 detail.** `symbolic.py`'s uncovered region 197–226 is `to_sympy_component_expressions`, which takes a `GeneratorFamily` (polynomial-basis form) and requires sympy. `PointSymmetryEntry` uses `FormulaGeneratorFamily`, which lives in `formula.py` and carries its own evaluator. Different type, different path — the registry never reaches the weak module. Registry coverage is **100%**.

**B-3 finding — the usefulness metric never consults the symmetry.** Keying the classification on `ρ_IR < 1` put **all three supported PDEs in the same bucket**, and sweeping all ten two-element supports of the canonical heat design, only **1 of 10** reached the useful branch:

| PDE | ρ_IR at the canonical support | verdict |
|---|---|---|
| heat_1d | 2.743 | valid_but_not_useful |
| burgers_1d | 2.194 | valid_but_not_useful |
| advection_diffusion_1d | 1.178 | valid_but_not_useful |

The cause is structural: **ρ_IR is a property of the design matrix and support — it never consults the symmetry at all.** v0.35a and v0.35c classify *designs*, not *symmetries*. A classification whose verdict does not depend on the thing being classified is a constant.

**Frozen:** the two axes come from different places. **Validity is a property of the symmetry** and is a *required caller input* from the existing verification machinery — never inferred. **Usefulness is a property of the design** and comes from v0.35a. This is exactly the structure of the wedge example (`validation.conclusion`, then `downstream_workflow`), so it composes what exists rather than adding scope. Both branches are reachable and tested — the useful branch at the measured ρ_IR = 0.9634.

Expect the wedge to be wide: at the canonical weak-form configuration every supported PDE reports ρ_IR > 1, so a symmetry that validates there is `valid_but_not_useful`. That is a finding about the design, not a defect.

**B-4 finding — the v0.36 precondition could not be satisfied as written.** `SymmetryMethod` requires `fit(field, ...)`: an algorithm that *discovers* a generator from data. A catalogued point symmetry is analytically known and discovers nothing. Registering the catalogue would mean a `fit()` that ignores its input, and would make `list_symmetry_methods()` report 14 methods of which 13 never read the data they are handed.

**Resolved (team decision):** catalogue ships as data in `pdelie.symmetry._point_symmetry_registry`; `SymmetryMethod` keeps exactly one built-in and its `fit()` semantics intact.

Consequence, recorded rather than papered over: **v0.35.0 success criterion 4 — "the `SymmetryMethod` contract now has multiple entries" — is NOT met**, and [`ROADMAP.md`](ROADMAP.md) has been amended. The v0.36 line previously gated the Ko infinitesimal-generator port on the registry "having proven the multi-method contract"; that precondition is dropped, and **the Ko infinitesimal-generator port is itself what proves it**. v0.36 is unblocked — it is the proof, not the beneficiary of one.

### 5.3 v0.35b gates — detail

**B-1 · Coverage probe before schema freeze.** `PointSymmetryEntry.generator_formula` is typed as `FormulaGeneratorFamily` (`symmetry/formula.py:265`, module at 79%, backed by `symbolic.py` at 67%). Construct one entry per planned catalogue symmetry and confirm the construction path is exercised. If it lands in `symbolic.py:197-226` (uncovered), that region needs tests **before** the registry depends on it.

> ### 🔴 B-2 · Public-write-up check — default to private
>
> The team's instruction inverts the spec's mitigation, and it is the right inversion. The spec treats underscore-private as a fallback "invoked at close." **Make `pdelie.symmetry._point_symmetry_registry` the default plan at kickoff.** Un-privatising is a one-line follow-on PR; retracting a public API is not.
>
> Precedent: the v0.30.1 `SymmetryCandidate` reserved discriminators shipped reserved-but-unconstructable, and v0.32a hardened them from warning to `ScopeValidationError` without breaking anyone — because nothing public depended on them yet.

**B-4 · Success criterion 4 needs a definition.** *"The v0.30.1 `SymmetryMethod` contract now has multiple entries"* — the registry (`symmetry/registry.py`, 80%) currently has exactly one built-in, `polynomial_translation_svd`. Whether catalogue entries **register as `SymmetryMethod` adapters** or merely **exist as catalogue data** is unresolved in the spec. These are different amounts of work and different invariant surfaces. Settle before freeze.

---

## 6. Day-0 actions

### 6.1 Housekeeping — stale local branches ✅ **done**

Verified by **patch identity** (`git cherry origin/main <branch>`), not merge status, per protocol. All five returned `-` — an equivalent patch exists upstream — and were then deleted:

| Branch | Commit | Verdict |
|---|---|---|
| `feat/v0.34a-variable-coefficient-residuals` | `8da63f6` | contained (#118) |
| `feat/v0.34b-admissibility-scoring` | `7061bdb` | contained (#119) |
| `feat/v0.34c-column-normalized-weak-stlsq` | `498118a` | contained (#117) |
| `release/v0.34.0` | `dcd03cf` | contained (#120) |
| `release/v0.33.0` | `e901300` | contained |

Two notes:

1. **The v0.34c branch name in the memo was approximate** — actual name `feat/v0.34c-column-normalized-weak-stlsq`. Verified and deleted under its real name.
2. **A naive "empty diff vs main" check is the wrong test and reports these as unsafe.** `git diff origin/main..<branch>` on `feat/v0.34a` shows 24 files / 1322 deletions — but that is main's *subsequent* work (v0.34b, v0.34c, the release close) appearing as deletions when read in that direction. Patch identity is the correct containment test for squash merges. Recording this so the next housekeeping pass does not conclude these branches held unmerged work.

> **Finding H-1 (backlog, beyond the memo).** After deleting the five, **25 local branches remain, and 21 of them are also fully contained in main** — every `feat/v0.30.1*` through `feat/v0.33c` branch, plus `docs/v0_2-readiness` and `release/v0.31.x` (both zero unique commits). Only three carry unique commits: `backup/feat-v0_2-burgers-before-rebase` (3), `backup/local-main-diverged` (3), `polish/v0.32.0-plan-header-complete` (2).
>
> Not deleted — outside the memo's scope. **Recommend a single housekeeping pass clearing the 21 contained branches** and a decision on whether the two `backup/*` refs are still wanted. The three with unique commits should be inspected before any deletion.

### 6.2 README guard tightening — blocking, tiny PR

Current, at `tests/test_current_release_gate.py:63-69`:

```python
assert ("V0.33" in readme or "v0.33" in readme
        or "V0.34" in readme or "v0.34" in readme)
```

The team's diagnosis is exact: this accepts four variants across two release lines. A README advertising **v0.33** passes while the package is **v0.34** — which is the same class of hole that let v0.33.0 ship a README pointing at v0.32.0.

Replacement, coupling the guard to `pyproject.toml`:

```python
current = pyproject["project"]["version"]              # "0.35.0"
major_minor = ".".join(current.split(".")[:2])         # "0.35"
assert f"v{major_minor}" in readme or f"V{major_minor}" in readme, (
    f"README does not advertise the current release line v{major_minor}"
)
```

**One addition beyond the team's version:** also assert the README's install-pin examples reference the current tag. v0.33.0's README was stale in *two* places — the prose line and four `@v0.32.0` pip pins. The proposed guard catches the prose only.

```python
assert f"@v{current}" in readme, (
    f"README install examples do not pin the current tag v{current}"
)
```

Ship as a polish PR against `main` before v0.35a branches — same shape as #108 was for v0.32.0.

### 6.3 Advisory-job promotion — **deferred to the v0.36 close, not day-0**

Findings G-1 and G-2 are real, and the decision on them is: **leave as-is for now.**

Rationale, recorded so it is not re-argued: promoting a job from advisory to blocking changes the merge criterion for everyone, which is a materially bigger call than the two one-line CI-correctness fixes the day-0 PR carries. And the risk is not currently live — coverage sits at **84.36%** against a `fail_under = 80` floor, so there is 4.36 points of headroom and no near-term danger of silently breaching it. A polish PR is the wrong vehicle for a policy change.

**Carried to the "hygiene to promote at v0.36 close" list:**

| Item | Current | Proposed at v0.36 |
|---|---|---|
| `coverage` job | advisory; `fail_under = 80` configured but unenforced | blocking at the floor already configured |
| `typecheck` job | advisory; 147 standing errors | delta-check that fails only if the count *increases* — regression protection without third-party-stub fragility |

The `typecheck` shape matters: promoting it outright at 147 would fail CI on any new error including ones originating in third-party stubs, which is why v0.30.1a deliberately promoted `lint` alone. A delta-check gets the protection without the fragility.

**Not deferred, and shipping day-0:** the toolchain pins in §6.4. Those are not policy changes — they make the *existing* gates reproducible, which is a correctness fix to a gate that already blocks.

### 6.4 Pin the lint toolchain — small, and it belongs with the README PR

Per Finding G-3. One line in `pyproject.toml:77`:

```diff
- "ruff>=0.6",
+ "ruff~=0.16.0",   # pinned: `lint` is blocking, so the linter version is part of the gate
```

Rationale worth stating once, because it generalizes: **the version of a tool that gates merges is part of the gate's contract.** An unpinned blocking linter means the merge criterion changes without anyone editing it — which is the same property that made the v0.34c weak-form diagnostic unpinnable, arriving through the dependency resolver instead of the RNG.

Ship alongside the README guard in the same day-0 polish PR; both are one-line CI-correctness fixes with no runtime effect. Note this pins only `[test]` — **core stays `numpy>=2,<3`**, unaffected.

---

## 7. The `CoefficientField` audit the team asked for

**Finding: `CoefficientField` does not exist anywhere in the repo** — not in `src`, `docs`, or `configs`. It is a name from the v0.34a design discussion, not shipped code.

What exists instead is the informal `parameter_tags` path, and it is doing real work:

| Tag | Shipped in | Consumed by |
|---|---|---|
| `nu_profile_kind` | v0.33d | v0.34a dispatch |
| `nu_form` / `c_form` | v0.33d | v0.34a operator selection |
| `nu_treatment_policy` | v0.33d | v0.34b (extension point) |
| `nu_min` / `nu_max` / `nu_l2_norm` | v0.33d | v0.34a uniform read path |
| `nu_profile_hash` | v0.33d | provenance |

**Decision: do not formalize.** *"Don't formalize what's already load-bearing until measurement shows the informal shape has broken something."* Nothing has broken: v0.34a consumed these tags across three evaluators and two equation forms with no shape problems, and both `_coefficient_profiles.py` and `_variable_coefficient.py` sit at 97% coverage. **Formalizing is currently the risk, not deferring.**

The reasoning and the **four explicit revisit triggers** are recorded in [`docs/design/COEFFICIENT_FIELD_DEFERRAL.md`](../design/COEFFICIENT_FIELD_DEFERRAL.md) — deliberately a *design* doc rather than a section here, so the next maintainer finds it when they encounter the flat `parameter_tags` dict and reach for a dataclass, rather than having to re-derive the argument from a superseded planning file.

Triggers in brief — **none fires in v0.35**:

| | Trigger | v0.35 status |
|---|---|---|
| T-1 | An evaluator needs >3 coefficient fields (prefix convention becomes an unenforced schema) | no new evaluator; v0.35a/c take raw arrays |
| T-2 | Coefficient provenance must survive a symmetry action (the v0.34b equivalence reading) | v0.35b consumes `FormulaGeneratorFamily`, not coefficients |
| T-3 | Informal-path coverage <90% for two consecutive releases | at 97% |
| T-4 | 2-D contract widening lands (v0.37+) | out of v0.35 scope |

Re-check at the v0.35.0 close and record the outcome in the design doc rather than re-deriving it.

---

## 8. Standing invariants for every v0.35 PR

Non-negotiable; each has a live test:

- Frozen four `method_scores`: `{span_distance, residual_l2, error_curve_max, svd_condition_number}`
- `_CONFIDENCE_LABELS` vocabulary
- `discovery_task_result` — exactly **22** top-level keys
- `pdelie_weak_pde_library_diagnostic` — exactly **27** default keys (28 on the opt-in `column_normalize` path only)
- `VerificationReport.classification` ∈ `{exact, approximate, failed}`
- `SymmetryCandidate` reserved discriminators
- Root `pdelie` namespace — **no new root exports**; v0.35 is submodule-only
- `ResidualBatch` top-level shape
- Every new report: strict-JSON, `diagnostic_only = True`
- **No pinned metric compared with `==`** — `rtol=1e-6` floor, cross-BLAS

### 8.1 New-package conventions (from v0.34c's precedent)

1. Pure-NumPy where possible; no backend import at module level.
2. Report shape: `metric_name`, `metric_value`(s), `interpretation`, `warnings`, `diagnostic_only`.
3. Validate at entry, before numerical work — `ShapeValidationError` for shape, `ScopeValidationError` for scope/finiteness.
4. Fixture + named-cause regeneration CLI, modelled on `tests/_helpers/regenerate_golden_fixture.py`.
5. Docstring records the *measurement* that justified any constant, not just its value.

---

## 9. Risk register

| ID | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-1 | scipy/core mismatch blocks `pdelie.design` | **Certain** — measured | High | **RESOLVED** — hand-rolled Householder QR (G&VL §5.4); scipy test-side only |
| R-2 | v0.34c weak matrix irreproducible for A-1 | **Certain** — W-4 | Medium | **RESOLVED** — v0.35a lands `v0_35a_canonical_design_matrix.npz` at seed 20340 |
| R-3 | Exchange method non-deterministic | Medium | High | Gate C-2; seed + documented tie-break |
| R-4 | `FormulaGeneratorFamily` path under-tested | Medium | High | Gate B-1 before schema freeze |
| R-5 | Write-up not public at v0.35b | Medium | High | Gate B-2; private-by-default |
| R-6 | Coverage regresses invisibly in greenfield | Medium | Medium | **Accepted for v0.35** — 84.36% vs floor 80; promotion deferred to v0.36 close |
| R-7 | RE-constant definition ambiguity | High | Medium | Gate A-3; freeze one, cite it |
| R-8 | Two new `summary_type`s bloat `summaries.py` | Medium | Medium | W-1; standalone modules |
| R-9 | Registry-vs-`SymmetryMethod` scope unresolved | **Certain** — unresolved | Medium | Gate B-4 before freeze |
| R-10 | Unpinned `ruff` fails `main` with no code change | Medium | High — blocks all merges | §6.4; pin `ruff~=0.16.0` |

---

## 10. Open questions for the team

**Resolved at day 0** (2026-07-29) — recorded so the reasoning is not re-argued:

| | Question | Resolution |
|---|---|---|
| ~~1~~ | C-1 QR-pivot strategy | **Hand-roll** Householder-with-pivoting per G&VL §5.4; scipy stays a test-side oracle. §5.2 |
| ~~2~~ | Promote `coverage` / `typecheck`? | **Deferred to the v0.36 close.** Not a polish-PR decision; 84.36% vs floor 80 is not at risk. §6.3 |
| ~~5~~ | README guard: prose only, or pip pins too? | **Both.** The v0.33.0 staleness was two-dimensional; a prose-only guard closes one. §6.2 |
| ~~6~~ | Pin `ruff`? | **Yes, plus `mypy`** — its `>=1.11` floor had already drifted to 2.3.0 in CI. §6.4 |
| ~~7~~ | `CoefficientField` | **Do not formalize.** Four revisit triggers recorded in the design doc; none fires. §7 |

**Still open — these gate their sub-milestones:**

1. **B-4** — do registry entries register as `SymmetryMethod` adapters, or are they catalogue data only? Different work, different invariant surface. Must settle before the v0.35b freeze.
2. **B-2** — is the taxonomy write-up public? **If unknown at kickoff, private-by-default proceeds without further discussion** — this is not a blocking question, it is a question whose default is already decided.

---

## Appendix A — measurement commands

```bash
# coverage with the configured floor
python -m pytest -q --cov=src/pdelie --cov-report=term

# mypy delta against the standing 147
python -m mypy src/pdelie 2>&1 | tail -1

# per-file mypy concentration
python -m mypy src/pdelie 2>&1 | grep "error:" | cut -d: -f1 | sort | uniq -c | sort -rn

# CI blocking-vs-advisory audit
grep -B2 "continue-on-error: true" .github/workflows/ci.yml

# regenerate the v0.34c weak matrix for gate A-2
python -c "
from tests._helpers.conditioning_ratios import CONDITIONING_SEED
print('seed =', CONDITIONING_SEED)"
```

## Appendix B — provenance

Every figure in this document was measured against `c0aa1e0` (tag `v0.34.0`) on 2026-07-29. Where this document and a planning document disagree, this document states the measured value and names the disagreement. Nothing here is carried forward from a roadmap without re-measurement — which is the discipline the v0.34c finding earned.
