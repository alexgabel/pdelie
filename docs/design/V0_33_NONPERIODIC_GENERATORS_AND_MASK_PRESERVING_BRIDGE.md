# V0.33 — Nonperiodic Generators + Mask-Preserving Bridge (design freeze)

**Status:** FROZEN by v0.33 planning kickoff. Machine-readable form: [`configs/planning/v0_33_scope.json`](../../configs/planning/v0_33_scope.json). This document is the design freeze; the runtime lands under sub-milestones v0.33a / v0.33b / v0.33c and consolidates at v0.33.0 per the solo-dev consolidation policy.

**Decision label:** `v0_33_nonperiodic_generators_and_mask_preserving_bridge`.

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

| Sub-milestone | Focus | Rough scope |
|---|---|---|
| **v0.33a** | Nonperiodic dispatch in `fit_translation_generator` + `polynomial_translation_svd` | Boundary-condition-aware fit path; interior-only residual diagnostics; `bc_type` metadata on the diagnostics dict; periodic path byte-preserved. |
| **v0.33b** | Overlap-crop finite-transform verification | Nonperiodic dispatch in `verify_translation_generator`; overlap-fraction diagnostic; overlap-crop residual comparator. Delivers what v0.31.5 previously deferred. |
| **v0.33c** | Mask-preserving discovery bridge | `run_pysindy_pde_task` masks **after** differentiation; new `fit_diagnostics.mask_application_stage` + `mask_row_count` + `unmasked_row_count` fields. `discovery_task_result` schema key-count invariant preserved (22 keys). |
| **v0.33.0** | Release close consolidation | Single tag consolidating v0.33a-c. Version bump `0.32.0` → `0.33.0`. `V0_33_RELEASE_READINESS.md`. `support_matrix.v0_33.json`. Release-gate manifest consolidated `0.33` row. |

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

### Frozen invariant on `VerificationReport`

`classification` vocabulary unchanged: `"exact"` / `"approximate"` / `"failed"`. No new labels. The classification is computed the same way; only its inputs change (nonperiodic classification is based on the overlap-crop residual, not a full-domain residual). This is a documented weakening of the classification's meaning on nonperiodic data — the diagnostic-only note on `dispatch_path` makes it explicit.

## v0.33c — Mask-preserving discovery bridge

### Motivation

`run_pysindy_pde_task` today calls `pdelie._boundary.is_x_periodic` up front (a hard gate) and passes the field values to the discovery adapter with no separate mask propagation. Callers who assemble a masked training FieldBatch expect the mask's row-set to match the row-set that reaches the optimizer, but the derivative stencil widens the effective mask by `stencil_order` rows on each side. External optimizers that consume the design matrix see a set of rows that has been silently expanded compared to what PDELie audited.

### Frozen shape

`run_pysindy_pde_task(field, *, task_name, pysindy_model, ..., heldout_field=None, ..., mask_application=...)`:

- New kwarg `mask_application: Literal["before_differentiation", "after_differentiation"] = "after_differentiation"`. Default flips to the correct-by-construction "after" path. Callers who need the pre-v0.33 behavior for reproducibility can pass `"before_differentiation"` explicitly and get a warning.
- The differentiation call sees the full (unmasked) field values. After differentiation, the mask is applied to the design matrix — the row-set that reaches the optimizer is exactly the row-set the mask declares.

New keys added inside `discovery_task_result.fit_diagnostics` (which is `dict[str, Any]`; adding keys does NOT change the outer 22-key schema):

- `mask_application_stage`: `"before_differentiation"` | `"after_differentiation"` | `"none"` (when no mask).
- `mask_row_count`: `int`. Rows retained after mask application.
- `unmasked_row_count`: `int`. Rows the derivative operator saw.
- `mask_row_count_reduction_from_derivative_stencil`: `int`. `unmasked_row_count - mask_row_count` on the "after" path when the derivative stencil widens; used to catch silent leakage regressions in the release-gate.

### Non-goals for v0.33c

- No change to the periodic-only enforcement gate. Nonperiodic PySINDy discovery via `run_pysindy_pde_task` remains blocked; `PySINDyDiscoveryUnsupportedBoundaryError` still fires. Callers who need nonperiodic PySINDy discovery still hit that error explicitly.
- No modification to `discovery_task_result` schema outside `fit_diagnostics`. The 22-key top-level count is a v0.31 invariant.
- No mask-propagation into `heldout_field`. Callers still supply an explicitly-masked heldout FieldBatch.

## Test-case surface (to be authored in v0.33a-c)

At consolidation the v0.33.0 release-gate must include:

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
