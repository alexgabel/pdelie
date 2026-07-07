# V0.30 Scope - Nonperiodic Readiness and Low-Order Finite-Difference Derivative Diagnostics

**Status:** COMPLETE

`v0.30` is the nonperiodic-readiness and low-order finite-difference derivative-diagnostics release.

It loosens canonical ingestion to accept structured nonperiodic boundary conditions for scalar 1D fields, adds a finite-difference derivative backend limited to `u_t`, `u_x`, and `u_xx`, and lands cross-cutting hygiene infrastructure (ruff, mypy, coverage) under staged enforcement. It does not change the existing periodic spectral derivative path, does not promote any new PDE, does not add a symmetry-method registry, and does not unlock any external-dataset support claim.

This file documents the frozen scope. The first executed slice is the design-only sub-release `v0.30a`, which adds documents, configs, and audit tests without modifying any runtime code or bumping the package version.

Release conclusion (recorded by v0.30a, finalized by v0.30 proper):

```text
nonperiodic_readiness_and_low_order_finite_difference_diagnostics_design_only
```

## Stable Intent

v0.30 widens the canonical-ingestion surface from "periodic x only" to "periodic and structured nonperiodic" for scalar 1D fields, and adds a corresponding low-order finite-difference derivative backend. The existing periodic spectral path stays untouched. The release ships diagnostics, not new PDE-domain support claims.

Three explicit user paths are unlocked:

1. structured boundary metadata: `metadata["boundary_conditions"]["x"]` becomes a structured spec with `type`, optional per-face values, and explicit `specified` provenance
2. finite-difference derivative diagnostics: `u_t`, `u_x`, `u_xx` on Dirichlet, Neumann, and `open_unknown` data
3. residual preflight on manufactured nonperiodic Heat, Burgers, and advection-diffusion fields, with interior-vs-full-grid residual domain policy

## Scope

The v0.30 release scope is:

- scalar 1D nonperiodic readiness for canonical `FieldBatch` inputs
- low-order finite-difference derivative backend (implementation limited to u_t, u_x, u_xx — no higher orders on nonperiodic data in the stable `v0.30` surface)
- design and implementation of structured `BoundaryConditionSpec`
- cross-cutting hygiene preparation, audit-only in v0.30a and staged enforcement in v0.30 proper
- release-gate consolidation proposal (consolidation lands in v0.30 proper, not v0.30a)

The v0.30 deliverables, design-frozen in v0.30a and implemented in v0.30 proper:

- structured `BoundaryConditionSpec` accepting legacy string inputs and normalizing them under a backwards-compatible loader
- `compute_finite_difference_derivatives(field, *, max_spatial_order=2)` for `u_t`, `u_x`, `u_xx` only
- `compute_derivatives(field, *, backend="auto", max_spatial_order=...)` dispatcher that records its selection explicitly in `DerivativeBatch.config`
- residual interior-vs-full-grid policy reported on residual summaries
- Heat, Burgers, and advection-diffusion residual preflight on manufactured nonperiodic scalar fields
- readiness reports updated to surface boundary-condition under-specification as `needs_attention`
- cross-cutting hygiene: `[tool.ruff]`, `[tool.mypy]` (initially strict on `src/pdelie/contracts.py`, `src/pdelie/derivatives/`, `src/pdelie/data/`, `src/pdelie/residuals/` only), `[tool.coverage]` in `pyproject.toml`; new audit-only CI jobs

## Deferred Scope

Explicit non-goals (the scope-freeze test will assert these phrases are present):

- no PDEBench support claim
- no The Well support claim
- no file loaders or broad adapter framework
- no KdV nonperiodic
- no KS nonperiodic
- no public KS runtime API
- no weak nonperiodic
- no public weak derivative backend
- no high-order nonperiodic finite differences
- no `u_xxx` or `u_xxxx` on nonperiodic data in the stable v0.30 surface
- no finite-transform verification for nonperiodic translations
- no symmetry arena
- no symmetry-method registry
- no root `pdelie.discover_symmetries`
- no external symmetry-method ports
- no new root pdelie exports
- no neural or callable generator APIs
- no train/test policy or leakage prevention
- no PyPI or TestPyPI publication; package-index publishing remains deferred to `v1.0` or later

The symmetry-method registry is the v0.30.1 deliverable, not v0.30. The PySINDy `PDELibrary` / `WeakPDELibrary` task-bridge work is v0.31. External-dataset readiness cookbooks (one scalar 1D PDEBench slice, optionally one scalar 1D The Well slice) are v0.32.

## Boundary Condition Schema (Designed in v0.30a)

The structured form is documented in `docs/design/BOUNDARY_CONDITION_SPEC.md`. Summary:

```
metadata["boundary_conditions"]["x"] = {
    "type": "periodic" | "dirichlet" | "neumann" | "open_unknown",
    "left": BoundaryFace | None,
    "right": BoundaryFace | None,
    "specified": bool,
    "time_dependent": bool | None,
    "notes": str | None,
}
```

`BoundaryFace` carries `{"value": float | None, "time_dependent": bool, "source": "user_supplied" | "default" | "inferred_unspecified"}`.

Legacy `0.1`-schema payloads that present `boundary_conditions["x"]` as a string normalize to the structured form under the v0.30 loader; the normalization is recorded in `preprocess_log` under operation `"schema_0_1_to_0_2_boundary_normalization"`. `FieldBatch.SCHEMA_VERSION` bumps `0.1` to `0.2`; `from_dict` accepts both versions. v0.30a does not bump the schema; v0.30 proper does.

## Derivative Backend Policy (Designed in v0.30a)

The full policy is documented in `docs/design/DERIVATIVE_BACKEND_POLICY.md`. Summary:

- `spectral_fd` remains periodic-only; the check at `src/pdelie/derivatives/spectral_fd.py:32-33` is unchanged
- `finite_difference` v1 supports `u_t`, `u_x`, `u_xx` on Dirichlet, Neumann, and `open_unknown` data
- `u_xxx` and `u_xxxx` on nonperiodic data are not part of the stable v0.30 surface
- `compute_derivatives(backend="auto")` dispatch is explicit: `DerivativeBatch.config` records `backend_selected_by_boundary_condition` and `backend_selection_reason`
- residual domain policy on nonperiodic FD-derived residuals defaults to `interior_only`
- finite-transform translation verification on nonperiodic data is deferred to v0.31.5 (overlap-crop design)

## Hygiene Audit (Performed in v0.30a)

The audit baseline is documented in `docs/design/V0_30_HYGIENE_AUDIT.md`. Headline findings:

- no `[tool.ruff]`, `[tool.mypy]`, or `[tool.coverage]` in `pyproject.toml` today
- CI runs only Python 3.11
- `numpy>=1.24,<2` is the current upper-bound cap
- 26 per-release-gate test files exist; consolidation is proposed via a parameterized test driven by a manifest file
- optional-dependency lazy import pattern at `src/pdelie/discovery/pysindy_adapter.py:12-20` is the reference implementation; the audit confirms the policy must remain unchanged
- strict JSON / `allow_nan=False` discipline confirmed; the audit confirms new outputs must follow it

Staged enforcement (no implementation in v0.30a, designed only):

1. Phase 0 (v0.30a): audit-only
2. Phase 1 (v0.30 proper): ruff, mypy (strict on core modules, lenient elsewhere), coverage; non-blocking CI
3. Phase 2 (v0.30.1 or v0.31): mypy strict across `src/pdelie/`; blocking CI
4. Phase 3 (v0.32): Python 3.11 / 3.12 / 3.13 matrix; numpy 2.x side-job validation
5. Phase 4 (v1.0): lift `numpy<2` cap once 2.x validation has soaked

## Milestone Status

- Milestone 0: scope freeze and design documents - COMPLETE (in v0.30a)
- Milestone 1: structured `BoundaryConditionSpec` runtime - COMPLETE (in v0.30b)
- Milestone 2: `compute_finite_difference_derivatives` and dispatcher - COMPLETE (in v0.30c)
- Milestone 3: residual domain policy uptake in summaries - COMPLETE (in v0.30c) and residual evaluator auto-dispatch - COMPLETE (in v0.30d)
- Milestone 4: manufactured nonperiodic residual preflight tests - COMPLETE (in v0.30c and v0.30d)
- Milestone 5: ruff/mypy/coverage Phase 1 in `pyproject.toml` and CI - COMPLETE (in v0.30e, non-blocking)
- Milestone 6: release-gate consolidation - COMPLETE narrowly (in v0.30f; manifest-driven, zero file deletions)

## Release Gate (v0.30 close)

`v0.30.0` shipped with the following criteria satisfied:

- `FieldBatch.SCHEMA_VERSION` is `"0.2"` and `from_dict` accepts both `"0.1"` and `"0.2"` payloads — landed in `v0.30b`.
- `compute_finite_difference_derivatives` is importable from `pdelie.derivatives` and supports `u_t`, `u_x`, `u_xx` on Dirichlet/Neumann/`open_unknown` data — landed in `v0.30c`.
- `compute_derivatives(backend="auto")` is importable and records its selection explicitly in `DerivativeBatch.config` — landed in `v0.30c`.
- Heat, Burgers, advection-diffusion, and reaction-diffusion residual evaluators route through `compute_derivatives(backend="auto")` when derivatives are omitted — landed in `v0.30d`.
- `summarize_residual_batch` and `summarize_field_batch_readiness` expose `residual_domain_policy` and `boundary_condition_warnings` respectively — landed in `v0.30c`.
- `[tool.ruff]`, `[tool.mypy]`, `[tool.coverage]` are configured in `pyproject.toml`; the `lint`, `typecheck`, and `coverage` CI jobs run as **advisory / non-blocking** — landed in `v0.30e`. Promotion to blocking is Phase 2 (post-v0.30).
- The parameterized release-gate consolidation lands as `configs/release_gate_manifest.json` + `tests/test_release_gates.py`. **Narrowly**: no per-version `tests/test_v0_NN_release_gate.py` file is deleted; the consolidation is by manifest addition. Files that use assertion patterns outside the 11 supported classes stay in-place and are listed in `excluded_functional_release_gate_files` — landed in `v0.30f`.
- The v0.30 declarative gate is a row in `configs/release_gate_manifest.json` replayed by `tests/test_release_gates.py`; a standalone `tests/test_v0_30_release_gate.py` file is intentionally not added.
- The full test suite passes.
- Package metadata is bumped to `0.30.0`; `numpy>=1.24,<2` and `requires-python >=3.11` are unchanged.
- Git-tag-only; PyPI/TestPyPI remain deferred to `v1.0` or later.

## v0.30a Sub-Release Gate

v0.30a is complete when:

- this scope document is in place and the scope-freeze test passes
- the three design documents in `docs/design/` are in place
- `docs/planning/ROADMAP.md` records v0.30a
- `docs/planning/PLAN.md` records v0.30a as IN_PROGRESS with the decision label
- `docs/specs/API_STABILITY.md` contains a "Decision-only note for the frozen v0.30a" subsection
- `configs/planning/v0_30_nonperiodic_readiness_scope.json` is present and strictly JSON-compatible (`allow_nan=False`)
- `tests/test_v0_30_scope_freeze.py` and `tests/test_v0_30_hygiene_audit.py` pass
- the full test suite still passes
- no file under `src/pdelie/` is modified
- no version bump in `pyproject.toml`
- no new optional dependency added
- no new CI job added
