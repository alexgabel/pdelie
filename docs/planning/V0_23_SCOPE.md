# V0.23 Scope - Split / Leakage Provenance Diagnostics

**Status:** COMPLETE

`v0.23` is a downstream supportability release for reporting provenance risks across user-supplied partitions.

Stable path:

```text
user-supplied partition labels + FieldBatch/orbit-batch provenance
-> JSON-compatible split provenance report
-> leakage-risk diagnostics
-> optional downstream workflow summary integration
```

## Public Runtime APIs

`v0.23` adds submodule-only runtime APIs:

- `pdelie.reporting.summarize_split_leakage_provenance(...)`
- `pdelie.examples.run_split_leakage_provenance_example(...)`

It also extends:

- `pdelie.reporting.summarize_downstream_discovery_workflow(..., split_provenance=None)`

No root `pdelie` exports are added.

## Frozen Report Semantics

Split provenance reports return JSON-compatible runtime reports with:

- `summary_schema_version = "0.1"`
- `summary_type = "split_leakage_provenance"`
- `partition_counts`
- `sample_count`
- `provenance_available`
- `source_index_traceable`
- `shift_index_traceable`
- `duplicate_source_across_partitions`
- `duplicate_shifted_source_across_partitions`
- `identity_shift_cross_partition_overlap`
- `partition_pair_diagnostics`
- `risk_label`
- `risk_reasons`
- `component_statuses`
- `extra_metrics`

Frozen `risk_label` values:

- `no_detected_overlap`
- `traceable_overlap`
- `missing_provenance`
- `inconclusive`

## Interpretation

`v0.23` reports detectable provenance overlap only.

- `no_detected_overlap`: available provenance shows no same-source or same-source/same-shift overlap across distinct partitions.
- `traceable_overlap`: available provenance shows at least one source or orbit-derived sample appears across distinct partitions.
- `missing_provenance`: sample count is known but source/shift provenance is absent or insufficient.
- `inconclusive`: provenance is partially available but not enough to classify cleanly.

The helper accepts user-supplied partition labels and optional source/sample metadata. It does not choose label names or require a fixed train/heldout/test vocabulary.

## Orbit-Batch Provenance Policy

When `orbit_batch` is supplied, it may be:

- an `OrbitBatchResult`
- a `uniform_translation_orbit_batch` report mapping

The report uses existing `source_batch_indices`, `shift_indices`, raw shifts, and normalized shifts when present. Duplicate shifts remain preserved. Identity-shift overlap is reported separately from source-only overlap.

## Non-goals

`v0.23` does not add:

- no split creation
- train/test split management
- no leakage prevention
- benchmark policy
- downstream success criteria
- automatic augmentation policy
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
- Milestone 1: COMPLETE - semantics freeze
- Milestone 2: COMPLETE - split provenance helper
- Milestone 3: COMPLETE - orbit-batch risk coverage
- Milestone 4: COMPLETE - workflow integration and example
- Milestone 5: COMPLETE - API/public-surface audit
- Milestone 6: COMPLETE - release gate and readiness

## Release Gate Expectations

`v0.23` is complete only if:

- partition labels are user supplied and validated as non-empty strings
- partition/sample count mismatches raise typed validation errors
- optional metadata is strict JSON-compatible
- no-overlap, source-overlap, source-and-shift-overlap, identity-shift-overlap, missing-provenance, and partial-provenance cases are tested
- `summarize_downstream_discovery_workflow(...)` nests split provenance reports without changing split policy
- example output is JSON only
- new APIs are importable from their submodules only
- root `pdelie` remains unchanged
- no split manager, leakage-prevention helper, file loader, Dataset adapter, broad backend framework, new PDE, KS runtime API, weak-form expansion, time-translation API, neural/callable API, or operator API lands
