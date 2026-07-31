# PySINDy 2.x Migration Audit (v0.32a — implemented)

**Status:** IMPLEMENTED — v0.32a landed the migration. This document is retained as the historical record of the six API deltas and the per-call-site mapping used during migration.

**Addendum, v0.36a-β:** the migration also changed *numbers*, not only APIs. Read the section **"Numerical finding (v0.36a-β): legacy STLSQ conditioning"** below before citing any coefficient magnitude produced under PySINDy 1.7.5.

**Companion documents:**

- `docs/design/RUNTIME_COMPATIBILITY_POLICY.md` — the SPEC 0 policy frame.
- `configs/runtime_compatibility_matrix.json` — machine-readable summary.
- **The private research prototype** (`src/pdelie/discovery/_pysindy2_prototype.py`) **was deleted by v0.32a**. The v0.31.1a research phase chose outcome A (modern-only future line); no runtime compatibility shim was needed. Every migration site listed below was rewritten directly against the pysindy 2.1.x API.

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

## Numerical finding (v0.36a-β): legacy STLSQ conditioning

The six deltas below are API breaks. The v0.36a-β full migration audit measured the
**numerical** consequence of the same version change, and it is not a formatting
difference.

Measured over five 1-D PDEs, 20 pipeline stages each, legacy `v0.22.0` on
CPython 3.11 / NumPy 1.26.4 / PySINDy 1.7.5 against modern `v0.35.0` on CPython
3.12 / NumPy 2.5.1 / PySINDy 2.1.0:

| PDE | Legacy ‖c‖∞ | Modern ‖c‖∞ | Support agreement |
|---|---:|---:|---|
| `heat_1d` | — | — | identical (both all-zero after thresholding) |
| `burgers_1d` | — | — | identical |
| `reaction_diffusion_1d` | — | — | identical |
| `advection_diffusion_1d` | `3.6695e+10` | `8.9725e+00` | differs on 0.067% of entries |
| `kdv_1d` | `1.2885e+09` | `1.9405e+02` | differs on 0.177% of entries |

**What is preserved.** Library construction is identical on both sides — same
coefficient array shape `(64, 2145)`, same library size `2145`, same nonzero
cardinality. The *regressor-selection* result is a qualitative agreement: the
same number of terms survive thresholding, and on three of five PDEs the
selected support is bit-identical.

**What is not.** On `advection_diffusion_1d` and `kdv_1d` the legacy STLSQ solve
produced coefficient magnitudes of order `1e9`–`1e10` to fit a 2145-column
library. Coefficients that large against an O(1) target are the signature of an
ill-conditioned solve, not of a physical model — the fitted magnitudes are
**fit-conditioning artifacts**. The modern stack produces well-scaled
coefficients (`8.97e+00`, `1.94e+02`) on the same input data and the same
library.

**Downstream implication.** Any *coefficient value* reported for
`advection_diffusion_1d` or `kdv_1d` under the PySINDy 1.7.5 line rests on a
numerically fragile solve and should not be re-cited as a magnitude.
*Regressor-selection* results for those PDEs are not implicated: the structure
is preserved on the modern stack. The difference is fit conditioning, not a
modeling change — nothing about the library, the target, or the thresholding
policy differs between the two sides.

**Direct evidence, from the Linux replay.** Comparing each side *against itself*
across macOS and Linux — identical data, library and seed, only BLAS differing:

| PDE | Legacy relative difference | Modern relative difference |
|---|---:|---:|
| `advection_diffusion_1d` | `4.74e-03` | `4.21e-11` |
| `kdv_1d` | **`2.17e-01`** | `9.86e-12` |

A solve whose answer moves 22% when the BLAS changes is ill-conditioned. The
legacy coefficients are not merely large, they are **not reproducible**; the
modern coefficients agree across platforms to ~`1e-11`. A legacy coefficient
magnitude for these two PDEs would not survive being recomputed on different
hardware — which is a stronger reason not to re-cite it than its magnitude alone.

**Attribution, stated honestly.** The two environments differ in PySINDy *and*
NumPy version, so a raw comparison cannot separate them. What separates them is
v0.36a-α: it audited sixteen non-PySINDy stages across the same environment
boundary — derivatives, design and Gram matrices, coefficients, residuals — and
closed with every numeric stage agreeing to `~1e-8` or better. An environment
that moves the shared numerical substrate by `1e-8` does not move a fitted
coefficient by ten orders of magnitude. The divergence is therefore attributed
to the PySINDy version delta, per the attribution rule in
`docs/planning/V0_36A_ALPHA_TO_BETA_RUNBOOK.md`.

This is a finding about the legacy line, not a defect to repair: `v0.22.0` is a
frozen tag. Both affected stages are labelled `intentional_contract_change` in
`configs/full_migration/comparison_policy.json`, never `unexplained_regression`.

Full measurement: `docs/planning/V0_36A_BETA_MIGRATION_FREEZE.md` §3.

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
