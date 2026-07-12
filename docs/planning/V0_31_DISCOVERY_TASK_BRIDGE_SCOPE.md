# V0.31 Scope - Downstream Discovery Task Bridge

**Status:** IN_PROGRESS (v0.31a scope-freeze sub-release)

`v0.31` is the downstream-discovery task-bridge release. It designs a narrow, submodule-only bridge from canonical PDELie objects into PySINDy's `PDELibrary` (and, as a diagnostic-only wrapper, `WeakPDELibrary`), records a stable `TaskResult` schema for the composed task output, and freezes what stays out of scope.

The first executed slice is the design-only sub-release `v0.31a`, which adds documents, configs, and audit tests without modifying any runtime code, adding any new optional dependency, or bumping the package version. **v0.31a is design-only; runtime lands in v0.31b+.**

Release conclusion (recorded by v0.31a):

```text
downstream_discovery_task_bridge_design_only
```

## Sequencing

Per the current planning agreement recorded in `docs/planning/ROADMAP.md`, **v0.31 sequences before v0.30.1**: the discovery task bridge delivers the larger user-facing scientific delta, while the submodule-only symmetry-method registry MVP is smaller and can follow. In particular, **SymmetryCandidate wrapper is v0.30.1 responsibility not v0.31** — no `SymmetryCandidate` contract or wrapper lands in this release.

## Stable Intent

`v0.31` widens the *downstream-discovery* surface from the existing narrow bridge (`pdelie.discovery.to_pysindy_trajectories`, `pdelie.discovery.fit_pysindy_discovery`) to a small task layer that composes canonical PDELie inputs, PySINDy's PDE-form libraries, and PDELie's existing recovery / residual reporting into one stable JSON-compatible artifact.

Two user paths are unlocked by the runtime that this scope freezes:

1. **PySINDy `PDELibrary` bridge (periodic-only in v0.31)**: `fit_pysindy_discovery` accepts a caller-supplied `pysindy_model` configured with a `PDELibrary` and a `differentiation_method` compatible with PDELie's canonical scalar 1D periodic layout. The scope-frozen policy for this milestone is: **PySINDy PDELibrary bridge is periodic-only in v0.31; FD-nonperiodic extension is explicitly deferred**. The v0.30c `finite_difference` backend does not become a supported PySINDy-side derivative source in this release.
2. **`WeakPDELibrary` diagnostic wrapper**: an optional wrapper that composes PySINDy's `WeakPDELibrary` output into a PDELie-side diagnostic report. The wrapper is diagnostic-only — it is not a public weak derivative backend, not a WSINDy design-matrix layer, not a claim of weak-form supportability, and not a replacement for the existing `pdelie.residuals.weak_1d` slice.

The composed task output is a `TaskResult` payload (design in `docs/design/DISCOVERY_TASK_RESULT_SCHEMA.md`) with `summary_type = "discovery_task_result"` and `summary_schema_version = "0.1"`.

## Scope

The v0.31 release scope is:

- a new submodule `pdelie.tasks.discovery` that composes canonical FieldBatch inputs, PySINDy PDE-library fitting, and PDELie recovery/residual reporting into a stable `TaskResult` artifact
- loosening of `pdelie.discovery.fit_pysindy_discovery` to accept a caller-supplied `pysindy_model` (currently rejected as `config != None` at `src/pdelie/discovery/pysindy_adapter.py:196-204`), routed through the existing periodic-only `to_pysindy_trajectories` bridge
- a `WeakPDELibrary` diagnostic wrapper with `summary_type = "pdelie_weak_pde_library_diagnostic"` carrying `diagnostic_only: true` and using method/test-function/quadrature identifier strings **distinct from** the pdelie-native `weak_1d` path
- an additive supportability-policy update that adds `supports_pysindy_weak_library_diagnostic` and re-scopes `supports_weak_derivative_backend` to explicitly cover the *public strong-derivative-only pdelie-native path* while noting that the WeakPDELibrary wrapper is a diagnostic-scope weak derivative backend
- release-gate consolidation via a row in `configs/release_gate_manifest.json` replayed by `tests/test_release_gates.py` — **the v0.31 release-gate is a row in configs/release_gate_manifest.json** and **not a new tests/test_v0_31_release_gate.py file**, following the v0.30f consolidation pattern

The v0.31 deliverables, design-frozen in v0.31a and implemented from v0.31b onward:

- `pdelie.tasks.discovery` skeleton (`run_pysindy_pde_task` or similar; final name pinned in v0.31b design)
- `fit_pysindy_discovery(config=...)` config loosening; the existing `ScopeValidationError` gate is narrowed to a runtime schema-validation gate
- `TaskResult` schema runtime under strict JSON (`_validate_strict_json_compatible`, mirroring `src/pdelie/reporting/summaries.py:1311` and `:1954`)
- `WeakPDELibraryDiagnostic` wrapper, submodule-only (`pdelie.tasks.discovery`, not `pdelie.residuals`)
- `supportability_policy` dict update covering both bullet points above

## Deferred Scope

Explicit non-goals (the scope-freeze test asserts every phrase is present):

- **no root API** — no root `pdelie.run_discovery_task`, no root `pdelie.fit_pysindy_pde_task`, no root `pdelie.TaskResult`, no root `pdelie.WeakPDELibraryDiagnostic`, no root `pdelie.SymmetryCandidate`, no root `pdelie.SymmetryMethod`, no root `pdelie.discover_symmetries`
- **no WSINDy implementation** — v0.31 does not add a WSINDy design matrix, a weak sparse recovery layer, or an SR3-style weak solver
- **no weak nonperiodic** — the v0.30 nonperiodic readiness surface stays strong-form-only; no nonperiodic weak residuals in v0.31
- **no noise robustness claim** — v0.31 does not certify robustness of discovery to additive noise; `pdelie.data.add_gaussian_noise` remains an ingestion helper, not a discovery-side robustness gate
- **no clean/noisy gate** — v0.31 does not add a policy that gates a discovery TaskResult on clean-vs-noisy inputs
- **no external dataset benchmark claim** — v0.31 does not claim recovery on any external dataset; readiness reports and TaskResult are configured evidence, not benchmarks
- **no PDEBench support claim** — external-dataset readiness cookbooks remain a `v0.32` scope
- **no The Well support claim** — same as above
- **no multi-channel** — TaskResult carries `input_layout = "scalar_1d_uniform"` as a first-class field so v0.34a-c multi-channel widening does not retrofit the schema, but multi-channel dispatch itself is out of v0.31
- **no 2D** — the canonical `('batch','time','x','var')` layout remains the sole supported layout
- **scalar 1D only** — every v0.31 code path assumes a single scalar variable
- **no promotion of lint/typecheck/coverage to blocking in v0.31** — the v0.30e advisory jobs stay advisory
- **no LieGG / trained-model extraction in v0.31** — deferred to `v0.35a`
- **no multi-channel or 2D FieldBatch dispatch in v0.31** — deferred to `v0.34`
- **no SymmetryCandidate contract in v0.31** — deferred to `v0.30.1` (submodule-only symmetry-method registry MVP)
- **no symmetry-method registry in v0.31** — the `pdelie.symmetry.SymmetryMethod` registry MVP + `SymmetryCandidate` wrapper contract freeze both land in `v0.30.1`, sequenced after v0.31 per the ROADMAP
- **no PyPI or TestPyPI publication** — Git-tag-only through the `v0.x` series

Additional retention:

- **weak_1d retained through v0.32 close; removal contingent on the v0.31 PDELibrary bridge shipping a documented replacement path AND the WeakPDELibrary diagnostic wrapper landing a validated parity harness with a documented O((dx)^p) tolerance.**

## TaskResult Schema (Designed in v0.31a)

The composed task output has `summary_schema_version = "0.1"` and `summary_type = "discovery_task_result"`. The full field-by-field design is documented in `docs/design/DISCOVERY_TASK_RESULT_SCHEMA.md`. Summary:

- `task_name: str`
- `backend_name: Literal["pysindy"]` (Literal expansion is v0.32+)
- `backend_version: dict[str, str]` with required keys `pysindy`, `sklearn`, `pdelie`
- `target_convention: Literal["pde_library", "weak_pde_library"]`
- `derivative_backend: str` — promoted from `fit_config.pysindy_model.differentiation_method`, referencing the v0.30c `spectral_fd` / `finite_difference` dispatch
- `input_layout: Literal["scalar_1d_uniform"]` (reserved enum for v0.34+ multi-channel/2D expansion)
- `library_feature_names: list[str]` (renamed from `library_terms` for continuity with `summarize_discovery_result` at `src/pdelie/discovery/contracts.py:395`)
- `selected_terms: dict[str, dict[str, float]]` (verbatim from `equation_terms` of the embedded `discovery_result`)
- `coefficients: dict | None` (optional; opt-in shape, not required)
- `support_precision: float`, `support_recall: float`, `support_f1: float`, `exact_support: bool`, `coefficient_relative_l2: float`
- `train_residual: dict | None`, `heldout_residual: dict | None` (both strict-numeric `{size, l2_norm, rms, max_abs}` when present, matching the normative shape from `_residual_summary_or_none` at `src/pdelie/discovery/contracts.py:198-214`)
- `weak_contract: dict | None` (non-null iff `target_convention == "weak_pde_library"`; carries `method_family`, `test_function_family`, `quadrature_rule`, `diagnostic_only: true`)
- `warnings: list[str]`
- `underlying_discovery_result: dict` (embedded `summarize_discovery_result` payload; sibling wrapper, not parent/child)

The composed payload MUST pass `json.loads(json.dumps(payload, allow_nan=False)) == payload` before return, via `_validate_strict_json_compatible(payload, name="discovery_task_result summary")` — mirroring `src/pdelie/reporting/summaries.py:1311` and `:1954`. Only 2 of 14 current `summarize_*` functions enforce `allow_nan=False`; TaskResult must not inherit the assumption of strict-JSON safety from the permissive `_summary_payload` funnel.

## WeakPDELibrary Wrapper (Designed in v0.31a)

The wrapper composes PySINDy's `WeakPDELibrary` output into a PDELie diagnostic report with:

- `summary_type = "pdelie_weak_pde_library_diagnostic"`
- `method_family = "pysindy_weak_pde_library_polynomial_gauss_v1"` (distinct from the pdelie-native `weak_1d` value `"local_separable_quartic_bump_trapezoid_v1"` at `src/pdelie/residuals/weak_1d.py:20`)
- `test_function_family` distinct from the pdelie-native `"separable_quartic_bump_beta"` at `src/pdelie/residuals/weak_1d.py:22`
- `quadrature_rule` distinct from the pdelie-native `"composite_tensor_product_trapezoidal_native_window"` at `src/pdelie/residuals/weak_1d.py:21`
- explicit `"diagnostic_only": true` marker so downstream tooling cannot mistake the wrapper for a supportability claim

The three pdelie-native identifier strings are recorded here so any future WeakPDELibrary-wrapper TaskResult does not accidentally collide with them; there is no enum or allowlist gating these strings today, so provenance disambiguation is the design's responsibility.

## Supportability Policy Update (Designed in v0.31a)

The supportability-policy dict gains one new key and one re-scoping note:

- `supports_pysindy_weak_library_diagnostic: True` — records that the WeakPDELibrary wrapper is available as a diagnostic-only surface
- `supports_weak_derivative_backend` is re-scoped to "public strong-derivative-only pdelie-native path" with an explicit note that WeakPDELibrary is a **diagnostic-scope** weak derivative backend, not a public weak derivative backend

Both are additive; no existing public field is removed.

## Retention Window

**weak_1d retained through v0.32 close; removal contingent on the v0.31 PDELibrary bridge shipping a documented replacement path AND the WeakPDELibrary diagnostic wrapper landing a validated parity harness with a documented O((dx)^p) tolerance.**

## Milestones

- **M0: scope freeze — COMPLETE (in v0.31a; this release)**
- **M1: `pdelie.tasks.discovery` skeleton + `fit_pysindy_discovery` config loosening — DESIGN COMPLETE in v0.31a, IMPLEMENTATION DEFERRED to v0.31b**
- **M2: TaskResult schema runtime + strict-JSON adversarial test — DESIGN COMPLETE in v0.31a, IMPLEMENTATION DEFERRED to v0.31b**
- **M3: WeakPDELibrary diagnostic wrapper — DESIGN COMPLETE in v0.31a, IMPLEMENTATION DEFERRED to v0.31b (contingent on the installed PySINDy version exposing `WeakPDELibrary`)**
- **M4: supportability-policy dict update — DESIGN COMPLETE in v0.31a, IMPLEMENTATION DEFERRED to v0.31b**
- **M5: release-gate consolidation — CONFIRMED as manifest row (no new tests/test_v0_31_release_gate.py file), IMPLEMENTATION at v0.31 release close (v0.31 proper)**

## Release Gate (v0.31 close)

The v0.31 release-gate is a row in `configs/release_gate_manifest.json` replayed by `tests/test_release_gates.py`, **not a new tests/test_v0_31_release_gate.py file**. This follows the v0.30f consolidation pattern: no standalone per-version release-gate file is added; the declarative content becomes a manifest row alongside the existing 18 rows.

## v0.31a Sub-Release Gate

v0.31a is complete when:

- this scope document is in place and required phrases are present
- the design document `docs/design/DISCOVERY_TASK_RESULT_SCHEMA.md` is in place and required schema fields are documented
- `configs/planning/v0_31_discovery_task_bridge_scope.json` is present and strictly JSON-compatible (`allow_nan=False`)
- `docs/planning/ROADMAP.md` records `v0.31a`
- `docs/planning/PLAN.md` records `v0.31a` with the decision label
- `docs/specs/API_STABILITY.md` contains the "Decision-only note for the frozen `v0.31a`" subsection
- `tests/test_v0_31_discovery_task_bridge_scope.py` passes
- `tests/test_discovery_task_result_schema.py` passes with the NaN adversarial test
- the full test suite still passes
- no file under `src/pdelie/` is modified
- no version bump in `pyproject.toml`
- no new optional dependency added
- no new CI job added
