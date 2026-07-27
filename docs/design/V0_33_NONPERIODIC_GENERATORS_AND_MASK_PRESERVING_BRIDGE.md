# V0.33 — Nonperiodic Interior-Symmetry and Mask-Validity Support (design freeze)

**Status:** FROZEN by v0.33 planning kickoff; **amended** before v0.33a implementation — see the "Claim scope" section below (claim-scope narrowing) and the v0.33c section (three-mask decomposition). Machine-readable form: [`configs/planning/v0_33_scope.json`](../../configs/planning/v0_33_scope.json). This document is the design freeze; the runtime lands under sub-milestones v0.33a / v0.33b / v0.33c and consolidates at v0.33.0 per the solo-dev consolidation policy.

**Decision label:** `v0_33_nonperiodic_generators_and_mask_preserving_bridge` (unchanged — a stable identifier, not a claim; the file path is likewise retained so existing cross-references keep resolving).

## Claim scope

v0.33 was originally titled "Nonperiodic generator support." That overclaims, and the title is now narrowed to **nonperiodic interior-symmetry and mask-validity support**.

What v0.33a/b actually establish, and what they do not:

| Established | **Not** established |
|---|---|
| The candidate is a symmetry of the **differential equation** as evaluated on interior rows. | That the candidate preserves the **boundary-value problem**. |
| The transformed and original fields agree on their **physical overlap** after an overlap crop. | That the transformation maps the domain to itself, or that boundary data is carried correctly. |
| Interior differential-operator covariance under the fitted generator. | Anything about the boundary rows the interior-only shave and the overlap crop discard. |

A uniform translation on a bounded domain is a **domain-changing action**: it maps `[0, L]` to `[ε, L + ε]`. Verifying residual agreement on the overlap says the differential operator is covariant there. It says nothing about whether the Dirichlet or Neumann data at the original boundary is respected — the overlap crop has removed exactly the rows that would answer that.

Reporting this as "nonperiodic symmetry supported" would therefore be an overclaim. v0.33a/b emit an explicit claim label (below) so the distinction is machine-readable rather than buried in prose.

## Purpose

v0.33 closes two long-standing wedge gaps that the v0.30–v0.32 arc did not reach:

1. **The nonperiodic generator gap.** v0.30 shipped nonperiodic `FieldBatch` readiness, boundary-condition metadata, and strong-form residuals via `compute_derivatives(backend="auto")`, but the **generator layer** — `fit_translation_generator`, `verify_translation_generator`, and the `polynomial_translation_svd` symmetry method — remains periodic-only. Callers with genuinely nonperiodic Heat / Burgers / advection-diffusion / reaction-diffusion fields cannot exercise the symmetry-diagnostics chain end-to-end.
2. **The discovery-bridge mask leakage.** `run_pysindy_pde_task` applies the input mask **before** differentiation, which means the mask can move through the derivative stencil and contaminate interior rows that PDELie already treats as clean. Any downstream optimizer sees a design matrix whose row-set differs from the row-set PDELie audited.

Both gaps have been named as reviewer objections. Both fit the wedge (empirical diagnostics on scalar 1D data) and do not require multi-D or new PDEs.

## Non-goals (frozen)

- **No new PDE.** Heat, Burgers, KdV, Fisher-KPP, advection-diffusion, reaction-diffusion — unchanged.
- **No new symmetry method.** Ko-sparse / LieGAN / LaLiGAN move to v0.34+.
- **No new `SymmetryCandidate` discriminator.** The seven reserved discriminators from v0.30.1 are unchanged.
- **No new `summary_type`.** All new diagnostics land inside existing `diagnostics` / `fit_diagnostics` dicts on existing summary types.
- **No `discovery_task_result` schema change.** Still 22 keys. Mask-related diagnostics live inside `fit_diagnostics`, not at the top level.
- **No noise-robustness claim. No WSINDy claim.** Column-normalized weak-form STLSQ is a separate v0.34 milestone.
- **No multi-D / 2-D contract widening.** Deferred to v0.4.
- **No root `pdelie` export. No package version bump until v0.33.0 release close.**
- **No hidden train/test policy invented on the caller's behalf.** Callers still partition trajectories explicitly.

## Sub-milestone structure

The v0.33 arc has three focus sub-milestones (a/b/c), two parallel scope-widenings (d/e), and one consolidation (v0.33.0):

| Sub-milestone | Focus | Rough scope |
|---|---|---|
| **v0.33a** | Nonperiodic dispatch in `fit_translation_generator` + `polynomial_translation_svd` | Boundary-condition-aware fit path; interior-only residual diagnostics; `bc_type` metadata on the diagnostics dict; periodic path byte-preserved. |
| **v0.33b** | Overlap-crop finite-transform verification | Nonperiodic dispatch in `verify_translation_generator`; overlap-fraction diagnostic; overlap-crop residual comparator. Delivers what v0.31.5 previously deferred. |
| **v0.33c** | Mask-preserving discovery bridge | `run_pysindy_pde_task` masks **after** differentiation; new `fit_diagnostics.mask_application_stage` + `mask_row_count` + `unmasked_row_count` fields. `discovery_task_result` schema key-count invariant preserved (22 keys). |
| **v0.33d** (parallel scope-widening) | Variable-coefficient data-generator support | Add `diffusivity_profile: array \| callable \| None` (and analogous `advection_profile` for advection-diffusion) to the data generators. Profile recorded in `field.metadata["parameter_tags"]`. Constant-coefficient residuals + generators run unchanged against variable-coefficient data — the **admissibility crash test** — with no residual-side changes required. The residual-side ν(x) support is v0.34a. |
| **v0.33e** (parallel hygiene) | Golden-numbers regression gate | Frozen per-PDE derivative + residual + vertical-slice numerical fixtures pinned into the release-gate. Verifies that v0.30's FD-backend change, v0.30's `compute_derivatives(backend="auto")`, and v0.30's interior-only diagnostics did not silently shift numeric results downstream — and that no future release does either. Any drift emits a named cause on the diff. |
| **v0.33.0** | Release close consolidation | Single tag consolidating v0.33a-e. Version bump `0.32.0` → `0.33.0`. `V0_33_RELEASE_READINESS.md`. `support_matrix.v0_33.json`. Release-gate manifest consolidated `0.33` row. |

## v0.33a — Nonperiodic `fit_translation_generator` + `polynomial_translation_svd`

### Frozen dispatch shape

`fit_translation_generator(field, residual_evaluator, epsilon=...)`:

- Periodic (`is_x_periodic(field) == True`): unchanged. Byte-preserved. Uses spectral_fd derivatives.
- Nonperiodic (`is_x_periodic(field) == False`): dispatches through `compute_derivatives(field, backend="auto")` — the v0.30d auto-dispatcher already handles the finite-difference backend selection. Residual comparison is **interior-only** (drops one row on each spatial boundary). The generator fit itself uses the same SVD over the polynomial translation basis; the input matrix rows are those the interior-only mask keeps.

New keys added to the diagnostics dict returned by `fit_translation_generator` (already a strict-JSON `dict[str, Any]`):

- `boundary_condition_x`: one of `"periodic"`, `"dirichlet"`, `"neumann"`, `"open_unknown"`. Sourced from `field.metadata["boundary_conditions"]["x"]` via `pdelie._boundary.get_x_boundary_type`.
- `boundary_condition_dispatch_reason`: `"is_x_periodic_true"` | `"is_x_periodic_false_field_metadata"`. Explains which branch fired.
- `interior_only_reduction_applied`: `bool`. `True` on the nonperiodic branch (one-row shave each side); `False` on the periodic branch.
- `interior_only_row_count`: `int`. The number of rows retained after the interior-only shave. On the periodic branch this equals the full spatial row count.

### Amended by measurement: shave width and fallback suppression

Two items in the v0.33a draft did not survive measurement against all four supported PDEs. Both were re-frozen before implementation.

**1. The interior shave is `boundary_trim_width`, not one row.** The draft froze a 1-row shave and `interior_only_row_count = num_points - 2`. Measured `span_distance` against shave width (ceiling `√2` ≈ 1.4142):

| shave | Heat | Burgers | Reaction-diffusion | Advection-diffusion |
|---|---|---|---|---|
| 1 (drafted) | 1.13 | 1.40 | 1.25 | 0.78 |
| 2 | 1.13 | 1.40 | 0.98 | 0.81 |
| **4 (= `boundary_trim_width`)** | **0.0043** | 0.24 | 0.27 | 0.64 |

At a 1-row shave every PDE sits near the ceiling — the SVD recovers a direction nearly orthogonal to translation. The residual evaluator already trims `boundary_trim_width` rows on the FD path and translation corrupts the edge further, so a 1-row shave leaves contaminated rows dominating the design matrix. The shave is therefore **read from the residual diagnostics** rather than hardcoded, so it tracks the FD stencil rather than duplicating a constant that could silently diverge from it. `interior_only_row_count = num_points - 2 * boundary_trim_width`, and `interior_only_trim_width` is emitted so the reduction is auditable.

**2. The reference fallback is suppressed on the nonperiodic branch.** `_select_translation_coefficients` returns the reference coefficients when the SVD drifts *and* the constant basis is least-sensitive, which drives the emitted `span_distance` to exactly `0.0` — reporting a *perfect* translation generator regardless of the true drift. Measured at `num_points = 128` with the shave at `boundary_trim_width`:

| PDE | honest `svd_span_distance` | fallback fires? | emitted without suppression |
|---|---|---|---|
| Heat | 0.0043 | no | 0.0043 |
| Burgers | 0.242 | **yes** | **0.0** |
| Reaction-diffusion | 0.272 | **yes** | **0.0** |
| Advection-diffusion | 0.638 | **yes** | **0.0** |

Three of four PDEs would have reported a perfect fit on a substantially drifted one — the same inversion that made `span_distance` unusable as v0.33d's crash-test gate. On the nonperiodic branch the fallback is therefore skipped entirely: `fit_mode` stays `"svd"`, `reference_fallback_used` is `False`, and `fallback_reason` records `"reference_fallback_suppressed_on_nonperiodic_branch"`. **The periodic branch keeps the fallback unchanged**, so periodic behaviour is byte-preserved.

**Resolution caveat.** Convergence is real but PDE-dependent: Heat reaches `3.3e-4` by `num_points = 512` (clean second order), while Burgers is still at `0.12` at `num_points = 256`. Only Heat is well resolved below `num_points = 256`. v0.33a emits the honest number and a low-row warning rather than a hard resolution gate; callers must read `span_distance`, which is now trustworthy on both branches.

**Files.** Two of the three blocking gates live in `src/pdelie/symmetry/parameterization/polynomial_translation.py` (`build_translation_basis`, `apply_pointwise_translation`), which the draft's file list omitted; `translation_baseline.py` itself carried no gate.

### Frozen claim-label vocabulary

A fifth diagnostic key, `symmetry_claim`, records **what the run actually established** — orthogonal to the pass/fail classification, which is unchanged. Frozen vocabulary, exactly six values:

| Value | Meaning |
|---|---|
| `equation_symmetry_candidate` | A generator was fitted against the differential equation. No verification has been run. |
| `interior_overlap_verified` | The candidate was verified on the interior/overlap rows. The differential operator is covariant there. **This is not a BVP claim.** |
| `boundary_value_problem_preserved` | The transformation additionally preserves the boundary-value problem. **v0.33 never emits this** — no code path can currently establish it; reserved for v0.34+. |
| `boundary_value_problem_not_preserved` | The transformation demonstrably violates the boundary conditions. |
| `domain_changing_action` | The action maps the domain off itself (any nonzero translation on a bounded domain). Emitted alongside the overlap-crop path. |
| `inconclusive_boundary_metadata` | Boundary metadata is `open_unknown` or otherwise insufficient to classify. |

`boundary_value_problem_preserved` is reserved-but-unemittable in v0.33 on purpose: naming it now fixes the vocabulary so v0.34 does not have to widen a frozen set, while the absence of an emitting path makes it impossible to claim accidentally. A v0.33a test asserts no v0.33 code path emits it.

This key is **orthogonal metadata**. It does not alter `VerificationReport.classification`, whose vocabulary stays exactly `{exact, approximate, failed}`, and it introduces no new `summary_type` and no new `SymmetryCandidate` discriminator.

### Frozen invariant on `SymmetryCandidate`

The emitted `SymmetryCandidate` payload is unchanged — the seven reserved discriminators from v0.30.1 continue to apply. The candidate's `payload` remains a `GeneratorFamily` on both branches. Only the containing `SymmetryMethodResult.fit_diagnostics` grows.

### `polynomial_translation_svd` diagnostic surface

The built-in adapter forwards the four new diagnostic keys from `fit_translation_generator` verbatim into its `fit_diagnostics`. The frozen four score names (`span_distance`, `residual_l2`, `error_curve_max`, `svd_condition_number` — v0.32b) are preserved verbatim; the score values on the nonperiodic branch are computed on the interior-only rows.

## v0.33b — Overlap-crop finite-transform verification

### Motivation

Uniform periodic translation wraps the domain and preserves every row. Nonperiodic translation shifts the domain, so the translated field and the original field share only an **overlap region**; comparing on the full domain is a physically invalid operation because outside the overlap the translated field has no meaningful values.

The overlap-crop design was scoped for v0.31.5 and never implemented. It lands here.

### Frozen shape

`verify_translation_generator(field, generator, residual_evaluator, epsilon_values=..., min_heldout_initial_conditions=..., span_tolerance=..., dispatch=...)`:

- Periodic (`is_x_periodic(field) == True`): unchanged. Byte-preserved. Uses `_apply_uniform_translation` (FFT-based wrap).
- Nonperiodic: dispatches through the new `_apply_overlap_crop_translation(field, shift)` helper. The residual comparison is restricted to the overlap region; the report records the overlap fraction and the retained row count.

New keys added to `VerificationReport.diagnostics` (already `dict[str, Any]`):

- `boundary_condition_x`: same vocabulary as above.
- `dispatch_path`: `"periodic_fft_wrap"` | `"overlap_crop"`.
- `overlap_fraction`: `float` in `[0.0, 1.0]`. On the periodic branch: always `1.0`. On the nonperiodic branch: `1.0 - abs(shift) / domain_length` clamped to `[0.0, 1.0]`.
- `overlap_row_count`: `int`. On the nonperiodic branch: the number of spatial rows retained per epsilon in the overlap comparison.
- `symmetry_claim`: one of the six frozen values above. The overlap-crop branch emits `interior_overlap_verified` on success (never `boundary_value_problem_preserved`), `domain_changing_action` when the shift is nonzero on a bounded domain, `boundary_value_problem_not_preserved` on a demonstrated boundary violation, and `inconclusive_boundary_metadata` when the boundary type is `open_unknown`.

### Frozen invariant on `VerificationReport`

`classification` vocabulary unchanged: `"exact"` / `"approximate"` / `"failed"`. No new labels. The classification is computed the same way; only its inputs change (nonperiodic classification is based on the overlap-crop residual, not a full-domain residual). This is a documented weakening of the classification's meaning on nonperiodic data — `dispatch_path` and `symmetry_claim` together make it explicit.

A `classification == "exact"` on the overlap-crop path therefore means *"exact on the overlap"*, not *"exact as a symmetry of the boundary-value problem"*. `symmetry_claim` is the field that carries that distinction; consumers that report a symmetry as supported must read it.

## v0.33c — Mask-preserving discovery bridge

### Motivation

`run_pysindy_pde_task` today calls `pdelie._boundary.is_x_periodic` up front (a hard gate) and passes the field values to the discovery adapter with no separate mask propagation. Callers who assemble a masked training FieldBatch expect the mask's row-set to match the row-set that reaches the optimizer, but the derivative stencil widens the effective mask by `stencil_order` rows on each side. External optimizers that consume the design matrix see a set of rows that has been silently expanded compared to what PDELie audited.

### Frozen shape

`run_pysindy_pde_task(field, *, task_name, pysindy_model, ..., heldout_field=None, ..., mask_application=...)`:

- New kwarg `mask_application: Literal["before_differentiation", "after_differentiation"] = "after_differentiation"`. Default flips to the correct-by-construction "after" path. Callers who need the pre-v0.33 behavior for reproducibility can pass `"before_differentiation"` explicitly and get a warning.
- The differentiation call sees the full (unmasked) field values. After differentiation, the mask is applied to the design matrix — the row-set that reaches the optimizer is exactly the row-set the mask declares.

### The three-mask decomposition

The original freeze carried a single `mask_row_count` / `unmasked_row_count` pair. That is too coarse: it conflates *"the value is missing"* with *"the value is present but its derivative is not trustworthy"* with *"the row was dropped by split policy."* Three distinct masks are tracked instead, each strictly contained in the previous:

| Mask | Definition |
|---|---|
| **observation** | Points where the field value is actually available. |
| **derivative validity** | Points whose *full stencil footprint* lies inside the observation set — the observation mask eroded by the FD stencil half-width. |
| **regression row** | The derivative-validity mask after task/split policy filtering. This is the row-set the optimizer actually sees. |

Nesting is an invariant: `regression_row ⊆ derivative_validity ⊆ observation`. A v0.33c test asserts it directly.

New keys added inside `discovery_task_result.fit_diagnostics` (which is `dict[str, Any]`; adding keys does NOT change the outer 22-key schema):

- `mask_application_stage`: `"before_differentiation"` | `"after_differentiation"` | `"none"` (when no mask).
- `observation_mask_row_count`: `int`. Points where the field value is available.
- `derivative_validity_mask_row_count`: `int`. Points whose full stencil footprint lies inside the observation set.
- `regression_row_mask_row_count`: `int`. The above after task/split policy filtering; the row-set the optimizer receives.
- `mask_row_count_reduction_from_derivative_stencil`: `int`. `observation_mask_row_count - derivative_validity_mask_row_count` — the erosion attributable to the stencil, kept as the release-gate's leakage-regression signal.

This supersedes the drafted `mask_row_count` / `unmasked_row_count` pair, which are **not** shipped: they have no unambiguous meaning under the three-mask model, and v0.33c has not shipped, so there is no compatibility cost to dropping them before they exist.

### Spectral derivatives on partially-observed fields are hard-rejected

A spectral derivative is globally coupled: every output point depends on every input point through the FFT. On a partially-observed field this leaks unobserved values back into rows the mask declares "observed," which is precisely what the mask contract exists to prevent — and it does so invisibly, since the output array is fully populated and finite.

`run_pysindy_pde_task` therefore raises `ScopeValidationError` when a field carries a mask **and** the resolved derivative backend is `spectral_fd`. This is a hard rejection, not a warning: there is no correct way to interpret the resulting design matrix, so silently accepting it would produce a confidently wrong answer. Callers on masked data must use the finite-difference backend, whose stencil footprint is local and therefore erodible in a well-defined way — which is exactly what the derivative-validity mask records.

Note this interacts with `compute_derivatives(backend="auto")`, which selects `spectral_fd` for periodic data. A masked periodic field consequently hits the rejection; the caller must request `finite_difference` explicitly. That is the intended behaviour, not an oversight.

### Non-goals for v0.33c

- No change to the periodic-only enforcement gate. Nonperiodic PySINDy discovery via `run_pysindy_pde_task` remains blocked; `PySINDyDiscoveryUnsupportedBoundaryError` still fires. Callers who need nonperiodic PySINDy discovery still hit that error explicitly.
- No modification to `discovery_task_result` schema outside `fit_diagnostics`. The 22-key top-level count is a v0.31 invariant.
- No mask-propagation into `heldout_field`. Callers still supply an explicitly-masked heldout FieldBatch.

## v0.33d — Variable-coefficient data-generator support (parallel scope-widening)

### Motivation

PDELie's data generators (`generate_heat_1d_field_batch`, `generate_burgers_1d_field_batch`, `generate_advection_diffusion_1d_field_batch`, `generate_reaction_diffusion_1d_field_batch`) all take a **constant** coefficient today (`nu`, `c`, etc.). Extending them to accept a variable-coefficient profile (`nu(x)`, `c(x)`) is a small, self-contained data-side widening that unlocks two things independent of any residual-side change:

1. It gives PDELie a first-class way to generate variable-coefficient PDE data — a useful library primitive in its own right, and the natural next step after v0.30's boundary-condition metadata.
2. It exposes an **admissibility crash test**: constant-coefficient generators (like the built-in `polynomial_translation_svd`, whose ansatz assumes translation invariance) run **unchanged** against variable-coefficient data and are expected to fail. That failure is the diagnostic — empirical evidence that applying a translation candidate without first checking against x-dependent coefficients is worse than not augmenting at all. No residual-side changes are required to observe it.

The residual-side variable-coefficient support (a `HeatResidualEvaluator` that consumes `nu(x)`, similarly for Burgers / advection-diffusion) is the completing half of this story and lands in v0.34a as a separate sub-milestone. Splitting the data half here delivers the admissibility diagnostic in v0.33 without waiting for the residual-side rework.

### Frozen shape

New kwarg on the data generators (existing signatures byte-preserved when the kwarg is omitted):

- `generate_heat_1d_field_batch(..., diffusivity_profile: np.ndarray | Callable[[np.ndarray], np.ndarray] | None = None)` — `array` samples on the generator's `x`-grid; `callable` invoked as `diffusivity_profile(x)` and validated for finiteness and shape.
- `generate_burgers_1d_field_batch(..., diffusivity_profile: np.ndarray | Callable | None = None)` — same shape.
- `generate_advection_diffusion_1d_field_batch(..., advection_profile: np.ndarray | Callable | None = None, diffusivity_profile: np.ndarray | Callable | None = None)`.
- `generate_reaction_diffusion_1d_field_batch(...)` — deferred (its coefficient set is larger; the v0.33d scope is Heat / Burgers / advection-diffusion only).

`FieldBatch.metadata["parameter_tags"]` records the profile provenance:

- `nu_profile_kind: "constant" | "array" | "callable"`.
- `nu_profile_shape: [int]` (`array` case only).
- `nu_profile_hash: str` (`array` case only; SHA-256 of the values for deterministic provenance).
- `nu_profile_callable_repr: str` (`callable` case only; `repr(profile)`).
- `nu_min: float`, `nu_max: float`, `nu_l2_norm: float` — same three fields the `constant` case surfaces, so downstream diagnostics have a uniform read path.

The generator's numerical scheme uses the sampled `nu(x)` array (the callable path samples once, up-front). All finiteness / positivity / dimensionality checks fire the same way they do for the constant path.

### Non-goals for v0.33d

- No residual-side `nu(x)` support. `HeatResidualEvaluator` etc. still consume a scalar `nu`; feeding it a variable-coefficient FieldBatch is a documented misuse (`ScopeValidationError` on shape mismatch). The residual-side rework is v0.34a.
- No `polynomial_translation_svd` extension for variable-coefficient admissibility scoring. The built-in method runs unchanged; the failure IS the diagnostic.
- No `KdV` support (KdV has a more complex coefficient structure; deferred).
- No new `summary_type`, no new `SymmetryCandidate` discriminator, no root export.

### Test-case surface (v0.33d)

- Constant `diffusivity_profile=None` byte-preserves the constant-coefficient path.
- `diffusivity_profile=np.array([...])` records `nu_profile_kind="array"` + `nu_profile_hash` + `nu_min`/`nu_max`/`nu_l2_norm`.
- `diffusivity_profile=callable` records `nu_profile_kind="callable"` + `nu_profile_callable_repr`.
- Shape mismatch on the array path raises `ShapeValidationError` before any generator call.
- Non-finite / non-positive `nu(x)` raises `ScopeValidationError`.
- Constant-coefficient `polynomial_translation_svd` on a variable-coefficient field runs to completion (does not raise) and reports a **`residual_l2` at least 10× the constant-coefficient baseline** — the crash test.

### The crash test asserts `residual_l2`, not `span_distance`

The planning draft specified `span_distance` for this assertion. Measurement before implementation showed it cannot carry it, for two compounding reasons:

1. **`span_distance` is bounded.** `normalize_translation_coefficients` returns a unit vector with a non-negative leading component and the reference is `[1,0,0,0]`, so `span_distance = sqrt(2 - 2·a[0]) ∈ [0, √2]`. Any multiplicative gate has a hard ceiling at 1.4142.
2. **The reference fallback zeroes it.** `_select_translation_coefficients` discards the SVD result and returns the reference coefficients when the SVD drifts *and* the constant basis is the least-sensitive direction. `span_distance` is then exactly `0.0` — the method reports a **perfect** translation generator precisely where it should fail hardest. A `span_distance`-based gate does not merely miss the failure; it asserts the opposite of the truth.

Measured across grid `{32, 64, 128}` × seed `{0, 1, 7}` × batch `{1, 2}` on the frozen profile:

| Candidate gate | Configurations separated | Worst ratio |
|---|---|---|
| `span_distance ≥ 10×` | 8 / 18 | **0.0** (inverted) |
| `reference_fallback_used` | 12 / 18 | — |
| `svd_span_distance ≥ 10×` | 18 / 18 | 1402× |
| **`residual_l2 ≥ 10×`** | **18 / 18** | **1772×** |

`residual_l2` is the chosen gate: it separates every configuration with ~177× of headroom, and it is already one of the frozen four score names on the public `polynomial_translation_svd` surface, so the assertion needs no new diagnostic. (`svd_span_distance` is also robust but is not forwarded into the method's `fit_diagnostics`; exposing it would widen a surface this sub-milestone's non-goals put out of scope.)

`tests/test_v0_33d_variable_coefficient_generators.py::test_span_distance_is_not_a_usable_crash_gate` pins the inverted behaviour, so a future selection-policy change that makes `span_distance` usable will fail that test and prompt revisiting this choice.

### Frozen crash-test profile

`nu(x) = nu_0 · (1 + 0.5 · sin(2πx/L))` — slowly varying, strictly positive, and with mean equal to the constant reference, so the measured failure is attributable to x-dependence rather than to a shifted average coefficient. Observed `residual_l2` ratios with the shipped generators: Heat 1819×, Burgers 22025×, advection-diffusion 1561×.

### Equation form is selected, not assumed

The equation form is an explicit kwarg and a recorded tag, because `∂ₓ(ν(x) ∂ₓu)` and `ν(x)·u_xx` are different operators for any `ν(x)` and a residual evaluator cannot recover which one produced the data:

| Kwarg | Values | Tag | Default |
|---|---|---|---|
| `diffusivity_form` | `conservative_divergence`, `nonconservative_nu_uxx` | `parameter_tags["nu_form"]` | `conservative_divergence` |
| `advection_form` (advection-diffusion only) | `conservative_divergence`, `nonconservative_c_ux` | `parameter_tags["c_form"]` | `nonconservative_c_ux` |

Both values of each selector are implemented, not merely recorded. Divergence form is the diffusive default because it is conservative — it preserves the spatial integral of `u` for periodic data at any `ν(x)`. The advective default is non-conservative because that is what `AdvectionDiffusionResidualEvaluator` models with a scalar `c`. Unknown values raise `ScopeValidationError` before any numerical work. **This tag is the v0.34a residual-evaluator dispatch key.**

The two diffusive forms coincide analytically for constant `ν`, so selecting either leaves the byte-preserved constant path untouched — asserted per-PDE in `test_form_selection_does_not_disturb_the_constant_path`.

### Coefficient treatment policy

`parameter_tags["nu_treatment_policy"]` is emitted with the single v0.33d value `"fixed_background"`: the coefficient field is a fixed background that does **not** co-transform under a symmetry transformation. v0.34b extends the vocabulary with `"co_transforming_equivalence_target"` for the symmetry-breaking-versus-equivalence benchmark. It is emitted now rather than retrofitted so that v0.33d-generated payloads are already self-describing when that benchmark lands.

### Constant paths are left literally unchanged

Heat and advection-diffusion have closed-form constant-coefficient paths (an analytic Fourier series and an exact spectral multiplier respectively) that do not generalise to `ν(x)`, so their variable paths integrate with RK4 from the same initial condition. Those constant-coefficient paths are left literally unchanged rather than re-expressed as a special case of the variable path — routing a constant array through the variable scheme is not bit-identical, and byte-preservation is an exit gate.

### Dose-response

`tests/fixtures/v0_33d_admissibility_dose_response.json` pins the curve behind the binary gate, so the admissibility claim can be cited rather than merely asserted. Family `ν_α(x) = ν₀(1 + α·sin(2πx/L))`, `α ∈ {0, 0.1, 0.25, 0.5, 0.75}`, measured as `residual_l2` ratio against the constant-coefficient reference:

| α | Heat | Burgers | Advection-diffusion |
|---|---|---|---|
| 0.00 | 1.0× | 1.0× | 1.0× |
| 0.10 | 372× | 4470× | 303× |
| 0.25 | 920× | 11107× | 766× |
| 0.50 | **1819×** | **22025×** | **1561×** |
| 0.75 | 2724× | 32826× | 2395× |

`α = 0` is the control: the profile is a constant *array*, so it routes through the RK4 variable path rather than the closed-form path. Its ratio of 1.0× shows the variable-coefficient scheme reproduces the closed-form result when `ν` is constant — which is what makes the growth at `α > 0` attributable to x-dependence rather than to having switched numerical schemes. The curve is asserted strictly increasing per PDE.

This is a separate fixture from `v0_33e_golden_numbers.json` by design: the dose-response *requires* the v0.33d generators, so it cannot live in a v0.33e artifact that pins the constant-coefficient pipeline. The v0.33e fixture, schema, and regeneration CLI are untouched. Regenerate with `python -m tests._helpers.admissibility_dose_response --reason "<named cause>"`.

## v0.33e — Golden-numbers regression gate (parallel hygiene)

### Motivation

v0.30 shipped three numerically-load-bearing changes: a `finite_difference` derivative backend, the `compute_derivatives(backend="auto")` dispatcher, and interior-only residual diagnostics for Heat / Burgers / advection-diffusion / reaction-diffusion. The existing per-version release-gate tests (`tests/test_v0_*_release_gate.py`) enforce **structural** invariants (schema shapes, forbidden root attributes, phrase presence) but do not pin the **numerical** outputs of the derivative / residual / vertical-slice pipelines. Downstream users who depend on a specific reproducible number (a residual RMS at a fixed seed, a verification `first_error` at a fixed epsilon) have no protection against silent drift.

v0.33e adds golden-numbers fixtures across every supported PDE and pins them into the release-gate. Any drift emits a named cause on the diff, so the release-close review can accept the change explicitly or investigate it as a regression.

### Frozen shape

New fixture file: `tests/fixtures/v0_33e_golden_numbers.json` (strict-JSON). Structure:

```text
{
  "summary_schema_version": "0.1",
  "summary_type": "pdelie_golden_numbers_fixture",
  "generator_seed": <int>,
  "batch_size": 1,
  "num_times": <int>,
  "num_points": <int>,
  "last_regeneration_reason": <str>,
  "pdes": [
    {
      "name": "heat_1d" | "burgers_1d" | "kdv_1d"
            | "advection_diffusion_1d" | "reaction_diffusion_1d",
      "generator_kwargs": {"max_time": <float>},
      "max_spatial_order": <int>,
      "boundary_condition_x": "periodic" | "dirichlet" | "neumann" | "open_unknown",
      "residual_l2_norm": <float>,
      "residual_rms": <float>,
      "residual_max_abs": <float>,
      "derivative_u_x_l2_norm": <float>,
      "derivative_u_xx_l2_norm": <float>,
      "derivative_u_t_l2_norm": <float>
    },
    ...
  ]
}
```

**Five PDE entries, not six.** The planning draft listed `fisher_kpp_1d` and `reaction_diffusion_1d` as separate PDEs; they are the same generator. `generate_reaction_diffusion_1d_field_batch` stamps `parameter_tags["equation"] == "reaction_diffusion_fisher_kpp"`, and `docs/specs/SUPPORT_MATRIX.md` carries a single **Fisher-KPP** row for it. The fixture pins the five distinct generators with public runtime support; KS is excluded by the same matrix (`no public runtime`).

**Per-PDE `generator_kwargs` and `max_spatial_order`.** Two parameters cannot live in the shared fixture header:

- `max_time` is numerically load-bearing and differs by an order of magnitude across PDEs — KdV is normalized short-horizon-only at `0.03`, Heat runs to `0.6`. Recording it per entry keeps the fixture self-describing and regenerable.
- `max_spatial_order` is per-PDE because `compute_derivatives` defaults to `2` while `KdVResidualEvaluator` requires `u_xxx`.

The shared header pins only what genuinely is shared: `generator_seed`, `batch_size`, `num_times`, `num_points`.

New test file: `tests/test_v0_33e_golden_numbers_regression_gate.py`. For each PDE, regenerate the reference FieldBatch under the pinned seed, run `compute_derivatives(field, backend="auto")` and the appropriate residual evaluator, and compare the resulting metrics against the fixture with a **tight** relative tolerance (`rtol=1e-6`, `atol=1e-12`). Any breach fails the release-gate with a diff message that names the drifted metric and the observed vs. expected values.

**Tolerance rationale.** `rtol=1e-6` is a cross-BLAS margin. Measured empirically: the fixture is generated on macOS (Accelerate/OpenBLAS) and replayed on the Linux CI runners (manylinux OpenBLAS), where the worst observed relative deviation on an unchanged pipeline is **1.5e-9** — roughly 650× of headroom under the tolerance. Within a single platform the reproduction is bit-exact across py3.12 and py3.13; **across** platforms it is not, and must not be asserted as such. `atol=1e-12` keeps near-zero metrics (e.g. residuals of exactly-integrated fields) above float64 denormal-and-cancellation noise. The underlying pipeline is float64 throughout (`_to_numpy` → `dtype=float`); the tolerances are **not** tied to float32 quantization.

Consequently **no test in the gate compares a pinned metric with `==`**, including the regeneration-integrity test. The only bit-exact comparisons are of non-metric structure (names, ordering, `generator_kwargs`, `max_spatial_order`, `boundary_condition_x`), of carried-over entries on the `--pde` path (which are copied, not recomputed), and of repeat evaluation within a single process.

Only **aggregate norms** are pinned — never element-wise values. BLAS reduction order differs across the Linux and macOS wheels, so element-wise equality is not a portable invariant while aggregate norms at `rtol=1e-6` are. `np.random.default_rng(seed)` is stable across NumPy 2.x and is kept as the generators' seeding path.

### Regeneration workflow

`tests/_helpers/regenerate_golden_fixture.py` is the single source of truth: it holds the frozen spec table, the metric computation, and the regeneration CLI. The gate test imports the same table, so the fixture can never drift from the configuration the gate replays.

```bash
# Regenerate every entry.
python -m tests._helpers.regenerate_golden_fixture --all \
    --reason "v0.30d FD-backend stencil widened to 4th order"

# Regenerate one PDE; the other four entries are carried over verbatim.
python -m tests._helpers.regenerate_golden_fixture --pde kdv_1d \
    --reason "KdV dealiasing cutoff changed from N/3 to 2N/5"
```

`--reason` is mandatory and is recorded in the fixture's `last_regeneration_reason` field. The gate asserts the field is non-empty, and `test_full_regeneration_reproduces_the_committed_fixture` asserts a no-op `--all` regeneration reproduces the committed numbers exactly — so the fixture cannot be hand-edited into agreement.

**`--all` vs `--pde`.** For cross-cutting numerical changes (FD backend, residual formulas, generator schemes), use `--all` so every PDE lands on the new code state atomically. Use `--pde <name>` only for isolated changes to a single PDE's generator or evaluator. If unsure, use `--all` — a full regeneration is cheap. A targeted regeneration against a cross-cutting change is not silently wrong: the carried-over entries fail on the next CI run with a named metric and drift value.

### Update policy

- On a legitimate numerical change (a bug fix in the FD backend, a new spectral cutoff), the release-close PR regenerates the fixture and records the cause in the CHANGELOG entry.
- No unnamed drift. If a metric moves by more than the tolerance without a named cause in the diff, the release-gate fails and the PR must document why.

### Non-goals for v0.33e

- No coverage-goal change. The existing `coverage` CI job stays advisory.
- No new `summary_type`.
- No new PDE (Heat / Burgers / KdV / Fisher-KPP / advection-diffusion / reaction-diffusion — the existing set).
- No golden fixtures on nonperiodic-x boundary conditions **until** v0.33a lands; the initial v0.33e fixture is periodic-only. Nonperiodic golden fixtures land alongside v0.33a as part of the same sub-milestone.

## Test-case surface (to be authored in v0.33a-e)

At consolidation the v0.33.0 release-gate must include the 20 cases below plus the v0.33d and v0.33e test surfaces documented in those sections:

1. Periodic fit_translation_generator byte-preserved (regression guard on the periodic branch).
2. Nonperiodic Dirichlet Heat: `boundary_condition_x = "dirichlet"` in `fit_diagnostics`.
3. Nonperiodic Neumann Burgers: same.
4. Nonperiodic open_unknown reaction-diffusion: same.
5. `polynomial_translation_svd` frozen four score names preserved on both branches.
6. Periodic verify_translation_generator byte-preserved.
7. Nonperiodic verify_translation_generator emits `dispatch_path = "overlap_crop"` + `overlap_fraction` in `[0.0, 1.0]`.
8. Overlap-fraction monotonicity: larger `abs(shift)` ⇒ smaller `overlap_fraction`.
9. `run_pysindy_pde_task(mask_application="after_differentiation")` emits `mask_row_count < unmasked_row_count` on a genuinely-masked field.
10. `run_pysindy_pde_task(mask_application="before_differentiation")` emits a warning naming the leakage risk.
11. `discovery_task_result` still exactly 22 top-level keys.
12. `VerificationReport.classification` vocabulary unchanged: still exactly `{exact, approximate, failed}`.
13. `SymmetryCandidate` reserved discriminators unchanged.
14. No new root `pdelie` export.
15. No new `summary_type`.
16. Strict-JSON round-trip on every new diagnostic dict.
17. `_CONFIDENCE_LABELS` invariant (v0.20 vocabulary) unchanged.
18. `boundary_condition_x` vocabulary is exactly the v0.30d frozen `{periodic, dirichlet, neumann, open_unknown}` — no new values.
19. Interior-only diagnostics on the nonperiodic fit path align with the v0.30d interior-only residual diagnostics reported by `HeatResidualEvaluator` etc.
20. Overlap-crop verification result depends only on the overlap region — no boundary rows leak into the L2 comparison.

## What v0.33 does NOT unlock

- **Nonperiodic KdV.** KdV remains periodic-only (fourth-derivative stencil on nonperiodic data is a separate deferred item).
- **Nonperiodic PySINDy discovery.** The v0.33c mask fix does not lift `PySINDyDiscoveryUnsupportedBoundaryError`.
- **Nonperiodic weak-form residual.** `weak_1d` stays periodic-only.
- **A new PDE / new symmetry method / new dataset.**

## References

- [`configs/planning/v0_33_scope.json`](../../configs/planning/v0_33_scope.json) — machine-readable frozen scope.
- [`docs/design/BOUNDARY_CONDITION_SPEC.md`](BOUNDARY_CONDITION_SPEC.md) — v0.30 boundary-condition metadata design that v0.33a builds on.
- [`docs/design/DERIVATIVE_BACKEND_POLICY.md`](DERIVATIVE_BACKEND_POLICY.md) — v0.30d `compute_derivatives(backend="auto")` policy that v0.33a leans on.
- [`src/pdelie/symmetry/fitting/translation_baseline.py`](../../src/pdelie/symmetry/fitting/translation_baseline.py) — v0.33a target.
- [`src/pdelie/verification/finite_transform.py`](../../src/pdelie/verification/finite_transform.py) — v0.33b target.
- [`src/pdelie/tasks/discovery.py`](../../src/pdelie/tasks/discovery.py) — v0.33c target.
