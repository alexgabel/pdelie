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
