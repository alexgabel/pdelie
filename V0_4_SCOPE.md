# V0.4 Scope

## Summary

`v0.4` is the first **Lie-algebra span, symbolic reporting, algebra diagnostics, and visual inspection** release for PDELie.

It does **not**:

- introduce a new numerical regime
- add weak-form methods
- add operator methods
- add neural generators as stable API
- add broad dataset adapters
- add a stable 2D PDE pipeline
- add stable multi-generator PDE fitting

Instead, it asks a narrower and more important question:

> Can PDELie represent, normalize, compare, diagnose, and visually inspect a small polynomial Lie-generator family under controlled stable conditions?

`v0.4` is therefore the first **generator-family and algebra-inspection** release, not the first **weak-form**, **operator**, or **broad downstream** release.

---

## Stable Scope

- uniform rectilinear grids only
- synthetic PDE data only
- polynomial Lie point generators only
- Heat/Burgers stable paths remain regression-protected
- multi-generator `GeneratorFamily` representation
- symbolic generator normalization and display
- span comparison diagnostics
- Lie bracket / closure diagnostics
- minimal optional visualization
- no new stable canonical object unless absolutely necessary

### Stable canonical objects

Stable in `v0.4`:

- `FieldBatch`
- `DerivativeBatch`
- `ResidualBatch`
- `ResidualEvaluator`
- `GeneratorFamily`
- `InvariantMapSpec`
- `VerificationReport`

Runtime-only, not canonical:

- symbolic rendering helpers
- optional basis simplification helpers
- span-diagnostics helpers
- closure-diagnostics helpers
- visualization helpers
- existing `InvariantApplier`
- existing downstream bridge helpers

---

## GeneratorFamily Contract

### Canonical core

Canonical meaning depends only on:

- `schema_version`
- `parameterization`
- `coefficients`
- `basis_spec`
- `normalization`
- optional `generator_names`

`diagnostics` is optional and non-authoritative.

Rule:

- `GeneratorFamily` stores enough information to reproduce analysis reports
- symbolic/span/closure/viz helpers compute runtime reports
- attached diagnostics are summaries or provenance, not the contract itself

### Schema policy

- `schema_version` is an **object-schema epoch**, not a package version
- `GeneratorFamily.schema_version = "0.2"` means “post-family-semantics GeneratorFamily”
- other canonical objects may remain at `"0.1"` until their schemas actually change
- schema versions advance independently per canonical object family as needed

### Canonical family form

Canonical `v0.4` output must always be:

- `schema_version = "0.2"`
- `coefficients.shape == (num_generators, num_coefficients_per_generator)`
- explicit `basis_spec`

Required `basis_spec` fields:

- `variables`
- `component_names`
- `basis_terms`
- `component_ordering`
- `term_ordering`
- `layout`

Freeze:

- `layout = "component_major"`

Freeze one concrete example:

```json
{
  "variables": ["t", "x", "u"],
  "component_names": ["tau", "xi", "phi"],
  "basis_terms": [
    {"label": "1", "powers": [0, 0, 0]},
    {"label": "t", "powers": [1, 0, 0]},
    {"label": "x", "powers": [0, 1, 0]},
    {"label": "u", "powers": [0, 0, 1]}
  ],
  "component_ordering": ["tau", "xi", "phi"],
  "term_ordering": ["1", "t", "x", "u"],
  "layout": "component_major"
}
```

Coefficient interpretation rule:

- for each generator row
- iterate `component_names` in order
- within each component, iterate `basis_terms` in order
- each scalar coefficient multiplies that component-term pair

### Legacy compatibility and canonical serialization

- direct construction without `basis_spec` is invalid in `v0.4`
- legacy `0.1` single-generator translation payloads remain accepted only via `GeneratorFamily.from_dict()`
- legacy payloads without `basis_spec` are accepted only when they match the frozen translation parameterization
- those payloads are upgraded in memory to canonical `0.2` family form
- `to_dict()` always emits canonical `0.2` output
- canonical output always includes explicit `basis_spec`
- missing `basis_spec` outside the explicit legacy translation case is a typed validation error
- round-trip tests must cover:
  - legacy input -> canonical in-memory form -> canonical output
  - canonical input -> canonical output

Frozen canonical translation compatibility target:

```json
{
  "schema_version": "0.2",
  "parameterization": "polynomial_translation_affine",
  "coefficients": [[1.0, 0.0, 0.0, 0.0]],
  "basis_spec": {
    "variables": ["t", "x", "u"],
    "component_names": ["xi"],
    "basis_terms": [
      {"label": "1", "powers": [0, 0, 0]},
      {"label": "t", "powers": [1, 0, 0]},
      {"label": "x", "powers": [0, 1, 0]},
      {"label": "u", "powers": [0, 0, 1]}
    ],
    "component_ordering": ["xi"],
    "term_ordering": ["1", "t", "x", "u"],
    "layout": "component_major"
  },
  "normalization": "l2_unit"
}
```

---

## Normalization And Reports

### Numerical vs display normalization

Numerical normalization:

- canonical meaning only
- default row-wise `l2_unit`
- used for fitting/comparison/diagnostics

Display normalization:

- runtime-only
- default `anchor`
- never mutates canonical coefficients
- used only for human-readable output

### Symbolic display promise

- deterministic symbolic display for the given basis
- no promise of canonical algebra-basis recovery
- span equivalence remains primary
- optional runtime-only sparse/anchor basis simplification helper may try to find a nicer displayed basis
- simplification is heuristic and not part of stable equivalence semantics

---

## Span And Closure Diagnostics

### Span diagnostics policy

Primary metric:

- principal angles

Paired derived metric:

- projection residual

Comparison precondition:

- compared families must have structurally equivalent `basis_spec` semantics

Freeze one default inner-product policy:

- normalized variable domain
- default algebraic-fixture domain `[-1, 1]^n`
- PDE-associated variables are affine-mapped to `[-1, 1]`
- uniform component weights after normalization

Preferred computation mode:

- exact polynomial inner product for the current algebraic/runtime polynomial scope

Deferred later work:

- field-aware scaling for PDE-associated learned spans
- deterministic sampled fallback modes for broader comparison settings

Required core span report fields:

- inner_product
- evaluation_mode
- domain
- component_weights
- reference_rank
- candidate_rank
- comparison_rank
- principal_angles_radians
- projection_residual
- conditioning

Additional runtime diagnostic fields may be included, but are not frozen in `v0.4` Milestone 3 unless promoted later.

### Closure / structure-constant policy

Preferred mode:

- exact polynomial Lie brackets for the current monomial algebraic/runtime polynomial scope

Fallback mode:

- deterministic sampled/projection closure only when exact mode is unavailable or explicitly forced

Exact-mode policy:

- closure diagnostics use raw vector-field brackets
- exact brackets may use an internal expanded polynomial representation when bracket monomials leave the stored family basis
- that expanded bracket representation is runtime-only and not a canonical object or stable basis contract
- projected brackets determine reported structure constants and closure diagnostics
- exact mode is available only for the current monomial basis-term encoding; richer or noncanonical term encodings must reject exact mode or downgrade to fallback

Interpretation rule:

- `symmetry_algebra_diagnostics` means closure diagnostics on a family with supplied symmetry-validity evidence
- it does not claim a full family symmetry proof or full per-generator coverage in `v0.4`
- `symmetry_algebra_diagnostics` requires non-empty supplied verification evidence whose classifications are all `exact` or `approximate`
- otherwise the label is `vector_field_algebra_diagnostics`
- closure is interpretive support, never primary evidence
- finite-flow validity, residual validity, and held-out verification remain primary

Required core closure report fields:

- interpretation_label
- verification_classifications
- inner_product
- computation_mode
- domain
- component_weights
- component_targets
- family_rank
- structure_constants
- closure
- antisymmetry
- jacobi
- conditioning

---

## Controlled Targets

Freeze two target classes:

- algebraic family fixtures with exact known coefficients and brackets
- regression protection on existing Heat/Burgers stable paths

Allowed algebraic fixtures:

- translation-style
- scaling-style
- mixed affine
- rotation-style for symbolic/span/bracket tests only

Rotation-style fixtures must be coefficient-level algebra fixtures, not PDE/data fixtures.

---

## Frozen Milestones

### Milestone 1 — `GeneratorFamily` representation semantics
**Status:** Complete

- freeze family-shaped `GeneratorFamily`
- add required `basis_spec`
- freeze canonical serialization and migration policy
- no symbolic display
- no fitting
- no visualization

### Milestone 2 — Symbolic normalization and display
**Status:** Complete

- deterministic symbolic rendering
- runtime-only display normalization
- optional SymPy output
- no heuristic basis simplification helper in the completed M2 slice

### Milestone 3 — Span diagnostics
**Status:** Complete

- principal angles
- projection residual
- frozen inner-product policy
- controlled algebraic fixtures

### Milestone 4 — Closure diagnostics
**Status:** Complete

- exact polynomial Lie brackets where supported
- deterministic fallback where needed and kept minimal
- structure constants
- closure / antisymmetry / Jacobi diagnostics
- verification-aware interpretation labels

### Milestone 5 — Minimal visualization
**Status:** Complete

- optional `[viz]` extra only
- visualization consumes existing canonical objects and runtime reports only
- no visualization-specific contracts
- coefficient-bar renderer for `GeneratorFamily`
- symbolic summary renderer using the frozen M2 symbolic display
- verification-curve renderer for `VerificationReport`
- span-diagnostics renderer for the frozen M3 report shape
- closure-diagnostics renderer for the frozen M4 report shape
- no transformed-field plots, rollout heatmaps, animation, or interactive backends
- explicitly deferrable first if M1–M4 take longer than expected

### Milestone 6 — Algebra-span release gate
**Status:** Active

- one focused pytest release-gate module over the already-implemented M1–M5 behavior
- one dedicated CI visibility job running only that release-gate module
- migration / canonical serialization checks for the translation slice
- symbolic determinism checks for canonical and legacy-upgraded translation families
- tolerant span reproducibility checks on representative exact multi-rank fixtures
- tolerant closure reproducibility checks on representative nontrivial closed fixtures
- compact Heat/Burgers stable translation regression checks
- optional-viz smoke tests using a non-interactive backend with figure cleanup
- no downstream or SymPy behavior in the gate itself
- the CI job may still use the standard `.[test]` environment; this milestone does not claim total optional-dependency isolation
- the dedicated CI job supplements, and does not replace, the full editable/full-suite job

---

## Release Gate

`v0.4` is releasable only if:

- Heat and Burgers still pass unchanged
- `GeneratorFamily` backward compatibility is preserved for the current translation slice
- canonical family serialization is stable and tested
- symbolic rendering is deterministic for a given basis
- span diagnostics are reproducible under the frozen inner-product policy
- closure diagnostics are reproducible and condition-aware
- release-gate numeric assertions use tolerant checks for floating outputs
- visualization remains optional and outside the core install
- visualization smoke does not require an interactive/display backend and closes figures cleanly
- no weak-form, operator, neural, broad-adapter, or manuscript-facing feature is required

---

## Explicit Non-goals

- weak-form methods
- operator methods
- neural generators as stable API
- representative-loss or research-loss code
- broad dataset adapters
- broad downstream benchmark expansion
- stable 2D PDE fitting or data pipeline
- stable multi-generator PDE fitting
- full algebra-basis canonicalization as a stable promise
- polished plotting library
- paper-specific or manuscript-facing logic
