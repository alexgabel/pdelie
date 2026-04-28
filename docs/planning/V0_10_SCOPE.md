# V0.10 Scope Freeze

## Summary

`v0.10` is the supportability and `v1.0` readiness release for `pdelie`.

Its purpose is:

> harden the existing Heat/Burgers/weak-report/KdV engine into a more supportable public surface before adding more numerical scope.

Stable release definition:

`existing stable Heat/Burgers/weak-report/KdV surfaces -> compact supportability reports -> consistent examples/release gates/docs -> v1.0 readiness`

`v0.10` is not a new numerics release.
It does not add another PDE, weak KdV, broad adapters, multidimensional grids, or operator-facing work.

---

## Stable Scope

Stable `v0.10` scope is limited to supportability work around the surfaces already stable through `v0.9`:

- canonical Heat/Burgers strong paths
- window-indexed weak Heat/Burgers report APIs
- structured `from_numpy(...)` and `from_xarray(...)` ingestion
- normalized periodic short-horizon KdV strong path
- polynomial translation fitting and held-out verification
- existing examples and release gates
- package, publishing, and release-readiness documentation

Committed supportability directions:

- compact runtime reporting helpers over existing residual, fit, verification, and vertical-slice outputs
- consistent example summaries where useful
- API stability audit and accidental-public-surface guards
- CI release-gate cleanup
- package/readiness documentation cleanup for eventual `v1.0` publishing decisions

---

## Public API Policy

No new `v0.10` public API is frozen in M0.

If `v0.10` adds reporting helpers, M1 must freeze their exact names, import paths, return shape, and non-goals before implementation.

Any new `v0.10` reporting helper must be:

- runtime-level, not a canonical object
- deterministic for frozen representative inputs
- JSON-compatible or explicitly documented as runtime-only if NumPy arrays are returned
- scoped to existing stable surfaces
- documented in `API_STABILITY.md` in the same milestone where the public API lands

No root `pdelie` export should be added for new `v0.10` helper APIs unless the scope freeze explicitly justifies it.

---

## Reporting Helper Direction

`v0.10` may add compact reporting helpers for supportability.
Exact helper names and schemas are deferred to M1.

Candidate reporting targets:

- residual diagnostics summaries
- generator fitting summaries
- verification report summaries
- vertical-slice summaries
- release-gate support summaries

Reporting helpers must not:

- redefine canonical object meaning
- make example outputs canonical artifacts
- encode manuscript-specific tables or figures
- hide backend-specific caveats
- broaden numerical scope

---

## Example Consistency

Heat and KdV examples should be made more consistent where that improves supportability.

Example outputs remain runtime smoke summaries.
They are not stable canonical artifact schemas.

Expected properties:

- JSON-serializable plain Python values
- deterministic for frozen example inputs
- compact enough for command-line smoke checks
- explicit about backend and verification classification

---

## API Stability Audit

M0 audits `docs/specs/API_STABILITY.md` only.

Audit result for M0:

- all public APIs through `v0.9` remain documented
- no `v0.10` public API has landed yet
- `API_STABILITY.md` should remain unchanged until reporting helpers or other public APIs actually land

Future `v0.10` milestones must update `API_STABILITY.md` in the same milestone where any public API is added or changed.

---

## CI Cleanup Direction

`v0.10` should reduce release-gate CI sprawl without deleting useful historical tests.

Target direction:

- keep historical release-gate test modules runnable locally
- keep the current release gate visible in CI
- avoid redundant historical release-gate CI jobs unless intentionally retained
- keep full editable tests and package smoke as required release checks
- do not change test semantics just to make CI faster

Exact workflow edits are deferred until the CI cleanup milestone.

---

## Package and Publishing Readiness

`v0.10` should prepare the project for the `v1.0` publishing decision.

Required decision record:

- whether package-index publishing resumes at `v1.0`
- whether `v0.10` remains Git-tag-only
- what local build and wheel-smoke checks are required before any future publishable release
- what CI jobs are required before tagging

No PyPI or TestPyPI publication is added by this scope freeze.

---

## Scope Limits

Stable `v0.10` scope is limited to:

- supportability helpers around existing stable runtime surfaces
- existing canonical objects
- existing scalar 1D uniform rectilinear / periodic regimes
- existing Heat, Burgers, weak Heat/Burgers report, and KdV strong-path surfaces
- documentation and CI release-process cleanup

---

## Explicit Non-goals

Out of stable `v0.10` scope:

- no new PDE
- no weak KdV API
- no new weak derivative API
- no KdV weak residual report
- no broad benchmark adapters
- no PDEBench or The Well adapter work
- no multidimensional grids
- no multivariable systems
- no nonuniform-grid expansion
- no operator-method expansion
- no neural generators
- no manuscript-specific reporting logic
- no new canonical object unless M1 proves a repeated supportability problem cannot be solved with runtime helpers

---

## Milestones

Planned `v0.10` sequence:

- Milestone 0 - supportability scope reset
- Milestone 1 - reporting semantics freeze
- Milestone 2 - reporting helper implementation
- Milestone 3 - example consistency
- Milestone 4 - API stability audit and public-surface guards
- Milestone 5 - CI cleanup and release-gate consolidation
- Milestone 6 - release readiness and documentation alignment

`API_STABILITY.md` is updated only when public APIs land:

- M0 audits it but leaves it unchanged
- M1 may freeze proposed public reporting contracts in planning docs only
- M2 updates it if public reporting helpers land
- later milestones update it only if they add or change public APIs
