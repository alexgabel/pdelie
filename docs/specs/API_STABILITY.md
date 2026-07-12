# API Stability Policy

For a compact user-facing map of stable PDE surfaces, workflows, and selected runtime helpers, see `docs/specs/SUPPORT_MATRIX.md`.

## Stable API (v0.x)

- FieldBatch
- DerivativeBatch
- `DerivativeBatch.backend="spectral_fd"`
- ResidualBatch
- ResidualEvaluator
- GeneratorFamily (polynomial only; canonical `v0.4` family semantics with explicit `basis_spec`)
- InvariantMapSpec (single-generator only)
- VerificationReport
- basic verification tools
- typed validation errors (`PDELieValidationError`, `SchemaValidationError`, `ShapeValidationError`, `ScopeValidationError`)

Stable `GeneratorFamily` note:

- canonical `v0.4` output uses `schema_version = "0.2"` and family-shaped 2D coefficients
- direct construction is canonical-only and requires explicit `basis_spec`
- legacy `0.1` single-generator translation payloads are a narrow `from_dict()` compatibility path only

Stable public import path for the invariant canonical object:

- `pdelie.InvariantMapSpec`

Runtime public API for the frozen `v0.3` Milestone 1 slice:

- `pdelie.invariants.InvariantApplier` for single-generator periodic `x` uniform translation only

Runtime public API for the frozen `v0.3` Milestone 2 slice:

- `pdelie.discovery.to_pysindy_trajectories` for a backend-specific, narrow, flattened-trajectory PySINDy bridge

Runtime public API for the frozen `v0.4` Milestone 2 slice:

- `pdelie.symmetry.render_generator_family` for deterministic runtime-only symbolic display of the stored generator basis
- `pdelie.symmetry.to_sympy_component_expressions` for optional runtime-only SymPy component expressions when `sympy` is installed

Runtime public API for the frozen `v0.4` Milestone 3 slice:

- `pdelie.symmetry.compare_generator_spans` for runtime-only algebraic span comparison of canonical polynomial `GeneratorFamily` objects under the frozen normalized polynomial inner product

Runtime public API for the frozen `v0.4` Milestone 4 slice:

- `pdelie.symmetry.diagnose_generator_family_closure` for runtime-only closure, structure-constant, and algebra-diagnostic reports on canonical polynomial `GeneratorFamily` objects

Runtime public API for the frozen `v0.4` Milestone 5 slice:

- `pdelie.viz.plot_generator_coefficients` for optional Matplotlib coefficient-bar figures over canonical `GeneratorFamily` objects
- `pdelie.viz.plot_generator_symbolic_summary` for optional Matplotlib text-summary figures over runtime symbolic rendering output
- `pdelie.viz.plot_verification_curve` for optional Matplotlib verification-curve figures over `VerificationReport`
- `pdelie.viz.plot_span_diagnostics` for optional Matplotlib figures over frozen M3 span-diagnostic reports
- `pdelie.viz.plot_closure_diagnostics` for optional Matplotlib figures over frozen M4 closure-diagnostic reports

Runtime public API for the frozen `v0.5` Milestone 1 slice:

- `pdelie.portability.export_generator_family_manifest` for dict-level export of a stable manifest artifact schema around canonical `GeneratorFamily` payloads
- `pdelie.portability.import_generator_family_manifest` for dict-level validation/import of the frozen manifest schema back into canonical `GeneratorFamily`

Runtime public API for the frozen `v0.5` Milestone 2 slice:

- `pdelie.portability.coerce_generator_family` for strict normalization of canonical in-memory families, canonical family payloads, manifests, and the narrow legacy translation payload into canonical `GeneratorFamily`

Runtime public API for the frozen `v0.6` Milestone 1 slice:

- `pdelie.discovery.evaluate_discovery_recovery` for runtime-only support and coefficient recovery metrics over caller-supplied canonical term strings

Runtime public API for the frozen `v0.6` Milestone 2 slice:

- `pdelie.discovery.fit_pysindy_discovery` for a runtime-only, backend-native PySINDy fit adapter over the current flattened `to_pysindy_trajectories(...)` bridge
- this M2 API returns a runtime backend report dict, not a stable JSON-compatible artifact schema
- its `coefficients` field is runtime NumPy data, and its `equation_terms` / `equation_strings` fields are backend-native, non-canonical debug outputs

Runtime public API for the frozen `v0.6` Milestone 3 slice:

- `pdelie.discovery.build_translation_canonical_discovery_inputs` for a runtime-only, heuristic translation-canonical discovery-input helper over canonical Heat/Burgers `FieldBatch` data
- this M3 API returns a runtime dict containing a transformed `FieldBatch`, the narrow `to_pysindy_trajectories(...)` bridge output, and deterministic alignment metadata
- its canonicalization policy is heuristic peak alignment, not a strong invariant-theoretic guarantee

Runtime public API for the frozen `v0.6` Milestone 4 slice:

- `pdelie.data.add_gaussian_noise` for deterministic additive Gaussian perturbation of canonical `FieldBatch` data while preserving `FieldBatch` validity and preprocess provenance
- `pdelie.data.subsample_time` for stride-only time-axis subsampling of canonical `FieldBatch` data
- `pdelie.data.subsample_x` for stride-only x-axis subsampling of canonical `FieldBatch` data under the stable minimum-two-x-points rule
- `pdelie.data.split_batch_train_heldout` for deterministic batch-axis train/held-out splitting of canonical `FieldBatch` data
- `pdelie.discovery.summarize_recovery_grid` for runtime-only grouped aggregation of nested recovery-grid records
- the M4 summarizer is runtime convenience only, not a canonical artifact schema, JSON contract, or manuscript-table format

Runtime public API for the frozen `v0.7` Milestone 1 slice:

- `pdelie.data.from_numpy` for strict runtime conversion of explicit NumPy/array-like 1D uniform rectilinear trajectory data into canonical `FieldBatch`
- this M1 API is core-only, not file-based, not alias-based, and not a broad external-loader framework

Runtime public API for the frozen `v0.7` Milestone 2 slice:

- `pdelie.data.from_xarray` for strict runtime conversion of explicit `xarray.DataArray` 1D uniform rectilinear trajectory data into canonical `FieldBatch`
- this M2 API is runtime-optional, DataArray-only, not Dataset-based, and not a broad external-loader framework

Runtime public API for the frozen `v0.8` Milestone 2 slice:

- `pdelie.residuals.evaluate_weak_heat_residual` for deterministic window-indexed weak residual reports over canonical scalar 1D uniform periodic Heat `FieldBatch` data
- `pdelie.residuals.evaluate_weak_burgers_residual` for deterministic window-indexed weak residual reports over canonical scalar 1D uniform periodic Burgers `FieldBatch` data
- these M2 APIs return runtime report dicts, not canonical `ResidualBatch` objects
- their stable report shape and diagnostics surface are frozen by `docs/planning/V0_8_SCOPE.md`

Runtime public API update for the frozen `v0.9` Milestone 1 slice:

- `pdelie.derivatives.compute_spectral_fd_derivatives(field, *, max_spatial_order=2)` preserves the current default `spectral_fd` behavior and derivative outputs
- `max_spatial_order=3` adds the third spatial derivative output `u_xxx`
- `max_spatial_order=1` emits only the time derivative and first spatial derivative outputs
- unsupported `max_spatial_order` values raise `ScopeValidationError`

Runtime public API update for the frozen `v0.11` Milestone 2 slice:

- `pdelie.derivatives.compute_spectral_fd_derivatives(field, *, max_spatial_order=4)` adds the fourth spatial derivative output `u_xxxx`
- `max_spatial_order=4` emits `u_t`, `u_x`, `u_xx`, `u_xxx`, and `u_xxxx`
- this API update preserves the existing default `max_spatial_order=2` behavior, config, diagnostics, and derivative outputs
- this derivative extension does not add a stable public Kuramoto-Sivashinsky data generator or residual evaluator

Runtime public API for the frozen `v0.9` Milestone 2 slice:

- `pdelie.data.generate_kdv_1d_field_batch` for normalized periodic short-horizon synthetic KdV under the frozen `v0.9` generator regime
- this API has no root `pdelie` export
- this API does not accept custom initial conditions in `v0.9`
- accepted generator parameters outside the release-guaranteed regime are user-risk

Runtime public API for the frozen `v0.9` Milestone 3 slice:

- `pdelie.residuals.KdVResidualEvaluator` for normalized periodic short-horizon KdV strong-form residuals under the frozen `v0.9` regime
- this evaluator computes the formula-defined residual `u_t + 6*u*u_x + u_xxx = 0` using numerical derivatives
- when derivatives are omitted, the evaluator computes `compute_spectral_fd_derivatives(field, max_spatial_order=3)`
- when derivatives are supplied, they must validate against the field and include `u_t`, `u_x`, and `u_xxx`
- stable inputs must include `field.metadata["parameter_tags"]["equation"] == "kdv_normalized"`
- this API has no root `pdelie` export
- this API does not expose configurable KdV coefficients or weak KdV behavior in `v0.9`

Runtime public API for the frozen `v0.10` Milestone 2 slice:

- `pdelie.reporting.summarize_residual_batch` for JSON-compatible runtime summaries of `ResidualBatch` residual shape, definition type, normalization, residual norms, and diagnostics
- `pdelie.reporting.summarize_weak_residual_report` for JSON-compatible runtime summaries of frozen `v0.8` weak residual report mappings
- `pdelie.reporting.summarize_generator_family` for JSON-compatible runtime summaries of `GeneratorFamily` coefficients, parameterization, normalization, translation span distance when applicable, and fitting diagnostics
- `pdelie.reporting.summarize_verification_report` for JSON-compatible runtime summaries of `VerificationReport` epsilon sweeps, classification, first-error metrics, and diagnostics
- `pdelie.reporting.summarize_vertical_slice` for JSON-compatible runtime summaries that combine derivative metadata plus residual, generator, verification, and optional extra metrics summaries
- these APIs are runtime supportability helpers, not canonical objects, artifact schemas, manuscript-table generators, or figure/rendering APIs
- these APIs have no root `pdelie` exports

Runtime public API for the frozen `v0.12` Milestone 2 slice:

- `pdelie.reporting.summarize_generator_fit_diagnostics` for JSON-compatible runtime summaries of `GeneratorFamily` fit diagnostics, including singular values, condition number, selected/SVD span distances, fallback status, and evidence labels
- this API summarizes existing `GeneratorFamily` diagnostics and coefficients; it does not create a canonical object or mutate the generator
- this API is a runtime supportability helper, not a manuscript table, fitting algorithm, promotion gate, or stable KS runtime surface
- this API has no root `pdelie` export

Runtime public API for the frozen `v0.13` Milestone 2/M3 slice:

- `pdelie.invariants.compute_periodic_window_coverage` for JSON-compatible grid-point coverage diagnostics over 1D uniform endpoint-excluded periodic grids, half-open periodic windows, and uniform translation shifts
- `pdelie.invariants.diagnose_uniform_translation_consistency` for JSON-compatible diagnostics of single-generator uniform periodic translation consistency over canonical scalar 1D periodic `FieldBatch` inputs
- these APIs support invariant and finite-transform workflows by reporting coverage and consistency only
- these APIs do not construct augmented datasets, orbit views, training branches, canonical artifacts, figures, or manuscript tables
- these APIs have no root `pdelie` exports

Runtime public API for the frozen `v0.14` Milestone 2/M3 slice:

- `pdelie.reporting.summarize_invariant_workflow` for JSON-compatible runtime summaries that combine coverage, consistency, orbit, generator, fit-diagnostic, verification, and optional extra-metric reports
- `pdelie.invariants.summarize_uniform_translation_orbit` for JSON-compatible read-only reports over finite uniform `x` translations of canonical scalar 1D periodic `FieldBatch` inputs
- these APIs support invariant and finite-transform workflows by reporting combined workflow and orbit metadata only
- these APIs do not construct augmented datasets, orbit datasets, or transformed `FieldBatch` collections
- `source_field_id` is optional JSON-compatible provenance metadata only, not a canonical identity system
- time-translation diagnostics remain deferred; `InvariantApplier` still exposes only uniform periodic `x` translation in the stable runtime path
- these APIs have no root `pdelie` exports

Runtime public API for the frozen `v0.15` Milestone 2 slice:

- `pdelie.invariants.build_uniform_translation_orbit_batch` for materializing finite uniform `x`-translation orbit batches from canonical scalar 1D periodic `FieldBatch` inputs
- `pdelie.invariants.OrbitBatchResult` as a runtime-only structured result containing the materialized `FieldBatch` and a JSON-compatible provenance report
- the materialized output appends along the batch dimension, preserves raw shift order and duplicate shifts, and records optional source/shift indices in the report
- the helper reuses `InvariantApplier` uniform translation and does not introduce a second translation implementation
- the helper records orbit-materialization metadata and appends one aggregate preprocess-log entry
- this API is a conservative data utility, not a train/test splitter, split-management helper, leakage detector, sparse-discovery branch policy, canonical object, figure/rendering API, or manuscript artifact schema
- time-translation, public KS runtime APIs, weak KS, broad adapters, and operator-facing APIs remain deferred
- these APIs have no root `pdelie` exports

Runtime public API for the frozen `v0.16` Milestone 2/M3 slice:

- `pdelie.symmetry.validate_symmetry_candidate` for empirical configured validation reports over externally supplied symmetry candidates
- accepted candidate inputs are `GeneratorFamily`, canonical `GeneratorFamily` payload mappings, `InvariantMapSpec`, and canonical `InvariantMapSpec` payload mappings
- reports distinguish `candidate_kind = "generator_family"` from `candidate_kind = "invariant_map_spec"`
- `validated` means all configured empirical checks passed for the supplied field, residual evaluator, epsilons, and optional reference; it is not a mathematical proof of symmetry
- callable descriptors, learned detector training, formula-backed generator families, public KS runtime APIs, weak KS, broad adapters, split policy, and operator-facing APIs remain deferred
- this API returns a JSON-compatible runtime report, not a canonical object, detector, fitting algorithm, manuscript artifact, or training framework
- this API has no root `pdelie` export

Runtime public API for the frozen `v0.17` Milestone 2/M3 slice:

- `pdelie.symmetry.FormulaGeneratorFamily` as a runtime-only structured record for formula-backed scalar 1D Lie-point generator families
- `pdelie.reporting.summarize_formula_generator_family` for JSON-compatible runtime summaries of formula-backed generator records
- `pdelie.symmetry.validate_symmetry_candidate` now also accepts `FormulaGeneratorFamily` objects and strict current `FormulaGeneratorFamily` payload mappings
- formula candidate validation reports distinguish `candidate_kind = "formula_generator_family"`
- formula expressions use a safe JSON AST with supported nodes `const`, `var`, `add`, `mul`, integer `pow`, `sin`, `cos`, `reciprocal`, and metadata-only `symbolic_reference`
- formula-backed validation performs schema checks, finite formula-evaluation diagnostics when expressions are evaluable, and optional finite-transform validation when a supported `InvariantMapSpec` payload is attached
- `FormulaGeneratorFamily` is runtime-only and does not change canonical polynomial `GeneratorFamily` semantics
- arbitrary executable formula strings, Python callables, learned-generator training, neural detector APIs, public KS runtime APIs, weak KS, broad adapters, split policy, and operator-facing APIs remain deferred
- these APIs have no root `pdelie` exports

Runtime public API for the frozen `v0.18` Milestone 2/M3/M4 slice:

- `pdelie.data.generate_reaction_diffusion_1d_field_batch` for deterministic synthetic scalar 1D periodic Fisher-KPP reaction-diffusion fields under the frozen `v0.18` generator regime
- stable generated fields use `field.metadata["parameter_tags"]["equation"] == "reaction_diffusion_fisher_kpp"` and include the frozen `nu` / `rho` parameter tags
- this generator has no public custom initial-condition API in `v0.18`; it emits smooth bounded Fourier-mode initial conditions inside the frozen synthetic regime
- `pdelie.residuals.ReactionDiffusionResidualEvaluator` for Fisher-KPP strong-form residuals `u_t - nu*u_xx - rho*u*(1-u) = 0`
- when derivatives are omitted, the evaluator computes the existing default `compute_spectral_fd_derivatives(field)` order-2 derivative path
- when derivatives are supplied, they must validate against the field and include `u_t` and `u_xx`
- stable inputs must be canonical scalar 1D uniform periodic finite unmasked `FieldBatch` objects with the frozen reaction-diffusion equation tag
- `pdelie.examples.run_reaction_diffusion_vertical_slice_example` for a compact JSON-only runtime smoke example that emits the existing nested `summarize_vertical_slice(...)` summary shape
- the stable public claim covers the frozen scalar 1D periodic synthetic Fisher-KPP path with direct SVD translation-fit evidence; it does not add advection-diffusion, KS promotion, weak reaction-diffusion, custom initial-condition APIs, broad adapters, multidimensional or nonuniform support, split policy, neural/callable generators, or operator-facing APIs
- these APIs have no root `pdelie` exports

Runtime public API for the frozen `v0.19` Milestone 2/M3/M4 slice:

- `pdelie.data.generate_advection_diffusion_1d_field_batch` for deterministic synthetic scalar 1D periodic constant-coefficient advection-diffusion fields under the frozen `v0.19` generator regime
- stable generated fields use `field.metadata["parameter_tags"]["equation"] == "advection_diffusion_constant_coefficient"` and include the frozen `c` / `nu` parameter tags
- this generator has no public custom initial-condition API in `v0.19`; it emits zero-mean smooth Fourier-mode initial perturbations inside the frozen synthetic regime
- generated fields use exact periodic Fourier evolution for `u_t + c*u_x = nu*u_xx`
- `pdelie.residuals.AdvectionDiffusionResidualEvaluator` for strong-form residuals `u_t + c*u_x - nu*u_xx = 0`
- when derivatives are omitted, the evaluator computes the existing default `compute_spectral_fd_derivatives(field)` order-2 derivative path
- when derivatives are supplied, they must validate against the field and include `u_t`, `u_x`, and `u_xx`
- stable inputs must be canonical scalar 1D uniform periodic finite unmasked `FieldBatch` objects with the frozen advection-diffusion equation tag
- `pdelie.examples.run_advection_diffusion_vertical_slice_example` for a compact JSON-only runtime smoke example that emits the existing nested `summarize_vertical_slice(...)` summary shape
- the stable public claim covers the frozen scalar 1D periodic synthetic constant-coefficient advection-diffusion path with direct SVD translation-fit evidence; it does not add variable-coefficient advection-diffusion, reaction-advection-diffusion, weak advection-diffusion, custom initial-condition APIs, public KS runtime APIs, broad adapters, multidimensional or nonuniform support, time translation, split policy, neural/callable generators, or operator-facing APIs
- these APIs have no root `pdelie` exports

Runtime public API for the frozen `v0.20` Milestone 2/M3 slice:

- `pdelie.reporting.summarize_generator_confidence` for JSON-compatible runtime confidence reports that combine residual, generator, fit-diagnostic, verification, candidate-validation, coverage, consistency, orbit, threshold, and extra-metric evidence
- reports use `summary_type = "generator_confidence"` and `summary_schema_version = "0.1"`
- confidence reports expose categorical `confidence_label` values: `strong`, `qualified`, `failed`, and `insufficient_evidence`
- component statuses are `passed`, `warning`, `failed`, `not_configured`, or `unavailable`
- confidence is empirical configured evidence, not a mathematical proof, benchmark policy, train/test policy, or scalar confidence score
- the helper accepts canonical `ResidualBatch`, `GeneratorFamily`, and `VerificationReport` objects where available, plus existing runtime summary mappings for the supported evidence sections
- `pdelie.examples.run_generator_confidence_report_example` for a compact JSON-only runtime smoke example demonstrating one strong direct-SVD case and one qualified partial-validation case
- this API does not return transformed `FieldBatch` collections, augmented datasets, canonical artifacts, manuscript tables, downstream success policies, scalar scores, train/test split decisions, or heldout-leakage decisions
- this API does not add new PDEs, public KS runtime APIs, weak-form expansion, broad adapters, time translation, split policy, neural/callable generators, or operator-facing APIs
- these APIs have no root `pdelie` exports

Runtime public API for the frozen `v0.21` Milestone 2/M4 slice:

- `pdelie.reporting.summarize_field_batch_readiness` for JSON-compatible runtime readiness reports over canonical `FieldBatch` inputs before downstream residual, confidence, and discovery workflows
- reports use `summary_type = "field_batch_readiness"` and `summary_schema_version = "0.1"`
- readiness reports expose categorical `readiness_label` values: `ready`, `needs_attention`, and `not_ready`
- component statuses reuse the reporting vocabulary `passed`, `warning`, `failed`, `not_configured`, and `unavailable`
- the helper reports canonical shape/dim compatibility, finite-value diagnostics, mask diagnostics, uniform coordinate diagnostics, metadata completeness, optional expected-equation checks, conservative metadata suggestions, and optional residual-evaluator preflight
- residual preflight captures typed `PDELieValidationError` failures in the report and propagates unexpected non-PDELie exceptions
- `pdelie.examples.run_external_data_readiness_example` for a compact JSON-only runtime smoke example demonstrating a ready `from_numpy` field, incomplete metadata, and residual-evaluator mismatch
- this API is a runtime supportability report, not a canonical object, file loader, `xarray.Dataset` adapter, broad dataset adapter, resampling helper, metadata mutation helper, PDE identity inference engine, train/test policy, or leakage detector
- this API does not add new PDEs, public KS runtime APIs, weak-form expansion, broad adapters, multidimensional or nonuniform stable support, time translation, split policy, neural/callable generators, or operator-facing APIs
- these APIs have no root `pdelie` exports

Runtime public API for the frozen `v0.22` Milestone 2/M3/M4 slice:

- `pdelie.discovery.summarize_discovery_bridge_output` for JSON-compatible runtime summaries over downstream bridge arrays
- bridge summaries use `summary_type = "discovery_bridge_output"` and `summary_schema_version = "0.1"`
- bridge summaries validate finite 2D trajectories, shared trajectory shape, strictly increasing time, unique feature names, and JSON-compatible source/provenance metadata
- `pdelie.discovery.summarize_discovery_result` for JSON-compatible runtime summaries over backend-neutral or `fit_pysindy_discovery(...)`-style discovery-result mappings
- discovery-result summaries use `summary_type = "discovery_result"` and compact coefficient summaries by shape, finite status, norms, and nonzero count; they do not copy full coefficient matrices into the report
- optional `target_terms` must be feature-keyed and recovery summaries reuse `evaluate_discovery_recovery(...)` for exact, partial, and failed per-feature recovery diagnostics
- backend failure mappings are summarized as reports instead of raising, while malformed mappings and nonfinite coefficients raise typed validation errors
- `pdelie.reporting.summarize_downstream_discovery_workflow` for JSON-compatible workflow reports that combine field-readiness, generator-confidence, orbit-batch, bridge, and discovery-result reports
- downstream workflow reports use `summary_type = "downstream_discovery_workflow"` and report orbit-batch provenance traceability without detecting leakage or managing splits
- `pdelie.examples.run_downstream_discovery_contracts_example` for a compact JSON-only runtime smoke example
- these APIs are runtime supportability reports, not canonical objects, backend plugin frameworks, split policies, leakage detectors, manuscript benchmark summaries, file loaders, or transformed `FieldBatch` collections
- this API does not add new PDEs, public KS runtime APIs, weak-form expansion, broad adapters, `xarray.Dataset` support, multidimensional or nonuniform stable support, time translation, neural/callable generators, or operator-facing APIs
- these APIs have no root `pdelie` exports

Runtime public API for the frozen `v0.23` Milestone 2/M4 slice:

- `pdelie.reporting.summarize_split_leakage_provenance` for JSON-compatible runtime reports over user-supplied partition labels and available source/shift provenance
- split provenance reports use `summary_type = "split_leakage_provenance"` and `summary_schema_version = "0.1"`
- reports expose `risk_label` values: `no_detected_overlap`, `traceable_overlap`, `missing_provenance`, and `inconclusive`
- accepted partition labels are user-supplied non-empty strings; PDELie does not create, optimize, or enforce train/heldout splits
- when supplied, `OrbitBatchResult` or `uniform_translation_orbit_batch` reports are inspected through existing `source_batch_indices`, `shift_indices`, and shift metadata
- optional `source_ids`, `sample_metadata`, `source_report_id`, and `extra_metrics` must remain strict JSON-compatible runtime metadata
- diagnostics report source overlap, source-and-shift overlap, identity-shift overlap, partition-pair counts, component statuses, and risk reasons
- `pdelie.reporting.summarize_downstream_discovery_workflow` now accepts optional `split_provenance` reports and nests them as downstream workflow evidence
- `pdelie.examples.run_split_leakage_provenance_example` for a compact JSON-only runtime smoke example
- these APIs are runtime provenance diagnostics, not split managers, leakage preventers, benchmark-policy engines, automatic augmentation policies, or manuscript success criteria
- this API does not add file loaders, Dataset adapters, broad backend frameworks, new PDEs, public KS runtime APIs, weak-form expansion, multidimensional or nonuniform stable support, time translation, neural/callable generators, operator-facing APIs, or root exports
- these APIs have no root `pdelie` exports

Runtime public API for the frozen `v0.24` Milestone 2/M4 slice:

- `pdelie.reporting.summarize_weak_form_supportability` for JSON-compatible runtime reports over existing weak residual reports, explicit weak contracts, strong residual summaries, robustness/imported-parity diagnostics, and internal feasibility summaries
- weak supportability reports use `summary_type = "weak_form_supportability"` and `summary_schema_version = "0.1"`
- reports expose `supportability_label` values: `supported_existing_slice`, `diagnostic_only`, `failed`, and `insufficient_evidence`
- `supported_existing_slice` is intentionally narrow: it means the configured evidence supports only the frozen public Heat/Burgers weak residual report surface, not a general weak derivative backend, weak residual evaluator integration, weak design matrix, or weak sparse-discovery method
- weak contracts normalize report metadata such as test-function family/order, supported operator order, integration-by-parts depth, boundary vanishing order, patch shape/stride, quadrature rule, normalization, valid-window policy, row counts, skipped-patch counts, finite-value policy, equation, and equation form
- quadrature is recorded in every weak supportability report
- malformed/nonfinite evidence raises typed validation errors unless a nested report already encodes a failure status
- internal Fisher-KPP weak feasibility remains diagnostic-only test evidence; no public weak reaction-diffusion API is added
- `pdelie.examples.run_weak_form_supportability_example` for a compact JSON-only runtime smoke example demonstrating Heat/Burgers weak supportability plus a static internal Fisher-KPP feasibility marker
- `v0.24` does not implement WSINDy, weak design matrices, weak sparse recovery, a weak derivative backend, weak KdV, weak KS, public weak reaction-diffusion residual evaluators, new PDEs, broad adapters, split policy, neural/callable generators, operator-facing APIs, or root exports
- these APIs have no root `pdelie` exports

Runtime public API for the frozen `v0.25` Milestone 5 slice:

- `pdelie.examples.run_kdv_scope_decision_example` for a compact JSON-only runtime smoke example documenting the KdV scope decision
- KdV scope-decision examples use `summary_type = "kdv_scope_decision_example"` and `summary_schema_version = "0.1"`
- report evidence categories are `current_frozen_supported`, `diagnostic_only`, and `deferred_no_go`
- the existing normalized scalar 1D periodic short-horizon KdV strong path remains stable and direct-SVD-backed under the frozen public regime
- the recorded `v0.25` decision is `keep_public_kdv_surface_frozen`
- custom KdV initial conditions, configurable KdV coefficients, general KdV support outside the frozen normalized short-horizon regime, and weak KdV remain deferred
- `v0.25` adds no new KdV generator, residual evaluator, weak residual report, custom initial-condition API, configurable-coefficient API, weak derivative backend, WSINDy-like surface, broad adapter, time-translation API, neural/callable generator API, operator-facing API, or root export
- these APIs have no root `pdelie` exports

Decision-only note for the frozen `v0.26` KS revisit decision:

- `v0.26` adds no new public runtime API
- `v0.26` records the KS revisit decision `current_no_go_reference_fallback`
- internal KS residual and verification evidence remains feasible, but translation fitting remains reference-fallback-backed and therefore not promotable
- decision labels include `current_no_go_reference_fallback`, `residual_feasible_fit_not_promotable`, `direct_strong_candidate_for_v0_26b_promotion`, and `deferred_no_go`
- `v0.26b` is reserved as the follow-up KS promotion release name if a separate scope freeze accepts future direct-SVD/no-fallback evidence
- this decision does not add a stable public Kuramoto-Sivashinsky data generator or residual evaluator
- this decision does not add a public KS vertical-slice example, public KS status example, residual-only KS public API, weak KS API, custom KS initial-condition API, configurable KS coefficient API, broad KS regime support, root KS export, broad adapter, time-translation API, neural/callable generator API, or operator-facing API

Runtime public API and behavior updates for the frozen `v0.27` multi-generator diagnostics decision:

- `pdelie.examples.run_multi_generator_diagnostics_example` for a compact JSON-only runtime diagnostic example over supplied multi-row `GeneratorFamily` objects
- multi-generator diagnostic examples use `summary_type = "multi_generator_diagnostics_example"` and `summary_schema_version = "0.1"`
- `pdelie.symmetry.diagnose_generator_family_closure` now reports well-formed rank-deficient families as diagnostic reports with `family_rank_status = "rank_deficient"` instead of raising solely because structure constants are non-unique
- `pdelie.symmetry.compare_generator_spans` now reports well-formed zero-rank/rank-deficient span comparisons with `comparison_status = "failed"` or `"warning"` instead of crashing solely because rank is deficient
- `pdelie.symmetry.validate_symmetry_candidate` now accepts `closure_required=True|False` for `GeneratorFamily` candidates
- multi-row `GeneratorFamily` validation keeps algebraic closure diagnostics separate from PDE-context evidence; closure passing alone does not prove PDE residual symmetry
- the recorded `v0.27` decision is `multi_generator_diagnostics_feasible_fitting_deferred`
- this release does not add public multi-generator PDE fitting, finite multi-generator flows, BCH composition, exponential-map integration, invariant charts, multi-parameter orbit charts, group-action atlases, operator APIs, neural/callable generator APIs, or root exports
- these APIs have no root `pdelie` exports

Runtime public API for the frozen `v0.28` data-ecosystem feasibility slice:

- `pdelie.data.from_xarray_dataset` for strict runtime conversion of one explicit scalar `xarray.Dataset` data variable into canonical scalar 1D uniform periodic `FieldBatch`
- `pdelie.reporting.summarize_xarray_dataset_readiness` for strict JSON-compatible runtime readiness reports over `xarray.Dataset` inputs before conversion
- Dataset readiness reports use `summary_type = "xarray_dataset_readiness"` and `summary_schema_version = "0.1"`
- `pdelie.examples.run_data_ecosystem_feasibility_example` for a compact JSON-only runtime smoke example demonstrating Dataset readiness, Dataset-to-FieldBatch conversion, and existing FieldBatch readiness
- the recorded `v0.28` decision is `xarray_dataset_scalar_slice_supported_file_loaders_deferred`
- Dataset conversion delegates to the existing `from_xarray(...)` DataArray path after data-variable and optional mask-variable selection; all frozen scalar 1D periodic layout, coordinate, metadata, mask, and singleton-var rules remain in force
- metadata remains explicit for conversion; Dataset attrs are report metadata only and are never silently promoted into canonical `FieldBatch.metadata`
- this release does not add file loaders, NetCDF/Zarr readers, PDEBench/The Well adapters, broad adapter registries, implicit metadata inference, resampling APIs, multidimensional or nonuniform stable support, multivariable `FieldBatch` support, train/test policy, neural/callable generators, operator-facing APIs, or root exports
- these APIs have no root `pdelie` exports

Decision-only note for the frozen `v0.29` workflow recipes and support matrix release:

- `v0.29` adds no new runtime public API
- `v0.29` records the release decision `workflow_recipes_and_support_matrix_complete_no_new_numerical_scope`
- `docs/workflows/` provides public documentation recipes for data readiness, candidate validation, downstream/export provenance, Dataset-to-downstream, and candidate-to-split-provenance paths
- `docs/specs/support_matrix.v0_29.json` is a machine-readable docs/spec artifact, not a package runtime API
- `docs/specs/SUPPORT_MATRIX.md` is the human-readable support matrix and selected helper inventory
- `v0.29` adds rendered tutorial notebooks for the two complete workflow recipes
- this decision does not add `pdelie.reporting.summarize_workflow_readiness(...)`, new PDEs, file loaders, broad adapters, multidimensional or nonuniform stable support, public KS runtime APIs, train/test policy, neural/callable generators, operator-facing APIs, or root exports

Decision-only note for the frozen `v0.30a` scope-freeze sub-release:

- `v0.30a` adds no new runtime public API
- `v0.30a` records the design decision `nonperiodic_readiness_and_low_order_finite_difference_diagnostics_design_only`
- `v0.30a` does not change any existing public surface, does not bump `pyproject.toml`, does not change CI, and does not declare any new optional dependency
- `v0.30a` freezes the design of structured `BoundaryConditionSpec`, the `finite_difference` derivative backend, the `compute_derivatives(backend="auto")` dispatcher, and the residual interior-vs-full-grid domain policy; the documents are at `docs/planning/V0_30_SCOPE.md`, `docs/design/BOUNDARY_CONDITION_SPEC.md`, `docs/design/DERIVATIVE_BACKEND_POLICY.md`, and `docs/design/V0_30_HYGIENE_AUDIT.md`
- the runtime implementation lands in `v0.30` proper, not in `v0.30a`
- the `v0.30` release will bump `FieldBatch.SCHEMA_VERSION` from `"0.1"` to `"0.2"` to carry the structured `BoundaryConditionSpec`; `FieldBatch.from_dict` will accept both `"0.1"` and `"0.2"` payloads under a backwards-compatible loader so external tooling can prepare
- `v0.30` will add `pdelie.derivatives.compute_finite_difference_derivatives` and `pdelie.derivatives.compute_derivatives` under their submodules; neither becomes a root `pdelie` export
- `v0.30a` does not add a `SymmetryMethod` registry, a `pdelie.discover_symmetries` root API, any external symmetry-method port, any file loader, any PDEBench or The Well adapter, any KS runtime API, any weak nonperiodic surface, or any new PDE generator/evaluator
- `v0.30a` records that `u_xxx` and `u_xxxx` on nonperiodic data remain deferred from the stable `v0.30` surface
- `v0.30a` records that finite-transform verification for nonperiodic translations is deferred to the `v0.31.5` orbit/action scope decision

Decision-only note for the frozen `v0.30e` hygiene phase 1 sub-release:

- `v0.30e` adds no new runtime public API and no new root `pdelie` export
- `v0.30e` records the design decision `hygiene_phase_1_non_blocking_ruff_mypy_coverage`
- `v0.30e` does not bump `pyproject.toml` (stays at `0.29.0`); the version bump is reserved for the v0.30 release close
- `v0.30e` configures `[tool.ruff]` (target-version `py311`, line-length 120, extend-select `["E", "W", "F", "B", "I", "UP", "RUF", "NPY"]`), `[tool.mypy]` (strict scope narrowed to `pdelie.contracts`, `pdelie._boundary`, `pdelie.derivatives.*`; lenient elsewhere with `ignore_missing_imports` on optional-extras stubs), and `[tool.coverage.*]` (`source = ["src/pdelie"]`, `branch = true`, `fail_under = 80`) in `pyproject.toml`
- `ruff`, `mypy`, `pytest-cov` are added to the `[project.optional-dependencies].test` group (not to any runtime extra)
- three new CI jobs (`lint`, `typecheck`, `coverage`) run on Python 3.11 and are non-blocking (`continue-on-error: true`); a red run reports findings but does not gate merges
- `v0.30e` does not lift the `numpy<2` cap and does not expand the Python matrix; both are Phase 3 items reserved for v0.32 or later
- `v0.30e` does not add a symmetry-method registry, any external symmetry-method port, any file loader, any PDEBench / The Well adapter, any KS runtime API, any weak nonperiodic surface, any new PDE, or a v0.30f release-gate consolidation

Decision-only note for the frozen `v0.30d` residual-evaluator auto-dispatch sub-release:

- `v0.30d` adds no new runtime public API and no new root `pdelie` export
- `v0.30d` records the design decision `strong_residual_evaluator_auto_dispatch_and_interior_only_diagnostics`
- `HeatResidualEvaluator`, `BurgersResidualEvaluator`, `AdvectionDiffusionResidualEvaluator`, and `ReactionDiffusionResidualEvaluator` now route through `compute_derivatives(backend="auto")` when derivatives are omitted; supplied derivatives take precedence and are used as-is
- their diagnostics gain `residual_domain_policy` (`"full_grid"` on periodic data via `spectral_fd`; `"interior_only"` on supported nonperiodic BCs via `finite_difference`), `rms_residual` (Heat and Burgers previously omitted this), `boundary_trim_width` (interior-only paths), and a nested `full_grid_diagnostic` block (interior-only paths)
- `KdVResidualEvaluator`, `evaluate_weak_heat_residual`, `evaluate_weak_burgers_residual`, and the translation finite-transform verifier remain periodic-only per the v0.30 scope
- `v0.30d` does not add ruff / mypy / coverage configuration, a symmetry-method registry, any external symmetry-method port, any file loader, any PDEBench or The Well adapter, any KS runtime API, any weak nonperiodic surface, or any new PDE
- `v0.30d` does not bump `pyproject.toml`; the version bump is reserved for the v0.30 release close

Decision-only note for the frozen `v0.30b` BoundaryConditionSpec runtime and FieldBatch 0.2 migration sub-release:

- `v0.30b` adds no new runtime public API and no new root `pdelie` export
- `v0.30b` records the design decision `boundary_condition_spec_runtime_and_field_batch_0_2_migration`
- `v0.30b` does not bump the package version (`pyproject.toml` stays at `0.29.0`); the version bump lands at v0.30 release close
- `v0.30b` bumps `FieldBatch.SCHEMA_VERSION` from `"0.1"` to `"0.2"`; `FieldBatch.from_dict` accepts both `"0.1"` and `"0.2"` payloads under a backwards-compatible loader
- legacy `metadata["boundary_conditions"]["x"]` string values (`"periodic"`, `"dirichlet"`, `"neumann"`, `"open"`, `"open_unknown"`) are normalized to the structured `BoundaryConditionSpec` form on load and recorded in `preprocess_log` under operation `"schema_0_1_to_0_2_boundary_normalization"`
- the helpers live in the internal `src/pdelie/_boundary.py` module; they are not promoted as a public submodule API
- `from_numpy` and `from_xarray` accept structured nonperiodic specs and the supported legacy nonperiodic strings; unsupported strings raise `ScopeValidationError`
- downstream consumers (`spectral_fd`, `HeatResidualEvaluator`, `BurgersResidualEvaluator`, `KdVResidualEvaluator`, `ReactionDiffusionResidualEvaluator`, `AdvectionDiffusionResidualEvaluator`, `evaluate_weak_heat_residual`, `evaluate_weak_burgers_residual`, translation basis, `InvariantApplier`, finite-transform verification, candidate validation, formula generators, downstream discovery bridge) remain strict-periodic; they now route through the `is_x_periodic` helper rather than direct string compares
- `v0.30b` does not add `compute_finite_difference_derivatives`, `compute_derivatives`, any nonperiodic residual support, any nonperiodic translation/verification path, or any new PDE; those land in v0.30c and later
- `v0.30b` does not add a symmetry-method registry, an external method port, a file loader, a PDEBench/The Well adapter, a KS runtime API, a weak nonperiodic surface, or any new optional dependency

Runtime public API for the frozen `v0.30c` low-order finite-difference derivative slice:

- `pdelie.derivatives.compute_finite_difference_derivatives(field, *, max_spatial_order=2)` for `u_t`, `u_x`, and optionally `u_xx` on scalar 1D nonperiodic (`dirichlet`, `neumann`, `open_unknown`) uniform-grid `FieldBatch` data. The backend uses ``numpy.gradient`` with ``edge_order=2`` for both axes. ``max_spatial_order`` is restricted to ``{1, 2}``; higher orders raise ``ScopeValidationError`` (no `u_xxx`/`u_xxxx` on nonperiodic data in the stable surface).
- the backend rejects periodic data with an explicit `ScopeValidationError`; periodic users must call `compute_spectral_fd_derivatives` or the dispatcher.
- returned `DerivativeBatch.config` carries the v0.30c keys: `spatial_method = "finite_difference_centered"`, `temporal_method = "finite_difference"`, `stencil_edge_order = 2`, `boundary_handling ∈ {"dirichlet", "neumann", "open_unknown"}`, `spatial_max_order ∈ {1, 2}`, `backend_selected_by_boundary_condition` (default `False`), `backend_selection_reason` (default `None`), `recommended_residual_domain_policy = "interior_only"`, and `recommended_boundary_trim_width = 4`.
- `pdelie.derivatives.compute_derivatives(field, *, backend="auto", max_spatial_order=2)` dispatches between `spectral_fd` for periodic data and `finite_difference` for any supported nonperiodic boundary type. When `backend="auto"`, the resulting `DerivativeBatch.config` sets `backend_selected_by_boundary_condition = True` and a non-null `backend_selection_reason` (`"periodic_x_uses_spectral_fd"` or `"nonperiodic_x_uses_finite_difference"`); the selection is always auditable from the artifact itself. Explicit `backend="spectral_fd"` on nonperiodic data and explicit `backend="finite_difference"` on periodic data both raise `ScopeValidationError`; the dispatcher never silently falls back.
- both APIs are submodule-only (no root `pdelie` export) and do not change any existing residual evaluator behavior. Residual evaluator auto-dispatch is deferred.
- `pdelie.contracts.ALLOWED_DERIVATIVE_BACKENDS` now includes the canonical `"finite_difference"` name; the legacy `"finite"` entry is retained.

Runtime public API update for the frozen `v0.30c` boundary-aware reporting slice:

- `pdelie.reporting.summarize_field_batch_readiness` now emits an additive `boundary_condition_warnings: list[str]` field with the v0.30c vocabulary: `"x_boundary_legacy_string_under_schema_0_2"`, `"x_boundary_open_unknown"`, `"x_boundary_dirichlet_unspecified"`, `"x_boundary_neumann_unspecified"`. The list is empty for periodic (legacy or structured) FieldBatches and for fully-specified structured nonperiodic FieldBatches. A non-empty list downgrades the report's `readiness_label` from `"ready"` to `"needs_attention"`; harder failures (non-finite values, missing required metadata keys, non-uniform x or time coordinates) still route to `"not_ready"`.
- `pdelie.reporting.summarize_xarray_dataset_readiness` exposes the same `boundary_condition_warnings` field with the same vocabulary and the same readiness-label downgrade rule.
- `pdelie.reporting.summarize_residual_batch` now records `residual_domain_policy: str` sourced from `ResidualBatch.diagnostics["residual_domain_policy"]` when present; defaults to `"not_configured"` so the field is always present and strict-JSON serializable. No existing residual evaluator output is mutated.
- the readiness reports now treat a non-periodic boundary as a warning rather than a metadata failure; the `"x_boundary_not_periodic"` failure key has been replaced by the new warning vocabulary. Unsupported BC strings (e.g. `"insulating"`) continue to route to a metadata failure under `"x_boundary_unsupported"`.

Decision-only note for the frozen `v0.30c` low-order finite-difference and boundary-aware reporting sub-release:

- `v0.30c` adds no new runtime root `pdelie` export and no new optional dependency
- `v0.30c` records the design decision `low_order_finite_difference_backend_and_boundary_aware_readiness`
- `v0.30c` does not bump the package version (`pyproject.toml` stays at `0.29.0`); the version bump lands at v0.30 release close
- residual evaluator auto-dispatch, residual interior-trim policy enforcement, and finite-transform verification on nonperiodic data are explicitly deferred to v0.30d / v0.31.5
- `u_xxx` and `u_xxxx` on nonperiodic data remain unsupported; no experimental flag is exposed in v0.30c
- the `finite_difference` backend uses only `numpy.gradient(edge_order=2)`; higher-order one-sided stencils, Fornberg-style families, and weak/Galerkin formulations remain deferred

Decision-only note for the frozen `v0.30f` narrow declarative release-gate consolidation sub-release:

- `v0.30f` adds no new runtime public API and no new root `pdelie` export
- `v0.30f` records the design decision `narrow_declarative_release_gate_consolidation`
- `v0.30f` does not bump `pyproject.toml` (stays at `0.29.0`); the version bump is reserved for the v0.30 release close
- `v0.30f` adds `configs/release_gate_manifest.json` (strict JSON, `summary_type = "pdelie_declarative_release_gate_manifest"`) and `tests/test_release_gates.py`; the CI release-gate job is renamed from `v0_29-release-gate` to `v0_30f-release-gate`
- `v0.30f` deletes zero release-gate files. All 26 `tests/test_v0_NN_release_gate.py` files stay in place. Consolidation is by manifest addition, not by file removal.
- `v0.30f` does not extend the supported-assertion-class schema beyond the 11 classes named in the manifest — files that use `forbidden_phrases_in_*`, CHANGELOG / README / ROADMAP_HISTORY phrase checks, disjunctive+forbidden per-page phrase rules, or `required_json_fields` on manifests are listed in `excluded_functional_release_gate_files` and their declarative content stays in the source file
- `v0.30f` does not lift the `numpy<2` cap, does not expand the Python matrix, and does not promote the v0.30e advisory jobs (`lint`, `typecheck`, `coverage`) to blocking

Stable public-surface note for the frozen `v0.30.0` release close:

- `v0.30.0` records the release decision `nonperiodic_readiness_and_low_order_finite_difference_diagnostics`
- `v0.30.0` bumps `pyproject.toml` from `0.29.0` to `0.30.0`; `numpy>=1.24,<2` and `requires-python >=3.11` are unchanged; CI matrix stays Python 3.11 only
- `v0.30.0` adds **no** new root `pdelie` export
- new public submodule surfaces (all stable, submodule-only):
  - `pdelie.derivatives.compute_finite_difference_derivatives(field, *, max_spatial_order=2)` — supports `u_t`, `u_x`, `u_xx` on scalar 1D Dirichlet, Neumann, and `open_unknown` uniform-grid data; `max_spatial_order` is limited to `{1, 2}`; `u_xxx` and `u_xxxx` on nonperiodic data are **not** part of the stable v0.30 surface
  - `pdelie.derivatives.compute_derivatives(field, *, backend="auto", max_spatial_order=2)` — dispatcher; `backend="auto"` routes periodic data to `spectral_fd` and nonperiodic data (Dirichlet, Neumann, `open_unknown`) to `finite_difference`; explicit-mismatch calls raise `ScopeValidationError`; the selection is recorded in `DerivativeBatch.config["backend_selected_by_boundary_condition"]` and `DerivativeBatch.config["backend_selection_reason"]`; there is no silent fallback
  - `pdelie.reporting.summarize_field_batch_readiness` and `pdelie.reporting.summarize_xarray_dataset_readiness` now emit `boundary_condition_warnings: list[str]`; the `readiness_label` is downgraded from `"ready"` to `"needs_attention"` when warnings are present (behavior first shipped in v0.30c and stable now)
  - `pdelie.reporting.summarize_residual_batch` now records a `residual_domain_policy` field sourced from `residual.diagnostics["residual_domain_policy"]`, defaulting to `"not_configured"` when absent; auto-dispatched nonperiodic residuals emit `"interior_only"` and periodic residuals emit `"full_grid"` (behavior first shipped in v0.30c/d and stable now)
- schema migration confirmed stable in v0.30.0:
  - `FieldBatch.SCHEMA_VERSION = "0.2"`
  - `FieldBatch.LEGACY_SCHEMA_VERSIONS = frozenset({"0.1"})`
  - `FieldBatch.from_dict` accepts both `"0.1"` and `"0.2"` payloads and normalizes legacy string `boundary_conditions["x"]` values via the internal `pdelie._boundary` helpers; migrated payloads carry a `schema_0_1_to_0_2_boundary_normalization` entry in `preprocess_log`
- internal-only (not public API): `pdelie._boundary` (`BoundaryFace`, `BoundaryConditionSpec`, `normalize_x_boundary_condition`, `get_x_boundary_type`, `is_x_periodic`) — the module is intentionally underscore-prefixed and not re-exported from any submodule
- cross-cutting hygiene phase 1 (`[tool.ruff]`, `[tool.mypy]` strict scope narrowed to `pdelie.contracts`, `pdelie._boundary`, `pdelie.derivatives.*`, and `[tool.coverage.*]`) is configured and wired to non-blocking CI jobs `lint`, `typecheck`, `coverage`; **promotion to blocking is not part of v0.30 and remains deferred to Phase 2**
- narrow declarative release-gate consolidation shipped: `configs/release_gate_manifest.json` + `tests/test_release_gates.py` replay declarative content across 18 releases plus the v0.30 close row; the CI job is renamed to `v0_30-release-gate`; **zero release-gate files were deleted**; functional smoke tests intentionally remain explicit
- deferred surfaces (not present, not planned in v0.30):
  - root `pdelie.discover_symmetries` (deferred to `v1.0` scope decision)
  - `pdelie.symmetry.SymmetryMethod` registry (deferred to `v0.30.1`)
  - external symmetry-method ports (Ko, LieGAN, LaLiGAN — deferred to `v0.33`+)
  - KdV nonperiodic; KS nonperiodic; public KS runtime API
  - weak nonperiodic residuals; public weak derivative backend; WSINDy design matrices; weak sparse recovery
  - `u_xxx` and `u_xxxx` on nonperiodic data
  - finite-transform verification on nonperiodic translations (`pdelie.verification.verify_translation_generator` and `_apply_uniform_translation` remain periodic-only; overlap-crop is a `v0.31.5` topic)
  - PDEBench and The Well loaders, `load_field_batch`, `from_pdebench`, `from_the_well`, `from_netcdf`, `from_zarr`, dataset-adapter registries (none of these are on `pdelie.data`)
  - multi-generator fitting, finite multi-generator flows, BCH composition, orbit charts
  - multi-channel or 2D contract widening (`v0.34` scope decision)
  - neural or callable generator APIs; operator symmetry
  - train/test policy, split enforcement, leakage prevention
  - PyPI or TestPyPI publication (Git-tag-only for the `v0.x` series; deferred to `v1.0` or later)
- `v0.30.0` is Git-tag-only. Do not publish to TestPyPI or PyPI for `v0.30.0`.

Planning note for `v0.30.1` (registry MVP + `SymmetryCandidate` contract):

- `v0.30.1` will land the submodule-only `pdelie.symmetry.SymmetryMethod` registry MVP alongside a `pdelie.symmetry.SymmetryCandidate` discriminated-union wrapper contract.
- `SymmetryCandidate` is the single input/output shape that every downstream release consumes: v0.31's discovery task bridge, v0.33's Ko-sparse external candidate-generator adapter, and v0.35a's LieGG-style extraction all take and return `SymmetryCandidate`.
- `SymmetryCandidate` represents any of: existing `GeneratorFamily`, `FormulaGeneratorFamily`, `InvariantMapSpec`, matrix Lie-algebra generators, coordinate vector fields, finite-transform specs, and (later) latent generators from trained models. No release forces one shape onto another.
- The built-in `polynomial_translation_svd` adapter must return `SymmetryCandidate`, not `GeneratorFamily` directly. This is what avoids the "SymmetryMethod outputs all coerced into GeneratorFamily" failure mode.
- v0.30.1 remains submodule-only. No root `pdelie` export. No `pdelie.discover_symmetries`. No external-method port in v0.30.1 (Ko-sparse lands in v0.33 as a distinct experimental adapter).
- v0.31 (discovery task bridge) is fenced against `SymmetryCandidate` inputs and outputs: v0.31 consumes only `FieldBatch` + `DerivativeBatch` + `ResidualBatch`, and its `TaskResult` schema records a `candidate_reference: dict | None` that becomes the `SymmetryCandidate` cross-link only after v0.30.1 lands and stabilizes.

Runtime-level APIs are versioned public APIs, but they are not canonical objects.
They are backend-specific and may change with a version bump.

These must not change without version bump.

---

## Experimental API

- neural generators
- weak-form derivatives and weak-form methods beyond the frozen `v0.8` weak residual report slice and the `v0.24` weak supportability reporting layer
- operator symmetry
- advanced invariant maps
- broad dataset adapters, file loaders, metadata inference engines, resampling APIs, and broad Dataset-level ingestion
- multi-generator invariant machinery, finite flows, BCH composition, and public multi-generator PDE fitting

These may change without warning.

---

## Internal / Private

- helper utilities
- intermediate representations

No stability guarantees.
