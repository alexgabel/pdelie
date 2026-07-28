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

## Nonperiodic Generator Layer (v0.33)

| Stage | Periodic | Nonperiodic |
| --- | --- | --- |
| `fit_translation_generator` | unchanged (spectral_fd, full-domain SVD) | finite_difference + interior-only shave at `boundary_trim_width`; reference fallback suppressed |
| `polynomial_translation_svd` | unchanged | accepts; forwards dispatch diagnostics; frozen four score names unchanged |
| `verify_translation_generator` | unchanged (FFT wrap) | overlap-crop ∩ interior trim |
| `run_pysindy_pde_task` | supported | **blocked** — `PySINDyDiscoveryUnsupportedBoundaryError` |

Boundary types dispatched: `periodic`, `dirichlet`, `neumann`, `open_unknown`.

**Claim scope.** v0.33a/b establish interior differential-operator covariance on the overlap. They do **not** establish boundary-value-problem preservation — the interior shave and the overlap crop discard exactly the rows that would settle it. The `symmetry_claim` diagnostic carries the distinction; `boundary_value_problem_preserved` and `boundary_value_problem_not_preserved` are reserved but never emitted.

**Resolution caveat.** Nonperiodic fit quality is PDE-dependent. Only Heat is well resolved below `num_points = 256`. The honest `span_distance` plus a low-row warning are emitted rather than a hard resolution gate.

## Variable-Coefficient Data Generators (v0.33d)

| PDE | `diffusivity_profile` | `advection_profile` |
| --- | --- | --- |
| Heat | yes | n/a |
| Burgers | yes | n/a |
| Advection-diffusion | yes | yes |
| KdV | no | n/a |
| Fisher-KPP | no | n/a |

Constant-coefficient path byte-preserved. Residual-side ν(x) support is deferred to v0.34a; feeding a variable-coefficient FieldBatch to a constant-coefficient evaluator is a documented misuse and is the mechanism of the admissibility crash test.

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

## External data readiness (v0.32d, submodule-only)

- `pdelie.examples.pdebench_burgers_1d_readiness` — narrow readiness cookbook for exactly one PDEBench 1D Burgers shard (`1D_Burgers_Sols_Nu0.001.hdf5`, DaRUS `10.18419/darus-2986`, CC-BY-4.0, MD5 `b4be2fc3383f737c76033073e6d2ccfb`). Not a broad PDEBench adapter. No recovery benchmark claim. `h5py` is installed via the narrow `[pdebench]` extra (`pip install 'pdelie[pdebench]'`; h5py-only).
- `pdelie.examples.the_well_feasibility_scan` — metadata-only scan of The Well v1 (Ohana et al., NeurIPS 2024). No network I/O. Every dataset is 2D or 3D on a structured grid with coupled channels or geometry; frozen conclusion is `blocked_multichannel_required`. Not a broad The Well adapter.

## Boundary Statement

PDELie reports empirical Lie-symmetry diagnostics under explicit contracts. A positive report means the configured evidence passed for the supplied field, residual evaluator, generator candidate, thresholds, and validation path. It is not a mathematical proof, a broad benchmark claim, a learned symmetry model, or a guarantee that finite transforms are safe outside the documented scope.
