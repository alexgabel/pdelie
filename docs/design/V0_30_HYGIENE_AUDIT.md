# V0.30 Hygiene Audit

**Status:** AUDIT-ONLY in v0.30a. **Phase 1 IMPLEMENTED in v0.30e**: ruff, mypy (strict scope narrowed to `pdelie.contracts`, `pdelie._boundary`, `pdelie.derivatives.*`), and pytest-cov are configured in `pyproject.toml` and wired into three new non-blocking CI jobs (`lint`, `typecheck`, `coverage`). Coverage baseline at v0.30e HEAD: **86%** on `src/pdelie/`. Non-blocking gates: a red run reports findings but does not fail the workflow. Numpy `<2` cap and Python 3.11-only matrix remain unchanged; broadening those is Phase 3+ work.

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

Recommendation for v0.30 proper:

Replace the 26 per-version release-gate test files with **one parameterized test** driven by a manifest file at `configs/release_gate_manifest.json`. The manifest lists, per past release:

- the file paths that must exist (`docs/planning/V0_NN_SCOPE.md`, `docs/releases/V0_NN_RELEASE_READINESS.md`)
- the phrases that must appear in `docs/planning/V0_NN_SCOPE.md`, `docs/planning/ROADMAP.md`, `docs/specs/API_STABILITY.md`, and `docs/planning/PLAN.md` for the *current* release
- the names that must not appear on `pdelie` or any submodule at the time of that release

The consolidated test reads the manifest and parameterizes its assertions over the listed releases. The existing `tests/test_v0_29_release_gate.py` is the template for the parameterized test body: helpers `_repo_path`, `_repo_text`, `_repo_json`; per-release assertions on file existence, phrase presence, forbidden-name absence, and JSON-strict manifest validation.

The current `tests/test_v0_NN_release_gate.py` files (for `NN ∈ {4..29}`) are removed in the same release that adds the consolidated test. The consolidated test must pass at parity with the removed files before deletion.

This change reduces 26 hand-maintained files to 1 parameterized test + 1 JSON manifest. The maintenance burden becomes editing the manifest, not adding a new test file per release.

**This consolidation is scoped to v0.30 proper, not v0.30a.** v0.30a only specifies the consolidation contract. The `tests/test_v0_30_hygiene_audit.py::test_v0_30_hygiene_audit_documents_release_gate_consolidation_proposal` test verifies this section contains the required text and that the consolidation lands in v0.30 proper, not v0.30a.

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
