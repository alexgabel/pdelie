# PDELie Roadmap

This file is the authoritative release-planning document for `pdelie`.

It defines:

- the current release series
- the next committed release target
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

## Current State

### `v0.1.x` — Stabilization
**Status:** Committed

`v0.1.x` is the release series for the first proven vertical slice:

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

## Previous Release Target

### `v0.2` — Second PDE under the current pipeline
**Status:** Committed

`v0.2` is the next stable release target.

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

## Previous Completed Release

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

## Previous Completed Release

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

## Previous Completed Release

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

## Current Completed Release

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

## Next Committed Release Target

### `v0.7` — Structured external data ingestion
**Status:** Committed

`v0.7` is the next committed release after the completed `v0.6` discovery-utility release.

Its purpose is:

> make PDELie able to ingest external structured 1D uniform rectilinear PDE data into canonical `FieldBatch`, so the existing symmetry and discovery utilities can run outside internally generated synthetic fixtures.

### Committed scope for `v0.7`

- `pdelie.data.from_numpy(...)`
- `pdelie.data.from_xarray(...)`
- strict conversion to canonical `FieldBatch`
- 1D uniform rectilinear inputs only
- scalar-variable stable slice only
- explicit dims, coords, metadata, and provenance validation
- parity tests showing imported Heat/Burgers-like data behaves like native `FieldBatch`

### Out of scope for `v0.7`

- no PDEBench-specific loader
- no The Well adapter
- no HDF5, netCDF, or Zarr stable loader
- no 2D/3D external-data ingestion
- no nonuniform-grid support
- no broad metadata inference
- no weak-form methods
- no operator methods

`v0.7` is therefore not a broad dataset-support release. It is the first structured-ingestion release:

> external structured arrays -> canonical `FieldBatch` -> existing PDELie pipeline.

The authoritative `v0.7` scope freeze belongs in:

- `V0_7_SCOPE.md`

`V0_7_PREP.md` remains non-authoritative preparation material.

---

## Medium-Term Horizon

### `v0.8` — Robust high-derivative and weak-form numerics
**Status:** Planned / Experimental

`v0.8` is the likely next major numerical expansion after structured ingestion.

Its purpose is:

> add derivative-robust machinery for noisy, coarse, or high-derivative PDE discovery, while preserving the canonical data and generator-family contracts.

Candidate directions:

- weak-form derivatives / weak residual workflows
- WSINDy-style integration tests
- robust residual evaluation under noise
- high-derivative stress tests
- KdV promotion if the weak/spectral story is mature enough

KdV does not require weak-form methods for clean synthetic periodic tests, but noisy or coarse KdV is a natural pressure point for weak-form machinery. `v0.8` is therefore the right place to decide whether weak methods become a stable numerical axis.

### `v0.9` — Broader PDE and dataset coverage
**Status:** Planned / Experimental

`v0.9` may broaden PDE and dataset coverage once structured ingestion and robust numerics are stable.

Candidate directions:

- stable KdV if not already promoted
- wave equation after second-time-derivative semantics are clarified
- reaction-diffusion systems
- Kuramoto-Sivashinsky as a harder high-derivative stress test
- PDEBench / The Well adapters after generic ingestion is proven
- multidimensional structured grids if the 1D path is stable

### `v1.0` — Stable public engine
**Status:** Deferred

`v1.0` should only happen once PDELie has a stable, supportable public surface for:

- canonical PDE field data
- generator families
- verification and diagnostics
- portability manifests
- discovery utilities
- selected structured external-data ingestion

`v1.0` should be a stabilization milestone, not a scope-expansion milestone.

### Later / Experimental — Operator-facing symmetry discovery
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
- `PLAN.md` for current execution only

### Non-authoritative for scheduling
- `V0_7_PREP.md`
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
- `v0.8` = robust high-derivative / weak-form numerics
- `v0.9` = broader PDE and dataset coverage
- `v1.0` = stable public engine
- later / experimental = operator-facing symmetry discovery
