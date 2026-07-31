# V0.36 Engineering Spec — Per-Sub-Phase Technical Breakdown

**Status:** living document. Sub-phases that have shipped record what was *measured*; sub-phases that have not record what is *planned*, with every numeric threshold left unset until its pilot runs.

**Baseline:** `c75f5ab` (v0.36a-α merged, PR #127). Package version remains `0.35.0` until the v0.36 release close.

**Structure per sub-phase:** branch → files → public surface → contracts → implementation notes → tests → exit gates → non-goals → risks.

---

## Standing assumptions

Every sub-phase inherits these. Each is enforced by a live test; none is renegotiated per sub-phase.

| Assumption | Enforced by |
|---|---|
| No root `pdelie` export — `pdelie.__all__` stays at 11 names | per-module test in every sub-milestone |
| No `discovery_task_result` schema change (22 top-level keys) | `tests/test_v0_31b1_discovery_task_runtime.py` |
| No `pdelie_weak_pde_library_diagnostic` drift beyond the frozen 27/28 conditional | `tests/test_v0_34c_column_normalized_weak_stlsq.py` |
| No cross-platform bit-exact assertion outside `exact_discrete` | `docs/design/CROSS_PLATFORM_PORTABILITY_CLASSES.md` + the portability lane |
| Hypothesis freeze → pilot → confirmatory freeze on every numerical work package | `docs/design/DESIGN_FREEZE_PROCESS.md` |

### Current measured state

| Metric | Value |
|---|---|
| Tests collected | **1953** |
| mypy | **147 errors in 29 files**, 106 files checked — delta zero since v0.35.0 |
| Portability lane | **11 of 1953** marked, budget 30 |
| Shipped v0.36 modules | `pdelie.artifact` (2 files), `pdelie.audit` (4 files) |

---

## Sub-phase index

| Sub-phase | Branch | Status |
|---|---|---|
| day-zero | `polish/v0.36-day-zero` | **merged** — PR #126 |
| v0.36a-α | `feat/v0.36a-alpha-paper-migration` | **merged** — PR #127 |
| v0.36b | `feat/v0.36b-design-contracts` | planned |
| v0.36a-β | `feat/v0.36a-beta-full-migration` | planned — after b |
| v0.36c | `feat/v0.36c-attainable-design` | planned — after b, parallel to β |
| v0.36d | `feat/v0.36d-sparse-recovery-assumptions` | planned — after b, parallel to c |
| v0.36e | `feat/v0.36e-deterministic-seed` | planned — independent |
| v0.36f | `release/v0.36.0rc1-testpypi` | planned — after all above |
| v0.36.0 | `release/v0.36.0` | planned — after rc1 validation |

**Merge discipline:** one substantive PR under active review at a time. Draft and stacked branches are fine; the merge queue is serial.

---

# day-zero — process, identity, and hygiene ✅ MERGED (#126)

## Files

**New:** `docs/design/DESIGN_FREEZE_PROCESS.md`, `docs/design/CROSS_PLATFORM_PORTABILITY_CLASSES.md`, `configs/mypy_baseline.v0_36.json`, `src/pdelie/artifact/semantic_hash.py`, `src/pdelie/artifact/__init__.py`, `.github/workflows/portability.yml`, `.github/pull_request_template.md`, and four guard tests (`test_semver_planning_monotonicity`, `test_portability_lane_budget`, `test_forbidden_language`, `test_v0_36_mypy_baseline`).

**Modified:** `ROADMAP.md`, `PLAN.md`, `API_STABILITY.md`, `CONTRIBUTING.md`, `pyproject.toml`, `docs/design/index.rst`, `tests/test_v0_33e_golden_numbers_regression_gate.py`.

> `src/pdelie/artifact/__init__.py` is listed under v0.36b in the original plan but landed here, deliberately: `semantic_hash` must exist before any consumer, so that consumers converge on one function rather than three.

## Public surface

`pdelie.artifact.semantic_hash(payload) -> str` — the only canonical-JSON hash. Implemented exactly as specified. Submodule-only.

## Contracts

- No alternative canonical-JSON implementation may exist anywhere in the codebase.
- The `portability` marker is registered in `pyproject.toml`; an unregistered marker silently selects nothing under `-m`.
- The mypy fingerprint rename rule: a renamed module inherits a fingerprint **iff** error code *and* line-agnostic message both match.

## Implementation notes — three corrections the specification required

**1. mypy pinned at `~=2.3.0`, not `~=1.11`.** The plan asked for both `mypy~=1.11` *and* a ratchet passing at 147. Measured on this tree:

| pin | resolves to | reports |
|---|---|---|
| `mypy~=2.3.0` (what CI resolves) | 2.3.0 | **147** |
| `mypy~=1.11` | **1.20.2** | **148** + an unused-section config warning |

Mutually exclusive. The `~=1.11` line was written against the pre-v0.35 state when the floor was `>=1.11`; the intent — pin the checker — is already met. Baseline records `"pin": "2.3.x"` with the rationale inline.

**2. Fifteen Ko sites, not eight — and they split.** Nine are active docs (renamed); six are **frozen shipped evidence** — four support matrices, `CHANGELOG.md`, the v0.35 readiness note — left as-shipped per the plan's own non-goal. The exit-gate grep scope (`src/`, `docs/planning/`, `API_STABILITY.md`) proved exactly consistent with that split.

**3. The forbidden-language scan had to be scoped, not repo-wide.** Every occurrence of the vocabulary in shipped code is a *disclaimer* or negative-valued key: `"It is not WSINDy and makes no noise-robustness claim"`, `"supports_wsindy": False`, the warning *name* `"noise_robustness_claimed"`, `wsindy_benchmark_claim` in deferred lists. A repo-wide grep flags the disclaimer as the violation and pushes the codebase toward silence. The plan's own wording — "new v0.36 source paths" — resolves it; `V0_36_SOURCE_PATHS` is the single point of control and grows per sub-milestone.

> **Open decision.** The §15 vocabulary was not supplied. If it includes **`oracle`**, shipped v0.35c violates it — `src/pdelie/design/row_selection.py` uses "SciPy oracle" five times, meaning a test reference implementation. Not added to the term list; a rename would be required first.

## Tests

Four new guard files. The semver guard found more than the defect it was written for.

## Exit gates — all passed

| Gate | Result |
|---|---|
| roadmap `v0.4` renamed; semver monotonicity green | PASS |
| zero Ko-sparse in `src/`, `docs/planning/`, `API_STABILITY.md` | PASS |
| `semantic_hash` importable, deterministic ×3 | PASS |
| portability lane on Linux + macOS, ≤30 marked | PASS — **green on both platforms first run** |
| mypy baseline authored; ratchet at 147 | PASS (147 = 147) |
| weak 27/28 conditional still green | PASS |
| no runtime API change beyond `semantic_hash` | PASS (`__all__` = 11) |

### Roadmap corrections the semver guard surfaced

| Row | Was | Now | Evidence |
|---|---|---|---|
| 2-D widening arc | `v0.4` | **`v0.40`** | `v0.4.0` is a shipped tag sorting *below* `0.35.0` |
| `v0.31` | Planned (next) | **Completed** | released as `v0.31.0`; a Completed row already existed |
| `v0.30.1` | Planned | **Completed** | shipped inside the v0.31.0 line; contracts now frozen invariants |
| `v0.31.1` | Planned | **Superseded by v0.32a** | `PYSINDY_2_MIGRATION_AUDIT.md`: *"IMPLEMENTED — v0.32a landed the migration"* |

## Non-goals — held

No runtime API change beyond `semantic_hash`; no shipped payload modified; no historical support-matrix rewrite.

## Risks — outcome

| Risk | Outcome |
|---|---|
| Grep false-positives on disclaimers | **Materialized.** Resolved by scoping to declared v0.36 paths. |
| Portability lane fails on macOS first run | **Did not materialize** — green on both platforms immediately. Pilot is 11 cases (the full golden set), not the 5 anticipated: `GOLDEN_PDE_NAMES` spans 5 periodic + 3 nonperiodic + 3 variable-coefficient. Marking 5 of 11 would leave six goldens unvalidated on macOS while claiming coverage. |

---

# v0.36a-α — paper-critical migration audit ✅ MERGED (#127)

## Files

**New:** `src/pdelie/audit/{__init__,stage_bundle,comparators,pipeline_migration}.py`, `scripts/{legacy_exporter,modern_exporter,run_alpha_migration}.py`, `configs/alpha_migration/{burgers,hard_heat}_experiment.json`, `tests/test_v0_36a_alpha_paper_migration.py`, `.github/workflows/alpha_migration.yml`, `docs/planning/V0_36A_ALPHA_MIGRATION_FREEZE.md`.

## Public surface

`compare_pipeline_stages(...)` → `summary_type = "pdelie_pipeline_migration_report"`; `write_stage_bundle` / `read_stage_bundle`; the comparator set; `PRINCIPAL_ANGLE_RESOLUTION_FLOOR_RAD`.

## Contracts

**Division of authority is enforced, not documented.** A comparator may assign only the four labels its array evidence supports. `intentional_contract_change`, `platform_specific_difference`, and `blocked_missing_legacy_dependency` are policy decisions requiring a justification — and an intentional contract change additionally requires a **linked release note**, because "we meant to do that" without a citation is indistinguishable from "we noticed it afterwards."

A policy override may only be applied to a comparator **failure**. It can explain a difference; it cannot manufacture agreement. `StagePolicy` rejects an override into a preserved label.

`tolerance_numeric` stages **raise** if their policy supplies no `rtol`/`atol`. A defaulted tolerance is what the freeze process forbids, so the code refuses one rather than inventing it.

**The two sides share a format, never a serializer.** `legacy_exporter.py` duplicates the bundle writer rather than importing `pdelie.audit` — asserted by test.

## Implementation notes — measured before the freeze was written

A hypothesis that assumes an unbuildable legacy is worthless, so the legacy environment was probed first. **Two planning assumptions were wrong.**

**The planned legacy toolchain does not work.** The mitigation pinned `setuptools==65.5.0`. v0.22.0's own `[build-system]` declares `requires = ["setuptools>=68"]`, so 65.5.0 is *below* its floor and the build aborts with `Missing dependencies: setuptools>=68`. Builds with `setuptools==68.2.2` + `wheel==0.38.4`. **The Docker fallback is not required.**

**A bare wheel install yields a pdelie with no discovery path.** `pysindy` and `scikit-learn` are in v0.22.0's `[downstream]` extra, not core, both marked `python_version < '3.12'`. The legacy venv must be CPython 3.11 *and* install `pdelie[downstream]`. Resolved: pdelie 0.22.0 / numpy 1.26.4 / pysindy 1.7.5 / scikit-learn 1.2.2 on 3.11.14.

**The generated field is bit-identical across the version gap.** `max|Δ| = 0.000e+00` on a heat field at `seed=3120`, Python 3.11 + numpy 1.26 versus 3.12 + numpy 2.5. Stage 1 may be reclassifiable from `qualitative_invariant` to `exact_discrete` — a decision for the confirmatory freeze. `u_xx` differs by `1.245e-14` relative.

**The first `intentional_contract_change` is identified.** `DerivativeBatch` is contract-identical across the gap — the same six fields — but the entry point moved from `compute_spectral_fd_derivatives` to `compute_derivatives`, and `config` gained `backend_selected_by_boundary_condition` and `backend_selection_reason` from v0.30d dispatch. Requires a linked release note before stage 7 can be labelled.

## Tests

66 contract tests. Coverage: `stage_bundle` 99%, `pipeline_migration` 98%, `comparators` 97%. The audit itself runs via `workflow_dispatch`, never in PR CI.

## Exit gates

| Gate | Status |
|---|---|
| A-α-0 provenance completeness | **enforced at write time** — `source_dirty` is a required `bool`; "unknown" is not an answer |
| A-α-1 …-4 | **pending the pilot** — require the 16-stage run |
| A-α-5 legacy artifacts untouched | orchestrator checks out the tag detached and never writes to it |
| A-α-6 `grep private_paper_repo/` | **NOT EVALUABLE HERE** — that repository is not present in or reachable from this one. Recorded as such rather than silently passed. |

## Non-goals — held

No full pipeline coverage (β); no public paper-specific API; no claim about β stages; no global artifact store.

## Risks — outcome

| Risk | Outcome |
|---|---|
| v0.22 unbuildable | **Did not materialize**, but the planned pin was wrong; corrected above |
| Legacy PySINDy ambiguity | **Deferred to the pilot** — the freeze's invalidation clause covers it |
| Cross-BLAS drift on the Gram matrix | **Open** — candidate `rtol=1e-9, atol=1e-12` carries no authority until measured |

> **Correction, recorded.** A test asserted principal angles equal `0.0` to `abs=1e-12`; it passed on macOS and failed on Linux at `1.4901161e-08`. Not a platform defect: `arccos` is ill-conditioned near 1, so identical subspaces report an angle of order `√eps`. **This was the fourth "measured on one platform, recorded as universal" in this repo's history — occurring in the PR that adds the machinery to catch it.** Fixed as a usability issue: `PRINCIPAL_ANGLE_RESOLUTION_FLOOR_RAD` is exported and documented with both measured values, since a caller would naturally reach for `1e-12`.

## Remaining α work

The pilot has **not** run. Fourteen of sixteen exporter stages are unwritten, because their tolerances come from the pilot. Sequence: run `workflow_dispatch` → record spreads → write the confirmatory freeze → implement the remaining stages against the frozen tolerances.

---

# v0.36b — contracts 📋 PLANNED

**Branch:** `feat/v0.36b-design-contracts` · **Timeline:** 3 weeks solo, 2 weeks team

## Files

**New:** `artifact/refs.py`, `artifact/store.py`, `observation/{__init__,operator_spec}.py`, `differentiation/{__init__,policy_spec}.py`, `actions/{__init__,action_ref,problem_action_spec,interaction_rules}.py`, `design/budget.py`, `design/lineage.py`, plus eight test files.

> `artifact/__init__.py` already exists from day-zero. v0.36b **extends** it rather than creating it.

## Public surface

`pdelie.artifact` — `ArtifactRef`, `RunManifest`, `StageRecord`, `JSONValue`, `ArtifactStore` (Protocol), `MemoryArtifactStore`, `ContentAddressedFileStore`. `pdelie.observation` — `ObservationOperatorSpec`. `pdelie.differentiation` — `DifferentiationPolicySpec`. `pdelie.actions` — `ActionRef`, `ProblemActionSpec`, `validate_action_spec`. `pdelie.design` — `DesignBudget`, `DesignRowLineage`, `compute_semantic_design_hash`, `compute_numeric_design_hash`. All submodule-only.

## Contracts

- `compute_semantic_design_hash` routes through `pdelie.artifact.semantic_hash`. No second canonical-JSON path.
- `ArtifactRef.artifact_id` **is** the identity — frozen dataclasses with `Mapping` fields are unhashable, so identity is a canonical string, not `__hash__`.
- `ContentAddressedFileStore` writes under a per-run root and **never** a global directory.
- `budget_unit` outside the seven-value vocabulary raises; unknown strings are never silently accepted.

## Implementation notes

Semantic hash is **order-sensitive by design** — row order carries meaning, so a reordered lineage must hash differently. Numeric hash is byte-level over `matrix.tobytes()`, so a column permutation also differs.

## Tests

Per-rule failing example for every interaction rule; **20+ canonical legal specs pass**; store protocol conformance; same content twice → same `artifact_id`, no duplicate file.

## Exit gates

- `put_bytes(content).sha256 == sha256(content).hexdigest()`
- `sum(m for _, m in histogram) == budget.budget_value` when `budget_unit == "rows"`
- every illegal action combination rejects with its expected message
- `hasattr(pdelie, "ArtifactRef") is False` and equivalents

## Non-goals

No cross-process artifact sharing (β); no global store; no MLflow/DVC/W&B; no model serialization; no caching layer.

## Risks

| Risk | Mitigation |
|---|---|
| Rule engine incomplete | Freeze the rule **count** as an exit gate; a new rule requires a PR that grows the count with a test |
| Frozen dataclasses unhashable | `identity()` returning a canonical string; `ArtifactRef.artifact_id` is the key material |
| File store accumulates disk state | `cleanup()`; per-run directory deleted by the orchestrator; documented in `docs/design/ARTIFACT_STORAGE.md` |

---

# v0.36a-β — full migration audit 📋 PLANNED

**Branch:** `feat/v0.36a-beta-full-migration` · **After:** v0.36b · **Timeline:** 4-5 weeks solo, 2-3 weeks team

## Files

**New:** `audit/full_migration_scope.py`, `configs/full_migration/full_migration_scope.json`, `tests/test_v0_36a_beta_full_migration.py`, `.github/workflows/beta_migration.yml`. **Modified:** all three scripts, generalized to accept a scope config.

## Scope

5 PDEs (heat, Burgers, advection-diffusion, reaction-diffusion, KdV periodic-only) × applicable boundaries × weak default (27-key) and normalized (28-key) paths, plus candidate/downstream workflows and v0.35c row-selection diagnostics.

## Contracts

Every stage bundle carries `ArtifactRef` + `StageRecord`; every design carries `DesignRowLineage`; observation and derivative stages use the v0.36b spec shapes.

## Exit gates

Every artifact traceable through `parent_stage_ids`; no `unexplained_regression` remains; every intentional change linked to a release note; all portable claims pass Linux **and** macOS; report reproducible from built wheels; α conclusions still valid under generalized tooling.

## Non-goals

No new PDE coverage (KS stays blocked); no new residual evaluator; no new symmetry method.

## Risks

| Risk | Mitigation |
|---|---|
| KdV audit too expensive | Periodic-only; nonperiodic KdV stays deferred as it always has been |
| Weak-normalized path has no v0.22 counterpart | Label `intentional_contract_change` against the v0.34c release notes; do **not** attempt a legacy comparison |

---

# v0.36c — attainable-design comparison 📋 PLANNED

**Branch:** `feat/v0.36c-attainable-design` · **After:** v0.36b, parallel to β · **Timeline:** 4-5 weeks solo, 2-3 weeks team

## Files

**New:** `design/attainability.py`, `design/comparators.py`, `design/candidate_record.py`, `design/statistics.py`, plus four test files.

## Public surface

`attainability_report(...)` → `summary_type = "pdelie_attainable_design_comparison"`; `DesignCandidateRecord`; eight comparators; `paired_bootstrap_interval`.

## Contracts

**All six `information_access` flags are mandatory.** A comparator with any hidden privileged access is invalid, and a missing key raises rather than defaulting to `False`.

**`oracle_qualification` replaces the bare word "oracle"** with four explicit values: `attainable_policy`, `full_design_matrix_heuristic`, `true_support_diagnostic_oracle`, `exact_small_problem_solver`. Regex-tested against emitted JSON.

## Implementation notes

> **Reuse, do not reimplement.** v0.35c already ships `qr_pivot_row_selection`, `leverage_row_selection`, and `d_optimal_exchange_row_selection` in `pdelie/design/row_selection.py`, with measured determinism properties. The three corresponding v0.36c comparators must **wrap** them. Reimplementing would fork the tie-break policy and the LINPACK norm-downdate safeguard — the latter measured as load-bearing on 8 of 12 adversarial matrices.
>
> Two v0.35c measurements carry directly into the comparator declarations:
> - `leverage_row_selection` beat only **8%** of 40 random draws on the canonical weak matrix where the other two beat 100%. It is not a conditioning method, and its record must say so.
> - `d_optimal_exchange_row_selection` reached **4–5 distinct optima** across five random starts. Its `seed` and starting set are part of its identity.

## Tests

Each of eight comparators produces a valid record; missing access key raises; `_budget_equal` catches synthetic mismatches; fixed-seed bootstrap reproduces byte-identical intervals; `full_field_design` declares `requires_full_domain=True`; `exact_enumeration_comparator` returns `None` when `n_rows > 20`.

## Exit gates

`all(len(c.information_access) >= 6 ...)`; every record passes `_validate_information_access`; incomparable pairs either empty or fully populated; `pair["seed_ids_A"] == pair["seed_ids_B"]`; `failed_run_count == sum(1 for m in metrics if m is None)`.

## Non-goals

No new symmetry method; **no dependency on the private v0.35b point-symmetry registry**; no global-optimality claim unless exact enumeration ran; no "oracle beats us therefore we're bad" narrative.

## Risks

| Risk | Mitigation |
|---|---|
| D-optimal non-determinism | Seed-fixed init, deterministic tie-break, `max_iter` cap, non-convergence warning — all already implemented in v0.35c |
| Bootstrap correlation from PDE dynamics | Trajectory- or seed-level resampling only; row bootstrap refused with a typed error |
| Access declarations drift | Class-level constant plus a test asserting the declaration matches the implementation |

---

# v0.36d — sparse-recovery assumptions 📋 PLANNED

**Branch:** `feat/v0.36d-sparse-recovery-assumptions` · **After:** v0.36b, parallel to c · **Timeline:** 2-3 weeks solo, 1.5-2 weeks team

## Files

**New:** `diagnostics/sparse_recovery.py`, two test files, `docs/design/SPARSE_RECOVERY_ASSUMPTION_REPORT.md`.

## Public surface

`sparse_recovery_assumption_report(...)` and `empirical_support_stability_report(...)`, emitting two new `summary_type` values.

## Contracts

**Seven required statuses**, none of which is a generic recovery claim. The forbidden vocabulary — `recoverable`, `not_recoverable`, `recovery_guaranteed`, `recovery_impossible`, `ell1_recoverable`, `ell1_not_recoverable` — must appear in neither source nor emitted JSON. Theorem-specific names only.

**No pseudoinverse fallback.** `np.linalg.solve` raising `LinAlgError` on a rank-deficient support is caught and returned as `None` with `undefined_singular_support`. Substituting a minimum-norm solution is exactly the v0.35a defect: it produced `0.4956551696` — finite, plausible, sub-threshold — from a system that determines nothing.

**Row-level resampling is refused** with a typed error; it would break the correlation structure of PDE-derived design matrices.

## Implementation notes

> **The restricted-eigenvalue rename is already half-done.** v0.35a emits `restricted_eigenvalue_definition = "support_restricted_min_gram_eigenvalue_over_n"` and its docstring states plainly that this is *not* the cone-constrained Bickel–Ritov–Tsybakov constant. v0.36d's `active_support_min_singular_value` should be introduced as an explicitly-named alternative in the new report, with the v0.35a function kept importable and unchanged. The distinction is already carried in the payload; do not re-litigate it, and do not silently redefine the shipped name.

Signed and uniform irrepresentability are both computed per candidate support. When `sign_patterns` is `None`, the status is `sign_pattern_unavailable` and **uniform is the only actionable statistic**.

## Tests

Hand-computed references on identity, orthogonal, and 4×2 correlated matrices to `rtol=1e-12`; signed and uniform differ on at least one fixture where the sign matters; singular support returns `undefined_singular_support`; row bootstrap refused; trajectory bootstrap deterministic under a fixed seed.

## Exit gates

Hand-computed references pass; signed ≠ uniform somewhere; singular support handled; no generic recovery claim in source or JSON; empirical stability separate from the theoretical report; no row bootstrap ever succeeds; canonical findings reproduce under the confirmatory freeze.

## Non-goals

No global ℓ1 recovery claim; no p-value from stability without predeclared multiple-testing correction; no dependency on a specific external Lasso implementation.

## Risks

| Risk | Mitigation |
|---|---|
| `sign_patterns=None` corner case | `sign_pattern_unavailable` status; uniform reported regardless |
| `G_SS` solve instability | If `cond(G_SS) > 1e12`, return `None` with `poorly_conditioned_active_support` |

---

# v0.36e — deterministic weak-diagnostic seed 📋 PLANNED

**Branch:** `feat/v0.36e-deterministic-seed` · **Independent** · **Timeline:** 4-6 days solo

## Files

**Modified:** `tasks/weak_pde_library.py`, `tests/test_v0_31b2_weak_pde_library_diagnostic.py`. **New:** `tests/test_v0_36e_deterministic_seed.py`.

## Contracts

Three-state `seed`: omitted (`_UNSET`) → `FutureWarning` + legacy nondeterminism; `None` → explicit opt-in, no warning; `int` → deterministic. `bool` and `str` raise.

**`FutureWarning`, not `DeprecationWarning`** — the latter is hidden by default outside `__main__`, which would make the transition invisible to exactly the users who need to see it.

**The 27/28 conditional must not drift.** `seed_provenance` lives **inside** the existing provenance block; no top-level key is added. Verified: default 27, `column_normalize=True` 28, across all three seed states.

## Implementation notes

This retires the last known nondeterministic default. The v0.34c work added the `seed` kwarg but deliberately left the default alone to avoid changing a shipped surface — correct then, wrong once artifacts are published, because new users hit the default first.

## Tests

Exactly one `FutureWarning` on omission (not zero, not many); category assertion; `stacklevel=2` resolves to the caller not a pdelie frame; `seed=None` silent; identical seeds → identical column-scale ratios; provenance block has all seven keys; warning visible from a non-`__main__` module.

## Non-goals

No change to any other function's seed semantics; no hard flip (v0.37); no retroactive warning.

## Risks

| Risk | Mitigation |
|---|---|
| `-Werror` builds break | Document in CHANGELOG; the warning message names both exact fixes |
| `stacklevel=2` wrong for wrapped callers | Test asserts the warning resolves to the caller's line |

---

# v0.36f — TestPyPI 0.36.0rc1 📋 PLANNED

**Branch:** `release/v0.36.0rc1-testpypi` · **After:** all above · **Timeline:** 1 week

## Files

**New:** `.github/workflows/publish-testpypi.yml`, `tests/test_v0_36f_testpypi_postpublish_smoke.py`, PUBLISHING.md TestPyPI section. **Modified:** `pyproject.toml` → `0.36.0rc1`, `docs/conf.py`.

## Contracts

**OIDC trusted publishing — zero API tokens in repo secrets.** Two-job pattern: `build` hashes artifacts into `SHA256SUMS`; `publish-testpypi` downloads the exact artifact and verifies the hash before upload. `id-token: write` is scoped to the publish job only. **No `skip-existing`** — versions are immutable; a defect means rc2.

> The workflow in the plan uses floating action tags (`actions/checkout@v4`). This repository SHA-pins every action. Match the existing convention.

## Implementation notes

All install validation happens **outside the source checkout** — a smoke test run from the repo root can import the working tree instead of the installed wheel and prove nothing.

## Exit gates

`test.pypi.org/project/pdelie/0.36.0rc1/` accessible; all 6 install configurations pass `pip check` on a fresh py3.12 venv outside the checkout; CLI smokes return expected JSON; artifact hash unchanged between build and publish; zero tokens; no production PyPI upload.

## Non-goals

No production PyPI upload; no `skip-existing`.

## Risks

| Risk | Mitigation |
|---|---|
| Trusted-publisher not registered | One-time setup documented in PUBLISHING.md; register **before** the first run |
| rc1 finds a defect | Bump to rc2; never overwrite rc1 |

---

# v0.36.0 — release close 📋 PLANNED

**Branch:** `release/v0.36.0` · **Timeline:** 5-7 days solo

## Files

**New:** `docs/releases/V0_36_RELEASE_READINESS.md`, `docs/specs/support_matrix.v0_36.json`. **Modified:** version bump, `docs/conf.py`, `CHANGELOG.md`, release-gate manifest and job rename `v0_35_0` → `v0_36_0`, doc alignment across PLAN/ROADMAP/API_STABILITY, existing release-gate tests.

## Contracts

Decision label `v0_36_0_contracts_migration_attainability_and_sparse_recovery_hardening`. Forbidden root attributes extended to every v0.36 addition. Support matrix records four new `summary_type` values and eight new public submodules, plus a deferred block naming Ko (v0.39) and the 2-D contract (v0.40).

> The README/release guard tightened in v0.35 day-0 now asserts **both** the prose release line and every `@vX.Y.Z` pip pin, derived from `pyproject`. All four README references must move together.
>
> The stale-job-name guard must gain `v0_35_0-release-gate:` when the job is renamed, following the pattern established at each prior close.

## Preflight

Full suite on 3.12 **and** 3.13; ruff delta 0; **no new mypy fingerprint** against `configs/mypy_baseline.v0_36.json`; coverage ≥80% blocking (investigate below 82%); sphinx `-W` clean; sdist + wheel build; core-only and all-extras `pip check` green; CLI smokes; portability lane green on both platforms; strict-JSON round-trip for every new payload; `git diff --check` clean.

> **Test-count target.** The plan projects ~1930 from a stated v0.35 baseline of 1727. The actual v0.35.0 baseline is **1856 passed / 2 skipped**, and the tree already collects **1953** with day-zero and α merged. Expect roughly **2150–2250** at close. The 1727 figure predates the v0.33–v0.35 arcs.

## Non-goals

No production PyPI upload; no Ko (v0.39); no 2-D widening (v0.40); no LieGG; no new PDE.

## Risks

| Risk | Mitigation |
|---|---|
| mypy fingerprint drift across the arc | Run mypy after each merge; refresh the baseline in the **same** PR that changes the count |
| Coverage below 80% from new modules | Per-sub-milestone acceptance requires ≥85% on new modules. Shipped so far: `artifact` and `audit` at **97–99%** |

---

## Cross-cutting infrastructure

```text
day-zero (SHIPPED)   pdelie.artifact.semantic_hash — the one canonical hash
                     portability marker + Linux/macOS lane (green, 11/30 used)
                     mypy fingerprint baseline (147, pinned to 2.3.x)
                     freeze process + portability class taxonomy

v0.36a-α (SHIPPED)   stage-bundle interchange (no pickle, content-hashed)
                     comparator set + seven-label vocabulary
                     policy/comparator authority split

v0.36b               ArtifactRef / RunManifest / StageRecord
                     Memory + ContentAddressed stores
                     ObservationOperatorSpec, DifferentiationPolicySpec
                     ProblemActionSpec + rule engine
                     DesignBudget, DesignRowLineage

v0.36c uses          DesignCandidateRecord, ArtifactStore, DesignBudget,
                     DesignRowLineage — and WRAPS v0.35c row selection
v0.36d uses          ArtifactRef; extends v0.35a diagnostics vocabulary
v0.36a-β uses        every v0.36b contract
v0.36f uses          pyproject metadata verified at day-zero
v0.36.0 uses         everything
```

## Open decisions

1. **§15 forbidden vocabulary** was never supplied. If it includes `oracle`, shipped v0.35c code violates it and needs a rename first.
2. **Exit gate A-α-6** references `private_paper_repo/`, unreachable from this repository. Either supply it, or restate the gate as out-of-scope here.
3. **The α pilot has not run.** Fourteen exporter stages and every `tolerance_numeric` threshold are blocked on it — by design, not by oversight.
