# PySINDy 2.x Migration Audit (v0.31.1a — research spike)

**Status:** RESEARCH. Enumerates the exact API deltas between PySINDy `1.7.5` (v0.31 legacy line) and PySINDy `2.1.0` (v0.32 modern target), and maps each delta to the pdelie call site that needs a change. Implementation deferred to the v0.31.1 / v0.32 migration PR.

**Companion documents:**

- `docs/design/RUNTIME_COMPATIBILITY_POLICY.md` — the SPEC 0 policy that frames this audit's recommendation.
- `configs/runtime_compatibility_matrix.json` — machine-readable summary.
- `src/pdelie/discovery/_pysindy2_prototype.py` — private, experimental compatibility sketch showing the intended shim shape. **Not wired into any production code path.**

## Environment matrix outcome

Full data lives in `configs/runtime_compatibility_matrix.json`. Summary:

| Lane | Python | PySINDy | Install | Task fit | Weak diagnostic | CLI |
|---|---|---|---|---|---|---|
| A core | 3.11 | — | pass | n/a | n/a | n/a |
| B core | 3.12 | — | pass | n/a | n/a | n/a |
| C core | 3.13 | — | pass (numpy 1.26.4 builds from source) | n/a | n/a | n/a |
| D core | 3.14 | — | pass (numpy 1.26.4 builds from source) | n/a | n/a | n/a |
| E downstream | 3.11 | 1.7.5 | pass | pass | pass | pass |
| F downstream | 3.12 | 2.1.0 | **fail (numpy floor)** | fail (TypeError) | fail (TypeError) | fail |
| G downstream | 3.13 | 2.1.0 | **fail (numpy floor)** | fail (TypeError) | fail (TypeError) | fail |
| H downstream | 3.14 | 2.1.0 | **fail (numpy floor)** | fail (TypeError) | fail (TypeError) | fail |

Lanes F/G/H fail at the natural-resolver step because pdelie declares `numpy>=1.24,<2` core-dep and pysindy 2.1.0 requires `numpy>=2.0`. Under a `--no-deps` probe (informational only — NOT the supported install path), pdelie's core surface imports cleanly against numpy 2.5.1; the `numpy<2` cap is currently a resolver floor rather than a runtime floor.

## PySINDy 1.7.5 → 2.1.0 API delta

Six independent API breaks between the versions pdelie's v0.31 task bridge and diagnostic wrapper depend on.

### Delta 1 — `SINDy.__init__`

**1.7.5**: `SINDy(optimizer=None, feature_library=None, differentiation_method=None, feature_names=None, t_default=1, discrete_time=False)`.

**2.1.0**: `SINDy(optimizer=None, feature_library=None, differentiation_method=None)` — `feature_names`, `t_default`, `discrete_time` REMOVED. Passing any of them raises `TypeError`.

**pdelie sites**: The default-config path in `src/pdelie/discovery/pysindy_adapter.py::_build_pysindy_model` and any downstream caller who passes a v0.31-shaped `pysindy_model` to `run_pysindy_pde_task` will trip the ctor.

**Migration cost**: mechanical — drop the three kwargs; move `feature_names` to `SINDy.fit(...)`.

### Delta 2 — `SINDy.fit`

**1.7.5**: `SINDy.fit(x, t=None, x_dot=None, u=None, multiple_trajectories=False, unbias=True, quiet=False, ensemble=False, library_ensemble=False, replace=True, ...)`.

**2.1.0**: `SINDy.fit(x, t, x_dot=None, u=None, feature_names=None)` — `t` is positional-required; `multiple_trajectories`, `unbias`, `quiet`, `ensemble`, `library_ensemble`, `replace`, `n_candidates_to_drop`, `n_subset`, `n_models`, `ensemble_aggregator` all REMOVED; `feature_names` moved here from the ctor.

**pdelie sites**: `pdelie.discovery.pysindy_adapter.fit_pysindy_discovery` and `pdelie.discovery.pysindy_adapter._fit_caller_supplied_model` both pass `multiple_trajectories=True, unbias=True, quiet=True` — all three raise `TypeError` under 2.1.0. Observed lane F failure: `TypeError: SINDy.fit() got an unexpected keyword argument 'multiple_trajectories'`.

**Migration cost**: mechanical — drop the removed kwargs; route ensembling through `EnsemblingOptimizer` if that behavior is still desired (currently unused by pdelie's task path).

### Delta 3 — `SINDy.differentiate` removed

**1.7.5**: `SINDy.differentiate(x, t=None, multiple_trajectories=False)` — computes time-derivatives via the configured differentiation method.

**2.1.0**: method REMOVED. `hasattr(pysindy.SINDy, 'differentiate') == False`.

**pdelie sites**: `src/pdelie/tasks/discovery.py::_compute_residual_over_trajectories` at line ~638 calls `pysindy_model.differentiate(...)` inside a try/except that degrades to `None` on failure — under 2.1.0 the try/except would silently return None and the discovery_task_result's `train_residual` would be `None`, silently degrading the output. That's a silent-degradation risk the migration PR must address.

**Migration cost**: small — route through `model.differentiation_method_(trajectory, t=time_values)` on 2.x, or reconstruct via `numpy.gradient` if the differentiation-method attribute proves unreliable.

### Delta 4 — `SINDy.model` attribute removed

**1.7.5**: fitted `SINDy` instance exposes a `.model` attribute holding the internal sklearn Pipeline.

**2.1.0**: `hasattr(fitted_model, 'model') == False`. No such attribute on class or instance.

**pdelie sites**: none today. But any downstream introspection helper users have built against `sindy.model.steps` would break.

**Migration cost**: none inside pdelie; document in the CHANGELOG for downstream consumers.

### Delta 5 — `STLSQ.__init__` narrowed

**1.7.5**: `STLSQ(threshold=0.1, alpha=0.05, max_iter=20, ridge_kw=None, normalize_columns=False, fit_intercept=False, copy_X=True, initial_guess=None, verbose=False, unbias=True)`.

**2.1.0**: `STLSQ(threshold=0.1, alpha=0.05, max_iter=20, ...)` — `fit_intercept` REMOVED. Passing it raises `TypeError`.

**pdelie sites**: `pdelie.discovery._pysindy_defaults.get_default_pysindy_discovery_config` passes `fit_intercept=False`. Observed lane F failure: `TypeError: STLSQ.__init__() got an unexpected keyword argument 'fit_intercept'`.

**Migration cost**: mechanical — drop the kwarg from the default-config builder.

### Delta 6 — `PDELibrary.__init__` and `WeakPDELibrary.__init__` reshaped

**1.7.5**: both accept `library_functions=[...]`, `function_names=[...]`, `interaction_only=True/False`.

**2.1.0**: both REQUIRE `function_library=<BaseFeatureLibrary>` and REMOVE `library_functions`, `function_names`, `interaction_only`. Migration pattern:

```python
# 1.7.5
lib = pysindy.PDELibrary(
    library_functions=[lambda x: x, lambda x: x*x],
    function_names=[lambda s: s, lambda s: s + "^2"],
    interaction_only=True,
    derivative_order=2,
    spatial_grid=x_grid,
)

# 2.1.0
lib = pysindy.PDELibrary(
    function_library=pysindy.PolynomialLibrary(degree=2, interaction_only=True),
    derivative_order=2,
    spatial_grid=x_grid,
)
```

**pdelie sites**: `src/pdelie/tasks/weak_pde_library.py::_build_weak_library` at line ~444 constructs `pysindy.WeakPDELibrary(library_functions=..., function_names=..., interaction_only=...)`. Observed lane F failure: `TypeError: WeakPDELibrary.__init__() got an unexpected keyword argument 'library_functions'`, wrapped by pdelie's existing `ScopeValidationError('installed PySINDy WeakPDELibrary API is incompatible with the v0.31b2 diagnostic wrapper')` — the guard already fires cleanly. The default `PDELibrary` construction inside `pysindy_adapter._build_pysindy_model` has the same shape and would need the same rewrite.

**Migration cost**: moderate — the library shape is the load-bearing v0.31 design surface. Migration PR must verify the term-mapping golden fixture (`tests/test_v0_31b0_pysindy_term_mapping_golden.py`) still holds under the `function_library=PolynomialLibrary(...)` form. The feature-name convention (`x0`, `x0^2`, `x0_1`, `x0x0_1`, ...) is documented as byte-identical across 1.x and 2.x — that's the extraction anchor.

### Delta 7 — `WeakPDELibrary` random-state (informational)

**1.7.5**: no `random_state` kwarg on the constructor; K subdomain-center placement uses `np.random.*` global RNG. pdelie's example wraps that with a private `_legacy_numpy_rng_seed_scope` context manager (v0.31c1).

**2.1.0**: still no `random_state` kwarg. Same global-RNG behavior. **The determinism workaround does not retire under the pysindy 2.x port** — the `_legacy_numpy_rng_seed_scope` context manager remains necessary until upstream adds a seedable Generator.

## Transitive numpy floor conflict

pdelie 0.31.0 declares `numpy>=1.24,<2` as a core dep. pysindy 2.1.0 declares `numpy>=2.0` as a core dep. Natural pip resolve: unsatisfiable.

**Options for v0.32**:

- **Widen the numpy cap to `<3`.** The `--no-deps` probe in lane F showed pdelie's core surface (data / derivatives / residuals / reporting / verification / examples) imports and runs against numpy 2.5.1 without changes — the `<2` cap is currently a resolver floor, not a runtime one. Widening is the smallest defensible change.
- **Set an explicit numpy 2.x floor** if the migration PR discovers a numpy 2.x-only API PDELie wants to depend on. Not currently expected.

## Prototype scope

The private `src/pdelie/discovery/_pysindy2_prototype.py` provides the SHAPE of a pysindy 2.x compatibility helper — module-level constants naming each API break, plus a small `_detect_pysindy_api_generation()` returning `Literal["1x", "2x"]` and a `raise_if_unsupported_generation()` guard that emits the same actionable v0.31.1 deferral message as the runtime already emits for Python 3.12+. **Nothing in the prototype is wired into any production code path.** It exists so the v0.31.1 implementation PR has a concrete anchor to point at.

## Migration PR recommendation

The v0.31.1 implementation PR should:

1. Widen `numpy>=1.24,<3` on the core dep.
2. Retire the `pysindy>=1.7.5,<2` pin — replace with `pysindy>=2.1,<3; python_version < '3.15'` on the `[downstream]` extra.
3. Retire the `scikit-learn>=1.2.2,<1.3` pin — replace with a current supported range (`>=1.4,<2` or similar based on pysindy 2.1.0's transitive requirements).
4. Retire the `setuptools<82; python_version < '3.12'` temporary cap — pysindy 2.x uses `importlib.metadata`, no `pkg_resources` dependency.
5. Migrate the six API-break sites listed above.
6. Convert the `_pysindy2_prototype.py` shim shape into a real `_pysindy_compat.py` if any residual 1.x/2.x branching is needed (audit result suggests none is required — 2.x-only migration is cleaner).
7. Update `configs/pysindy_compatibility_matrix.json` to declare 2.1.x as the supported line.
8. Delete `_pysindy2_prototype.py`, retire the three xfailed tests in `tests/test_v0_31b3_pysindy_compatibility_policy.py`, and update the term-mapping golden fixture if pysindy 2.x's feature-name emission ordering has shifted.
9. Rename CI release-gate job `v0_31-release-gate → v0_32-release-gate` at v0.32 release close.

## Not part of the migration PR

- No new PDE. No new report schema. No new root export.
- No SymmetryMethod / SymmetryCandidate runtime (that's v0.30.1).
- No PDEBench / The Well support claim.
- No multi-channel / 2D contract widening.
- No WSINDy benchmark, no noise-robustness claim, no nonperiodic PySINDy discovery.

## References

- Environment matrix log: `/private/tmp/claude-501/-Users-agabel-projects-pdelie/73129605-dc34-41b8-9919-110e458eea3f/scratchpad/v031_1a/` (retained for reproducibility).
- Companion audit: `docs/design/PYSINDY_COMPATIBILITY_POLICY.md` (v0.31.x legacy line).
- Feature-name convention (byte-identical across pysindy 1.x/2.x): `docs/planning/PYSINDY_API_PREFLIGHT_AUDIT.md` and `tests/test_v0_31b0_pysindy_term_mapping_golden.py`.
