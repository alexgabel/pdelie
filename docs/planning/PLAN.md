# PDELie - Execution Plan (V0.33 — Nonperiodic Generators + Mask-Preserving Bridge, planning kickoff)

**Status:** PLANNING_FROZEN

`v0.33` closes two long-standing wedge gaps that the v0.30–v0.32 arc did not reach: the **nonperiodic generator gap** (`fit_translation_generator`, `verify_translation_generator`, and `polynomial_translation_svd` remain periodic-only despite v0.30 shipping nonperiodic `FieldBatch` readiness + boundary-condition metadata + strong-form nonperiodic residuals) and the **discovery-bridge mask leakage** (`run_pysindy_pde_task` applies the input mask before differentiation, so the derivative stencil widens the effective mask and the row-set the optimizer sees no longer matches the row-set PDELie audited). Both fit the wedge (empirical diagnostics on scalar 1D data) and do not require multi-D or new PDEs.

Decision label: `v0_33_nonperiodic_generators_and_mask_preserving_bridge`.

Design freeze: [`docs/design/V0_33_NONPERIODIC_GENERATORS_AND_MASK_PRESERVING_BRIDGE.md`](../design/V0_33_NONPERIODIC_GENERATORS_AND_MASK_PRESERVING_BRIDGE.md). Machine-readable scope: [`configs/planning/v0_33_scope.json`](../../configs/planning/v0_33_scope.json).

Sub-milestone structure (three focus items a/b/c + two parallel scope-widenings d/e + one consolidation, mirrors the v0.32 arc):

- **v0.33a** — Nonperiodic dispatch in `fit_translation_generator` and `polynomial_translation_svd`. Periodic path byte-preserved. New `boundary_condition_x` / `boundary_condition_dispatch_reason` / `interior_only_reduction_applied` / `interior_only_row_count` diagnostic keys.
- **v0.33b** — Overlap-crop finite-transform verification. `verify_translation_generator` grows a nonperiodic dispatch path; `VerificationReport.diagnostics` reports `dispatch_path`, `overlap_fraction`, `overlap_row_count`. Classification vocabulary unchanged (`{exact, approximate, failed}`). Delivers what v0.31.5 previously deferred.
- **v0.33c** — Mask-preserving discovery bridge. `run_pysindy_pde_task` gains `mask_application: Literal["before_differentiation", "after_differentiation"]` (default `"after_differentiation"`). New `fit_diagnostics.mask_application_stage` / `mask_row_count` / `unmasked_row_count` / `mask_row_count_reduction_from_derivative_stencil` keys. `discovery_task_result` top-level 22-key schema preserved.
- **v0.33d** (parallel scope-widening) — Variable-coefficient data-generator support. `generate_heat_1d_field_batch(..., diffusivity_profile=...)` and analogous kwargs on the Burgers + advection-diffusion generators. Profile provenance recorded in `field.metadata["parameter_tags"]` (`nu_profile_kind` + `nu_profile_hash` + `nu_min` / `nu_max` / `nu_l2_norm`). Constant-coefficient path byte-preserved. Delivers the **admissibility crash test** in v0.33 without waiting for the residual-side rework (which is v0.34a). Silverware residual-side `nu(x)` support explicitly out of scope for v0.33d.
- **v0.33e** (parallel hygiene) — Golden-numbers regression gate. Frozen per-PDE derivative + residual + vertical-slice numerical fixtures pinned into the release-gate at `tests/fixtures/v0_33e_golden_numbers.json` with a strict-JSON `pdelie_golden_numbers_fixture` schema; tight tolerances (`rtol=1e-6, atol=1e-12`); nonperiodic golden fixtures land alongside v0.33a. No unnamed drift permitted — every release-close PR either regenerates the fixture with a named cause in the CHANGELOG or fixes the regression.
- **v0.33.0** — Release close consolidation. Single tag consolidating v0.33a-e. Version bump `0.32.0` → `0.33.0`. `V0_33_RELEASE_READINESS.md`. `support_matrix.v0_33.json`. Release-gate manifest consolidated `0.33` row. CI job rename `v0_32_0-release-gate` → `v0_33_0-release-gate`.

Non-goals: no new PDE; no new symmetry method (Ko-sparse moves to v0.34+); no new `SymmetryCandidate` discriminator; no new `summary_type`; no `discovery_task_result` schema change (still 22 keys); no root export; no noise / WSINDy claim; no multi-D / 2D contract widening; no package version bump until v0.33.0 release close.

---

# PDELie - Execution Plan (V0.32.0 Release Close — Consolidated)

**Status:** COMPLETE — tag `v0.32.0` @ `8ec6e4e` on `origin/main`, cut 2026-07-27. See [`docs/releases/V0_32_RELEASE_READINESS.md`](../releases/V0_32_RELEASE_READINESS.md). No PyPI publication (Git-tag-only per policy).

Decision label: `v0_32_0_consolidated_modernization_and_external_readiness`.

`v0.32.0` consolidates the four v0.32 sub-milestones (v0.32a modern-runtime migration, v0.32b strict method-score/uncertainty/calibration reporting, v0.32c candidate-to-discovery workflow example, v0.32d external-data readiness cookbooks) under a single tag per the solo-dev consolidation policy. Version `0.31.0` → `0.32.0`. Release-close artifacts: `docs/releases/V0_32_RELEASE_READINESS.md`, `docs/specs/support_matrix.v0_32.json`, consolidated release-gate manifest row, CHANGELOG entry, CI job rename `v0_32-release-gate` → `v0_32_0-release-gate`, `release/v0.31.x` maintenance branch cut from the `v0.31.0` tag with a documented security-only 12-month maintenance-end policy.

Non-goals for the release-close pass itself: no new runtime feature, no new `summary_type`, no root export, no external-data recovery-benchmark claim, no generic symmetry-discovery claim, no PyPI/TestPyPI publication.

Release-close preflight (all done):

1. Modern env recreated on py3.12.13 (also py3.13.14); NumPy 2.5.1; PySINDy 2.1.0; h5py 3.16.0; scipy 1.18.0; sklearn 1.9.0.
2. Full pytest under modern env — 1430/1430 pass on py3.12 (post-preflight-additions), 1427/1427 pass on py3.13 (pre-preflight-additions run).
3. `run_pysindy_pde_task` multi-trajectory path verified end-to-end on `batch_size=4`; v0.32c workflow no longer performs silent first-trajectory slicing.
4. `[pdebench]` extra (h5py-only) added; v0.30 hygiene invariant vocabulary relaxed to include it; loader ImportError names the extra.
5. `evidence_conclusion.reasons` name the exact `downstream_comparison.metric_key`.
6. The Well scan distinguishes `paper_dataset_count = 16` from `catalogue_entry_count = 23`.

---

# PDELie - Execution Plan (V0.32d External-Data Readiness Cookbooks)

**Status:** COMPLETE (rolled into v0.32.0)

`v0.32d` ships two narrow external-data readiness cookbooks required for the v0.32 milestone: (1) an honest PDEBench 1D Burgers slice cookbook, and (2) a metadata-only The Well feasibility scan. Neither is a broad dataset adapter framework; neither makes a recovery benchmark claim.

Decision label: `v0_32d_pdebench_1d_burgers_readiness_and_the_well_feasibility_scan`.

Substantive changes:

- Preflight audit: PDEBench 1D Burgers V8 shard `1D_Burgers_Sols_Nu0.001.hdf5` (DaRUS `doi:10.18419/darus-2986`, CC-BY-4.0) with MD5 `b4be2fc3383f737c76033073e6d2ccfb`. Layout `(n_traj, T, X)` float32; datasets `/tensor`, `/x-coordinate`, `/t-coordinate`; periodic-in-x boundary; equation convention `u_t + u u_x = nu u_xx` — exact match with `pdelie.residuals.BurgersResidualEvaluator`. Frozen at `configs/external_data/pdebench_burgers_1d_readiness.json`.
- Preflight audit: The Well v1 (Ohana et al., NeurIPS 2024) — paper reports **16 datasets**; current PolymathicAI catalogue enumerates them as **23 hosted variants** (splits like `rayleigh_benard` + `rayleigh_benard_uniform`, `mhd_64` + `mhd_256`, `supernova_explosion_64` + `_128`, `turbulent_radiative_layer_2D` + `_3D`, `euler_multi_quadrants_periodic` + `_open_bc`). Every entry is 2D or 3D on a structured grid and either carries multiple physically coupled channels or is coupled through the geometry itself. NO honest scalar 1D slice exists. Frozen at `configs/external_data/the_well_feasibility_scan.json` with `conclusion = "blocked_multichannel_required"`; the emitted payload records both `paper_dataset_count` and `catalogue_entry_count` verbatim.
- New submodule-only cookbook `pdelie.examples.pdebench_burgers_1d_readiness` with `run_pdebench_burgers_1d_readiness_cookbook(cached_file_path=..., residual_preflight=...)` and a `__main__` CLI. Narrow loader: exact expected filename + MD5 checksum + HDF5 dataset-path verification + axis-shape validation + uniformity check + optional Burgers residual preflight (interior-only + full-grid diagnostics, `diagnostic_only=True`). Emits a strict-JSON `pdelie_external_data_readiness` report.
- New submodule-only scan `pdelie.examples.the_well_feasibility_scan` with `run_the_well_feasibility_scan()` and a `__main__` CLI. Metadata-only — no network I/O — emits a strict-JSON `pdelie_the_well_feasibility_scan` report with `conclusion = "blocked_multichannel_required"`.
- Optional dependency: `h5py`, installed via the narrow `[pdebench]` extra (`pip install 'pdelie[pdebench]'`). The extra is scoped to `h5py` only and does NOT imply broad PDEBench support. Absent the extra, all non-file paths of the cookbook (unavailable / config validation / checksum-mismatch on the wrong file) still work, and the loader raises an `ImportError` that names the extra explicitly.
- 20 v0.32d contract tests in `tests/test_v0_32d_external_data_readiness.py` covering: strict-JSON config + output; exact dataset identifier and checksum enforcement; wrong-checksum rejection; unknown-variable rejection; axis-mismatch rejection; missing-boundary-metadata blocks residual; missing-coefficient-metadata blocks residual; supported-cached-slice FieldBatch construction; no-train-test-policy-invented; no-recovery-claim in conclusion; optional-dataset absence nonfatal; no-bulk-network-download; The Well scan metadata-only; The Well conclusion `blocked_multichannel_required`; no broad root/data API leaks; citation/license/provenance present; strict-JSON NaN/Inf rejection; docs do NOT use broad "PDEBench support" / "The Well support" phrases; CLI JSON-only; release-gate manifest pins the narrow surface.

Non-goals: no broad `from_pdebench` / `from_the_well` adapter; no adapter registry; no automatic dataset-name inference; no broad PDEBench support claim; no recovery benchmark claim; no model training; no FNO/U-Net/PINN comparison; no external-data symmetry discovery claim; no The Well full-data download in CI; no multi-channel or 2D widening; no root API; no hidden train/test redefinition; no package version bump; no PyPI/TestPyPI publication.

---

# PDELie - Execution Plan (V0.32c Candidate-to-Discovery Workflow Example)

**Status:** IN_PROGRESS

`v0.32c` ships the first public candidate-to-downstream-task workflow example. It composes `FieldBatch → run_symmetry_method("polynomial_translation_svd") → SymmetryCandidate → validate_symmetry_candidate → verify_translation_generator → caller-configured periodic-translation orbit (train-only) → run_pysindy_pde_task (baseline + candidate-guided) → strict composed workflow evidence`, using only public submodule APIs. It is a controlled example, not a general workflow engine, benchmark harness, or automatic augmentation policy.

Decision label: `v0_32c_candidate_to_discovery_workflow_example`.

Substantive changes:

- New composed summary `pdelie.reporting.summarize_candidate_to_discovery_workflow` (`summary_type = "candidate_to_discovery_workflow"`). Composition audit (in-tree) established that no existing composed summary can natively carry the required 15 stages side-by-side; the new type nests existing per-stage summaries by their frozen `summary_type` and adds four glue-only fields: `action_policy`, `downstream_comparison`, `evidence_conclusion`, `scope_boundaries`.
- 15 explicit stages preserved in fixed order: `field_readiness`, `derivative_residual_evidence`, `symmetry_method_result`, `candidate_summary`, `generator_confidence` (optional), `candidate_validation`, `finite_transform_verification`, `action_policy`, `orbit_or_coverage_diagnostics`, `split_leakage_provenance`, `baseline_discovery_task`, `candidate_guided_discovery_task`, `downstream_comparison`, `evidence_conclusion`, `scope_boundaries`. Every stage is retained in the payload; unavailable / blocked / skipped stages carry a `candidate_to_discovery_workflow_stage_marker` payload rather than being silently omitted.
- New JSON-only example runner `pdelie.examples.candidate_to_discovery_workflow.run_candidate_to_discovery_workflow_example(scenario=...)` with two deterministic scenarios: `"successful"` (fully executable end-to-end) and `"valid_but_not_useful_static"` (all real stages run; the two discovery-task and comparison blocks are a provenance-backed static illustration marked `static_illustration=True`). Includes a `__main__` CLI that prints the payload as JSON.
- Action-policy separation: the discovered generator identifies a family/direction only; the caller supplies shifts, orbit cardinality, augmentation budget, and train/test policy explicitly. `explicitly_configured_by_caller=True` is a hard invariant; `False` is refused with a `SchemaValidationError`.
- Held-out and leakage policy: heldout FieldBatch is passed to `run_pysindy_pde_task(heldout_field=...)` for evaluation and is never fed through the orbit materializer; `action_policy.train_test_policy = "orbit_train_only_heldout_untransformed"`. Split/leakage provenance is emitted for every partition entry (never silently dropped).
- 20 v0.32c contract tests in `tests/test_v0_32c_candidate_to_task_workflow.py` covering: public-submodule-only imports, root-API cleanliness, exact stage order, stage retention on failure, strict-JSON round-trip, NaN/Inf adversarial rejection, validation/verification gating, explicit action-policy fields, no-inference-from-method-scores, heldout untransformed, split/leakage provenance, comparable baseline/candidate-guided configs, no silent stage exclusion, deterministic output, valid-but-not-useful honesty, no automatic best selection, CLI JSON-only, end-to-end example smoke, and scope-boundary non-claim vocabulary.

Non-goals: no new PDE; no new symmetry method; no root exports; no `SymmetryCandidate` discriminator change; no automatic candidate winner; no automatic shift-budget selection; no universal-downstream-benefit claim; no noise / nonperiodic / multi-D / external-data claim; no `discovery_task_result` schema modification; no held-out transformation; no silent stage exclusion; no package version bump.

---

# PDELie - Execution Plan (V0.32b Strict Method-Score, Uncertainty, and Calibration Reporting)

**Status:** IN_PROGRESS

`v0.32b` extends `pdelie.reporting.summarize_generator_confidence` with three additive optional fields — `method_scores`, `uncertainty_report`, `calibration_report` — and migrates the assembled generator-confidence payload to the strict-JSON validation boundary. The v0.20 `confidence_label` categorical vocabulary is unchanged; all three new fields default to `None`; existing callers without new arguments retain equivalent output semantics.

Decision label: `v0_32b_generator_confidence_additive_method_scores_uncertainty_calibration`.

Substantive changes:

- `summarize_generator_confidence` gains `method_scores`, `uncertainty_report`, `calibration_report` kwargs (all default `None`) and routes the assembled payload through `_validate_strict_json_compatible` instead of the permissive `_validate_json_compatible`. NaN/Inf raise `SchemaValidationError` at every nested level.
- New submodule-only helper `pdelie.reporting.enrich_method_scores(values, metadata)` composes a plain `dict[str, float | None]` (from `SymmetryMethodResult.method_scores`) with a frozen `SCORE_METADATA` map into the enriched-form dict accepted by the report.
- The built-in `polynomial_translation_svd` method_scores now uses the **frozen four names**: `span_distance` (lower_is_better), `residual_l2` (lower_is_better), `error_curve_max` (diagnostic_only), `svd_condition_number` (diagnostic_only). Underlying diagnostics semantic mapping: `span_distance ← selected_span_distance`; `residual_l2` = L2 norm of the residual field; `error_curve_max = max(basis_delta_norms.values())`; `svd_condition_number ← condition_number`. The class-level `SCORE_METADATA` attribute exposes direction/description/units for the enrichment helper. `SymmetryMethodResult.method_scores` remains a plain `dict[str, float | None]` for backward compatibility with the v0.30.1 registry contract.
- New method-specific helper `pdelie.symmetry.methods.polynomial_translation_svd.bootstrap_uncertainty(field, residual_evaluator, *, seed, num_resamples=64, interval_level=0.95, min_units=8, resampling_unit="batch")`. Batch (trajectory) resampling only; `resampling_unit="row"` raises `ScopeValidationError`. Seeded and deterministic; each resample re-runs the full underlying fit; failed resamples are counted, not silently retried. Below `min_units`, intervals are all None with an explicit `insufficient_independent_units` warning. `diagnostic_only=True`.
- New tests: `tests/test_v0_32b_method_scores_uncertainty.py` (20 named cases covering backward compatibility, three-field validation, direction vocabulary, strict-JSON round-trip, built-in coverage, bootstrap determinism, insufficient-units warning, row-bootstrap refusal).
- Design frozen at `docs/design/GENERATOR_CONFIDENCE_ADDITIVE_FIELDS.md` and `configs/planning/v0_32_method_scores_scope.json`.

Non-goals: no scalar aggregate confidence probability; no reinterpretation of method-native scores as probabilities; no bootstrap intervals renamed to Bayesian posterior intervals; no new symmetry method; no root exports; no `SymmetryCandidate` discriminator semantic change; no noise-robustness claim; no package version bump; no tag; no PyPI/TestPyPI publication.

---

# PDELie - Execution Plan (V0.32a Modern Runtime Migration)

**Status:** IN_PROGRESS

`v0.32a` migrates the active development line from Python 3.11 + NumPy 1.x + PySINDy 1.7.5 to Python ≥3.12 + NumPy 2.x + PySINDy 2.1.x per the v0.31.1a research spike's outcome A (modern-only future line). It deletes the private prototype from that spike, retires the v0.31c1 `setuptools<82` cap, and hardens the reserved-`SymmetryCandidate`-representation construction path from a warning-gated placeholder to a hard `ScopeValidationError`.

Decision label: `v0_32_modernization_outcome_A_modern_only_future_line`.

Substantive changes:

- pyproject.toml: `requires-python>=3.12`, `numpy>=2,<3`, `pysindy>=2.1,<3`, `scikit-learn>=1.4,<2`, `scipy>=1.14,<2`; the v0.31c1 `setuptools<82` cap is REMOVED (pysindy 2.x uses `importlib.metadata`).
- PySINDy 2.x runtime migration across `src/pdelie/discovery/pysindy_adapter.py`, `src/pdelie/discovery/pysindy_bridge.py`, `src/pdelie/discovery/_pysindy_defaults.py`, `src/pdelie/tasks/discovery.py`, `src/pdelie/tasks/weak_pde_library.py`, `src/pdelie/examples/downstream_discovery_task_bridge.py`, and `tests/_helpers/downstream_benchmark.py`. Six documented API breaks absorbed (SINDy ctor kwargs removed, SINDy.fit kwargs removed + `t` positional-required, SINDy.differentiate removed → `model.differentiation_method(x, t)`, SINDy.model removed, STLSQ.fit_intercept removed, PDELibrary/WeakPDELibrary require `function_library=<BaseFeatureLibrary>`).
- `SymmetryCandidate` reserved-type hardening: public construction of `matrix_lie_algebra` / `coordinate_vector_field` / `finite_transform_spec` / `latent_generator_reference` now raises `ScopeValidationError` (was warning-gated placeholder).
- Deletions: `_pysindy2_prototype.py`, `test_pysindy_2_migration_prototype.py`, `test_v0_31b3_pysindy_compatibility_policy.py`, `test_v0_31c1_downstream_packaging_policy.py`.
- New tests: `tests/test_v0_32a_modern_runtime.py` (20+ named tests).
- CI: `v0_31-release-gate` → `v0_32-release-gate` (matrix Python 3.12/3.13); `editable-tests` matrixed; new `py314-core-only-advisory` job; `setuptools<81` co-install workaround removed.

Non-goals: no PySINDy 1.x production support on main, no dual-generation shim, no schema changes on `discovery_task_result` (22 keys) or `pdelie_weak_pde_library_diagnostic` (27 keys), no new symmetry method, no nonperiodic discovery, no external dataset support, no new PDE, no noise/WSINDy claim, no root exports, no package version bump, no tag.

Follow-up milestones in v0.32 arc: v0.32b (method_scores + uncertainty_report + calibration_report), v0.32c (composed workflow example), v0.32d (PDEBench readiness cookbook), v0.32.0 (release close — single tag).

---

# PDELie - Execution Plan (V0.30.1 SymmetryMethod Registry MVP)

**Status:** IN_PROGRESS

`v0.30.1` is a submodule-only extensibility-foundation release. It introduces:

- The representation-neutral :class:`SymmetryCandidate` contract with seven reserved discriminators (three implemented, four reserved-only).
- The lazy :class:`SymmetryMethod` registry + :class:`SymmetryMethodResult` + :class:`SymmetryMethodSpec`.
- One built-in adapter — ``polynomial_translation_svd`` — that wraps :func:`pdelie.symmetry.fitting.translation_baseline.fit_translation_generator` without changing its numerics.

**No external symmetry method is added.** Ko-style, LieGAN, LaLiGAN, and LieGG remain deferred to their own scope-freeze designs.

Per the solo-dev consolidation policy adopted after the v0.30.1 code review, this sub-release is a milestone name only — its code ships publicly as part of `v0.32.0` and no `v0.30.1` tag is created.

submodule_only_symmetry_method_registry_mvp_plus_symmetry_candidate_contract
```

## Architectural rule

External methods GENERATE candidates. PDELie verification determines EVIDENCE. Candidate generation, candidate validation, and downstream utility remain distinct stages. The registry deliberately does NOT rank candidates, does NOT expose a ``best`` accessor, and does NOT call arbitrary method-native scores "confidence" — the field name is ``method_scores`` and values are finite floats or ``None``.

## Sub-release contents (v0.30.1)

- ``src/pdelie/symmetry/candidates.py`` — ``SymmetryCandidate``, ``build_symmetry_candidate``, ``summarize_symmetry_candidate``, ``REPRESENTATION_TYPES``.
- ``src/pdelie/symmetry/registry.py`` — ``SymmetryMethod`` (Protocol), ``SymmetryMethodMetadata``, ``SymmetryMethodResult``, ``SymmetryMethodSpec``, ``register_symmetry_method``, ``get_symmetry_method``, ``list_symmetry_methods``, ``run_symmetry_method``, ``summarize_symmetry_method_result``.
- ``src/pdelie/symmetry/methods/__init__.py`` — deliberately empty (no eager adapter import).
- ``src/pdelie/symmetry/methods/polynomial_translation_svd.py`` — built-in adapter.
- ``tests/test_symmetry_candidate_contract.py`` (30 tests).
- ``tests/test_symmetry_method_registry.py`` (16 tests).
- ``tests/test_polynomial_translation_svd_method.py`` (15 tests).
- ``docs/design/SYMMETRY_METHOD_REGISTRY.md`` — the full design.
- Extended ``pdelie.symmetry`` ``__init__.py`` re-exports (submodule-only surface).

Explicit non-goals for v0.30.1:

- No external symmetry method port. No Ko-style, LieGAN, LaLiGAN, LieGG code.
- No PyTorch dependency.
- No root ``pdelie.discover_symmetries`` API.
- No root exports for any registry function.
- No file-path input. No ndarray/xarray coercion in the symmetry API.
- No ``ArenaResult.best``, no automatic ranking, no winner selection.
- No ``method_confidence`` field on any registry output.
- No NaN or Inf in any summary output.
- No change to ``GeneratorFamily`` semantics or ``validate_symmetry_candidate`` semantics.
- No multi-D expansion, no new finite-transform implementation.
- No package version bump. No tag.

Lazy-import guarantee:

Importing ``pdelie.symmetry`` and ``pdelie.symmetry.methods`` does NOT load any adapter module. ``list_symmetry_methods()`` returns metadata without importing any adapter. ``get_symmetry_method(name)`` and ``run_symmetry_method(name, ...)`` are the only paths that resolve the adapter module (via ``importlib.import_module``). Failed imports raise ``ScopeValidationError`` with an actionable "pip install pdelie[<extras>]" hint.

---

# PDELie - Execution Plan (V0.31.1a Research Spike)

**Status:** COMPLETE (merged as PR #101)

`v0.31.1a` is a compatibility research spike and decision milestone — **not** an implementation release. It does not modify any v0.31.0 report schema, add any root API, or bump the package version. It produces the SPEC 0 policy, the PySINDy 2.x migration audit, a machine-readable compatibility matrix, a private compatibility prototype (research-only), and the two test files that gate future implementation PRs.

Decision label:

```text
spec_0_modernization_outcome_A_modern_only_future_line
```

Outcome: **A (modern-only future line).** v0.32 targets Python ≥3.12 + NumPy 2.x + PySINDy 2.1.x. v0.31.x remains the legacy Python 3.11 + PySINDy 1.7.x maintenance line during the transition.

## Sub-release contents (v0.31.1a)

New research artifacts:

- `docs/design/RUNTIME_COMPATIBILITY_POLICY.md` — SPEC 0 alignment (Python ~3 years, core deps ~2 years, named-owner / removed-by rule for temporary exceptions), the target runtime matrix for v0.32, the retirement plan for every currently declared temporary exception, and the CI matrix proposal for the v0.32 implementation PR.
- `docs/design/PYSINDY_2_MIGRATION_AUDIT.md` — exhaustive per-delta API diff between pysindy 1.7.5 and 2.1.0, mapped to specific pdelie call sites; per-lane environment-matrix failure signatures; the recommended migration PR shape.
- `configs/runtime_compatibility_matrix.json` — strict-JSON machine-readable form of the two documents above (`summary_type = "pdelie_runtime_compatibility_matrix"`, `policy_outcome = "A_modern_only_future_line"`).
- `src/pdelie/discovery/_pysindy2_prototype.py` — **experimental, private, research-only** compatibility prototype recording the shape of the eventual shim. Not wired into any production code path.
- `tests/test_runtime_compatibility_policy.py` (18 tests) — strict-JSON invariants on the matrix; SPEC 0 policy statements; every-supported-Python-has-a-CI-lane guard; every-unsupported-generation-has-an-actionable-message guard; no-schema-drift guards on the 22-key and 27-key public reports; no-new-root-exports guard; NaN/Inf strict-JSON boundary preservation.
- `tests/test_pysindy_2_migration_prototype.py` (26 tests) — prototype detects 1.x and 2.x; rejects unsupported generations with an actionable message; enumerates the six documented API breaks; delta enumeration matches the audit document; prototype does not silently catch arbitrary exceptions; prototype is private (no public re-export); legacy 1.x task runtime is unaffected by the prototype's presence.

Environment matrix (audited under `uv`-managed Python 3.11 / 3.12 / 3.13 / 3.14 fresh venvs):

- Core-only lanes A/B/C/D (no `[downstream]` extra): all pass. Python 3.12–3.14 core surface is ready today (numpy 1.26.4 builds from source on 3.13/3.14 aarch64).
- Legacy lane E (Python 3.11 + pysindy 1.7.5): fully green (matches v0.31.0 baseline).
- Modern lanes F/G/H (Python 3.12/3.13/3.14 + pysindy 2.1.0): natural resolver refuses due to the numpy floor conflict (pdelie `<2` vs pysindy 2.1.0 `>=2.0`). Under `--no-deps` probe, pdelie core imports cleanly against numpy 2.5.1 — the `<2` cap is currently a resolver floor, not a runtime one. All fit paths fail with clean TypeError chains mapping to specific pysindy 2.x API changes.

PySINDy 2.x API deltas (six independent breaks + one unchanged random-state observation):

1. `SINDy.__init__`: removes `feature_names`, `t_default`, `discrete_time`.
2. `SINDy.fit`: drops `multiple_trajectories`, `unbias`, `quiet`, `ensemble`, `library_ensemble`, `replace`; moves `feature_names` from ctor.
3. `SINDy.differentiate`: method REMOVED.
4. `SINDy.model`: attribute REMOVED.
5. `STLSQ.__init__`: drops `fit_intercept`.
6. `PDELibrary.__init__` / `WeakPDELibrary.__init__`: drops `library_functions`, `function_names`, `interaction_only`; now requires `function_library=<BaseFeatureLibrary>`.
7. `WeakPDELibrary` random-state: unchanged (still no seed kwarg). The v0.31c1 `_legacy_numpy_rng_seed_scope` workaround does NOT retire with the port.

## Explicit non-goals for v0.31.1a

- No PySINDy 2.x compatibility code wired into production paths.
- No modification of the 22-key `discovery_task_result` schema.
- No modification of the 27-key `pdelie_weak_pde_library_diagnostic` schema.
- No new root export.
- No new PDE. No `SymmetryMethod` / `SymmetryCandidate` registry. No nonperiodic PySINDy discovery. No WSINDy benchmark. No noise-robustness claim.
- No pyproject dependency-range change. No CI job rename. No package version bump.
- No claim of PySINDy 2 support until v0.31.1 / v0.32 lands the full task and diagnostic paths.
- No dual 1.x/2.x runtime branching in the follow-up implementation PR (single-generation cutover per outcome A).

## Recommended follow-up implementation

`v0.32` (implementation, follows this research spike, per solo-dev consolidation policy): widen `numpy>=1.24,<3`; move the `[downstream]` extra to `pysindy>=2.1,<3` scoped to `python_version < '3.15'`; retire the `setuptools<82` temporary cap (pysindy 2.x uses `importlib.metadata`); migrate the six API-break sites; delete `_pysindy2_prototype.py` (outcome A — no runtime shim); retire the three xfailed tests in `tests/test_v0_31b3_pysindy_compatibility_policy.py`; rename CI release-gate job `v0_31-release-gate → v0_32-release-gate` at v0.32 release close.

## Retained xfails (unchanged by this spike)

The three v0.31b3-era xfails remain xfail in v0.31.1a — the spike does not land runtime version guards on `run_pysindy_pde_task` / `inspect_pysindy_weak_pde_library` and does not extend `_resolve_backend_version` to include scipy. All three retire under the v0.32 implementation.

---

# PDELie - Execution Plan (V0.31.0 Release Close)

**Status:** COMPLETE

`V0.31.0 is complete.` This is the mechanical release-close record.

Release decision: `downstream_discovery_task_bridge`.

Release close closes the v0.31 downstream-discovery task-bridge slice:

- v0.31a — design-only scope freeze (PR #84).
- v0.31b0 — PySINDy term-mapping golden + PDL-JSON debt tickets + preflight audit + label-registry fix (PR #94).
- v0.31b1 — executable periodic PySINDy `PDELibrary` task runner + `discovery_task_result` (22-key strict-JSON schema); adapter loosening for a caller-supplied `pysindy_model` (PR #95).
- v0.31b2 — diagnostic-only `WeakPDELibrary` wrapper + `pdelie_weak_pde_library_diagnostic` (27-key strict-JSON schema; `diagnostic_only = True`) (PR #96).
- v0.31b3 — temporary PySINDy 1.x compatibility policy (`C_temporary_1x_policy`) + compatibility-matrix JSON + CI pins (PR #97).
- v0.31c — public JSON-only downstream task-bridge example (submodule-only, seven-key composed wrapper — NOT a new schema); mandatory clean-install audit outcome A; xfail ledger (PR #98).
- v0.31c1 — adversarial setuptools 81/82/83 install matrix (verdict `B_setuptools_82_boundary`); narrow temporary `setuptools<82; python_version<'3.12'` cap on `[downstream]` and `[test]` extras; RNG audit refactor to a private `_legacy_numpy_rng_seed_scope` context manager (PR #99).
- **v0.31.0 release close (this PR)** — version bump `0.30.0 → 0.31.0`; `docs/releases/V0_31_RELEASE_READINESS.md`, `docs/specs/support_matrix.v0_31.json`, `CHANGELOG.md`; CI release-gate job rename `v0_30-release-gate → v0_31-release-gate`; scope status → COMPLETE; Python 3.12+ downstream UX targeted-message change.

Non-goals at release close (preserved verbatim from earlier sub-releases):

- No new discovery backend. No new summary type. No change to the 22-key `discovery_task_result` schema. No change to the 27-key `pdelie_weak_pde_library_diagnostic` schema.
- No WSINDy benchmark claim. No noise-robustness claim. No nonperiodic PySINDy discovery. No PySINDy 2.x code.
- No SymmetryMethod registry. No SymmetryCandidate runtime. No new root exports.
- No PDEBench / The Well support claim. No multi-channel or 2D widening.
- `numpy>=1.24,<2` unchanged. `pysindy>=1.7.5,<2` unchanged. `setuptools<82; python_version<'3.12'` retained. Python support policy unchanged.
- No PyPI or TestPyPI publication.
- No git tag created — deferred to explicit authorization after review.

Retained xfails (final v0.31.0 ledger, 3 entries): all in `tests/test_v0_31b3_pysindy_compatibility_policy.py`; every entry carries a non-empty reason; all deferred to `v0.31.1` (runtime version guards on the two task entry points) or to a nested provenance follow-up (scipy on `_resolve_backend_version`).

---

# PDELie - Execution Plan (V0.31c1)

**Status:** IN_PROGRESS

`v0.31c1` is a tiny pre-release compatibility milestone that hardens `pdelie[downstream]` against the realistic Python 3.11 environment where the ambient `setuptools` has already been upgraded past `pkg_resources` removal. It ships:

1. A mandatory adversarial install matrix on fresh Python 3.11 venvs with `setuptools` force-pinned to `81.0.0`, `82.0.0`, and `83.0.0` before `pip install "<wheel>[downstream]"`. Verdict: **B_setuptools_82_boundary**. Setuptools 81 works (with a removal warning); 82 and 83 fail with `ModuleNotFoundError: No module named 'pkg_resources'` at `import pysindy`, because pysindy 1.7.5 imports `pkg_resources` at package init and setuptools 82 removed the module.
2. A narrow temporary constraint added to the `[downstream]` and `[test]` extras: `setuptools<82; python_version < '3.12'`. Rebuilt-wheel post-fix verification confirms pip auto-downgrades an ambient setuptools 82/83 to 81 without any user co-install. Fresh-venv baseline unaffected (setuptools stays at the bundled `65.5.0`).
3. A small RNG-audit refactor: the v0.31c example's inline `try/finally` `np.random` seed/restore is extracted into a private `_legacy_numpy_rng_seed_scope(seed)` context manager. Deterministic behavior preserved verbatim; the manager's docstring documents that the workaround is **not thread-safe** because PySINDy 1.7.5 uses the legacy global RNG. No concurrency API is exposed.
4. `tests/test_v0_31c1_downstream_packaging_policy.py` (9 named tests) asserting: the extra declares the boundary; every runtime `setuptools` cap is bounded and Python-version-scoped; the policy doc records the reason; PySINDy pin stays `>=1.7.5,<2`; the 22-key and 27-key public schemas are unchanged; no new root exports; the installed wheel metadata declares the cap under `extra == 'downstream'`; the pip resolver plan downgrades an ambient setuptools past 82.
5. Documentation updates: `PYSINDY_COMPATIBILITY_POLICY.md` gains a "v0.31c1 adversarial install matrix — outcome B" section with the boundary table and post-fix verification; `configs/pysindy_compatibility_matrix.json` gains a `v0_31c1_packaging_audit` block; ROADMAP marks v0.31c completed and v0.31c1 in progress.

Decision label:

```text
adversarial_downstream_install_audit_and_setuptools_cap
```

Non-goals for v0.31c1:

- No new summary type. No change to the 22-key `discovery_task_result` schema. No change to the 27-key `pdelie_weak_pde_library_diagnostic` schema.
- No PySINDy 2.x port. Pin stays `pysindy>=1.7.5,<2`.
- No new root export.
- No new PDE. No symmetry-method registry. No WSINDy claim. No noise benchmark. No FD-nonperiodic discovery. No additional example.
- No package version bump. No tag. No PyPI/TestPyPI publication.
- No stricter-than-necessary cap: the constraint is `setuptools<82`, not `<81` — the audit proved 81 works.
- No release-gate manifest sub-release row for v0.31c1 (dependency policy is expressed via `pyproject.toml` + the compatibility-matrix JSON; the existing `0.31` manifest row is unchanged).

Files touched in v0.31c1:

- MODIFIED `pyproject.toml` — add `setuptools<82; python_version < '3.12'` to `[downstream]` and `[test]` extras.
- MODIFIED `src/pdelie/examples/downstream_discovery_task_bridge.py` — extract `_legacy_numpy_rng_seed_scope` context manager.
- NEW `tests/test_v0_31c1_downstream_packaging_policy.py` — 9 named tests.
- MODIFIED `docs/design/PYSINDY_COMPATIBILITY_POLICY.md` — adversarial-matrix section.
- MODIFIED `configs/pysindy_compatibility_matrix.json` — `v0_31c1_packaging_audit` block.
- MODIFIED `docs/planning/PLAN.md`, `docs/planning/ROADMAP.md`.

---

# PDELie - Execution Plan (V0.31c)

**Status:** IN_PROGRESS

`v0.31c` is the final sub-release of the v0.31 arc before the mechanical release-close PR. It ships:

1. A mandatory clean-install audit that proves the advertised `pip install "<wheel>[downstream]"` command is self-sufficient on Python 3.11 (outcome A) — no manual pre-install of setuptools/PySINDy/NumPy/SciPy/scikit-learn is required. `pyproject.toml` is unchanged; the existing `python_version < '3.12'` marker already handles the Python 3.12+ `pkg_resources` footgun via the ambient CI `setuptools<81` co-install.
2. One compact JSON-only public example — `pdelie.examples.run_downstream_discovery_task_bridge_example` and CLI `python -m pdelie.examples.downstream_discovery_task_bridge` — that demonstrates both v0.31 paths (`run_pysindy_pde_task` + `inspect_pysindy_weak_pde_library`) side-by-side on one canonical periodic scalar 1D Heat field. The example is deterministic under a frozen seed, records exact backend versions, and encodes its scope boundaries as machine-readable non-claim flags plus interpretation prose.
3. An xfail audit covering every currently-declared xfail (3, all in `tests/test_v0_31b3_pysindy_compatibility_policy.py`); each has a non-empty reason, each defers to v0.31.1 (PySINDy 2.x port) or to a nested provenance addition already implicit in the b3 policy.
4. Preflight notes for the v0.31 support-matrix additions, stored in this doc rather than as a finalized `support_matrix.v0_31.json` — the finalized matrix belongs in the release-close PR.

Decision label:

```text
downstream_task_bridge_public_example_and_install_self_sufficiency
```

Non-goals for v0.31c:

- No new scientific algorithm and no new report schema.
- No PySINDy 2.x port (deferred to `v0.31.1`).
- No change to the 22-key `discovery_task_result` schema.
- No change to the 27-key `pdelie_weak_pde_library_diagnostic` schema.
- No new PDE. No symmetry-method registry. No WSINDy claim. No noise benchmark. No FD-nonperiodic discovery.
- No root `pdelie` export. No package version bump. No tag. No PyPI/TestPyPI publication.
- No `setuptools<81` constraint added to the `[downstream]` extra (the clean-install audit demonstrated it is not needed on Python 3.11).

Files touched in v0.31c:

- NEW `src/pdelie/examples/downstream_discovery_task_bridge.py`
- MODIFIED `src/pdelie/examples/__init__.py` (re-export the new runner)
- NEW `tests/test_v0_31c_downstream_task_bridge_example.py` (15 named tests)
- MODIFIED docs: `PLAN.md`, `ROADMAP.md`, `API_STABILITY.md`, `PYSINDY_COMPATIBILITY_POLICY.md`
- MODIFIED `configs/release_gate_manifest.json` (single "0.31" row extended; no new sub-release row; `release_count` stays 19)

Support-matrix preflight (draft only — final content lives in the release-close PR):

- PySINDy `PDELibrary` task: supported for periodic scalar 1D under PySINDy 1.x (v0.31b1).
- `WeakPDELibrary` diagnostic: diagnostic-only, no benchmark claim (v0.31b2).
- PySINDy 2.x: deferred to `v0.31.1`.
- FD-nonperiodic PySINDy discovery: unsupported / deferred.
- WSINDy / noise robustness: explicitly unsupported claim.

Retained xfails (release-readiness ledger draft):

| test node id | reason | disposition |
|---|---|---|
| `test_v0_31b3::test_unsupported_major_pysindy_version_rejected_by_discovery_task_runner` | runtime version guard not yet landed on `run_pysindy_pde_task`; awaits `v0.31.1` | KEEP as xfail |
| `test_v0_31b3::test_unsupported_major_pysindy_version_rejected_by_weak_diagnostic` | runtime version guard not yet landed on `inspect_pysindy_weak_pde_library`; awaits `v0.31.1` | KEEP as xfail |
| `test_v0_31b3::test_discovery_task_backend_version_records_exact_pysindy_and_sklearn` | asks `pdelie.tasks.discovery._resolve_backend_version` to include `scipy` for uniformity with the weak diagnostic's provenance | KEEP as xfail — nested provenance extension deferred to a follow-up |

Every xfail carries a non-empty reason. None of the xfails represent a genuine failure being masked to make the suite green. None have been converted stale.

---

# PDELie - Execution Plan (V0.31b3)

**Status:** IN_PROGRESS

`v0.31b3` is the third runtime sub-release under the v0.31 arc. It does **not** ship a new PDE, a new schema, a new symmetry-registry surface, a new discovery task type, or a new WSINDy claim. Its scope is entirely **downstream compatibility hardening**: it formalizes the existing `pysindy>=1.7.5,<2` pin as a declared temporary policy, documents the exact PySINDy versions the `pdelie.tasks.*` runtime is verified against, records the four independent 2.x-API deltas that a future `v0.31.1` / `v0.32` shim will need to absorb, and reflects the policy into `configs/release_gate_manifest.json`, `configs/pysindy_compatibility_matrix.json`, and the CI matrix. `pyproject.toml` stays pinned at `0.30.0`.

Decision label:

```text
downstream_pysindy_compatibility_policy_and_wheel_hardening
```

Chosen outcome: `C_temporary_1x_policy`. The env-audit phase verified that `pysindy 1.7.5` passes 61/61 targeted `pdelie.tasks.discovery` / `pdelie.tasks.weak_pde_library` tests against the current `pdelie 0.30.0` code, while `pysindy 2.1.0` HARD-breaks on three independent axes (`SINDy(feature_names=, discrete_time=)` constructor kwargs removed, `WeakPDELibrary(library_functions=, function_names=, interaction_only=)` kwargs removed, `SINDy.differentiate` removed) plus a transitive `numpy>=2` floor conflict with pdelie's `numpy<2` pin (21/61 targeted tests fail on 2.1.0; `pip` rejects joint install with `ResolutionImpossible`). The correct v0.31b3 posture is therefore to declare the existing `pysindy>=1.7.5,<2` pin as an intentional temporary policy, document the `setuptools<81` install footgun for the 1.x line, and defer PySINDy 2.x support to a dedicated migration release. **No compat shim is added in v0.31b3.**

## Sub-release contents (v0.31b3)

- `docs/design/PYSINDY_COMPATIBILITY_POLICY.md` (NEW) — the authoritative policy document. Enumerates the supported PySINDy range (`1.7.5` only under the pinned `>=1.7.5,<2` constraint), the primary tested version (`1.7.5`; no secondary), the unsupported ranges (`<1.7.5` and `>=2.0.0`) with per-axis rationale, the exact public pdelie surfaces covered (`pdelie.tasks.discovery.run_pysindy_pde_task`, `summarize_discovery_task_result`, `PySINDyDiscoveryUnsupportedBoundaryError`; `pdelie.tasks.weak_pde_library.inspect_pysindy_weak_pde_library`, `summarize_pysindy_weak_pde_library_diagnostic`, `WeakPDELibraryDiagnostic`), the nine known 1.x-vs-2.x API-diff rows recorded for the future shim, the `setuptools<81` install footgun for pysindy 1.x, the CI matrix summary, and a reserved "Resource envelope" section for the follow-on resource-envelope phase to append its numbers. Also explicitly declares the non-claims: no WSINDy benchmark, no noise robustness claim, no nonperiodic discovery, no PDEBench / The Well support claim, no `weak_1d` retirement, no PySINDy 2.x support.
- `configs/pysindy_compatibility_matrix.json` (NEW) — strict-JSON machine-readable matrix under `summary_type = "pdelie_pysindy_compatibility_matrix"`, `summary_schema_version = "0.1"`. Carries `policy_outcome`, `pyproject_constraint`, `primary_tested_version`, `secondary_tested_version` (null), `supported_versions`, `unsupported_versions`, and `ci_matrix`. Loads under `json.loads(json.dumps(m, allow_nan=False)) == m`.
- `configs/release_gate_manifest.json` (MODIFIED) — the existing `0.31` row is **extended in place** (no new `0.31b3` row; `release_count` stays 19). `forbidden_root_attributes.names` grows to reject the future compat-shim leak surface (`_pysindy_compat`, `SUPPORTED_PYSINDY_VERSIONS`) so those names cannot silently reach the `pdelie` root when the shim is later introduced. `forbidden_submodule_attributes` mirrors the same forbiddance for the `pdelie.discovery`, `pdelie.tasks`, `pdelie.tasks.discovery`, and `pdelie.tasks.weak_pde_library` submodules. A `strict_json_manifests` entry is added for `configs/pysindy_compatibility_matrix.json`. Every v0.31b1 and v0.31b2 assertion is preserved verbatim.
- `.github/workflows/ci.yml` (MODIFIED) — narrow, additive change: the two existing blocking jobs (`editable-tests`, `v0_30-release-gate`) have their PySINDy version made explicit via an `env: PDELIE_PINNED_PYSINDY_VERSION: "1.7.5"` variable and an install-time `python -m pip install "pysindy==1.7.5"` step immediately after the `.[test]` install. The `.[test]` extra already resolves to `pysindy>=1.7.5,<2`; the explicit pin makes the CI's exercised version match the compatibility matrix's declared primary tested version. Both jobs run the v0.31b3 test file (`tests/test_v0_31b3_pysindy_compat_policy.py`) alongside the existing v0.30 release-gate suite; both remain blocking. No other CI job is modified; the Python version matrix is unchanged.
- `docs/specs/API_STABILITY.md` (MODIFIED) — appends a new sub-note under the v0.31b2 stable public-surface note recording the declared temporary `pysindy>=1.7.5,<2` compatibility policy, the fact that any future `_pysindy_compat` helpers are private (no root export, no submodule public re-export), and a pointer to `docs/design/PYSINDY_COMPATIBILITY_POLICY.md`. No existing text is changed.
- `docs/planning/ROADMAP.md` (MODIFIED) — v0.31b2 status moves to `Completed (PR #96)`; v0.31b3 gets a new `In progress` row on the planned-direction table with the decision label above; a new `v0.31.1` row is added for "PySINDy 2.x port" per the `C_temporary_1x_policy` outcome. No existing row is deleted.
- `docs/planning/PLAN.md` (this section prepended).
- `tests/test_v0_31b3_pysindy_compat_policy.py` (Author B's remit; not written by this author) — will exercise the manifest, JSON matrix, and installed-pysindy version at runtime.

## Scope-in files (v0.31b3)

- `docs/design/PYSINDY_COMPATIBILITY_POLICY.md`
- `configs/pysindy_compatibility_matrix.json`
- `configs/release_gate_manifest.json` (extend the `0.31` row in place)
- `.github/workflows/ci.yml` (narrow, additive per-job change; no new job)
- `docs/specs/API_STABILITY.md`
- `docs/planning/ROADMAP.md`
- `docs/planning/PLAN.md`
- `tests/test_v0_31b3_pysindy_compat_policy.py` (Author B)

## Scope-out files (v0.31b3)

- Any file under `src/` — the runtime is unchanged. No shim is introduced; `pdelie.discovery.pysindy_adapter`, `pdelie.discovery._pysindy_defaults`, `pdelie.tasks.discovery`, `pdelie.tasks.weak_pde_library` are untouched.
- Any file under `tests/` other than the new v0.31b3 policy test file authored by Author B — the b0/b1/b2 test files are unchanged.
- `pyproject.toml` — unchanged. The existing `pysindy>=1.7.5,<2` pin on the `[downstream]` and `[test]` extras is the policy. No version bump. No optional-dependency addition.
- `src/pdelie/discovery/_pysindy_compat.py` — **not created** in v0.31b3. The compat shim is deferred to `v0.31.1` / `v0.32` when the pin is widened to admit PySINDy 2.x.
- `docs/specs/SPEC.md`, `docs/specs/CONTRACTS_AND_DEFAULTS.md`, `docs/specs/SUPPORT_MATRIX.md`, `docs/specs/LABEL_REGISTRY.md` — no changes. This is a compatibility-policy release, not a public-API expansion.

## Explicit non-goals for v0.31b3

- No new schema; no new PDE; no new symmetry registry; no new discovery task type; no WSINDy claim; no nonperiodic discovery.
- No new `pdelie` runtime code, no new submodule, no new public re-export.
- No compat shim (`src/pdelie/discovery/_pysindy_compat.py` is **not** created in this sub-release).
- No PySINDy 2.x support. `>=2.0.0` remains explicitly unsupported.
- No `numpy>=2` floor bump. Widening the numpy floor is coupled with admitting PySINDy 2.x and is deferred to `v0.31.1` / `v0.32`.
- No new CI job for a per-PySINDy-version matrix — the existing two blocking jobs already exercise the sole supported PySINDy version through the `.[test]` extra.
- No promotion of the v0.30e advisory `lint` / `typecheck` / `coverage` CI jobs to blocking; Phase 2 remains deferred.
- No version bump in `pyproject.toml` (`0.30.0` remains pinned).
- No standalone `tests/test_v0_31b3_release_gate.py`; the `0.31` release-gate lives as a single row in `configs/release_gate_manifest.json` replayed by `tests/test_release_gates.py` (extended in place, following the v0.30f consolidation pattern).
- No new label family in `docs/specs/LABEL_REGISTRY.md`.
- No `pdelie.residuals.weak_1d` removal; retention through `v0.32` close is unchanged.
- No public root `pdelie` export for any new name.

## v0.31b3 sub-release gate

`v0.31b3` is complete when:

- `docs/design/PYSINDY_COMPATIBILITY_POLICY.md` exists and enumerates the supported range (`1.7.5` only), the primary tested version (`1.7.5`), the unsupported ranges (`<1.7.5` and `>=2.0.0`) with per-axis rationale, the exact six public pdelie surfaces covered, the known 1.x-vs-2.x API differences, the explicit non-claims (no WSINDy benchmark, no noise robustness claim, no nonperiodic discovery), and reserves a "Resource envelope" section for later.
- `configs/pysindy_compatibility_matrix.json` exists, is strict-JSON compatible (`json.loads(json.dumps(m, allow_nan=False)) == m`), carries `summary_type = "pdelie_pysindy_compatibility_matrix"`, `summary_schema_version = "0.1"`, `policy_outcome = "C_temporary_1x_policy"`, `pyproject_constraint = "pysindy>=1.7.5,<2"`, `primary_tested_version = "1.7.5"`, `secondary_tested_version = null`, `supported_versions = ["1.7.5"]`, `unsupported_versions = ["<1.7.5", ">=2.0.0"]`, and a two-entry `ci_matrix`.
- The `0.31` row of `configs/release_gate_manifest.json` is extended in place: `forbidden_root_attributes.names` includes `_pysindy_compat` and `SUPPORTED_PYSINDY_VERSIONS`; `forbidden_submodule_attributes.names` includes the same names against `pdelie.tasks`, `pdelie.tasks.discovery`, `pdelie.tasks.weak_pde_library`, and `pdelie.discovery`; a `strict_json_manifests` entry is added for `configs/pysindy_compatibility_matrix.json`. `release_count` stays 19; no `0.31b3` row is added.
- `.github/workflows/ci.yml` records `pysindy==1.7.5` explicitly on the two existing blocking jobs (`editable-tests`, `v0_30-release-gate`) and runs `tests/test_v0_31b3_pysindy_compat_policy.py` alongside the existing release-gate suite. No other job is modified.
- `docs/specs/API_STABILITY.md` carries a compatibility-policy note that names the supported range and points to `docs/design/PYSINDY_COMPATIBILITY_POLICY.md`.
- `docs/planning/ROADMAP.md` shows v0.31b2 as `Completed (PR #96)`, v0.31b3 as `In progress`, and adds a `v0.31.1` "PySINDy 2.x port" row.
- `pyproject.toml` still declares `version = "0.30.0"`; no file under `src/` is added or modified; the compat shim is deferred.

---

# PDELie - Execution Plan (V0.31b2)

**Status:** IN_PROGRESS

`v0.31b2` is the second runtime sub-release under the v0.31 arc. It lands the `pdelie.tasks.weak_pde_library` submodule with a diagnostic-only wrapper around PySINDy's `WeakPDELibrary`. The wrapper produces a **separate** top-level strict-JSON summary type (`pdelie_weak_pde_library_diagnostic`, `diagnostic_only=True`); it does **not** extend the v0.31b1 `discovery_task_result` shape and does not promote any PDE to `supported_existing_slice`. Three new submodule-only names ship (`WeakPDELibraryDiagnostic`, `summarize_pysindy_weak_pde_library_diagnostic`, `inspect_pysindy_weak_pde_library`), all available from `pdelie.tasks.weak_pde_library` and re-exported from `pdelie.tasks`; none is added to the `pdelie` root. `pyproject.toml` stays pinned at `0.30.0`.

Decision label:

```text
downstream_discovery_task_bridge_diagnostic_weakpdelibrary
```

## Sub-release contents (v0.31b2)

- `src/pdelie/tasks/weak_pde_library.py` (NEW) — submodule housing `WeakPDELibraryDiagnostic` (dataclass with `as_dict()`), `summarize_pysindy_weak_pde_library_diagnostic` (strict-JSON summarizer), and `inspect_pysindy_weak_pde_library` (PySINDy inspector). The inspector consumes a periodic scalar 1D `FieldBatch`, invokes PySINDy's `WeakPDELibrary` under the frozen identifier strings (`method_family = "pysindy_weak_pde_library_polynomial_gauss_v1"`, `test_function_family = "pysindy_weak_pde_library_polynomial_bump_v1"`, `quadrature_rule = "pysindy_weak_pde_library_composite_gauss_v1"`), and returns a `WeakPDELibraryDiagnostic` carrying weak-feature names, matrix/target shapes, retained/skipped-row counts, column norms, rank and condition number, and finite-value status.
- `src/pdelie/tasks/__init__.py` (MODIFIED) — re-exports `WeakPDELibraryDiagnostic`, `summarize_pysindy_weak_pde_library_diagnostic`, and `inspect_pysindy_weak_pde_library` alongside the v0.31b1 re-exports; no new root `pdelie` export.
- `src/pdelie/reporting/summaries.py` (MODIFIED) — additive supportability-policy update in `summarize_weak_form_supportability` at lines 1942-1951: a new key `"supports_pysindy_weak_library_diagnostic": True` is inserted immediately after the existing `"supports_weak_derivative_backend": False` line. The existing `"supports_weak_derivative_backend": False` value is **not** changed; its comment / docstring is re-scoped to name the pdelie-native strong-derivative-only path explicitly. No existing key is removed; no existing value is silently flipped.
- Runtime boundary-condition guard (unchanged from v0.31b1): the wrapper reuses `PySINDyDiscoveryUnsupportedBoundaryError` (already defined in `pdelie.tasks.discovery`, subclass of `ScopeValidationError`). Nonperiodic-x inputs raise before any PySINDy call. The two-layer periodic-only fence (task-entry `is_x_periodic` + `to_pysindy_trajectories` bridge gate) covers the wrapper path.
- Strict-JSON boundary — the wrapper summarizer routes its final payload through the existing `_validate_strict_json_compatible` helper at `src/pdelie/reporting/summaries.py:196-202`, mirroring the v0.31b1 discovery-task-result and the earlier weak-supportability strict-JSON summaries. NaN or Inf anywhere in the payload raises `SchemaValidationError`.
- `tests/test_v0_31b2_weak_pde_library_diagnostic.py` (NEW) — runtime test file for the new submodule surface (import invariants, submodule-only export shape, `pdelie` root non-exposure, `pdelie.tasks` package re-export), the strict-JSON contract at the composed payload boundary (NaN/Inf adversarials on numeric fields), the inspector's periodic-only BC guard (raises `PySINDyDiscoveryUnsupportedBoundaryError` on nonperiodic-x inputs), the frozen identifier strings, the frozen top-level key set, the `diagnostic_only=True` marker, and the additive supportability-policy update in `summarize_weak_form_supportability`. Tests scope PySINDy `numpy.product` DeprecationWarning cascade narrowly via `pytest.warns(...)` / `warnings.filterwarnings("ignore", ...)` inside the specific weak-library tests; no global `warnings=error` filter is added.
- `configs/release_gate_manifest.json` (MODIFIED) — the existing `0.31` row is **extended** in place (no new row). `required_submodule_attributes` grows to include the three new names on `pdelie.tasks.weak_pde_library` and their re-exports on `pdelie.tasks`. `forbidden_root_attributes.names` and `forbidden_submodule_attributes.names` are extended with the union of the new names and `weak_pde_library` (as a forbidden root attribute). `release_count` stays at 19; the `0.31` row is one row covering the whole minor.
- Docs updated: `docs/design/DISCOVERY_TASK_RESULT_SCHEMA.md` (status line moved from RUNTIME DEFERRED to RUNTIME IMPLEMENTED for the WeakPDELibrary wrapper, plus a new section documenting the separate summary type and the 27-key top-level shape); `docs/specs/API_STABILITY.md` (new stable public-surface note for `v0.31b2`); `docs/planning/ROADMAP.md` (v0.31b1 marked Completed with PR #95 link; v0.31b2 marked In progress); `docs/planning/PLAN.md` (this section).
- Preflight reference — `docs/planning/PYSINDY_API_PREFLIGHT_AUDIT.md` recorded the frozen PySINDy version (`1.7.5`), and a subsequent b2-specific preflight (`weak_pdelibrary_available: true`, `weak_pdelibrary_signature: (library_functions=..., derivative_order=..., spatiotemporal_grid=..., ..., is_uniform=..., periodic=...)`) verified that the installed WeakPDELibrary API is fully consumable via the same `pysindy.SINDy` integration path used in v0.31b1. Three preflight assumption-diffs are recorded there and are non-blocking: (a) `is_uniform=`/`periodic=` are still functional but emit a `UserWarning` — b2 routes the periodic hint through `differentiation_method` where possible and scopes warning filters narrowly per-test otherwise; (b) the frozen `pysindy_weak_pde_library_polynomial_gauss_v1` / `pysindy_weak_pde_library_composite_gauss_v1` strings mislabel PySINDy's actual method (analytical piecewise-polynomial integration under a polynomial test function) but the strings are opaque provenance labels, are deliberately distinct from pdelie-native `weak_1d`, and are carried forward verbatim; (c) PySINDy's internal `numpy.product` cascade emits ~30 DeprecationWarnings per fit — scoped narrowly per-test and not filtered globally.

## Scope-in files (v0.31b2)

- `src/pdelie/tasks/weak_pde_library.py`
- `src/pdelie/tasks/__init__.py`
- `src/pdelie/reporting/summaries.py` (additive supportability-policy key only)
- `tests/test_v0_31b2_weak_pde_library_diagnostic.py`
- `configs/release_gate_manifest.json` (extend the `0.31` row in place)
- `docs/design/DISCOVERY_TASK_RESULT_SCHEMA.md`
- `docs/specs/API_STABILITY.md`
- `docs/planning/ROADMAP.md`
- `docs/planning/PLAN.md`

## Scope-out files (v0.31b2)

- `src/pdelie/tasks/discovery.py` — unchanged; the v0.31b1 discovery-task runner is not extended and its `TaskResult` 22-key top-level shape is preserved.
- `src/pdelie/residuals/weak_1d.py` — untouched; retention guaranteed through `v0.32` close.
- `src/pdelie/discovery/*` — untouched; the periodic-only bridge and the v0.31b1 config-lock loosening are preserved.
- `src/pdelie/_boundary.py` — untouched; the periodic-only-x fence is unchanged.
- `pyproject.toml` — unchanged; no version bump.
- `docs/specs/LABEL_REGISTRY.md` — not touched. The v0.31b2 wrapper reuses the existing `supportability_label` vocabulary (`diagnostic_only` is already one of the frozen values on the `weak_form_supportability` family, v0.24). No new label family is introduced; the wrapper adds one **field** on the supportability-policy dict (`supports_pysindy_weak_library_diagnostic`), not a new label vocabulary.

## Explicit non-goals for v0.31b2

- No WSINDy design matrix, no SR3 weak sparse recovery, no weak-sparse-recovery claim of any kind.
- No noise-robustness claim; no clean/noisy gate.
- No PDEBench support claim, no The Well support claim, no external-dataset benchmark claim.
- No validated `O((dx)^p)` parity harness with pdelie-native `weak_1d`. Parity is contingent on `weak_1d` removal beyond `v0.32` close and is deliberately deferred.
- No promotion of any PDE to `supported_existing_slice` via the wrapper. The `diagnostic_only=True` marker on the wrapper payload and its condensed `weak_contract` block is load-bearing.
- No root `pdelie` export for any of the three new names.
- No new label family in `docs/specs/LABEL_REGISTRY.md`; the wrapper reuses `supportability_label` / `diagnostic_only` on the existing v0.24 `weak_form_supportability` family.
- No widening of the periodic-only-x guard. Nonperiodic-x is still rejected at the task entry with `PySINDyDiscoveryUnsupportedBoundaryError`.
- No public strong extension of `supports_weak_derivative_backend`. That key stays `False` and is re-scoped in comment/docstring only to name the pdelie-native strong-derivative-only path.
- No FD-nonperiodic PySINDy discovery. That extension is a `v0.32.5` target.
- No multi-channel or 2D `FieldBatch` dispatch (deferred to `v0.34+`).
- No new PDE row.
- No new optional dependency; no CI workflow change; no promotion of the v0.30e advisory `lint` / `typecheck` / `coverage` jobs to blocking.
- No version bump in `pyproject.toml` (`0.30.0` remains pinned).
- No standalone `tests/test_v0_31b2_release_gate.py`; the `0.31` release-gate lives as a single row in `configs/release_gate_manifest.json` replayed by `tests/test_release_gates.py` (extended in place, following the v0.30f consolidation pattern).

## v0.31b2 sub-release gate

`v0.31b2` is complete when:

- `pdelie.tasks.weak_pde_library` exists and exports exactly `WeakPDELibraryDiagnostic`, `summarize_pysindy_weak_pde_library_diagnostic`, and `inspect_pysindy_weak_pde_library`; the same three names are re-exported from `pdelie.tasks`; no other name leaks from `pdelie.tasks.weak_pde_library`; no root `pdelie` export is added; `pdelie.residuals`, `pdelie.reporting`, and `pdelie.discovery` do not carry any of the three new names.
- `summarize_pysindy_weak_pde_library_diagnostic` returns a strict-JSON-compatible dict matching the frozen 27-key top-level shape; `summary_type == "pdelie_weak_pde_library_diagnostic"`; `summary_schema_version == "0.1"`; `diagnostic_only == True`; `method_family == "pysindy_weak_pde_library_polynomial_gauss_v1"`; `input_layout == "scalar_1d_uniform"`; `_validate_strict_json_compatible` is invoked at the composed payload boundary.
- `inspect_pysindy_weak_pde_library` raises `PySINDyDiscoveryUnsupportedBoundaryError` (the existing v0.31b1 exception) on any nonperiodic-x `FieldBatch` before any PySINDy call.
- `summarize_weak_form_supportability`'s policy dict at `src/pdelie/reporting/summaries.py:1942-1951` carries the additive `"supports_pysindy_weak_library_diagnostic": True` key immediately after `"supports_weak_derivative_backend": False`; the `False` value is unchanged; no other key is added or removed.
- The v0.31b1 `discovery_task_result` 22-key top-level shape is preserved; no new top-level key is added; the condensed 4-key `weak_contract` block embedded when `target_convention == "weak_pde_library"` is unchanged from v0.31a.
- `tests/test_v0_31b2_weak_pde_library_diagnostic.py` is present and its named tests pass; the full test suite still passes; the extended `0.31` row in `configs/release_gate_manifest.json` is enforced by `tests/test_release_gates.py`.
- No file under `src/pdelie/` is added or modified beyond `tasks/weak_pde_library.py`, `tasks/__init__.py`, and the additive `summarize_weak_form_supportability` policy-dict update; `pyproject.toml` still declares `version = "0.30.0"`; no CI workflow is modified.

---

# PDELie - Execution Plan (V0.31b1)

**Status:** IN_PROGRESS

`v0.31b1` is the first runtime sub-release for the downstream discovery task bridge frozen by `v0.31a`. It lands the `pdelie.tasks.discovery` submodule with a periodic-only PySINDy `PDELibrary`-backed task runner, the composed `TaskResult` schema wrapper, a runtime boundary-condition guard, and a narrow loosening of the `fit_pysindy_discovery` config-lock to accept a caller-supplied `pysindy_model`. The `WeakPDELibrary` diagnostic wrapper (`target_convention="weak_pde_library"`) remains deferred to `v0.31b2`. No root `pdelie` export is added. `pyproject.toml` stays pinned at `0.30.0`.

Decision label:

```text
downstream_discovery_task_bridge_runtime_pdelibrary_only
```

## Sub-release contents (v0.31b1)

- `src/pdelie/tasks/__init__.py` + `src/pdelie/tasks/discovery.py` — new runtime submodule. Provides `run_pysindy_pde_task`, `summarize_discovery_task_result`, and `PySINDyDiscoveryUnsupportedBoundaryError`. Submodule-only; no root `pdelie` export.
- `PySINDyDiscoveryUnsupportedBoundaryError` — new exception, subclass of `ScopeValidationError`. Raised at the `pdelie.tasks.discovery` entry when a nonperiodic-x `FieldBatch` is supplied, before any PySINDy call.
- `summarize_discovery_task_result` — TaskResult wrapper. Enforces the composed schema invariants frozen in `docs/design/DISCOVERY_TASK_RESULT_SCHEMA.md`: 22-key top-level shape, `summary_type = "discovery_task_result"`, `summary_schema_version = "0.1"`, `pysindy_bridge_variant = "periodic_only_v1"`, and strict-JSON compatibility via `_validate_strict_json_compatible` at the composed payload boundary. `underlying_discovery_result` embeds `summarize_discovery_result` verbatim.
- `run_pysindy_pde_task` — task runner. Accepts a periodic scalar 1D `FieldBatch` plus optional caller-supplied `pysindy_model`, runs the fit through the existing bridge, and returns a `TaskResult`-shaped dict. Runtime BC guard is the first check; nonperiodic-x inputs raise `PySINDyDiscoveryUnsupportedBoundaryError` immediately.
- `fit_pysindy_discovery` — config-lock loosened. The existing `config=None`-only check (`src/pdelie/discovery/pysindy_adapter.py:204`) is broadened so that a caller-supplied `pysindy_model` is accepted; `config=None` default behavior is unchanged for existing callers.
- `tests/test_v0_31b1_discovery_task_runtime.py` — 20 named runtime tests covering the submodule surface, the runner happy path, the BC guard, the TaskResult wrapper schema invariants, the strict-JSON contract at the composed boundary, the loosened `fit_pysindy_discovery` config-lock, and the `pysindy_bridge_variant = "periodic_only_v1"` invariant.
- `configs/release_gate_manifest.json` — new `0.31` row (following the `v0.30f` consolidation pattern; no standalone `test_v0_31_release_gate.py`).
- Docs updated: `docs/specs/API_STABILITY.md` (stable public-surface note for `v0.31b1`), `docs/planning/ROADMAP.md` (Next Planned Work rows updated), `docs/planning/PLAN.md` (this section), `docs/design/DISCOVERY_TASK_RESULT_SCHEMA.md` (status line moved from RUNTIME DEFERRED to RUNTIME IMPLEMENTED for `target_convention="pde_library"`; `weak_pde_library` remains DEFERRED to `v0.31b2`).

## Explicit non-goals for v0.31b1

- No root `pdelie` export for any of the three new names.
- No `SymmetryCandidate` contract or wrapper — that surface is `v0.30.1` responsibility.
- No `SymmetryMethod` registry — that is also `v0.30.1`.
- No `WeakPDELibrary` runtime — the diagnostic wrapper is `v0.31b2`.
- No WSINDy implementation and no noise-robustness claim.
- No FD-nonperiodic PySINDy discovery. The bridge and the task runner are periodic-only in `v0.31b1`.
- No PDEBench support claim, no The Well support claim.
- No multi-channel or 2D `FieldBatch` dispatch (deferred to `v0.34+`).
- No new PDE. The task runner is agnostic across the existing v0.30 stable PDE rows, but no new PDE row is added.
- No deletion of `weak_1d`. It is retained through `v0.32` close per the `v0.31a` scope freeze.
- No top-level `diagnostic_only` key on `TaskResult` — that key is exclusive to the `pdelie_weak_pde_library_diagnostic` summary type introduced in `v0.31b2`.
- No `discovery_result` key on the composed payload — the embedded backend-native summary lives under `underlying_discovery_result` per the design.
- No version bump. `pyproject.toml` stays at `0.30.0`.

## v0.31b1 sub-release gate

`v0.31b1` is complete when:

- `src/pdelie/tasks/__init__.py` and `src/pdelie/tasks/discovery.py` exist and export exactly `run_pysindy_pde_task`, `summarize_discovery_task_result`, and `PySINDyDiscoveryUnsupportedBoundaryError`; no other name leaks from `pdelie.tasks.discovery`; no root `pdelie` export is added.
- `PySINDyDiscoveryUnsupportedBoundaryError` is a subclass of `ScopeValidationError` and is raised at the `pdelie.tasks.discovery` entry on any nonperiodic-x `FieldBatch` before any PySINDy call.
- `summarize_discovery_task_result` returns a strict-JSON-compatible dict matching the frozen 22-key schema; `underlying_discovery_result` is verbatim `summarize_discovery_result`; `pysindy_bridge_variant == "periodic_only_v1"` on every produced `TaskResult`; `_validate_strict_json_compatible` is invoked at the composed payload boundary.
- `fit_pysindy_discovery` accepts a caller-supplied `pysindy_model` kwarg without raising the historical `config=None`-only guard; `config=None` default behavior is unchanged for existing callers.
- `tests/test_v0_31b1_discovery_task_runtime.py` is present and its 20 named tests pass; the full test suite still passes; the new `0.31` release-gate manifest row is enforced by `tests/test_release_gates.py`.
- No file under `src/pdelie/` is added beyond `tasks/__init__.py`, `tasks/discovery.py`, and the narrow `fit_pysindy_discovery` loosening; `pyproject.toml` still declares `version = "0.30.0"`; no CI workflow is modified.

---

# PDELie - Execution Plan (V0.31b0 preparatory hygiene)

**Status:** IN_PROGRESS

`v0.31b0` is a preparatory hygiene sub-release for the `v0.31b1` runtime (`pdelie.tasks.discovery` implementation). It ships **no runtime code, no schema surface, and no version bump** (`pyproject.toml` stays pinned at `0.30.0`). It exists to land five preparatory artifacts that de-risk the `v0.31b1` implementation phase: a term-mapping golden fixture that pins the current PySINDy feature-name → PDELie canonical-term mapping, two planning tickets that inventory and stage the strict-JSON debt migration, a PySINDy API preflight audit that is a mandatory prerequisite for `v0.31b1`, and a documentation-anomaly fix in `LABEL_REGISTRY.md`. No file under `src/pdelie/` is modified. No new optional dependency is added. No CI job is added.

Decision label:

```text
preparatory_hygiene_before_discovery_task_bridge_runtime
```

## Sub-release contents (v0.31b0)

- `tests/test_v0_31b0_pysindy_term_mapping_golden.py` — golden pytest suite (8 tests) that pins the current PySINDy feature-name → PDELie canonical-term mapping. Specifically: the 17-key `summarize_discovery_result` top-level keyset; the `f"{var}__x_index_{i}"` bridge feature-name convention emitted by `to_pysindy_trajectories`; the 6-key frozen `coefficient_summary` inner shape; the `{train, heldout}` residuals block with 4-key inner blocks (`size`, `l2_norm`, `rms`, `max_abs`); the `equation_terms: dict[str, dict[str, float]]` shape keyed by `feature_names`; and the `returns_coefficients=False` invariant. STLSQ-selected term content is deliberately NOT pinned — threshold=0.1 makes term counts fragile. `pytest.importorskip("pysindy", ...)` gates the whole suite so the golden is skippable in minimal environments.
- `docs/planning/PDL_JSON_1_STRICT_JSON_INVENTORY.md` — planning ticket that inventories every strict-JSON call site and every schema-emitting surface in `src/pdelie/reporting/`, records which surfaces currently pass `_validate_strict_json_compatible` and which do not, and enumerates the outstanding strict-JSON debt items. Design-only; no runtime change.
- `docs/planning/PDL_JSON_2_STRICT_JSON_MIGRATION.md` — planning ticket that stages the migration of the debt items catalogued in `PDL_JSON_1`. Defines the migration ordering, the per-surface acceptance test shape, and the release-cycle in which each item lands. Design-only; no runtime change; explicitly not `v0.31b1` scope.
- `docs/planning/PYSINDY_API_PREFLIGHT_AUDIT.md` — preflight audit of the exact PySINDy public surface `v0.31b1` will consume. Records the pinned PySINDy version, the specific classes/methods used (`WeakPDELibrary`, `PDELibrary`, `SINDy`, `.fit`, `.print`, `.feature_names_in_`, `.coefficients_`), their argument shapes at the pinned version, and the known-drift-risk items (feature-name string format across PySINDy minor versions). **Mandatory prerequisite for v0.31b1** — the runtime PR cannot land without this audit in place.
- `docs/specs/LABEL_REGISTRY.md` — documentation-anomaly fix. The `residual_domain_policy` row's Source reference cell now cites `src/pdelie/reporting/summaries.py:1320-1327` (the extraction/default block) rather than the vague `(residual-summary path)` parenthetical. Every other row in the registry cites a specific line or line range; this row now matches that style. No runtime change; the vocabulary is unchanged.

## Files modified (v0.31b0)

- `docs/specs/LABEL_REGISTRY.md` — line-number citation fix on the `residual_domain_policy` row (see above).
- `docs/planning/PLAN.md` — this section prepended above the existing `v0.31a` and `v0.32a` planning notes and the `v0.30` release-close record.
- `docs/planning/ROADMAP.md` — new `v0.31b0` row added ahead of the `v0.31b` runtime placeholder; scope-note phrasing aligned with the `preparatory_hygiene_before_discovery_task_bridge_runtime` decision label.
- `docs/planning/index.rst` — `PDL_JSON_1_STRICT_JSON_INVENTORY`, `PDL_JSON_2_STRICT_JSON_MIGRATION`, and `PYSINDY_API_PREFLIGHT_AUDIT` added to the planning toctree between `V0_31_DISCOVERY_TASK_BRIDGE_SCOPE` and `archive/index`.

## Explicit non-goals

- No `src/pdelie/` change. `v0.31b0` is preparatory-only; the runtime implementation lives in `v0.31b1`.
- No `pyproject.toml` version bump (`0.30.0` remains pinned).
- No runtime code. The golden fixture is JSON; the three docs are Markdown planning artifacts; the LABEL_REGISTRY fix is a citation edit.
- No new optional dependency; no new PySINDy version pin (the pin is *documented* in `PYSINDY_API_PREFLIGHT_AUDIT.md` but not moved).
- No new CI job. No promotion of the `v0.30e` advisory `lint`/`typecheck`/`coverage` jobs. No new release-gate manifest row (the `v0.31b0` gate below is enforced by the same infrastructure that enforces `v0.31a`).

## v0.31b0 sub-release gate

`v0.31b0` is complete when:

- `tests/test_v0_31b0_pysindy_term_mapping_golden.py` is present and its 8 named tests pass on current HEAD (bridge feature-name convention, summarize keyset, library_feature_names shape, equation_terms shape, coefficient_summary keyset, residuals shape, `returns_coefficients=False`, and a no-regression keyset assertion).
- `docs/planning/PDL_JSON_1_STRICT_JSON_INVENTORY.md` and `docs/planning/PDL_JSON_2_STRICT_JSON_MIGRATION.md` are in place, both referenced from the planning toctree, and both explicitly annotate that they are design-only and not `v0.31b1` scope.
- `docs/planning/PYSINDY_API_PREFLIGHT_AUDIT.md` is in place, records the pinned PySINDy version, enumerates the exact public surface `v0.31b1` will consume, and is referenced from the `v0.31b1` planning ticket as a mandatory prerequisite.
- `docs/specs/LABEL_REGISTRY.md`'s `residual_domain_policy` row cites `src/pdelie/reporting/summaries.py:1320-1327`; no other row is modified; the vocabulary is unchanged.
- The full test suite still passes; no file under `src/pdelie/` is modified; `pyproject.toml` still declares `version = "0.30.0"`.

---

# PDELie - Execution Plan (V0.31a)

**Status:** IN_PROGRESS

`v0.31a` is the design-only scope-freeze sub-release for the downstream discovery task bridge. It adds one scope document, one design document, one strict-JSON scope manifest, and two test files. No file under `src/pdelie/` is modified. No new optional dependency is added. No CI job is added. The `pyproject.toml` version stays pinned at `0.30.0`.

Decision label:

```text
downstream_discovery_task_bridge_design_only
```

## Sub-release contents (v0.31a)

- `docs/planning/V0_31_DISCOVERY_TASK_BRIDGE_SCOPE.md` — scope freeze covering the `pdelie.tasks.discovery` submodule design, the `TaskResult` schema shape, the `WeakPDELibrary` diagnostic wrapper policy, the supportability-policy update, and the release-gate consolidation confirmation.
- `docs/design/DISCOVERY_TASK_RESULT_SCHEMA.md` — TaskResult schema design document with per-field types, the strict-JSON NaN-safety contract (`_validate_strict_json_compatible` at `src/pdelie/reporting/summaries.py:196-202`), the `weak_contract` trigger predicate, and the WeakPDELibrary wrapper's distinct identifier strings.
- `configs/planning/v0_31_discovery_task_bridge_scope.json` — strict-JSON scope manifest. `release = "0.31a"`, `status = "in_progress"`, `parent_release = "0.31"`, `decision_label = "downstream_discovery_task_bridge_design_only"`, `guard_no_version_bump = "0.30.0"`.
- `tests/test_v0_31_discovery_task_bridge_scope.py` — scope-freeze test. Loads the JSON manifest and drives every assertion from it. Enforces required literal phrases in the scope doc, PLAN, ROADMAP, and API_STABILITY. Asserts forbidden root/submodule attributes are absent. Asserts no version bump. Asserts no premature pyproject sections or CI jobs.
- `tests/test_discovery_task_result_schema.py` — TaskResult schema tests. Imports the real `_validate_strict_json_compatible` from `pdelie.reporting.summaries` and proves it raises `SchemaValidationError` on:
  1. NaN in `train_residual.l2_norm` at the TaskResult top level
  2. NaN embedded in `underlying_discovery_result.coefficient_summary.l2_norm` (the load-bearing adversarial the peer-memo review flagged as absent)
  3. NaN inside the `weak_contract` subtree
  4. positive infinity in `train_residual.max_abs`

## Files modified (v0.31a)

- `docs/planning/ROADMAP.md` — new `v0.31a` row added above the existing `v0.31` row. The `v0.31` row's Notes now state "Design frozen by v0.31a. Runtime lands in v0.31b+." Every other row is preserved.
- `docs/planning/PLAN.md` — this file. Prepends the v0.31a section above the v0.32a planning note and the v0.30 release-close section; earlier sections are retained below.
- `docs/specs/API_STABILITY.md` — a Decision-only note for the frozen `v0.31a` scope-freeze sub-release is appended after the `v0.30.0` stable public-surface note and the `v0.30.1` planning note, mirroring the shape of the v0.30a-f notes. It records the decision label `downstream_discovery_task_bridge_design_only`, states that `v0.31a adds no new runtime public API`, references the composed `TaskResult` schema, and enumerates the deferred surfaces (SymmetryCandidate is v0.30.1 not v0.31; noise robustness deferred; multi-channel and 2D are `v0.34+`; LieGG / trained-model extraction is `v0.35a`; no PDEBench / The Well support claim; no external dataset benchmark claim).
- `docs/planning/index.rst` — `V0_31_DISCOVERY_TASK_BRIDGE_SCOPE` added to the planning toctree between `V0_30_SCOPE` and `archive/index`.
- `docs/design/index.rst` — `DISCOVERY_TASK_RESULT_SCHEMA` added to the design toctree.

## Explicit non-goals for v0.31a

- No `src/pdelie/` change. This is the load-bearing v0.31a design-only guard.
- No version bump (`pyproject.toml` stays at `0.30.0`).
- No new optional dependency; no new PySINDy version pin.
- No new CI job; no promotion of the v0.30e advisory `lint` / `typecheck` / `coverage` jobs to blocking.
- No root `pdelie` export.
- No SymmetryCandidate contract or wrapper — that surface is v0.30.1 responsibility, not v0.31.
- No WSINDy implementation, no weak nonperiodic surface, no noise robustness claim, no clean/noisy gate, no external dataset benchmark claim, no PDEBench support claim, no The Well support claim, no multi-channel or 2D FieldBatch dispatch, no LieGG / trained-model extraction.
- No standalone `tests/test_v0_31_release_gate.py` file. The v0.31 release-gate is a row in `configs/release_gate_manifest.json` replayed by `tests/test_release_gates.py`, following the v0.30f consolidation pattern.

## v0.31a Sub-Release Gate

v0.31a is complete when:

- the scope doc, design doc, and scope manifest above are in place and strictly JSON-compatible
- `docs/planning/ROADMAP.md`, `docs/planning/PLAN.md`, and `docs/specs/API_STABILITY.md` carry the `v0.31a` records above
- `tests/test_v0_31_discovery_task_bridge_scope.py` and `tests/test_discovery_task_result_schema.py` pass
- the full test suite still passes
- no file under `src/pdelie/` is modified
- no version bump in `pyproject.toml`
- no new optional dependency added
- no new CI job added

---

# PDELie - Planning Note (V0.32a design freeze — method_scores / uncertainty_report / calibration_report)

**Status:** IMPLEMENTED at `v0.32b`. This planning note is retained verbatim as history. The actual v0.32b shape (enriched-metadata per score entry, strict-JSON boundary, batch-only bootstrap) is documented in [`docs/design/GENERATOR_CONFIDENCE_ADDITIVE_FIELDS.md`](../design/GENERATOR_CONFIDENCE_ADDITIVE_FIELDS.md) and [`configs/planning/v0_32_method_scores_scope.json`](../../configs/planning/v0_32_method_scores_scope.json), which are more rigorous than the shape sketched below (each `method_scores` entry is `{value, direction, description, units}` rather than a bare float; `uncertainty_report` uses percentile bootstrap intervals with an explicit `resampling_unit ∈ {"batch", "trajectory", "not_applicable"}`, `seed`, `failed_resamples`, `warnings`, `diagnostic_only`; `calibration_report` mirrors the same `diagnostic_only` invariant).

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
