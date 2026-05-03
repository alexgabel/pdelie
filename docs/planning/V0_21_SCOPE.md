# V0.21 Scope - External Data Readiness Reports

**Status:** COMPLETE

`v0.21` is a reporting/supportability release for bring-your-own scalar 1D periodic data workflows.

Stable path:

```text
user-owned data -> canonical FieldBatch -> readiness report -> optional residual-evaluator preflight -> confidence/downstream workflows
```

## Public Runtime APIs

`v0.21` adds submodule-only runtime APIs:

- `pdelie.reporting.summarize_field_batch_readiness(...)`
- `pdelie.examples.run_external_data_readiness_example(...)`

No root `pdelie` exports are added.

## Frozen Report Semantics

`summarize_field_batch_readiness(...)` returns a JSON-compatible runtime report with:

- `summary_schema_version = "0.1"`
- `summary_type = "field_batch_readiness"`
- `readiness_label`
- `component_statuses`
- field shape/dim diagnostics
- finite-value diagnostics
- mask diagnostics
- time and x coordinate diagnostics
- metadata completeness diagnostics
- conservative metadata suggestions
- optional residual-evaluator preflight
- current stable-scope summary

Frozen `readiness_label` values:

- `ready`
- `needs_attention`
- `not_ready`

Frozen component statuses:

- `passed`
- `warning`
- `failed`
- `not_configured`
- `unavailable`

## Residual Preflight Policy

If no residual evaluator is supplied, residual compatibility is `not_configured`.

If a residual evaluator is supplied:

- it must be a `ResidualEvaluator`
- successful preflight includes a compact residual summary
- typed PDELie validation failures are captured into the report as `not_ready`
- unexpected non-PDELie exceptions propagate

## Metadata Policy

Readiness reports may suggest conservative metadata based on directly observed facts such as dims, coordinate spacing, scalar variable count, and inferred x-domain length.

They do not mutate `FieldBatch` inputs and do not infer PDE identity.

## Non-goals

`v0.21` does not add:

- file loaders
- `xarray.Dataset` support
- PDEBench or The Well adapters
- broad dataset adapter framework
- multidimensional support
- nonuniform-grid support
- resampling APIs
- metadata mutation APIs
- PDE identity inference
- train/test split policy
- heldout-leakage policy
- downstream discovery contracts
- new PDEs
- KS runtime promotion
- weak-form expansion
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- root `pdelie` exports

## Milestone Status

- Milestone 0: COMPLETE - scope freeze
- Milestone 1: COMPLETE - semantics freeze
- Milestone 2: COMPLETE - readiness helper implementation
- Milestone 3: COMPLETE - external data path coverage
- Milestone 4: COMPLETE - example and notebook alignment
- Milestone 5: COMPLETE - API/public-surface audit
- Milestone 6: COMPLETE - release gate and readiness

## Release Gate Expectations

`v0.21` is complete only if:

- readiness reports are JSON-compatible and covered by tests
- generated stable PDE fields report `ready`
- NumPy and xarray DataArray ingestion paths have readiness coverage
- malformed or out-of-scope field states report `needs_attention` or `not_ready`
- residual preflight captures typed validation failures without hiding unexpected exceptions
- new APIs are importable from their submodules only
- root `pdelie` remains unchanged
- no file loader, Dataset adapter, broad adapter, resampling API, new PDE, KS runtime API, weak-form expansion, split/leakage policy, time translation, neural/callable generator API, or operator API lands
