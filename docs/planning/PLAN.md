# PDELie - Execution Plan (V0.30d)

**Status:** IN_PROGRESS

`v0.30d` routes the Heat, Burgers, advection-diffusion, and reaction-diffusion residual evaluators through `compute_derivatives(backend="auto")` and consumes the interior-only residual-domain policy that v0.30c's finite-difference backend recommends. KdV and the weak evaluators remain periodic-only per v0.30 scope. No new optional dependency, no CI change, no version bump. Hygiene phase 1 (ruff/mypy/coverage) is deferred to v0.30e.

## Release Theme

`v0.30d` closes the "nonperiodic residuals" loop for the four supported strong-form evaluators. Once complete, a user can pass a Dirichlet, Neumann, or `open_unknown` FieldBatch to any of {Heat, Burgers, advection-diffusion, reaction-diffusion} and receive a residual whose diagnostics honor the interior-only trim policy.

Decision label:

```text
strong_residual_evaluator_auto_dispatch_and_interior_only_diagnostics
```

## Implemented Surfaces

- `src/pdelie/residuals/base.py`: shared helper `build_residual_diagnostics_from_derivatives` that reads `recommended_residual_domain_policy` and `recommended_boundary_trim_width` from `DerivativeBatch.config`, computes interior-only max/RMS residuals when the recommended policy is `"interior_only"`, and nests a `full_grid_diagnostic` block for transparency.
- `src/pdelie/residuals/heat_1d.py`: derivatives default now dispatch through `compute_derivatives(backend="auto")`; diagnostics use the shared helper (adds `residual_domain_policy` and `rms_residual` to Heat outputs).
- `src/pdelie/residuals/burgers_1d.py`: same routing and shared-helper adoption.
- `src/pdelie/residuals/advection_diffusion_1d.py`: same routing + shared helper; the direct `is_x_periodic` early-guard is dropped since `compute_derivatives(backend="auto")` decides the backend.
- `src/pdelie/residuals/reaction_diffusion_1d.py`: same as advection-diffusion.

## Explicitly Untouched

- `src/pdelie/residuals/kdv_1d.py`: KdV remains periodic-only (`equation == "kdv_normalized"` tag + periodic-x check).
- `src/pdelie/residuals/weak_1d.py`: weak Heat/Burgers residuals stay periodic-only.
- `src/pdelie/verification/finite_transform.py`: translation finite-transform verification stays periodic-only. Nonperiodic overlap-crop design is a v0.31.5 topic.

## Tests Added

- `tests/test_manufactured_nonperiodic_residuals.py`: manufactured-analytic solutions on Dirichlet (Heat, Burgers) and `open_unknown` (advection-diffusion) plus a Fisher-KPP smoke on Dirichlet; O(h²) interior convergence for Heat; regression that periodic Heat/Burgers still route to spectral_fd with `full_grid` policy; regression that Heat/Burgers diagnostics gain `rms_residual`.

## Tests Updated

- `tests/test_advection_diffusion_residual.py`, `tests/test_reaction_diffusion_residual.py`: the "dirichlet-tagged data raises" parametrization is dropped — that case is now a legitimate nonperiodic residual path.
- `tests/test_boundary_condition_internal_usage.py`:
  - `test_heat_residual_evaluator_still_rejects_nonperiodic_derivative_path` replaced by `test_heat_residual_evaluator_now_handles_nonperiodic_via_fd_dispatch`.
  - `must_import_helper` drops `advection_diffusion_1d.py` and `reaction_diffusion_1d.py`.
- `tests/test_boundary_readiness_reporting.py`: the "not_configured" residual-domain-policy check now uses a directly constructed `ResidualBatch`; adds a positive test that periodic Heat emits `"full_grid"`.
- `tests/test_reporting.py`: the frozen residual-summary policy field now expects `"full_grid"` for periodic Heat.

## Public-Surface Audit

Confirmed in `v0.30d`:

- no new `pdelie` root export
- no new submodule runtime API
- no new optional dependency
- no new PDE
- no KdV nonperiodic, no KS nonperiodic, no weak nonperiodic
- no PDEBench / The Well support claim
- no symmetry-method registry
- no `pyproject.toml` version bump (still `0.29.0`)
- no CI workflow change
- ruff / mypy / coverage configuration remains deferred to v0.30e

## v0.30d Sub-Release Gate

`v0.30d` is complete when:

- Heat, Burgers, advection-diffusion, reaction-diffusion evaluators route through `compute_derivatives(backend="auto")` when derivatives are omitted
- their diagnostics include `residual_domain_policy` (and, when interior-only, `boundary_trim_width` + `full_grid_diagnostic`)
- KdV, weak, and translation verification remain periodic-only
- manufactured-analytic tests pass with the expected tolerances
- the full suite still passes
- `git diff --check` reports no whitespace damage

---

# PDELie - Execution Plan (V0.30c)

**Status:** COMPLETE

`v0.30c` lands the second runtime step of the v0.30 sequence: the low-order finite-difference derivative backend, the `compute_derivatives(backend="auto")` dispatcher, boundary-aware readiness warnings, and the `residual_domain_policy` field on residual summaries. Residual evaluator auto-dispatch is deferred to v0.30d.

## Release Theme

`v0.30c` implements the v1 `finite_difference` derivative backend (`u_t`, `u_x`, `u_xx` only on nonperiodic 1D scalar uniform grids) and the explicit-and-auditable `compute_derivatives` dispatcher. `spectral_fd` is unchanged. The reporting layer now surfaces boundary-condition warnings and an additive `residual_domain_policy` field. No new optional dependency, no version bump, no root export, no CI workflow change.

Decision label:

```text
low_order_finite_difference_backend_and_boundary_aware_readiness
```

## Implemented Surfaces

- `src/pdelie/derivatives/finite_difference.py` (NEW) — `compute_finite_difference_derivatives(field, *, max_spatial_order=2)` for `u_t`, `u_x`, `u_xx` only on Dirichlet, Neumann, or `open_unknown` data. Uses `np.gradient(edge_order=2)` for both axes.
- `src/pdelie/derivatives/__init__.py` (UPDATED) — exports `compute_finite_difference_derivatives` and a new `compute_derivatives(field, *, backend="auto", max_spatial_order=2)` dispatcher. `backend="auto"` picks `spectral_fd` for periodic data and `finite_difference` for any supported nonperiodic boundary type; the selection is recorded in `DerivativeBatch.config` as `backend_selected_by_boundary_condition=True` plus a non-null `backend_selection_reason`. Explicit `backend="spectral_fd"` on nonperiodic data and explicit `backend="finite_difference"` on periodic data both raise `ScopeValidationError`. The dispatcher never silently falls back from one backend to the other.
- `src/pdelie/contracts.py` (UPDATED) — `ALLOWED_DERIVATIVE_BACKENDS` now includes `"finite_difference"` (the legacy `"finite"` entry is retained).
- `src/pdelie/reporting/summaries.py` (UPDATED) — two remaining direct periodic compares migrated to `get_x_boundary_type`. `summarize_field_batch_readiness` now emits `boundary_condition_warnings: list[str]` and downgrades a would-be `"ready"` label to `"needs_attention"` when warnings are present. `summarize_xarray_dataset_readiness` does the same. `summarize_residual_batch` now records a `residual_domain_policy` field, sourced from `residual.diagnostics["residual_domain_policy"]` if present, else `"not_configured"`.

## Documents Added or Updated

- `docs/design/DERIVATIVE_BACKEND_POLICY.md` (updated status — `finite_difference` v1 implemented)
- `docs/planning/PLAN.md` (this file; v0.30b record retained below)
- `docs/specs/API_STABILITY.md` (new "Decision-only note for the frozen `v0.30c`" subsection appended after the v0.30b note)
- `docs/planning/ROADMAP.md` (v0.30c row updated; v0.30b row flipped to Completed)
- `configs/planning/v0_30_nonperiodic_readiness_scope.json` (removed `pdelie.derivatives.compute_finite_difference_derivatives` and `pdelie.derivatives.compute_derivatives` from `forbidden_submodule_attributes` — they ship in v0.30c)

## Tests Added

- `tests/test_finite_difference_backend.py` — manufactured-polynomial accuracy, max_spatial_order limits, JSON-strict config, periodic-input rejection, nonuniform-grid rejection, too-few-points rejection, structured/legacy nonperiodic BC acceptance.
- `tests/test_derivative_dispatcher.py` — `backend="auto"` periodic + nonperiodic routing, explicit-backend success/mismatch behavior, unknown backend rejection, no-fallback semantics, `backend_selected_by_boundary_condition` only true under auto.
- `tests/test_boundary_readiness_reporting.py` — `boundary_condition_warnings` for legacy/structured periodic/nonperiodic/open_unknown, readiness label downgrade, residual-domain-policy passthrough, strict JSON compatibility, unsupported BC string routes to failure.

## Tests Updated

- `tests/test_reporting.py`:
  - `_FIELD_BATCH_READINESS_SUMMARY_KEYS` and `_XARRAY_DATASET_READINESS_SUMMARY_KEYS` now include `boundary_condition_warnings`.
  - the residual-batch frozen-keys assertion now includes `residual_domain_policy` and pins its default to `"not_configured"`.
  - the nonperiodic-field readiness case now expects `"needs_attention"` plus the `x_boundary_dirichlet_unspecified` and `x_boundary_legacy_string_under_schema_0_2` warnings (the v0.30c behavior change).
- `tests/test_boundary_condition_internal_usage.py`:
  - dropped the `reporting/summaries.py` allowlist entry (no longer needed; the file now goes through the helper).
  - `must_import_helper` enlarged to also list the new derivative-backend module, the dispatcher module, and `reporting/summaries.py`.
- `configs/planning/v0_30_nonperiodic_readiness_scope.json`: `pdelie.derivatives.compute_finite_difference_derivatives` and `pdelie.derivatives.compute_derivatives` removed from `forbidden_submodule_attributes`.

## Public-Surface Audit

Confirmed in `v0.30c`:

- no new `pdelie` root export
- `pdelie.derivatives.compute_finite_difference_derivatives` and `pdelie.derivatives.compute_derivatives` are submodule-only
- no new optional dependency
- no new PDE
- no PDEBench / The Well support claim
- no KdV nonperiodic
- no KS nonperiodic
- no weak nonperiodic
- no symmetry-method registry yet
- no residual evaluator auto-dispatch (deferred to v0.30d)
- no `u_xxx` / `u_xxxx` on nonperiodic data (`max_spatial_order ∈ {1, 2}` only)
- no version bump (`pyproject.toml` remains at `0.29.0`)
- no CI workflow change

## v0.30c Sub-Release Gate

`v0.30c` is complete when:

- `pdelie.derivatives.compute_finite_difference_derivatives` is importable and produces correct `u_t`, `u_x`, `u_xx` on manufactured polynomials
- `pdelie.derivatives.compute_derivatives(backend="auto")` routes by BC and records the selection in `DerivativeBatch.config`
- `summarize_field_batch_readiness` exposes `boundary_condition_warnings` and downgrades the label when warnings exist
- `summarize_residual_batch` exposes `residual_domain_policy`
- all v0.30c new tests pass plus the existing v0.30a/b tests
- the full test suite passes
- `git diff --check` reports no whitespace damage

---

# PDELie - Execution Plan (V0.30b)

**Status:** COMPLETE

`v0.30b` lands the first runtime step of the v0.30 sequence: the structured `BoundaryConditionSpec`, the `FieldBatch` 0.1 → 0.2 schema migration with backwards-compatible loader, and internal helpers that centralize the x-boundary-type check. Adapter ingestion is loosened to accept supported nonperiodic specs; downstream derivative and residual consumers remain strict-periodic.

## Release Theme

`v0.30b` implements the contracts frozen in `v0.30a` for boundary metadata. It modifies `src/pdelie/` but adds no new optional dependency, no version bump, no root export, no CI workflow change.

Decision label:

```text
boundary_condition_spec_runtime_and_field_batch_0_2_migration
```

## Implemented Surfaces

- `src/pdelie/_boundary.py` (NEW) — internal helpers `BoundaryFace`, `BoundaryConditionSpec`, `normalize_x_boundary_condition`, `get_x_boundary_type`, `is_x_periodic`; module is intentionally underscore-prefixed (no submodule re-export).
- `FieldBatch.SCHEMA_VERSION` bumped from `"0.1"` to `"0.2"`.
- `FieldBatch.LEGACY_SCHEMA_VERSIONS = frozenset({"0.1"})`; `from_dict` accepts both versions.
- `FieldBatch.from_dict` normalizes legacy `boundary_conditions["x"]` strings via `normalize_x_boundary_condition` and records a `schema_0_1_to_0_2_boundary_normalization` entry in `preprocess_log` for migrated payloads.
- 14 downstream consumer sites refactored to use `is_x_periodic(field)` (preserves reject-nonperiodic semantics; no behavior change for periodic data).
- `from_numpy` and `from_xarray` accept structured nonperiodic specs and supported legacy nonperiodic strings; unsupported strings still raise `ScopeValidationError`.

## Documents Added or Updated

- `docs/design/BOUNDARY_CONDITION_SPEC.md` (updated status — design frozen + runtime implemented)
- `docs/planning/PLAN.md` (this file; v0.30a record retained below)
- `docs/specs/API_STABILITY.md` (new "Decision-only note for the frozen `v0.30b`" subsection appended after the v0.30a note)
- `docs/planning/ROADMAP.md` (new v0.30b row)

## Tests Added

- `tests/test_boundary_condition_spec.py` — direct tests for the helper module.
- `tests/test_field_batch_schema_0_2_migration.py` — `FieldBatch` schema 0.1 → 0.2 migration tests.
- `tests/test_boundary_condition_internal_usage.py` — invariants: downstream consumers still reject nonperiodic, adapters accept structured nonperiodic, no new direct periodic compares outside the helper module, all migrated modules import the helper.

## Tests Updated

- `tests/test_v0_30_scope_freeze.py`:
  - removed `test_v0_30_no_src_changes_against_main` (v0.30b modifies src by design).
  - replaced `test_v0_30_schema_migration_is_documented_but_not_yet_applied` with two tests: `test_v0_30_schema_migration_design_is_documented` (still passes against the design docs) and `test_v0_30b_schema_migration_is_applied_at_runtime` (asserts `FieldBatch.SCHEMA_VERSION == "0.2"`).
- `tests/test_data_numpy_adapter.py` and `tests/test_data_xarray_adapter.py`:
  - replaced the rejection-of-`dirichlet` tests with acceptance tests for `dirichlet`/`neumann`/`open_unknown` (the new loosened adapter behavior).
  - added new rejection tests for unsupported BC strings (`"insulating"`).

## Public-Surface Audit

Confirmed in `v0.30b`:

- no new `pdelie` root export
- no new submodule runtime API
- no new optional dependency
- no new PDE
- no PDEBench or The Well support claim
- no KdV nonperiodic
- no KS nonperiodic
- no weak nonperiodic
- no `compute_finite_difference_derivatives` module yet (deferred to v0.30c)
- no `compute_derivatives` dispatcher yet (deferred to v0.30c)
- no symmetry-method registry yet
- no root `pdelie.discover_symmetries`
- no version bump (`pyproject.toml` remains at `0.29.0`)
- no CI workflow change

## v0.30b Sub-Release Gate

`v0.30b` is complete when:

- `FieldBatch.SCHEMA_VERSION == "0.2"`
- `FieldBatch.from_dict` accepts both `"0.1"` and `"0.2"` payloads
- legacy `boundary_conditions["x"]` strings are normalized via `normalize_x_boundary_condition`
- all 14 downstream consumer sites use `is_x_periodic` (no new direct compares)
- `from_numpy` / `from_xarray` accept structured nonperiodic specs; downstream consumers still reject
- the three new tests pass plus the updated v0.30 scope-freeze tests
- the full test suite passes
- `git diff --check` reports no whitespace damage

---

# PDELie - Execution Plan (V0.30a)

**Status:** COMPLETE

`v0.30a` is the scope-freeze, compatibility-audit, and design-contract sub-release that precedes `v0.30`.

## Release Theme

`v0.30a` freezes the design of nonperiodic-readiness ingestion, the low-order finite-difference derivative backend, the dispatch and residual-domain policies, and the cross-cutting hygiene audit. It adds no runtime API, bumps no package version, and modifies no file under `src/pdelie/`.

Decision label:

```text
nonperiodic_readiness_and_low_order_finite_difference_diagnostics_design_only
```

## Implemented Surfaces

None at runtime. The sub-release is design-only.

## Documents Added

- `docs/planning/V0_30_SCOPE.md`
- `docs/design/BOUNDARY_CONDITION_SPEC.md`
- `docs/design/DERIVATIVE_BACKEND_POLICY.md`
- `docs/design/V0_30_HYGIENE_AUDIT.md`
- `configs/planning/v0_30_nonperiodic_readiness_scope.json`
- `tests/test_v0_30_scope_freeze.py`
- `tests/test_v0_30_hygiene_audit.py`

## Documents Updated

- `docs/planning/ROADMAP.md` (new `v0.30a` row in Next Planned Work; refined `v0.30` theme; appended deferred surfaces)
- `docs/planning/PLAN.md` (this file; v0.29 record retained below)
- `docs/specs/API_STABILITY.md` (new "Decision-only note for the frozen `v0.30a`" subsection appended after the v0.29 note)

## Public-Surface Audit

Confirmed in `v0.30a`:

- no new `pdelie` root export
- no new submodule runtime API
- no new optional dependency
- no new PDE
- no PDEBench or The Well support claim
- no KdV nonperiodic
- no KS nonperiodic
- no weak nonperiodic
- no `compute_finite_difference_derivatives` module yet
- no symmetry-method registry yet
- no root `pdelie.discover_symmetries`
- no version bump (`pyproject.toml` remains at `0.29.0`)
- no CI workflow change

## v0.30a Sub-Release Gate

`v0.30a` is complete when:

- the four design documents in `docs/design/` and `docs/planning/V0_30_SCOPE.md` are in place
- `tests/test_v0_30_scope_freeze.py` and `tests/test_v0_30_hygiene_audit.py` pass
- the full test suite still passes
- `git diff --check` reports no whitespace damage
- no file under `src/pdelie/` is modified

---

# PDELie - Execution Plan (V0.29)

**Status:** COMPLETE

**V0.29 is complete as the workflow recipes and support matrix release**

This file is the completed execution record for the `v0.29` release series.

## Release Theme

`v0.29` consolidates the existing `v0.19-v0.28` surface into explicit user workflows and a machine-readable support matrix. It adds no numerical scope, no runtime helper, no new public API, and no root export.

Decision label:

```text
workflow_recipes_and_support_matrix_complete_no_new_numerical_scope
```

## Implemented Surfaces

- `docs/workflows/` with recipe pages for data readiness, candidate validation, downstream/export provenance, Dataset-to-downstream, and candidate-to-split-provenance workflows
- `docs/specs/support_matrix.v0_29.json` as the machine-readable support matrix
- `docs/specs/SUPPORT_MATRIX.md` as the human-readable support matrix
- `notebooks/12_dataset_to_downstream_workflow.ipynb`
- `notebooks/13_candidate_to_split_provenance_workflow.ipynb`

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

Authoritative scope:

- `docs/planning/V0_29_SCOPE.md`

## Public-Surface Audit

Confirmed:

- no `pdelie.reporting.summarize_workflow_readiness(...)`
- no new runtime API
- no new root export
- no new PDE or numerical regime
- no file loader, broad adapter, metadata inference engine, resampling API, multidimensional/nonuniform API, train/test policy, KS runtime API, neural/callable API, or operator API landed

## Release Gate and Readiness

Implemented:

- `tests/test_v0_29_release_gate.py`
- CI `v0_29-release-gate`
- package metadata bump to `0.29.0`
- Git-tag-only release-readiness docs; PyPI/TestPyPI remain deferred until `v1.0` or later
