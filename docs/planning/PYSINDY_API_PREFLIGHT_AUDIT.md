# PySINDy API Preflight Audit

**Status:** MANDATORY prerequisite for v0.31b1 runtime authoring. Advisory reference for future PySINDy-touching releases (v0.31b2, v0.32.5, v0.33).

## Motivation

PySINDy evolves. The `pdelie.discovery` bridge is written against a specific minor-version shape of the upstream API — `PDELibrary` constructor keywords, `WeakPDELibrary` availability, the naming convention used by `.get_feature_names()`, the layout of `.coefficients_`, and the exception surface raised on misconfigured fits. Between the moment a scope document is frozen and the moment a coding agent picks it up, any of these shapes can silently shift under a pinned range (`pysindy>=1.7.5,<2`), a wheel-only patch release, or a transitive dependency (numpy, scipy, scikit-learn) bump. The task-bridge design in `DISCOVERY_TASK_RESULT_SCHEMA.md` assumes concrete field names, concrete feature-name formats, and a concrete config-lock shape in the adapter; if any of those assumptions has drifted since the design freeze, code written on top of them is wrong before it compiles.

This preflight exists to catch that drift *before* any code diff, test, or design edit is authored. **Fail-fast** here means: the coding agent runs the probes below as its first action on a v0.31b1 (or any downstream PySINDy-touching) task, and if any probe output differs from the recorded expectation, the agent halts. It does not attempt to reconcile, does not soft-adapt the code around the diff, does not silently rewrite tests to match the observed behavior. Instead, it emits an **assumption-diff report** as the final deliverable of that PR: a short document listing every probe whose actual output diverged from expected, the specific line in the design doc / adapter / contracts that referenced the now-wrong shape, and no code diff. The reviewer then decides whether to update the design doc, update this preflight doc, or update the `pyproject.toml` pin.

## Probes

### Probe 1 — Installed version

```bash
python -c 'import pysindy; print(pysindy.__version__)'
```

Expected: version string matching the `pyproject.toml` pin (`pysindy>=1.7.5,<2`). If `pysindy` is not importable (ImportError, ModuleNotFoundError), HALT: task-bridge work cannot proceed without pysindy. If the version parses but falls outside the pin range, treat this as a probe failure — either the environment is inconsistent with `pyproject.toml`, or the pin needs to be widened before code changes.

### Probe 2 — PDELibrary constructor surface

```python
from pysindy import PDELibrary
import inspect
print(inspect.signature(PDELibrary.__init__))
```

Expected: at minimum accepts `library_functions`, `function_names`, `derivative_order`, `spatial_grid`, `periodic` keyword arguments. If any of these five keywords is missing, renamed, or has a materially changed default from what `DISCOVERY_TASK_RESULT_SCHEMA.md` assumes, HALT and emit an assumption-diff report. Extra keywords beyond this set are informational, not a fail condition — record them in the report but do not halt on them alone.

### Probe 3 — WeakPDELibrary availability

```python
try:
    from pysindy import WeakPDELibrary
    print('available')
except ImportError:
    print('MISSING')
```

Expected: `available`. If `MISSING`, the `WeakPDELibrary` diagnostic wrapper (v0.31b2 target) is out of scope for the installed PySINDy version — v0.31b1 (`PDELibrary`-only) may still proceed, but the gap **must** be documented in the b1 commit message and surfaced to the reviewer so the b2 scope can be adjusted or the pin tightened.

### Probe 4 — Fit-result shape

Run a minimal `PDELibrary` fit against a synthetic scalar 1D signal, then read `.coefficients_` and `.get_feature_names()` to characterize the actual naming convention. In particular, record:

- The feature-name format for spatial derivatives — does PySINDy emit `u_1`, `u_1(1)`, `u_1_11`, `u_x`, `u_xx`, or something else?
- The token used for polynomial powers — literal `^2`, `**2`, `_2`, or juxtaposition (`u u`)?
- The token used for products between functions of the field and their derivatives (space-separated, `*`, or concatenated?).
- The dtype and shape of `.coefficients_` (2-D `(n_targets, n_features)` vs. flattened `(n_features,)`).

Record the observed feature-name format in this doc as a fixture note under `## Observed fixtures` (create the section if absent) with the PySINDy version string alongside. The v0.31b1 selected-term keys in `TaskResult.selected_terms` and `library_feature_names` MUST be derived from the observed format, not from any format assumed at design time.

### Probe 5 — Existing PDELie adapter invariants

```bash
grep -n 'ScopeValidationError' src/pdelie/discovery/pysindy_adapter.py
grep -n '_pysindy_defaults\|DEFAULT_PYSINDY_DISCOVERY_CONFIG' src/pdelie/discovery/pysindy_adapter.py
grep -n 'library_feature_names\|equation_terms' src/pdelie/discovery/contracts.py
```

Expected: config-lock at lines 203-204, `DEFAULT_PYSINDY_DISCOVERY_CONFIG` referenced in `pysindy_adapter` (verify the actual name/location), `library_feature_names` on `contracts.py:395` or thereabouts.

Recorded observations at the time this doc was authored (branch `feat/v0.31b0-prep`):

- `ScopeValidationError` raised on line **204** of `src/pdelie/discovery/pysindy_adapter.py` (`raise ScopeValidationError("fit_pysindy_discovery only supports config=None in V0.6 Milestone 2.")`).
- The default-config accessor imported into `pysindy_adapter.py` is **`get_default_pysindy_discovery_config`** (from `pdelie.discovery._pysindy_defaults`), *not* a bare `DEFAULT_PYSINDY_DISCOVERY_CONFIG` symbol. The v0.31b1 coding agent must reference the accessor, not the design-doc symbol name.
- `library_feature_names` appears on `src/pdelie/discovery/contracts.py` at lines **348** (schema read + validation) and **395** (constructor assignment on the summary object). `equation_terms` appears at lines 330, 335, 382, 396.

If line numbers or symbol names differ from the observations above when a future agent runs these probes, that agent MUST update this doc in the same PR that reflects the drift, and the v0.31b1 (or downstream) prompt should be updated to point at the new line numbers before code lands.

## Fail-fast policy

If ANY probe surfaces a diff from expected — a missing dependency, a renamed keyword, an unavailable symbol, a different feature-name format, a shifted line number that indicates deeper refactoring since the design freeze — the coding agent HALTS. No code diff is authored. No test file is created or edited. No design doc is edited. No release-gate manifest row is added. The single deliverable of the PR becomes an **assumption-diff report**: a short markdown document (or PR description body, if no doc target is natural) that enumerates each probe, its expected output, its actual output, and the specific line of `DISCOVERY_TASK_RESULT_SCHEMA.md`, `pysindy_adapter.py`, `contracts.py`, `pyproject.toml`, or this preflight doc that references the now-wrong shape.

The reviewer then decides the remediation path: (a) update the design doc if the change in PySINDy is an acceptable adaptation, (b) update this preflight doc if the expectation itself was wrong or stale, or (c) update the `pyproject.toml` pin (narrow, widen, or move) to restore compatibility with the assumed shape. Only after that reviewer decision is merged does a fresh PR resume the substantive v0.31b1 (or downstream) coding work. This policy is intentionally strict: silent adaptation to a drifted upstream API is exactly the failure mode this preflight exists to prevent, and it costs less to emit an assumption-diff report than to unwind a schema-first commit that codified a wrong contract.

## Cross-references

- `docs/design/DISCOVERY_TASK_RESULT_SCHEMA.md` — the `TaskResult` schema whose assumed field shapes (feature-name format, `library_feature_names`, `selected_terms`, `coefficients`) this preflight validates.
- `docs/planning/PDL_JSON_1_STRICT_JSON_INVENTORY.md` — the strict-JSON inventory sibling doc; probe 4's recorded feature-name format feeds the inventory's key-format entries.
- `docs/planning/V0_31_DISCOVERY_TASK_BRIDGE_SCOPE.md` — v0.31 scope freeze that specifies periodic-only `PDELibrary` bridge for b1, `WeakPDELibrary` diagnostic wrapper for b2, and the `fit_pysindy_discovery(config=...)` loosening that removes the `src/pdelie/discovery/pysindy_adapter.py:204` scope-lock referenced in probe 5.
