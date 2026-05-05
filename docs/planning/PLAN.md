# PDELie - Execution Plan (V0.29)

**Status:** COMPLETE

**V0.29 is complete as the workflow recipes and support matrix release**

This file is the completed execution record for the `v0.29` release series.

## Release Theme

`v0.29` consolidates the existing `v0.19-v0.28` surface into explicit user workflows and a machine-readable support matrix. It adds no numerical scope, no runtime helper, no new public API, and no root export.

Decision label:

```text
workflow_recipes_and_support_matrix_complete_no_new_numerical_scope
```

## Implemented Surfaces

- `docs/workflows/` with recipe pages for data readiness, candidate validation, downstream/export provenance, Dataset-to-downstream, and candidate-to-split-provenance workflows
- `docs/specs/support_matrix.v0_29.json` as the machine-readable support matrix
- `docs/specs/SUPPORT_MATRIX.md` as the human-readable support matrix
- `notebooks/12_dataset_to_downstream_workflow.ipynb`
- `notebooks/13_candidate_to_split_provenance_workflow.ipynb`

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE

Authoritative scope:

- `docs/planning/V0_29_SCOPE.md`

## Public-Surface Audit

Confirmed:

- no `pdelie.reporting.summarize_workflow_readiness(...)`
- no new runtime API
- no new root export
- no new PDE or numerical regime
- no file loader, broad adapter, metadata inference engine, resampling API, multidimensional/nonuniform API, train/test policy, KS runtime API, neural/callable API, or operator API landed

## Release Gate and Readiness

Implemented:

- `tests/test_v0_29_release_gate.py`
- CI `v0_29-release-gate`
- package metadata bump to `0.29.0`
- Git-tag-only release-readiness docs; PyPI/TestPyPI remain deferred until `v1.0` or later
