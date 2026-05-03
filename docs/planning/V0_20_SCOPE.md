# V0.20 Scope - Unified Generator Confidence Reports

## Summary

`v0.20` is a reporting/supportability release.

Stable path:

`residual / fit / verification / candidate-validation / orbit diagnostics -> JSON-compatible generator confidence report -> categorical evidence label and component statuses`

This release promotes the notebook confidence-card teaching pattern into one public runtime reporting helper.

## Stable Scope

`v0.20` adds submodule-only runtime APIs:

- `pdelie.reporting.summarize_generator_confidence(...)`
- `pdelie.examples.run_generator_confidence_report_example(...)`

No root `pdelie` export is added.

## Confidence Helper

Frozen signature:

```python
pdelie.reporting.summarize_generator_confidence(
    *,
    residual=None,
    generator=None,
    fit_diagnostics=None,
    verification=None,
    candidate_validation=None,
    coverage=None,
    consistency=None,
    orbit=None,
    thresholds=None,
    extra_metrics=None,
) -> dict[str, Any]
```

The helper accepts canonical `ResidualBatch`, `GeneratorFamily`, and `VerificationReport` objects where available, plus existing runtime report mappings for residual, fit, verification, candidate validation, coverage, consistency, and orbit evidence.

If `generator` is a `GeneratorFamily`, the helper nests both `summarize_generator_family(...)` and `summarize_generator_fit_diagnostics(...)` unless explicit `fit_diagnostics` is supplied.

## Report Semantics

Frozen output fields:

- `summary_schema_version = "0.1"`
- `summary_type = "generator_confidence"`
- `confidence_label`
- `component_statuses`
- nested evidence summaries
- `thresholds`
- `missing_evidence`
- `extra_metrics`

Frozen `confidence_label` values:

- `strong`
- `qualified`
- `failed`
- `insufficient_evidence`

Frozen component statuses:

- `passed`
- `warning`
- `failed`
- `not_configured`
- `unavailable`

No scalar confidence score ships in `v0.20`.

## Threshold Policy

Supported threshold keys:

- `residual_max_abs`
- `residual_rms`
- `verification_first_error`
- `verification_max_error`
- `coverage_fraction_min`

Residual and coverage checks are pass/fail only when corresponding thresholds are configured. Verification passes when classification is not `failed` unless configured error thresholds fail. Fit and candidate validation use existing evidence labels and conclusion labels.

## Non-goals

`v0.20` does not add:

- scalar confidence score
- benchmark success policy
- train/test split policy
- heldout-leakage policy
- transformed `FieldBatch` collections from reporting helpers
- canonical confidence object
- new PDEs
- KS runtime promotion
- weak-form expansion
- broad dataset adapters
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- root `pdelie` exports

## Milestone Status

- Milestone 0: COMPLETE - scope freeze
- Milestone 1: COMPLETE - semantics freeze
- Milestone 2: COMPLETE - reporting helper implementation
- Milestone 3: COMPLETE - example and notebook alignment
- Milestone 4: COMPLETE - cross-PDE confidence coverage
- Milestone 5: COMPLETE - API/public-surface audit
- Milestone 6: COMPLETE - release gate and readiness

## Release Gate Expectations

`v0.20` is complete only if:

- `summarize_generator_confidence(...)` is documented and importable from `pdelie.reporting`
- root `pdelie` remains unchanged
- reports are JSON-compatible
- direct-SVD, fallback, partial-validation, failed-candidate, residual-threshold-failure, and insufficient-evidence cases are covered
- example output is JSON only
- no new numerical scope, KS runtime API, weak-form expansion, broad adapter, train/test policy, scalar score, or operator-facing API lands
- package/readiness docs preserve the `v1.0` package-index publishing deferral
