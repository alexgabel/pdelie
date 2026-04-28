# V0.10 Scope Freeze

## Summary

`v0.10` is the supportability and `v1.0` readiness release for `pdelie`.

Its purpose is:

> harden the existing Heat/Burgers/weak-report/KdV engine into a more supportable public surface before adding more numerical scope.

Stable release definition:

`existing stable Heat/Burgers/weak-report/KdV surfaces -> compact supportability reports -> consistent examples/release gates/docs -> v1.0 readiness`

`v0.10` is not a new numerics release.
It does not add another PDE, weak KdV, broad adapters, multidimensional grids, or operator-facing work.

---

## Stable Scope

Stable `v0.10` scope is limited to supportability work around the surfaces already stable through `v0.9`:

- canonical Heat/Burgers strong paths
- window-indexed weak Heat/Burgers report APIs
- structured `from_numpy(...)` and `from_xarray(...)` ingestion
- normalized periodic short-horizon KdV strong path
- polynomial translation fitting and held-out verification
- existing examples and release gates
- package, publishing, and release-readiness documentation

Committed supportability directions:

- compact runtime reporting helpers over existing residual, fit, verification, and vertical-slice outputs
- consistent example summaries where useful
- API stability audit and accidental-public-surface guards
- CI release-gate cleanup
- package/readiness documentation cleanup for eventual `v1.0` publishing decisions

---

## Public API Policy

M1 freezes a new runtime-level public helper surface for M2:

- `pdelie.reporting`

This is a public runtime submodule.
It is not a canonical object system.
It has no root `pdelie` exports.

Frozen M2 public APIs:

```python
summarize_residual_batch(residual: ResidualBatch) -> dict[str, Any]
summarize_weak_residual_report(report: Mapping[str, Any]) -> dict[str, Any]
summarize_generator_family(generator: GeneratorFamily) -> dict[str, Any]
summarize_verification_report(report: VerificationReport) -> dict[str, Any]
summarize_vertical_slice(
    *,
    derivatives: DerivativeBatch,
    residual: ResidualBatch,
    generator: GeneratorFamily,
    verification: VerificationReport,
    extra_metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]
```

Frozen common reporting rules:

- runtime-level, not a canonical object
- deterministic for identical inputs
- JSON-compatible plain Python dict outputs
- NumPy arrays become lists
- NumPy scalar values become Python scalar values
- input object types and required report keys are validated
- validation failures use existing typed validation errors
- scoped to existing stable surfaces
- no helper mutates its inputs
- no helper creates or changes canonical objects
- no manuscript-specific table, figure, threshold, or label logic
- no root `pdelie` exports
- `API_STABILITY.md` is updated in M2 when these APIs land

---

## Reporting Helper Schemas

Every reporting helper returns a dict containing:

- `summary_schema_version = "0.1"`
- `summary_type`

### ResidualBatch Summary

`summarize_residual_batch(...)` freezes these keys:

- `summary_schema_version`
- `summary_type = "residual_batch"`
- `residual_shape`
- `definition_type`
- `normalization`
- `max_abs_residual`
- `rms_residual`
- `diagnostics`

`max_abs_residual` and `rms_residual` are computed from `residual.residual`.
The original diagnostics are preserved after JSON-safe conversion.

### Weak Residual Report Summary

`summarize_weak_residual_report(...)` freezes these keys:

- `summary_schema_version`
- `summary_type = "weak_residual_report"`
- `equation`
- `equation_form`
- `method_family`
- `normalization`
- `window_residual_shape`
- `max_abs_residual`
- `l2_residual`
- `diagnostics`

The helper supports the frozen `v0.8` weak report shape only.
It validates that the input mapping contains the frozen weak report keys before summarizing.

### GeneratorFamily Summary

`summarize_generator_family(...)` freezes these keys:

- `summary_schema_version`
- `summary_type = "generator_family"`
- `parameterization`
- `normalization`
- `coefficient_shape`
- `coefficients`
- `generator_names`
- `translation_span_distance`
- `fit_mode`
- `reference_fallback_used`
- `fallback_reason`
- `diagnostics`

`translation_span_distance` is populated only for `polynomial_translation_affine`.
For other parameterizations, it is `None`.
Fit and fallback fields are read from diagnostics when present and otherwise reported as `None`.

### VerificationReport Summary

`summarize_verification_report(...)` freezes these keys:

- `summary_schema_version`
- `summary_type = "verification_report"`
- `norm`
- `classification`
- `epsilon_values`
- `error_curve`
- `first_epsilon`
- `first_error`
- `max_error`
- `diagnostics`

`first_epsilon` and `first_error` are the first entries of the verification sweep.
`max_error` is computed from `error_curve`.

### Vertical Slice Summary

`summarize_vertical_slice(...)` freezes these keys:

- `summary_schema_version`
- `summary_type = "vertical_slice"`
- `derivative_backend`
- `derivative_keys`
- `derivative_config`
- `derivative_diagnostics`
- `residual`
- `generator`
- `verification`
- `extra_metrics`

The nested `residual`, `generator`, and `verification` values are produced by the corresponding summary helpers.
`extra_metrics` is optional and JSON-safe converted when provided.
It must not be used to smuggle manuscript-specific reporting logic into the runtime API.

Reporting helpers must not:

- redefine canonical object meaning
- make example outputs canonical artifacts
- encode manuscript-specific tables or figures
- hide backend-specific caveats
- broaden numerical scope

---

## Example Consistency

Heat and KdV examples should be made more consistent where that improves supportability.

Example outputs remain runtime smoke summaries.
They are not stable canonical artifact schemas.

Expected properties:

- JSON-serializable plain Python values
- deterministic for frozen example inputs
- compact enough for command-line smoke checks
- explicit about backend and verification classification

---

## API Stability Audit

M0 audits `docs/specs/API_STABILITY.md` only.
M1 freezes future public reporting APIs in planning docs only.

Audit result for M0:

- all public APIs through `v0.9` remain documented
- no `v0.10` public API has landed yet
- `API_STABILITY.md` should remain unchanged until reporting helpers or other public APIs actually land

M1 audit result:

- `pdelie.reporting` APIs are frozen for M2 but not implemented yet
- `API_STABILITY.md` remains unchanged in M1
- M2 must update `API_STABILITY.md` when `pdelie.reporting` lands

Future `v0.10` milestones must update `API_STABILITY.md` in the same milestone where any public API is added or changed.

---

## CI Cleanup Direction

`v0.10` should reduce release-gate CI sprawl without deleting useful historical tests.

Target direction:

- keep historical release-gate test modules runnable locally
- keep the current release gate visible in CI
- avoid redundant historical release-gate CI jobs unless intentionally retained
- keep full editable tests and package smoke as required release checks
- do not change test semantics just to make CI faster

Exact workflow edits are deferred until the CI cleanup milestone.

---

## Package and Publishing Readiness

`v0.10` should prepare the project for the `v1.0` publishing decision.

Required decision record:

- whether package-index publishing resumes at `v1.0`
- whether `v0.10` remains Git-tag-only
- what local build and wheel-smoke checks are required before any future publishable release
- what CI jobs are required before tagging

No PyPI or TestPyPI publication is added by this scope freeze.

---

## Scope Limits

Stable `v0.10` scope is limited to:

- supportability helpers around existing stable runtime surfaces
- existing canonical objects
- existing scalar 1D uniform rectilinear / periodic regimes
- existing Heat, Burgers, weak Heat/Burgers report, and KdV strong-path surfaces
- documentation and CI release-process cleanup

---

## Explicit Non-goals

Out of stable `v0.10` scope:

- no new PDE
- no weak KdV API
- no new weak derivative API
- no KdV weak residual report
- no broad benchmark adapters
- no PDEBench or The Well adapter work
- no multidimensional grids
- no multivariable systems
- no nonuniform-grid expansion
- no operator-method expansion
- no neural generators
- no manuscript-specific reporting logic
- no new canonical object unless M1 proves a repeated supportability problem cannot be solved with runtime helpers

---

## Milestones

Planned `v0.10` sequence:

- Milestone 0 - supportability scope reset
- Milestone 1 - reporting semantics freeze
- Milestone 2 - reporting helper implementation
- Milestone 3 - example consistency
- Milestone 4 - API stability audit and public-surface guards
- Milestone 5 - CI cleanup and release-gate consolidation
- Milestone 6 - release readiness and documentation alignment

`API_STABILITY.md` is updated only when public APIs land:

- M0 audits it but leaves it unchanged
- M1 freezes public reporting contracts in planning docs only
- M2 updates it when public reporting helpers land
- later milestones update it only if they add or change public APIs
