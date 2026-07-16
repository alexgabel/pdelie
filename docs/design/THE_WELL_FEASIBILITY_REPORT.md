# The Well Feasibility Report (v0.32d — frozen, metadata-only)

**Status:** FROZEN by v0.32d. Machine-readable form:
`configs/external_data/the_well_feasibility_scan.json`. Runtime entry:
`pdelie.examples.the_well_feasibility_scan.run_the_well_feasibility_scan`.

**Decision label:** `v0_32d_pdebench_1d_burgers_readiness_and_the_well_feasibility_scan`.

## Purpose

Determine, from the official The Well v1 metadata and code catalogue (no downloads), whether any dataset in the release admits a **scientifically honest** scalar 1D slice compatible with PDELie's `(batch, time, x, var)` contract.

Cite: Ohana, McCabe, et al., *The Well: a Large-Scale Collection of Diverse Physics Simulations for Machine Learning*, NeurIPS 2024 Datasets & Benchmarks Track.

Records: [polymathic-ai.org/the_well](https://polymathic-ai.org/the_well/) and [github.com/PolymathicAI/the_well](https://github.com/PolymathicAI/the_well).

## Result

**Conclusion: `blocked_multichannel_required`.**

The scan enumerates 23 datasets in The Well v1 release. Every dataset is either 2D or 3D on a structured grid and either carries multiple physically coupled channels or is coupled through the geometry itself. **No dataset in the release admits a scientifically honest scalar 1D slice.**

This is the correct v0.32d result — it is not a solvable gap. PDELie's scalar 1D contract does not accept "drop channels" tricks, "select one component" tricks, dimensional flattening, or averaging as valid scalar-1D reductions of coupled physics.

## Per-dataset findings (all `scalar_1d_extractable = False`)

Each row is drawn from The Well catalogue and paper appendix.

| Dataset | Dimension | Layout | Block reason |
|---|---|---|---|
| acoustic_scattering_discontinuous | 2D | 256×256 | acoustic scattering is intrinsically 2D and geometry-dependent |
| acoustic_scattering_inclusions | 2D | 256×256 | 2D geometry-dependent wave scattering |
| acoustic_scattering_maze | 2D | 256×256 | 2D maze geometry |
| active_matter | 2D | 256×256 | nematic dynamics require 2D |
| convective_envelope_rsg | 3D spherical | 256×128×256 | 3D stellar convection |
| euler_multi_quadrants (periodic + open BC) | 2D | 512×512 | 2D Riemann quadrants |
| gray_scott_reaction_diffusion | 2D | 128×128 | pattern formation is intrinsically 2D |
| helmholtz_staircase | 2D | 1024×256 | 2D staircase geometry |
| mhd_64 / mhd_256 | 3D | 64³ / 256³ | MHD turbulence is fundamentally 3D |
| planetswe | 2D spherical | 256×512 | shallow water on sphere |
| post_neutron_star_merger | 3D log-spherical | 192×128×66 | 3D relativistic MHD |
| rayleigh_benard (+ uniform variant) | 2D | 512×128 | convection cells are 2D |
| rayleigh_taylor_instability | 3D | 128³ | 3D instability |
| shear_flow | 2D | 128×256 / 256×512 | 2D Kelvin–Helmholtz |
| supernova_explosion_64 / _128 | 3D | 64³ / 128³ | asymmetric 3D explosion |
| turbulence_gravity_cooling | 3D | 64³ | 3D turbulence |
| turbulent_radiative_layer_2D / _3D | 2D / 3D | 128×384, 128×128×256 | cross-layer variation is 2D / 3D |
| viscoelastic_instability | 2D | 512×512 | 2D elastic turbulence |

## What this scan is NOT

- **not** a broad The Well adapter. There is no `from_the_well`, no adapter registry.
- **not** a recovery benchmark. There is no fit, no evaluation, no metric.
- **not** a channel-dropping trick to fake a 1D slice.
- **not** a "select one Cartesian axis" trick to fake a 1D slice.
- **not** a full-data download in CI. The scan is metadata-only and performs no network I/O.

## Reproducing the scan

```python
from pdelie.examples.the_well_feasibility_scan import (
    run_the_well_feasibility_scan,
)

report = run_the_well_feasibility_scan()
print(report["conclusion"])  # "blocked_multichannel_required"
```

Or via CLI:

```bash
python -m pdelie.examples.the_well_feasibility_scan
```

## When this may change

A future release of The Well may add datasets with genuinely scalar 1D content — e.g. a Burgers or KdV shard on a periodic 1D grid. If that happens, PDELie will re-run this scan and, if the new dataset satisfies the same evidence bar as the v0.32d PDEBench cookbook, add a companion narrow readiness cookbook. Until then, the frozen conclusion stands.

## References

- `configs/external_data/the_well_feasibility_scan.json` — frozen machine-readable scan input.
- `src/pdelie/examples/the_well_feasibility_scan.py` — metadata-only scan emitter.
- `tests/test_v0_32d_external_data_readiness.py` — 20 v0.32d contract tests.
- `docs/design/PDEBENCH_BURGERS_1D_READINESS_COOKBOOK.md` — companion PDEBench cookbook.
