# V0.22 Scope - Downstream Discovery Contracts

**Status:** COMPLETE

`v0.22` is a downstream supportability release for sparse-discovery workflows.

Stable path:

```text
FieldBatch / orbit batch / bridge outputs / backend-native discovery result
-> JSON-compatible discovery summaries
-> optional recovery summary
-> downstream workflow report
```

## Public Runtime APIs

`v0.22` adds submodule-only runtime APIs:

- `pdelie.discovery.summarize_discovery_bridge_output(...)`
- `pdelie.discovery.summarize_discovery_result(...)`
- `pdelie.reporting.summarize_downstream_discovery_workflow(...)`
- `pdelie.examples.run_downstream_discovery_contracts_example(...)`

No root `pdelie` exports are added.

## Frozen Report Semantics

Bridge summaries return JSON-compatible runtime reports with:

- `summary_schema_version = "0.1"`
- `summary_type = "discovery_bridge_output"`
- finite trajectory checks
- shared trajectory shape
- strictly increasing time diagnostics
- unique feature names
- source/provenance metadata

Discovery-result summaries return JSON-compatible runtime reports with:

- `summary_schema_version = "0.1"`
- `summary_type = "discovery_result"`
- backend status and backend name
- feature names and equation strings
- sparse equation-term mappings
- compact coefficient summaries
- optional feature-keyed recovery summaries

Workflow summaries return JSON-compatible runtime reports with:

- `summary_schema_version = "0.1"`
- `summary_type = "downstream_discovery_workflow"`
- `workflow_label`
- component statuses
- nested readiness, confidence, orbit-batch, bridge, and discovery-result reports
- orbit-provenance traceability diagnostics

## Coefficient And Recovery Policy

Discovery-result summaries do not copy full coefficient matrices into the report.

Coefficient arrays are summarized by:

- shape
- finite status
- L2 norm
- L-infinity norm
- nonzero count under `support_epsilon`

When `target_terms` are supplied, they must be feature-keyed:

```python
{"u": {"u_xx": 0.1}}
```

Per-feature recovery uses the existing `evaluate_discovery_recovery(...)` support/coefficient diagnostics. Aggregate recovery counts and rates summarize exact, partial, and failed feature recovery.

## Non-goals

`v0.22` does not add:

- split management
- train/test split policy
- heldout-leakage detection
- downstream augmentation policy
- a general discovery-backend framework
- manuscript benchmark thresholds
- file loaders
- `xarray.Dataset` support
- PDEBench or The Well adapters
- multidimensional support
- nonuniform-grid support
- new PDEs
- KS runtime promotion
- weak-form expansion
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- root `pdelie` exports

## Milestone Status

- Milestone 0: COMPLETE - scope freeze
- Milestone 1: COMPLETE - contract semantics freeze
- Milestone 2: COMPLETE - bridge output summary
- Milestone 3: COMPLETE - discovery result and recovery summary
- Milestone 4: COMPLETE - workflow summary and example
- Milestone 5: COMPLETE - API/public-surface audit
- Milestone 6: COMPLETE - release gate and readiness

## Release Gate Expectations

`v0.22` is complete only if:

- bridge summaries validate finite 2D trajectory arrays, strictly increasing time, and unique feature names
- discovery-result summaries accept PySINDy-style and backend-neutral result mappings without leaking coefficient arrays
- feature-keyed recovery summaries are covered by tests
- workflow summaries combine readiness, confidence, orbit-batch, bridge, and discovery-result reports
- orbit provenance checks report traceability only and do not manage splits or leakage
- new APIs are importable from their submodules only
- root `pdelie` remains unchanged
- no file loader, Dataset adapter, broad backend framework, new PDE, KS runtime API, weak-form expansion, split/leakage policy, time translation, neural/callable generator API, or operator API lands
