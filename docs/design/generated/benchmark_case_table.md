<!-- GENERATED FILE -- do not edit.
     Source: pdelie.benchmarks.case_registry.render_case_table()
     Regenerate: python -m pdelie.benchmarks.case_registry
     CI compares this file against a fresh render. -->

# Benchmark Cases (generated)

| case | freeze | equation family | profile | obstruction | numeric params |
|---|---|---|---|---|---:|
| C-1 | v0.37c | `heat_1d` | `constant` | no | 1 |
| C-2 | v0.37c | `heat_1d` | `sinusoidal` | no | 1 |
| C-3 | v0.37c | `heat_1d` | `sinusoidal` | yes | 1 |
| C-5 | v0.37c | `burgers_1d` | `constant` | yes | 1 |
| C-6 | v0.37c | `advection_diffusion_1d` | `localized_bump` | yes | 1 |
| C-7 | v0.38e | `advection_diffusion_1d` | `sinusoidal` | no | 2 |
| C-8 | v0.38e | `advection_diffusion_1d` | `sinusoidal` | yes | 2 |

## Derived counts

- **Total cases:** 7
- **Deliberate obstructions:** 4 (C-3, C-5, C-6, C-8)
- **Multi-parameter cases:** 2 (C-7, C-8)
- **Equation families:** `advection_diffusion_1d`, `burgers_1d`, `heat_1d`

### Cases by governing freeze

- **v0.37c:** C-1, C-2, C-3, C-5, C-6
- **v0.38e:** C-7, C-8

A signed freeze governs the population it measured. A case added later belongs to a later freeze, never retroactively to an earlier one.
