# PDELie Support Matrix

This page is a compact map of the stable `v0.x` user-facing surface. It is a navigation aid, not a replacement for `API_STABILITY.md`.

## Core Workflows

| Workflow | First APIs | Defensible output |
| --- | --- | --- |
| Data readiness | `from_numpy(...)`, `from_xarray(...)`, `from_xarray_dataset(...)`, `summarize_xarray_dataset_readiness(...)`, `summarize_field_batch_readiness(...)` | report-only compatibility checks for canonical scalar 1D periodic `FieldBatch` workflows |
| Candidate validation | `validate_symmetry_candidate(...)`, `verify_translation_generator(...)`, `summarize_generator_confidence(...)` | configured validation and finite-transform verification evidence |
| Downstream/export provenance | `to_pysindy_trajectories(...)`, `summarize_discovery_bridge_output(...)`, `summarize_discovery_result(...)`, `summarize_downstream_discovery_workflow(...)`, `summarize_split_leakage_provenance(...)` | backend-neutral runtime summaries, provenance traceability, and split-risk diagnostics |

## PDE Support Matrix

| PDE surface | Generator/data path | Residual evaluator | Vertical slice | Candidate validation | Weak support | External-data readiness |
| --- | --- | --- | --- | --- | --- | --- |
| Heat | Stable scalar 1D periodic synthetic path | Yes | Yes | Yes, configured validation | Frozen Heat weak report slice | Yes |
| Burgers | Stable scalar 1D periodic synthetic path | Yes | Yes | Yes, configured validation | Frozen Burgers weak report slice | Yes |
| KdV | Normalized scalar 1D periodic short-horizon path only | Yes, normalized form only | Yes | Yes, within frozen regime | No public weak KdV | Yes |
| Fisher-KPP reaction-diffusion | Stable scalar 1D periodic synthetic path | Yes | Yes | Yes, configured validation | Internal diagnostic feasibility only | Yes |
| Constant-coefficient advection-diffusion | Stable scalar 1D periodic synthetic path | Yes | Yes | Yes, configured validation | No public weak path | Yes |
| Kuramoto-Sivashinsky | No public runtime path | No public evaluator | No public slice | Internal no-go/decision evidence only | No public weak KS | No public KS readiness path |

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
