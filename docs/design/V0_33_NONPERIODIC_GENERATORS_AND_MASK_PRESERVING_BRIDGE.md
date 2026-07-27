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
- Constant-coefficient `polynomial_translation_svd` on a variable-coefficient field runs to completion (does not raise), reports a **higher** `span_distance` / `residual_l2` than the constant-coefficient baseline, and is a documented `valid_but_not_useful` diagnostic in the resulting confidence report — the crash test.

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
