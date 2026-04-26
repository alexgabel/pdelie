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

Runtime-level APIs are versioned public APIs, but they are not canonical objects.
They are backend-specific and may change with a version bump.

These must not change without version bump.

---

## Experimental API

- neural generators
- weak-form methods
- operator symmetry
- advanced invariant maps
- multi-generator invariant machinery

These may change without warning.

---

## Internal / Private

- helper utilities
- intermediate representations

No stability guarantees.
