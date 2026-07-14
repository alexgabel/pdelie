# PDELie Support Matrix

This page is a compact map of the stable `v0.x` user-facing surface. It is a navigation aid, not a replacement for `API_STABILITY.md`.

The machine-readable version for the current `v0.31` release is `support_matrix.v0_31.json`. The `v0.30` matrix at `support_matrix.v0_30.json` and the `v0.29` matrix at `support_matrix.v0_29.json` are retained for compatibility.

## Core Workflows

| Workflow | First APIs | Defensible output |
| --- | --- | --- |
| Data readiness | `pdelie.data.from_numpy(...)`, `pdelie.data.from_xarray(...)`, `pdelie.data.from_xarray_dataset(...)`, `pdelie.reporting.summarize_xarray_dataset_readiness(...)`, `pdelie.reporting.summarize_field_batch_readiness(...)` | report-only compatibility checks for canonical scalar 1D periodic `FieldBatch` workflows |
| Candidate validation | `pdelie.symmetry.validate_symmetry_candidate(...)`, `pdelie.verification.verify_translation_generator(...)`, `pdelie.reporting.summarize_generator_confidence(...)` | configured validation and finite-transform verification evidence |
| Downstream/export provenance | `pdelie.discovery.to_pysindy_trajectories(...)`, `pdelie.discovery.summarize_discovery_bridge_output(...)`, `pdelie.discovery.summarize_discovery_result(...)`, `pdelie.reporting.summarize_downstream_discovery_workflow(...)`, `pdelie.reporting.summarize_split_leakage_provenance(...)` | backend-neutral runtime summaries, provenance traceability, and split-risk diagnostics |

## PDE Support Matrix

| PDE | Generator | Residual | Vertical slice | Candidate validation | Weak support | External-data readiness |
| --- | --- | --- | --- | --- | --- | --- |
| Heat | yes | yes | yes | yes | frozen weak slice | yes |
| Burgers | yes | yes | yes | yes | frozen weak slice | yes |
| KdV | normalized short-horizon only | yes | yes | yes | no | yes |
| Fisher-KPP | yes | yes | yes | yes | internal weak diagnostic only | yes |
| Advection-diffusion | yes | yes | yes | yes | no | yes |
| KS | no public runtime | no | no | diagnostic/no-go | no | no |

## Selected Runtime Helpers

These helpers are stable public APIs under their submodules. They remain runtime supportability tools, not canonical objects or manuscript artifact schemas.

- `pdelie.reporting.summarize_generator_fit_diagnostics`
- `pdelie.invariants.compute_periodic_window_coverage`
- `pdelie.invariants.diagnose_uniform_translation_consistency`
- `pdelie.reporting.summarize_invariant_workflow`
- `pdelie.invariants.summarize_uniform_translation_orbit`
- `pdelie.invariants.build_uniform_translation_orbit_batch`
- `pdelie.invariants.OrbitBatchResult`
- `pdelie.symmetry.validate_symmetry_candidate`
- `pdelie.symmetry.FormulaGeneratorFamily`
- `pdelie.reporting.summarize_generator_confidence`
- `pdelie.reporting.summarize_field_batch_readiness`
- `pdelie.discovery.summarize_discovery_bridge_output`
- `pdelie.discovery.summarize_discovery_result`
- `pdelie.reporting.summarize_downstream_discovery_workflow`
- `pdelie.reporting.summarize_split_leakage_provenance`
- `pdelie.reporting.summarize_weak_form_supportability`
- `pdelie.data.from_xarray_dataset`
- `pdelie.reporting.summarize_xarray_dataset_readiness`

## Boundary Statement

PDELie reports empirical Lie-symmetry diagnostics under explicit contracts. A positive report means the configured evidence passed for the supplied field, residual evaluator, generator candidate, thresholds, and validation path. It is not a mathematical proof, a broad benchmark claim, a learned symmetry model, or a guarantee that finite transforms are safe outside the documented scope.
