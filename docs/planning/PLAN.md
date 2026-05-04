# PDELie - Execution Plan (V0.27)

**Status:** COMPLETE

**V0.27 is complete as the multi-generator diagnostics decision release**

This file is the completed execution record for the `v0.27` release series.

## Release Theme

`v0.27` diagnoses supplied multi-row `GeneratorFamily` objects without promoting public multi-generator PDE fitting or finite group-action machinery.

Decision label:

```text
multi_generator_diagnostics_feasible_fitting_deferred
```

Stable investigation path:

```text
canonical scalar 1D periodic FieldBatch
-> residual evaluator
-> supplied multi-row GeneratorFamily
-> algebraic diagnostics + PDE-context diagnostics + fit probe diagnostics
-> explicit public promotion decision
```

The release adds no public multi-generator fitting API, finite-flow API, BCH composition API, invariant chart, orbit builder, operator API, neural/callable generator API, or root export.

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

Authoritative scope:

- `docs/planning/V0_27_SCOPE.md`

## Milestone 0 - Scope Freeze

Freeze `v0.27` as multi-generator diagnostics/decision only.

Closeout:

- added `docs/planning/V0_27_SCOPE.md`
- reset `PLAN.md` as the active `v0.27` execution record
- updated `ROADMAP.md` to record `v0.27` as the current completed release
- explicitly deferred multi-generator PDE fitting, finite flows, BCH composition, invariant charts, orbit charts, and root exports

## Milestone 1 - Semantics Freeze

Frozen semantics:

- bracket convention: `[X_i, X_j] = X_i · ∇X_j - X_j · ∇X_i`
- structure constants: `[X_i, X_j] = sum_k C[i, j, k] X_k`
- basis order is the row order of `GeneratorFamily.coefficients`
- closure diagnostics are algebraic evidence only
- rank-deficient well-formed families report diagnostic status instead of raising solely due to redundancy
- `closure_required=True|False` controls whether closure failure is a failed or warning validation check

## Milestone 2 - Algebraic Diagnostic Matrix

Implemented supplied-family diagnostic coverage for:

- abelian two-generator translations
- affine `x` algebra
- affine `u` algebra
- non-closed polynomial family
- rank-deficient family
- basis-mismatch behavior

No generator fitting from PDE data was added in this milestone.

## Milestone 3 - PDE-Context Diagnostics

Candidate validation now separates algebraic closure from PDE-context evidence.

Closeout:

- multi-row family closure checks no longer imply PDE residual symmetry
- multi-row candidates without finite-transform or residual-preservation evidence conclude at most `partially_validated`
- PDE-context reports use explicit algebraic-only / blocked / not-meaningful language
- single-generator translation validation remains unchanged

## Milestone 4 - Internal Fit Probe

Fit-probe evidence remains diagnostic-only.

Closeout:

- no public fitting helper was added
- no runtime example performs fitting
- no API stability entry promotes multi-generator fitting
- no best-of-sweep promotion path was added

## Milestone 5 - Example And Docs

Implemented:

- added `python -m pdelie.examples.multi_generator_diagnostics`
- added `pdelie.examples.run_multi_generator_diagnostics_example(...)`
- updated README, changelog, roadmap, API stability, release readiness, and public-surface docs

The example uses supplied `GeneratorFamily` objects only and reports diagnostic status.

## Milestone 6 - Release Gate And Readiness

Implemented:

- added compact `tests/test_v0_27_release_gate.py`
- updated CI so the current explicit release gate is `v0_27-release-gate`
- kept full editable `python -m pytest`
- kept package smoke
- bumped package metadata to `0.27.0`
- documented direct `v0.27.0` Git-tag release path

Required checks before tagging:

- `v0_27-release-gate`
- `editable-tests`
- `package-smoke`

Local validation checklist:

- `python -m pytest`
- `python -m build --sdist --wheel`
- all packaged examples
- `python scripts/check_notebooks.py`
- `git diff --check`
