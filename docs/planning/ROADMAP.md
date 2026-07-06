# PDELie Roadmap

This is the authoritative release-planning document for `pdelie`.

It records current status, the next planned direction, and compact release history. It does **not** define package contracts. Stable behavior is defined in:

- `../specs/SPEC.md`
- `../specs/CONTRACTS_AND_DEFAULTS.md`
- `../specs/API_STABILITY.md`
- `../specs/SUPPORT_MATRIX.md`

Execution state belongs in `PLAN.md`.

Long historical release detail is archived in `archive/ROADMAP_HISTORY.md`.

---

## Current State

- Current completed release: `v0.29.0`
- Current release decision: `workflow_recipes_and_support_matrix_complete_no_new_numerical_scope`
- Current theme: workflow recipes and support matrix, with no new numerical scope, runtime helper, public API, or root export
- Current package policy: Git-tag-only `v0.x` releases; PyPI/TestPyPI publishing remains deferred until `v1.0` or later
- Current user entry points: repository-root `README.md`, hosted RTD docs, `docs/workflows/`, `docs/specs/SUPPORT_MATRIX.md`, and rendered tutorials in `notebooks/`

## Next Planned Work

The next release `v0.30` is design-frozen by the `v0.30a` sub-release (audit-only, no runtime change, no version bump). Runtime implementation lands in `v0.30` proper.

Planned direction:

| Target | Theme | Status | Notes |
| --- | --- | --- | --- |
| `v0.26b` | KS promotion | Reserved | Only if a separate scope freeze accepts direct-SVD/no-fallback KS evidence. |
| `v0.30a` | Scope freeze + design contracts | Completed | Audit-only sub-release. No runtime change, no version bump. Froze BoundaryConditionSpec and derivative-backend policy. |
| `v0.30b` | BoundaryConditionSpec runtime + FieldBatch 0.2 migration | Completed | Implemented the structured boundary spec, `FieldBatch.from_dict` 0.1->0.2 migration, and the `is_x_periodic` helper centralization. Adapters accept structured nonperiodic specs; downstream consumers stay strict-periodic. |
| `v0.30c` | Finite-difference derivative backend (low-order) + boundary-aware reporting | Completed | Ships `compute_finite_difference_derivatives` (`u_t`, `u_x`, `u_xx` only), the `compute_derivatives(backend="auto")` dispatcher, `boundary_condition_warnings` on readiness summaries, and the `residual_domain_policy` field on residual summaries. |
| `v0.30d` | Residual evaluator auto-dispatch + interior-only diagnostics | Completed | Heat, Burgers, advection-diffusion, and reaction-diffusion evaluators route through `compute_derivatives(backend="auto")` and consume `recommended_residual_domain_policy` / `recommended_boundary_trim_width` from `DerivativeBatch.config`. KdV and weak stay periodic-only. |
| `v0.30e` | Hygiene phase 1 | In progress | `[tool.ruff]`, `[tool.mypy]` (strict scope narrowed to contracts+_boundary+derivatives), `[tool.coverage]` configured; three non-blocking CI jobs added (`lint`, `typecheck`, `coverage`). Coverage baseline 86%. `numpy<2` cap not lifted (deferred). |
| `v0.30f` | Release-gate consolidation (narrow declarative) | Planned | Consolidate the declarative subset of the 26 `tests/test_v0_NN_release_gate.py` files into one manifest + parameterized test. Functional smoke tests stay explicit. |
| `v0.30` | Release close: Nonperiodic readiness + low-order FD diagnostics + hygiene preparation | Planned | Final v0.30 release; bumps `pyproject.toml` version to `0.30.0` and tags. |
| `v0.30.1` | Submodule-only SymmetryMethod registry MVP | Planned | One built-in adapter (`polynomial_translation_svd`). No root API. No external method ports. |
| `v0.31` | Downstream discovery task bridge | Planned | Unlock PySINDy `PDELibrary` config, add `WeakPDELibrary` diagnostic wrapper. Tasks live under `pdelie.tasks.discovery`, not under the symmetry registry. |
| `v0.31.5` | Nonperiodic orbit/action scope decision | Planned | Overlap-crop design for nonperiodic translation; decision on whether finite-transform/orbit action machinery can be promoted beyond diagnostics. |
| `v0.32` | External dataset readiness cookbooks | Planned | One scalar 1D PDEBench slice readiness and, if feasible, one scalar 1D The Well slice readiness. No recovery benchmark claim. |
| `v0.33` | First external symmetry candidate-generator method | Planned | Ko-style sparse generator behind an experimental flag. LieGAN/LaLiGAN as a later optional stochastic extra. |
| `v0.34` | Multi-channel / 2D contract widening scope decision | Planned | Required for any meaningful The Well coverage. Relaxes `var_names` length-1 and the canonical `('batch','time','x','var')` dim layout. |
| `v0.35` | Trained-model extraction layer | Planned | `TrainedModelArtifact` contract; LieGG-style extraction adapter. Distinct API path from `fit(field, residual_evaluator=...)`. |
| `v1.0` | Stable public engine; PyPI publish; optional root-entry decision | Planned | Stabilization milestone. Reopens the root one-call API question explicitly rather than pre-banning it. |

## Planning Labels

- **Committed** - frozen for the active release series.
- **Planned** - intended later, but not frozen.
- **Experimental** - research direction, not stable API.
- **Deferred** - intentionally postponed.

Only **Committed** work may define the next stable release.

## Release Philosophy

PDELie advances one stable axis at a time.

1. A release expands at most one major scientific or numerical axis.
2. Stable scope grows only after the previous scope is proven end to end.
3. Experimental work may inform future releases but does not define public API.
4. Supportability reports are empirical configured evidence, not mathematical proofs or benchmark success claims.
5. Public examples and notebooks must remain paper-agnostic and self-contained.

## Completed Releases

| Release | Status | Theme | Public-surface conclusion |
| --- | --- | --- | --- |
| `v0.1.x` | Completed | First Heat vertical slice | Stabilized canonical `FieldBatch -> DerivativeBatch -> ResidualBatch -> GeneratorFamily -> VerificationReport`. |
| `v0.2` | Completed | Burgers as second PDE | Added a second PDE under the same stable pipeline. |
| `v0.3` | Completed | Invariant map contracts | Added public invariant-map objects and portable contracts without orbit expansion. |
| `v0.4` | Completed | Closure/span/viz diagnostics | Added algebraic diagnostics and visualization over existing generator objects. |
| `v0.5` | Completed | Portability and manifest contracts | Hardened generator-family interchange without executable generator APIs. |
| `v0.6` | Completed | Downstream bridge and robustness | Added narrow PySINDy bridge/evaluation paths. |
| `v0.7` | Completed | External array ingestion core | Added structured `from_numpy(...)` style ingestion without broad adapters. |
| `v0.8` | Completed | Frozen weak residual reports | Added narrow Heat/Burgers weak residual report slices. |
| `v0.9` | Completed | KdV strong path | Added normalized short-horizon KdV strong residual/fitting path. |
| `v0.10` | Completed | Reporting consolidation | Standardized runtime reporting surfaces. |
| `v0.11` | Completed | Derivative/order hardening | Hardened derivative support through higher orders needed by existing scope. |
| `v0.12` | Completed | Diagnostics and supportability | Added fit diagnostics and explicit KS no-go guardrails. |
| `v0.13` | Completed | Orbit/coverage diagnostics | Added public coverage and uniform-translation consistency diagnostics. |
| `v0.14` | Completed | Invariant workflow summaries | Added read-only orbit and invariant workflow summaries. |
| `v0.15` | Completed | Materialized orbit batches | Added controlled uniform-translation orbit batch results with provenance. |
| `v0.16` | Completed | External candidate validation | Added configured validation for supplied symmetry candidates. |
| `v0.17` | Completed | Formula generator family validation | Added safe formula-backed generator records without executable strings. |
| `v0.18` | Completed | Fisher-KPP strong path | Added stable reaction-diffusion/Fisher-KPP strong path. |
| `v0.19` | Completed | Advection-diffusion strong path | Added stable constant-coefficient advection-diffusion strong path. |
| `v0.20` | Completed | Generator confidence reports | Added categorical evidence-backed generator confidence reports. |
| `v0.21` | Completed | Field readiness reports | Added external-data readiness reporting for canonical scalar 1D periodic `FieldBatch`. |
| `v0.22` | Completed | Downstream discovery contracts | Added bridge/result/workflow summaries without backend framework expansion. |
| `v0.23` | Completed | Split/leakage provenance diagnostics | Added report-only partition provenance and overlap diagnostics. |
| `v0.24` | Completed | Weak-form supportability reset | Added weak supportability reports while deferring WSINDy, weak backends, weak KdV/KS. |
| `v0.25` | Completed | KdV scope decision | Kept public KdV frozen to normalized short-horizon strong path. |
| `v0.26` | Completed | KS revisit decision | Kept KS runtime APIs deferred; reserved `v0.26b` for separate promotion only if evidence settles. |
| `v0.27` | Completed | Multi-generator diagnostics decision | Promoted diagnostics for supplied multi-row families; deferred fitting, finite actions, BCH, orbit charts. |
| `v0.28` | Completed | Narrow xarray Dataset ingestion | Added explicit scalar Dataset readiness/conversion; deferred file loaders and broad adapters. |
| `v0.29` | Completed | Workflow recipes and support matrix | Added workflow docs, machine-readable support matrix, and rendered recipe notebooks; no new runtime API. |

## Current Support Matrix

The compact public support matrix lives in:

- `../specs/SUPPORT_MATRIX.md`
- `../specs/support_matrix.v0_29.json`

Current stable PDE rows:

| PDE | Generator | Residual | Vertical slice | Candidate validation | Weak support | External-data readiness |
| --- | --- | --- | --- | --- | --- | --- |
| Heat | yes | yes | yes | yes | frozen weak slice | yes |
| Burgers | yes | yes | yes | yes | frozen weak slice | yes |
| KdV | normalized short-horizon only | yes | yes | yes | no | yes |
| Fisher-KPP | yes | yes | yes | yes | internal weak diagnostic only | yes |
| Advection-diffusion | yes | yes | yes | yes | no | yes |
| KS | no public runtime | no | no | diagnostic/no-go | no | no |

## Deferred Surfaces

The following remain deferred unless explicitly frozen in a later scope:

- public KS runtime APIs
- broad file loaders, PDEBench/The Well loaders, NetCDF/Zarr loaders, and adapter registries
- nonuniform, multidimensional, or multivariable stable numerical scope
- weak derivative backends, WSINDy design matrices, weak sparse recovery, weak KdV, and weak KS
- public multi-generator fitting, finite multi-generator flows, BCH composition, group-action atlases, and orbit charts
- neural/callable generator APIs and operator symmetry
- split creation, split optimization, benchmark policy, and leakage-prevention enforcement
- root export expansion for runtime helpers
- high-order finite-difference derivatives on nonperiodic data (no `u_xxx`, `u_xxxx` in the stable `v0.30` surface)
- finite-transform verification on nonperiodic translations (deferred to `v0.31.5` overlap-crop design)
- weak-form derivatives or weak residuals on nonperiodic data
- root-level one-call symmetry-discovery API (deferred to `v1.0` scope decision)

## Historical Detail

Historical release narratives, original milestone wording, and older medium-term plans are preserved in:

- `archive/ROADMAP_HISTORY.md`
- `archive/V0_15_PLUS_STRATEGY.md`
- `V0_*_SCOPE.md`
- `../releases/V0_*_RELEASE_READINESS.md`

Those files are audit records. This roadmap remains the current planning authority.
