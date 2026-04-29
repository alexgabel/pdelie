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

## Current Completed Release

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

## No Committed Release Target

No next release is committed after `v0.11`.
`v0.12+` remains planned and conditional until a separate scope freeze is accepted.

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

## Medium-Term Horizon

### `v0.12+` - Later PDE and dataset coverage
**Status:** Planned

Later PDE and dataset coverage remains planned after the supportability release and the completed `v0.11` KS feasibility no-go closeout.

Candidate directions:

- wave equation only after second-time-derivative semantics are frozen
- reaction-diffusion systems after multivariable semantics are explicitly scoped
- PDEBench / The Well adapters after generic ingestion and provenance policies are proven
- multidimensional structured grids only after the 1D path is stable and supportable

Each of these requires its own scope freeze before implementation.

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
- `PLAN.md` for current execution only

### Non-authoritative for scheduling
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
- `v0.12+` = wave semantics, external benchmark adapters, and broader PDE coverage only after scope freezes
- `v1.0` = stable public engine
- later / experimental = operator-facing symmetry discovery
