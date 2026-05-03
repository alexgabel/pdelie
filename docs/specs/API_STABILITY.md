# API Stability Policy

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

Runtime-level APIs are versioned public APIs, but they are not canonical objects.
They are backend-specific and may change with a version bump.

These must not change without version bump.

---

## Experimental API

- neural generators
- weak-form derivatives and weak-form methods beyond the frozen `v0.8` weak residual report slice
- operator symmetry
- advanced invariant maps
- multi-generator invariant machinery

These may change without warning.

---

## Internal / Private

- helper utilities
- intermediate representations

No stability guarantees.
