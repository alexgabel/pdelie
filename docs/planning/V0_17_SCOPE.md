# V0.17 Scope - Formula-backed Generator Families

## Summary

`v0.17` is a narrow formula-backed generator interoperability release.

Stable path:

`canonical scalar 1D periodic FieldBatch + formula-backed generator candidate -> safe formula metadata/evaluation diagnostics -> empirical configured validation report`

This release adds formula-backed runtime records without changing existing polynomial `GeneratorFamily` semantics.

## Stable Scope

`v0.17` adds submodule-only runtime APIs:

- `pdelie.symmetry.FormulaGeneratorFamily`
- `pdelie.reporting.summarize_formula_generator_family(...)`
- `pdelie.symmetry.validate_symmetry_candidate(...)` support for formula-backed candidates

`FormulaGeneratorFamily` is runtime-only. It is not a new canonical object and does not change canonical `GeneratorFamily`.

## Formula Record

Frozen record properties:

- `schema_version = "0.1"`
- `parameterization = "formula_generator_family"`
- supported variables are exactly `t`, `x`, and `u`
- supported components are exactly `tau`, `xi`, and `phi`
- each generator row has a nonempty `name`
- each generator row must define all three components
- optional `finite_transform_spec` is a canonical `InvariantMapSpec` payload
- `diagnostics` are JSON-compatible provenance only

Formula records support `.to_dict()` and `.from_dict()` round trips.

## Safe Expression AST

Formula expressions use a small JSON AST. They are not Python code and are not parsed from arbitrary executable strings.

Supported nodes:

- `const`
- `var`
- `add`
- `mul`
- integer `pow`
- `sin`
- `cos`
- `reciprocal`
- metadata-only `symbolic_reference`

Rational expressions use `reciprocal` with a fixed denominator floor. Denominator-floor violations are empirical validation failures.

Symbolic references are metadata only. They may be summarized, but they are not evaluated.

## Candidate Validation

`validate_symmetry_candidate(...)` accepts:

- `FormulaGeneratorFamily` objects
- strict current `FormulaGeneratorFamily` payload mappings

Formula reports use:

- `summary_schema_version = "0.1"`
- `summary_type = "symmetry_candidate_validation"`
- `candidate_kind = "formula_generator_family"`

Validation behavior:

- malformed formula records raise typed validation errors
- well-formed formulas that evaluate to nonfinite values return `conclusion = "failed"`
- formulas with finite evaluable components but no finite transform are generally `partially_validated`
- symbolic-reference-only formulas are reporting/schema results and do not pretend to evaluate
- formulas with supported passing finite-transform checks may be `validated`
- `validated` remains empirical configured validation, not a mathematical proof of symmetry

## Reporting

`summarize_formula_generator_family(...)` returns a JSON-compatible runtime summary with:

- formula parameterization and schema version
- variables and component names
- generator count and names
- expression node kinds
- component root-node summaries
- finite-transform availability
- symbolic-reference metadata
- reciprocal denominator floor
- diagnostics

The helper does not mutate inputs and does not evaluate arbitrary code.

## Non-goals

`v0.17` does not add:

- Python callable generator APIs
- arbitrary executable formula-string parsing
- neural generator training
- learned-generator detector APIs
- formula-derived finite-flow integration for arbitrary infinitesimal formulas
- canonical `GeneratorFamily` schema changes
- new PDEs
- stable KS generator/residual/example APIs
- weak KS
- broad dataset adapters
- PDEBench or The Well support
- multidimensional, multivariable, or nonuniform-grid expansion
- train/test policy
- split management
- operator-facing APIs
- root `pdelie` exports

## Milestone Status

- Milestone 0: COMPLETE - scope freeze
- Milestone 1: COMPLETE - formula schema and validation semantics freeze
- Milestone 2: COMPLETE - formula record and reporting implementation
- Milestone 3: COMPLETE - formula candidate validation
- Milestone 4: COMPLETE - formula validation example
- Milestone 5: COMPLETE - API/public-surface audit
- Milestone 6: COMPLETE - release gate and readiness

## Release Gate Expectations

`v0.17` is complete only if:

- formula records round-trip through strict JSON-compatible payloads
- invalid formulas raise typed validation errors
- formula summaries are JSON-compatible and submodule-only
- formula candidates validate through `validate_symmetry_candidate(...)`
- finite formula diagnostics and denominator-floor failures are covered
- attached supported finite-transform specs reuse existing invariant-map validation
- existing `GeneratorFamily` and `InvariantMapSpec` candidate validation behavior remains unchanged
- formula validation example emits JSON only
- no callable, executable-string, neural-detector, KS, weak KS, broad-adapter, operator, split-policy, or root-export surface lands
- package/readiness docs preserve the `v1.0` package-index publishing deferral
