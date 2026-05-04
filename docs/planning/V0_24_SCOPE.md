# V0.24 Scope - Weak-Form Supportability Reset

**Status:** COMPLETE

`v0.24` is a supportability/reporting release that resets the weak-form story without promoting a weak derivative backend or broad weak discovery method.

Stable path:

```text
existing Heat/Burgers weak residual reports
+ explicit weak contract summaries
+ strong residual / fit / verification evidence
+ noisy/coarse/imported parity diagnostics
+ internal identity-first Fisher-KPP feasibility
-> JSON-compatible weak-form supportability report
-> explicit supported / diagnostic / failed / insufficient-evidence conclusion
```

## Public Runtime APIs

`v0.24` adds submodule-only runtime APIs:

- `pdelie.reporting.summarize_weak_form_supportability(...)`
- `pdelie.examples.run_weak_form_supportability_example(...)`

No root `pdelie` exports are added.

## Frozen Report Semantics

Weak supportability reports return strict JSON-compatible runtime reports with:

- `summary_schema_version = "0.1"`
- `summary_type = "weak_form_supportability"`
- `supportability_label`
- `component_statuses`
- normalized weak report summaries
- normalized weak contract summaries
- quadrature rule
- optional strong residual summaries
- optional robustness/imported-parity summaries
- optional feasibility summaries
- local thresholds
- missing-evidence diagnostics
- policy metadata
- extra metrics

Frozen `supportability_label` values:

- `supported_existing_slice`
- `diagnostic_only`
- `failed`
- `insufficient_evidence`

`supported_existing_slice` means only the existing frozen public Heat/Burgers weak residual report surface. It does not imply a general weak-form derivative backend, weak residual evaluator integration, weak sparse discovery capability, weak KdV support, weak KS support, or public weak reaction-diffusion support.

## Weak Contract Schema

Weak contracts normalize these fields when available:

- `schema_version`
- `equation`
- `equation_form`
- `test_function_family`
- `test_function_order`
- `operator_order_supported`
- `integration_by_parts_depth`
- `boundary_vanishing_order`
- `patch_shape`
- `patch_stride`
- `quadrature_rule`
- `normalization`
- `valid_window_policy`
- `row_count`
- `skipped_patch_count`
- `finite_value_policy`

Malformed contract mappings and nonfinite values raise typed validation errors. Quadrature is recorded in every weak supportability report.

## Label Precedence

The label is deterministic:

1. Malformed or nonfinite input evidence raises typed validation errors unless the nested report already encodes a failure status.
2. Any explicitly configured component failure gives `failed`.
3. No weak evidence gives `insufficient_evidence`.
4. Only internal feasibility evidence gives `diagnostic_only`.
5. Public Heat/Burgers weak report evidence with configured checks passing gives `supported_existing_slice`.

## Thresholds

Supported local threshold keys:

- `weak_report_max_abs`
- `weak_report_rms`
- `weak_report_l2`
- `finite_required`
- `min_weak_rows`
- `max_skipped_fraction`
- `imported_parity_abs_tol`
- `imported_parity_rel_tol`
- `robustness_required_cases`

No scalar weak confidence score is added.

## Internal Fisher-KPP Feasibility

Fisher-KPP weak-form feasibility remains internal diagnostic evidence only.

The internal harness is identity-first:

- constant-field identity checks
- pure-time sign checks
- pure-space Fourier integration-by-parts checks
- manufactured smooth Fisher-KPP-like weak identity checks
- generated Fisher-KPP weak sanity checks
- quadrature/tolerance recording
- no-public-export guards

The public example includes only a static JSON-compatible Fisher-KPP feasibility marker. It does not import `tests/_helpers`.

## WSINDy Boundary

`v0.24` does not implement WSINDy, weak design matrices, weak sparse recovery, or a weak derivative backend. It only reports supportability of existing weak residual report slices and internal feasibility summaries.

## Non-goals

`v0.24` does not add:

- weak derivative backend
- `DerivativeBatch.backend = "weak"` promotion
- weak design matrices
- WSINDy implementation
- weak sparse recovery
- weak KdV
- weak KS
- public weak reaction-diffusion API
- weak residual evaluator subclasses
- new PDEs
- broad adapters
- multidimensional or nonuniform support
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- train/test policy
- root `pdelie` exports

## Milestone Status

- Milestone 0: COMPLETE - scope freeze
- Milestone 1: COMPLETE - semantics freeze
- Milestone 2: COMPLETE - reporting helper
- Milestone 3: COMPLETE - internal feasibility harness
- Milestone 4: COMPLETE - example and docs
- Milestone 5: COMPLETE - API/public-surface audit
- Milestone 6: COMPLETE - release gate and readiness

## Release Gate Expectations

`v0.24` is complete only if:

- Heat/Burgers weak reports can produce `supported_existing_slice`
- only internal feasibility evidence produces `diagnostic_only`
- configured weak metric failures produce `failed`
- missing weak evidence produces `insufficient_evidence`
- malformed contracts, invalid thresholds, and nonfinite metadata raise typed validation errors
- Fisher-KPP weak feasibility remains test-only and identity-first
- example output is JSON only
- new APIs are importable from their submodules only
- root `pdelie` remains unchanged
- no weak backend, WSINDy surface, weak KdV, weak KS, public weak reaction-diffusion API, new PDE, broad adapter, split policy, neural/callable API, operator API, or root export lands
