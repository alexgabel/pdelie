# V0.30.0 Release Readiness

## Decision

`v0.30.0` is ready as a Git-tag-only release.

Release conclusion:

```text
nonperiodic_readiness_and_low_order_finite_difference_diagnostics
```

## Package Metadata

- package version: `0.30.0`
- git tag: `v0.30.0`
- PyPI/TestPyPI: deferred until `v1.0` or later

Do not publish to TestPyPI or PyPI for `v0.30.0`.

## Public Surface

### New in `v0.30`

Runtime additions (submodule-only, no root export):

- `pdelie.derivatives.compute_finite_difference_derivatives(field, *, max_spatial_order=2)` — low-order finite-difference backend on scalar 1D nonperiodic uniform grids. Supports `u_t`, `u_x`, `u_xx` only. `u_xxx` and `u_xxxx` on nonperiodic data are not part of the stable surface.
- `pdelie.derivatives.compute_derivatives(field, *, backend="auto", max_spatial_order=2)` — dispatcher. `backend="auto"` routes periodic data to `spectral_fd` and nonperiodic data (Dirichlet, Neumann, `open_unknown`) to `finite_difference`. Explicit-mismatch calls raise `ScopeValidationError`; there is no silent fallback. Backend selection is recorded in `DerivativeBatch.config["backend_selected_by_boundary_condition"]` and `DerivativeBatch.config["backend_selection_reason"]`.
- `FieldBatch.SCHEMA_VERSION` bumped from `"0.1"` to `"0.2"`. `FieldBatch.LEGACY_SCHEMA_VERSIONS = frozenset({"0.1"})`; `from_dict` accepts both versions. Legacy string `boundary_conditions["x"]` payloads normalize to the structured form and are recorded in `preprocess_log` under operation `"schema_0_1_to_0_2_boundary_normalization"`.
- `pdelie.reporting.summarize_field_batch_readiness` and `pdelie.reporting.summarize_xarray_dataset_readiness` emit `boundary_condition_warnings: list[str]`; readiness downgrades from `"ready"` to `"needs_attention"` when warnings are present.
- `pdelie.reporting.summarize_residual_batch` records a `residual_domain_policy` field (default `"not_configured"`; auto-dispatched nonperiodic residuals emit `"interior_only"`; periodic residuals emit `"full_grid"`).
- Heat, Burgers, advection-diffusion, and reaction-diffusion residual evaluators route through `compute_derivatives(backend="auto")` when derivatives are omitted, and consume the interior-only residual-domain policy via a shared `build_residual_diagnostics_from_derivatives` helper. Heat and Burgers diagnostics gain `rms_residual` alongside `max_abs_residual`.

Internal (not public API):

- `pdelie._boundary` — internal `BoundaryFace`, `BoundaryConditionSpec`, `normalize_x_boundary_condition`, `get_x_boundary_type`, `is_x_periodic`. The module is intentionally underscore-prefixed; no submodule re-export.

### Retained from earlier `v0.x`

- Canonical `FieldBatch → DerivativeBatch → ResidualBatch → GeneratorFamily → VerificationReport` pipeline (frozen since `v0.1.x`).
- `pdelie.data.from_numpy`, `pdelie.data.from_xarray`, `pdelie.data.from_xarray_dataset` (unchanged; adapters now accept structured nonperiodic BCs and supported legacy nonperiodic strings; unsupported strings still raise `ScopeValidationError`).
- Existing PDE strong paths: Heat, Burgers, KdV (normalized short-horizon only), Fisher-KPP, advection-diffusion.
- `pdelie.derivatives.compute_spectral_fd_derivatives` — periodic-only; unchanged.
- Weak Heat / Burgers residual report slice (v0.8, periodic-only).
- Frozen invariant, closure, span, and confidence-report surfaces (v0.13–v0.22).
- Xarray Dataset ingestion (v0.28).
- Workflow recipes, support matrix, and rendered tutorials (v0.29).

## Cross-Cutting Hygiene (Phase 1, non-blocking)

`v0.30` includes the hygiene phase 1 landed by `v0.30e`:

- `[tool.ruff]` with `target-version = "py311"`, `line-length = 120`, `extend-select = ["E", "W", "F", "B", "I", "UP", "RUF", "NPY"]`.
- `[tool.mypy]` with a `strict = true` override narrowed to `pdelie.contracts`, `pdelie._boundary`, `pdelie.derivatives.*`. Broader modules run under lenient mypy.
- `[tool.coverage.*]` with `source = ["src/pdelie"]`, `branch = true`, `fail_under = 80`. Coverage baseline: **86%** on `src/pdelie/`.
- CI jobs `lint`, `typecheck`, `coverage` are **advisory / non-blocking** (`continue-on-error: true`). A red run reports findings but does not gate merges. Promotion to blocking is Phase 2 (post-v0.30).

## Release-Gate Consolidation (Narrow)

`v0.30` includes the narrow declarative release-gate consolidation landed by `v0.30f`:

- `configs/release_gate_manifest.json` — strict-JSON manifest that replays declarative content for every migrated release, including a new `v0.30` row for this release close. The manifest schema supports 11 assertion classes; files that use novel patterns (`forbidden_phrases_in_*`, CHANGELOG / README / ROADMAP_HISTORY phrase checks, disjunctive+forbidden per-page phrase rules, `required_json_fields`) are named in `excluded_functional_release_gate_files` with a per-file reason and their declarative content stays in the source file.
- `tests/test_release_gates.py` — parameterized replay of the manifest.
- CI job `v0_30f-release-gate` is renamed to `v0_30-release-gate` for the final `v0.30` release.
- Zero release-gate files deleted. All 26 `tests/test_v0_NN_release_gate.py` files retained; functional smoke tests intentionally remain explicit Python tests.

## Deferred Scope Confirmed

The following remain deferred, per the frozen `v0.30` scope and the `v0.30a` decision label:

- no PDEBench support claim
- no The Well support claim
- no file loaders, broad adapters, `pdelie.data.load_field_batch`, `from_pdebench`, `from_the_well`, `from_netcdf`, `from_zarr`, or dataset-adapter registries
- no KdV nonperiodic (KdV remains periodic-only)
- no KS nonperiodic (KS retains diagnostic/no-go status)
- no public KS runtime API
- no weak nonperiodic residuals or weak derivatives
- no public weak derivative backend, WSINDy design matrices, or weak sparse recovery
- no `u_xxx` / `u_xxxx` on nonperiodic data in the stable `v0.30` surface
- no finite-transform verification on nonperiodic translations (`pdelie.verification.verify_translation_generator` and `_apply_uniform_translation` remain periodic-only; overlap-crop is a `v0.31.5` topic)
- no `pdelie.symmetry.SymmetryMethod` registry (deferred to `v0.30.1`)
- no root `pdelie.discover_symmetries` (deferred to `v1.0` scope decision)
- no external symmetry-method ports (LieGAN, LaLiGAN, Ko-style sparse — deferred to `v0.33`+)
- no new root `pdelie` exports
- no neural or callable generator APIs
- no train/test policy, split-management, or leakage-prevention enforcement (`summarize_split_leakage_provenance` remains report-only)
- no operator symmetry
- no multi-generator fitting, finite multi-generator flows, BCH composition, or orbit charts
- no multi-channel or 2D contract widening (scalar 1D remains the stable target; deferred to `v0.34` scope decision)
- no lift of the `numpy<2` cap (deferred to Phase 3, `v0.32` or later)
- no Python-matrix expansion (CI stays Python 3.11 only)
- no promotion of the advisory `lint`/`typecheck`/`coverage` CI jobs to blocking (deferred to Phase 2)
- no PyPI or TestPyPI publication; package-index publishing remains deferred to `v1.0` or later

## Validation Checklist

Expected release validation:

```bash
python -m pytest tests/test_release_gates.py tests/test_current_release_gate.py tests/test_v0_30_scope_freeze.py tests/test_v0_30_hygiene_audit.py -q
python -m pytest
python -m ruff check .
python -m mypy src/pdelie/contracts.py src/pdelie/_boundary.py src/pdelie/derivatives/
python -m sphinx -b html -W --keep-going docs docs/_build/html
python -m build --sdist --wheel
git diff --check
```
