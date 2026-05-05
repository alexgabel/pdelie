# Downstream and Export Provenance Workflow

This is a V0.29 recipe page over existing public APIs; it adds no runtime surface.

Use this path when handing canonical data, orbit batches, or discovery outputs to sparse discovery or ML workflows.

```text
FieldBatch / orbit batch / bridge output / backend-native result
-> JSON-compatible summaries
-> workflow report
-> optional split provenance diagnostics
```

## Recipe

1. Convert downstream bridge arrays with `to_pysindy_trajectories(...)` only after the source `FieldBatch` is ready.
2. Summarize bridge outputs before calling a backend.
3. Summarize backend-native results without copying full coefficient matrices into report artifacts.
4. Attach orbit-batch provenance when materialized translations are used.
5. Report user-supplied partitions with `summarize_split_leakage_provenance(...)`.

## Primary APIs

- `pdelie.discovery.to_pysindy_trajectories(...)`
- `pdelie.discovery.summarize_discovery_bridge_output(...)`
- `pdelie.discovery.summarize_discovery_result(...)`
- `pdelie.reporting.summarize_downstream_discovery_workflow(...)`
- `pdelie.reporting.summarize_split_leakage_provenance(...)`

## Defensible Claim

The downstream workflow reports provenance, shape, finite-value, recovery, and traceability evidence. PDELie does not choose benchmark thresholds, create train/test splits, prevent leakage, or certify downstream scientific success.

## Next Step

Use `end_to_end_dataset_to_downstream.md` for a full Dataset-to-downstream recipe, or `candidate_to_split_provenance.md` when the starting point is a supplied generator candidate.
