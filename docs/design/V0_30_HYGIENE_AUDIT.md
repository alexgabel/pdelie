# V0.30 Hygiene Audit

**Status:** AUDIT-ONLY in v0.30a. **Phase 1 IMPLEMENTED in v0.30e**: ruff, mypy (strict scope narrowed to `pdelie.contracts`, `pdelie._boundary`, `pdelie.derivatives.*`), and pytest-cov are configured in `pyproject.toml` and wired into three new non-blocking CI jobs (`lint`, `typecheck`, `coverage`). Coverage baseline at v0.30e HEAD: **86%** on `src/pdelie/`. Non-blocking gates: a red run reports findings but does not fail the workflow. Numpy `<2` cap and Python 3.11-only matrix remain unchanged; broadening those is Phase 3+ work. **Release-gate consolidation IMPLEMENTED narrowly in v0.30f**: `configs/release_gate_manifest.json` and the parameterized `tests/test_release_gates.py` replay declarative assertions for 18 releases; all 26 per-version files are retained (functional smoke tests intentionally remain explicit Python tests). See "Release-gate consolidation" below.

This document audits the current state of cross-cutting code-quality infrastructure (lint, type-checking, coverage, Python matrix, NumPy upper bound, release-gate proliferation, optional-dependency import policy, JSON-strict reporting policy) and proposes staged enforcement.

## Lint status

No `[tool.ruff]`, `[tool.black]`, or `[tool.flake8]` configuration is present in `pyproject.toml`. The current file contains only `[build-system]`, `[project]`, `[project.urls]`, `[project.optional-dependencies]`, `[tool.setuptools]`, `[tool.setuptools.packages.find]`, and `[tool.pytest.ini_options]`.

There is no `.pre-commit-config.yaml` at the repository root.

The project's documented manual lint step is the whitespace check `git diff --check` (referenced in `CONTRIBUTING.md:88` under "Check whitespace"). This is run by hand at PR time.

Codebase shape: a quick scan of `src/pdelie/` shows consistent `from __future__ import annotations` and inline PEP-604 unions (`str | None`). A default ruff configuration with selections `["E", "W", "F", "B", "I", "UP", "RUF", "NPY"]` is plausible without large refactor cost.

## Type-checker status

No `[tool.mypy]`, `[tool.pyright]`, or equivalent configuration in `pyproject.toml`. No `mypy.ini`, `.mypy.ini`, `pyrightconfig.json`, or equivalent at the repository root.

The codebase uses typed parameters and return annotations throughout (e.g. `src/pdelie/derivatives/spectral_fd.py` carries full annotations, `src/pdelie/symmetry/fitting/translation_baseline.py` annotates SVD results). A strict-on-`src/pdelie/contracts.py` and `src/pdelie/derivatives/` configuration is plausible immediately; broader strictness will require some tightening (untyped dictionaries in `diagnostics: dict[str, object]` fields where the values are heterogeneous).

## Coverage status

No `[tool.coverage]` in `pyproject.toml`. No `coverage` or `pytest-cov` in the `test` optional-dependency group (verified in `pyproject.toml` lines 55-62, which lists `build`, `matplotlib`, `pysindy`, `scikit-learn`, `pytest`, `xarray`). CI emits no `coverage.xml` artifact.

The test suite is large — 689 test functions across 106 test files. Coverage measurement is feasible once `pytest-cov` is added; the absolute coverage number on `src/pdelie/` is likely high given the inventory of release-gate, public-API audit, and per-module tests.

## Python version matrix

CI runs only `python-version: "3.11"`, verified across all four jobs in `.github/workflows/ci.yml`:

- `v0_29-release-gate` — Python 3.11
- `docs-build` — Python 3.11
- `editable-tests` — Python 3.11
- `package-smoke` — Python 3.11

`pyproject.toml` declares `requires-python = ">=3.11"`. No upper bound is declared. There is no validation against Python 3.12 or 3.13.

## NumPy upper bound

`pyproject.toml` line 32: `numpy>=1.24,<2`. This excludes the entire NumPy 2.x line.

The scientific Python ecosystem completed the NumPy 2.x migration during 2024. Major downstream consumers (SciPy, scikit-learn, xarray, PyTorch) are all on 2.x-compatible code paths. The `numpy<2` cap is now an adoption blocker rather than a safety measure.

A NumPy 2.x compatibility validation side job is feasible; the codebase uses NumPy in mainstream ways (FFT, gradient, SVD, linspace, basic broadcasting), all of which have stable APIs across the 1.x/2.x boundary. Likely-affected sites are limited to:

- type-hint usage of `np.bool_` / `np.integer` / `np.generic` (compatible across versions)
- `np.fft` calls (compatible)
- `np.random.default_rng` (compatible, used as `np.random.default_rng(seed)`)

Estimated 1–2 days to validate and lift the cap, but this work is **not** in scope for v0.30 proper.

## Release-gate proliferation

Counted at v0.30a baseline: **26 per-version release-gate test files** in `tests/`:

- `tests/test_v0_4_release_gate.py` through `tests/test_v0_9_release_gate.py` (6 files)
- `tests/test_v0_10_release_gate.py` through `tests/test_v0_29_release_gate.py` (20 files)

Releases `v0.1`, `v0.2`, `v0.3` did not produce dedicated release-gate test files; the modern pattern began at `v0.4`.

Each file follows the same structural pattern: read several documents by path, assert specific phrases are present, assert forbidden names are not on `pdelie` or any submodule, validate JSON manifests for strict JSON compatibility. The structure is mechanical; the duplication is significant.

This audit recommends consolidation in v0.30 proper. See "Release-gate consolidation" below.

## Optional-dependency import pattern

The current pattern is correct. Reference implementation at `src/pdelie/discovery/pysindy_adapter.py:12-20`:

```
def _require_discovery_dependencies():
    try:
        pysindy = importlib.import_module("pysindy")
        importlib.import_module("sklearn")
    except (ModuleNotFoundError, ImportError, ValueError) as exc:
        raise ImportError(
            "PySINDy discovery adapter requires pdelie[downstream] or pdelie[test]."
        ) from exc
    return pysindy
```

Key properties:

- Optional dependencies are imported on first use, not at module load time.
- The import error is raised with an actionable message naming the optional-extras install target.
- The function is private (leading underscore) and called only from inside `fit_pysindy_discovery`, never at package-level import.

The viz layer follows the same pattern. `tests/test_public_api.py:462-487` verifies this by mocking out `matplotlib` and confirming that `import pdelie.viz` still succeeds; only at first call to `plot_*` does the `ImportError` surface.

This policy must remain unchanged through v0.30 and beyond. New optional extras (e.g., a future `pdelie[generative]` for LieGAN-style methods) must follow this exact pattern.

## Strict JSON / no-NaN policy

The current policy is correct. Reference helpers exist in the reporting layer:

- `_validate_strict_json_compatible(value, *, name)` is called by `summarize_*` helpers throughout `src/pdelie/reporting/summaries.py` and elsewhere
- The pattern `json.loads(json.dumps(matrix, allow_nan=False)) == matrix` is the gate (verified in `tests/test_v0_29_release_gate.py:93`)
- `_json_safe(value)` (in `src/pdelie/verification/__init__.py:28-37`) normalizes numpy arrays and scalars to Python natives before serialization

Any new reporting output landed in v0.30 proper must follow this discipline:

- No `float("nan")` in serialized output. Use `None` or an explicit unavailable-status string.
- No `numpy.ndarray`, `numpy.generic`, or `pandas` objects in serialized output. Convert to nested Python lists/dicts.
- No tensor objects, file paths, or model handles in serialized output.

This policy is non-negotiable for new APIs.

## Staged enforcement

No `pyproject.toml` or CI change in v0.30a. The audit recommends:

### Phase 0 — v0.30a (this release)

Audit-only. This document records the baseline. No `pyproject.toml` change, no CI change. The negative tests in `tests/test_v0_30_hygiene_audit.py` confirm that no premature enforcement has landed.

### Phase 1 — v0.30 proper

- Add `[tool.ruff]` with `target-version = "py311"`, selections `["E", "W", "F", "B", "I", "UP", "RUF", "NPY"]`, and the project's whitespace-conscious line length (likely 100 or 120). Add a `lint` CI job that runs `ruff check .` as **warning-only / non-blocking**.
- Add `[tool.mypy]` with `strict = true` initially scoped to:
  - `src/pdelie/contracts.py`
  - `src/pdelie/derivatives/`
  - `src/pdelie/data/`
  - `src/pdelie/residuals/`
  Leave the rest lenient. Add a `typecheck` CI job as **warning-only / non-blocking**.
- Add `[tool.coverage.run]` with `source = ["src/pdelie"]` and `branch = true`; add `[tool.coverage.report]` with an initial floor `fail_under = 80` (conservative; raise later). Add `pytest-cov` to the `test` optional-dependency group. Coverage job runs but **does not gate merges** initially.

Phase 1 is opt-in by CI: the existing `editable-tests`, `package-smoke`, `docs-build`, and `v0_29-release-gate` (which becomes `v0_30-release-gate`) jobs continue unchanged and remain the merge gates.

### Phase 2 — v0.30.1 or v0.31

- Tighten `[tool.mypy].strict` across all of `src/pdelie/`. Address strictness violations site by site.
- Promote `lint` and `typecheck` CI jobs to **blocking**.

### Phase 3 — v0.32

- Expand CI matrix to `python-version: ["3.11", "3.12", "3.13"]` for `editable-tests` and `package-smoke`.
- Add a NumPy 2.x side job: `editable-tests-numpy2x` that installs `numpy>=2,<3` and runs the test suite. Initially warning-only.

### Phase 4 — v1.0

- Lift the `numpy<2` upper bound to `numpy<3` once the 2.x side job has soaked for at least two releases without regressions.

## Release-gate consolidation

**Landed in v0.30f — narrowly.** The consolidation is by manifest addition, not by file deletion. The design goal — one parameterized test driven by a JSON manifest — was implemented, but the "replace 26 files" outcome that v0.30a proposed is scoped down: only declarative assertions that fit the 11 supported classes migrate to the manifest. Functional smoke and numeric behavior tests continue as explicit Python tests. Files are retained regardless.

### What v0.30f ships

- `configs/release_gate_manifest.json` — strict-JSON manifest with `summary_type = "pdelie_declarative_release_gate_manifest"`. 18 release rows migrated, spanning `v0.10`, `v0.13`–`v0.25`, `v0.27`–`v0.29`, and a self-check row for `v0.30f`. `release_gate_manifest.json` is the sole source of truth for declarative assertions moving forward.
- `tests/test_release_gates.py` — single parameterized test file that dispatches over the 11 supported assertion classes:
  - `required_phrases_in_scope_doc`, `required_phrases_in_api_stability`, `required_phrases_in_roadmap`, `required_phrases_in_plan`, `required_phrases_in_readiness_doc`
  - `forbidden_root_attributes`, `forbidden_submodule_attributes`, `required_root_attributes`, `required_submodule_attributes`
  - `strict_json_manifests`, `notebook_structural_checks`
- CI: the `v0_29-release-gate` job is renamed to `v0_30f-release-gate`. Its invocation invokes `tests/test_current_release_gate.py`, the new `tests/test_release_gates.py`, and every retained `tests/test_v0_NN_release_gate.py` (v0.4 through v0.29).

### Classification (Explore audit, v0.30f)

- **`functional_only` (2 files):** `test_v0_4_release_gate.py`, `test_v0_7_release_gate.py`. No declarative content to replay; retained unchanged.
- **`mixed` (23 files):** `test_v0_6_release_gate.py`, `test_v0_8_release_gate.py`, `test_v0_9_release_gate.py`, `test_v0_10_release_gate.py`, and every file `test_v0_11_release_gate.py` through `test_v0_29_release_gate.py`. Declarative content that fits the 11 supported classes is replayed via the manifest; functional/numeric assertions stay in the source file.
- **`declarative_only`:** zero files. This is why no file is deleted in v0.30f.

### Files excluded from the manifest and why

Some `mixed` files use assertion patterns outside the 11 supported classes. The manifest does not partially convert these; their declarative content stays in the source file, and the file is listed under `excluded_functional_release_gate_files` in the manifest with a per-file reason. These are the excluded files:

- `v0.4` (`tests/test_v0_4_release_gate.py`) — reason: `pure_numeric_vertical_slice`. No declarative content at all.
- `v0.6` (`tests/test_v0_6_release_gate.py`) — reason: `declarative_block_embedded_in_functional_test_tail`. Declarative attribute checks are nested inside a functional pipeline test.
- `v0.7` (`tests/test_v0_7_release_gate.py`) — reason: `pure_numeric_bridge_parity`. No declarative content at all.
- `v0.8` (`tests/test_v0_8_release_gate.py`) — reason: `schema_gap_forbidden_phrases_in_api_stability`. Uses `... not in api_stability` on specific phrases; the manifest does not yet support `forbidden_phrases_in_*`.
- `v0.9` (`tests/test_v0_9_release_gate.py`) — same reason as `v0.8`.
- `v0.11` (`tests/test_v0_11_release_gate.py`) — reason: `interleaved_runtime_and_declarative_in_same_test`. Test 1 mixes `compute_spectral_fd_derivatives` calls with declarative assertions inside one function.
- `v0.12` (`tests/test_v0_12_release_gate.py`) — reason: `schema_gap_changelog_readme_roadmap_history_phrase_checks`. Uses `CHANGELOG.md`, `README.md`, and `docs/planning/archive/ROADMAP_HISTORY.md` phrase checks; the manifest does not yet support those doc-path classes.
- `v0.26` (`tests/test_v0_26_release_gate.py`) — same reason as `v0.8` and `v0.9`.

### What did **not** get consolidated

- 26 per-version `tests/test_v0_NN_release_gate.py` files. All retained. No file deleted in v0.30f.
- Every `mixed` file's functional/numeric assertions. These remain explicit Python tests.
- The v0.29 `SUPPORT_MATRIX.md` phrase checks, `docs/tutorials/*.nblink` link checks, `docs/workflows/*.md` disjunctive+forbidden per-page phrase rules, and `required_json_fields` structural checks on the support-matrix manifest — all schema gaps for the current 11-class manifest. They stay in `tests/test_v0_29_release_gate.py`.

### Why this is still worth doing

Even with zero deletions, v0.30f delivers a durable pattern:

1. Future release gates (v0.30 proper, v0.31+) that fit the 11 classes can skip a Python file entirely — add a row to the manifest instead.
2. The manifest is a strict-JSON, machine-readable audit surface: what phrases must appear in which docs, what attributes must (not) exist on which modules. Downstream tooling can consume it.
3. Schema gaps are named explicitly (`excluded_functional_release_gate_files`), so future manifest-schema extensions (e.g. `forbidden_phrases_in_api_stability`, `required_phrases_in_readme`) can be planned rather than accidental.

## Summary table

| Concern | Current state | v0.30 proper target | Final target |
| --- | --- | --- | --- |
| Lint | none | ruff non-blocking | ruff blocking (v0.30.1+) |
| Type-checker | none | mypy strict on core, non-blocking | mypy strict everywhere, blocking (v0.30.1+) |
| Coverage | none | pytest-cov non-blocking, floor 80 | gate at 85 (v0.30.1+) |
| Python matrix | 3.11 only | 3.11 only (no change) | 3.11/3.12/3.13 (v0.32) |
| numpy upper bound | `<2` | `<2` (no change) | `<3` (v1.0) |
| Release-gate files | 26 hand-maintained | 1 parameterized + manifest | 1 (stable) |
| Optional imports | lazy via `importlib.import_module` | unchanged | unchanged |
| JSON strictness | `allow_nan=False` enforced | unchanged | unchanged |
