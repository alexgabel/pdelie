# Candidate Validation Workflow

This is a V0.29 recipe page over existing public APIs; it adds no runtime surface.

Use this path when you already have a generator, invariant map, or formula-backed candidate and want configured validation evidence.

```text
candidate object
-> schema and finite evaluation checks
-> optional finite-transform verification
-> generator confidence report
```

## Recipe

1. Normalize the candidate into a supported public form: `GeneratorFamily`, `InvariantMapSpec`, or `FormulaGeneratorFamily`.
2. Validate against a specific `FieldBatch` and residual evaluator.
3. Treat closure diagnostics, residual checks, and finite-transform verification as separate evidence surfaces.
4. Use `summarize_generator_confidence(...)` to combine evidence categorically.
5. Keep failed, fallback-backed, partial, and unconfigured evidence visible in the report.

## Primary APIs

- `pdelie.symmetry.validate_symmetry_candidate(...)`
- `pdelie.verification.verify_translation_generator(...)`
- `pdelie.reporting.summarize_generator_confidence(...)`
- `pdelie.reporting.summarize_generator_fit_diagnostics(...)`
- `pdelie.reporting.summarize_verification_report(...)`

## Defensible Claim

`validated` means all configured empirical checks passed for the supplied data, residual evaluator, candidate, epsilons, thresholds, and optional reference. It is not a mathematical proof of symmetry and does not imply validity outside the configured workflow.

## Next Step

Continue to `candidate_to_split_provenance.md` for a complete recipe that combines candidate validation, confidence interpretation, orbit provenance, and split-leakage diagnostics.
