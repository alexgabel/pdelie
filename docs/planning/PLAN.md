# PDELie — Archived Execution Plan (V0.4)

## Archive State

**V0.4 feature milestones complete — archival planning record after the `0.4.0` release**

This file is the archived execution plan for the completed `v0.4` release series.

It should contain:

- a short record of the completed `v0.3` release
- the frozen record of the completed `v0.4` milestone line
- milestone-specific rules and gates

It should **not** redefine package contracts or roadmap commitments. Those belong in:

- `../specs/SPEC.md`
- `../specs/CONTRACTS_AND_DEFAULTS.md`
- `../specs/API_STABILITY.md`
- `ROADMAP.md`
- `V0_4_SCOPE.md`

---

## V0.3 Closeout

`v0.3` is complete as the first invariant/downstream utility release.

Completed outcome:

- stable `InvariantMapSpec`
- runtime-only `InvariantApplier`
- runtime-only narrow PySINDy bridge
- internal controlled downstream benchmark / release gate
- Heat and Burgers regression protection preserved

`v0.4` begins from that frozen release surface.

---

## Milestone 5 — Minimal Visualization Suite

### Goal

Add a minimal report-first optional visualization layer over existing canonical objects and frozen runtime reports without changing scientific semantics or the Heat/Burgers stable paths.

### Frozen Decisions

- visualization is runtime-only and must not mutate stored coefficients, normalization, or diagnostics
- `pdelie.viz` is an optional package and must not be exported from root `pdelie`
- Matplotlib is the only M5 visualization dependency
- renderers must consume existing canonical objects or frozen runtime report dicts only
- no new visualization-specific contracts or canonical objects are introduced
- no field rollout heatmaps, transformed-field plots, animation, or interactive backends are part of M5
- no fitting, verification, span, or closure semantics change in M5

### Deliverables

- optional `pdelie.viz` runtime package
- coefficient-bar renderer for `GeneratorFamily`
- symbolic summary renderer using M2 symbolic display
- verification-curve renderer for `VerificationReport`
- span-diagnostics renderer over the frozen M3 report schema
- closure-diagnostics renderer over the frozen M4 report schema

### Acceptance Criteria

Milestone 5 is complete only if:

- existing Heat/Burgers stable paths still pass unchanged
- canonical objects and runtime scientific report semantics remain unchanged
- `pdelie.viz` is importable only through the optional visualization package path
- each M5 renderer returns a Matplotlib `Figure`
- malformed runtime report dicts fail with typed validation errors
- no new canonical object is introduced
- no public fitting, invariant, span, closure, or canonical semantics are broadened

### Test Plan

Run at minimum:

- runtime visualization tests
- runtime public API import tests
- coefficient-bar structural tests
- symbolic-summary text tests
- verification-curve log-scale tests
- span-plot report-shape tests
- closure-plot report-shape tests
- malformed-report validation tests
- existing Heat/Burgers regression tests
- full `pytest`

---

## Milestone 6 — Algebra-Span Release Gate

### Goal

Turn the already-implemented V0.4 M1–M5 behavior into one explicit pytest+CI release gate without adding any new capabilities or changing any runtime semantics.

### Frozen Decisions

- M6 is a release-gate milestone only; it does not add new public APIs, canonical objects, or runtime behavior
- M6 excludes downstream and SymPy behavior from the gate itself
- the dedicated CI job may still install the standard `.[test]` extra; M6 does not claim total optional-dependency isolation
- floating outputs in the release gate must use tolerant numeric checks; exact assertions are reserved for strings and small clearly algebraic fixtures
- the dedicated M6 CI job is an explicit release-gate visibility job and does not replace the full editable/full-suite job
- visualization smoke in M6 must use a non-interactive backend and must close figures cleanly

### Deliverables

- one focused `tests/test_v0_4_release_gate.py` module over frozen M1–M5 behavior
- one dedicated `v0_4-release-gate` CI job that runs only the release-gate module

### Acceptance Criteria

Milestone 6 is complete only if:

- legacy translation payloads still upgrade cleanly to canonical `GeneratorFamily`
- canonical translation family serialization remains explicit and stable
- symbolic rendering remains deterministic for the frozen translation slice
- span diagnostics are reproducible on representative exact multi-rank fixtures
- closure diagnostics are reproducible on representative nontrivial closed fixtures
- Heat and Burgers stable translation paths still verify as `exact`
- all current M5 renderers smoke-test cleanly under a non-interactive backend
- the dedicated M6 CI job is added without replacing the existing full-suite or package-smoke jobs

### Test Plan

Run at minimum:

- `pytest tests/test_v0_4_release_gate.py`
- full `pytest`

Milestone 6 is now complete. No further V0.4 feature milestones are planned in the released `0.4.0` line.

---

## Later Milestones

Feature milestone sequencing for `v0.4` is complete.

Hard sequencing rules:

- do not add fitting logic before representation and diagnostics semantics are frozen
- do not let visualization define new semantics or helper contracts

---

## Rules

- DO NOT add weak-form methods
- DO NOT add operator methods
- DO NOT add broad dataset adapters
- DO NOT add neural generators as stable API
- DO NOT add representative-loss or research-loss code
- DO NOT add stable 2D PDE pipeline work
- DO NOT add stable multi-generator PDE fitting in `v0.4`
- DO NOT add broad downstream benchmark expansion
- DO NOT add paper-specific or manuscript-facing language

---

## Status

- `v0.3`: **COMPLETE**
- Milestone 1: **COMPLETE**
- Milestone 2: **COMPLETE**
- Milestone 3: **COMPLETE**
- Milestone 4: **COMPLETE**
- Milestone 5: **COMPLETE**
- Milestone 6: **COMPLETE**
