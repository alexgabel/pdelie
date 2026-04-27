# PDELie — Execution Plan (V0.8)

## Current Release Status

**V0.8 complete and release-ready**

This file is the execution record for the `v0.8` release series.

It should contain:

- a short closeout record for the completed `v0.7` release
- the active `v0.8` milestone sequence
- milestone-specific rules and gates

It should not redefine package contracts or roadmap commitments. Those belong in:

- `docs/specs/SPEC.md`
- `docs/specs/CONTRACTS_AND_DEFAULTS.md`
- `docs/specs/API_STABILITY.md`
- `docs/planning/ROADMAP.md`
- `docs/planning/V0_8_SCOPE.md`

`API_STABILITY.md` is updated only when a frozen runtime weak API actually lands.

---

## V0.7 Closeout

`v0.7` is complete as the structured external-data ingestion release.

Completed outcome:

- strict `pdelie.data.from_numpy(...)` ingestion into canonical `FieldBatch`
- strict runtime-optional `pdelie.data.from_xarray(...)` ingestion for `xarray.DataArray`
- parity protection proving imported Heat/Burgers-like data behaves like the native `FieldBatch` path
- a compact `v0.7` release gate and dedicated CI visibility job

`v0.8` begins from that frozen Heat/Burgers plus structured-ingestion surface.

This release series is weak-residual first.
It does not broaden the stable canonical object set, PDE coverage, or adapter surface.

---

## Milestone 0 — Roadmap Reset

**Status:** Complete

### Goal

Promote `v0.8` to the next committed release target, create `V0_8_SCOPE.md`, reset `PLAN.md`, and keep `API_STABILITY.md` unchanged.

### Completed Outcome

- promoted `v0.8` to committed in `ROADMAP.md`
- created `V0_8_SCOPE.md`
- reset `PLAN.md` as the active `v0.8` execution record
- left `API_STABILITY.md` unchanged

### Acceptance Criteria

M0 is complete only if:

- `ROADMAP.md`, `PLAN.md`, and `V0_8_SCOPE.md` are internally consistent
- `v0.7` is consistently described as completed
- `v0.8` is consistently described as the next committed release
- `v0.9` remains planned
- `API_STABILITY.md` remains unchanged during M0

---

## Milestone 1 — Weak Semantics Freeze

**Status:** Complete

### Goal

Freeze the exact weak residual formulas, test-function details, report schema, and benchmark fixtures before runtime implementation.

### Completed Outcome

- froze the exact weak residual formulas for Heat and Burgers
- froze the exact quartic-bump test-function formulas, local-coordinate scaling, and centered overlapping window profile
- froze the exact report schema for the stable window-indexed weak residual reports
- froze deterministic clean/noisy/coarse benchmark fixtures using the existing native generators and robustness utilities
- explicitly deferred `ResidualBatch` / `ResidualEvaluator` integration unless later experimental work justifies it

---

## Milestone 2 — Weak Residual Report Implementation

**Status:** Complete

### Goal

Implement report-style weak Heat/Burgers residual APIs only.

### Completed Outcome

- implemented `evaluate_weak_heat_residual(...)`
- implemented `evaluate_weak_burgers_residual(...)`
- landed one shared internal weak-window engine for the frozen quartic-bump, wrapped-periodic, trapezoidal report path
- derived `nu` from `field.metadata["parameter_tags"]["nu"]` when not provided
- added typed rejection for unsupported inputs and public-API boundary tests

---

## Milestone 3 — Optional Contract-Integration Exploration

**Status:** Complete

### Goal

Allow optional non-critical exploration of contract integration without making it part of the committed stable `v0.8` surface.

### Completed Outcome

- added a test-only report-space fitting / verification harness under `tests/_helpers/weak_contract_integration.py`
- reused the stable translation basis and transform stack without forcing weak reports into `ResidualBatch`, `ResidualEvaluator`, or any new runtime surface
- recorded singular values, condition diagnostics, rank estimates, and fallback reasons for the weak-report nullspace fit
- added an M3-only canonical translation fallback when the selected weak-report fit still drifted outside the stable translation span tolerance
- confirmed reproducible clean-fixture report-space verification on Heat and Burgers with no public API changes

### Closeout Decision

**Promising internal compatibility experiment; stable contract integration still deferred**

Observed deterministic clean-fixture outcome:

- Heat used canonical translation reference fallback with `fallback_reason="svd_translation_span_drift"` and achieved a first-epsilon wrong-vs-fitted median error ratio of `17.14x`
- Burgers used canonical translation reference fallback with `fallback_reason="weak_report_contract_span_drift"` and achieved a first-epsilon wrong-vs-fitted median error ratio of `6.04x`
- both PDEs therefore cleared the internal `5x` closeout target while keeping contract integration out of the stable `v0.8` surface

M4 proceeds as planned. `v0.8` remains weak-residual-report first, and stable contract integration is still deferred.

---

## Milestone 4 — Robustness Comparison Layer

**Status:** Complete

### Goal

Add deterministic robustness comparisons against the current spectral/analytic path.

### Completed Outcome

- added a compact internal downstream benchmark helper under `tests/_helpers/weak_robustness_benchmark.py`
- compared the strong path against the weak-report path on the frozen clean/noisy/coarse Heat/Burgers matrix
- kept the benchmark summary-level and internal-only, with no new public API surface
- added frozen imported-parity checks for `from_numpy` on `heat/noisy` and `burgers/coarse`
- kept `from_xarray` as optional-runtime parity only

### Frozen M4 Benchmark Contract

M4 is frozen to one downstream benchmark matrix.
It compares translation fitting plus held-out verification, not direct weak-report-vs-strong-residual magnitudes.

Shared M4 settings:

- `train_batch_size = 4`
- `heldout_batch_size = 3`
- `num_times = 33`
- `num_points = 64`
- `noise_std_fraction = 1e-3`
- coarse degradation is exactly `subsample_time(stride=2)` then `subsample_x(stride=2)`
- wrong-generator control is fixed to `[0.0, 0.0, 1.0, 0.0]`

Frozen M4 seeds:

- Heat:
  - clean training seed `8401`
  - clean heldout seed `8402`
  - noisy training seed `8403`
  - noisy heldout seed `8404`
- Burgers:
  - clean training seed `8501`
  - clean heldout seed `8502`
  - noisy training seed `8503`
  - noisy heldout seed `8504`

Frozen degraded-data success rule:

- clean baseline:
  - both strong and weak paths must be deterministic on repeated runs for Heat and Burgers
  - both paths must return either in-tolerance translation coefficients or an explicit canonical translation reference fallback
  - both paths must achieve a first-epsilon wrong-vs-fitted median separation ratio of at least `5.0x` on clean Heat and clean Burgers
- degraded robustness:
  - for each PDE separately, at least one degraded condition in `{noisy, coarse}` must produce a weak-path robustness signal
  - a weak-path robustness signal requires deterministic repeated-run behavior and either:
    - weak contract stability where the weak path returns in-tolerance translation coefficients or a canonical translation fallback and the strong path does not, or
    - weak separation where the weak first-epsilon wrong-vs-fitted median separation ratio is at least `1.5x` the strong-path ratio and the weak-path ratio is at least `3.0x`
- M4 does not require the weak path to beat the strong path on every degraded fixture
- imported-field parity in M4 must reuse the same frozen seeds and degradations after canonical ingestion

### Closeout Decision

**Frozen representative robustness signal landed; weak degraded passes were fallback-driven, not in-tolerance weak-fit recoveries**

Observed outcome:

- Heat:
  - passing degraded condition: `noisy`
  - `robustness_signal_source = "contract_stability_signal"`
  - weak `contract_mode = "canonical_fallback"`
  - weak `fallback_reason = "svd_translation_span_drift"`
  - weak ratio: `17.93x`
  - strong ratio: `18.65x`
  - plain-language result: weak robustness signal via canonical fallback
- Burgers:
  - passing degraded conditions: `noisy` and `coarse`
  - representative closeout case: `noisy`
  - `robustness_signal_source = "contract_stability_signal"`
  - weak `contract_mode = "canonical_fallback"`
  - weak `fallback_reason = "weak_report_contract_span_drift"`
  - weak ratio: `9.90x`
  - strong ratio: `60.39x`
  - plain-language result: weak robustness signal via canonical fallback
- imported parity:
  - required `from_numpy` subset passed on `heat/noisy` and `burgers/coarse`
  - optional `from_xarray` subset was skipped because `xarray` was not installed in the active `.venv`

Interpretation:

- M4 provides the frozen release signal required for `v0.8`
- the degraded weak-path wins are currently driven by canonical fallback plus stable held-out verification behavior, not by direct in-tolerance weak-fit recovery
- this keeps the weak report path viable for the release, but it does not change the M3 conclusion that stable contract integration remains deferred

---

## Milestone 5 — Optional KdV Stress

**Status:** COMPLETE

### Goal

Keep KdV as optional non-blocking exploratory stress coverage only.

### Outcome

- optional KdV stress deferred/skipped for `v0.8`
- no weak KdV runtime surface lands in `v0.8`
- M6 proceeds unchanged
- no stable KdV API/export

### Closeout

- weak KdV deferred because the frozen `v0.8` quartic-bump weak profile is mathematically unsuitable for an honest KdV weak form
- KdV `u_xxx` requires a third-order integration-by-parts treatment, but the frozen profile only guarantees `phi = 0` and `phi_x = 0` at support boundaries; it does not guarantee `phi_xx = 0`
- the boundary incompatibility is explicit in the frozen profile: `beta(s) = (1 - s^2)^2` has `beta''(±1) = 8`, so the required third-derivative boundary cancellation fails
- M4's degraded weak-path wins were via canonical fallback / contract stability, not via in-tolerance weak-fit recovery or separation superiority over the strong path
- because the current release case for weak methods is already fallback-backed and narrow, `v0.8` does not broaden into a harder weak KdV branch
- this is a mathematical scope guard, not a timing defer; any future real weak KdV work would require a new weak-profile freeze with higher-order boundary vanishing

---

## Milestone 6 — Release Gate

**Status:** COMPLETE

### Goal

Add a compact release gate and align docs once runtime weak APIs land.

### Outcome

- compact `v0_8-release-gate`
- dedicated `v0_8-release-gate` CI visibility job
- release metadata and release-facing docs aligned for direct `0.8.0`
- package-smoke extended with a tiny built-wheel weak-report check

### Closeout

- implemented `tests/test_v0_8_release_gate.py` on top of the landed weak-report, M4 benchmark, and KdV-feasibility helpers
- added the `v0_8-release-gate` job to CI without changing the earlier release-gate jobs
- aligned `pyproject.toml`, `CHANGELOG.md`, `README.md`, `ROADMAP.md`, and `V0_8_RELEASE_READINESS.md` with the implemented `v0.8` surface
- audited `docs/specs/API_STABILITY.md` against the landed weak runtime surface and kept the document aligned with no new stable weak-derivative or KdV API claims
- kept the release interpretation narrow: degraded weak-path wins remain representative fallback-backed contract-stability signals, not direct weak-fit recovery or general weak superiority
- encoded the strict direct-final release path: full test suite, build, clean wheel smoke, optional TestPyPI preflight if available, and final tagging only after CI is green
- post-`v0.8` CI cleanup remains a follow-up item; historical release-gate jobs stay in place for this milestone

---

## Executed Milestone Sequence

Locked sequence:

Milestone 0 -> roadmap reset  
Milestone 1 -> weak semantics freeze  
Milestone 2 -> weak residual report implementation  
Milestone 3 -> optional contract-integration exploration  
Milestone 4 -> robustness comparison layer  
Milestone 5 -> optional KdV stress  
Milestone 6 -> release gate

---

## Rules

- DO NOT broaden `docs/specs/API_STABILITY.md` beyond the frozen `v0.8` weak residual report surface
- DO NOT add a stable weak derivative API in `v0.8`
- DO NOT force weak outputs into `DerivativeBatch` or `ResidualBatch` in `v0.8`
- DO NOT promote KdV to stable scope in `v0.8`
- DO NOT broaden `v0.8` into nonuniform-grid, multidimensional, multivariable, operator, or adapter work

---

## Status

- `v0.7`: COMPLETE
- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE
