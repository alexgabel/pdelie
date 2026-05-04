# Changelog

## 0.24.0

First final release for the frozen V0.24 weak-form supportability reset.

- adds `pdelie.reporting.summarize_weak_form_supportability(...)` for JSON-compatible report-only supportability summaries over existing weak residual reports, weak contracts, strong residual evidence, robustness/imported-parity diagnostics, and internal feasibility summaries
- adds `python -m pdelie.examples.weak_form_supportability` and `pdelie.examples.run_weak_form_supportability_example(...)` as JSON-only runtime smoke examples
- freezes `summary_type == "weak_form_supportability"` with supportability labels `supported_existing_slice`, `diagnostic_only`, `failed`, and `insufficient_evidence`
- defines `supported_existing_slice` narrowly as the existing frozen public Heat/Burgers weak residual report surface, not a general weak backend or weak discovery claim
- normalizes weak contract metadata including equation, equation form, test-function family/order, supported operator order, integration-by-parts depth, boundary vanishing order, patch shape/stride, quadrature rule, normalization, valid-window policy, row count, skipped-patch count, and finite-value policy
- records quadrature in every weak supportability report and validates strict JSON compatibility with `allow_nan=False`
- adds test-only, identity-first Fisher-KPP weak feasibility diagnostics covering constant-field, pure-time, pure-space Fourier integration-by-parts, manufactured smooth-field, generated-field sanity, quadrature tolerance, and no-public-export guards
- keeps Fisher-KPP weak feasibility diagnostic-only and out of package runtime examples except for a static JSON-compatible marker
- documents the new helper in `API_STABILITY.md` as a submodule-only runtime API with no root export
- preserves existing split provenance, downstream discovery contracts, external-data readiness, confidence reports, Heat/Burgers strong paths, weak Heat/Burgers residual reports, normalized periodic KdV, Fisher-KPP reaction-diffusion strong path, advection-diffusion strong path, invariant/orbit diagnostics, orbit batches, candidate validation, and formula-backed generator support

Explicitly deferred for this final release:

- WSINDy
- weak design matrices
- weak sparse recovery
- public weak derivative backend or `DerivativeBatch.backend = "weak"` promotion
- weak KdV APIs
- weak KS APIs
- public weak reaction-diffusion APIs
- weak residual evaluator subclasses
- new PDE support
- KS runtime promotion
- broad adapters or file loaders
- multidimensional, multivariable, or nonuniform-grid support
- train/test policy or leakage prevention
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.23.0

First final release for the frozen V0.23 split/leakage provenance diagnostics slice.

- adds `pdelie.reporting.summarize_split_leakage_provenance(...)` for JSON-compatible report-only diagnostics over user-supplied partitions and available source/shift provenance
- extends `pdelie.reporting.summarize_downstream_discovery_workflow(...)` with optional `split_provenance`
- adds `python -m pdelie.examples.split_leakage_provenance` and `pdelie.examples.run_split_leakage_provenance_example(...)` as JSON-only runtime smoke examples
- freezes `summary_type == "split_leakage_provenance"` with risk labels `no_detected_overlap`, `traceable_overlap`, `missing_provenance`, and `inconclusive`
- validates non-empty partition labels, sample counts, orbit-batch provenance reports, source IDs, sample metadata, and strict JSON compatibility
- reports source overlap, same-source/same-shift overlap, identity-shift overlap, partition-pair diagnostics, component statuses, and risk reasons
- accepts existing `OrbitBatchResult` objects and `uniform_translation_orbit_batch` report mappings without returning transformed `FieldBatch` objects
- documents the new helper in `API_STABILITY.md` as a submodule-only runtime API with no root export
- preserves existing Heat/Burgers strong paths, weak residual reports, normalized periodic KdV, Fisher-KPP reaction-diffusion, advection-diffusion, external data readiness, confidence reports, downstream discovery contracts, invariant/orbit diagnostics, orbit batches, candidate validation, and formula-backed generator support

Explicitly deferred for this final release:

- split creation or train/test split management
- leakage prevention or benchmark policy
- downstream success criteria
- automatic augmentation policy
- file loaders
- `xarray.Dataset` support
- PDEBench or The Well adapters
- broad dataset adapter framework
- multidimensional, multivariable, or nonuniform-grid support
- new PDE support
- KS runtime promotion
- weak-form expansion
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.22.0

First final release for the frozen V0.22 downstream discovery contracts slice.

- adds `pdelie.discovery.summarize_discovery_bridge_output(...)` for JSON-compatible summaries over downstream bridge arrays
- adds `pdelie.discovery.summarize_discovery_result(...)` for compact backend-neutral discovery-result and recovery summaries
- adds `pdelie.reporting.summarize_downstream_discovery_workflow(...)` for composing readiness, confidence, orbit-batch, bridge, and discovery-result reports
- adds `python -m pdelie.examples.downstream_discovery_contracts` and `pdelie.examples.run_downstream_discovery_contracts_example(...)` as JSON-only runtime smoke examples
- freezes `summary_type == "discovery_bridge_output"`, `summary_type == "discovery_result"`, and `summary_type == "downstream_discovery_workflow"`
- validates finite 2D trajectory arrays, shared trajectory shapes, strictly increasing time values, unique feature names, and JSON-compatible provenance
- summarizes coefficient arrays by shape, finite status, norms, and nonzero counts without copying full coefficient matrices into reports
- supports optional feature-keyed recovery summaries through `evaluate_discovery_recovery(...)`
- reports orbit-batch source/shift provenance traceability without detecting leakage or managing splits
- documents the new helpers in `API_STABILITY.md` as submodule-only runtime APIs with no root exports
- preserves existing Heat/Burgers strong paths, weak residual reports, normalized periodic KdV, Fisher-KPP reaction-diffusion, advection-diffusion, confidence reports, external data readiness, invariant/orbit diagnostics, orbit batches, candidate validation, and formula-backed generator support

Explicitly deferred for this final release:

- split management or heldout-leakage detection
- downstream augmentation policy
- a general discovery-backend framework
- manuscript benchmark thresholds
- file loaders
- `xarray.Dataset` support
- PDEBench or The Well adapters
- broad dataset adapter framework
- multidimensional, multivariable, or nonuniform-grid support
- new PDE support
- KS runtime promotion
- weak-form expansion
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.21.0

First final release for the frozen V0.21 external data readiness report slice.

- adds `pdelie.reporting.summarize_field_batch_readiness(...)` for JSON-compatible readiness reports over canonical `FieldBatch` inputs
- adds `python -m pdelie.examples.external_data_readiness` and `pdelie.examples.run_external_data_readiness_example(...)` as JSON-only runtime smoke examples
- freezes `summary_type == "field_batch_readiness"` with readiness labels `ready`, `needs_attention`, and `not_ready`
- reuses component statuses `passed`, `warning`, `failed`, `not_configured`, and `unavailable`
- reports canonical dims/shape, finite values, mask state, time/x coordinate compatibility, metadata completeness, optional expected-equation matching, conservative metadata suggestions, and optional residual-evaluator preflight
- captures typed PDELie residual-preflight validation failures in the report while leaving unexpected exceptions visible
- demonstrates one ready `from_numpy(...)` Heat field, one metadata-incomplete field, and one residual-evaluator mismatch
- documents the new helper in `API_STABILITY.md` as a submodule-only runtime API with no root export
- preserves existing Heat/Burgers strong paths, weak residual reports, normalized periodic KdV, Fisher-KPP reaction-diffusion, advection-diffusion, confidence reporting, invariant/orbit diagnostics, orbit batches, candidate validation, and formula-backed generator support

Explicitly deferred for this final release:

- file loaders
- `xarray.Dataset` support
- PDEBench or The Well adapters
- broad dataset adapter framework
- multidimensional, multivariable, or nonuniform-grid support
- resampling APIs
- metadata mutation or PDE identity inference
- train/test split policy or heldout-leakage policy
- downstream discovery contracts
- new PDE support
- KS runtime promotion
- weak-form expansion
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.20.0

First final release for the frozen V0.20 unified generator confidence report slice.

- adds `pdelie.reporting.summarize_generator_confidence(...)` for JSON-compatible categorical confidence reports over residual, generator, fit-diagnostic, verification, candidate-validation, coverage, consistency, orbit, threshold, and extra-metric evidence
- adds `python -m pdelie.examples.generator_confidence_report` and `pdelie.examples.run_generator_confidence_report_example(...)` as JSON-only runtime smoke examples
- freezes `summary_type == "generator_confidence"` with categorical labels `strong`, `qualified`, `failed`, and `insufficient_evidence`
- freezes component statuses `passed`, `warning`, `failed`, `not_configured`, and `unavailable`
- supports caller-configured thresholds for residual max/RMS, verification first/max error, and coverage fraction
- demonstrates one strong direct-SVD Heat case and one qualified partial formula-candidate validation case
- documents the new helper in `API_STABILITY.md` as a submodule-only runtime API with no root export
- preserves existing Heat/Burgers strong paths, weak residual reports, normalized periodic KdV, Fisher-KPP reaction-diffusion, advection-diffusion, reporting helpers, invariant/orbit diagnostics, orbit batches, candidate validation, and formula-backed generator support

Explicitly deferred for this final release:

- scalar confidence scores
- benchmark success policy
- train/test split policy or heldout-leakage policy
- transformed `FieldBatch` collections from reporting helpers
- canonical confidence objects
- new PDE support
- KS runtime promotion
- weak-form expansion
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, or nonuniform-grid support
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.19.0

First final release for the frozen V0.19 constant-coefficient advection-diffusion strong path.

- adds `pdelie.data.generate_advection_diffusion_1d_field_batch(...)` for deterministic synthetic scalar 1D periodic constant-coefficient advection-diffusion fields
- adds `pdelie.residuals.AdvectionDiffusionResidualEvaluator` for the strong residual `u_t + c*u_x - nu*u_xx = 0`
- adds `python -m pdelie.examples.advection_diffusion_vertical_slice` and `pdelie.examples.run_advection_diffusion_vertical_slice_example(...)` as JSON-only runtime smoke examples
- freezes the equation tag `advection_diffusion_constant_coefficient` with `c` and `nu` metadata
- uses exact periodic Fourier evolution for the synthetic rollout
- verifies the frozen vertical slice with direct SVD translation evidence, no reference fallback, residual max around `5.51e-5`, residual RMS around `8.44e-6`, and exact held-out verification
- documents the new APIs in `API_STABILITY.md` as submodule-only runtime APIs with no root exports
- preserves prior Heat/Burgers strong paths, weak residual reports, normalized periodic KdV, Fisher-KPP reaction-diffusion, reporting helpers, invariant/orbit diagnostics, orbit batches, candidate validation, and formula-backed generator support

Explicitly deferred for this final release:

- variable-coefficient advection-diffusion
- reaction-advection-diffusion
- weak advection-diffusion
- public custom advection-diffusion initial-condition APIs
- KS runtime promotion
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, or nonuniform-grid support
- time-translation APIs
- neural or callable generator APIs
- operator-facing APIs
- train/test policy, split management, or heldout-leakage detection
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.18.0

First final release for the frozen V0.18 Fisher-KPP reaction-diffusion strong path.

- adds `pdelie.data.generate_reaction_diffusion_1d_field_batch(...)` for deterministic synthetic scalar 1D periodic Fisher-KPP fields
- adds `pdelie.residuals.ReactionDiffusionResidualEvaluator` for the strong residual `u_t - nu*u_xx - rho*u*(1-u) = 0`
- adds `python -m pdelie.examples.reaction_diffusion_vertical_slice` and `pdelie.examples.run_reaction_diffusion_vertical_slice_example(...)` as JSON-only runtime smoke examples
- freezes the equation tag `reaction_diffusion_fisher_kpp` with `nu` and `rho` metadata
- verifies the frozen vertical slice with direct SVD translation evidence, no reference fallback, residual max around `1.07e-5`, residual RMS around `1.22e-6`, and exact held-out verification
- documents the new APIs in `API_STABILITY.md` as submodule-only runtime APIs with no root exports
- preserves prior Heat/Burgers strong paths, weak residual reports, normalized periodic KdV, reporting helpers, invariant/orbit diagnostics, orbit batches, candidate validation, and formula-backed generator support

Explicitly deferred for this final release:

- advection-diffusion
- KS runtime promotion
- weak reaction-diffusion
- public custom initial-condition APIs
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, or nonuniform-grid support
- neural or callable generator APIs
- operator-facing APIs
- train/test policy, split management, or heldout-leakage detection
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.17.0

First final release for the frozen V0.17 formula-backed generator interoperability slice.

- adds `pdelie.symmetry.FormulaGeneratorFamily` as a runtime-only structured record for formula-backed scalar 1D Lie-point generator families
- adds `pdelie.reporting.summarize_formula_generator_family(...)` for JSON-compatible formula metadata summaries
- extends `pdelie.symmetry.validate_symmetry_candidate(...)` to accept `FormulaGeneratorFamily` objects and strict current formula payload mappings
- distinguishes formula candidates with `candidate_kind == "formula_generator_family"`
- freezes a safe JSON expression AST with `const`, `var`, `add`, `mul`, integer `pow`, `sin`, `cos`, `reciprocal`, and metadata-only `symbolic_reference`
- reports finite formula-evaluation diagnostics and denominator-floor failures without executing arbitrary strings or callables
- reuses existing invariant-map residual/inverse validation when a supported finite-transform spec is attached
- adds `python -m pdelie.examples.formula_generator_validation` and `pdelie.examples.run_formula_generator_validation_example(...)` as runtime smoke examples
- documents the new APIs in `API_STABILITY.md` as submodule-only runtime APIs with no root exports
- preserves existing polynomial `GeneratorFamily`, `GeneratorFamily`/`InvariantMapSpec` candidate validation, Heat/Burgers strong paths, weak residual reports, normalized periodic KdV, reporting helpers, orbit diagnostics, orbit batches, and external candidate validation

Explicitly deferred for this final release:

- Python callable generator APIs
- arbitrary executable formula-string parsing
- neural symmetry-detector training or learned-generator classes
- formula-derived finite-flow integration for arbitrary infinitesimal formulas
- canonical `GeneratorFamily` schema changes
- train/test policy, split management, or heldout-leakage detection
- time-translation APIs or `axis="time"` support
- new PDE support
- stable KS data generator, residual evaluator, vertical-slice example, imported parity, weak API, or root KS exports
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.16.0

First final release for the frozen V0.16 external symmetry-candidate validation slice.

- adds `pdelie.symmetry.validate_symmetry_candidate(...)` for JSON-compatible empirical validation reports over externally supplied symmetry candidates
- accepts `GeneratorFamily`, canonical `GeneratorFamily` payload mappings, `InvariantMapSpec`, and canonical `InvariantMapSpec` payload mappings
- distinguishes `candidate_kind == "generator_family"` from `candidate_kind == "invariant_map_spec"` in every report
- defines `validated` as configured empirical validation under the supplied field, residual evaluator, epsilons, and optional reference, not a mathematical proof of symmetry
- reuses existing finite-transform verification, span comparison, closure diagnostics, invariant application, and reporting helpers without changing their behavior
- adds `python -m pdelie.examples.symmetry_candidate_validation` and `pdelie.examples.run_symmetry_candidate_validation_example(...)` as runtime smoke examples
- documents the new helper in `API_STABILITY.md` as a submodule-only runtime API with no root export
- preserves the prior Heat/Burgers strong paths, `v0.8` weak residual report APIs, `v0.9` normalized periodic KdV strong path, `v0.10` reporting helpers, `v0.11` order-4 derivatives, `v0.12` fit diagnostics, `v0.13` orbit/coverage diagnostics, `v0.14` invariant workflow summaries, and `v0.15` orbit batch materialization

Explicitly deferred for this final release:

- callable transform descriptors and arbitrary external executable candidates
- neural symmetry-detector training or learned-generator classes
- formula-backed or non-polynomial generator families
- train/test policy, split management, or heldout-leakage detection
- time-translation APIs or `axis="time"` support
- new PDE support
- stable KS data generator, residual evaluator, vertical-slice example, imported parity, weak API, or root KS exports
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.15.0

First final release for the frozen V0.15 materialized uniform translation orbit batch slice.

- adds `pdelie.invariants.build_uniform_translation_orbit_batch(...)` for materializing finite uniform `x`-translation orbit batches from canonical scalar 1D periodic `FieldBatch` inputs
- adds `pdelie.invariants.OrbitBatchResult` as a runtime-only structured result containing the materialized `FieldBatch` and a JSON-compatible provenance report
- preserves raw shift order and duplicate shifts, appends along the batch dimension in shift-major order, and records optional source/shift indices
- records aggregate orbit-materialization metadata and one aggregate preprocess-log entry on the output field
- adds `python -m pdelie.examples.translation_orbit_batch` and `pdelie.examples.run_translation_orbit_batch_example(...)` as runtime smoke examples for Heat and KdV orbit batches
- documents the new helper in `API_STABILITY.md` as a submodule-only runtime API with no root exports
- tightens public-surface guards so train/test policy, split management, time translation, KS APIs, weak KS, broad adapters, and root runtime exports remain absent
- updates CI to the compact current `v0_15-release-gate` while preserving full editable tests and package smoke
- preserves the prior Heat/Burgers strong paths, `v0.8` weak residual report APIs, `v0.9` normalized periodic KdV strong path, `v0.10` reporting helpers, `v0.11` order-4 derivatives, `v0.12` fit diagnostics, `v0.13` orbit/coverage diagnostics, and `v0.14` invariant workflow summaries

Explicitly deferred for this final release:

- train/test policy, split management, or heldout-leakage detection
- sparse-discovery branch policy or private-paper augmentation recipes
- time-translation APIs or `axis="time"` support
- new PDE support
- stable KS data generator, residual evaluator, vertical-slice example, imported parity, weak API, or root KS exports
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.14.0

First final release for the frozen V0.14 invariant workflow summary and read-only translation orbit report slice.

- adds `pdelie.reporting.summarize_invariant_workflow(...)` for JSON-compatible runtime summaries that combine coverage, consistency, orbit, generator, fit-diagnostic, verification, and extra-metric reports
- adds `pdelie.invariants.summarize_uniform_translation_orbit(...)` for read-only uniform `x`-translation orbit reports over canonical scalar 1D periodic `FieldBatch` inputs
- adds `python -m pdelie.examples.invariant_workflow_summary` and `pdelie.examples.run_invariant_workflow_summary_example(...)` as runtime smoke examples combining Heat, KdV, coverage, orbit, fit, and verification summaries
- documents the new helpers in `API_STABILITY.md` as submodule-only runtime APIs with no root exports
- tightens public-surface guards so augmentation, orbit datasets, time translation, KS APIs, weak KS, broad adapters, and root runtime exports remain absent
- updates CI to the compact current `v0_14-release-gate` while preserving full editable tests and package smoke
- preserves the prior Heat/Burgers strong paths, `v0.8` weak residual report APIs, `v0.9` normalized periodic KdV strong path, `v0.10` reporting helpers, `v0.11` order-4 derivatives, `v0.12` fit diagnostics, and `v0.13` orbit/coverage diagnostics

Explicitly deferred for this final release:

- augmented datasets or orbit dataset builders
- transformed `FieldBatch` collections from reporting helpers
- time-translation APIs or `axis="time"` support
- new PDE support
- stable KS data generator, residual evaluator, vertical-slice example, imported parity, weak API, or root KS exports
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- private-paper experiment policy, tables, figures, thresholds, or branch logic
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.13.0

First final release for the frozen V0.13 public orbit and coverage diagnostics slice.

- adds `pdelie.invariants.compute_periodic_window_coverage(...)` for JSON-compatible grid-point periodic-window coverage diagnostics under the frozen field-shift-then-fixed-window convention
- adds `pdelie.invariants.diagnose_uniform_translation_consistency(...)` for JSON-compatible uniform-translation consistency diagnostics over canonical scalar 1D periodic `FieldBatch` inputs
- adds `python -m pdelie.examples.orbit_coverage_diagnostics` and `pdelie.examples.run_orbit_coverage_diagnostics_example(...)` as runtime smoke examples for the diagnostics
- documents the diagnostics in `API_STABILITY.md` as submodule-only runtime APIs with no root exports
- tightens public-surface guards so augmentation, orbit-view builders, KS APIs, weak KS, broad adapters, and root runtime exports remain absent
- updates CI to the compact current `v0_13-release-gate` while preserving full editable tests and package smoke
- preserves the prior Heat/Burgers strong paths, `v0.8` weak residual report APIs, `v0.9` normalized periodic KdV strong path, `v0.10` reporting helpers, `v0.11` order-4 derivatives, and `v0.12` fit diagnostics

Explicitly deferred for this final release:

- new PDE support
- stable KS data generator, residual evaluator, vertical-slice example, imported parity, weak API, or root KS exports
- public augmentation utilities
- public orbit-view builders
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- private-paper experiment policy, tables, figures, thresholds, or branch logic
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.12.0

First final release for the frozen V0.12 diagnostics and supportability hardening slice.

- adds `pdelie.reporting.summarize_generator_fit_diagnostics(...)` for JSON-compatible summaries of generator-fit diagnostics, singular values, condition number, selected/SVD span distances, fallback status, and evidence labels
- enriches `fit_translation_generator(...)` diagnostics without changing coefficient selection or fitting behavior
- adds internal KS diagnostic sweep evidence showing residuals and verification remain healthy while direct residual-based SVD fitting remains fallback-backed across frozen epsilons and cheap fixture variants
- adds internal orbit/coverage feasibility diagnostics over stable Heat and KdV fixtures, including periodic-window coverage and uniform-translation consistency checks
- tightens API stability and public-surface guards so KS, orbit/coverage, augmentation, weak KS, broad adapter, and root runtime exports remain absent
- updates CI to the compact current `v0_12-release-gate` while preserving full editable tests and package smoke
- preserves the prior Heat/Burgers strong paths, `v0.8` weak residual report APIs, `v0.9` normalized periodic KdV strong path, `v0.10` reporting helpers, and `v0.11` order-4 derivative API

Explicitly deferred for this final release:

- new PDE support
- stable KS data generator, residual evaluator, vertical-slice example, imported parity, weak API, or root KS exports
- public orbit/coverage helpers
- public augmentation utilities
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- manuscript-specific experiment logic, tables, figures, or thresholds
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.11.0

First final release for the frozen V0.11 Kuramoto-Sivashinsky feasibility/no-go closeout.

- extends `pdelie.derivatives.compute_spectral_fd_derivatives(...)` with `max_spatial_order=4` and stable `u_xxxx` output while preserving the `max_spatial_order=2` default behavior
- adds internal KS feasibility coverage for the normalized strong form `u_t + u*u_x + u_xx + u_xxxx = 0`
- records strong internal KS residual, mass-conservation, and held-out canonical translation-verification evidence
- closes stable KS runtime promotion as no-go/defer for `v0.11` because the frozen fixture relies on `reference_fallback` rather than direct SVD in-tolerance fitting
- adds compact `v0_11-release-gate` CI visibility while preserving the full editable test suite and package smoke
- preserves the prior Heat/Burgers strong paths, `v0.8` weak residual report APIs, `v0.9` normalized periodic KdV strong path, and `v0.10` reporting helpers

Explicitly deferred for this final release:

- stable KS data generator
- stable KS residual evaluator
- KS vertical-slice example
- KS imported parity
- weak KS APIs
- root `pdelie` exports for KS runtime APIs
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- manuscript-specific experiment logic, tables, figures, or thresholds
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.10.0

First final release for the frozen V0.10 supportability and `v1.0` readiness slice.

- adds public runtime supportability helpers under `pdelie.reporting` for JSON-compatible summaries of residual batches, weak residual reports, generator families, verification reports, and vertical slices
- refactors Heat and KdV vertical-slice examples to emit the shared nested `vertical_slice` summary shape while keeping their command entrypoints unchanged
- adds focused API stability audit coverage and public-surface guards for stable submodule APIs, root-export boundaries, and explicitly deferred surfaces
- consolidates CI release-gate visibility to a single current `v0_10-release-gate` job while keeping historical release-gate tests runnable locally and covered by full editable tests
- preserves the prior Heat/Burgers strong paths, `v0.8` weak residual report APIs, `v0.9` normalized periodic KdV strong path, structured ingestion, and symmetry/discovery utilities

Explicitly deferred for this final release:

- new PDE support
- weak KdV APIs
- weak derivative APIs or broader weak-form expansion
- broad dataset adapters such as PDEBench or The Well
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- manuscript-specific reporting logic, tables, figures, or thresholds
- new canonical reporting objects
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.9.0

First final release for the frozen V0.9 normalized periodic KdV strong path.

- extends `pdelie.derivatives.compute_spectral_fd_derivatives(...)` with `max_spatial_order=3` and stable `u_xxx` output while preserving the `max_spatial_order=2` default behavior
- adds `pdelie.data.generate_kdv_1d_field_batch(...)` for normalized periodic short-horizon synthetic KdV under the frozen v0.9 generator regime
- adds `pdelie.residuals.KdVResidualEvaluator` for the normalized strong-form residual `u_t + 6*u*u_x + u_xxx = 0`
- adds `python -m pdelie.examples.kdv_vertical_slice` and `pdelie.examples.run_kdv_vertical_slice_example(...)` as runtime smoke examples for the stable KdV path
- adds compact `v0_9-release-gate` CI visibility and representative KdV imported-parity checks
- preserves the prior `v0.8` weak residual report APIs and structured-ingestion / symmetry-discovery utility surface

Explicitly deferred for this final release:

- weak KdV APIs
- weak derivative APIs or broader weak-form expansion
- root `pdelie` exports for KdV runtime APIs
- custom KdV initial conditions or configurable KdV coefficients
- general KdV stability guarantees outside the frozen short-horizon release fixtures
- multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- PyPI and TestPyPI publication; package-index publishing is deferred to `v1.0` or later

## 0.8.0

First final release for the frozen V0.8 weak residual report core.

- adds `pdelie.residuals.evaluate_weak_heat_residual(...)` for deterministic window-indexed weak residual reports over canonical scalar 1D uniform periodic Heat `FieldBatch` data
- adds `pdelie.residuals.evaluate_weak_burgers_residual(...)` for deterministic window-indexed weak residual reports over canonical scalar 1D uniform periodic Burgers `FieldBatch` data
- adds a compact `v0_8-release-gate` CI visibility job and representative release-gate pytest module
- adds a frozen representative robustness layer for clean/noisy/coarse Heat/Burgers comparisons against the current spectral/analytic path
- preserves the prior `v0.7` structured-ingestion and symmetry/discovery runtime surface while adding the narrow `v0.8` weak residual report APIs

Explicitly deferred for this final release:

- weak derivatives
- weak `ResidualBatch` / `ResidualEvaluator` integration
- stable KdV promotion
- multidimensional, multivariable, or nonuniform-grid weak paths
- broader PDE, grid, or adapter expansion
- paper-specific experiment logic

## 0.7.0

First final release for the frozen V0.7 structured external-data ingestion core.

- adds `pdelie.data.from_numpy(...)` for strict runtime conversion of explicit NumPy/array-like 1D uniform rectilinear trajectory data into canonical `FieldBatch`
- adds `pdelie.data.from_xarray(...)` for strict runtime conversion of explicit `xarray.DataArray` 1D uniform rectilinear trajectory data into canonical `FieldBatch`
- adds native-vs-imported parity coverage across the current derivative, residual, symmetry-fit, verification, and discovery-bridge layers
- adds a compact `v0_7-release-gate` CI visibility job and representative release-gate pytest module
- preserves the frozen Heat/Burgers symmetry and discovery-utility surface from `v0.6` while extending the library to structured external ingestion

Explicitly deferred for this final release:

- `xarray.Dataset` support
- dim aliases
- static-field ingestion
- multidimensional external-data ingestion
- nonuniform-grid support
- metadata inference
- PDEBench-specific loaders
- The Well adapters
- HDF5, netCDF, or Zarr stable loaders
- weak-form methods
- operator methods
- stable KdV promotion
- paper-specific experiment logic

## 0.6.0

First final release for the frozen V0.6 symmetry-guided PDE discovery utilities core.

- adds runtime-only discovery recovery metrics under `pdelie.discovery.evaluate_discovery_recovery(...)`
- adds a thin runtime-only PySINDy backend-fit adapter under `pdelie.discovery.fit_pysindy_discovery(...)`
- adds runtime-only heuristic translation-canonical discovery inputs under `pdelie.discovery.build_translation_canonical_discovery_inputs(...)`
- adds deterministic robustness helpers under `pdelie.data` plus grouped recovery-grid summaries under `pdelie.discovery`
- adds a compact `v0_6-release-gate` CI visibility job and representative release-gate pytest module
- finalizes the frozen `v0.6` Heat/Burgers discovery-utility surface without promoting KdV

Explicitly deferred for this final release:

- stable KdV API or stable KdV runtime module
- external structured dataset ingestion
- weak-form methods
- operator methods
- broad discovery adapters or backend frameworks
- paper-specific experiment logic, figures, or manuscript tables

## 0.5.0

First final release for the frozen V0.5 portability and external-compatibility core.

- functionally identical to `0.5.0rc1` unless a release blocker required a minimal fix
- finalizes the `0.5.0rc1` release surface for the V0.5 portability slice

## 0.5.0rc1

First release candidate for the frozen V0.5 generator-family portability and external-compatibility core.

- stable manifest export/import helpers added under `pdelie.portability`
- strict external-family normalization added under `pdelie.portability.coerce_generator_family(...)`
- compact portability benchmark / semantic-preservation layer added for canonical, manifest, and narrow legacy translation inputs
- compact V0.5 release-gate layer and `v0_5-release-gate` CI visibility job added
- normalized periodic KdV feasibility passes in the tests-first slice, but KdV remains non-stable in `v0.5`
- package metadata, milestone docs, and release-readiness docs aligned with the implemented V0.5 state

Explicitly deferred for this release candidate:

- stable KdV API or stable KdV runtime module
- weak-form methods
- operator methods
- broad dataset adapters or interoperability expansion
- prediction-facing utility work
- new canonical stable objects beyond the current V0.5 slice

## 0.4.0

First final release for the frozen V0.4 stable core.

- finalizes the frozen V0.4 generator-family, algebra-diagnostics, and optional-visualization release surface

## 0.4.0rc1

First release candidate for the frozen V0.4 generator-family and algebra-diagnostics core.

- canonical `GeneratorFamily` family semantics finalized with `schema_version = "0.2"`, family-shaped coefficients, and explicit `basis_spec`
- runtime-only symbolic generator rendering added under `pdelie.symmetry`
- optional runtime-only SymPy component expressions added under `pdelie.symmetry`
- runtime-only span diagnostics added under `pdelie.symmetry`
- runtime-only closure / structure-constant diagnostics added under `pdelie.symmetry`
- optional Matplotlib visualization layer added under `pdelie.viz`
- explicit V0.4 release-gate pytest module and `v0_4-release-gate` CI visibility job added
- package metadata, README, milestone docs, and release-readiness docs aligned with the implemented V0.4 state

Explicitly deferred for this release candidate:

- weak-form methods
- operator methods
- broad adapters or interoperability expansion
- stable multi-generator PDE fitting
- broader downstream compatibility or prediction-facing workflows
- new canonical stable objects beyond the current V0.4 slice

## 0.3.0

First final release for the frozen V0.3 stable core.

- functionally identical to `0.3.0rc1` unless a release blocker required a minimal fix
- finalizes the `0.3.0rc1` release surface for the invariant/downstream utility slice

## 0.3.0rc1

First release candidate for the frozen V0.3 invariant/downstream utility core.

- stable canonical pipeline extended with `InvariantMapSpec`
- runtime-only `pdelie.invariants.InvariantApplier` added for the frozen single-generator periodic `x` uniform-translation path
- runtime-only `pdelie.discovery.to_pysindy_trajectories` added as the narrow backend-specific PySINDy bridge
- controlled four-branch downstream benchmark / release-gate layer added internally under frozen settings:
  `vanilla`, `known_invariant`, `discovered_invariant`, `nuisance`
- release metadata, package description, README, and release-readiness docs aligned with the implemented V0.3 state

Explicitly deferred for this release candidate:

- weak-form methods
- operator methods
- multi-generator invariant machinery
- broad adapters or interoperability expansion
- new canonical objects beyond the current V0.3 slice

## 0.2.0

First final release for the frozen V0.2 stable core.

- scientifically/functionally identical to `0.2.0rc1`
- final release metadata and release-readiness docs updated for `0.2.0`

## 0.2.0rc1

First release candidate for the frozen V0.2 stable core.

- extends the stable core from Heat-only to matched Heat and Burgers coverage
- stable pipeline remains:
  `FieldBatch -> DerivativeBatch -> ResidualBatch -> GeneratorFamily -> VerificationReport`
- synthetic 1D Burgers added as the second stable PDE under the existing contracts
- current translation fitting and finite-transform verification paths hardened across Heat and Burgers
- matched cross-PDE benchmark / release-gate layer added in the test surface under shared defaults and shared low-noise held-out conditions
- release metadata, packaging text, and user-facing docs aligned with the implemented V0.2 state

Explicitly deferred for this release candidate:

- invariant pipelines as a stable feature
- weak-form methods
- operator methods
- broad adapters or interoperability expansion
- new canonical objects beyond the current stable slice

## 0.1.0

First final release for the frozen V0.1 MVP slice.

- scientifically identical to `0.1.0rc1`
- final release metadata and release-readiness docs updated for `0.1.0`

## 0.1.0rc1

First release candidate for the frozen V0.1 MVP slice.

- stable V0.1 canonical objects implemented:
  `FieldBatch`, `DerivativeBatch`, `ResidualBatch`, `ResidualEvaluator`,
  `GeneratorFamily`, `VerificationReport`
- synthetic 1D heat-equation vertical slice implemented on a uniform periodic grid
- stable derivative backend `spectral_fd` implemented
- analytic heat residual evaluator implemented
- polynomial spatial-translation baseline implemented
- finite-transform verification path implemented
- README, packaged example module, editable-install path, and built-wheel smoke path aligned for release validation

Explicitly deferred for this release candidate:

- Burgers or any second PDE
- operator methods
- weak-form features
- broad adapters or interoperability expansion
- new canonical objects beyond the current V0.1 slice
