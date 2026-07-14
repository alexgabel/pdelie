# V0.31.0 Release Readiness

## Decision

`v0.31.0` is ready as a Git-tag-only release.

Release conclusion:

```text
downstream_discovery_task_bridge
```

## Package Metadata

- package version: `0.31.0`
- git tag: `v0.31.0` (do not create until explicitly authorized after review)
- PyPI/TestPyPI: deferred until `v1.0` or later

Do not publish to TestPyPI or PyPI for `v0.31.0`.

## Public Surface

### New in `v0.31` — downstream discovery task bridge (submodule-only)

The v0.31 arc adds one narrow scientific delta: a submodule-only downstream discovery task bridge under `pdelie.tasks`. No root `pdelie` export is added. The `pdelie.residuals.weak_1d` PDELie-native weak-derivative path remains available and distinct.

Stable public submodule surfaces:

- `pdelie.tasks.run_pysindy_pde_task` — executable PySINDy `PDELibrary`-backed sparse-discovery task runner (v0.31b1). Periodic scalar 1D only. Layer-1 boundary-condition guard raises `PySINDyDiscoveryUnsupportedBoundaryError` before any PySINDy call when `is_x_periodic(field)` is false. Returns a strict-JSON `discovery_task_result`.
- `pdelie.tasks.summarize_discovery_task_result` — strict-JSON payload assembler (v0.31b1). Enforces the 22-key composed schema, records `summary_type = "discovery_task_result"`, `summary_schema_version = "0.1"`, and `pysindy_bridge_variant = "periodic_only_v1"`. Embeds the v0.31b0-frozen backend-native `summarize_discovery_result` verbatim under `underlying_discovery_result`.
- `pdelie.tasks.PySINDyDiscoveryUnsupportedBoundaryError` — subclass of `ScopeValidationError`. Raised at the `pdelie.tasks.discovery` entry when a nonperiodic-x `FieldBatch` is supplied.
- `pdelie.tasks.inspect_pysindy_weak_pde_library` — diagnostic-only wrapper around PySINDy's `WeakPDELibrary` (v0.31b2). Two-layer scope guard (periodic-x, uniform x/t grids, batch==1, single var, K-scaled grid-sufficiency floor `max(8, 4*K)`, unsupported PySINDy API). Returns a strict-JSON `pdelie_weak_pde_library_diagnostic`.
- `pdelie.tasks.summarize_pysindy_weak_pde_library_diagnostic` — strict-JSON payload assembler for the diagnostic-only wrapper (v0.31b2). Enforces the 27-key composed schema.
- `pdelie.tasks.WeakPDELibraryDiagnostic` — caller-declared, JSON-safe library-configuration dataclass with `as_dict()` (v0.31b2). Rejects NaN/Inf at construction via `_validate_strict_json_compatible`.
- `pdelie.examples.run_downstream_discovery_task_bridge_example` and CLI `python -m pdelie.examples.downstream_discovery_task_bridge` (v0.31c) — composed JSON-only demonstration runner. Not a new report schema.

All names above are exposed from `pdelie.tasks` (or `pdelie.examples`) as their canonical submodule-only public surface. **None** appear at the root `pdelie` namespace.

### Discovery task support

- input_layout: `"scalar_1d_uniform"`.
- periodic scalar 1D only.
- backend: PySINDy `PDELibrary` (or any caller-configured `pysindy.SINDy` model per the v0.31b1 adapter loosening).
- output `summary_type`: `"discovery_task_result"`.
- 22-key top-level composed schema.
- Strict-JSON composition: `_validate_strict_json_compatible(payload, name="discovery_task_result summary")` invoked exactly once at the final composition boundary.
- `pysindy_bridge_variant = "periodic_only_v1"` on every produced TaskResult.
- Adapter loosening: `fit_pysindy_discovery` accepts a caller-supplied `pysindy_model` kwarg (v0.31b1); `config != None` still raises; the `config=None, pysindy_model=None` default path is byte-preserved for existing v0.30 callers.

### Weak diagnostic support

- output `summary_type`: `"pdelie_weak_pde_library_diagnostic"`.
- `diagnostic_only = True` on every produced summary.
- 27-key top-level composed schema.
- `method_family = "pysindy_weak_pde_library_polynomial_gauss_v1"`.
- `test_function_family = "pysindy_weak_pde_library_polynomial_bump_v1"`.
- `quadrature_rule = "pysindy_weak_pde_library_composite_gauss_v1"`.
- **No WSINDy benchmark claim.**
- **No noise-robustness claim.**
- **No numerical equivalence with `pdelie.residuals.weak_1d`.** The PDELie-native weak-derivative path remains available and is retained through at least `v0.32` close.
- Two-layer scope guard: nonperiodic-x rejected via `PySINDyDiscoveryUnsupportedBoundaryError` (reused from v0.31b1); scope violations (dims, var_names, batch, uniform grids, K-scaled grid-sufficiency floor, unsupported PySINDy API) rejected via `ScopeValidationError` / `SchemaValidationError`.

### Retained from earlier `v0.x`

- Canonical `FieldBatch → DerivativeBatch → ResidualBatch → GeneratorFamily → VerificationReport` pipeline (frozen since `v0.1.x`).
- All `v0.30` runtime and reporting surfaces including `BoundaryConditionSpec`, structured `FieldBatch` schema 0.2, low-order finite-difference derivative backend, interior-only residual diagnostics, and the ambient supportability report layer.
- `pdelie.residuals.weak_1d` behavior — unchanged.

## Compatibility Policy

The v0.31 downstream task bridge is a **temporary compatibility surface**. It validates against a single narrow PySINDy generation, and its compatibility constraints are all bounded:

- **PySINDy**: `>=1.7.5,<2` under `python_version < '3.12'`.
- **scikit-learn**: `>=1.2.2,<1.3` under `python_version < '3.12'`.
- **setuptools**: `<82` under `python_version < '3.12'` — temporary constraint added by v0.31c1 because pysindy 1.7.5 imports `pkg_resources` at package init and setuptools 82 removed that module.
- **Python**: downstream task support is validated on Python 3.11 only.

The v0.31c1 adversarial matrix confirmed:

- setuptools 81.0.0: pass end-to-end.
- setuptools 82.0.0: install succeeds but `import pysindy` fails with `ModuleNotFoundError: No module named 'pkg_resources'`.
- setuptools 83.0.0: same failure mode as 82.

Post-fix rebuilt-wheel verification confirms pip auto-downgrades an ambient setuptools 82/83 to 81 without any user co-install. Fresh-venv baseline: setuptools stays at the bundled `65.5.0`, untouched.

Deferred to `v0.31.1`:

- **PySINDy 2.x support**. Four independent 2.x API breaks are documented in `docs/design/PYSINDY_COMPATIBILITY_POLICY.md` (SINDy kwargs removed; SINDy.fit signature; SINDy.differentiate removed; PDELibrary/WeakPDELibrary kwargs).
- **Python 3.12+ downstream support**. The `[downstream]` extra is marker-scoped to `python_version < '3.12'`; a user on Python 3.12+ who invokes the task bridge receives a targeted, actionable error message that names the v0.31.1 deferral and states that reinstalling the same extra will not fix the environment.
- **numpy>=2 floor bump**. Coordinated with the PySINDy 2.x port.

No hidden manual installation step is required in the documented user path.

## Public Example

The v0.31c JSON-only demonstration runner:

- Public submodule surface: `pdelie.examples.run_downstream_discovery_task_bridge_example`.
- CLI: `python -m pdelie.examples.downstream_discovery_task_bridge`.
- Composes both v0.31 paths on one manufactured periodic scalar 1D Heat field (T=64, X=64, K=16, seed=31000).
- 7-key top-level `summary_type = "downstream_discovery_task_bridge_example"`. NOT a new report schema — the composed wrapper carries the verbatim v0.31b1 `discovery_task_result` (22 keys) and v0.31b2 `pdelie_weak_pde_library_diagnostic` (27 keys) as children.
- Deterministic under the frozen seed via a private `_legacy_numpy_rng_seed_scope` context manager (v0.31c1). Not thread-safe — PySINDy 1.7.5 uses the legacy `np.random` global RNG and does not accept a modern `Generator`.
- Uses only public submodule APIs (AST-checked in `tests/test_v0_31c_downstream_task_bridge_example.py`).

## Expected xfails ledger

The v0.31.0 release close retains three declared xfails, each with a non-empty reason and each assigned to a documented follow-up milestone. None represent a genuine failure masked to make the suite green.

| Node id | Reason | Strictness | Owner milestone | Planned disposition |
|---|---|---|---|---|
| `tests/test_v0_31b3_pysindy_compatibility_policy.py::test_unsupported_major_pysindy_version_rejected_by_discovery_task_runner` | The runtime version guard on `run_pysindy_pde_task` has not been landed. The test monkeypatches `pysindy.__version__` to `"999.0.0"` and expects a `ScopeValidationError`; no such guard exists today. | runtime-conditional `pytest.xfail(...)` inside `try/except pytest.fail.Exception:` (not decorator strict) | `v0.31.1` (PySINDy 2.x port introduces `_pysindy_compat._detect_api_generation` gate) | KEEP as xfail until v0.31.1 lands the guard |
| `tests/test_v0_31b3_pysindy_compatibility_policy.py::test_unsupported_major_pysindy_version_rejected_by_weak_diagnostic` | The same runtime version guard has not been landed on `inspect_pysindy_weak_pde_library`. | runtime-conditional `pytest.xfail(...)` | `v0.31.1` (PySINDy 2.x port) | KEEP as xfail until v0.31.1 |
| `tests/test_v0_31b3_pysindy_compatibility_policy.py::test_discovery_task_backend_version_records_exact_pysindy_and_sklearn` | Asks `pdelie.tasks.discovery._resolve_backend_version` to include `scipy` for uniformity with the weak diagnostic's provenance. `scipy` is currently a nested-value extension, not required for v0.31 release close. | runtime-conditional `pytest.xfail(...)` on the `"scipy" not in backend_version` branch | provenance follow-up (v0.31.1 or earlier) | KEEP as xfail until the follow-up lands |

## Compatibility test / release-close validation

- pytest full suite baseline at v0.31.0 close: **1252 passed, 3 skipped, 3 xfailed** (v0.31c1 close baseline) → **1253 passed, 3 skipped, 3 xfailed** after adding the Python 3.12+ UX test.
- `ruff check .` clean.
- `mypy src/pdelie/tasks/` clean.
- `sphinx -b html -W --keep-going docs docs/_build/html` clean.
- `python -m build --sdist --wheel` produces `pdelie-0.31.0.tar.gz` and `pdelie-0.31.0-py3-none-any.whl`.
- `git diff --check` clean.

Clean-install smoke matrix:

- Core-only (Python 3.11, no `[downstream]`): install passes; task runner raises `ImportError` naming `pdelie[downstream]`.
- Downstream (Python 3.11, ambient `setuptools>=82`): pip auto-downgrades setuptools to 81; `run_pysindy_pde_task` passes (22-key summary, strict JSON); `inspect_pysindy_weak_pde_library` passes (27-key summary, `diagnostic_only=True`, strict JSON); example runner + CLI pass.
- Downstream (Python 3.11, fresh venv): setuptools stays at the bundled 65.5.0; smoke passes.
- Python 3.12+ unsupported downstream behavior: targeted `ImportError` (or `ScopeValidationError` on the weak path) message names Python 3.12, the v0.31.1 deferral, and states that reinstalling the same extra will not fix the environment. Verified by `tests/test_v0_31c1_downstream_packaging_policy.py::test_v0_31_python_312_downstream_missing_extra_message_is_actionable` under monkeypatched `sys.version_info`.

## Boundaries / non-goals for v0.31.0

- **No new discovery backend.** PySINDy 1.x only.
- **No new summary type.** `discovery_task_result` (22 keys) and `pdelie_weak_pde_library_diagnostic` (27 keys) are the entire v0.31 report surface.
- **No WSINDy benchmark claim.** The `WeakPDELibrary` wrapper is diagnostic-only.
- **No noise-robustness claim.**
- **No nonperiodic PySINDy discovery.** Both task paths raise on nonperiodic-x inputs.
- **No PySINDy 2.x code.** Deferred to `v0.31.1`.
- **No symmetry-method registry, no `SymmetryCandidate` runtime.** Deferred to `v0.30.1`.
- **No PDEBench / The Well support claim.**
- **No multi-channel / 2D widening.** Deferred to `v0.34+`.
- **No new PDE.**
- **No root pdelie export added.**
- **No package version bump beyond `0.31.0`.**
- **No PyPI or TestPyPI publication.**

## Deferred scope confirmed

- `v0.31.1`: PySINDy 2.x migration (four independent API breaks + numpy>=2 floor + Python 3.12+ downstream support + runtime version guard on unsupported pysindy versions).
- `v0.30.1`: submodule-only `SymmetryMethod` registry MVP + `SymmetryCandidate` wrapper contract freeze.
- `v0.31.5`: nonperiodic orbit/action scope decision.
- `v0.32`: external dataset readiness cookbooks (no benchmark claim).
- `v0.33`: first external symmetry candidate-generator method.
- `v0.34`: multi-channel / 2D contract widening scope decision.
- `v0.35`: trained-model extraction layer.
- `v1.0`: stable public engine + PyPI publish + optional root-entry decision.

## Validation checklist

- [x] version bump `0.30.0 → 0.31.0` in `pyproject.toml` and `docs/conf.py`.
- [x] release readiness document exists (this file).
- [x] `CHANGELOG.md` v0.31.0 entry with the five subsections (Added / Compatibility / Diagnostics / Examples / Boundaries).
- [x] `docs/specs/support_matrix.v0_31.json` written as strict JSON with the v0.31 additions.
- [x] `docs/planning/V0_31_DISCOVERY_TASK_BRIDGE_SCOPE.md` status → COMPLETE.
- [x] `docs/planning/PLAN.md` v0.31.0 release-close record.
- [x] `docs/planning/ROADMAP.md` v0.31 moved to completed releases; v0.31c1 marked completed; next active items called out explicitly.
- [x] `docs/specs/API_STABILITY.md` v0.31 final stable-surface note.
- [x] `configs/release_gate_manifest.json` — `"0.31"` row extended in place; `current_release_gate_job_name` renamed to `v0_31-release-gate`.
- [x] `.github/workflows/ci.yml` release-gate job renamed `v0_30-release-gate → v0_31-release-gate`.
- [x] `tests/test_current_release_gate.py` updated to the new job name.
- [x] Full validation gates pass (pytest / ruff / mypy / sphinx / build / git diff-check).
- [x] Clean-install smoke matrix (core-only, downstream, ambient setuptools 82/83, Python 3.12+ UX message).
- [ ] Git tag `v0.31.0` — deferred to explicit authorization after review.
