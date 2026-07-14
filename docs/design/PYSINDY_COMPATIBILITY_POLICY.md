# PySINDy Compatibility Policy (v0.31b3)

**Status:** IN_PROGRESS (v0.31b3)

**Decision label:** `downstream_pysindy_compatibility_policy_and_wheel_hardening`

**Outcome:** `C_temporary_1x_policy` — the `pdelie[downstream]` extra pins
`pysindy>=1.7.5,<2` as a **declared temporary policy**. PySINDy 2.x is
**not supported** in `v0.31`. A dedicated migration release
(`v0.31.1` / `v0.32`) will widen the pin once the four independent
2.x-API deltas are absorbed under a version-dispatch shim and once the
transitive `numpy>=2` floor bump is coordinated.

This document is the single source of truth for the supported PySINDy
range, the exact public pdelie surfaces covered under that range, the
known 1.x-vs-2.x API differences, and the explicit non-claims the
downstream compatibility surface makes. The machine-readable form of
this policy lives at
`configs/pysindy_compatibility_matrix.json` and is emitted verbatim
under `summary_type = "pdelie_pysindy_compatibility_matrix"`.

## Supported PySINDy versions

- `1.7.5` (primary tested — pinned by `pdelie[downstream]` / `pdelie[test]`).

The pyproject constraint is:

```text
pysindy>=1.7.5,<2
```

### Primary tested version

- **`1.7.5`** — verified against `pdelie 0.30.0` on Python 3.11.7 with
  `numpy 1.26.4`, `scipy 1.17.1`, and `scikit-learn 1.2.2`. All 61
  targeted `pdelie.tasks.discovery` / `pdelie.tasks.weak_pde_library`
  tests pass (b0/b1/b2 test files) with no test-visible failures.

### Secondary tested version

None. The declared range admits exactly one PySINDy release
(`1.7.5`). Later `1.7.x` point releases (if any) are covered by the
`<2` upper bound but are not separately exercised.

### Unsupported versions

- `<1.7.5` — not exercised; the `pdelie.discovery.pysindy_adapter`
  code paths depend on `SINDy.coefficients()` returning the
  `(n_state, n_library_terms)` matrix shape and on
  `library.get_feature_names()` being available on the fitted
  library. Earlier `1.7.x` sub-minors are excluded to keep the
  supported version set to exactly one line-item.

- `>=2.0.0` — HARD-broken against `pdelie 0.30.0` on three independent
  axes:

  1. **`pysindy.SINDy(feature_names=..., discrete_time=..., t_default=...)`**
     constructor kwargs removed. `pdelie.discovery.pysindy_adapter._build_pysindy_model`
     raises `TypeError` on any 2.x install.
  2. **`pysindy.WeakPDELibrary(library_functions=..., function_names=..., interaction_only=...)`**
     kwargs removed. `pdelie.tasks.weak_pde_library._construct_weak_pde_library`
     raises `ScopeValidationError` on any 2.x install (the existing
     runtime guard catches the `TypeError` and rethrows).
  3. **`pysindy.SINDy.differentiate(...)`** removed.
     `pdelie.tasks.discovery._compute_residuals_from_predictions`
     raises `AttributeError` on the residual path.

  Additionally, `pysindy 2.x` requires `numpy>=2.0`, while
  `pdelie 0.30.0` pins `numpy<2`. `pip` resolves `ResolutionImpossible`
  on any joint install. Admitting `pysindy>=2` is therefore an atomic
  release-note question coupled with a `numpy` floor bump; it is
  deferred to the `v0.31.1` / `v0.32` migration release.

## Public pdelie surfaces covered by this policy

The following runtime public surfaces are the exact call-sites that
this compatibility policy guards. They are the surfaces a
`pdelie[downstream]` user actually exercises through PySINDy under the
supported range:

- `pdelie.tasks.discovery.run_pysindy_pde_task`
- `pdelie.tasks.discovery.summarize_discovery_task_result`
- `pdelie.tasks.discovery.PySINDyDiscoveryUnsupportedBoundaryError`
- `pdelie.tasks.weak_pde_library.inspect_pysindy_weak_pde_library`
- `pdelie.tasks.weak_pde_library.summarize_pysindy_weak_pde_library_diagnostic`
- `pdelie.tasks.weak_pde_library.WeakPDELibraryDiagnostic`

Re-exports on `pdelie.tasks` (v0.31b2) are covered by the same policy.
No root `pdelie` export is added, and no submodule outside
`pdelie.tasks.*` re-exports any of the six names above.

Internal helpers that the future `v0.31.1` / `v0.32` shim will live
under are explicitly private:

- `pdelie.discovery.pysindy_adapter` (existing, private).
- `pdelie.discovery._pysindy_defaults` (existing, private).
- `pdelie.discovery._pysindy_compat` (deferred; will be introduced
  when the pin is widened to admit PySINDy 2.x; no such module exists
  in `v0.31b3`).

The private-helper convention is enforced by the
`configs/release_gate_manifest.json` `0.31` row: `_pysindy_compat` and
any accompanying constants such as `SUPPORTED_PYSINDY_VERSIONS` are
recorded as `forbidden_root_attributes` so they cannot leak to the
`pdelie` root once introduced.

## Explicit non-claims

The v0.31b3 downstream compatibility surface makes **none** of the
following claims. Each item below is a non-claim of the covered
surfaces above, not a hidden guarantee.

- **No WSINDy benchmark.** The wrapper produces a diagnostic-only
  strict-JSON summary (`summary_type = "pdelie_weak_pde_library_diagnostic"`,
  `diagnostic_only = True`). No sparse-recovery correctness claim, no
  design-matrix conditioning claim, and no recovery-rate benchmark
  are made.
- **No noise robustness claim.** No clean-vs-noisy gate is added.
  Callers are responsible for controlling input noise; the wrapper
  does not add or remove noise from any `FieldBatch`.
- **No nonperiodic discovery.** The task-runner and the WeakPDELibrary
  wrapper reject nonperiodic-x `FieldBatch` inputs with
  `PySINDyDiscoveryUnsupportedBoundaryError` before any PySINDy call.
  FD-nonperiodic PySINDy discovery is a `v0.32.5` target.
- **No PDEBench / The Well support claim.** No external-dataset
  benchmark is claimed. The v0.28 `pdelie.data.from_xarray_dataset`
  readiness path is orthogonal to this policy.
- **No `pdelie.residuals.weak_1d` retirement.** `weak_1d` is retained
  through `v0.32` close. This policy does not claim numerical
  equivalence between the WeakPDELibrary wrapper and `weak_1d`.
- **No PySINDy 2.x support.** `>=2.0.0` is explicitly unsupported.

## Known API differences (1.x vs 2.x)

The following diffs are recorded here so that the future `v0.31.1` /
`v0.32` shim has a single reference point. **They are not shimmed in
v0.31b3** — the pin excludes 2.x entirely. Recording them here is a
planning artifact.

Each row cites the pdelie call-site that would break under 2.x and
the compact required change.

| PySINDy API surface | 1.x behavior | 2.x behavior | pdelie call-site | Required change (deferred) |
| --- | --- | --- | --- | --- |
| `pysindy.SINDy.__init__` kwargs | accepts `optimizer, feature_library, differentiation_method, feature_names, t_default, discrete_time` | accepts only `optimizer, feature_library, differentiation_method`; `feature_names / t_default / discrete_time` removed | `pdelie.discovery.pysindy_adapter._build_pysindy_model`; `pdelie.discovery._pysindy_defaults` | drop `feature_names=` / `discrete_time=` from constructor; thread `feature_names` into `fit(...)`; version-dispatch in the future `_pysindy_compat._build_sindy` helper |
| `pysindy.SINDy.fit` signature | accepts `multiple_trajectories, unbias, quiet, ensemble, library_ensemble, replace, n_candidates_to_drop, n_subset, n_models, ensemble_aggregator`; `t` optional | drops all of the above kwargs; `t` becomes positional-required; `feature_names` moves here | `pdelie.discovery.pysindy_adapter`; `pdelie.discovery._pysindy_defaults` | rewrite default `pysindy_fit` dict on the 2.x path; route ensembling through `EnsemblingOptimizer`; pass trajectory lists directly |
| `pysindy.SINDy.differentiate` | present; `differentiate(x, t=None, multiple_trajectories=False)` | REMOVED (`AttributeError` on access) | `pdelie.tasks.discovery._compute_residuals_from_predictions` | replace with a call through `model.differentiation_method_(traj, t=t)` or a pdelie-owned FD helper |
| `pysindy.SINDy.predict` signature | `predict(x, u=None, multiple_trajectories=False)` | `predict(x, u=None)`; `multiple_trajectories` gone | `pdelie.tasks.discovery._compute_residuals_from_predictions` (single-trajectory only today) | doc-only for the current single-traj call site; multi-traj callers must switch idiom |
| `SINDy.model` internal Pipeline | present on fitted `SINDy` | absent | none in pdelie today | doc-only; gate any future introspection on version |
| `pysindy.PDELibrary.__init__` kwargs | accepts `library_functions, function_names, interaction_only, library_ensemble, ensemble_indices, ...` | drops those; requires `function_library=<BaseFeatureLibrary>` | not built directly in pdelie today (docstring reference only); downstream examples that build a `PDELibrary` directly will break | rewrite docs/examples; optionally add a `pdelie.discovery.build_pysindy_pde_library` helper |
| `pysindy.WeakPDELibrary.__init__` kwargs | accepts `library_functions, function_names, interaction_only, library_ensemble, ensemble_indices, ...` | drops those; requires `function_library=<BaseFeatureLibrary>` | `pdelie.tasks.weak_pde_library._construct_weak_pde_library` | refactor to build a `CustomLibrary(library_functions, function_names)` (or `PolynomialLibrary` of matching degree) and pass it as `function_library=` on 2.x; version-dispatch in the future `_pysindy_compat._build_weak_pde_library` helper |
| `SINDy.coefficients()` / `library.get_feature_names()` | `(n_state, n_library_terms)` ndarray; `list[str]` | **IDENTICAL** shape and semantics | `pdelie.discovery.pysindy_adapter` extraction path | **none** — this is the anchor of stability that makes the future shim feasible |
| numpy floor (transitive) | `pysindy 1.7.5` works with `numpy 1.24-1.26`; `pdelie` pins `numpy<2,>=1.24` | `pysindy 2.x` requires `numpy>=2.0`; `pip` rejects joint install | `pyproject.toml` core `requires` block; `pdelie[downstream]` extra | any release that admits `pysindy>=2` must simultaneously widen `numpy` to `>=2` (or dual-track) |
| `pysindy` runtime import (`pkg_resources`) | `pysindy 1.7.5` imports `pkg_resources` at package init | `pysindy 2.1.0` uses `importlib.metadata`; no `pkg_resources` dependency | none at code level; `pdelie[downstream]` does not pull `setuptools` | document the `setuptools<81` install footgun for `pysindy 1.x` (fresh venvs with `pip 25.x` need `pip install 'setuptools<81'`) |

## Install footgun: `setuptools<81` with PySINDy 1.x

`pysindy 1.7.5` imports `pkg_resources` at package init, which was
removed from `setuptools>=81`. Downstream users installing
`pdelie[downstream]` into a fresh venv with `pip 25.x` may hit
`ModuleNotFoundError: No module named 'pkg_resources'` when importing
`pysindy`.

### v0.31c1 adversarial install matrix — outcome B (setuptools cap added)

The v0.31c self-sufficiency claim held only because `python -m venv` on
Python 3.11 pre-bundles `setuptools 65.5.0` (which ships
`pkg_resources`). The v0.31c1 sub-release ran an adversarial follow-up
matrix on fresh Python 3.11 venvs with the ambient `setuptools` version
force-pinned to `81.0.0`, `82.0.0`, and `83.0.0` BEFORE installing
`pdelie[downstream]` — i.e. simulating a realistic environment where the
user (or the system, or a routine `pip install --upgrade setuptools`)
has already upgraded past the pkg_resources boundary.

| Ambient setuptools | pdelie[downstream] install | `import pysindy` | Smoke |
|---|---|---|---|
| `81.0.0` | pass | pass (removal warning) | pass |
| `82.0.0` | pass | **fail** — `ModuleNotFoundError: No module named 'pkg_resources'` | not run |
| `83.0.0` | pass | **fail** — same | not run |

Outcome **B_setuptools_82_boundary**. The install itself never fails
(pip check reports clean); the failure surfaces only at
`import pysindy` because `pysindy/__init__.py` does `from pkg_resources
import DistributionNotFound`, and setuptools 82 removed the
`pkg_resources` module entirely.

v0.31c1 amends the `[downstream]` extra with the narrow temporary
constraint:

```text
setuptools<82; python_version < '3.12'
```

Post-fix verification (fresh venvs, rebuilt wheel): with ambient
setuptools 82.0.0 or 83.0.0 pre-installed, `pip install
"<wheel>[downstream]"` auto-downgrades setuptools to `81.0.0` and both
smoke paths (`run_pysindy_pde_task`, `inspect_pysindy_weak_pde_library`)
plus the example CLI (`python -m
pdelie.examples.downstream_discovery_task_bridge`) pass. Fresh venv
baseline: setuptools stays at the bundled `65.5.0`, untouched.

The cap is scoped to `python_version < '3.12'` because the pysindy /
sklearn deps themselves are already scoped that way — Python 3.12+
does not receive `pdelie[downstream]` in v0.31. The constraint is
temporary: it retires when the pysindy pin widens to `>=2` in
`v0.31.1` / `v0.32`, since pysindy 2.x uses `importlib.metadata`
instead of `pkg_resources`.

### v0.31c clean-install audit — outcome A (self-sufficient on Python 3.11)

The v0.31c sub-release ran the mandatory clean-install audit with the
advertised command `pip install "<wheel>[downstream]"` into a fresh
Python 3.11 venv, **without** any manual `setuptools<81` co-install.
The install succeeded end-to-end: CPython 3.11's `python -m venv`
still bundles `setuptools 65.5.0` (which ships `pkg_resources`), so
the standard install path is self-sufficient. Both v0.31 downstream
task paths (`run_pysindy_pde_task` and `inspect_pysindy_weak_pde_library`)
executed, and both emitted payloads passed
`json.dumps(payload, allow_nan=False)`.

Therefore **no `setuptools<81` constraint is added to the
`pdelie[downstream]` extra** in v0.31c. The declared `python_version <
'3.12'` marker on the downstream deps already gates the footgun
population: on Python 3.12+, `python -m venv` no longer bundles
`setuptools`, and the pysindy `pkg_resources` import would fail without
an explicit co-install. That population is not supported by
`pdelie[downstream]` today.

### Workaround for the 1.x line on Python 3.12+ (opt-in only)

```bash
python -m pip install 'setuptools<81'
python -m pip install 'pdelie[downstream]'
```

Widening the pin to `pysindy>=2` eliminates this footgun; that
migration is scheduled for `v0.31.1` / `v0.32`.

## CI matrix

The CI matrix is machine-readable at
`configs/pysindy_compatibility_matrix.json`. Both currently-blocking
jobs exercise PySINDy `1.7.5` via the `.[test]` extra, which resolves
to the pinned `pysindy>=1.7.5,<2` range:

| Job | PySINDy version | Blocking |
| --- | --- | --- |
| `editable-tests` | `1.7.5` | yes |
| `v0_30-release-gate` | `1.7.5` | yes |

No new CI job is required for `v0.31b3`. A dedicated matrix over
PySINDy versions is unnecessary while the pin admits exactly one
major and one minor line. When `v0.31.1` / `v0.32` widens the pin,
an advisory `pysindy-2x` job on `pysindy==2.1.0` will be added.

## Resource envelope

The numbers below are **diagnostic guidance only** — a single point
measurement from one manufactured Heat 1D fixture on one developer
machine. They are recorded so downstream users have an order-of-
magnitude sense of the WeakPDELibrary diagnostic's cost. They are
**not** a public runtime memory limit, not a performance contract,
and not a supported benchmark. No pdelie API is gated on them.

Representative WeakPDELibrary run (v0.31b3):

| Field           | Value                                           |
|-----------------|-------------------------------------------------|
| field shape     | `(1, 256, 256, 1)` (batch, time, x, var)        |
| grid shape      | `(256, 256, 2)` (X, T, coord)                   |
| K (weak windows)| 60                                              |
| feature count   | 8 (`polynomial_degree=2`, `derivative_order=2`) |
| weak matrix     | `(60, 8)`                                       |
| runtime         | ~0.75 s (`time.perf_counter`, single call)      |
| peak RSS        | ~144 MiB (`resource.getrusage`, macOS, whole process) |
| PySINDy         | 1.7.5                                           |

Method: the measurement wraps a single call to
`pdelie.tasks.weak_pde_library.inspect_pysindy_weak_pde_library` on a
manufactured periodic Heat 1D field batch generated by
`pdelie.data.heat_1d.generate_heat_1d_field_batch`. Peak RSS is the
resident set size of the whole Python process (including NumPy, SciPy,
PySINDy, and pdelie import overhead), reported via
`resource.getrusage(RUSAGE_SELF).ru_maxrss` and converted from bytes
to MiB on macOS. Note: the intended representative grid was
T=X=128, but the wrapper's defensive lower bound `max(8, 4*K)` requires
at least 240 samples per axis for K=60, so the grid was bumped to
T=X=256 (the nearest power-of-two admissible above 240). Runs with
lower K may fit on the T=X=128 grid at proportionally lower runtime
and RSS.
