# V0.7 Prep Playbook

This document is a concrete preparation checklist for the next development cycle after the shipped `v0.6.0` release.

It is **not** the authoritative `v0.7` scope freeze.
The authoritative planning documents remain:

- `ROADMAP.md`
- future `V0_7_SCOPE.md` once frozen
- `PLAN.md` once `v0.7` execution starts

---

## Purpose

`v0.7` is currently the planned structured external-data ingestion release:

> external structured arrays -> canonical `FieldBatch` -> existing PDELie pipeline

The goal of this prep playbook is to make the transition from the completed `v0.6` discovery-utility release into `v0.7` development deliberate and low-noise.

---

## Immediate Release-Boundary Cleanup

These items should be true before meaningful `v0.7` implementation work starts:

- user-facing docs describe the shipped repo as `v0.6`, not `v0.5`
- roadmap docs mark `v0.6` complete and `v0.7` as the next planned step
- exploratory notebooks exist for the shipped `v0.6` surfaces so future ingestion work can be evaluated against known baselines
- release metadata, changelog, and planning docs are mutually consistent

This prep pass addresses the first three directly.

---

## Current Red Flags

These are the main carry-over issues to keep in mind while preparing `v0.7`:

1. README drift:
   the repository README had still been describing the shipped state as `v0.5`

2. Roadmap drift:
   the roadmap had still been presenting `v0.6` as the next release instead of a completed one

3. Example coverage:
   the packaged example remains Heat-only even though the stable slice covers Heat and Burgers

4. Notebook/tooling policy:
   the repo now benefits from exploratory notebooks, but Jupyter itself is still not part of the package/runtime contract

5. External-ingestion contract gap:
   `v0.7` is planned, but the exact acceptance/rejection rules for imported arrays, coordinates, metadata, provenance, and optional dependencies are not frozen yet

6. Discovery-path caution:
   the shipped discovery adapter remains backend-native and intentionally narrow; `v0.7` must not accidentally turn external ingestion into a broad discovery-framework expansion

---

## Recommended V0.7 Milestone 0

Before writing runtime ingestion code, freeze the `v0.7` ingestion contract in docs and tests.

Recommended M0 checklist:

- define the exact public signatures for:
  - `pdelie.data.from_numpy(...)`
  - `pdelie.data.from_xarray(...)`
- define the stable optional-dependency policy for `xarray`
- define required dims and accepted dim aliases
- define required coordinate semantics and monotonicity checks
- define minimum metadata/provenance requirements for imported `FieldBatch`
- define copy/ownership semantics for imported arrays
- define mask / `NaN` acceptance and normalization policy
- define the exact uniform-rectilinear acceptance rules
- define rejection policy for nonuniform, multidimensional, or under-specified inputs
- define parity tests that compare imported structured data against native Heat/Burgers `FieldBatch` behavior

Do not start by writing broad loader code.
Start by freezing the acceptance and rejection rules.

---

## Recommended Early V0.7 Sequence

Suggested order once the prep work is done:

1. freeze `v0.7` scope and M0 contracts
2. add focused tests for accepted and rejected `from_numpy(...)` inputs
3. implement `from_numpy(...)`
4. add parity tests against native Heat/Burgers fields
5. add focused tests for accepted and rejected `from_xarray(...)` inputs
6. implement `from_xarray(...)`
7. add a compact `v0.7` release gate

This keeps `v0.7` aligned with the existing one-axis-per-release policy.

---

## Explicit Guardrails

While preparing `v0.7`, keep these boundaries explicit:

- no PDEBench-specific stable loader
- no The Well adapter
- no HDF5, netCDF, or Zarr stable loader
- no multidimensional stable ingestion
- no nonuniform-grid support
- no broad metadata inference layer
- no weak-form or operator-method expansion
- no stable KdV promotion piggybacked into ingestion work
- no paper-specific private-repo logic in the public library

---

## Tutorials and Evaluation

The exploratory notebooks under `notebooks/` should be treated as the baseline evaluation surface for the shipped `v0.6` runtime layer.

Before `v0.7` changes land, it should remain easy to:

- run the shipped Heat verification example
- run raw vs translation-canonical discovery comparisons
- run robustness sweeps
- check portability round-trips
- compare discovered vs known translation generators
- inspect closure/algebra diagnostics

That baseline is useful because `v0.7` should expand data ingestion without destabilizing the existing symmetry/discovery stack.
