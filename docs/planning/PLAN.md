# PDELie - Planning Note (V0.32a design freeze — method_scores / uncertainty_report / calibration_report)

**Status:** PLANNED (design freeze scheduled for `v0.32a`)

Records the additive extension planned for `pdelie.reporting.summarize_generator_confidence`. This is a **planning note only** — it does not schedule the runtime implementation, does not bump any version, and does not touch `src/pdelie/`. It exists here so the label registry (`docs/specs/LABEL_REGISTRY.md`), the API stability policy (`docs/specs/API_STABILITY.md`), and the scientific positioning doc (`docs/strategy/SCIENTIFIC_POSITIONING.md`) can reference a single canonical decision for what "beyond `confidence_label`" looks like.

## Motivation

The v0.20 `confidence_label` (`strong`, `qualified`, `failed`, `insufficient_evidence`) is a frozen public contract. Renaming it or extending its allowed values would break `tests/test_v0_20_release_gate.py` and every downstream consumer that already relies on the categorical vocabulary. However, the peer review of the v0.31 arc flagged that:

- users need numeric per-component scores for calibration and cross-method comparison work, not only a categorical rollup;
- future release adapters (v0.33 Ko-sparse, v0.35a LieGG) naturally emit uncertainty distributions that today have nowhere to land in PDELie's public reporting;
- BARNN-style calibration studies require reliability-diagram data that `confidence_label` cannot represent.

The additive path avoids the breaking-change trap: keep `confidence_label` exactly as-is (v0.20 contract), and add three **optional** fields alongside it that default to `None` so existing downstream consumers are unaffected.

## Planned additive fields on `summarize_generator_confidence`

Design frozen at `v0.32a`; runtime implementation at `v0.32b+`. The fields are:

- `method_scores: dict[str, float] | None` — numeric per-component scores alongside the categorical `confidence_label`. Expected keys at first ship: `span_distance`, `residual_l2`, `error_curve_max`, `svd_condition_number`. Consumers pre-registering keys must accept `None` until `v0.32b`.
- `uncertainty_report: dict | None` — where a method emits mean / variance / HDR intervals, this is where they land. Expected shape at first ship: `{"method": Literal["point_estimate", "svd_perturbation", "bootstrap", "bayesian_hdr"], "point": float, "hdr_low": float | None, "hdr_high": float | None, "samples_n": int | None}`. `None` for point-estimate methods (current default for `polynomial_translation_svd`).
- `calibration_report: dict | None` — where reliability-diagram data or ECE is available. Expected shape: `{"method": Literal["ece", "reliability_diagram"], "ece": float | None, "bin_edges": list[float] | None, "bin_conf": list[float] | None, "bin_acc": list[float] | None, "n": int | None}`. `None` for uncalibrated methods (all v0.30 methods).

**All three fields default to `None` and never replace `confidence_label`.** Existing consumers that read `confidence_label` continue to work without modification. Consumers that want the numeric surfaces can opt in field-by-field.

## Why v0.32a (and not v0.31)

- `v0.31` is the discovery task bridge; it lands a new `discovery_task_result` schema. Bundling `generator_confidence` extension into v0.31 would confuse two axes (task-bridge scope vs reporting-refinement scope) in one release.
- `v0.31.5` is the nonperiodic orbit/action scope decision — a decision-only sub-release that doesn't touch reporting.
- `v0.32` is external dataset readiness cookbooks — user-facing, dataset-side, orthogonal to reporting internals.

`v0.32a` is the earliest natural design-freeze slot: a small planning sub-release before `v0.32b` cookbooks, on a release axis where reporting extensions fit cleanly. If the release cadence changes, this planning note updates its date but not its shape.

## Backwards compatibility

- Field additions to `summarize_generator_confidence` require a scope-freeze note in the release that introduces them (`v0.32a` design freeze; `v0.32b` runtime). No existing field is removed or renamed.
- The `_CONFIDENCE_LABELS` frozenset in `src/pdelie/reporting/summaries.py:38` is not touched — the v0.20 vocabulary is invariant.
- The v0.20 release gate at `tests/test_v0_20_release_gate.py` continues to pass without modification; the added fields do not appear in that test.
- Downstream tooling that reads only `confidence_label` sees no change. Downstream tooling that wants `method_scores` / `uncertainty_report` / `calibration_report` must accept `None` as the frozen default for methods that don't emit them.

## Cross-references

- `docs/specs/LABEL_REGISTRY.md` — "Planned additive extensions" section references this planning note. When `v0.32a` freezes, the label registry gains a note that `method_scores` / `uncertainty_report` / `calibration_report` are additive fields on the `generator_confidence` summary, not new label families.
- `docs/specs/API_STABILITY.md` — Surface Matrix "deferred — additive reporting fields" row references this planning note.
- `docs/strategy/SCIENTIFIC_POSITIONING.md` — "PDELie should not become Bayesian" section from the peer review is the design constraint: PDELie does not become a calibration or UQ framework, it exposes fields where methods that natively emit those quantities can land them without breaking the categorical contract.
- `docs/strategy/VALID_BUT_NOT_USEFUL.md` — the wedge principle explains why `method_scores` is preferable to a generic `confidence` overload. Numeric per-component scores let downstream tooling reason about the wedge; a single overloaded scalar cannot.

## Not in scope for this planning note

- No `src/pdelie/reporting/summaries.py` change.
- No test change; existing v0.20 release gate is preserved verbatim.
- No version bump; `pyproject.toml` stays at `0.30.0`.
- No new dependency; the fields are pure numerical values from existing method internals.
- No renaming of `confidence_label`.
- No promotion of `evidence_label` from diagnostic to pass-fail vocabulary.
- No commitment on `v0.32a` PR shape beyond design-only; the runtime lands in `v0.32b+`.

---

# PDELie - Execution Plan (V0.30 Release Close)

**Status:** COMPLETE

**V0.30.0 is complete as the nonperiodic-readiness and low-order finite-difference derivative-diagnostics release.**

The `v0.30` arc closed on 2026-07-07. Sub-releases `v0.30a` (scope freeze), `v0.30b` (BoundaryConditionSpec runtime + FieldBatch 0.2 migration), `v0.30c` (finite-difference backend + boundary-aware readiness), `v0.30d` (residual evaluator auto-dispatch + interior-only diagnostics), `v0.30e` (non-blocking ruff/mypy/coverage hygiene phase 1), and `v0.30f` (narrow declarative release-gate consolidation) all merged before this close.

Decision label:

```text
nonperiodic_readiness_and_low_order_finite_difference_diagnostics
```

## Release Close Actions

- `pyproject.toml` version bumped `0.29.0` → `0.30.0`; description updated to reflect the v0.30 nonperiodic-readiness content.
- `docs/conf.py` `release`/`version` strings bumped to `0.30.0` / `0.30`.
- `docs/releases/V0_30_RELEASE_READINESS.md` written, mirroring the v0.29 structure and enumerating the new public surface, retained scope, hygiene phase 1 configuration, narrow release-gate consolidation, and deferred surfaces.
- `docs/specs/support_matrix.v0_30.json` written (strict JSON) with per-PDE support, boundary-condition-support map, derivative-backend policy, residual-domain-policy, and deferred-scope list.
- `docs/specs/SUPPORT_MATRIX.md` updated to reference `support_matrix.v0_30.json` alongside the v0.29 entry.
- `docs/releases/PUBLISHING.md` v0.29-specific language extended to name v0.30.0 as the current Git-tag-only release.
- `docs/releases/index.rst` extended to list `V0_30_RELEASE_READINESS`.
- `docs/planning/V0_30_SCOPE.md` status flipped `IN_PROGRESS` → `COMPLETE`; milestones 1–6 flipped from "DESIGN COMPLETE, IMPLEMENTATION DEFERRED" to the concrete sub-release that landed each.
- `docs/planning/ROADMAP.md` — `v0.30` and `v0.30f` moved to Completed Releases; `v0.30` becomes the current completed release; Next Planned Work now leads with `v0.31` (discovery task bridge) ahead of `v0.30.1` (submodule-only symmetry-method registry MVP), matching the ROADMAP table order and the earlier sequencing agreement to take the discovery task bridge before the symmetry-method registry.
- `docs/specs/API_STABILITY.md` — a `v0.30` stable public-surface note added summarizing the new submodule-only APIs (`pdelie.derivatives.compute_finite_difference_derivatives`, `pdelie.derivatives.compute_derivatives`), the `FieldBatch.SCHEMA_VERSION` bump, the reporting additions (`boundary_condition_warnings`, `residual_domain_policy`), the internal-only `pdelie._boundary` module, and the deferred surfaces.
- `CHANGELOG.md` prepended with a `## 0.30.0` entry.
- `configs/release_gate_manifest.json` — new `v0.30` row replacing the `v0.30f` self-check; `current_release_gate_job_name` renamed `v0_30f-release-gate` → `v0_30-release-gate`; `release_count` updated. All existing rows retained.
- `configs/planning/v0_30_nonperiodic_readiness_scope.json` — `status: complete`, `guard_no_version_bump: "0.30.0"`, `expected_ci_jobs: ["v0_30-release-gate", ...]`.
- `.github/workflows/ci.yml` — release-gate job renamed `v0_30f-release-gate` → `v0_30-release-gate`.
- Test guards flipped: `tests/test_current_release_gate.py`, `tests/test_v0_30_scope_freeze.py`, `tests/test_v0_30_hygiene_audit.py`, `tests/test_v0_30e_hygiene_config.py`.

## Explicit Non-Goals for v0.30 Release Close

- No new runtime feature. No `src/pdelie/` change beyond what already landed in v0.30b–f.
- No symmetry-method registry, root API, PDEBench/The Well support claim, KdV/KS/weak nonperiodic, or nonperiodic finite-transform support.
- No lift of the `numpy<2` cap. No Python matrix expansion. No promotion of the `lint`/`typecheck`/`coverage` CI jobs from advisory to blocking.
- No standalone `tests/test_v0_30_release_gate.py` file — the declarative gate lives as a row in `configs/release_gate_manifest.json` replayed by `tests/test_release_gates.py`.
- No PyPI or TestPyPI publication. Git-tag-only.

---

# PDELie - Execution Plan (V0.30f)

**Status:** COMPLETE (merged as PR #79)

`v0.30f` lands the narrow declarative release-gate consolidation proposed in `docs/design/V0_30_HYGIENE_AUDIT.md`. A strict-JSON manifest at `configs/release_gate_manifest.json` encodes 18 release rows of declarative assertions; the parameterized `tests/test_release_gates.py` replays them. The CI release-gate job is renamed `v0_29-release-gate` → `v0_30f-release-gate` and its invocation extended to run the manifest test alongside every retained per-version file. No runtime behavior change. No package version bump. No new dependency. No `src/pdelie/` change. Zero files deleted — consolidation is by manifest addition, not by file removal.

Decision label:

```text
narrow_declarative_release_gate_consolidation
```

## Files touched (v0.30f)

- `configs/release_gate_manifest.json` — new. Strict JSON, `summary_type = "pdelie_declarative_release_gate_manifest"`, `release_count = 18`, plus `excluded_functional_release_gate_files` listing every file whose declarative content stays in-place (with per-file reason).
- `tests/test_release_gates.py` — new. Loads the manifest, runs 4 meta-level tests (strict-JSON, release-count parity, only-supported-classes, job-name/CI-workflow alignment), and one parametrized test that dispatches to a per-class handler. Failure messages always start with `[v<release>][<assertion_class>]`.
- `.github/workflows/ci.yml` — modified. Renames the release-gate job; extends its `run:` to invoke `tests/test_current_release_gate.py`, `tests/test_release_gates.py`, and every retained `tests/test_v0_NN_release_gate.py` (v0.4 through v0.29). No other job change.
- `tests/test_current_release_gate.py` — modified. Expects `["v0_30f-release-gate"]`, requires the invocation to reference the new manifest test file, and gains a `"v0_29-release-gate:" not in workflow` regression guard.
- `tests/test_v0_30_hygiene_audit.py` — modified. Adds `test_v0_30f_release_gate_consolidation_manifest_exists`, `test_v0_30f_all_release_gate_files_are_retained` (26 == 26), and `test_v0_30f_hygiene_audit_records_consolidation_landed`. Updates the release-gate-job regex check from `["v0_29-release-gate"]` to `["v0_30f-release-gate"]`.
- `docs/design/V0_30_HYGIENE_AUDIT.md` — appended "Release-gate consolidation IMPLEMENTED narrowly in v0.30f" summary; rewrote the "Release-gate consolidation" section to describe what shipped, what is excluded, and why the "delete 26 files" outcome was scoped down.
- `docs/planning/PLAN.md` — this file. Replaces v0.30e header with v0.30f header.
- `docs/planning/ROADMAP.md` — `v0.30f` status flipped from `Planned` to `In progress` (or `Completed` on merge).
- `docs/specs/API_STABILITY.md` — Decision-only note for the frozen `v0.30f` narrow declarative release-gate consolidation.

## Explicit non-goals for v0.30f

- No deletion of any `tests/test_v0_NN_release_gate.py` file. All 26 stay in place.
- No modification of any assertion inside an existing release-gate file. The manifest replays declarative content; the source files remain unchanged.
- No extension of the supported-assertion-class schema beyond the 11 classes listed above. Novel patterns (forbidden phrases in a doc, CHANGELOG/README/ROADMAP_HISTORY/SUPPORT_MATRIX phrase checks, disjunctive+forbidden per-page phrase rules, `required_json_fields` on manifests) are named as schema gaps in the manifest's `excluded_functional_release_gate_files` list and left in their source files. Extending the schema is separate future work.
- No `src/pdelie/` change. No runtime API. No new root export. No new optional dependency.
- No version bump (`pyproject.toml` stays at `0.29.0`).
- No lift of the `numpy<2` cap. No Python matrix expansion. No promotion of v0.30e's `lint`/`typecheck`/`coverage` jobs from advisory to blocking.

---

# PDELie - Execution Plan (V0.30e)

**Status:** COMPLETE (merged as PR #78)

`v0.30e` lands cross-cutting hygiene phase 1 as spec'd in `docs/design/V0_30_HYGIENE_AUDIT.md`: `[tool.ruff]`, `[tool.mypy]` (strict scope narrowed), `[tool.coverage.*]` in `pyproject.toml`, plus three non-blocking CI jobs (`lint`, `typecheck`, `coverage`). No runtime behavior change. No package version bump. No new optional dependency in runtime extras (only test extras).

Decision label:

```text
hygiene_phase_1_non_blocking_ruff_mypy_coverage
```

## Implemented Surfaces

- `pyproject.toml`:
  - `[tool.ruff]` with `target-version = "py311"`, `line-length = 120`, `extend-select = ["E", "W", "F", "B", "I", "UP", "RUF", "NPY"]`, `extend-exclude = ["notebooks/*.ipynb"]`.
  - `[tool.ruff.lint.per-file-ignores]` with targeted, documented ignores. Test files carry a broad ignore for advisory patterns (B905, RUF043, RUF012) plus per-file E501/E402 for legitimate long-fixture files. Src files carry per-file E501 ignores where breaking long lines in status-return statements hurts readability.
  - `[tool.mypy]` with `python_version = "3.11"`, `warn_unused_configs`, `warn_unreachable`, `warn_redundant_casts`, `show_error_codes`, plus a `strict = true` override for `pdelie.contracts`, `pdelie._boundary`, `pdelie.derivatives.*`. Data and residuals modules are outside strict scope for v0.30e — NumPy strict-typing pain (missing type-args on ndarray without stubs) makes them impractical at strict mode without significant clutter for no correctness benefit. Broaden in v0.30.1 or later.
  - `[tool.coverage.run]` with `source = ["src/pdelie"]`, `branch = true`, `omit = ["*/tests/*", "*/__init__.py"]`.
  - `[tool.coverage.report]` with `show_missing = true`, `fail_under = 80`, standard `exclude_lines`.
  - `[project.optional-dependencies].test` gains `ruff>=0.6`, `mypy>=1.11`, `pytest-cov>=5.0`.

- `.github/workflows/ci.yml`: three new jobs on `ubuntu-latest` / Python 3.11, all `continue-on-error: true`:
  - `lint` — `python -m ruff check .`
  - `typecheck` — `python -m mypy src/pdelie`
  - `coverage` — `python -m pytest --cov=src/pdelie --cov-report=xml --cov-report=term-missing`, plus artifact upload of `coverage.xml`.

- Src fixes applied to make the strict-scope mypy clean and the ruff rule set green:
  - Docstring reordered above `from __future__ import annotations` in 5 src files (`symmetry/{closure,symbolic,span}.py`, `symmetry/_polynomial_metric.py`, `discovery/pysindy_bridge.py`) — required to satisfy E402 without weakening the module docstring convention.
  - 5 `zip(...)` calls in src gained `strict=False` (behavior-preserving; documents the fixture-pairing invariant).
  - 1 unused loop variable renamed to `_index` in `discovery/pysindy_adapter.py`.
  - `contracts.py`: every `np.ndarray` annotation updated to `np.ndarray[Any, Any]` (mypy strict scope requirement). One `# type: ignore[unreachable]` added to `GeneratorFamily.__post_init__`'s `if self.diagnostics is None: ...` branch, which mypy narrows away based on the declared dataclass type but which is runtime-reachable because the field default is `None`.
  - `derivatives/spectral_fd.py` and `derivatives/finite_difference.py`: `typing.Any` import + `np.ndarray[Any, Any]` on the one internal helper each.
  - 2 unused local variables removed (`values` in `test_finite_difference_backend.py` and `plan` in `test_api_stability_audit.py`).

## Observed Metrics at v0.30e HEAD

- ruff: **442 baseline errors → 0** (192 auto-fixed via `ruff check --fix`; 8 manual fixes to src; per-file-ignores added for a documented list of files, each with a rule + reason).
- mypy strict scope (`pdelie.contracts`, `pdelie._boundary`, `pdelie.derivatives.*`): **0 errors**, 5 source files checked.
- mypy full-tree (advisory, non-blocking): 311 errors across 44 files, dominated by `[type-arg]` on `np.ndarray` in `data/*` and `residuals/*`. These would each need `[Any, Any]` annotations or numpy stubs to clear. Not blocking, not shipping — captured here as a v0.30.1 or later stretch.
- coverage on `src/pdelie/`: **86%** (line + branch), well above the 80% floor.
- pytest: **1028 passed, 2 skipped** (unchanged from v0.30d).

## Tests Added

- `tests/test_v0_30e_hygiene_config.py` — asserts the ruff/mypy/coverage sections exist with the expected shape, test extras include the three new tools, numpy/Python/version guards are unchanged, and the three new CI jobs exist AND are non-blocking. Also guards that v0.30f's release-gate consolidation has not preempted.

## Tests Updated

- `tests/test_v0_30_hygiene_audit.py`:
  - `test_v0_30_no_premature_pyproject_changes` inverted to `test_v0_30e_pyproject_now_configures_ruff_mypy_coverage` (checks presence, still guards numpy cap + Python floor + version).
  - `test_v0_30_no_premature_ci_changes` inverted to `test_v0_30e_ci_workflow_now_has_lint_typecheck_coverage_jobs_nonblocking` (checks presence + non-blocking property + no v0.30f preemption).
  - The 26-release-gate-file count assertion, strict-JSON, and lazy-optional-import documentation checks all stay unchanged.

## Public-Surface Audit

Confirmed in `v0.30e`:

- no new `pdelie` root export
- no new submodule runtime API
- no new *runtime* optional dependency (only test extras: ruff, mypy, pytest-cov)
- no new PDE, no KdV/KS nonperiodic, no weak nonperiodic
- no PDEBench / The Well support claim
- no symmetry-method registry
- no `pyproject.toml` version bump — still `0.29.0`
- no CI job becomes blocking (all three new jobs are `continue-on-error: true`)
- no numpy cap change (still `<2`)
- no Python matrix expansion (still 3.11-only)

## v0.30e Sub-Release Gate

`v0.30e` is complete when:

- `[tool.ruff]`, `[tool.mypy]`, `[tool.coverage.*]` are configured in `pyproject.toml` with the exact shape spec'd in `V0_30_HYGIENE_AUDIT.md`.
- The three CI jobs (`lint`, `typecheck`, `coverage`) exist and are non-blocking.
- Strict-scope mypy passes cleanly (0 errors).
- `ruff check .` passes cleanly (0 errors under the configured rule set + per-file-ignores).
- Coverage clears the 80% floor.
- The full test suite still passes.
- `git diff --check` reports no whitespace damage.

---

# PDELie - Execution Plan (V0.30d)

**Status:** COMPLETE

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
