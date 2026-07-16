# PDEBench 1D Burgers Readiness Cookbook (v0.32d — frozen)

**Status:** FROZEN by v0.32d. Machine-readable form:
`configs/external_data/pdebench_burgers_1d_readiness.json`. Runtime entry:
`pdelie.examples.pdebench_burgers_1d_readiness.run_pdebench_burgers_1d_readiness_cookbook`.

**Decision label:** `v0_32d_pdebench_1d_burgers_readiness_and_the_well_feasibility_scan`.

## Scope

This cookbook is a **narrow** readiness reporter for exactly one PDEBench shard:

| Field | Value |
|---|---|
| Dataset family | 1D_Burgers |
| Dataset version | V8 (DaRUS) |
| Shard filename | `1D_Burgers_Sols_Nu0.001.hdf5` |
| DOI | [10.18419/darus-2986](https://darus.uni-stuttgart.de/dataset.xhtml?persistentId=doi:10.18419/darus-2986) |
| License | CC-BY-4.0 |
| Checksum (MD5) | `b4be2fc3383f737c76033073e6d2ccfb` |
| Format | HDF5 |
| Layout | `(n_traj, T, X)` float32 |
| HDF5 dataset paths | `/tensor`, `/x-coordinate`, `/t-coordinate` |
| Viscosity nu | 0.001 |
| Boundary condition | periodic in x |
| Equation convention | `u_t + u * u_x = nu * u_xx` (matches `pdelie.residuals.BurgersResidualEvaluator`) |

Cite: Takamoto et al., *PDEBench Datasets*, DaRUS V8, 2022.

## What this cookbook is NOT

- **not** a broad PDEBench adapter. There is no `from_pdebench`, no adapter registry, and no dataset-name inference.
- **not** a recovery benchmark. The residual preflight is diagnostic-only.
- **not** a model training path. There is no FNO / U-Net / PINN comparison.
- **not** a symmetry-discovery claim on external data.
- **not** a multi-channel / 2D widening.
- **not** a root `pdelie` export.

## How to use it

Users install `h5py` directly (v0.32d intentionally does not add a broad `pdelie[pdebench]` extra, because doing so would imply broad PDEBench support that is out of scope):

```bash
pip install h5py
```

Download the shard from DaRUS (CC-BY-4.0; obey the license) and note its path:

```bash
# From the DaRUS record at doi:10.18419/darus-2986
# Verify the MD5 against b4be2fc3383f737c76033073e6d2ccfb.
```

Then invoke the readiness cookbook:

```python
from pdelie.examples.pdebench_burgers_1d_readiness import (
    run_pdebench_burgers_1d_readiness_cookbook,
)

report = run_pdebench_burgers_1d_readiness_cookbook(
    cached_file_path="/path/to/1D_Burgers_Sols_Nu0.001.hdf5",
    residual_preflight=False,      # diagnostic-only; opt in explicitly
    max_trajectories=4,            # keep the FieldBatch cheap
)
```

Or run the CLI:

```bash
python -m pdelie.examples.pdebench_burgers_1d_readiness
```

## Conclusion vocabulary

The report's `conclusion` field takes exactly one of:

- `ready_scalar_1d_readiness_only` — file checksum matched; FieldBatch built; readiness label is `ready`. No residual metric attached.
- `ready_residual_preflight_only` — same as above **plus** a diagnostic-only Burgers residual (full-grid + interior-only L2). Requires `residual_preflight=True`. NOT a recovery claim.
- `blocked_boundary_metadata_unverified` — boundary evidence in the config is not marked `verified=True`.
- `blocked_parameter_convention_mismatch` — the equation convention drifts from PDELie's residual form.
- `blocked_nonuniform_grid` — the loaded x or t coordinate is not uniform within float32 quantization tolerance.
- `blocked_schema_mismatch` — the HDF5 layout does not match the pinned `(n_traj, T, X)` shape.
- `blocked_multichannel_required` — reserved; not emitted by this cookbook (this dataset is scalar).
- `blocked_download_or_checksum_failure` — the file's MD5 does not match the pinned value.
- `unavailable_no_cached_dataset` — no path supplied, or the path does not exist.

No conclusion label implies recovery success.

## Train/test policy

The DaRUS shard is monolithic — there is no in-file train/test split. The cookbook records this in `split_metadata` with `invented_by_cookbook = False`. Callers who need a split partition trajectories explicitly downstream; the cookbook never invents a split.

## Residual preflight

The residual preflight runs only when:

- the equation convention is verified (`equation_convention_match.conclusion == "match"`);
- coefficients are verified (`parameter_evidence.verified == True`);
- boundary metadata is verified (`boundary_condition_evidence.verified == True`);
- the coordinate grid is uniform.

When those gates pass and `residual_preflight=True`, the cookbook computes both full-grid and interior-only L2 norms of the Burgers residual on the loaded FieldBatch. Both are labeled `diagnostic_only = True`, and the report explicitly notes: **residual magnitudes reflect the reconstruction gap between PDELie's derivative backend and the source solver's operator; they are NOT a recovery benchmark.**

## References

- `configs/external_data/pdebench_burgers_1d_readiness.json` — frozen machine-readable config.
- `src/pdelie/examples/pdebench_burgers_1d_readiness.py` — narrow loader + report emitter.
- `tests/test_v0_32d_external_data_readiness.py` — 20 v0.32d contract tests.
- `docs/design/THE_WELL_FEASIBILITY_REPORT.md` — companion metadata-only scan.
