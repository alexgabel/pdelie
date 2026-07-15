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

- Current completed release: `v0.31.0`
- Current release decision: `downstream_discovery_task_bridge`
- Current theme: submodule-only downstream discovery task bridge — periodic scalar 1D PySINDy `PDELibrary` task runner (`discovery_task_result`, 22-key strict-JSON schema), diagnostic-only `WeakPDELibrary` wrapper (`pdelie_weak_pde_library_diagnostic`, 27-key strict-JSON schema, `diagnostic_only = True`), one public JSON-only demonstration example, temporary PySINDy 1.x + `setuptools<82` compatibility policy, and a targeted Python 3.12+ downstream-UX message. Zero root-API expansion; no new PDE; no WSINDy / noise-robustness / nonperiodic-discovery claim.
- Current package policy: Git-tag-only `v0.x` releases; PyPI/TestPyPI publishing remains deferred until `v1.0` or later
- Current user entry points: repository-root `README.md`, hosted RTD docs, `docs/workflows/`, `docs/specs/SUPPORT_MATRIX.md`, `docs/specs/support_matrix.v0_31.json`, `docs/releases/V0_31_RELEASE_READINESS.md`, and rendered tutorials in `notebooks/`

## Next Planned Work

`v0.31` is closed. The next active scientific items, in order:

1. **`v0.31.1a` — research spike (Completed, merged as PR #101).** SPEC 0 runtime-compatibility policy + PySINDy 2.x API delta audit + machine-readable compatibility matrix + private compatibility prototype (research-only, deleted by v0.32a).
2. **`v0.30.1` — submodule-only `SymmetryMethod` registry MVP + `SymmetryCandidate` wrapper contract freeze (Completed, merged as PR #102).** Representation-neutral `SymmetryCandidate` contract + lazy registry + one built-in adapter (`polynomial_translation_svd`). Ships publicly under the v0.32.0 tag per the solo-dev consolidation policy — no `v0.30.1` tag was created.
3. **`v0.32a` — modern runtime migration (IN PROGRESS on `feat/v0.32a-modern-runtime-migration`).** Python ≥3.12 minimum, NumPy 2.x, PySINDy 2.1.x. Six API-break sites migrated; `_pysindy2_prototype.py` deleted; `setuptools<82` cap retired; `SymmetryCandidate` reserved-type construction hardened. New CI matrix (Python 3.12/3.13 blocking, 3.14 advisory core-only).
4. **`v0.32b` — strict `method_scores` + optional `uncertainty_report` bootstrap over batch/trajectory units + `calibration_report` skeleton.** Adds three additive fields to `summarize_generator_confidence`.
5. **`v0.32c` — composed candidate-to-task workflow example.** Public JSON-only runner demonstrating `FieldBatch → SymmetryMethod → SymmetryCandidate → validate → verify → run_pysindy_pde_task → composed report`.
6. **`v0.32d` — one honest PDEBench readiness cookbook.** Single scalar 1D slice; The Well feasibility scan.
7. **`v0.32.0` — release close.** Version bump 0.31.0 → 0.32.0, `V0_32_RELEASE_READINESS.md`, `support_matrix.v0_32.json`, release-gate manifest 0.31 → 0.32 row. Only v0.32.0 is tagged. Legacy Python 3.11 / PySINDy 1.x line retires to a `release/v0.31.x` maintenance branch.

Per the earlier sequencing agreement, `v0.31` (downstream discovery task bridge) preceded `v0.30.1` (submodule-only symmetry-method registry MVP): the task-bridge release delivered the biggest user-facing scientific delta of the near-term work, while the registry MVP is smaller and can follow.

Planned direction:

| Target | Theme | Status | Notes |
| --- | --- | --- | --- |
| `v0.26b` | KS promotion | Reserved | Only if a separate scope freeze accepts direct-SVD/no-fallback KS evidence. |
| `v0.31a` | Downstream discovery task bridge scope freeze | In progress | Design-only sub-release. Records the decision label `downstream_discovery_task_bridge_design_only`. Freezes the `pdelie.tasks.discovery` submodule shape, the `TaskResult` schema (`summary_type = "discovery_task_result"`), and the `WeakPDELibrary` diagnostic wrapper. No runtime code, no root API, no version bump. |
| `v0.31b0` | Term-mapping golden + PDL-JSON prep | Completed | Pre-runtime sub-release. Adds `tests/test_v0_31b0_pysindy_term_mapping_golden.py` to pin the current PySINDy feature-name / library-term / `summarize_discovery_result` mapping surface (17-key top-level schema, `returns_coefficients=False`, bridge `f"{var}__x_index_{i}"` convention) BEFORE the v0.31b1 task runner is written, so the runner cannot silently absorb accidental mapping changes. Also anchors the PDL-JSON schema tickets (canonical-term convention, `WeakPDELibrary` wrapper identifiers, `TaskResult` composition boundary) referenced by the v0.31a design. No runtime code, no root API, no version bump. |
| `v0.31b1` | Discovery task runtime — PDELibrary periodic-only | Completed (PR #95) | First runtime sub-release. Landed `pdelie.tasks.discovery` with `run_pysindy_pde_task`, `summarize_discovery_task_result`, and `PySINDyDiscoveryUnsupportedBoundaryError`. PDELibrary periodic-only runner + TaskResult wrapper + runtime BC guard. Loosens `fit_pysindy_discovery` config-lock to accept a caller-supplied `pysindy_model`. `pysindy_bridge_variant = "periodic_only_v1"` on every TaskResult. Submodule-only; no root API. No version bump (`pyproject.toml` stays at `0.30.0`). |
| `v0.31b2` | Discovery task runtime — WeakPDELibrary diagnostic wrapper | Completed (PR #96) | Second runtime sub-release under v0.31. Landed `pdelie.tasks.weak_pde_library` with `WeakPDELibraryDiagnostic`, `summarize_pysindy_weak_pde_library_diagnostic`, and `inspect_pysindy_weak_pde_library`. Diagnostic-only wrapper around PySINDy's `WeakPDELibrary`; produces a **separate** top-level summary type (`pdelie_weak_pde_library_diagnostic`, `diagnostic_only=True`), NOT a `discovery_task_result` variant. Submodule-only; also re-exported from `pdelie.tasks`; no root `pdelie` export. Additive `supports_pysindy_weak_library_diagnostic: True` key on the `summarize_weak_form_supportability` policy dict; `supports_weak_derivative_backend` stays `False` and is re-scoped in docstring only. Reuses `PySINDyDiscoveryUnsupportedBoundaryError` on nonperiodic-x inputs. No WSINDy, no noise-robustness claim, no clean/noisy gate, no PDEBench / The Well benchmark claim, no `weak_1d` removal (retained through `v0.32` close). No version bump. |
| `v0.31b3` | Downstream PySINDy compatibility policy + wheel hardening | Completed (PR #97) | Third runtime sub-release under v0.31. Formalizes the existing `pysindy>=1.7.5,<2` pin as a declared temporary policy (`C_temporary_1x_policy` outcome). Adds `docs/design/PYSINDY_COMPATIBILITY_POLICY.md` and `configs/pysindy_compatibility_matrix.json` (machine-readable, `summary_type = "pdelie_pysindy_compatibility_matrix"`). Extends the `0.31` row of `configs/release_gate_manifest.json` in place to forbid future `_pysindy_compat` / `SUPPORTED_PYSINDY_VERSIONS` root and submodule leaks. Pins `pysindy==1.7.5` explicitly on the two existing blocking CI jobs (`editable-tests`, `v0_30-release-gate`). Decision label `downstream_pysindy_compatibility_policy_and_wheel_hardening`. No new PDE, no new schema, no new symmetry registry, no WSINDy claim, no nonperiodic discovery. No compat shim (deferred to `v0.31.1`). No `src/` change. No version bump. |
| `v0.31c` | Downstream task-bridge public example + install self-sufficiency | Completed (PR #98) | Final sub-release under v0.31 before the mechanical release-close PR. Adds `pdelie.examples.run_downstream_discovery_task_bridge_example` (and CLI `python -m pdelie.examples.downstream_discovery_task_bridge`), a compact JSON-only runner that composes both v0.31 paths (`run_pysindy_pde_task` + `inspect_pysindy_weak_pde_library`) on one canonical periodic scalar 1D Heat field. Deterministic under a frozen seed (RNG state save/restore around the PySINDy WeakPDELibrary calls, since its K subdomain-center placement uses numpy's global RNG). Records mandatory clean-install audit — `pip install "<wheel>[downstream]"` proven self-sufficient on Python 3.11 (outcome A); no `setuptools<81` constraint added. Records xfail audit — 3 declared xfails (all in b3), each has a non-empty reason, each defers to v0.31.1. Extends the `0.31` row of `configs/release_gate_manifest.json` in place; no new sub-release row. Decision label `downstream_task_bridge_public_example_and_install_self_sufficiency`. No new PDE, no new schema, no new symmetry registry, no WSINDy claim, no noise robustness claim, no root export, no version bump, no tag. |
| `v0.31c1` | Adversarial downstream-install audit + setuptools cap | Completed (PR #99) | Tiny pre-release compatibility milestone. The v0.31c "outcome A" only held because a newly-created `python -m venv` on Python 3.11 pre-bundles `setuptools 65.5.0` (still ships `pkg_resources`). v0.31c1 runs an adversarial matrix on Python 3.11 with `setuptools==81.0.0/82.0.0/83.0.0` pre-installed BEFORE `pip install "<wheel>[downstream]"`. Verdict: `B_setuptools_82_boundary` — setuptools 81 passes; 82 and 83 fail with `ModuleNotFoundError: No module named 'pkg_resources'` at `import pysindy`. Applies narrow temporary cap `setuptools<82; python_version < '3.12'` to `[downstream]` and `[test]` extras; rebuilt-wheel verification confirms pip auto-downgrades ambient 82/83 to 81. RNG-audit refactor extracts the example's seed/restore into a private `_legacy_numpy_rng_seed_scope` context manager with an explicit not-thread-safe docstring. Adds `tests/test_v0_31c1_downstream_packaging_policy.py` (9 tests, 1 pip-dry-run skip). Decision label `adversarial_downstream_install_audit_and_setuptools_cap`. No new PDE, no new schema, no new symmetry registry, no new example, no WSINDy claim, no noise robustness claim, no root export, no version bump, no tag. |
| `v0.31` | Downstream discovery task bridge | Planned (next) | Unlock PySINDy `PDELibrary` config, add `WeakPDELibrary` diagnostic wrapper. Tasks live under `pdelie.tasks.discovery` and `pdelie.tasks.weak_pde_library`, not under the symmetry registry. Design frozen by v0.31a. Runtime lands in v0.31b+. |
| `v0.30.1` | Submodule-only `SymmetryMethod` registry MVP **and** `SymmetryCandidate` wrapper contract freeze | Planned | One built-in adapter (`polynomial_translation_svd`). The adapter returns `SymmetryCandidate`, never `GeneratorFamily` directly. `SymmetryCandidate` is a discriminated-union wrapper representing `GeneratorFamily`, `FormulaGeneratorFamily`, `InvariantMapSpec`, matrix Lie-algebra generators, coordinate vector fields, finite-transform specs, and latent generators — the shape v0.31's discovery bridge, v0.33's Ko-sparse adapter, and v0.35a's LieGG extraction all consume without needing further contract rework. No root API. No external method ports. Follows `v0.31` per the discovery-first sequencing agreement. |
| `v0.31.1` | PySINDy 2.x port | Planned | Migration release. Introduces `src/pdelie/discovery/_pysindy_compat.py` as a private version-dispatch shim with a `_pysindy_major()` gate plus four helpers (`build_sindy`, `fit_sindy`, `compute_time_derivative`, `build_pde_library`, `build_weak_pde_library`). Absorbs four independent 2.x-API breaks: (i) `SINDy(feature_names=, discrete_time=, t_default=)` constructor kwargs removed — move `feature_names` into `fit()`; (ii) `SINDy.fit(...)` drops `multiple_trajectories/ensemble/library_ensemble/unbias/quiet/replace` and makes `t` positional-required — route ensembling through `EnsemblingOptimizer`; (iii) `SINDy.differentiate` removed — replace `pysindy_model.differentiate(traj, t=t)` in `pdelie.tasks.discovery._compute_residuals_from_predictions` with `model.differentiation_method_(traj, t=t)`; (iv) `PDELibrary`/`WeakPDELibrary` drop `library_functions/function_names/interaction_only` — callers must build a `CustomLibrary`/`PolynomialLibrary` and pass it as `function_library=`. Coordinated `numpy>=2` floor bump (required because `pysindy 2.x` requires `numpy>=2.0` while `pdelie 0.30.0` pins `numpy<2`). Advisory CI job on `pysindy==2.1.0`. No public root export change. |
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
| `v0.29` | Completed | Workflow recipes and support matrix | Added workflow docs, machine-readable support matrix, and rendered recipe notebooks; no new numerical scope, no new runtime helper, and no new runtime API. |
| `v0.30` | Completed | Nonperiodic readiness + low-order FD diagnostics + hygiene preparation | Bumps `pyproject.toml` version to `0.30.0`. Closes the v0.30a–f arc: structured `BoundaryConditionSpec` and `FieldBatch` schema 0.2 (v0.30b), `compute_finite_difference_derivatives` + `compute_derivatives(backend="auto")` dispatcher + boundary-aware readiness (v0.30c), residual evaluator auto-dispatch + interior-only diagnostics for Heat/Burgers/advection-diffusion/reaction-diffusion (v0.30d), non-blocking ruff/mypy/coverage hygiene (v0.30e), narrow declarative release-gate consolidation (v0.30f). No root-API expansion; `numpy<2` and Python-3.11-only matrix unchanged. |
| `v0.31` | Completed | Downstream discovery task bridge | Bumps `pyproject.toml` version to `0.31.0`. Closes the v0.31a–c1 arc: design-only scope freeze + strict `discovery_task_result` schema doc (v0.31a); PySINDy term-mapping golden + strict-JSON debt tickets + preflight audit + label-registry correction (v0.31b0); periodic-only PySINDy `PDELibrary` task runner + `discovery_task_result` (22-key) + `PySINDyDiscoveryUnsupportedBoundaryError` (v0.31b1); diagnostic-only `WeakPDELibrary` wrapper + `pdelie_weak_pde_library_diagnostic` (27-key, `diagnostic_only = True`) + `WeakPDELibraryDiagnostic` dataclass (v0.31b2); temporary `pysindy>=1.7.5,<2` policy + machine-readable compat matrix + CI pins (v0.31b3); public JSON-only example runner `pdelie.examples.run_downstream_discovery_task_bridge_example` + clean-install audit outcome A + xfail ledger (v0.31c); adversarial setuptools 81/82/83 matrix + temporary `setuptools<82; python_version<'3.12'` cap + private `_legacy_numpy_rng_seed_scope` context manager (v0.31c1). Submodule-only surface — no root `pdelie` export. Periodic scalar 1D only. No new PDE, no new report schema, no WSINDy / noise-robustness / nonperiodic-discovery claim, no PySINDy 2.x code, no `SymmetryMethod` registry. `numpy>=1.24,<2` and Python-3.11-only matrix unchanged. Python 3.12+ downstream support deferred to `v0.31.1`. |

## Current Support Matrix

The compact public support matrix lives in:

- `../specs/SUPPORT_MATRIX.md`
- `../specs/support_matrix.v0_31.json` (current release)
- `../specs/support_matrix.v0_30.json`
- `../specs/support_matrix.v0_29.json` (previous release, retained for compatibility)

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
