# V0.13 Scope Freeze

## Summary

`v0.13` is the public orbit and coverage diagnostics release for `pdelie`.

Stable release theme:

> promote the successful `v0.12` internal orbit/coverage feasibility into narrow public diagnostics under `pdelie.invariants`.

Stable path:

`canonical periodic 1D FieldBatch + uniform translation action -> grid-point coverage diagnostics + transform-consistency diagnostics -> compact example/release gate`

These diagnostics support invariant and finite-transform workflows.
In short: diagnostics support invariant/finite-transform workflows but do not construct augmented datasets.
They do not construct augmented datasets.

---

## Motivation

`v0.12` showed that paper-agnostic orbit/coverage diagnostics are useful over existing stable Heat and KdV paths:

- periodic-window grid coverage can be reported deterministically
- uniform translations preserve canonical field structure
- inverse and period-wrap consistency are measurable
- residual RMS is stable under representative Heat and KdV shifts
- provenance from `InvariantApplier` can be checked without requiring full preprocess-log equality

`v0.13` promotes only that diagnostic layer.
It does not promote downstream experiment policy, augmentation recipes, or private-paper branch logic.

---

## Stable Scope

`v0.13` adds two runtime public APIs under `pdelie.invariants` only:

```python
pdelie.invariants.compute_periodic_window_coverage(
    *,
    x,
    windows,
    shifts,
    domain_length=None,
) -> dict[str, Any]

pdelie.invariants.diagnose_uniform_translation_consistency(
    field,
    *,
    shifts,
    residual_evaluator=None,
) -> dict[str, Any]
```

Both helpers:

- return JSON-compatible runtime report dicts
- mutate no inputs
- create no canonical objects
- return no transformed `FieldBatch` objects
- have no root `pdelie` exports
- are supportability diagnostics, not manuscript schemas or sparse-discovery policy

`v0.13` also adds:

- `python -m pdelie.examples.orbit_coverage_diagnostics`
- `pdelie.examples.run_orbit_coverage_diagnostics_example(...)`
- compact `v0_13-release-gate` coverage

The example output is a runtime smoke summary, not a canonical artifact schema.

---

## `compute_periodic_window_coverage(...)` Semantics

Grid convention:

- one-dimensional uniform periodic grid
- endpoint excluded
- endpoint-duplicated grids are rejected
- inferred domain length is `len(x) * dx`, not `x[-1] - x[0]`
- supplied `domain_length` must match `len(x) * dx`

Coverage convention:

- `coverage_type = "grid_point"`
- `coverage_fraction = covered_grid_points / num_grid_points`
- this is not continuous interval measure
- windows are half-open: `[start, start + width)`
- coordinates, starts, and shifts are reduced modulo `domain_length`
- boundary tolerance is `1e-12 * domain_length`
- repeated windows increase coverage counts but not covered point count
- duplicate shifts are allowed and counted
- raw and normalized shifts are both reported
- max uncovered run is reported in grid points and physical length

Shift convention:

- `coverage_convention = "preimage_of_fixed_window_under_translation"`
- `shift_convention = "field_shift_then_fixed_window"`
- equivalent workflow: translate the field by `shift`, then observe a fixed window
- positive shift means original point `x0` is covered when `(x0 + shift) mod domain_length` lies inside the fixed window
- therefore the covered preimage region is `[window_start - shift, window_start + width - shift)` modulo the domain

Report fields include:

- `summary_schema_version = "0.1"`
- `summary_type = "periodic_window_coverage"`
- domain length, inferred domain length, `dx`, and grid point count
- raw and normalized windows
- raw and normalized shifts
- coverage counts
- covered point count and coverage fraction
- min, max, and mean coverage count
- max uncovered run in grid points and physical length

---

## `diagnose_uniform_translation_consistency(...)` Semantics

Supported inputs:

- canonical scalar 1D uniform periodic `FieldBatch`
- shifts as a non-empty finite float sequence
- optional `ResidualEvaluator`

The helper uses existing `InvariantApplier` and uniform translation.
It returns a report only and never returns transformed fields.

Structure preservation means:

- dims are preserved
- shape is preserved
- coords are preserved
- metadata is preserved
- var names are preserved
- mask shape/content are preserved

Preprocess logs are not required to be equal.
The helper reports the appended provenance entry:

- `operation == "invariant_apply"`
- `construction_method == "uniform_translation"`
- axis
- shift
- preprocess-log length delta

Error metrics:

- inverse error: relative L2 between inverse-transformed values and original values
- period-wrap error: relative L2 between `shift` and `shift + domain_length`
- relative L2 denominator: `norm(reference) + 1e-12`
- residual RMS: `sqrt(mean(residual**2))`
- residual absolute delta: `abs(after_rms - before_rms)`
- residual relative delta: `abs(after_rms - before_rms) / (abs(before_rms) + 1e-12)`
- residual stability passes if `absolute_delta <= 1e-8 or relative_delta <= 1e-6`

Residual evaluator behavior:

- if `residual_evaluator is None`, residual fields are reported as `None`
- if a residual evaluator is supplied, evaluator failures are fatal typed validation errors
- evaluator failures are not silently converted into per-shift failures

Report fields include:

- `summary_schema_version = "0.1"`
- `summary_type = "uniform_translation_consistency"`
- field dims and shape
- equation tag
- domain length and `dx`
- raw and normalized shifts
- residual evaluator name or `None`
- per-shift structure flags, provenance fields, inverse/period-wrap errors, residual metrics, and pass booleans

---

## Non-goals

`v0.13` explicitly does not include:

- a new PDE
- stable KS generator promotion
- stable KS residual evaluator promotion
- KS example or imported parity
- weak KS
- broad adapters
- PDEBench or The Well support
- multidimensional grids
- nonuniform grids
- multivariable systems
- operator-facing symmetry APIs
- public orbit-view builders
- stable public augmentation utilities
- train-augmentation policy
- sparse-discovery branch policy
- private-paper experiment logic
- manuscript-specific thresholds, tables, figures, or labels
- root `pdelie` export expansion

KS remains internal feasibility/no-go evidence from `v0.11` plus internal diagnostic evidence from `v0.12`.

---

## Relationship To Downstream Orbit-augmentation Work

Downstream orbit-augmentation experiments may use the new diagnostics to measure periodic-window coverage and translation consistency.

Reusable `pdelie` scope:

- grid-point periodic window coverage
- finite-transform consistency checks
- residual stability under stable translation actions
- provenance checks for invariant applications
- JSON-compatible runtime summaries

Downstream-only scope:

- augmentation policy
- train/test branch construction
- sparse-regression policy
- dataset-specific recovery thresholds
- paper-specific labels and plots

---

## Milestones

### Milestone 0 - Scope Freeze

Freeze `v0.13` as public orbit/coverage diagnostics under `pdelie.invariants`.

### Milestone 1 - API Semantics Freeze

Freeze exact coverage convention, shift sign, domain-length inference, boundary tolerance, duplicate behavior, transform-consistency metrics, provenance policy, and evaluator failure behavior.

### Milestone 2 - Periodic Coverage Diagnostic

Implement `pdelie.invariants.compute_periodic_window_coverage(...)` and document it in `API_STABILITY.md`.

### Milestone 3 - Translation Consistency Diagnostic

Implement `pdelie.invariants.diagnose_uniform_translation_consistency(...)` and document it in `API_STABILITY.md`.

### Milestone 4 - Example and Reporting Alignment

Add `python -m pdelie.examples.orbit_coverage_diagnostics` and `pdelie.examples.run_orbit_coverage_diagnostics_example(...)`.

### Milestone 5 - API / Public-surface Audit

Confirm the diagnostics are importable from `pdelie.invariants` only and that augmentation, KS, weak KS, broad adapters, and root exports remain absent.

### Milestone 6 - Release Gate and Readiness

Add `tests/test_v0_13_release_gate.py`, update CI, bump package metadata to `0.13.0`, and align release-facing docs.

---

## Release-gate Expectations

The `v0_13-release-gate` should be compact and representative.
It should not duplicate the full invariant diagnostic, example, public API, or historical release-gate suites.

Expected gate coverage:

- new diagnostics exist under `pdelie.invariants`
- new diagnostics are absent from root `pdelie`
- `API_STABILITY.md` documents the two public diagnostics
- representative coverage case has the frozen positive-shift convention
- representative transform-consistency case passes structure, provenance, inverse, period-wrap, and residual checks
- example module emits JSON only
- no public augmentation, orbit-view, KS, weak KS, broad adapter, or operator API lands

Historical release-gate tests remain covered by full editable tests.

---

## Status

- `v0.12`: COMPLETE as diagnostics/supportability hardening
- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE
