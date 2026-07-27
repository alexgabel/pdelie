# V0.32 Release Readiness

## Release Target

- package version: `0.32.0`
- git tag: `v0.32.0` (to be cut after review approval; **do not tag until then**)
- package-index publication: deferred until `v1.0` or later

`v0.32.0` is a Git-tag-only release. Do not publish to TestPyPI or PyPI for `v0.32`. Do not run TestPyPI or PyPI publishing for `v0.32`.

## Consolidation Policy

`v0.32.0` consolidates four internal sub-milestones under a single tag per the solo-dev consolidation policy. The four sub-milestones landed on `main` as separate squash-merged PRs; none was tagged individually.

- **v0.32a** — modern-runtime migration (PR #103, merged as `e0fbefc`).
- **v0.32b** — strict method-score, uncertainty, and calibration reporting (PR #104, merged as `86fc84e`).
- **v0.32c** — composed candidate-to-discovery workflow example (PR #105, merged as `dd5dbd0`).
- **v0.32d** — external-data readiness cookbooks (PR #106, merged as `8c8767a`).

Release decision label: `v0_32_0_consolidated_modernization_and_external_readiness`.

## Done

### v0.32a — modern runtime

- Python `>=3.12` minimum; NumPy 2.x; PySINDy 2.1.x; scikit-learn 1.4+; scipy 1.14+.
- Six PySINDy 2.x API-break sites migrated across `pdelie.discovery`, `pdelie.tasks`, `pdelie.examples`, and test helpers.
- Private prototype `_pysindy2_prototype.py` deleted.
- Temporary `setuptools<82` co-install cap retired.
- `SymmetryCandidate` reserved-representation construction hardened from warning-gate to `ScopeValidationError`.
- CI matrix: `v0_32-release-gate` on py3.12 + py3.13 blocking; `py314-core-only-advisory` core-only.

### v0.32b — additive reporting fields

- `pdelie.reporting.summarize_generator_confidence` gains three additive optional fields (`method_scores`, `uncertainty_report`, `calibration_report`); all default to `None`; strict-JSON boundary; `_CONFIDENCE_LABELS` invariant preserved.
- `pdelie.reporting.enrich_method_scores(values, metadata)` — helper that pairs a plain `dict[str, float | None]` with a method's frozen `SCORE_METADATA` into the enriched-form entry.
- `pdelie.symmetry.methods.polynomial_translation_svd` gains `SCORE_METADATA` and `bootstrap_uncertainty(field, residual_evaluator, *, seed, num_resamples=64, interval_level=0.95, min_units=8, resampling_unit="batch")`. Batch-only resampling; row-level bootstrap refused with `ScopeValidationError`; percentile intervals; deterministic under seed; fit-per-resample; `diagnostic_only=True`.
- Frozen four-score names: `{span_distance, residual_l2, error_curve_max, svd_condition_number}`.
- 20 v0.32b contract tests in `tests/test_v0_32b_method_scores_uncertainty.py`.

### v0.32c — candidate-to-discovery workflow

- `pdelie.reporting.summarize_candidate_to_discovery_workflow(...)` — composed strict-JSON summary carrying 15 explicit ordered stages. Blocked / skipped / unavailable stages carry a `candidate_to_discovery_workflow_stage_marker` payload — never silently omitted.
- `pdelie.examples.candidate_to_discovery_workflow.run_candidate_to_discovery_workflow_example(scenario=...)` and CLI `python -m pdelie.examples.candidate_to_discovery_workflow`. Two deterministic scenarios: `"successful"` fully executable end-to-end; `"valid_but_not_useful_static"` a provenance-backed static illustration.
- v0.32.0 release-close hardening: the workflow feeds the FULL training FieldBatch (`batch_size>1`) to `run_pysindy_pde_task` — no silent first-trajectory slicing. `evidence_conclusion.reasons` name the exact `downstream_comparison.metric_key` (`heldout_residual_l2_norm`).
- 20+2 v0.32c contract tests in `tests/test_v0_32c_candidate_to_task_workflow.py` (2 v0.32.0 release-close additions: no silent slicing; reasons name metric_key).

### v0.32d — external-data readiness cookbooks

- `pdelie.examples.pdebench_burgers_1d_readiness.run_pdebench_burgers_1d_readiness_cookbook(...)` + CLI. Narrow readiness cookbook pinned to a single DaRUS shard: `1D_Burgers_Sols_Nu0.001.hdf5`, DOI `10.18419/darus-2986`, CC-BY-4.0, MD5 `b4be2fc3383f737c76033073e6d2ccfb`. Emits strict-JSON `pdelie_external_data_readiness` reports with a frozen 9-label conclusion vocabulary. Optional-dependency extra: `pip install 'pdelie[pdebench]'` (h5py only). Absent the extra, an `ImportError` names the extra explicitly.
- `pdelie.examples.the_well_feasibility_scan.run_the_well_feasibility_scan()` + CLI. Metadata-only scan; no network I/O in default CI. Distinguishes the Ohana et al. 2024 paper count (`paper_dataset_count = 16`) from the current PolymathicAI catalogue count (`catalogue_entry_count = 23`, with hosted variants like `mhd_64` / `mhd_256` split). Every entry is `scalar_1d_extractable=False`; frozen conclusion `blocked_multichannel_required`.
- Frozen strict-JSON configs shipped both in-tree (`configs/external_data/`) and inside the package (`src/pdelie/examples/_external_data/`) for wheel installability.
- New optional extra `[pdebench]` (h5py-only, `h5py>=3.10`). No implication of broad PDEBench support; scoped strictly to the frozen v0.32d cookbook.
- 21+1 v0.32d contract tests in `tests/test_v0_32d_external_data_readiness.py` (1 v0.32.0 release-close addition: paper vs catalogue count distinction).

### Release-close preflight — done

- **Preflight #1** — modern env recreated on Python 3.12.13 (also py3.13.14); NumPy 2.5.1; PySINDy 2.1.0; h5py 3.16.0; scipy 1.18.0; sklearn 1.9.0.
- **Preflight #2** — full pytest on py3.12: **1430 passed, 2 skipped, 0 failed**. Full pytest on py3.13: **1427 passed, 2 skipped, 0 failed** (pre-preflight-additions count).
- **Preflight #3 (batch_size>1 for `run_pysindy_pde_task`):** the multi-trajectory path is exercised in the v0.32c workflow example on `batch_size=4` training and `batch_size=4` orbit output; both `train_residual` and `heldout_residual` populate correctly. `_slice_first_trajectory` was removed; the v0.32c workflow now feeds the FULL FieldBatch. New test `test_case_12b_no_silent_first_trajectory_slicing_in_discovery_tasks` guards against regression.
- **Preflight #4 (PDEBench cookbook h5py packaging):** `[pdebench]` extra added to `pyproject.toml` (h5py-only). The v0.30 hygiene invariant vocabulary was relaxed from `{downstream, xarray, viz, test}` to include `pdebench` with a pinned narrow allowlist (`["h5py>=3.10"]`). Absent the extra, the loader raises an `ImportError` that names the extra explicitly. Test-only h5py installation is no longer the sole path.
- **Preflight #5 (workflow metric_key labeling):** `evidence_conclusion.reasons` now contain the exact `metric_key` from `downstream_comparison` (e.g. `candidate_guided_heldout_residual_l2_norm_did_not_strictly_beat_baseline`). New test `test_case_12c_evidence_conclusion_reasons_name_metric_key` guards against reintroducing an unlabeled generic delta.
- **Preflight #6 (The Well paper vs catalogue count):** the emitted scan payload carries both `paper_dataset_count = 16` (Ohana et al. 2024, abstract & Table 1) and `catalogue_entry_count = 23` (current PolymathicAI catalogue), with an explicit note enumerating the split hosted variants. New test `test_case_14b_the_well_distinguishes_paper_count_from_catalogue_count` guards against reintroducing an ambiguous single count.

### Mechanical release close — done

- `pyproject.toml` version `0.31.0` → `0.32.0`.
- `docs/conf.py` release `0.31.0` → `0.32.0`; version `0.31` → `0.32`.
- CHANGELOG entry authored (this document's Added / Compatibility / non-claims sections mirrored in `CHANGELOG.md`).
- `docs/specs/support_matrix.v0_32.json` authored (strict-JSON, carries every v0.32 sub-milestone's non-claim vocabulary).
- Release-gate manifest consolidated to a single `0.32` row (the four sub-milestone rows are collapsed into one).
- CI release-gate job renamed `v0_32-release-gate` → `v0_32_0-release-gate`.
- Legacy line: `release/v0.31.x` maintenance branch cut from the `v0.31.0` tag. Maintenance-end policy documented in `docs/design/RUNTIME_COMPATIBILITY_POLICY.md`: security-only fixes for 12 months from the v0.32.0 tag, then archived.

## Explicit non-claims (v0.32.0)

- No new PDE.
- No new symmetry method.
- No new `SymmetryCandidate` discriminator.
- No `discovery_task_result` schema change (still 22 keys).
- No `pdelie_weak_pde_library_diagnostic` schema change (still 27 keys).
- No new `summary_type` beyond what the v0.32a-d sub-milestones each declared.
- No root `pdelie` export.
- No generic symmetry-discovery claim. PDELie continues to score and verify caller-supplied candidates, not to discover symmetries autonomously.
- No external-data recovery-benchmark claim.
- No noise-robustness claim. No WSINDy claim.
- No nonperiodic finite-transform verification (deferred).
- No multi-channel / 2D contract widening (deferred to v0.34+).
- No PyPI / TestPyPI publication.

## Remaining tag blockers

None on the codebase. Tagging is gated on **explicit review approval only**.

## Suggested tag command

```bash
git tag -a v0.32.0 -m "PDELie v0.32.0 — consolidated modernization and external-data readiness"
git push origin v0.32.0
```

Do not run this until review approval. TestPyPI / PyPI publication is out of scope for `v0.32.0`.
