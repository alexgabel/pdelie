# V0.16 Scope - External Symmetry-Candidate Validation

## Summary

`v0.16` is the external symmetry-candidate validation release.

Stable path:

`canonical scalar 1D periodic FieldBatch + external candidate payload + residual evaluator -> empirical configured validation report`

The release adds one public submodule-only validation helper:

```python
pdelie.symmetry.validate_symmetry_candidate(...)
```

The name is intentional. The helper accepts both generator-family candidates and invariant-map candidates, and reports the distinction through `candidate_kind`.

## Motivation

The post-`v0.15` direction is interoperability, not more numerical scope.
External detector methods should be able to export a candidate and use PDELie as a validation/reporting substrate.

The release also carries forward a `v0.15` guardrail:

- materialized orbit batches construct orbit-expanded data
- they do not decide train/heldout policy or leakage safety
- serious workflows should keep source and shift indices enabled so materialized samples remain auditable

## Stable Scope

In scope:

- `GeneratorFamily` candidate objects
- canonical `GeneratorFamily` payload mappings
- `InvariantMapSpec` candidate objects
- canonical `InvariantMapSpec` payload mappings
- strict JSON-compatible validation reports
- finite-transform verification for single-row translation-compatible `GeneratorFamily` candidates
- span comparison when `reference_generator` is supplied
- closure diagnostics for multi-generator `GeneratorFamily` candidates
- residual and inverse consistency diagnostics for global `uniform_translation` `InvariantMapSpec` candidates
- Heat, Burgers, and KdV stable fixtures as representative validation paths

## Public API

Frozen API:

```python
pdelie.symmetry.validate_symmetry_candidate(
    field,
    candidate,
    *,
    residual_evaluator,
    reference_generator=None,
    finite_transform_epsilons=None,
    source_candidate_id=None,
) -> dict[str, Any]
```

The helper is public under `pdelie.symmetry` only.
There is no root `pdelie` export.

## Report Semantics

Every report includes:

- `summary_schema_version = "0.1"`
- `summary_type = "symmetry_candidate_validation"`
- `candidate_kind = "generator_family"` for generator-family candidates
- `candidate_kind = "invariant_map_spec"` for invariant-map candidates
- `source_candidate_id`
- `empirical_interpretation = "configured_validation_not_mathematical_proof"`
- configured validation checks
- check reports
- thresholds
- conclusion

Conclusion labels:

- `validated`: every configured empirical check passed under the supplied field, residual evaluator, epsilons, and optional reference
- `partially_validated`: schema is valid and at least one configured check passed, but at least one optional configured check is unavailable or non-passing
- `failed`: a required empirical check ran and failed

`validated` is not a mathematical proof of symmetry.
It is an empirical configured validation result.

## Thresholds

Frozen thresholds:

- generator finite-transform check passes when `verify_translation_generator(...)` returns `classification != "failed"`
- default `finite_transform_epsilons` uses existing `DEFAULT_EPSILON_VALUES`
- invariant-map residual stability passes when `absolute_delta <= 1e-8 or relative_delta <= 1e-6`
- invariant-map inverse consistency passes when relative L2 error `<= 1e-8`
- reference span comparison passes when max principal angle and projection residual summary are `<= 1e-8`
- closure diagnostics pass when closure, antisymmetry, and Jacobi summaries are `<= 1e-8`

## Failure Behavior

Typed validation errors are raised for:

- malformed inputs
- unsupported scope
- invalid or ambiguous payload mappings
- callable descriptors
- nonfinite or non-increasing epsilons
- invalid references
- wrong residual evaluator types

Well-formed candidates that fail empirical checks return a report with `conclusion = "failed"`.

## Non-goals

`v0.16` does not add:

- callable transform descriptors
- arbitrary external executable candidate objects
- neural symmetry-detector training
- learned-generator classes
- formula-backed or non-polynomial generator families
- new PDE support
- stable KS runtime support
- weak KS
- broad adapters
- PDEBench or The Well support
- multidimensional, multivariable, or nonuniform-grid expansion
- operator-facing APIs
- train/test policy, split management, or leakage detection
- root runtime exports

## Milestones

- M0: scope freeze
- M1: API semantics freeze
- M2: `GeneratorFamily` candidate validation
- M3: `InvariantMapSpec` candidate validation
- M4: example
- M5: API/public-surface audit
- M6: release gate and readiness

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

## Release-gate Expectations

The compact `v0_16-release-gate` must verify:

- package metadata is `0.16.0`
- `validate_symmetry_candidate(...)` is documented and importable from `pdelie.symmetry`
- root `pdelie` does not export the helper
- representative generator-family and invariant-map candidates validate
- a wrong-span generator returns `conclusion = "failed"` rather than raising
- callable descriptors, formula-backed generators, neural detectors, KS runtime APIs, weak KS, broad adapters, split policy, operator APIs, and root exports remain absent
