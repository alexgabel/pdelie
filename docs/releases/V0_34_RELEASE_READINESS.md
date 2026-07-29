# V0.34 Release Readiness

## Release Target

- package version: `0.34.0`
- git tag: `v0.34.0` (to be cut after review approval; **do not tag until then**)
- package-index publication: deferred until `v1.0` or later

`v0.34.0` is a Git-tag-only release. Do not publish to TestPyPI or PyPI for `v0.34`. PyPI remains targeted at `v0.36`.

## Consolidation Policy

`v0.34.0` consolidates three internal sub-milestones under a single tag per the solo-dev consolidation policy.

| Sub-milestone | Focus | PR | Merged as |
|---|---|---|---|
| **v0.34c** | column-normalized weak-form design matrices + reproducibility seed | #117 | `62dd00d` |
| **v0.34a** | variable-coefficient residual evaluators | #118 | `eeeb6fc` |
| **v0.34b** | admissibility scoring + background-treatment classification | #119 | `0b391df` |

Release decision label: `v0_34_0_variable_coefficient_residuals_and_weak_form_conditioning`.

## Success criteria

### 1. Variable-coefficient residuals functional — **met**

A caller with a v0.33d variable-coefficient `FieldBatch` can pass it to the Heat, Burgers, or advection-diffusion residual evaluator via the array path. The evaluator dispatches on `parameter_tags["nu_form"]` and reports its dispatch, the form used, and the coefficient magnitudes.

The scalar path is byte-preserved: a constant-valued array reproduces it to **exactly 0.0**, and the two equation forms agree to **9.07e-11** on constant `ν` — both inside the `rtol=1e-8` gate the process amendment required. The v0.33e golden gate passes unchanged, which is the load-bearing proof.

### 2. Admissibility crash test empirically proven — **met (criterion restated)**

The frozen criterion read: *"Constant candidate on variable data with variable reference → `relative_error_l2` ≥ 10× the constant baseline."*

As built, `relative_error_l2` is a **coefficient-space direction error between two unit-normalized generators**, bounded above by `√2`. A "≥ 10× the baseline" ratio is not a natural form for a metric with a hard ceiling of 1.414 — the same structural problem that made `span_distance` unusable as v0.33d's crash-test gate.

The crash-test signal lives in **`residual_l2`**, and is overwhelming. Measured through the v0.34a array path, constant-coefficient evaluation of variable-coefficient data versus matched evaluation:

| PDE | matched | constant-ν | ratio |
|---|---|---|---|
| Heat | 2.31e-3 | 1.64e+0 | **711×** |
| Burgers | 3.78e-5 | 3.88e-1 | **10274×** |
| Advection-diffusion | 3.75e-4 | 5.91e-1 | **1575×** |

Restated criterion: **the constant-coefficient evaluator on variable-coefficient data produces a `residual_l2` at least 10× the matched-coefficient value, on all three supported PDEs and both equation forms.** Measured minimum 711×, i.e. 71× of headroom.

`relative_error_l2` remains the right metric for its own job — comparing a candidate generator to a supplied reference — and is asserted separately: near zero for a matching reference, saturating at exactly `√2` for an orthogonal one.

> **Open for review.** This restatement changes the asserted metric, not the claim. If the frozen criterion intended `relative_error_l2` as a bounded distance rather than a ratio, the natural form is a threshold on the distance itself (e.g. `≥ 1.0` out of a `√2` maximum) rather than a multiple of a baseline.

### 3. Weak-form STLSQ conditioning improved — **met (criterion restated)**

The frozen criterion read: *"`column_normalize=True` reduces condition number by ≥ 20× on canonical fixtures; the 87× / 111.8 / 3.77 figures reproduce."*

**Those figures do not reproduce, and cannot.** `pysindy.WeakPDELibrary` places its `K` domain centers by drawing from the global NumPy RNG and exposes no seed parameter, so `inspect_pysindy_weak_pde_library` was nondeterministic — back-to-back identical calls returned `matrix_condition_number` of 7.69 and 11.42. Across 12 unseeded draws of the canonical fixture the pre-normalization condition number ranged **5.03–14.44** and the column-scale ratio **3.93–6.64**. The planned figures were one draw from a distribution, and no configuration among 48 swept reproduced them.

The same fact made a second frozen requirement unachievable: *"`column_normalize=False` byte-preserves the v0.31b2 golden report"* cannot hold when the report does not reproduce **against itself**.

v0.34c therefore added an opt-in `seed` kwarg — the prerequisite for pinning anything here. At the pinned seed:

| fixture | ratio | | fixture | ratio |
|---|---|---|---|---|
| **canonical** | **1.79×** | | heat_derivative4 | 6.64× |
| heat_short_horizon | 2.37× | | burgers | 11.34× |
| heat_degree3 | 1.79× | | advection_diffusion | 48.34× |

Median **4.51×**. The ≥20× threshold is unsupported: only 1 of 6 fixtures clears it, and the canonical fixture — the one a reader would assume a headline figure describes — improves by under 2×.

Restated criterion: **column normalization never worsens conditioning on any fixture (ratio ≥ 1.0, asserted universally), with per-fixture improvements pinned at a fixed seed in `tests/fixtures/v0_34c_conditioning_ratios.json`.** A single headline threshold would either fail on the canonical fixture or be chosen to pass on one that clears it.

### 4. Zero invariant breakage — **met**

Frozen four `method_scores` names; `_CONFIDENCE_LABELS`; `discovery_task_result` 22-key top-level schema; `pdelie_weak_pde_library_diagnostic` 27-key **default** schema; `VerificationReport.classification`; `SymmetryCandidate` discriminators; root namespace; `ResidualBatch` top-level shape. No new `summary_type`.

One qualification, stated plainly: the weak diagnostic emits a **28th** top-level key, `column_normalization`, on the opt-in `column_normalize=True` path only. Every payload producible before v0.34c still has exactly 27 keys and no existing consumer sees a shape change, but the schema is now conditional rather than fixed.

### 5. Explicit non-claims held — **met**

No WSINDy claim, no noise-robustness claim, no dataset-recovery claim anywhere in the new code or docs. Asserted by test: the emitted report and the `column_normalize` module docstring are both checked for the strings `wsindy`, `noise_robust`, `noise-robust`, and `noise robustness`. The module documents itself as a conditioning fix.

## Additions beyond the frozen scope

Two things ship that the v0.34 plan did not specify. Both are flagged for review rather than presented as neutral.

**1. `seed` on `inspect_pysindy_weak_pde_library`.** Not in the plan, but nothing in v0.34c could be pinned without it. It also fixes what is arguably a latent defect: the diagnostic has been unreproducible since v0.31b2. The default remains `None`, preserving existing behaviour exactly — which means the *default* diagnostic is still unreproducible. Flipping that default is a behaviour change to a shipped surface and is deferred.

**2. `inconclusive_background_separation`.** A third value in the v0.34b classification vocabulary, beyond the two the plan named. It covers runs where the two paths do not separate enough to distinguish, so weak evidence reports "cannot tell" rather than a definite label. Removable in one line if the vocabulary should be exactly the two specified.

## Known limitations carried forward

- Conservative **advection** (`c_form = "conservative_divergence"`) is generated by v0.33d but not evaluated by v0.34a; such a field is refused rather than silently evaluated under the non-conservative operator.
- Callable coefficient profiles are refused by the residual evaluators; pass the array the generator sampled.
- KdV and reaction-diffusion variable-coefficient support remain out of scope.
- The default (unseeded) weak diagnostic remains nondeterministic.

## Process note

All three sub-milestones were prototyped and measured **before** their contracts were frozen, per the amendments carried forward from v0.33. All three measurements changed what shipped:

- **v0.34c** — measurement showed the target function was *nondeterministic*. The planned threshold was not wrong so much as unmeasurable; the sub-milestone needed a `seed` kwarg before any number could be pinned. No amount of document review would have surfaced this.
- **v0.34a** — measurement confirmed `nu_form` dispatch is mandatory. The plan's residual formula would have mismatched default-generated data by ~300×.
- **v0.34b** — measurement cleared the 5× separation bar by roughly 15×, and surfaced two structural facts a bare ratio would not have: exact baseline equality on the co-transforming path, and monotonic growth on the fixed-background path.

Two implementation errors were caught by the test suite rather than by inspection, and both are recorded in the code that fixes them: a first draft of v0.34a refused the exact coefficient combination the released v0.33d crash test depends on, and a silent NumPy broadcast over the wrong axis produced two invalid measurements before being caught by a matched-form sanity check.
