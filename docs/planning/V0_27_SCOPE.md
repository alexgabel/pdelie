# V0.27 Scope - Multi-Generator Diagnostics Decision

**Status:** COMPLETE

## Summary

`v0.27` is a multi-generator diagnostics decision release.

Stable investigation path:

```text
canonical scalar 1D periodic FieldBatch
-> residual evaluator
-> supplied multi-row GeneratorFamily
-> algebraic diagnostics + PDE-context diagnostics + fit probe diagnostics
-> explicit public promotion decision
```

Release conclusion:

```text
multi_generator_diagnostics_feasible_fitting_deferred
```

The release separates:

- `algebraic_diagnostics`: span, rank, closure, brackets, and structure constants
- `pde_context_diagnostics`: whether generator/PDE pairs are meaningful and empirically checked
- `fit_probe_diagnostics`: internal-only recoverability probes
- `public_promotion_decision`: whether any public API promotion is justified

Closure does not imply PDE residual symmetry.

## Public API Notes

New submodule-only runtime example:

- `pdelie.examples.run_multi_generator_diagnostics_example(...)`
- `python -m pdelie.examples.multi_generator_diagnostics`

Behavior updates to existing public diagnostic helpers:

- `pdelie.symmetry.diagnose_generator_family_closure(...)` now reports well-formed rank-deficient families as diagnostic reports instead of raising solely because the rows are redundant.
- `pdelie.symmetry.compare_generator_spans(...)` now reports zero-rank or rank-deficient span comparisons as failed/warning reports instead of crashing for well-formed families.
- `pdelie.symmetry.validate_symmetry_candidate(...)` now accepts `closure_required=True|False` for `GeneratorFamily` candidates.

No new public multi-generator fitting API, finite-flow API, invariant-chart API, orbit builder, BCH composition API, exponential-map flow integration, group-action atlas, or root export was added.

## Frozen Semantics

Bracket convention:

```text
[X_i, X_j] = X_i · ∇X_j - X_j · ∇X_i
```

Structure constants:

```text
[X_i, X_j] = sum_k C[i, j, k] X_k
```

Frozen diagnostic labels:

- `algebraic_diagnostics_feasible`
- `pde_context_validation_diagnostic_only`
- `fit_probe_diagnostic_only`
- `multi_generator_diagnostics_feasible_fitting_deferred`
- `multi_generator_fitting_candidate_for_future_promotion`
- `deferred_no_go`

Frozen PDE-context labels:

- `known_pde_symmetry`
- `algebraic_only`
- `blocked_no_finite_transform`
- `blocked_parameter_policy`
- `failed_residual_preservation`
- `not_meaningful_for_pde`

Rank policy:

- malformed family -> typed validation error
- well-formed rank-deficient family -> diagnostic status with `family_rank_status = "rank_deficient"`
- rank-deficient reference/span comparison -> failed or warning report

## Algebraic Diagnostic Matrix

`v0.27` records exact supplied-family evidence for:

- `abelian_two_translation_family`: `X1 = ∂x`, `X2 = ∂t`
- `affine_x_family`: `X1 = ∂x`, `X2 = x∂x`, `[X1, X2] = X1`
- `affine_u_family`: `X1 = ∂u`, `X2 = u∂u`, `[X1, X2] = X1`
- `nonclosed_polynomial_family`: `X1 = ∂x`, `X2 = x^2∂x`, `[X1, X2] = 2x∂x` outside the span
- `rank_deficient_affine_family`: redundant rows such as `X1 = ∂x`, `X2 = 2∂x`
- `basis_mismatch_family`: same apparent rows under incompatible basis specs

## Explicit Non-goals

- no public multi-generator PDE fitting
- no multi-generator invariant charts
- no finite multi-generator flows
- no BCH composition
- no exponential-map finite-flow integration
- no multi-parameter orbit charts
- no group-action atlas
- no operator-facing APIs
- no neural or callable generator APIs
- no root export expansion
- no train/test policy or leakage prevention
- no broad adapters or file loaders
- no multidimensional or nonuniform stable support

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

## Release Gate

`v0.27` is complete only if:

- supplied closed families report expected structure constants under the frozen bracket convention
- non-closed families report nonzero closure residuals
- rank-deficient well-formed families return diagnostic reports, not automatic exceptions
- multi-row candidate validation separates algebraic evidence from PDE-context evidence
- the public example is diagnostic-only and performs no fitting
- no public multi-generator fitting, finite-flow, BCH, invariant-chart, orbit-chart, operator, neural/callable, or root export surface lands
- CI uses one compact current release gate plus full editable tests and package smoke
- package-index publishing remains deferred until `v1.0` or later
