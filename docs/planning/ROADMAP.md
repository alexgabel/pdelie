# PDELie Roadmap

This file is the authoritative release-planning document for `pdelie`.

It defines:

- the current completed release
- the next committed release target when one is frozen
- the medium-term planned direction
- the experimental horizon

It does **not** define package contracts.  
All contracts and stable behavior are defined in:

- `../specs/SPEC.md`
- `../specs/CONTRACTS_AND_DEFAULTS.md`
- `../specs/API_STABILITY.md`

It does **not** define active task execution.  
Execution state belongs in:

- `PLAN.md`

---

## Planning Status Labels

Every roadmap item must be one of:

- **Committed** — planned for the next release series
- **Planned** — intended for a later release, but not yet frozen
- **Experimental** — active research direction, not stable API
- **Deferred** — intentionally postponed

Only **Committed** items may define the next stable release.

---

## Release Philosophy

PDELie advances by **one stable axis at a time**.

Rules:

1. one release should expand at most one major scientific or numerical axis
2. stable scope should only grow after the previous scope is proven end to end
3. experimental work may inform future releases, but does not define them
4. long-term ambition must not be confused with a committed roadmap item

---

## Earliest Stable Releases

### `v0.1.x` — Stabilization
**Status:** Completed

`v0.1.x` was the release series for the first proven vertical slice:

`FieldBatch -> DerivativeBatch -> ResidualBatch -> GeneratorFamily -> VerificationReport`

on the synthetic 1D heat equation with:

- uniform periodic grid
- `spectral_fd`
- analytic heat residual
- polynomial spatial-translation baseline
- finite-transform verification

### Goals for `v0.1.x`

- stabilize packaging
- stabilize public API
- fix bugs
- improve docs
- preserve exact current stable scope

### Non-goals for `v0.1.x`

- no second PDE
- no invariant pipeline
- no weak-form implementation
- no operator methods
- no broad adapters
- no benchmark expansion beyond the MVP path

---

## Second Completed Release

### `v0.2` — Second PDE under the current pipeline
**Status:** Completed

`v0.2` was the second stable release target.

Its purpose is:

> prove that the current stable contracts and symmetry pipeline survive contact with a second PDE.

### In scope for `v0.2`

- add Burgers as the second stable PDE benchmark
- keep the same canonical stable object set as the v0.1 slice where possible
- harden fitting and verification against a second known case
- broaden polynomial fitting just enough to support the second PDE cleanly
- preserve strict stable/experimental boundaries
- keep all comparisons and validation under controlled benchmark settings

### Out of scope for `v0.2`

- no stable invariant pipeline
- no stable weak-form implementation
- no operator symmetry
- no NeuralOperator integration
- no broad ecosystem adapters
- no large benchmark zoo
- no major scope increase in canonical stable objects unless required by the second-PDE path

### Release Gate for `v0.2`

`v0.2` is complete only if:

- Heat still passes the existing stable release gate
- Burgers works cleanly end to end through the current stable pipeline
- fitting and verification remain contract-compliant on both PDEs
- no experimental feature is required for the stable path

---

## Earlier Completed Releases

### `v0.3` — First invariant/downstream utility release
**Status:** Completed

`v0.3` is the first release where PDELie demonstrates stable downstream usefulness, not just symmetry recovery.

Completed scope:

- stable `InvariantMapSpec`
- runtime-only `InvariantApplier`
- one thin backend-specific downstream bridge
- one controlled internal downstream benchmark / release gate
- strict regression protection for the Heat/Burgers stable paths

This release expands the invariant/downstream utility axis without widening the stable library into weak-form methods, operator methods, or broad adapters.

---

### `v0.4` — Lie-algebra span, symbolic reporting, and visual diagnostics
**Status:** Completed

`v0.4` is the completed release where PDELie proves that it can represent, normalize, compare, diagnose, and inspect small polynomial generator families, not just one frozen generator.

Its purpose is:

> prove that PDELie can represent, normalize, compare, diagnose, and inspect small polynomial generator families, not just one frozen generator.

### In scope for `v0.4`

- `GeneratorFamily` family semantics with `basis_spec`
- canonical serialization and migration policy for `GeneratorFamily`
- symbolic generator display
- span comparison with principal angles and projection residual
- closure / structure-constant diagnostics
- minimal optional visualization
- Heat/Burgers regression protection
- controlled algebraic family fixtures

### Out of scope for `v0.4`

- no weak-form stable backend
- no operator symmetry
- no neural generators as stable API
- no broad dataset adapters
- no stable 2D PDE pipeline
- no stable multi-generator PDE fitting
- no research-loss or representative-loss machinery

### Release Gate for `v0.4`

`v0.4` is complete only if:

- Heat and Burgers still pass the existing stable paths unchanged
- family-shaped `GeneratorFamily` serialization is backward-compatible with the current translation slice
- symbolic display is deterministic for a given basis
- span diagnostics are reproducible under a frozen inner-product policy
- closure diagnostics prefer exact mode and document fallback mode when exact mode is unavailable
- visualization remains optional and consumes existing reports/diagnostics only

---

### `v0.5` — Generator-family portability and external-family compatibility
**Status:** Completed

`v0.5` is the completed release where PDELie proves that canonical polynomial generator families can be exported, imported, normalized, and reused without losing meaning.

Completed scope:

- generator-family export/import manifest
- strict external-family compatibility and coercion for canonical polynomial families
- compact portability benchmark focused on semantic preservation
- JSON-compatible manifest payloads under the existing canonical-object policy
- compact `v0.5` release gate
- KdV feasibility recorded as passed in a tests-first slice, with stable KdV promotion deferred

This release closes the portability / external-compatibility axis without broadening the stable numerics regime or adding a stable KdV surface.

---

### `v0.6` — Symmetry-guided PDE discovery utilities
**Status:** Completed

`v0.6` is the completed release where PDELie proves that the existing Heat/Burgers slice can support a small, generic public-library layer for controlled symmetry-guided PDE discovery workflows.

Its purpose is:

> make PDELie useful for controlled symmetry-guided PDE discovery experiments in the existing canonical Heat/Burgers regime.

Frozen release definition:

`PDE data -> generator family -> translation-canonical inputs -> sparse PDE discovery -> recovery metrics`

### In scope for `v0.6`

- discovery recovery metrics
- one thin PySINDy discovery adapter
- one translation-canonical discovery-input builder
- simple robustness utilities
- one compact `v0.6` release gate

### Out of scope for `v0.6`

- no new canonical object
- no root exports from `pdelie.__init__`
- no general discovery-backend framework
- no general invariant-theory engine
- no dataframe, plotting, manuscript, or experiment-matrix layer
- no stable KdV promotion
- no external dataset-ingestion axis
- no weak-form methods
- no operator methods
- no broad adapters
- no paper-specific thresholds, figures, or manuscript logic

### Release Gate for `v0.6`

`v0.6` is complete only if:

- discovery recovery metrics are deterministic and typed
- the thin PySINDy adapter runs reproducibly in the current scalar periodic regime
- translation-canonical discovery inputs are deterministic for representative known/imported translation families
- robustness utilities preserve `FieldBatch` validity and provenance behavior
- Heat/Burgers stable paths remain unchanged
- no stable KdV surface is added

---

## Recent Completed Release

### `v0.10` - Supportability and `v1.0` readiness
**Status:** Completed

`v0.10` is the completed supportability release after the `v0.9` normalized periodic KdV strong-path release.

Its purpose is:

> harden the existing Heat/Burgers/weak-report/KdV engine into a more supportable public surface before adding more numerical scope.

Completed stable scope:

- compact runtime reporting helpers under `pdelie.reporting`
- consistent Heat/KdV example summaries through nested `vertical_slice` reports
- API stability audit across root exports, submodule exports, runtime-only APIs, and explicitly deferred surfaces
- accidental-public-surface guards for stable and deferred APIs
- CI release-gate cleanup:
  - one current `v0_10-release-gate` CI job
  - full editable test suite remains in CI
  - historical release-gate tests remain runnable locally and covered by the full suite
- package/readiness documentation cleanup for eventual `v1.0` publishing decisions

Completed release definition:

`existing stable Heat/Burgers/weak-report/KdV surfaces -> compact supportability reports -> consistent examples/release gates/docs -> v1.0 readiness`

Release interpretation:

- this is a supportability release, not a new numerics release
- reporting helpers are runtime supportability APIs, not canonical objects or manuscript artifact schemas
- example outputs are runtime smoke summaries, not stable scientific-result schemas
- `v0.10.0` is a Git-tag-only release; PyPI and TestPyPI publication are deferred to `v1.0` or later

Explicit non-goals:

- no new PDE in `v0.10`
- no weak KdV API
- no new weak derivative API
- no broad benchmark adapters
- no multidimensional or nonuniform-grid expansion
- no operator-facing symmetry work
- no manuscript-specific reporting logic
- no new canonical object

The authoritative `v0.10` scope freeze belongs in:

- `V0_10_SCOPE.md`

### Release Gate for `v0.10`

`v0.10` is complete only if:

- reporting helpers are deterministic and scoped to existing runtime surfaces
- example outputs remain JSON-serializable runtime smoke summaries, not canonical artifacts
- API stability docs and public-surface tests agree
- historical release-gate tests remain runnable locally
- CI uses one current release-gate job plus full editable tests and package smoke
- package/readiness docs state the `v1.0` publishing decision clearly
- no new PDE, weak KdV, broad adapter, or operator scope lands

---

## Recent Completed Feasibility Release

### `v0.11` - Kuramoto-Sivashinsky strong-path feasibility
**Status:** Completed / Feasibility no-go

`v0.11` is the completed feasibility-first release after the `v0.10` supportability release.

Its purpose is:

> evaluate whether a normalized scalar 1D periodic Kuramoto-Sivashinsky strong path can be promoted safely into the stable runtime surface.

Candidate stable path evaluated internally:

`canonical scalar 1D uniform periodic FieldBatch -> spectral_fd higher spatial derivatives -> normalized KS residual evaluator -> translation fit/verification`

Completed scope:

- stable public `compute_spectral_fd_derivatives(..., max_spatial_order=4)` with `u_xxxx`
- internal normalized KS generator feasibility helper under tests only
- internal KS residual feasibility helper under tests only
- internal KS vertical-slice feasibility coverage
- explicit no-go/defer decision for stable KS runtime promotion
- compact `v0_11-release-gate` CI visibility

Completed release definition:

`existing Heat/Burgers/weak-report/KdV/reporting surfaces -> order-4 spectral derivatives -> internal KS feasibility evidence -> explicit stable-KS no-go/defer closeout`

Release interpretation:

- this is a feasibility/no-go release, not stable KS support
- order-4 spectral derivatives are stable public API
- KS residual and vertical-slice feasibility evidence is internal only
- stable KS runtime promotion is deferred because translation fitting is reference-fallback-backed, not direct SVD in-tolerance recovery
- `v0.11.0` is a Git-tag-only release; PyPI and TestPyPI publication are deferred to `v1.0` or later

Explicit non-goals:

- no public KS generator
- no public KS residual evaluator
- no public KS vertical-slice example
- no KS imported parity
- no weak KS API
- no broad dataset adapters
- no multidimensional, multivariable, or nonuniform-grid expansion
- no custom KS initial-condition API
- no configurable KS coefficient family
- no operator-facing symmetry work
- no manuscript-specific logic

The authoritative `v0.11` scope freeze belongs in:

- `V0_11_SCOPE.md`

### Release Gate for `v0.11`

`v0.11` is complete only if:

- order-4 derivative behavior is documented and covered by tests
- `API_STABILITY.md` states that order-4 derivatives do not add stable KS generator/residual APIs
- internal KS feasibility evidence is recorded as reference-fallback-backed
- public KS generator, residual evaluator, example, weak API, and root exports remain absent
- CI uses `v0_11-release-gate` plus full editable tests and package smoke
- package/readiness docs state the no-go/defer decision clearly

---

## Recent Completed Release

### `v0.12` - Diagnostics and supportability hardening
**Status:** Completed

`v0.12` is the completed diagnostics/supportability release after the completed `v0.11` KS feasibility no-go closeout.

Its purpose is:

> harden diagnostics and reporting around generator fitting, verification, and orbit/coverage supportability without adding new numerical scope.

Completed release definition:

`existing stable Heat/Burgers/weak-report/KdV/reporting surfaces -> fit and verification diagnostics -> orbit/coverage reporting feasibility -> release supportability`

Completed scope:

- fit and verification diagnostic semantics
- `pdelie.reporting.summarize_generator_fit_diagnostics(...)` as the only public `v0.12` API addition
- richer translation-fit diagnostics without changing fitting behavior
- internal KS diagnostic sweeps, with KS remaining unpromoted
- paper-agnostic orbit/coverage diagnostic feasibility kept internal
- API and public-surface audit
- compact current `v0_12-release-gate` readiness

Release interpretation:

- this is a supportability release, not a new PDE release
- KS remains internal feasibility/no-go evidence from `v0.11`
- public `v0.12` API growth is limited to the reporting helper documented in `API_STABILITY.md`
- internal KS diagnostic sweeps and orbit/coverage feasibility remain test-only evidence
- `v0.12.0` is a Git-tag-only release; PyPI and TestPyPI publication are deferred to `v1.0` or later

Explicit non-goals:

- no new PDE
- no stable KS generator
- no stable KS residual evaluator
- no KS vertical-slice example
- no KS imported parity
- no weak KS API
- no broad dataset adapters
- no PDEBench or The Well support
- no multidimensional, multivariable, or nonuniform-grid expansion
- no operator-facing symmetry work
- no private-paper experiment policy
- no root export expansion unless explicitly accepted by a later milestone
- no public orbit/coverage helper or augmentation utility

The authoritative `v0.12` scope freeze belongs in:

- `V0_12_SCOPE.md`

### Release Gate for `v0.12`

`v0.12` is complete only if:

- fit/verification diagnostics are frozen before implementation
- any new public reporting/diagnostic helpers are documented in `API_STABILITY.md`
- KS public generator, residual, example, weak API, imported parity, and root exports remain absent
- orbit/coverage work remains paper-agnostic and diagnostic unless explicitly frozen otherwise
- examples and reporting remain JSON-compatible runtime summaries
- CI uses one compact current release gate plus full editable tests and package smoke
- package/readiness docs preserve the `v1.0` package-index publishing deferral

---

## Current Completed Release

### `v0.21` - External data readiness reports
**Status:** Completed

`v0.21` is the completed external-data readiness reporting release after the `v0.20` unified confidence-reporting release.

Its purpose is:

> make bring-your-own scalar 1D periodic data safer to inspect before residual, confidence, and downstream workflows.

Completed release definition:

`user-owned data -> canonical FieldBatch -> readiness report -> optional residual-evaluator preflight -> confidence/downstream workflows`

Completed scope:

- `pdelie.reporting.summarize_field_batch_readiness(...)`
- `pdelie.examples.run_external_data_readiness_example(...)`
- frozen report type: `field_batch_readiness`
- categorical readiness labels: `ready`, `needs_attention`, `not_ready`
- component statuses: `passed`, `warning`, `failed`, `not_configured`, `unavailable`
- field shape/dim, finite-value, mask, coordinate, metadata, expected-equation, and residual-preflight diagnostics
- conservative metadata suggestions without mutation
- compact current `v0_21-release-gate` readiness

Release interpretation:

- this is a runtime reporting helper, not a canonical object
- readiness is empirical compatibility with current stable contracts, not proof of scientific validity
- `v0.21.0` is a Git-tag-only release; PyPI and TestPyPI publication are deferred to `v1.0` or later

Explicit non-goals:

- no file loaders
- no `xarray.Dataset` support
- no PDEBench or The Well adapters
- no broad dataset adapter framework
- no multidimensional or nonuniform-grid stable support
- no resampling APIs
- no metadata mutation or PDE identity inference
- no train/test split or heldout-leakage policy
- no downstream discovery contracts
- no new PDEs
- no KS runtime promotion
- no weak-form expansion
- no time-translation APIs
- no neural or callable generator API
- no operator-facing symmetry work
- no root export expansion

The authoritative `v0.21` scope freeze belongs in:

- `V0_21_SCOPE.md`

### Release Gate for `v0.21`

`v0.21` is complete only if:

- readiness reports are documented and covered by tests
- generated stable PDE fields report ready
- NumPy and xarray DataArray ingestion paths have readiness coverage
- malformed or out-of-scope field states report needs-attention or not-ready labels
- residual preflight captures typed validation failures without hiding unexpected exceptions
- new APIs are importable from their submodules only
- root `pdelie` remains unchanged
- no file loader, Dataset adapter, broad adapter, resampling API, new PDE, KS runtime API, weak-form expansion, split/leakage policy, time-translation, neural/callable, or operator API lands
- CI uses one compact current release gate plus full editable tests and package smoke
- package/readiness docs preserve the `v1.0` package-index publishing deferral

---

## Recent Completed Release

### `v0.20` - Unified generator confidence reports
**Status:** Completed

`v0.20` is the completed reporting/supportability release after the `v0.19` advection-diffusion strong-path release.

Its purpose is:

> promote the notebook confidence-card teaching pattern into a public runtime reporting helper without adding numerical scope or policy decisions.

Completed release definition:

`residual / fit / verification / candidate-validation / orbit diagnostics -> JSON-compatible generator confidence report -> categorical evidence label and component statuses`

Completed scope:

- `pdelie.reporting.summarize_generator_confidence(...)`
- `pdelie.examples.run_generator_confidence_report_example(...)`
- frozen report type: `generator_confidence`
- categorical confidence labels: `strong`, `qualified`, `failed`, `insufficient_evidence`
- component statuses: `passed`, `warning`, `failed`, `not_configured`, `unavailable`
- threshold keys for residual, verification, and coverage checks
- compact `v0_20-release-gate` readiness at release closeout

Release interpretation:

- this is a runtime reporting helper, not a canonical object
- confidence is empirical configured evidence, not mathematical proof
- no scalar confidence score ships in `v0.20`
- `v0.20.0` is a Git-tag-only release; PyPI and TestPyPI publication are deferred to `v1.0` or later

Explicit non-goals:

- no scalar confidence score
- no benchmark success policy
- no train/test split or heldout-leakage policy
- no transformed `FieldBatch` collections from reporting helpers
- no new PDEs
- no KS runtime promotion
- no weak-form expansion
- no broad dataset adapters
- no time-translation APIs
- no neural or callable generator API
- no operator-facing symmetry work
- no root export expansion

The authoritative `v0.20` scope freeze belongs in:

- `V0_20_SCOPE.md`

### Release Gate for `v0.20`

`v0.20` is complete only if:

- confidence reports are documented and covered by tests
- new APIs are importable from their submodules only
- root `pdelie` remains unchanged
- direct-SVD, fallback, partial-validation, failed-candidate, residual-threshold-failure, and insufficient-evidence cases are covered
- the confidence example emits JSON only
- no new PDE, KS runtime API, weak-form expansion, broad adapter, scalar score, train/test policy, time-translation, neural/callable, split-policy, or operator API lands
- CI used one compact release gate plus full editable tests and package smoke at release closeout
- package/readiness docs preserve the `v1.0` package-index publishing deferral

---

## Recent Completed Release

### `v0.19` - Stable advection-diffusion strong path
**Status:** Completed

`v0.19` is the completed narrow PDE-expansion release after the `v0.18` Fisher-KPP reaction-diffusion strong-path release.

Its purpose is:

> add one stable scalar 1D periodic constant-coefficient advection-diffusion strong path without broadening grids, adapters, weak-form scope, or generator scope.

Completed release definition:

`canonical scalar 1D periodic FieldBatch -> spectral_fd derivatives -> advection-diffusion residual -> translation fit/verification -> vertical-slice summary/example`

Completed scope:

- `pdelie.data.generate_advection_diffusion_1d_field_batch(...)`
- `pdelie.residuals.AdvectionDiffusionResidualEvaluator`
- `pdelie.examples.run_advection_diffusion_vertical_slice_example(...)`
- frozen advection-diffusion equation tag: `advection_diffusion_constant_coefficient`
- residual `u_t + c*u_x - nu*u_xx`
- default parameters `c = 0.75`, `nu = 0.05`
- exact periodic Fourier synthetic rollout
- direct-SVD translation fit evidence in the frozen vertical slice
- compact current `v0_19-release-gate` readiness

Release interpretation:

- this is a scoped synthetic strong-form constant-coefficient advection-diffusion path, not a broad transport-diffusion framework
- the stable claim is backed by direct SVD translation evidence, not reference fallback
- mean drift is diagnostic-only in the release report
- `v0.19.0` is a Git-tag-only release; PyPI and TestPyPI publication are deferred to `v1.0` or later

Explicit non-goals:

- no variable-coefficient advection-diffusion
- no reaction-advection-diffusion
- no weak advection-diffusion
- no public custom initial-condition API
- no KS runtime promotion
- no broad dataset adapters
- no PDEBench or The Well support
- no multidimensional, multivariable, or nonuniform-grid expansion
- no time-translation APIs
- no neural or callable generator API
- no operator-facing symmetry work
- no train/test policy or split management
- no root export expansion

The authoritative `v0.19` scope freeze belongs in:

- `V0_19_SCOPE.md`

### Release Gate for `v0.19`

`v0.19` is complete only if:

- advection-diffusion generator and residual APIs are documented and covered by tests
- new APIs are importable from their submodules only
- root `pdelie` remains unchanged
- the advection-diffusion vertical slice has direct SVD evidence in tolerance
- the advection-diffusion example emits JSON only using the nested vertical-slice summary shape
- no public variable-coefficient advection-diffusion, weak advection-diffusion, KS, broad adapter, custom-IC, nonuniform/multidimensional, time-translation, neural/callable, split-policy, or operator API lands
- CI uses one compact current release gate plus full editable tests and package smoke
- package/readiness docs preserve the `v1.0` package-index publishing deferral

---

## Earlier Completed Release

### `v0.18` - Stable Fisher-KPP reaction-diffusion strong path
**Status:** Completed

`v0.18` is the completed narrow PDE-expansion release after the `v0.17` formula-backed generator interoperability release.

Its purpose is:

> add one stable scalar 1D periodic reaction-diffusion strong path without broadening grids, adapters, or generator scope.

Completed release definition:

`canonical scalar 1D periodic FieldBatch -> spectral_fd derivatives -> Fisher-KPP residual -> translation fit/verification -> vertical-slice summary/example`

Completed scope:

- `pdelie.data.generate_reaction_diffusion_1d_field_batch(...)`
- `pdelie.residuals.ReactionDiffusionResidualEvaluator`
- `pdelie.examples.run_reaction_diffusion_vertical_slice_example(...)`
- frozen Fisher-KPP equation tag: `reaction_diffusion_fisher_kpp`
- residual `u_t - nu*u_xx - rho*u*(1-u)`
- default parameters `nu = 0.05`, `rho = 1.0`
- deterministic pseudo-spectral periodic RK4 synthetic rollout
- direct-SVD translation fit evidence in the frozen vertical slice
- compact current `v0_18-release-gate` readiness

Release interpretation:

- this is a scoped synthetic strong-form Fisher-KPP path, not a broad reaction-diffusion framework
- mass/mean drift is diagnostic-only because Fisher-KPP reaction terms are not mass conserving
- the stable claim is backed by direct SVD translation evidence, not reference fallback
- `v0.18.0` is a Git-tag-only release; PyPI and TestPyPI publication are deferred to `v1.0` or later

Explicit non-goals:

- no advection-diffusion
- no KS runtime promotion
- no weak reaction-diffusion
- no public custom initial-condition API
- no broad dataset adapters
- no PDEBench or The Well support
- no multidimensional, multivariable, or nonuniform-grid expansion
- no neural or callable generator API
- no operator-facing symmetry work
- no train/test policy or split management
- no root export expansion

The authoritative `v0.18` scope freeze belongs in:

- `V0_18_SCOPE.md`

### Release Gate for `v0.18`

`v0.18` is complete only if:

- reaction-diffusion generator and residual APIs are documented and covered by tests
- new APIs are importable from their submodules only
- root `pdelie` remains unchanged
- the reaction-diffusion vertical slice has direct SVD evidence in tolerance
- the reaction-diffusion example emits JSON only using the nested vertical-slice summary shape
- no public advection-diffusion, KS, weak reaction-diffusion, broad adapter, custom-IC, nonuniform/multidimensional, neural/callable, split-policy, or operator API lands
- CI uses one compact current release gate plus full editable tests and package smoke
- package/readiness docs preserve the `v1.0` package-index publishing deferral

---

## Recent Completed Release

### `v0.17` - Formula-backed generator families
**Status:** Completed

`v0.17` is the completed formula-backed generator interoperability release after the `v0.16` external symmetry-candidate validation release.

Its purpose is:

> accept safe formula-backed generator metadata and validate it empirically without turning PDELie into an executable formula parser or learned-generator framework.

Completed release definition:

`canonical scalar 1D periodic FieldBatch + formula-backed generator candidate -> safe formula metadata/evaluation diagnostics -> empirical configured validation report`

Completed scope:

- `pdelie.symmetry.FormulaGeneratorFamily`
- `pdelie.reporting.summarize_formula_generator_family(...)`
- `validate_symmetry_candidate(...)` support for `candidate_kind = "formula_generator_family"`
- strict JSON-compatible formula payload round trips
- safe formula AST nodes: `const`, `var`, `add`, `mul`, integer `pow`, `sin`, `cos`, `reciprocal`, and metadata-only `symbolic_reference`
- finite formula-evaluation diagnostics over canonical scalar 1D periodic `FieldBatch` inputs
- optional reuse of invariant-map validation when a supported finite-transform spec is attached
- affine, trigonometric, rational, finite-transform-backed, and failed-formula example coverage
- API/public-surface audit
- compact current `v0_17-release-gate` readiness

Release interpretation:

- `validated` means configured empirical validation under supplied inputs, not a mathematical proof
- this is formula metadata and empirical validation interop, not a mathematical proof of symmetry
- formula records are runtime-only and do not change canonical polynomial `GeneratorFamily` semantics
- symbolic references are metadata-only unless paired with supported finite-transform evidence
- callable descriptors, arbitrary executable formula strings, and learned-generator training remain deferred
- `v0.17.0` is a Git-tag-only release; PyPI and TestPyPI publication are deferred to `v1.0` or later

Explicit non-goals:

- no callable generator API
- no arbitrary executable formula-string evaluator
- no neural symmetry-detector training
- no canonical `GeneratorFamily` schema change
- no train/test policy
- no split management
- no new PDE
- no stable KS generator or residual evaluator
- no weak KS API
- no broad dataset adapters
- no PDEBench or The Well support
- no multidimensional, multivariable, or nonuniform-grid expansion
- no operator-facing symmetry work
- no root export expansion

The authoritative `v0.17` scope freeze belongs in:

- `V0_17_SCOPE.md`

### Release Gate for `v0.17`

`v0.17` is complete only if:

- formula-backed generator records are documented and covered by tests
- new APIs are importable from their submodules only
- root `pdelie` remains unchanged
- formula candidates validate through the existing symmetry-candidate validator
- finite formula diagnostics and denominator-floor failures are deterministic
- supported finite-transform specs reuse existing invariant-map validation
- formula validation example emits JSON only
- no public callable, executable-string, neural-detector, KS, weak KS, broad adapter, split-policy, or operator API lands
- CI uses one compact current release gate plus full editable tests and package smoke
- package/readiness docs preserve the `v1.0` package-index publishing deferral

---

## Earlier Completed Release

### `v0.16` - External symmetry-candidate validation
**Status:** Completed

`v0.16` is the completed external symmetry-candidate validation release after the `v0.15` materialized orbit batch release.

Its purpose is:

> allow external detector methods to export symmetry candidates and use PDELie as an empirical validation/reporting substrate.

Completed release definition:

`canonical scalar 1D periodic FieldBatch + external candidate payload + residual evaluator -> empirical configured validation report`

Completed scope:

- `pdelie.symmetry.validate_symmetry_candidate(...)`
- accepted `GeneratorFamily` objects and canonical payload mappings
- accepted `InvariantMapSpec` objects and canonical payload mappings
- strict payload disambiguation and typed validation errors
- finite-transform verification for single-row translation-compatible generator candidates
- optional reference-generator span comparison
- closure diagnostics for multi-generator families
- residual and inverse consistency diagnostics for global uniform-translation invariant-map candidates
- Heat, KdV, and failed-candidate example coverage
- API/public-surface audit
- compact current `v0_16-release-gate` readiness

Release interpretation:

- `validated` means configured empirical validation under supplied inputs, not a mathematical proof
- this is detector interop and validation, not detector training
- callable descriptors and formula-backed/non-polynomial generators remain deferred
- `v0.16.0` is a Git-tag-only release; PyPI and TestPyPI publication are deferred to `v1.0` or later

Explicit non-goals:

- no callable descriptors
- no neural symmetry-detector training
- no formula-backed generator families
- no train/test policy
- no split management
- no new PDE
- no stable KS generator or residual evaluator
- no weak KS API
- no broad dataset adapters
- no PDEBench or The Well support
- no multidimensional, multivariable, or nonuniform-grid expansion
- no operator-facing symmetry work
- no root export expansion

The authoritative `v0.16` scope freeze belongs in:

- `V0_16_SCOPE.md`

### Release Gate for `v0.16`

`v0.16` is complete only if:

- candidate validation is documented and covered by tests
- the new API is importable from `pdelie.symmetry` only
- root `pdelie` remains unchanged
- generator-family and invariant-map payload candidates validate
- failed candidates return failed reports rather than exceptions
- callable descriptors and formula-backed generators remain absent
- no public train/test policy, time-translation, KS, weak KS, broad adapter, or operator API lands
- CI uses one compact current release gate plus full editable tests and package smoke
- package/readiness docs preserve the `v1.0` package-index publishing deferral

---

## Recent Completed Release

### `v0.15` - Materialized uniform translation orbit batches
**Status:** Completed

`v0.15` is the completed materialized translation orbit batch release after the `v0.14` invariant workflow summary release.

Its purpose is:

> promote the first conservative user-facing data utility for materializing finite uniform translation orbits from canonical `FieldBatch` inputs.

Completed release definition:

`canonical scalar 1D periodic FieldBatch + finite uniform x-shifts -> materialized orbit FieldBatch + JSON-compatible provenance report`

Completed scope:

- `pdelie.invariants.build_uniform_translation_orbit_batch(...)`
- `pdelie.invariants.OrbitBatchResult`
- shift-major batch materialization
- duplicate-shift preservation
- optional `source_field_id` provenance metadata
- optional source and shift index reporting
- aggregate orbit-materialization metadata and preprocess provenance
- Heat and KdV translation orbit batch example
- API/public-surface audit
- compact current `v0_15-release-gate` readiness

Release interpretation:

- this is the first conservative user-facing data utility beyond diagnostics
- it materializes a `FieldBatch`, but does not manage experimental partitions
- no train/test policy, split management, or heldout-leakage detection is promoted
- time-translation diagnostics remain deferred
- `v0.15.0` is a Git-tag-only release; PyPI and TestPyPI publication are deferred to `v1.0` or later

Explicit non-goals:

- no train/test policy
- no split management
- no heldout-leakage detection
- no sparse-discovery branch policy
- no private-paper augmentation recipe
- no time-translation APIs
- no new PDE
- no stable KS generator or residual evaluator
- no weak KS API
- no broad dataset adapters
- no PDEBench or The Well support
- no multidimensional, multivariable, or nonuniform-grid expansion
- no operator-facing symmetry work
- no root export expansion

The authoritative `v0.15` scope freeze belongs in:

- `V0_15_SCOPE.md`

### Release Gate for `v0.15`

`v0.15` is complete only if:

- orbit-batch materialization is documented and covered by tests
- new APIs are importable from `pdelie.invariants` only
- root `pdelie` remains unchanged
- representative Heat and KdV orbit batches validate as `FieldBatch` objects
- output shape and provenance follow the frozen shift-major ordering
- duplicate shifts remain traceable
- residual diagnostics remain finite on representative materialized batches
- the translation-orbit-batch example emits JSON only
- no public train/test policy, split management, time-translation, KS, weak KS, broad adapter, or operator API lands
- CI uses one compact current release gate plus full editable tests and package smoke
- package/readiness docs preserve the `v1.0` package-index publishing deferral

---

## Recent Completed Release

### `v0.14` - Invariant workflow summaries and read-only orbit reports
**Status:** Completed

`v0.14` is the completed invariant workflow summary and orbit report release after the `v0.13` public orbit/coverage diagnostics release.

Its purpose is:

> combine coverage, consistency, fit, and verification diagnostics into reusable workflow summaries while keeping orbit handling read-only and report-only.

Completed release definition:

`FieldBatch + uniform x-translation shifts + optional windows + residual/fit/verification outputs -> read-only orbit report + combined invariant workflow summary`

Completed scope:

- `pdelie.reporting.summarize_invariant_workflow(...)`
- `pdelie.invariants.summarize_uniform_translation_orbit(...)`
- optional `source_field_id` provenance metadata
- nested coverage, consistency, orbit, generator, fit-diagnostic, and verification summaries
- Heat and KdV invariant workflow example
- API/public-surface audit
- compact current `v0_14-release-gate` readiness

Release interpretation:

- helpers return read-only runtime reports, not augmented datasets
- no transformed `FieldBatch` collections are returned
- no orbit dataset builder or train-augmentation policy is promoted
- time-translation diagnostics remain deferred
- `v0.14.0` is a Git-tag-only release; PyPI and TestPyPI publication are deferred to `v1.0` or later

Explicit non-goals:

- no new PDE
- no stable KS generator or residual evaluator
- no weak KS API
- no broad dataset adapters
- no PDEBench or The Well support
- no multidimensional, multivariable, or nonuniform-grid expansion
- no operator-facing symmetry work
- no public augmentation utilities
- no orbit dataset builders
- no time-translation APIs
- no root export expansion

The authoritative `v0.14` scope freeze belongs in:

- `V0_14_SCOPE.md`

### Release Gate for `v0.14`

`v0.14` is complete only if:

- invariant workflow and orbit report helpers are documented and covered by tests
- new APIs are importable from their submodules only
- root `pdelie` remains unchanged
- representative Heat and KdV invariant workflow reports are JSON-compatible
- the invariant workflow example emits JSON only
- no public augmentation, orbit dataset, time-translation, KS, weak KS, broad adapter, or operator API lands
- CI uses one compact current release gate plus full editable tests and package smoke
- package/readiness docs preserve the `v1.0` package-index publishing deferral

---

## Recent Completed Release

### `v0.13` - Public orbit and coverage diagnostics
**Status:** Completed

`v0.13` is the completed public orbit/coverage diagnostics release after the `v0.12` supportability hardening release.

Its purpose is:

> promote reusable orbit/coverage diagnostics under `pdelie.invariants` while keeping augmentation and downstream experiment policy out of the library.

Completed release definition:

`canonical periodic 1D FieldBatch + uniform translation action -> grid-point coverage diagnostics + transform-consistency diagnostics -> compact example/release gate`

Completed scope:

- `pdelie.invariants.compute_periodic_window_coverage(...)`
- `pdelie.invariants.diagnose_uniform_translation_consistency(...)`
- explicit grid-point coverage semantics for endpoint-excluded periodic grids
- explicit field-shift-then-fixed-window coverage convention
- typed validation for invalid grids, windows, shifts, and domain lengths
- uniform-translation consistency diagnostics over canonical scalar 1D periodic `FieldBatch` inputs
- optional residual-stability diagnostics with robust absolute-or-relative delta policy
- `python -m pdelie.examples.orbit_coverage_diagnostics`
- API/public-surface audit
- compact current `v0_13-release-gate` readiness

Release interpretation:

- diagnostics support invariant/finite-transform workflows but do not construct augmented datasets
- the new APIs are JSON-compatible runtime reports, not canonical objects or manuscript schemas
- public orbit-view builders and augmentation utilities remain deferred
- KS remains internal feasibility/no-go evidence from `v0.11` and `v0.12`
- `v0.13.0` is a Git-tag-only release; PyPI and TestPyPI publication are deferred to `v1.0` or later

Explicit non-goals:

- no new PDE
- no stable KS generator
- no stable KS residual evaluator
- no weak KS API
- no broad dataset adapters
- no PDEBench or The Well support
- no multidimensional, multivariable, or nonuniform-grid expansion
- no operator-facing symmetry work
- no public augmentation utilities
- no public orbit-view builders
- no train-augmentation policy
- no sparse-discovery branch policy
- no private-paper experiment logic
- no root export expansion

The authoritative `v0.13` scope freeze belongs in:

- `V0_13_SCOPE.md`

### Release Gate for `v0.13`

`v0.13` is complete only if:

- coverage and consistency diagnostics are documented and covered by tests
- new APIs are importable from `pdelie.invariants` only
- root `pdelie` remains unchanged
- representative coverage and transform-consistency reports are JSON-compatible
- the orbit/coverage example emits JSON only
- no public augmentation, orbit-view, KS, weak KS, broad adapter, or operator API lands
- CI uses one compact current release gate plus full editable tests and package smoke
- package/readiness docs preserve the `v1.0` package-index publishing deferral

---

## Earlier Completed KdV Release

### `v0.9` - Stable normalized periodic KdV strong path
**Status:** Completed

`v0.9` is the completed release after the `v0.8` weak residual report series.

Its purpose is:

> promote the existing tests-first KdV feasibility slice into a narrow stable runtime path for normalized, periodic, short-horizon KdV data.

Completed stable scope:

- extend `compute_spectral_fd_derivatives(...)` with `max_spatial_order` through `u_xxx`
- add `pdelie.data.generate_kdv_1d_field_batch(...)`
- add `pdelie.residuals.KdVResidualEvaluator`
- keep KdV normalized as `u_t + 6*u*u_x + u_xxx = 0`
- keep support limited to canonical scalar 1D uniform periodic `FieldBatch` inputs
- add KdV translation fitting and held-out verification through the existing polynomial translation stack
- add mandatory `from_numpy` parity and optional `from_xarray` parity for representative KdV data
- add one compact `v0_9-release-gate`

Completed release definition:

`canonical scalar 1D uniform periodic FieldBatch -> spectral_fd with u_xxx -> normalized KdV residual evaluator -> translation fit/verification`

Release interpretation:

- this is stable normalized periodic short-horizon KdV support, not general KdV support
- the stable numerical guarantee covers the frozen default short-horizon regime and release-gate fixtures
- accepted generator parameters outside the release-guaranteed regime are user-risk in `v0.9`
- `v0.9.0` is a Git-tag-only release; PyPI and TestPyPI publication are deferred to `v1.0` or later

Explicit non-goals:

- no weak KdV API
- no weak derivative API expansion
- no root `pdelie` exports for KdV APIs
- no custom KdV initial-condition API
- no variable-coefficient KdV
- no PDEBench or The Well adapters
- no multidimensional, multivariable, nonuniform-grid, operator, or broad adapter expansion
- no new canonical object

The authoritative `v0.9` scope freeze belongs in:

- `V0_9_SCOPE.md`

### Release Gate for `v0.9`

`v0.9` is complete only if:

- default derivative behavior remains compatible with `v0.8`
- `u_xxx` matches exact Fourier fixtures under the frozen derivative test
- KdV generator outputs are deterministic canonical `FieldBatch` objects
- default KdV fixtures satisfy frozen residual and conservation thresholds
- KdV translation fitting and held-out verification pass the frozen vertical slice
- representative KdV data passes mandatory `from_numpy` parity and optional `from_xarray` parity when available
- no weak KdV API or root KdV export is added

---

## Earlier Completed Release

### `v0.8` — Window-indexed weak residuals
**Status:** Completed

`v0.8` is the completed release after the `v0.7` structured-ingestion series.

Completed stable scope:

- `pdelie.residuals.evaluate_weak_heat_residual(...)`
- `pdelie.residuals.evaluate_weak_burgers_residual(...)`
- window-indexed weak residual reports rather than field-shaped residual arrays
- canonical scalar 1D uniform periodic `FieldBatch` inputs only
- Heat and Burgers only
- frozen local separable quartic-bump windows with fixed centered overlap and trapezoidal quadrature, with exact details in `V0_8_SCOPE.md`
- deterministic clean/noisy/coarse robustness comparisons against the current `spectral_fd` / analytic path
- one compact `v0_8-release-gate`

Completed release definition:

`canonical FieldBatch -> stable weak residual report APIs for Heat/Burgers -> deterministic clean/noisy/coarse robustness comparisons against the current spectral/analytic path`

Release interpretation:

- the degraded weak-path wins are frozen as representative contract-stability signals
- those degraded wins are fallback-backed release checks, not general weak-superiority claims
- stable weak derivatives, weak `ResidualBatch` / `ResidualEvaluator` integration, and weak KdV remain deferred

The authoritative `v0.8` scope freeze belongs in:

- `V0_8_SCOPE.md`

---

## Earlier Completed Release

### `v0.7` — Structured external data ingestion
**Status:** Completed

`v0.7` is the completed structured-ingestion release carried forward into later releases.

Completed scope:

- `pdelie.data.from_numpy(...)`
- `pdelie.data.from_xarray(...)`
- strict conversion to canonical `FieldBatch`
- 1D uniform rectilinear inputs only
- scalar-variable stable slice only
- explicit dims, coords, metadata, and provenance validation
- parity tests showing imported Heat/Burgers-like data behaves like native `FieldBatch`

The authoritative `v0.7` scope freeze belongs in:

- `V0_7_SCOPE.md`

---

## Medium-Term Planned Pre-`v1.0` Outline

The following sequence is planned, not committed execution.
Only `Committed` items define the next release target.

The principle is still one stable axis at a time: do not combine PDE expansion, data-adapter expansion, weak-form expansion, multi-generator machinery, and downstream policy in one release.

### `v0.22` - Downstream discovery contracts
**Status:** Planned

Purpose:

> turn the narrow downstream discovery path into clearer, backend-neutral runtime contracts and reports.

Candidate scope:

- broad downstream discovery contracts for runtime reports
- standardized recovery and provenance summaries
- bridge-output summaries for backend-native arrays and labels
- orbit-materialization provenance checks for downstream inputs
- paper-agnostic downstream evaluation templates

Deferred:

- general discovery-backend framework
- manuscript thresholds
- backend lock-in beyond thin adapters
- automatic experiment policy

### `v0.23` - Split/leakage provenance diagnostics
**Status:** Planned

Purpose:

> reduce misuse risk now that materialized orbit batches are public data utilities.

Candidate scope:

- diagnostics over user-supplied train/heldout partitions
- source/shift provenance overlap reports
- heldout-leakage risk reports for orbit-materialized data

Explicit boundary:

- no train/test split management
- no automatic split generation
- no downstream augmentation policy
- no benchmark success criteria

### `v0.24` - Weak-form supportability reset
**Status:** Planned

Purpose:

> decide whether weak derivatives and broader weak-form methods can be promoted beyond the frozen `v0.8` weak residual report slice.

Candidate scope:

- weak derivative backend feasibility
- broader weak-form residual method contracts
- weak reaction-diffusion feasibility
- noisy/coarse-data supportability diagnostics

Deferred unless separately proven:

- weak KdV APIs
- weak KS APIs
- broad noisy-data superiority claims

### `v0.25` - KdV scope decision
**Status:** Planned

Purpose:

> decide whether KdV should expand beyond the frozen normalized periodic short-horizon regime.

Candidate scope:

- custom KdV initial-condition feasibility
- configurable KdV coefficient feasibility
- general KdV support decision
- weak KdV decision

Acceptable outcome:

- keep KdV frozen and document why if the broader regime is not supportable.

### `v0.26` - KS revisit
**Status:** Planned

Purpose:

> revisit the `v0.11`/`v0.12` KS no-go with better confidence diagnostics.

Candidate decisions:

- stable KS residual-only public path
- stable full KS strong path
- continued no-go/defer

Explicitly evaluated:

- stable KS data generator
- stable KS residual evaluator
- KS vertical-slice example
- KS imported parity
- weak KS API
- root KS export

Default stance:

- no root KS export
- no weak KS
- no public full KS path unless direct residual-based fitting evidence improves

### `v0.27` - Multi-generator feasibility
**Status:** Planned

Purpose:

> test whether the current single-generator-centered runtime can support stable multi-generator workflows.

Candidate scope:

- stable multi-generator PDE fitting feasibility
- multi-generator invariant machinery feasibility
- closure/span/verification interactions for fitted families

High-risk boundary:

- this may alter core assumptions and should not be mixed with a PDE or adapter release.

### `v0.28` - Data ecosystem feasibility
**Status:** Planned

Purpose:

> decide whether external data ecosystem support can be widened without weakening canonical contracts.

Candidate scope:

- `xarray.Dataset` support
- file-based dataset loaders
- narrow adapter feasibility
- metadata inference expansion

Deferred unless scope is frozen:

- PDEBench / The Well as stable APIs
- broad adapter framework
- implicit alias-based loaders

### `v0.29` - Grid-domain feasibility
**Status:** Planned

Purpose:

> evaluate multidimensional and nonuniform-grid ingestion as a contract change, not a small adapter patch.

Candidate scope:

- multidimensional ingestion feasibility
- nonuniform-grid ingestion feasibility
- resampling/reporting decisions
- derivative/residual compatibility diagnostics for unsupported grids

Default stance:

- unsupported until a dedicated scope freeze proves the contracts.

### `v0.30` - Orbit/action scope decision
**Status:** Planned

Purpose:

> decide whether invariant actions should expand beyond frozen uniform spatial translation materialization.

Candidate scope:

- public orbit-view builders beyond the materialized uniform translation orbit batch helper
- transformed `FieldBatch` collection policy for data APIs
- time-translation APIs
- `axis="time"` support

Boundary:

- reporting helpers remain report-only
- transformed collections belong in explicit data/invariant APIs, not reporting APIs

### `v0.31` - `v1.0` readiness hardening
**Status:** Planned

Purpose:

> freeze the public engine before `v1.0`.

Candidate scope:

- public/private API audit
- root export policy audit
- deprecation policy
- package publishing plan
- docs and notebook consistency audit
- release-gate consolidation
- support matrix for stable PDEs, grids, residuals, candidate types, and downstream paths

### `v1.0` - Stable public engine
**Status:** Deferred

`v1.0` should only happen once PDELie has a stable, supportable public surface for:

- canonical PDE field data
- generator families
- verification and diagnostics
- portability manifests
- discovery utilities
- selected structured external-data ingestion
- selected stable strong-form PDE paths

`v1.0` should be a stabilization milestone, not a scope-expansion milestone.

### Later / Experimental - Operator-facing symmetry discovery
**Status:** Experimental / Deferred

Operator-facing symmetry work remains a later or separate track.

Candidate directions:

- FNO / DeepONet-compatible symmetry diagnostics
- operator-level generator probing
- learned symmetry representations in neural operators
- operator benchmark layers

This is not part of the near-term non-operator Paper 1 path and should not be mixed into `v0.6` or `v0.7`.

---

## Relationship Between Roadmap and Strategy Documents

### Authoritative for scheduling
- `ROADMAP.md`
- `V0_6_SCOPE.md` once frozen
- `V0_7_SCOPE.md` once frozen
- `V0_8_SCOPE.md` once frozen
- `V0_9_SCOPE.md` once frozen
- `V0_10_SCOPE.md` once frozen
- `V0_11_SCOPE.md` once frozen
- `V0_12_SCOPE.md` once frozen
- `V0_13_SCOPE.md` once frozen
- `V0_14_SCOPE.md` once frozen
- `V0_15_SCOPE.md` once frozen
- `V0_16_SCOPE.md` once frozen
- `V0_17_SCOPE.md` once frozen
- `V0_18_SCOPE.md` once frozen
- `V0_19_SCOPE.md` once frozen
- `PLAN.md` for current execution only

### Non-authoritative for scheduling
- `V0_15_PLUS_STRATEGY.md`
- `../strategy/INTEROPERABILITY_AND_BENCHMARKING.md`
- `LLM_CONTEXT.md`

These may describe strategic horizons or research directions, but they do **not** commit a feature to a release.

---

## Change Policy

This roadmap should only be updated:

- at release boundaries
- when a new release scope is frozen
- when a committed item is explicitly deferred

It should **not** be edited every time a new idea appears.

---

## Short Version

- `v0.1.x` = stabilize the proven heat-equation vertical slice
- `v0.2` = add Burgers under the same stable pipeline
- `v0.3` = first stable invariant/downstream utility via invariants
- `v0.4` = Lie-algebra span, symbolic reporting, and visual diagnostics
- `v0.5` = generator-family portability and external-family compatibility, with KdV kept non-stable
- `v0.6` = symmetry-guided PDE discovery utilities in the current Heat/Burgers regime
- `v0.7` = structured external data ingestion into canonical `FieldBatch`
- `v0.8` = window-indexed weak residual reports and representative robustness comparisons
- `v0.9` = stable normalized periodic short-horizon KdV strong path
- `v0.10` = supportability and `v1.0` readiness for the existing stable engine
- `v0.11` = order-4 spectral derivatives and Kuramoto-Sivashinsky feasibility no-go/defer closeout
- `v0.12` = diagnostics and supportability hardening for fitting, verification, reporting, and orbit/coverage diagnostics
- `v0.13` = public orbit/coverage diagnostics under `pdelie.invariants`, without augmentation
- `v0.14` = invariant workflow summaries and read-only uniform translation orbit reports, without augmentation
- `v0.15` = materialized uniform translation orbit batches under `pdelie.invariants`
- `v0.16` = external symmetry-candidate interop and validation, not detector training
- `v0.17` = formula-backed generator records and validation, without callables or learned-generator training
- `v0.18` = stable scalar 1D periodic Fisher-KPP reaction-diffusion strong path
- `v0.19` = stable scalar 1D periodic constant-coefficient advection-diffusion strong path
- `v0.20` = unified generator confidence reports
- `v0.21` = external data readiness reports
- `v0.22` = planned downstream discovery contracts and provenance reports
- `v0.23` = planned split/leakage provenance diagnostics, not split management
- `v0.24` = planned weak-form supportability reset
- `v0.25` = planned KdV scope decision
- `v0.26` = planned KS revisit
- `v0.27` = planned multi-generator feasibility
- `v0.28` = planned data ecosystem feasibility
- `v0.29` = planned grid-domain feasibility
- `v0.30` = planned orbit/action scope decision
- `v0.31` = planned `v1.0` readiness hardening
- `v1.0` = stable public engine
- later / experimental = operator-facing symmetry discovery
