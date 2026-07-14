# DiscoveryTaskResult — Design Document

**Status:** DESIGN-FROZEN in v0.31a; **RUNTIME IMPLEMENTED in v0.31b1** for `target_convention="pde_library"`; **WeakPDELibrary wrapper for `target_convention="weak_pde_library"` remains DEFERRED to v0.31b2**.

This document defines the composed `TaskResult` artifact returned by the `pdelie.tasks.discovery` submodule when a caller runs a PySINDy-backed PDE discovery task over a canonical scalar 1D PDELie input. It is normative for v0.31 proper.

## Motivation

The existing downstream-discovery surface consists of three narrow, disconnected pieces:

- `pdelie.discovery.to_pysindy_trajectories` — flattens a periodic scalar 1D `FieldBatch` into PySINDy-shape trajectories (`src/pdelie/discovery/pysindy_bridge.py`)
- `pdelie.discovery.fit_pysindy_discovery(config=None)` — runs a *default* PySINDy fit over the bridge output and refuses non-default configs (`src/pdelie/discovery/pysindy_adapter.py:196-204`)
- `pdelie.discovery.summarize_discovery_result` — normalizes a backend-native discovery-result dict into a JSON-compatible summary (`src/pdelie/discovery/contracts.py:305-409`)

A user who wants to run a `PDELibrary`-backed PDE discovery over their canonical data currently has to build the bridge, hand-configure PySINDy, run the fit outside PDELie, and then re-enter the reporting layer through `summarize_discovery_result`. The task bridge composes these three pieces into one call and produces a single stable JSON-compatible artifact that carries backend provenance, recovery metrics, and residuals side-by-side.

### Why a new schema

`summarize_discovery_result` is a stable v0.22 surface. It is intentionally *backend-native*: it wraps any dict shaped like PySINDy's output. It does not carry backend versions, does not carry input-layout provenance, does not carry a `weak_contract` block, and does not enforce strict-JSON (`allow_nan=False`). The task-bridge output needs all four of these, and it needs to compose cleanly with `summarize_discovery_result` as a sibling embedded payload rather than replacing it.

## Proposed schema

`TaskResult` is the return type of the (design-only) `pdelie.tasks.discovery.run_pysindy_pde_task(...)` runtime API. Its stable serialized form is:

```
{
    "summary_schema_version": "0.1",
    "summary_type": "discovery_task_result",
    "task_name": str,
    "backend_name": Literal["pysindy"],
    "backend_version": dict[str, str],
    "target_convention": Literal["pde_library", "weak_pde_library"],
    "derivative_backend": str,
    "input_layout": Literal["scalar_1d_uniform"],
    "library_feature_names": list[str],
    "selected_terms": dict[str, dict[str, float]],
    "coefficients": dict | None,
    "support_precision": float,
    "support_recall": float,
    "support_f1": float,
    "exact_support": bool,
    "coefficient_relative_l2": float,
    "train_residual": dict | None,
    "heldout_residual": dict | None,
    "weak_contract": dict | None,
    "warnings": list[str],
    "pysindy_bridge_variant": Literal["periodic_only_v1"],
    "underlying_discovery_result": dict,
}
```

### Field semantics

- `summary_schema_version` — literal `"0.1"`.
- `summary_type` — literal `"discovery_task_result"`.
- `task_name` — caller-supplied non-empty string identifying the task instance for provenance and logging.
- `backend_name` — `Literal["pysindy"]` in v0.31. Expansion of the Literal set (e.g. to `"pysr"`) is a `v0.32+` concern.
- `backend_version` — dict with required keys `pysindy`, `sklearn`, and `pdelie`. Values are version strings (`importlib.metadata.version(...)`).
- `target_convention` — `Literal["pde_library", "weak_pde_library"]`. Selects between the strong PySINDy `PDELibrary` bridge and the `WeakPDELibrary` diagnostic wrapper.
- `derivative_backend` — string promoted from `fit_config["pysindy_model"]["differentiation_method"]`. This is the PySINDy-side identifier (e.g. `"FiniteDifference"`, `"SmoothedFiniteDifference"`, or `"SpectralDerivative"`). The v0.30c PDELie-side `spectral_fd` / `finite_difference` dispatch continues to govern PDELie-native derivative computation; this field records which method PySINDy used, not which PDELie backend was invoked.
- `input_layout` — `Literal["scalar_1d_uniform"]`. Reserved enum for `v0.34+` multi-channel/2D expansion. The field is first-class *now* so that `v0.34a-c` do not retrofit the schema; only `"scalar_1d_uniform"` is accepted at runtime.
- `library_feature_names` — list of non-empty strings, unique. Renamed from `library_terms` for continuity with `summarize_discovery_result` (`src/pdelie/discovery/contracts.py:395`, which reports `library_feature_names` from `result_mapping["library_feature_names"]`).
- `selected_terms` — dict keyed by PySINDy target-feature name; values are `dict[str, float]` mapping candidate-term string to fitted coefficient. Verbatim from the `equation_terms` block of the embedded `discovery_result` (`src/pdelie/discovery/contracts.py:396`).
- `coefficients` — optional dict carrying the raw coefficient matrix in a JSON-compatible form (e.g. `{"shape": [num_features, num_terms], "values": list[list[float]], "epsilon": support_epsilon}`). Opt-in shape; consumers must tolerate `None`.
- `support_precision`, `support_recall`, `support_f1` — configured recovery metrics; produced via the existing `pdelie.discovery.evaluate_discovery_recovery` machinery.
- `exact_support` — bool; `True` iff `support_precision == 1.0 and support_recall == 1.0`.
- `coefficient_relative_l2` — float; `||fit - target||_2 / max(||target||_2, epsilon)`.
- `train_residual`, `heldout_residual` — optional strict-numeric dicts of the shape `{"size": int, "l2_norm": float, "rms": float, "max_abs": float}`, matching `_residual_summary_or_none` at `src/pdelie/discovery/contracts.py:198-214`.
- `weak_contract` — optional dict. **Non-null iff `target_convention == "weak_pde_library"`**. Its structure is documented under "WeakPDELibrary wrapper" below.
- `warnings` — list of non-empty strings drawn from a controlled vocabulary (`"heldout_residual_missing"`, `"support_epsilon_defaulted"`, `"weak_contract_diagnostic_only"`, `"differentiation_method_defaulted"`; extended per implementation review).
- `pysindy_bridge_variant` — `Literal["periodic_only_v1"]`. Provenance identifier for the PySINDy discovery bridge variant that produced this `TaskResult`. `"periodic_only_v1"` is the sole accepted value in v0.31 and encodes the periodic-only-x contract enforced at runtime by the `pdelie.tasks.discovery` entry point (see "Runtime boundary-condition guard" below). Future FD-nonperiodic variants (v0.32.5 target) will add distinct string values (e.g. `"nonperiodic_x_finite_difference_v1"`) so consumers reading a saved `TaskResult` can determine which bridge produced it without inferring from `derivative_backend` or the embedded field metadata. This is a first-class field so extension does not require a schema-version bump.
- `underlying_discovery_result` — the payload returned by `summarize_discovery_result(...)`. TaskResult composes with the existing summarizer as a sibling wrapper, not as a parent that swallows the child.

## Runtime boundary-condition guard

The v0.31a periodic-only fence is enforced at **two** places in v0.31b runtime:

1. **The `pdelie.tasks.discovery` task-runner entry point** — before assembling PySINDy trajectories, the runner calls `is_x_periodic(field)` from `pdelie._boundary`. If the field is not periodic, the runner raises `PySINDyDiscoveryUnsupportedBoundaryError` (a new dedicated exception in `pdelie.tasks.discovery`, subclass of `ScopeValidationError`) with a message pointing to `pysindy_bridge_variant == "periodic_only_v1"`.
2. The existing `to_pysindy_trajectories` gate at `src/pdelie/discovery/pysindy_bridge.py:27-28` continues to reject nonperiodic fields.

**Both are required.** Relying on the `to_pysindy_trajectories` gate alone leaves a hole: `fit_pysindy_discovery` accepts raw trajectory arrays and does not consult boundary metadata, so a caller who assembles trajectories directly bypasses the bridge gate. The task-runner-level guard closes that hole for v0.31.

The `pysindy_bridge_variant` field records which enforcement path was in effect at task time. When v0.32.5 lands FD-nonperiodic discovery, it will emit a distinct variant string; consumers reading old `TaskResult` payloads can filter by the periodic-only variant explicitly.

### `weak_contract` trigger predicate

`weak_contract` is:

- `None` when `target_convention == "pde_library"`
- a non-null dict when `target_convention == "weak_pde_library"`

There is no third state. The runtime rejects (`SchemaValidationError`) any TaskResult where `target_convention == "weak_pde_library"` and `weak_contract is None`, or where `target_convention == "pde_library"` and `weak_contract is not None`.

## NaN-safety contract

The composed payload MUST pass:

```python
assert json.loads(json.dumps(payload, allow_nan=False)) == payload
```

before return. The runtime accomplishes this by routing the final payload through the existing helper `_validate_strict_json_compatible(payload, name="discovery_task_result summary")` at `src/pdelie/reporting/summaries.py:196-202`, mirroring the two existing strict-JSON summaries (`summarize_xarray_dataset_readiness` at `summaries.py:1311` and `summarize_weak_form_supportability` at `summaries.py:1954`).

This is required BECAUSE only 2 of 14 current `summarize_*` functions enforce `allow_nan=False`; the other 12 route through the permissive `_summary_payload` funnel (`summaries.py:255-261` calling `_validate_json_compatible` at `:187-193`, which catches only `TypeError` and permits NaN/Inf). TaskResult **must not** inherit that assumption because:

- the embedded `underlying_discovery_result` can, in principle, carry NaN residual entries under the permissive summarizer path
- `train_residual` and `heldout_residual` are numeric-valued and an NaN in either would silently pass the permissive validator
- downstream consumers (dashboards, notebook checks, discovery-workflow reporting) treat TaskResult as a canonical artifact and would break on `NaN` deserialization in strict JSON parsers

The runtime uses `_validate_strict_json_compatible` at the *composition boundary* — after all sub-payloads are assembled, immediately before return. The check catches any NaN or Inf that leaked in through an embedded sub-summary.

## WeakPDELibrary wrapper

When `target_convention == "weak_pde_library"`, the task bridge additionally composes a diagnostic report from PySINDy's `WeakPDELibrary` output. This wrapper carries its own top-level payload with:

```
{
    "summary_schema_version": "0.1",
    "summary_type": "pdelie_weak_pde_library_diagnostic",
    "method_family": "pysindy_weak_pde_library_polynomial_gauss_v1",
    "test_function_family": "pysindy_weak_pde_library_polynomial_bump_v1",
    "quadrature_rule": "pysindy_weak_pde_library_composite_gauss_v1",
    "diagnostic_only": true,
    ...
}
```

and its condensed form is stored inside the TaskResult's `weak_contract` field:

```
{
    "method_family": "pysindy_weak_pde_library_polynomial_gauss_v1",
    "test_function_family": "pysindy_weak_pde_library_polynomial_bump_v1",
    "quadrature_rule": "pysindy_weak_pde_library_composite_gauss_v1",
    "diagnostic_only": true,
}
```

### Why these identifier strings

The three identifier strings above are **distinct** from the pdelie-native `weak_1d` identifiers:

- `method_family`: pdelie-native is `"local_separable_quartic_bump_trapezoid_v1"` (`src/pdelie/residuals/weak_1d.py:20`)
- `test_function` / `test_function_family`: pdelie-native is `"separable_quartic_bump_beta"` (`src/pdelie/residuals/weak_1d.py:22`)
- `quadrature` / `quadrature_rule`: pdelie-native is `"composite_tensor_product_trapezoidal_native_window"` (`src/pdelie/residuals/weak_1d.py:21`)

The wrapper's strings deliberately use the `pysindy_weak_pde_library_*` prefix so downstream consumers (`summarize_weak_residual_report`, `summarize_split_leakage_provenance`, any future `summarize_weak_form_supportability` extension) can disambiguate provenance. There is no enum or allowlist gating these strings today — they are free-form string constants — so nothing at the schema layer prevents accidental collision. The scope freeze **documents** the wrapper's chosen strings explicitly as the disambiguation mechanism.

### The `diagnostic_only: true` marker

The wrapper payload always carries `"diagnostic_only": true`. This marker exists so that no downstream summarizer can mistake a WeakPDELibrary wrapper report for a public weak-form supportability claim. In particular:

- `summarize_weak_form_supportability` continues to treat the pdelie-native `weak_1d` slice as `supported_existing_slice` (Heat/Burgers); the wrapper report **cannot** promote a PDE to `supported_existing_slice`.
- The wrapper contributes to `supportability_label = "diagnostic_only"` at most.

## Supportability policy update

The supportability-policy dict gains one new key and one re-scoping note:

- new key: `"supports_pysindy_weak_library_diagnostic": True` — records that the wrapper is available as a diagnostic-only surface
- existing key `"supports_weak_derivative_backend"` is re-scoped to *public strong-derivative-only pdelie-native path*, with an explicit inline note that the WeakPDELibrary wrapper is a diagnostic-scope weak derivative backend

Both changes are additive; no existing field is removed and no existing value is silently flipped.

## Legacy compatibility

- `summarize_discovery_result` is unchanged. TaskResult **composes with it** — it does not replace it. A caller who wants only the discovery-result summary continues to call `summarize_discovery_result` directly.
- `fit_pysindy_discovery(config=None)` continues to work at its existing default; the loosening in v0.31 accepts `config={"pysindy_model": <configured_SINDy>}` as an additional shape.
- The existing periodic-only guard in `to_pysindy_trajectories` (`src/pdelie/discovery/pysindy_bridge.py:18-28`) is unchanged; **PySINDy PDELibrary bridge is periodic-only in v0.31; FD-nonperiodic extension is explicitly deferred**.

## Retention window for `weak_1d`

`weak_1d` is retained through v0.32 close. Its removal is contingent on:

1. the v0.31 PySINDy `PDELibrary` bridge shipping a documented replacement path, AND
2. the `WeakPDELibrary` diagnostic wrapper landing a validated parity harness with a documented `O((dx)^p)` tolerance

Neither condition is expected to hold at the v0.31 close; the wrapper's `diagnostic_only: true` marker makes this explicit.

## Out of scope for v0.31

The following are deliberately deferred to later releases:

- root `pdelie` exports for any TaskResult, WeakPDELibrary wrapper, or discovery-task API
- WSINDy design-matrix / SR3 weak sparse recovery
- weak-form nonperiodic surface
- multi-channel or 2D FieldBatch dispatch (`v0.34`)
- SymmetryCandidate contract (`v0.30.1`)
- LieGG / trained-model extraction (`v0.35a`)
- benchmark policy or clean/noisy gating
- PDEBench / The Well support claims (`v0.32` external-data readiness cookbooks)
- promotion of the v0.30e advisory `lint` / `typecheck` / `coverage` CI jobs to blocking

## Validation requirements (for v0.31 proper, not v0.31a)

When the TaskResult runtime lands (v0.31b+):

- `run_pysindy_pde_task(...)` must call `_validate_strict_json_compatible(payload, name="discovery_task_result summary")` on the composed payload before return
- `summary_schema_version == "0.1"` and `summary_type == "discovery_task_result"` are literal-string invariants
- `backend_name in {"pysindy"}` and `target_convention in {"pde_library", "weak_pde_library"}` are literal-set invariants
- `input_layout == "scalar_1d_uniform"` is a literal invariant (widened only under a scope freeze)
- `weak_contract` non-null iff `target_convention == "weak_pde_library"`
- `underlying_discovery_result["summary_type"] == "discovery_result"`
- backend versions are strings from `importlib.metadata.version(...)` for `pysindy`, `sklearn`, `pdelie`

## Implementation pointer (for v0.31 proper)

The most surgical implementation places a new submodule `src/pdelie/tasks/discovery.py` with:

- `run_pysindy_pde_task(field, *, config, target_convention, task_name, target_terms=None, ...)` composing the existing `to_pysindy_trajectories` + `fit_pysindy_discovery` + `summarize_discovery_result` + `evaluate_discovery_recovery` machinery
- a strict-JSON helper import from `pdelie.reporting.summaries` — reuse `_validate_strict_json_compatible` without duplicating logic
- a `WeakPDELibraryDiagnostic` dataclass (submodule-only) with an `as_dict()` that produces the wrapper-payload shape above
- **no** new root `pdelie` export; **no** modification of `pdelie.residuals.weak_1d`

The existing summarizer strict-JSON helper (`_validate_strict_json_compatible` at `src/pdelie/reporting/summaries.py:196-202`) handles the serialization enforcement without modification.
