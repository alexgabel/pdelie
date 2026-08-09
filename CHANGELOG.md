# Changelog

## 0.38.0rc1

Release candidate. **No library behaviour changed since `0.38.0b1`** — every
commit is gate, harness, or record.

`b1` withheld the RC designation for one stated reason: Gate F had not passed,
and no v0.38 code had ever been replayed on a second platform. **Gate F closed**
on run `31328966332` — three runner cells, 229 gate rows each, worst
cross-platform scaled difference `4.168e-10` against a derived `1e-8` bound, and
bitwise-identical (325/325) across a CPython patch bump. From here, defect
corrections only.

It took three attempts and the two failures are recorded, not hidden:
Appendix B (a runner cell that does not exist) and **Appendix C** — a gate that
passed *vacuously*, because ten out-of-scope `d = 4` rows carried
`derivative_order: null` and F-4 read `null` as in scope. F-4 could not have
failed; the rows it existed to exclude were invisible to it.

### Fixed

- Row semantics now originate in a typed `ReplayRowSpec`. An order-parameterised
  row with no order **cannot be constructed**, not merely cannot be emitted. The
  row key is generated from the spec and never parsed back.
- New criteria **F-3a** (the gate/exploratory partition equals the frozen
  partition) and **F-4a** (a `null` order is in scope only where a *declared*
  order-free family permits it). F-3 now asserts **set equality** against a
  reviewed manifest rather than a count — the broken population had the correct
  total (286) throughout.
- Bitwise comparison runs before and independently of floor classification. The
  previous ordering skipped floor comparisons before counting them, so F-6's
  denominator excluded precisely the small-magnitude rows a libm change would
  perturb first.
- `scripts/release_gate_local.sh` pins its interpreter against `requires-python`
  and aborts with exit 3 **before any sub-gate runs**. Previously, running it
  where bare `python` was 3.11 reported one environment fault as three code
  faults.
- The CI release-gate job is renamed to the stable `release-gate`. The versioned
  name deadlocked branch protection at every cut: GitHub matches required
  contexts by exact string, so renaming the job left the required check unable
  to report, with `enforce_admins: true` allowing no override.

### Added

- `scripts/audit_replay_population.py` (**F-11**) — re-derives the scope rules
  independently and imports neither the generator nor the comparator, so an
  error common to both cannot cancel itself out. Runs on the runner, before
  upload.
- `configs/gate_f_expected_rows.json` — the frozen, reviewed row population.
- `docs/evidence/v0_38_gate_f/` — the three artifacts verbatim plus the
  comparison, because GitHub expires action artifacts. The verdict reproduces
  from those files alone.
- Roadmap rows for `v0.38` and `v0.41`, both previously absent — the arc being
  released was missing from planning, and two v0.38 deferrals pointed at a
  release with no row.
- `release/*` branch ruleset, and `required_conversation_resolution`, which the
  policy document specified and the repository did not have.

### Unchanged

- **No tolerance** was widened, narrowed, or reinterpreted. `1e-8` and `0.0`
  stand exactly as derived.
- Tags `v0.38.0a1` and `v0.38.0b1` remain published and unmoved.
- Appendices A, B and C are append-only and were **not** revised when D
  succeeded.
- `discovery_task_result` keeps its 22-key schema, frozen since v0.30.1.
- Git-tag-only; TestPyPI/PyPI publication remains deferred to `v1.0`.

## 0.38.0b1

Feature-complete for v0.38. Adds the irregular-grid layer (v0.38a-d) on top of
the a1 action-semantics work, freezes the public API from a measured inventory,
and records Gates A-F.

**Still not a release candidate.** Gate F (cross-platform replay) is not met: no
v0.38 code has been replayed. `rc1` is cut only after it is.

### Added since a1

- **v0.38a** row masks identified by `DesignRowLineage`, with derived
  `full_field_derivatives_available`.
- **v0.38b** Fornberg non-uniform finite differences, with a piloted G-5 ratio
  (`10.0`) and stencil cap (`13`), and four of v0.38a's five exclusion-reason
  producers.
- **v0.38c** irregular weak bridge: weak rows are windows in their own identity
  namespace, quadrature narrowed to two validated rules.
- **v0.38d** derivative error against a stated reference, with signal-versus-floor
  regimes and median/IQR timing.

### Public surface

`pdelie.__all__` unchanged at 11. 11 new modules carrying 61 names; 10 promoted
to package exports; 9 modules deliberately unexported, each with a recorded
reason. See [`public_api_freeze.v0_38.json`](docs/specs/public_api_freeze.v0_38.json).

## 0.38.0a1

Action-semantics hardening, and one breaking change that keeps a two-release-old
promise. See [`docs/releases/V0_38_SEED_MIGRATION.md`](docs/releases/V0_38_SEED_MIGRATION.md).

### Breaking

- **`inspect_pysindy_weak_pde_library` requires an explicit integer `seed`.**
  Keyword-only, no default. Omission is a `TypeError` from the signature;
  `seed=None` — previously "opt into nondeterminism" — raises
  `ScopeValidationError`; `bool` is refused despite being an `int` subclass,
  since `seed=True` would silently seed with `1`.

  **There is no undocumented compatibility default.** Retaining one would
  preserve exactly the nondeterminism this removes.

  Announced at v0.36e naming v0.37, deferred once at v0.37 because an unscoped
  breaking change during a release close is worse than a deferred one, and kept
  here. The `FutureWarning` is removed — it now describes a change already made.

  Migration: pass `seed=<int>`. The payload shape is unchanged; the frozen 27/28
  conditional schema and all seven `seed_provenance` keys are preserved, with
  `seed_was_omitted` and `nondeterministic_requested` now constant `False`.

### Fixed

- **A parameter action rescaled every numeric parameter.** `ActionRef` carried no
  target, so a `scalar_rescale` meant for the viscosity also tripled the
  advection speed on any problem with more than one parameter. No v0.37c case
  could observe it — each declares exactly one numeric parameter, and on a
  one-element population "rescale all" and "rescale the declared one" are the
  same function. Ambiguity is now refused rather than resolved by convention;
  `target_parameters` names the target explicitly.

- **The benchmark declared the wrong equation form.** `equation_form` was the
  literal `"nonconservative"` on every case while the evaluators dispatched from
  provenance and took the **conservative** branch on every variable-coefficient
  case. The forms differ by exactly `nu' * u_x`, which measures `1.035x` the
  residual magnitude on the sinusoidal profile. Now derived from provenance.
  **No measured number changed** — all 125 released measurements are bitwise
  identical.

### Added

- Two coefficient-array identities, `storage_representation_identity` and
  `scientific_identity`, as separate helpers with no shared implementation.
- `ArtifactResolver`, injected explicitly; no module-level registry.
- `pdelie_action_coaction_consistency`, a 16-key payload reporting whether a
  bundle's declaration determines what an executor does.
- Benchmark cases **C-7** and **C-8**, the first with two numeric parameters.

## 0.37.1

Hotfix. Repairs a semantic mismatch in benchmark case C-5, enforces parameter/coefficient ownership, and reruns the confirmatory freeze on a fresh seed packet. See [`docs/releases/V0_37_C5_ERRATUM.md`](docs/releases/V0_37_C5_ERRATUM.md).

**v0.37.0 did not test parameter-only obstruction correctly.** C-5's bundle declared a `scalar_rescale` on the *parameter*; the runner never read it, and rescaled the *state* instead. `execute_bundle` computed the rescaled parameter correctly into `transformed_parameters` and the benchmark discarded it.

The arithmetic was right. The v0.37.0 record states C-5's derivation reproduced the measurement at ratio `1.000000`, and it did — for a state rescale, which is not what C-5 declared.

Every v0.37 gate checked that a *declared* thing was coherent. None checked that the declared thing was the thing *executed*, which is why this survived a hypothesis freeze, three pilots, a confirmatory freeze, a release close and a tag.

### Fixed

- **C-5 now consumes the action it declares.** The runner reads `execution.transformed_parameters["nu_baseline"]` and builds an evaluator from the rescaled parameter, leaving the state untouched. Its derivation is now `|c−1|·ν·‖u_xx‖∞`, exact at ratio `1.000000` on every seed.
- **A name may not be owned twice.** `ProblemInstanceSpec` refuses a key appearing in both `parameters` and `coefficient_fields`. C-5 had `nu` in both — two declarations of one quantity with no rule about which an executor should read. The scalar is now `nu_baseline`.

### Changed

- **C-5's declared operator family: `scalar_multiplier` → `identity`.** The claim under test is that rescaling `ν` leaves the residual unchanged; measurement violates it. **No benchmark case now exercises `scalar_multiplier` end to end** — a coverage loss recorded rather than hidden.
- **Confirmatory freeze v2** on seeds `13, 17, 19, 23, 29`, disjoint from v1's. All five cases rerun, not just C-5: a confirmatory freeze is a paired comparison at a fixed seed packet, and mixing runs would make the margins incomparable. v1 is retained unedited and invalidated for C-5 only.

### Added

- **`tests/test_benchmark_action_semantics_guard.py`** — the gate the v0.37 arc lacked. Scans benchmark code for transformations applied outside the declared action path. Written from the pattern rather than this defect, it flagged all three of C-5's constructs on first run.
- **An append-only guard on the pilot report.** The first 419 lines are pinned by SHA-256, so runs 1–3 — two of which blocked — cannot be quietly rewritten to show only the passing run.


## 0.37.0

Release-close for the v0.37 arc: five sub-milestones consolidated into a single tag. Submodule-only — no root `pdelie` export added. No new PDE, and no change to any existing payload shape.

Release decision: `v0_37_0_parameter_equivariant_actions_and_admissibility_benchmark`.

**Git-tag-only.** Publication remains deferred to `v1.0`; the path hardened in v0.36f has still never been run.

**Process note.** v0.37c ran three pilots. Two blocked, and each caught a specification defect — an interface mismatch between two documents (bounds derived in one norm, measured in another) and a self-contradictory case (a nonperiodic profile on a domain declared periodic). Neither was a code bug, and neither was reachable by unit tests generated from the same defective specification — which is the trap, not a general claim about testing. Both were reachable by a manufactured-solution check, a symbolic expansion, a metamorphic property, or an execution-vs-declaration audit. Written up in `docs/releases/V0_37_RELEASE_READINESS.md`.

### Added

- **`pdelie.actions` contracts (v0.37a).** `ProblemInstanceSpec`, `CoefficientFieldRef`, `CoordinateFieldAction`, `ProblemActionBundle`, `ExpectedResidualRelation`, `ExpectedResidualOperator`, `ActionExecutionConfig`, and `validate_action_bundle` with a twelve-rule table. Five independent relation axes rather than one collapsed enum, because boundary preservation is orthogonal to equation equivalence. `CoefficientFieldRef.treatment` generalises the shipped v0.33d `nu_treatment_policy` tag from `nu`-specific to per-field, keeping `fixed_background` verbatim.
- **`pdelie.actions.execute` (v0.37b).** Six runtime paths P-1…P-6. The only implemented backend is `exact_grid_shift`, a whole-cell periodic translation that permutes samples and adds no interpolation error; a fractional shift is refused rather than rounded, because rounding would measure a different action than the one declared.
- **`pdelie.actions.commutation_report` (v0.37b).** New `summary_type` `pdelie_problem_action_residual_relation`. Three independent status fields — expected case, observed status, benchmark outcome — so a deliberate obstruction that fails reads as a benchmark success without contradiction. `scientific_payload` is hashed; `execution_metadata` carries runtime and is not.
- **`pdelie.actions.diagnostic_fit` (v0.37b).** Advisory by construction: no status field, no boolean verdict, no threshold. The analytical decision is computed first and alone.
- **`pdelie.benchmarks` (v0.37c).** A five-case admissibility benchmark with four coefficient profiles, disjoint pilot and confirmatory α grids, and a signed confirmatory freeze.
- **`pdelie.downstream` (v0.37d).** New `summary_type` `pdelie_downstream_task_with_action_bundle`. Seven branches; the four invalid ones block **before** discovery runs, measured by a sentinel task that raises on call and is asserted never to fire.

### Changed

- **Coverage floor 80 → 85**, against a measured 86.33%. A hygiene test pinning `fail_under == 80` exactly was changed to `>= 80`: an equality pin makes every ratchet read as a regression, inverting the invariant it protects.
- **Forbidden-language table 4 → 11 terms.** `wsindy_bridge` is recorded in `SUBSUMED_TERMS` because substring matching means it adds no detection — a redundant entry that looks load-bearing is worse than an absent one.
- **`execute_state_action` refuses non-periodic domains.** `numpy.roll` wraps, which is correct for a periodic domain and silently wrong otherwise.

### Fixed

- **A deprecation notice that promised something this release does not deliver.** The weak diagnostic's `FutureWarning` said "v0.37 will require an explicit integer seed". v0.37a's freeze scoped that transition out, so v0.37 ships without it and the notice was false. It now names v0.38, and a test asserts the version a deprecation names is always still in the future — a notice naming an already-released version is worse than no notice.
- **A schema-key convention I had mis-measured.** The v0.37 constraints doc claimed the repository had no convention, citing 37 vs 36 across all of `src/`. Re-measured over payloads that actually declare a `summary_type`, it is 34 to 5 in favour of `summary_schema_version`. There is a convention; the five exceptions are v0.36 modules that broke it. They are not migrated — changing an emitted key is a shape change for a cosmetic gain — and both new v0.37 types follow it.


## 0.36.0

Release-close for the v0.36 arc: eight sub-milestones consolidated into a single tag per the solo-dev consolidation policy. Submodule-only surface — no root `pdelie` export added. No new PDE, no change to any existing payload shape.

Release decision: `v0_36_0_migration_audit_artifact_lineage_and_design_comparison`.

**Git-tag-only.** An earlier plan targeted TestPyPI at v0.36; that was superseded and publication stays deferred to `v1.0`. v0.36f built and hardened the publish path without exercising it.

**Process note.** Three findings outlived the release, and they are the substantive contribution beyond feature delivery — the legacy PySINDy STLSQ conditioning result, the five-instance tolerance-calibration pattern now encoded as policy in `CONTRIBUTING.md`, and the three-layer structure of coefficient handling whose middle layer v0.36 completed. All three are written up in `docs/releases/V0_36_RELEASE_READINESS.md`.

### Added

- **`pdelie.audit` (v0.36a).** A legacy-vs-modern pipeline migration audit against the `v0.22.0` tag. Seven-label vocabulary with a comparator/policy authority split: comparators assign only evidence-backed labels, and `intentional_contract_change` additionally requires a linked release note. No-pickle interchange (`.npy` + strict JSON, `allow_nan=False`). `full_migration_scope` enumerates all 100 (PDE × boundary × path) combinations against what v0.22.0 can actually produce — 10 auditable, 90 blocked, each blocked one naming its reason and the release that introduced the gap.
- **`pdelie.artifact` (v0.36b).** Content-addressed artifact identity via `semantic_hash` as the single canonical hash. Per-run stores, never global.
- **`pdelie.observation`, `pdelie.differentiation` (v0.36b).** Observation-operator and differentiation-policy specifications.
- **`pdelie.actions` (v0.36b).** Declarative problem actions: `ProblemActionSpec` pairs each claim with the action implementing it, and seven interaction rules refuse self-contradictory specs. Five independent relation axes — equation, parameter, coefficient, domain, boundary — because boundary preservation is orthogonal to equation equivalence and one collapsed enum cannot say which combination a transformation is.
- **`pdelie.design` (v0.36c, v0.36d).** Budget-aware design comparison with six mandatory information-access flags (a missing flag raises rather than defaulting to `False`), four named method classes replacing the bare word "oracle", paired per-seed bootstrap intervals, and sparse-recovery assumption reporting. Row-level resampling is refused: rows of a PDE-derived design matrix are adjacent samples of a continuous field.
- **`docs/planning/V0_37_BINDING_DESIGN_CONSTRAINTS.md`.** Six design constraints pre-registered before v0.37 implementation, with a status vocabulary (`satisfied_in_v0_36` / `binds_absent_design` / `resolves_in_v0_37a`) and a named resolution vehicle. Machine-checked: 25 tests assert every drift-prone claim it makes about the code.

### Changed

- **`inspect_pysindy_weak_pde_library` seed semantics (v0.36e).** Three states: explicit `int`, explicit `None`, and omitted. Omission emits a `FutureWarning`; an explicit seed will be required from v0.37. The 27/28-key conditional schema is unchanged.
- **`ProblemActionSpec` gained `coefficient_relation`.** Additive and defaulted to `not_applicable`, so specs written against the four prior axes construct unchanged. `not_applicable` is deliberately distinct from `unknown`: a constant-coefficient problem has no background, which is not ignorance.
- **`publish.yml` hardened (v0.36f).** It was the only workflow still using floating action tags, and the only one granted `id-token: write`. All five actions SHA-pinned; the build job writes `SHA256SUMS` and each publish job verifies it before upload; no `skip-existing`, because index versions are immutable and a skip reports success having published nothing.
- **Residuals comparison tolerance.** `atol` `1e-12` → `5e-11` for the `residuals` stage only. α's value was calibrated on `heat_1d` alone and does not transfer; the new value is measured across five PDEs on two platforms with a 19.6× binding margin.

### Fixed

- **A latent cross-platform failure in the α stage-1 classification.** `generated_field_statistics` was frozen as `qualitative_invariant` with a `sign` invariant, but `std` and `l2` are non-negative by construction and the mean is `-4.17959937e-17` — numerical zero, whose sign is rounding noise. Reclassified to `tolerance_numeric` and asserted across all five β configs.
- **The migration orchestrator could not run on a clean machine.** `uv venv --seed` seeds setuptools 83.0.0, which removed `pkg_resources`; PySINDy 1.7.5 imports it at module load. Only the build venv was pinned, never the runtime venv, and `pip install <wheel>[extra]` exits 0 either way — so the failure was silent until an exporter tried to use it. Fixed with a runtime setuptools pin plus a probe that fails at the venv.
- **A duplicate publishing document.** v0.36f briefly added `PUBLISHING.md` at the repository root while `docs/releases/PUBLISHING.md` already existed and was referenced by the README, four readiness docs and a release-gate test. Consolidated into the canonical location.


## 0.35.0

Release-close for the v0.35 arc: three internal sub-milestones (v0.35a design-matrix diagnostics, v0.35c deterministic row selection, v0.35b private point-symmetry catalogue) plus a day-0 polish PR, consolidated into a single tag per the solo-dev consolidation policy. Submodule-only surface — no root `pdelie` export added. No new PDE, no new symmetry method, no change to any existing payload shape.

Release decision: `v0_35_0_design_diagnostics_row_selection_and_point_symmetry_catalogue`.

**Process note.** All three sub-milestones were prototyped and measured *before* their contracts were frozen; eight of the twelve gates changed what shipped. Three defects would otherwise have shipped silently: a leverage route that errs by 0.56 on a quantity bounded in `[0, 1]`, a classification whose verdict flipped under an arbitrary column rescaling, and an irrepresentability constant returning a plausible sub-threshold number from a singular system where `lstsq` had quietly substituted a minimum-norm solution.

Two errors were caught by CI rather than inspection, both the same class — a claim measured on macOS and recorded as universal, then failing on Linux. Both are documented in `docs/releases/V0_35_RELEASE_READINESS.md`.

### Added

- **`pdelie.diagnostics` (v0.35a).** Four report-only design-matrix metrics: `mutual_coherence`, `leverage_scores`, `irrepresentability_constant`, `restricted_eigenvalue`, plus `summarize_design_matrix_diagnostics`. New `summary_type`: `pdelie_design_matrix_diagnostic`. All metrics are computed on the column-normalized matrix (`||a_j||_2 = 1`) and every payload reports its `column_scaling` — coherence and leverage are scale-invariant, the other two are not, and an arbitrary rescaling moved the irrepresentability constant across the 1.0 recovery threshold on identical data. Leverage is computed from the thin SVD, never the hat matrix. Undefined cases return `None` with a named warning; no NaN, no Inf.
- **`pdelie.design` (v0.35c).** Three deterministic row-selection methods: `qr_pivot_row_selection`, `d_optimal_exchange_row_selection`, `leverage_row_selection`, plus `summarize_row_selection`. New `summary_type`: `pdelie_row_selection_diagnostic`. Pure NumPy and core-installable — `numpy.linalg.qr` has no `pivoting` parameter and scipy is not a core dependency, so the Householder QR with column pivoting is hand-rolled (Golub & Van Loan Alg. 5.4.1) with scipy retained as a test-side oracle only.
- **`pdelie.symmetry._point_symmetry_registry` (v0.35b).** Thirteen catalogued Lie point symmetries across heat / Burgers / advection-diffusion, with `classify_point_symmetry` emitting the frozen vocabulary `{exact_and_useful, valid_but_not_useful, invalid}`. New `summary_type`s: `pdelie_point_symmetry_catalogue`, `pdelie_point_symmetry_classification`. **Underscore-private on purpose:** no public write-up exists to cite for the taxonomy.
- **`tests/fixtures/v0_35a_canonical_design_matrix.npz`.** The canonical weak-form design matrix at `seed=20340` (16x5, rank 5, condition 5232.86), with a named-cause regeneration CLI. The v0.34c fixture stores scalars only, so the matrix the v0.35 plan referred to did not previously exist on disk.

### Changed

- **Blocking toolchain pinned (day-0).** `[test]` moves from `ruff>=0.6` to `ruff~=0.16.0` and from `mypy>=1.11` to `mypy~=2.3.0`. `lint` is a blocking CI job, so the linter version is part of the merge gate: on the unchanged v0.34.0 tree, ruff 0.9.10 reported 102 errors, 0.14.5-0.15.20 reported 5, and 0.16.0 reported none. `mypy`'s floor had already drifted to 2.3.0 in CI, unnoticed because `typecheck` is advisory.
- **README/release alignment guard tightened (day-0).** Now derived from `pyproject["project"]["version"]` and asserting both the prose release line and the pip-install pins. The prior form accepted four version strings across two release lines, which is how v0.33.0 shipped with a README advertising v0.32.0.
- **`docs/planning/ROADMAP.md` v0.36 precondition dropped.** It gated the Ko-sparse port on the point-symmetry registry "having proven the multi-method contract with more than one built-in". That cannot be satisfied by a catalogue-data registry; the Ko-sparse port is itself what proves the contract. v0.36 is unblocked.

### Not changed

- `SymmetryMethod` still has exactly one built-in, and its `fit(field, ...)` semantics are intact. Catalogued point symmetries are analytically known and discover nothing, so they ship as data rather than as registered methods. **v0.35.0 success criterion 4 is recorded as not met** rather than restated into a pass.
- Frozen four `method_scores` names; `_CONFIDENCE_LABELS`; `discovery_task_result` 22-key schema; `pdelie_weak_pde_library_diagnostic` 27-key default schema; `VerificationReport.classification`; `SymmetryCandidate` discriminators; `ResidualBatch` top-level shape; `pdelie.__all__`.

### Known limitations

- `leverage_row_selection` is not a conditioning method: it beat 8% of 40 random draws on the canonical weak matrix where the other two beat 100%. It reports influence, and says so in its own warnings.
- `d_optimal_exchange_row_selection` is a local search reaching four to five distinct optima across five random starting sets. The start defaults to the deterministic QR selection and is reported.
- The pivoted-QR permutation agrees with SciPy only where pivoting has signal; on tied-norm designs every tie-break is valid and SciPy's own choice varies by LAPACK build. Selection *quality* agrees everywhere.
- `classify_point_symmetry` requires caller-supplied validity and cannot determine on its own whether a symmetry holds on given data.

## 0.34.0

Release-close for the v0.34 arc: three internal sub-milestones (v0.34a variable-coefficient residual evaluators, v0.34b admissibility scoring, v0.34c column-normalized weak-form design matrices) consolidated into a single tag per the solo-dev consolidation policy. Submodule-only surface — no root `pdelie` export added. No new PDE, no new symmetry method, no new `summary_type`.

Release decision: `v0_34_0_variable_coefficient_residuals_and_weak_form_conditioning`.

**Process note.** All three sub-milestones were prototyped and measured *before* their contracts were frozen, and all three measurements changed what shipped. The most consequential was v0.34c, where measurement showed the target function was nondeterministic — the planned threshold was not wrong so much as unmeasurable.

### Added

- **Variable-coefficient residual evaluators (v0.34a).** `HeatResidualEvaluator`, `BurgersResidualEvaluator`, and `AdvectionDiffusionResidualEvaluator` accept `diffusivity` (and `advection_speed`) as a scalar, a pre-sampled `(num_points,)` array, or `None`. The array path dispatches on `parameter_tags["nu_form"]` recorded by the v0.33d generators. Additive `ResidualBatch.diagnostics` keys: `variable_coefficient_evaluator_dispatch`, `nu_form`, `coefficient_matches_field_provenance`, plus `nu_min`/`nu_max`/`nu_l2_norm`. `ResidualBatch` top-level shape unchanged.
- **Reference-relative admissibility (v0.34b).** `polynomial_translation_svd.fit()` gains optional `reference_generator_family` and `reference_generator_family_id`; the result lands in `fit_diagnostics["variable_coefficient_admissibility"]`, `None` when absent. `relative_error_l2` compares unit-normalized coefficient directions and is therefore scale-invariant, sign-invariant, and bounded above by `sqrt(2)`.
- **`pdelie.symmetry.admissibility.classify_background_treatment` (v0.34b).** Distinguishes a *symmetry* of a variable-coefficient problem from an *equivalence* mapping it to a different one. Frozen three-value vocabulary: `fixed_background_same_target_symmetry_failed`, `co_transforming_background_equivalence`, `inconclusive_background_separation`.
- **Column normalization (v0.34c).** `inspect_pysindy_weak_pde_library(..., column_normalize=True)` normalizes the weak design matrix to unit column L2 norm and emits a `column_normalization` block. New pure-NumPy module `pdelie.discovery.column_normalize`.
- **Reproducibility seed (v0.34c).** `inspect_pysindy_weak_pde_library(..., seed=...)`. `pysindy.WeakPDELibrary` places its `K` domain centers from the global NumPy RNG and exposes no seed parameter, so the diagnostic had been nondeterministic since v0.31b2. Default `None` preserves that behaviour exactly; a seed makes the report reproducible, with the caller's global RNG state saved and restored.
- **Golden fixture extensions.** Three variable-coefficient entries in `v0_33e_golden_numbers.json` exercising the array dispatch path. New `v0_34c_conditioning_ratios.json` pinning per-fixture conditioning at a fixed seed.

### Changed

- `inspect_pysindy_weak_pde_library` may now emit a 28th top-level key, `column_normalization`, **only** on the opt-in path. The default path keeps exactly the frozen 27 keys, so every payload producible before v0.34c is unchanged in shape.
- CI release-gate job renamed `v0_33_0-release-gate` → `v0_34_0-release-gate`.

### Amended during implementation

- **v0.34c — the planned figures do not reproduce.** An 87× column-scale ratio and a condition number of 111.8 → 3.77 could not be matched on any of 48 swept configurations. `WeakPDELibrary` is nondeterministic: across 12 unseeded draws of the canonical fixture, the pre-normalization condition number ranged 5.03–14.44 and the column-scale ratio 3.93–6.64. The planned figures were one draw from a distribution. The requirement that the default path "byte-preserve the v0.31b2 golden report" was likewise unachievable, because the report did not reproduce against itself. The ≥20× threshold is unsupported — only 1 of 6 fixtures clears it, and the canonical fixture improves by 1.79×.
- **v0.34a — `nu_form` dispatch is mandatory.** The planned residual formula `u_t + u·u_x − ν(x)·u_xx` is the non-conservative one, but the v0.33d generators default to conservative divergence form. Measured, evaluating the wrong operator against matched data inflates the residual L2 by roughly 300×, so the planned formula alone would have mismatched default-generated data by that factor.
- **v0.34a — a coefficient/provenance mismatch is reported, not refused.** A first implementation raised on "scalar coefficient, array-profile field" as a configuration error, which broke the released v0.33d admissibility crash test — that combination is precisely what the crash test performs.
- **v0.34b — the classification vocabulary was frozen only after measurement.** Across three PDEs and shifts of 1–16 grid points, the fixed-background residual exceeds the co-transforming residual by 77×–15437× (median 1049×), all 15 measurements above the 5× separation bar. The co-transforming residual equals the untranslated baseline *exactly* at every shift, and the fixed-background residual grows monotonically with displacement.

### Invariants preserved

Frozen four `method_scores` names; `_CONFIDENCE_LABELS` vocabulary; `discovery_task_result` 22-key top-level schema; `pdelie_weak_pde_library_diagnostic` 27-key default schema; `VerificationReport.classification` vocabulary; `SymmetryCandidate` discriminators; root `pdelie` namespace surface; `ResidualBatch` top-level shape. No new `summary_type`.

### Not unlocked

No WSINDy claim. No noise-robustness claim. No dataset-recovery claim. Conservative *advection* is generated by v0.33d but not evaluated by v0.34a. Callable coefficient profiles are refused by the residual evaluators. KdV and reaction-diffusion variable-coefficient support remain out of scope.

## 0.33.0

Release-close for the v0.33 arc: five internal sub-milestones (v0.33a nonperiodic generator dispatch, v0.33b overlap-crop finite-transform verification, v0.33c mask-preserving discovery bridge, v0.33d variable-coefficient data generators, v0.33e golden-numbers regression gate) plus one scope-freeze amendment, consolidated into a single tag per the solo-dev consolidation policy. Submodule-only surface — no root `pdelie` export added. No new PDE, no new symmetry method.

Release decision: `v0_33_0_nonperiodic_interior_symmetry_and_mask_validity`.

**Scope narrowing.** v0.33 was planned as "nonperiodic generator support" and ships as **nonperiodic interior-symmetry and mask-validity support**. v0.33a/b establish that a candidate is a symmetry of the differential equation on interior/overlap rows; they do **not** establish boundary-value-problem preservation. A uniform translation on a bounded domain is a domain-changing action, and the overlap crop discards exactly the rows that would settle the boundary question. The `symmetry_claim` diagnostic carries the distinction over a frozen six-value vocabulary; both `boundary_value_problem_preserved` and `boundary_value_problem_not_preserved` are reserved-but-never-emitted, asserted by test.

### Added

- **Nonperiodic generator fit (v0.33a).** `fit_translation_generator` and `polynomial_translation_svd` dispatch on `is_x_periodic`. The nonperiodic branch uses finite-difference derivatives and an interior-only shave; the periodic branch is byte-preserved. Six new diagnostic keys, forwarded verbatim by the method adapter: `boundary_condition_x`, `boundary_condition_dispatch_reason`, `interior_only_reduction_applied`, `interior_only_row_count`, `interior_only_trim_width`, `symmetry_claim`. `svd_span_distance` is also forwarded so the pre-fallback value is visible on both branches.
- **Overlap-crop verification (v0.33b).** `verify_translation_generator` dispatches on `is_x_periodic`; the nonperiodic branch compares on overlap ∩ interior via the new `_apply_overlap_crop_translation` helper. Nine new `VerificationReport.diagnostics` keys including `dispatch_path`, `overlap_fraction`, `overlap_row_count`, and `compared_row_count`. Delivers what v0.31.5 deferred.
- **Mask-preserving discovery bridge (v0.33c).** `run_pysindy_pde_task` gains `mask_application: "before_differentiation" | "after_differentiation"`, defaulting to `"after_differentiation"`. Seven mask diagnostics under the namespaced key `fit_diagnostics["pdelie_mask_diagnostics"]`, including the three-mask decomposition (`observation_mask_row_count`, `derivative_validity_mask_row_count`, `regression_row_mask_row_count`).
- **Variable-coefficient data generators (v0.33d).** `diffusivity_profile` on Heat / Burgers / advection-diffusion and `advection_profile` on advection-diffusion, each accepting an array, a callable, or `None`. `diffusivity_form` and `advection_form` selectors, recorded as `parameter_tags["nu_form"]` / `["c_form"]` — the v0.34a residual-evaluator dispatch key. `parameter_tags["nu_treatment_policy"] = "fixed_background"`. Full profile provenance (`nu_profile_kind`, `nu_profile_hash`, `nu_min` / `nu_max` / `nu_l2_norm` for all three kinds).
- **Golden-numbers regression gate (v0.33e).** `tests/fixtures/v0_33e_golden_numbers.json` pins six aggregate metrics per PDE at `rtol=1e-6`, `atol=1e-12`, across five periodic and three nonperiodic entries. Regeneration requires a named cause via `python -m tests._helpers.regenerate_golden_fixture`.
- **Admissibility dose-response fixture (v0.33d).** `tests/fixtures/v0_33d_admissibility_dose_response.json` pins the `residual_l2` curve at α ∈ {0, 0.1, 0.25, 0.5, 0.75} on the frozen ν(x) = ν₀(1 + α·sin(2πx/L)) family, with an α=0 integrator control.

### Changed

- **`polynomial_translation_svd` accepts nonperiodic input.** Acceptance is not a claim of boundary-value-problem preservation; the narrower claim is carried by `symmetry_claim`. The frozen four `method_scores` names are unchanged on both branches.
- **`build_translation_basis` no longer gates on boundary condition.** The basis `{1, t, x, u}` is built from coordinates and values alone and is boundary-condition-agnostic.
- **`apply_pointwise_translation` dispatches.** The periodic path wraps as before; the nonperiodic path does not wrap and clamps off-domain.
- **`underlying_discovery_result` verbatim guarantee narrowed.** Since v0.33c the task attaches mask diagnostics under exactly one namespaced key, `fit_diagnostics["pdelie_mask_diagnostics"]`. Every other field of the embedded sibling — including every backend-native `fit_diagnostics` entry — remains byte-for-byte what the backend summarizer produced. The regression guard strips only that key before comparing.
- **CI release-gate job renamed** `v0_32_0-release-gate` → `v0_33_0-release-gate`.

### Amended during implementation

Five of six frozen sub-milestone contracts required amendment on contact with measurement. Each amendment is recorded in `docs/design/V0_33_NONPERIODIC_GENERATORS_AND_MASK_PRESERVING_BRIDGE.md` with the measurement that forced it. Three would otherwise have shipped as silent defects.

- **v0.33e** — the fixture was specified with six PDEs; Fisher-KPP and reaction-diffusion are the same generator, so five ship. The `atol` rationale claimed a float32 quantization limit; the pipeline is float64 throughout. Bit-exact fixture comparison was replaced by tolerance comparison after it failed on Linux BLAS (worst cross-platform deviation 1.5e-9 against `rtol=1e-6`).
- **v0.33d** — the admissibility crash test was specified against `span_distance`. That metric is bounded by √2 and collapses to exactly `0.0` through the `reference_fallback` path, reporting a *perfect* translation generator on a failing candidate in 10 of 18 measured configurations. The shipped gate is `residual_l2 ≥ 10×`, which separated 18/18 with 177× headroom.
- **v0.33a** — the interior shave was specified as one row. Measured, a 1-row shave leaves `span_distance` near its √2 ceiling on all four PDEs (1.13–1.40); the shave must equal the residual evaluator's `boundary_trim_width`, at which point Heat collapses to 4.3e-3. The `reference_fallback` is additionally suppressed on the nonperiodic branch, where it fired on 3 of 4 PDEs and masked honest spans of 0.24–0.64 as `0.0`.
- **v0.33b** — `domain_length` must be `x[-1] - x[0] + dx` (N·dx), not the (N−1)·dx span; only that convention makes `overlap_fraction` equal `retained_rows / num_points` exactly. The comparison is overlap ∩ interior, not overlap alone. At every default epsilon the interior trim, not the crop, is the binding constraint.
- **v0.33c** — the bridge maps each x point to a PySINDy *feature* and each time step to a design-matrix *row*, so mask erosion is temporal and a spatial mask drives the observation row count to zero. Such masks are rejected. The correct path requires precomputed `x_dot`; differentiating a row-selected array computes derivatives across the removed rows (measured leakage 7.2e-5 relative). The spectral hard-reject inspects the caller's `pysindy_model.differentiation_method`, because `compute_derivatives` is never called in this code path.

### Invariants preserved

Frozen four `method_scores` names; `_CONFIDENCE_LABELS` vocabulary; `discovery_task_result` 22-key top-level schema; `pdelie_weak_pde_library_diagnostic` 27-key schema; `VerificationReport.classification` vocabulary `{exact, approximate, failed}`; `SymmetryCandidate` reserved discriminators; root `pdelie` namespace surface. No new `summary_type`.

### Not unlocked

Nonperiodic KdV; nonperiodic PySINDy discovery (`PySINDyDiscoveryUnsupportedBoundaryError` still fires); nonperiodic weak-form residuals; residual-side ν(x) support (v0.34a); spatial masks in the discovery bridge; boundary-value-problem preservation claims of any kind.

## 0.32.0

Release-close for the v0.32 arc: four internal sub-milestones (v0.32a modern-runtime migration, v0.32b strict method-score / uncertainty / calibration reporting, v0.32c candidate-to-discovery workflow example, v0.32d external-data readiness cookbooks) consolidated into a single tag per the solo-dev consolidation policy. Submodule-only surface — no root `pdelie` export added. Periodic scalar 1D only. No recovery-benchmark claim, no generic symmetry-discovery claim.

Release decision: `v0_32_0_consolidated_modernization_and_external_readiness`.

### Added

- `pdelie.reporting.summarize_generator_confidence` gains three additive optional fields (`method_scores`, `uncertainty_report`, `calibration_report`) and moves to the strict-JSON boundary. All three default to `None`; existing callers unchanged. `_CONFIDENCE_LABELS` frozen four-vocabulary invariant preserved.
- `pdelie.reporting.enrich_method_scores(values, metadata)` — pairs a plain `dict[str, float | None]` with a method's frozen `SCORE_METADATA` into the enriched-form entry.
- `pdelie.symmetry.methods.polynomial_translation_svd.SCORE_METADATA` and `bootstrap_uncertainty(field, residual_evaluator, *, seed, num_resamples=64, interval_level=0.95, min_units=8, resampling_unit="batch")`. Batch-only resampling; row-level bootstrap refused with `ScopeValidationError`; percentile intervals; deterministic under seed; fit-per-resample; `diagnostic_only=True`. Frozen four-score names: `{span_distance, residual_l2, error_curve_max, svd_condition_number}`.
- `pdelie.reporting.summarize_candidate_to_discovery_workflow(...)` — composed strict-JSON summary carrying 15 explicit ordered stages: `field_readiness`, `derivative_residual_evidence`, `symmetry_method_result`, `candidate_summary`, `generator_confidence`, `candidate_validation`, `finite_transform_verification`, `action_policy`, `orbit_or_coverage_diagnostics`, `split_leakage_provenance`, `baseline_discovery_task`, `candidate_guided_discovery_task`, `downstream_comparison`, `evidence_conclusion`, `scope_boundaries`. Blocked/skipped/unavailable stages carry a `candidate_to_discovery_workflow_stage_marker` payload — never silently omitted.
- `pdelie.examples.candidate_to_discovery_workflow.run_candidate_to_discovery_workflow_example(scenario=...)` and CLI `python -m pdelie.examples.candidate_to_discovery_workflow`. Two deterministic scenarios: `"successful"` fully executable end-to-end; `"valid_but_not_useful_static"` a provenance-backed static illustration. Feeds the FULL training FieldBatch (`batch_size>1`) to `run_pysindy_pde_task` — no silent first-trajectory slicing. `evidence_conclusion.reasons` name the exact `downstream_comparison.metric_key` (`heldout_residual_l2_norm`).
- `pdelie.examples.pdebench_burgers_1d_readiness.run_pdebench_burgers_1d_readiness_cookbook(...)` + CLI. Narrow readiness cookbook pinned to a single DaRUS shard: `1D_Burgers_Sols_Nu0.001.hdf5`, DOI `10.18419/darus-2986`, CC-BY-4.0, MD5 `b4be2fc3383f737c76033073e6d2ccfb`. Emits strict-JSON `pdelie_external_data_readiness` reports with conclusions in a frozen 9-label vocabulary. Optional-dependency extra: `pip install 'pdelie[pdebench]'` (h5py only). Absent the extra, an `ImportError` names the extra explicitly.
- `pdelie.examples.the_well_feasibility_scan.run_the_well_feasibility_scan()` + CLI. Metadata-only scan; no network I/O in default CI. Distinguishes the Ohana et al. 2024 paper count (`paper_dataset_count = 16`) from the current PolymathicAI catalogue count (`catalogue_entry_count = 23`, with hosted variants like `mhd_64` / `mhd_256` split). Every entry is `scalar_1d_extractable=False`; frozen conclusion `blocked_multichannel_required`.
- Frozen strict-JSON configs shipped both in-tree (`configs/external_data/`) and inside the package (`src/pdelie/examples/_external_data/`) so a clean wheel install can load them.
- New optional extra `[pdebench]` (h5py-only). No implication of broad PDEBench support; scoped strictly to the frozen v0.32d cookbook.
- Runtime rebase (v0.32a): Python `>=3.12`, NumPy 2.x, PySINDy 2.1.x. Six PySINDy-2.x API-break sites migrated. `_pysindy2_prototype.py` deleted. `setuptools<82` co-install workaround retired. `SymmetryCandidate` reserved-representation construction hardened from warning-gate to `ScopeValidationError`. New CI matrix (py3.12 + py3.13 blocking; py3.14 core-only advisory).

### Compatibility

- Python: `>=3.12`. Python 3.11 is no longer supported on the active line.
- Dependencies: `numpy>=2,<3`, `pysindy>=2.1,<3`, `scikit-learn>=1.4,<2`, `scipy>=1.14,<2`.
- Optional extras: `downstream`, `xarray`, `viz`, `test`, and (new) `pdebench` (h5py-only).
- Legacy Python 3.11 + PySINDy 1.7.5 users track the `release/v0.31.x` maintenance branch cut from the `v0.31.0` tag. Maintenance-end policy: security-only fixes for 12 months from the v0.32.0 tag, then archived.

### Explicit non-claims

- No new PDE. No new symmetry method. No new `SymmetryCandidate` discriminator.
- No `discovery_task_result` schema change (still 22 keys). No `pdelie_weak_pde_library_diagnostic` schema change (still 27 keys).
- No root `pdelie` export.
- No generic symmetry-discovery claim: PDELie continues to score and verify caller-supplied candidates, not to discover symmetries autonomously.
- No external-data recovery-benchmark claim. The v0.32d cookbooks report readiness and feasibility only.
- No noise-robustness claim. No WSINDy claim. No nonperiodic finite-transform verification (deferred). No multi-channel / 2D contract widening (deferred).

## 0.31.0

Final release for the v0.31 downstream discovery task-bridge slice. Submodule-only surface — no root `pdelie` export added. Periodic scalar 1D only.

Release decision: `downstream_discovery_task_bridge`.

### Added

- `pdelie.tasks.run_pysindy_pde_task(field, *, task_name, pysindy_model, ...)` — executable PySINDy `PDELibrary`-backed sparse-discovery task runner (v0.31b1). Layer-1 boundary-condition guard raises `PySINDyDiscoveryUnsupportedBoundaryError` before any PySINDy call when `is_x_periodic(field)` is false. Returns a strict-JSON `discovery_task_result`.
- `pdelie.tasks.summarize_discovery_task_result(...)` — strict-JSON payload assembler enforcing the frozen 22-key composed schema. `summary_type = "discovery_task_result"`, `summary_schema_version = "0.1"`, `pysindy_bridge_variant = "periodic_only_v1"`. `_validate_strict_json_compatible` invoked exactly once at the composition boundary.
- `pdelie.tasks.PySINDyDiscoveryUnsupportedBoundaryError` — subclass of `ScopeValidationError`.
- `pdelie.tasks.inspect_pysindy_weak_pde_library(field, ...)` — diagnostic-only wrapper around PySINDy's `WeakPDELibrary` (v0.31b2). Two-layer scope guard (periodic-x, uniform x/t grids, `batch == 1`, single var, K-scaled grid-sufficiency floor `max(8, 4*K)`, unsupported PySINDy API). Returns a strict-JSON `pdelie_weak_pde_library_diagnostic`.
- `pdelie.tasks.summarize_pysindy_weak_pde_library_diagnostic(...)` — strict-JSON payload assembler enforcing the 27-key composed schema. `summary_type = "pdelie_weak_pde_library_diagnostic"`, `diagnostic_only = True`, `method_family = "pysindy_weak_pde_library_polynomial_gauss_v1"`.
- `pdelie.tasks.WeakPDELibraryDiagnostic` — caller-declared JSON-safe library-configuration dataclass with `as_dict()`.
- `pdelie.examples.run_downstream_discovery_task_bridge_example` and CLI `python -m pdelie.examples.downstream_discovery_task_bridge` (v0.31c) — composed JSON-only public example. `summary_type = "downstream_discovery_task_bridge_example"` (7-key wrapper — not a new report schema).
- Adapter loosening: `fit_pysindy_discovery` accepts a caller-supplied `pysindy_model` kwarg (v0.31b1). `config != None` still raises; `config=None, pysindy_model=None` default path byte-preserved for existing v0.30 callers.
- `configs/pysindy_compatibility_matrix.json` — machine-readable machine-readable compatibility matrix under `summary_type = "pdelie_pysindy_compatibility_matrix"` (v0.31b3), with a `v0_31c1_packaging_audit` block enumerating the setuptools boundary (v0.31c1).
- `configs/release_gate_manifest.json` — extended `"0.31"` row pinning required submodule attributes and forbidden root attributes for the full v0.31 downstream task-bridge surface. The CI release-gate job is renamed `v0_30-release-gate → v0_31-release-gate`.
- `docs/design/DISCOVERY_TASK_RESULT_SCHEMA.md`, `docs/design/PYSINDY_COMPATIBILITY_POLICY.md`, `docs/planning/PYSINDY_API_PREFLIGHT_AUDIT.md` — new design and planning artifacts anchoring the schema, the compat policy, and the fail-fast preflight discipline for future PySINDy-touching releases.

### Compatibility

- PySINDy pin: `>=1.7.5,<2` under `python_version < '3.12'` (v0.31b3, `C_temporary_1x_policy` outcome). PySINDy 2.x support is deferred to `v0.31.1` — the release-close document enumerates four independent 2.x API breaks and a transitive `numpy>=2` floor conflict.
- scikit-learn pin: `>=1.2.2,<1.3` under `python_version < '3.12'`.
- setuptools pin: `<82` under `python_version < '3.12'` — **temporary** constraint added by v0.31c1 because pysindy 1.7.5 imports `pkg_resources` at package init and setuptools 82 removed the module. Confirmed by an adversarial matrix on Python 3.11 fresh venvs (setuptools 81 pass; 82/83 `ModuleNotFoundError` at `import pysindy`). Post-fix rebuilt-wheel verification: pip auto-downgrades ambient setuptools 82/83 to 81 without user co-install. The cap retires when the pysindy pin widens to `>=2` in `v0.31.1` / `v0.32`.
- Python 3.12+ downstream support: **deferred to `v0.31.1`.** The `[downstream]` extra is marker-scoped to `python_version < '3.12'`; on Python 3.12+, invoking the task bridge raises a targeted, actionable `ImportError` (or `ScopeValidationError` on the weak path) whose message names the v0.31.1 deferral and states that reinstalling the same extra will not fix the environment.
- `numpy>=1.24,<2` and Python `>=3.11` unchanged.

### Diagnostics

- `pdelie_weak_pde_library_diagnostic` is **diagnostic-only**. It reports column norms, matrix rank, matrix condition number, retained/skipped weak rows, weak feature names, and provenance — but does NOT compute a recovery benchmark, does NOT tune thresholds, and does NOT introduce a clean/noisy gate.
- No WSINDy benchmark claim.
- No noise-robustness claim.
- No numerical equivalence with `pdelie.residuals.weak_1d`. The PDELie-native weak-derivative path remains available and is retained through at least `v0.32` close.

### Examples

- One new public JSON-only example: `pdelie.examples.run_downstream_discovery_task_bridge_example` and its CLI. Composes both v0.31 paths on one canonical periodic scalar 1D Heat field (T=64, X=64, K=16, seed=31000). Deterministic under the frozen seed via a private `_legacy_numpy_rng_seed_scope` context manager (v0.31c1); documented as not-thread-safe because PySINDy 1.7.5 uses the legacy `np.random` global RNG.
- The example uses only public submodule APIs (AST-checked). No root `pdelie` export.

### Boundaries / non-goals

- No new PDE.
- No new summary type. The v0.31 report surface is exactly `discovery_task_result` (22 keys) and `pdelie_weak_pde_library_diagnostic` (27 keys) — plus the composed `downstream_discovery_task_bridge_example` wrapper, which is NOT a new report schema.
- No nonperiodic PySINDy discovery. Both v0.31 task paths raise on nonperiodic-x inputs.
- No FD-nonperiodic PySINDy discovery.
- No PySINDy 2.x code; the pin stays `<2` and code paths are byte-preserved for v0.30 callers.
- No `pdelie.symmetry.SymmetryMethod` registry, no `SymmetryCandidate` runtime — deferred to `v0.30.1`.
- No PDEBench / The Well support claim — deferred to `v0.32`.
- No multi-channel / 2D widening — deferred to `v0.34+` scope decision.
- No new root `pdelie` exports.
- No PyPI or TestPyPI publication; package-index publishing remains deferred to `v1.0` or later.
- The three retained xfails all have non-empty reasons and are assigned to `v0.31.1` (runtime version guards on the two task entry points) or to a nested provenance follow-up (adding `scipy` to `_resolve_backend_version`).

## 0.30.0

Final release for the frozen V0.30 nonperiodic-readiness and low-order finite-difference derivative-diagnostics slice.

- adds structured boundary metadata: `metadata["boundary_conditions"]["x"]` now supports `type ∈ {"periodic", "dirichlet", "neumann", "open_unknown"}` with optional per-face values; `FieldBatch.SCHEMA_VERSION` bumps `"0.1"` → `"0.2"`; `FieldBatch.from_dict` accepts both versions and normalizes legacy string BCs into the structured form via internal `pdelie._boundary` helpers, recording a `schema_0_1_to_0_2_boundary_normalization` entry in `preprocess_log`
- adds `pdelie.derivatives.compute_finite_difference_derivatives(field, *, max_spatial_order=2)` — low-order finite-difference backend on scalar 1D nonperiodic uniform grids for `u_t`, `u_x`, `u_xx` only
- adds `pdelie.derivatives.compute_derivatives(field, *, backend="auto", max_spatial_order=2)` — dispatcher that routes periodic data to `spectral_fd` and nonperiodic data to `finite_difference`; explicit-mismatch calls raise `ScopeValidationError`; the selection is recorded in `DerivativeBatch.config["backend_selected_by_boundary_condition"]` and `DerivativeBatch.config["backend_selection_reason"]`
- adds interior-only residual diagnostics: Heat, Burgers, advection-diffusion, and reaction-diffusion residual evaluators route through `compute_derivatives(backend="auto")` when derivatives are omitted, consume `recommended_residual_domain_policy` and `recommended_boundary_trim_width` from `DerivativeBatch.config`, and emit `residual_domain_policy` (`"interior_only"` for nonperiodic FD-derived residuals, `"full_grid"` for periodic residuals) plus a nested `full_grid_diagnostic` block for transparency; Heat and Burgers diagnostics gain `rms_residual` alongside `max_abs_residual`
- adds `boundary_condition_warnings` on `pdelie.reporting.summarize_field_batch_readiness` and `pdelie.reporting.summarize_xarray_dataset_readiness`, downgrading the readiness label from `"ready"` to `"needs_attention"` when warnings are present
- adds cross-cutting hygiene phase 1: `[tool.ruff]`, `[tool.mypy]` (strict scope narrowed to `pdelie.contracts`, `pdelie._boundary`, `pdelie.derivatives.*`), and `[tool.coverage.*]` in `pyproject.toml`; three non-blocking CI jobs (`lint`, `typecheck`, `coverage`); coverage baseline **86%** on `src/pdelie/`; ruff/mypy/pytest-cov/pyyaml added to the `[test]` extra
- adds narrow declarative release-gate consolidation: `configs/release_gate_manifest.json` (strict JSON) and `tests/test_release_gates.py` replay declarative content for 18 migrated releases plus a `v0.30` release-close row; the CI release-gate job is renamed to `v0_30-release-gate`; zero per-version `tests/test_v0_NN_release_gate.py` files are deleted
- records the release decision `nonperiodic_readiness_and_low_order_finite_difference_diagnostics`
- preserves the retained v0.29 workflow recipes, support matrix, and rendered tutorial notebooks; preserves v0.28 scalar `xarray.Dataset` ingestion; preserves the v0.19–v0.24 confidence, readiness, downstream, split-provenance, and weak-supportability report surfaces; preserves the frozen v0.8 weak Heat/Burgers report slice; preserves the stable Heat / Burgers / KdV (normalized short-horizon) / Fisher-KPP / advection-diffusion strong paths

Explicitly deferred for this final release:

- no new PDE
- no PDEBench or The Well support claim
- no file loaders, broad adapters, `from_pdebench`, `from_the_well`, `from_netcdf`, `from_zarr`, or dataset-adapter registries
- no KdV nonperiodic; no KS nonperiodic; no public KS runtime API
- no weak nonperiodic residuals or weak derivatives; no WSINDy design matrices; no weak sparse recovery
- no `u_xxx` or `u_xxxx` on nonperiodic data in the stable v0.30 surface
- no finite-transform verification on nonperiodic translations (deferred to `v0.31.5` overlap-crop design)
- no `pdelie.symmetry.SymmetryMethod` registry (deferred to `v0.30.1`)
- no root `pdelie.discover_symmetries` (deferred to `v1.0` scope decision)
- no external symmetry-method ports (deferred to `v0.33`+)
- no new root `pdelie` exports
- no neural, callable, or operator-facing APIs
- no train/test policy, split enforcement, or leakage prevention
- no multidimensional or multi-channel widening; no nonuniform grid support (deferred to `v0.34` scope decision)
- no lift of the `numpy<2` cap (deferred to Phase 3, `v0.32` or later)
- no Python matrix expansion (CI stays Python 3.11 only)
- no promotion of the advisory `lint` / `typecheck` / `coverage` CI jobs to blocking (deferred to Phase 2)
- no PyPI or TestPyPI publication; package-index publishing remains deferred to `v1.0` or later

## 0.29.0

First final release for the frozen V0.29 workflow recipes and support matrix slice.

- adds public Read the Docs workflow recipes for data readiness, candidate validation, downstream/export provenance, Dataset-to-downstream, and candidate-to-split-provenance paths
- adds `docs/specs/support_matrix.v0_29.json` as a strict machine-readable support matrix
- updates `docs/specs/SUPPORT_MATRIX.md` as the human-readable support matrix and selected helper inventory
- adds rendered tutorial notebooks `12_dataset_to_downstream_workflow.ipynb` and `13_candidate_to_split_provenance_workflow.ipynb`
- records the release decision `workflow_recipes_and_support_matrix_complete_no_new_numerical_scope`
- preserves the retained V0.28 scalar `xarray.Dataset` ingestion surface, confidence reports, readiness reports, downstream discovery contracts, split provenance, weak supportability, multi-generator diagnostics, and stable PDE strong paths

Explicitly deferred for this final release:

- new numerical scope
- new runtime APIs, including `pdelie.reporting.summarize_workflow_readiness(...)`
- new PDE support
- file loaders or broad adapter frameworks
- metadata inference engines
- multidimensional, multivariable, or nonuniform-grid support
- train/test split management or leakage prevention
- public KS runtime APIs
- neural, callable, or operator-facing APIs
- root export expansion
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.28.0

First final release for the frozen V0.28 narrow xarray Dataset ingestion and data-ecosystem feasibility slice.

- adds `pdelie.data.from_xarray_dataset(...)` for explicit scalar `xarray.Dataset` variable conversion into canonical `FieldBatch`
- adds `pdelie.reporting.summarize_xarray_dataset_readiness(...)` for strict JSON-compatible Dataset readiness reports
- adds `python -m pdelie.examples.data_ecosystem_feasibility` and `pdelie.examples.run_data_ecosystem_feasibility_example(...)`
- records the release decision `xarray_dataset_scalar_slice_supported_file_loaders_deferred`
- delegates Dataset conversion to the existing `from_xarray(...)` DataArray path after variable/mask selection, preserving the frozen scalar 1D periodic contract
- keeps metadata explicit for conversion; Dataset attrs are reported but never silently promoted into canonical metadata
- adds conservative report-only metadata suggestions for observed dims, coordinates, compatible variables, and domain length
- preserves existing `from_numpy(...)`, `from_xarray(...)`, field-readiness, confidence, downstream, split-provenance, weak-supportability, multi-generator diagnostics, and PDE strong paths

Explicitly deferred for this final release:

- file loaders such as NetCDF or Zarr readers
- PDEBench / The Well adapters
- broad dataset adapter registry
- implicit metadata inference or PDE identity inference
- resampling, multidimensional support, nonuniform-grid support, and multivariable `FieldBatch` support
- train/test policy or leakage prevention
- KS runtime promotion
- neural/callable/operator APIs
- root export expansion
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.27.0

First final release for the frozen V0.27 multi-generator diagnostics decision.

- adds `python -m pdelie.examples.multi_generator_diagnostics` and `pdelie.examples.run_multi_generator_diagnostics_example(...)` as JSON-only diagnostic examples
- records the multi-generator decision `multi_generator_diagnostics_feasible_fitting_deferred`
- freezes the bracket convention `[X_i, X_j] = X_i · ∇X_j - X_j · ∇X_i`
- records structure constants as `[X_i, X_j] = sum_k C[i, j, k] X_k`
- updates closure diagnostics so well-formed rank-deficient families return diagnostic reports instead of raising solely due to redundant rows
- updates span diagnostics so rank-deficient or zero-rank well-formed comparisons return warning/failed reports instead of untyped crashes
- extends `validate_symmetry_candidate(...)` with `closure_required=True|False` for `GeneratorFamily` candidates
- ensures multi-row generator candidates with only algebraic closure evidence conclude at most `partially_validated`
- adds supplied-family diagnostics for closed affine, non-closed polynomial, rank-deficient, and basis-mismatch cases
- preserves existing single-generator translation fitting, verification, confidence reports, KdV/KS decision evidence, weak supportability, downstream contracts, split provenance, invariant/orbit diagnostics, formula-backed generator records, Fisher-KPP, and advection-diffusion paths

Explicitly deferred for this final release:

- public multi-generator PDE fitting
- multi-generator finite flows
- BCH composition
- exponential-map finite-flow integration
- multi-generator invariant charts
- multi-parameter orbit charts
- group-action atlas
- operator-facing APIs
- neural or callable generator APIs
- root export expansion
- broad adapters or file loaders
- multidimensional, multivariable, or nonuniform-grid support
- train/test policy or leakage prevention
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.26.0

First final release for the frozen V0.26 KS revisit decision.

- records the KS decision `current_no_go_reference_fallback`
- confirms the internal normalized KS fixture remains residual-feasible and verification-feasible
- records that translation fitting remains reference-fallback-backed, so public KS support is still not promotable
- adds test-only KS revisit evidence with residual, fit, verification, and generator confidence diagnostics
- adds a minimal test-only KS no-go reproduction matrix covering the frozen fixture, seed sweep, fit-epsilon sweep, and one resolution variant
- reserves `v0.26b` as the follow-up KS promotion release name if a future scope freeze accepts direct-SVD/no-fallback evidence
- documents that `confidence_label == "strong"` would not be sufficient for KS promotion without direct SVD in tolerance and `reference_fallback_used is False`
- keeps `API_STABILITY.md` free of stable KS runtime contracts
- preserves existing Heat/Burgers strong paths, weak Heat/Burgers residual reports, weak supportability reporting, normalized short-horizon KdV, Fisher-KPP reaction-diffusion, advection-diffusion, invariant/orbit diagnostics, candidate validation, formula-backed generator records, confidence reports, readiness reports, downstream contracts, split provenance diagnostics, and KdV scope decision evidence

Explicitly deferred for this final release:

- public KS data generator
- public KS residual evaluator
- public KS vertical-slice or status example
- residual-only KS public API
- weak KS APIs
- custom KS initial-condition APIs
- configurable KS coefficient APIs
- broad KS regime support
- root KS exports
- broad adapters or file loaders
- multidimensional, multivariable, or nonuniform-grid support
- train/test policy or leakage prevention
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.25.0

First final release for the frozen V0.25 KdV scope decision.

- adds `python -m pdelie.examples.kdv_scope_decision` and `pdelie.examples.run_kdv_scope_decision_example(...)` as JSON-only runtime smoke examples
- records the KdV decision `keep_public_kdv_surface_frozen`
- keeps the existing normalized scalar 1D periodic short-horizon KdV strong path stable and direct-SVD-backed
- reports public KdV evidence through readiness, residual, fit diagnostics, verification, candidate validation, and generator confidence summaries
- freezes KdV decision evidence categories `current_frozen_supported`, `diagnostic_only`, and `deferred_no_go`
- adds test-only KdV scope matrix coverage for longer horizons, larger amplitudes, more Fourier modes, custom initial-condition rollout determinism, and configurable-coefficient sign/scaling
- adds test-only weak KdV identity checks for a stronger boundary-regular candidate profile
- preserves the no-go that the frozen quartic bump is not sufficient for honest third-order weak KdV
- documents the new example and decision in `API_STABILITY.md` as submodule-only runtime surface with no root export
- preserves existing Heat/Burgers strong paths, weak Heat/Burgers residual reports, weak supportability reporting, normalized short-horizon KdV, Fisher-KPP reaction-diffusion, advection-diffusion, invariant/orbit diagnostics, candidate validation, formula-backed generator records, confidence reports, readiness reports, downstream contracts, and split provenance diagnostics

Explicitly deferred for this final release:

- custom KdV initial-condition public APIs
- configurable KdV coefficient public APIs
- general KdV support outside the frozen normalized periodic short-horizon regime
- weak KdV APIs
- weak derivative backend
- WSINDy
- weak sparse recovery
- KS runtime promotion
- broad adapters or file loaders
- multidimensional, multivariable, or nonuniform-grid support
- train/test policy or leakage prevention
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.24.0

First final release for the frozen V0.24 weak-form supportability reset.

- adds `pdelie.reporting.summarize_weak_form_supportability(...)` for JSON-compatible report-only supportability summaries over existing weak residual reports, weak contracts, strong residual evidence, robustness/imported-parity diagnostics, and internal feasibility summaries
- adds `python -m pdelie.examples.weak_form_supportability` and `pdelie.examples.run_weak_form_supportability_example(...)` as JSON-only runtime smoke examples
- freezes `summary_type == "weak_form_supportability"` with supportability labels `supported_existing_slice`, `diagnostic_only`, `failed`, and `insufficient_evidence`
- defines `supported_existing_slice` narrowly as the existing frozen public Heat/Burgers weak residual report surface, not a general weak backend or weak discovery claim
- normalizes weak contract metadata including equation, equation form, test-function family/order, supported operator order, integration-by-parts depth, boundary vanishing order, patch shape/stride, quadrature rule, normalization, valid-window policy, row count, skipped-patch count, and finite-value policy
- records quadrature in every weak supportability report and validates strict JSON compatibility with `allow_nan=False`
- adds test-only, identity-first Fisher-KPP weak feasibility diagnostics covering constant-field, pure-time, pure-space Fourier integration-by-parts, manufactured smooth-field, generated-field sanity, quadrature tolerance, and no-public-export guards
- keeps Fisher-KPP weak feasibility diagnostic-only and out of package runtime examples except for a static JSON-compatible marker
- documents the new helper in `API_STABILITY.md` as a submodule-only runtime API with no root export
- preserves existing split provenance, downstream discovery contracts, external-data readiness, confidence reports, Heat/Burgers strong paths, weak Heat/Burgers residual reports, normalized periodic KdV, Fisher-KPP reaction-diffusion strong path, advection-diffusion strong path, invariant/orbit diagnostics, orbit batches, candidate validation, and formula-backed generator support

Explicitly deferred for this final release:

- WSINDy
- weak design matrices
- weak sparse recovery
- public weak derivative backend or `DerivativeBatch.backend = "weak"` promotion
- weak KdV APIs
- weak KS APIs
- public weak reaction-diffusion APIs
- weak residual evaluator subclasses
- new PDE support
- KS runtime promotion
- broad adapters or file loaders
- multidimensional, multivariable, or nonuniform-grid support
- train/test policy or leakage prevention
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.23.0

First final release for the frozen V0.23 split/leakage provenance diagnostics slice.

- adds `pdelie.reporting.summarize_split_leakage_provenance(...)` for JSON-compatible report-only diagnostics over user-supplied partitions and available source/shift provenance
- extends `pdelie.reporting.summarize_downstream_discovery_workflow(...)` with optional `split_provenance`
- adds `python -m pdelie.examples.split_leakage_provenance` and `pdelie.examples.run_split_leakage_provenance_example(...)` as JSON-only runtime smoke examples
- freezes `summary_type == "split_leakage_provenance"` with risk labels `no_detected_overlap`, `traceable_overlap`, `missing_provenance`, and `inconclusive`
- validates non-empty partition labels, sample counts, orbit-batch provenance reports, source IDs, sample metadata, and strict JSON compatibility
- reports source overlap, same-source/same-shift overlap, identity-shift overlap, partition-pair diagnostics, component statuses, and risk reasons
- accepts existing `OrbitBatchResult` objects and `uniform_translation_orbit_batch` report mappings without returning transformed `FieldBatch` objects
- documents the new helper in `API_STABILITY.md` as a submodule-only runtime API with no root export
- preserves existing Heat/Burgers strong paths, weak residual reports, normalized periodic KdV, Fisher-KPP reaction-diffusion, advection-diffusion, external data readiness, confidence reports, downstream discovery contracts, invariant/orbit diagnostics, orbit batches, candidate validation, and formula-backed generator support

Explicitly deferred for this final release:

- split creation or train/test split management
- leakage prevention or benchmark policy
- downstream success criteria
- automatic augmentation policy
- file loaders
- `xarray.Dataset` support
- PDEBench or The Well adapters
- broad dataset adapter framework
- multidimensional, multivariable, or nonuniform-grid support
- new PDE support
- KS runtime promotion
- weak-form expansion
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.22.0

First final release for the frozen V0.22 downstream discovery contracts slice.

- adds `pdelie.discovery.summarize_discovery_bridge_output(...)` for JSON-compatible summaries over downstream bridge arrays
- adds `pdelie.discovery.summarize_discovery_result(...)` for compact backend-neutral discovery-result and recovery summaries
- adds `pdelie.reporting.summarize_downstream_discovery_workflow(...)` for composing readiness, confidence, orbit-batch, bridge, and discovery-result reports
- adds `python -m pdelie.examples.downstream_discovery_contracts` and `pdelie.examples.run_downstream_discovery_contracts_example(...)` as JSON-only runtime smoke examples
- freezes `summary_type == "discovery_bridge_output"`, `summary_type == "discovery_result"`, and `summary_type == "downstream_discovery_workflow"`
- validates finite 2D trajectory arrays, shared trajectory shapes, strictly increasing time values, unique feature names, and JSON-compatible provenance
- summarizes coefficient arrays by shape, finite status, norms, and nonzero counts without copying full coefficient matrices into reports
- supports optional feature-keyed recovery summaries through `evaluate_discovery_recovery(...)`
- reports orbit-batch source/shift provenance traceability without detecting leakage or managing splits
- documents the new helpers in `API_STABILITY.md` as submodule-only runtime APIs with no root exports
- preserves existing Heat/Burgers strong paths, weak residual reports, normalized periodic KdV, Fisher-KPP reaction-diffusion, advection-diffusion, confidence reports, external data readiness, invariant/orbit diagnostics, orbit batches, candidate validation, and formula-backed generator support

Explicitly deferred for this final release:

- split management or heldout-leakage detection
- downstream augmentation policy
- a general discovery-backend framework
- manuscript benchmark thresholds
- file loaders
- `xarray.Dataset` support
- PDEBench or The Well adapters
- broad dataset adapter framework
- multidimensional, multivariable, or nonuniform-grid support
- new PDE support
- KS runtime promotion
- weak-form expansion
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.21.0

First final release for the frozen V0.21 external data readiness report slice.

- adds `pdelie.reporting.summarize_field_batch_readiness(...)` for JSON-compatible readiness reports over canonical `FieldBatch` inputs
- adds `python -m pdelie.examples.external_data_readiness` and `pdelie.examples.run_external_data_readiness_example(...)` as JSON-only runtime smoke examples
- freezes `summary_type == "field_batch_readiness"` with readiness labels `ready`, `needs_attention`, and `not_ready`
- reuses component statuses `passed`, `warning`, `failed`, `not_configured`, and `unavailable`
- reports canonical dims/shape, finite values, mask state, time/x coordinate compatibility, metadata completeness, optional expected-equation matching, conservative metadata suggestions, and optional residual-evaluator preflight
- captures typed PDELie residual-preflight validation failures in the report while leaving unexpected exceptions visible
- demonstrates one ready `from_numpy(...)` Heat field, one metadata-incomplete field, and one residual-evaluator mismatch
- documents the new helper in `API_STABILITY.md` as a submodule-only runtime API with no root export
- preserves existing Heat/Burgers strong paths, weak residual reports, normalized periodic KdV, Fisher-KPP reaction-diffusion, advection-diffusion, confidence reporting, invariant/orbit diagnostics, orbit batches, candidate validation, and formula-backed generator support

Explicitly deferred for this final release:

- file loaders
- `xarray.Dataset` support
- PDEBench or The Well adapters
- broad dataset adapter framework
- multidimensional, multivariable, or nonuniform-grid support
- resampling APIs
- metadata mutation or PDE identity inference
- train/test split policy or heldout-leakage policy
- downstream discovery contracts
- new PDE support
- KS runtime promotion
- weak-form expansion
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.20.0

First final release for the frozen V0.20 unified generator confidence report slice.

- adds `pdelie.reporting.summarize_generator_confidence(...)` for JSON-compatible categorical confidence reports over residual, generator, fit-diagnostic, verification, candidate-validation, coverage, consistency, orbit, threshold, and extra-metric evidence
- adds `python -m pdelie.examples.generator_confidence_report` and `pdelie.examples.run_generator_confidence_report_example(...)` as JSON-only runtime smoke examples
- freezes `summary_type == "generator_confidence"` with categorical labels `strong`, `qualified`, `failed`, and `insufficient_evidence`
- freezes component statuses `passed`, `warning`, `failed`, `not_configured`, and `unavailable`
- supports caller-configured thresholds for residual max/RMS, verification first/max error, and coverage fraction
- demonstrates one strong direct-SVD Heat case and one qualified partial formula-candidate validation case
- documents the new helper in `API_STABILITY.md` as a submodule-only runtime API with no root export
- preserves existing Heat/Burgers strong paths, weak residual reports, normalized periodic KdV, Fisher-KPP reaction-diffusion, advection-diffusion, reporting helpers, invariant/orbit diagnostics, orbit batches, candidate validation, and formula-backed generator support

Explicitly deferred for this final release:

- scalar confidence scores
- benchmark success policy
- train/test split policy or heldout-leakage policy
- transformed `FieldBatch` collections from reporting helpers
- canonical confidence objects
- new PDE support
- KS runtime promotion
- weak-form expansion
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, or nonuniform-grid support
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.19.0

First final release for the frozen V0.19 constant-coefficient advection-diffusion strong path.

- adds `pdelie.data.generate_advection_diffusion_1d_field_batch(...)` for deterministic synthetic scalar 1D periodic constant-coefficient advection-diffusion fields
- adds `pdelie.residuals.AdvectionDiffusionResidualEvaluator` for the strong residual `u_t + c*u_x - nu*u_xx = 0`
- adds `python -m pdelie.examples.advection_diffusion_vertical_slice` and `pdelie.examples.run_advection_diffusion_vertical_slice_example(...)` as JSON-only runtime smoke examples
- freezes the equation tag `advection_diffusion_constant_coefficient` with `c` and `nu` metadata
- uses exact periodic Fourier evolution for the synthetic rollout
- verifies the frozen vertical slice with direct SVD translation evidence, no reference fallback, residual max around `5.51e-5`, residual RMS around `8.44e-6`, and exact held-out verification
- documents the new APIs in `API_STABILITY.md` as submodule-only runtime APIs with no root exports
- preserves prior Heat/Burgers strong paths, weak residual reports, normalized periodic KdV, Fisher-KPP reaction-diffusion, reporting helpers, invariant/orbit diagnostics, orbit batches, candidate validation, and formula-backed generator support

Explicitly deferred for this final release:

- variable-coefficient advection-diffusion
- reaction-advection-diffusion
- weak advection-diffusion
- public custom advection-diffusion initial-condition APIs
- KS runtime promotion
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, or nonuniform-grid support
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- train/test policy, split management, or heldout-leakage detection
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.18.0

First final release for the frozen V0.18 Fisher-KPP reaction-diffusion strong path.

- adds `pdelie.data.generate_reaction_diffusion_1d_field_batch(...)` for deterministic synthetic scalar 1D periodic Fisher-KPP fields
- adds `pdelie.residuals.ReactionDiffusionResidualEvaluator` for the strong residual `u_t - nu*u_xx - rho*u*(1-u) = 0`
- adds `python -m pdelie.examples.reaction_diffusion_vertical_slice` and `pdelie.examples.run_reaction_diffusion_vertical_slice_example(...)` as JSON-only runtime smoke examples
- freezes the equation tag `reaction_diffusion_fisher_kpp` with `nu` and `rho` metadata
- verifies the frozen vertical slice with direct SVD translation evidence, no reference fallback, residual max around `1.07e-5`, residual RMS around `1.22e-6`, and exact held-out verification
- documents the new APIs in `API_STABILITY.md` as submodule-only runtime APIs with no root exports
- preserves prior Heat/Burgers strong paths, weak residual reports, normalized periodic KdV, reporting helpers, invariant/orbit diagnostics, orbit batches, candidate validation, and formula-backed generator support

Explicitly deferred for this final release:

- advection-diffusion
- KS runtime promotion
- weak reaction-diffusion
- public custom initial-condition APIs
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, or nonuniform-grid support
- neural or callable generator APIs
- operator-facing APIs
- train/test policy, split management, or heldout-leakage detection
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.17.0

First final release for the frozen V0.17 formula-backed generator interoperability slice.

- adds `pdelie.symmetry.FormulaGeneratorFamily` as a runtime-only structured record for formula-backed scalar 1D Lie-point generator families
- adds `pdelie.reporting.summarize_formula_generator_family(...)` for JSON-compatible formula metadata summaries
- extends `pdelie.symmetry.validate_symmetry_candidate(...)` to accept `FormulaGeneratorFamily` objects and strict current formula payload mappings
- distinguishes formula candidates with `candidate_kind == "formula_generator_family"`
- freezes a safe JSON expression AST with `const`, `var`, `add`, `mul`, integer `pow`, `sin`, `cos`, `reciprocal`, and metadata-only `symbolic_reference`
- reports finite formula-evaluation diagnostics and denominator-floor failures without executing arbitrary strings or callables
- reuses existing invariant-map residual/inverse validation when a supported finite-transform spec is attached
- adds `python -m pdelie.examples.formula_generator_validation` and `pdelie.examples.run_formula_generator_validation_example(...)` as runtime smoke examples
- documents the new APIs in `API_STABILITY.md` as submodule-only runtime APIs with no root exports
- preserves existing polynomial `GeneratorFamily`, `GeneratorFamily`/`InvariantMapSpec` candidate validation, Heat/Burgers strong paths, weak residual reports, normalized periodic KdV, reporting helpers, orbit diagnostics, orbit batches, and external candidate validation

Explicitly deferred for this final release:

- Python callable generator APIs
- arbitrary executable formula-string parsing
- neural symmetry-detector training or learned-generator classes
- formula-derived finite-flow integration for arbitrary infinitesimal formulas
- canonical `GeneratorFamily` schema changes
- train/test policy, split management, or heldout-leakage detection
- time-translation APIs or `axis="time"` support
- new PDE support
- stable KS data generator, residual evaluator, vertical-slice example, imported parity, weak API, or root KS exports
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.16.0

First final release for the frozen V0.16 external symmetry-candidate validation slice.

- adds `pdelie.symmetry.validate_symmetry_candidate(...)` for JSON-compatible empirical validation reports over externally supplied symmetry candidates
- accepts `GeneratorFamily`, canonical `GeneratorFamily` payload mappings, `InvariantMapSpec`, and canonical `InvariantMapSpec` payload mappings
- distinguishes `candidate_kind == "generator_family"` from `candidate_kind == "invariant_map_spec"` in every report
- defines `validated` as configured empirical validation under the supplied field, residual evaluator, epsilons, and optional reference, not a mathematical proof of symmetry
- reuses existing finite-transform verification, span comparison, closure diagnostics, invariant application, and reporting helpers without changing their behavior
- adds `python -m pdelie.examples.symmetry_candidate_validation` and `pdelie.examples.run_symmetry_candidate_validation_example(...)` as runtime smoke examples
- documents the new helper in `API_STABILITY.md` as a submodule-only runtime API with no root export
- preserves the prior Heat/Burgers strong paths, `v0.8` weak residual report APIs, `v0.9` normalized periodic KdV strong path, `v0.10` reporting helpers, `v0.11` order-4 derivatives, `v0.12` fit diagnostics, `v0.13` orbit/coverage diagnostics, `v0.14` invariant workflow summaries, and `v0.15` orbit batch materialization

Explicitly deferred for this final release:

- callable transform descriptors and arbitrary external executable candidates
- neural symmetry-detector training or learned-generator classes
- formula-backed or non-polynomial generator families
- train/test policy, split management, or heldout-leakage detection
- time-translation APIs or `axis="time"` support
- new PDE support
- stable KS data generator, residual evaluator, vertical-slice example, imported parity, weak API, or root KS exports
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.15.0

First final release for the frozen V0.15 materialized uniform translation orbit batch slice.

- adds `pdelie.invariants.build_uniform_translation_orbit_batch(...)` for materializing finite uniform `x`-translation orbit batches from canonical scalar 1D periodic `FieldBatch` inputs
- adds `pdelie.invariants.OrbitBatchResult` as a runtime-only structured result containing the materialized `FieldBatch` and a JSON-compatible provenance report
- preserves raw shift order and duplicate shifts, appends along the batch dimension in shift-major order, and records optional source/shift indices
- records aggregate orbit-materialization metadata and one aggregate preprocess-log entry on the output field
- adds `python -m pdelie.examples.translation_orbit_batch` and `pdelie.examples.run_translation_orbit_batch_example(...)` as runtime smoke examples for Heat and KdV orbit batches
- documents the new helper in `API_STABILITY.md` as a submodule-only runtime API with no root exports
- tightens public-surface guards so train/test policy, split management, time translation, KS APIs, weak KS, broad adapters, and root runtime exports remain absent
- updates CI to the compact current `v0_15-release-gate` while preserving full editable tests and package smoke
- preserves the prior Heat/Burgers strong paths, `v0.8` weak residual report APIs, `v0.9` normalized periodic KdV strong path, `v0.10` reporting helpers, `v0.11` order-4 derivatives, `v0.12` fit diagnostics, `v0.13` orbit/coverage diagnostics, and `v0.14` invariant workflow summaries

Explicitly deferred for this final release:

- train/test policy, split management, or heldout-leakage detection
- sparse-discovery branch policy or private-paper augmentation recipes
- time-translation APIs or `axis="time"` support
- new PDE support
- stable KS data generator, residual evaluator, vertical-slice example, imported parity, weak API, or root KS exports
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.14.0

First final release for the frozen V0.14 invariant workflow summary and read-only translation orbit report slice.

- adds `pdelie.reporting.summarize_invariant_workflow(...)` for JSON-compatible runtime summaries that combine coverage, consistency, orbit, generator, fit-diagnostic, verification, and extra-metric reports
- adds `pdelie.invariants.summarize_uniform_translation_orbit(...)` for read-only uniform `x`-translation orbit reports over canonical scalar 1D periodic `FieldBatch` inputs
- adds `python -m pdelie.examples.invariant_workflow_summary` and `pdelie.examples.run_invariant_workflow_summary_example(...)` as runtime smoke examples combining Heat, KdV, coverage, orbit, fit, and verification summaries
- documents the new helpers in `API_STABILITY.md` as submodule-only runtime APIs with no root exports
- tightens public-surface guards so augmentation, orbit datasets, time translation, KS APIs, weak KS, broad adapters, and root runtime exports remain absent
- updates CI to the compact current `v0_14-release-gate` while preserving full editable tests and package smoke
- preserves the prior Heat/Burgers strong paths, `v0.8` weak residual report APIs, `v0.9` normalized periodic KdV strong path, `v0.10` reporting helpers, `v0.11` order-4 derivatives, `v0.12` fit diagnostics, and `v0.13` orbit/coverage diagnostics

Explicitly deferred for this final release:

- augmented datasets or orbit dataset builders
- transformed `FieldBatch` collections from reporting helpers
- time-translation APIs or `axis="time"` support
- new PDE support
- stable KS data generator, residual evaluator, vertical-slice example, imported parity, weak API, or root KS exports
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- private-paper experiment policy, tables, figures, thresholds, or branch logic
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.13.0

First final release for the frozen V0.13 public orbit and coverage diagnostics slice.

- adds `pdelie.invariants.compute_periodic_window_coverage(...)` for JSON-compatible grid-point periodic-window coverage diagnostics under the frozen field-shift-then-fixed-window convention
- adds `pdelie.invariants.diagnose_uniform_translation_consistency(...)` for JSON-compatible uniform-translation consistency diagnostics over canonical scalar 1D periodic `FieldBatch` inputs
- adds `python -m pdelie.examples.orbit_coverage_diagnostics` and `pdelie.examples.run_orbit_coverage_diagnostics_example(...)` as runtime smoke examples for the diagnostics
- documents the diagnostics in `API_STABILITY.md` as submodule-only runtime APIs with no root exports
- tightens public-surface guards so augmentation, orbit-view builders, KS APIs, weak KS, broad adapters, and root runtime exports remain absent
- updates CI to the compact current `v0_13-release-gate` while preserving full editable tests and package smoke
- preserves the prior Heat/Burgers strong paths, `v0.8` weak residual report APIs, `v0.9` normalized periodic KdV strong path, `v0.10` reporting helpers, `v0.11` order-4 derivatives, and `v0.12` fit diagnostics

Explicitly deferred for this final release:

- new PDE support
- stable KS data generator, residual evaluator, vertical-slice example, imported parity, weak API, or root KS exports
- public augmentation utilities
- public orbit-view builders
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- private-paper experiment policy, tables, figures, thresholds, or branch logic
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.12.0

First final release for the frozen V0.12 diagnostics and supportability hardening slice.

- adds `pdelie.reporting.summarize_generator_fit_diagnostics(...)` for JSON-compatible summaries of generator-fit diagnostics, singular values, condition number, selected/SVD span distances, fallback status, and evidence labels
- enriches `fit_translation_generator(...)` diagnostics without changing coefficient selection or fitting behavior
- adds internal KS diagnostic sweep evidence showing residuals and verification remain healthy while direct residual-based SVD fitting remains fallback-backed across frozen epsilons and cheap fixture variants
- adds internal orbit/coverage feasibility diagnostics over stable Heat and KdV fixtures, including periodic-window coverage and uniform-translation consistency checks
- tightens API stability and public-surface guards so KS, orbit/coverage, augmentation, weak KS, broad adapter, and root runtime exports remain absent
- updates CI to the compact current `v0_12-release-gate` while preserving full editable tests and package smoke
- preserves the prior Heat/Burgers strong paths, `v0.8` weak residual report APIs, `v0.9` normalized periodic KdV strong path, `v0.10` reporting helpers, and `v0.11` order-4 derivative API

Explicitly deferred for this final release:

- new PDE support
- stable KS data generator, residual evaluator, vertical-slice example, imported parity, weak API, or root KS exports
- public orbit/coverage helpers
- public augmentation utilities
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- manuscript-specific experiment logic, tables, figures, or thresholds
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.11.0

First final release for the frozen V0.11 Kuramoto-Sivashinsky feasibility/no-go closeout.

- extends `pdelie.derivatives.compute_spectral_fd_derivatives(...)` with `max_spatial_order=4` and stable `u_xxxx` output while preserving the `max_spatial_order=2` default behavior
- adds internal KS feasibility coverage for the normalized strong form `u_t + u*u_x + u_xx + u_xxxx = 0`
- records strong internal KS residual, mass-conservation, and held-out canonical translation-verification evidence
- closes stable KS runtime promotion as no-go/defer for `v0.11` because the frozen fixture relies on `reference_fallback` rather than direct SVD in-tolerance fitting
- adds compact `v0_11-release-gate` CI visibility while preserving the full editable test suite and package smoke
- preserves the prior Heat/Burgers strong paths, `v0.8` weak residual report APIs, `v0.9` normalized periodic KdV strong path, and `v0.10` reporting helpers

Explicitly deferred for this final release:

- stable KS data generator
- stable KS residual evaluator
- KS vertical-slice example
- KS imported parity
- weak KS APIs
- root `pdelie` exports for KS runtime APIs
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- manuscript-specific experiment logic, tables, figures, or thresholds
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.10.0

First final release for the frozen V0.10 supportability and `v1.0` readiness slice.

- adds public runtime supportability helpers under `pdelie.reporting` for JSON-compatible summaries of residual batches, weak residual reports, generator families, verification reports, and vertical slices
- refactors Heat and KdV vertical-slice examples to emit the shared nested `vertical_slice` summary shape while keeping their command entrypoints unchanged
- adds focused API stability audit coverage and public-surface guards for stable submodule APIs, root-export boundaries, and explicitly deferred surfaces
- consolidates CI release-gate visibility to a single current `v0_10-release-gate` job while keeping historical release-gate tests runnable locally and covered by full editable tests
- preserves the prior Heat/Burgers strong paths, `v0.8` weak residual report APIs, `v0.9` normalized periodic KdV strong path, structured ingestion, and symmetry/discovery utilities

Explicitly deferred for this final release:

- new PDE support
- weak KdV APIs
- weak derivative APIs or broader weak-form expansion
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- manuscript-specific reporting logic, tables, figures, or thresholds
- new canonical reporting objects
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.9.0

First final release for the frozen V0.9 normalized periodic KdV strong path.

- extends `pdelie.derivatives.compute_spectral_fd_derivatives(...)` with `max_spatial_order=3` and stable `u_xxx` output while preserving the `max_spatial_order=2` default behavior
- adds `pdelie.data.generate_kdv_1d_field_batch(...)` for normalized periodic short-horizon synthetic KdV under the frozen v0.9 generator regime
- adds `pdelie.residuals.KdVResidualEvaluator` for the normalized strong-form residual `u_t + 6*u*u_x + u_xxx = 0`
- adds `python -m pdelie.examples.kdv_vertical_slice` and `pdelie.examples.run_kdv_vertical_slice_example(...)` as runtime smoke examples for the stable KdV path
- adds compact `v0_9-release-gate` CI visibility and representative KdV imported-parity checks
- preserves the prior `v0.8` weak residual report APIs and structured-ingestion / symmetry-discovery utility surface

Explicitly deferred for this final release:

- weak KdV APIs
- weak derivative APIs or broader weak-form expansion
- root `pdelie` exports for KdV runtime APIs
- custom KdV initial conditions or configurable KdV coefficients
- general KdV stability guarantees outside the frozen short-horizon release fixtures
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.8.0

First final release for the frozen V0.8 weak residual report core.

- adds `pdelie.residuals.evaluate_weak_heat_residual(...)` for deterministic window-indexed weak residual reports over canonical scalar 1D uniform periodic Heat `FieldBatch` data
- adds `pdelie.residuals.evaluate_weak_burgers_residual(...)` for deterministic window-indexed weak residual reports over canonical scalar 1D uniform periodic Burgers `FieldBatch` data
- adds a compact `v0_8-release-gate` CI visibility job and representative release-gate pytest module
- adds a frozen representative robustness layer for clean/noisy/coarse Heat/Burgers comparisons against the current spectral/analytic path
- preserves the prior `v0.7` structured-ingestion and symmetry/discovery runtime surface while adding the narrow `v0.8` weak residual report APIs

Explicitly deferred for this final release:

- weak derivatives
- weak `ResidualBatch` / `ResidualEvaluator` integration
- stable KdV promotion
- multidimensional, multivariable, or nonuniform-grid weak paths
- broader PDE, grid, or adapter expansion
- paper-specific experiment logic

## 0.7.0

First final release for the frozen V0.7 structured external-data ingestion core.

- adds `pdelie.data.from_numpy(...)` for strict runtime conversion of explicit NumPy/array-like 1D uniform rectilinear trajectory data into canonical `FieldBatch`
- adds `pdelie.data.from_xarray(...)` for strict runtime conversion of explicit `xarray.DataArray` 1D uniform rectilinear trajectory data into canonical `FieldBatch`
- adds native-vs-imported parity coverage across the current derivative, residual, symmetry-fit, verification, and discovery-bridge layers
- adds a compact `v0_7-release-gate` CI visibility job and representative release-gate pytest module
- preserves the frozen Heat/Burgers symmetry and discovery-utility surface from `v0.6` while extending the library to structured external ingestion

Explicitly deferred for this final release:

- `xarray.Dataset` support
- dim aliases
- static-field ingestion
- multidimensional external-data ingestion
- nonuniform-grid support
- metadata inference
- PDEBench-specific loaders
- The Well adapters
- HDF5, netCDF, or Zarr stable loaders
- weak-form methods
- operator methods
- stable KdV promotion
- paper-specific experiment logic

## 0.6.0

First final release for the frozen V0.6 symmetry-guided PDE discovery utilities core.

- adds runtime-only discovery recovery metrics under `pdelie.discovery.evaluate_discovery_recovery(...)`
- adds a thin runtime-only PySINDy backend-fit adapter under `pdelie.discovery.fit_pysindy_discovery(...)`
- adds runtime-only heuristic translation-canonical discovery inputs under `pdelie.discovery.build_translation_canonical_discovery_inputs(...)`
- adds deterministic robustness helpers under `pdelie.data` plus grouped recovery-grid summaries under `pdelie.discovery`
- adds a compact `v0_6-release-gate` CI visibility job and representative release-gate pytest module
- finalizes the frozen `v0.6` Heat/Burgers discovery-utility surface without promoting KdV

Explicitly deferred for this final release:

- stable KdV API or stable KdV runtime module
- external structured dataset ingestion
- weak-form methods
- operator methods
- broad discovery adapters or backend frameworks
- paper-specific experiment logic, figures, or manuscript tables

## 0.5.0

First final release for the frozen V0.5 portability and external-compatibility core.

- functionally identical to `0.5.0rc1` unless a release blocker required a minimal fix
- finalizes the `0.5.0rc1` release surface for the V0.5 portability slice

## 0.5.0rc1

First release candidate for the frozen V0.5 generator-family portability and external-compatibility core.

- stable manifest export/import helpers added under `pdelie.portability`
- strict external-family normalization added under `pdelie.portability.coerce_generator_family(...)`
- compact portability benchmark / semantic-preservation layer added for canonical, manifest, and narrow legacy translation inputs
- compact V0.5 release-gate layer and `v0_5-release-gate` CI visibility job added
- normalized periodic KdV feasibility passes in the tests-first slice, but KdV remains non-stable in `v0.5`
- package metadata, milestone docs, and release-readiness docs aligned with the implemented V0.5 state

Explicitly deferred for this release candidate:

- stable KdV API or stable KdV runtime module
- weak-form methods
- operator methods
- broad dataset adapters or interoperability expansion
- prediction-facing utility work
- new canonical stable objects beyond the current V0.5 slice

## 0.4.0

First final release for the frozen V0.4 stable core.

- finalizes the frozen V0.4 generator-family, algebra-diagnostics, and optional-visualization release surface

## 0.4.0rc1

First release candidate for the frozen V0.4 generator-family and algebra-diagnostics core.

- canonical `GeneratorFamily` family semantics finalized with `schema_version = "0.2"`, family-shaped coefficients, and explicit `basis_spec`
- runtime-only symbolic generator rendering added under `pdelie.symmetry`
- optional runtime-only SymPy component expressions added under `pdelie.symmetry`
- runtime-only span diagnostics added under `pdelie.symmetry`
- runtime-only closure / structure-constant diagnostics added under `pdelie.symmetry`
- optional Matplotlib visualization layer added under `pdelie.viz`
- explicit V0.4 release-gate pytest module and `v0_4-release-gate` CI visibility job added
- package metadata, README, milestone docs, and release-readiness docs aligned with the implemented V0.4 state

Explicitly deferred for this release candidate:

- weak-form methods
- operator methods
- broad adapters or interoperability expansion
- stable multi-generator PDE fitting
- broader downstream compatibility or prediction-facing workflows
- new canonical stable objects beyond the current V0.4 slice

## 0.3.0

First final release for the frozen V0.3 stable core.

- functionally identical to `0.3.0rc1` unless a release blocker required a minimal fix
- finalizes the `0.3.0rc1` release surface for the invariant/downstream utility slice

## 0.3.0rc1

First release candidate for the frozen V0.3 invariant/downstream utility core.

- stable canonical pipeline extended with `InvariantMapSpec`
- runtime-only `pdelie.invariants.InvariantApplier` added for the frozen single-generator periodic `x` uniform-translation path
- runtime-only `pdelie.discovery.to_pysindy_trajectories` added as the narrow backend-specific PySINDy bridge
- controlled four-branch downstream benchmark / release-gate layer added internally under frozen settings:
  `vanilla`, `known_invariant`, `discovered_invariant`, `nuisance`
- release metadata, package description, README, and release-readiness docs aligned with the implemented V0.3 state

Explicitly deferred for this release candidate:

- weak-form methods
- operator methods
- multi-generator invariant machinery
- broad adapters or interoperability expansion
- new canonical objects beyond the current V0.3 slice

## 0.2.0

First final release for the frozen V0.2 stable core.

- scientifically/functionally identical to `0.2.0rc1`
- final release metadata and release-readiness docs updated for `0.2.0`

## 0.2.0rc1

First release candidate for the frozen V0.2 stable core.

- extends the stable core from Heat-only to matched Heat and Burgers coverage
- stable pipeline remains:
  `FieldBatch -> DerivativeBatch -> ResidualBatch -> GeneratorFamily -> VerificationReport`
- synthetic 1D Burgers added as the second stable PDE under the existing contracts
- current translation fitting and finite-transform verification paths hardened across Heat and Burgers
- matched cross-PDE benchmark / release-gate layer added in the test surface under shared defaults and shared low-noise held-out conditions
- release metadata, packaging text, and user-facing docs aligned with the implemented V0.2 state

Explicitly deferred for this release candidate:

- invariant pipelines as a stable feature
- weak-form methods
- operator methods
- broad adapters or interoperability expansion
- new canonical objects beyond the current stable slice

## 0.1.0

First final release for the frozen V0.1 MVP slice.

- scientifically identical to `0.1.0rc1`
- final release metadata and release-readiness docs updated for `0.1.0`

## 0.1.0rc1

First release candidate for the frozen V0.1 MVP slice.

- stable V0.1 canonical objects implemented:
  `FieldBatch`, `DerivativeBatch`, `ResidualBatch`, `ResidualEvaluator`,
  `GeneratorFamily`, `VerificationReport`
- synthetic 1D heat-equation vertical slice implemented on a uniform periodic grid
- stable derivative backend `spectral_fd` implemented
- analytic heat residual evaluator implemented
- polynomial spatial-translation baseline implemented
- finite-transform verification path implemented
- README, packaged example module, editable-install path, and built-wheel smoke path aligned for release validation

Explicitly deferred for this release candidate:

- Burgers or any second PDE
- operator methods
- weak-form features
- broad adapters or interoperability expansion
- new canonical objects beyond the current V0.1 slice
