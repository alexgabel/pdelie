# V0.29.0 Scope - Workflow Recipes and Support Matrix

`v0.29.0` is a documentation, recipe, and support-matrix release.

It adds no new numerical scope, no runtime helper, no new public API, and no root export.

Release conclusion:

```text
workflow_recipes_and_support_matrix_complete_no_new_numerical_scope
```

## Stable Intent

The release makes the existing `v0.19-v0.28` surface easier to use through three explicit workflows:

1. data readiness
2. candidate validation
3. downstream/export provenance

## Additions

- public `docs/workflows/` pages rendered by Sphinx/Read the Docs
- machine-readable support matrix at `docs/specs/support_matrix.v0_29.json`
- human-readable support matrix at `docs/specs/SUPPORT_MATRIX.md`
- rendered tutorial notebook `notebooks/12_dataset_to_downstream_workflow.ipynb`
- rendered tutorial notebook `notebooks/13_candidate_to_split_provenance_workflow.ipynb`

## Support Matrix Rows

| PDE | Generator | Residual | Vertical slice | Candidate validation | Weak support | External-data readiness |
| --- | --- | --- | --- | --- | --- | --- |
| Heat | yes | yes | yes | yes | frozen weak slice | yes |
| Burgers | yes | yes | yes | yes | frozen weak slice | yes |
| KdV | normalized short-horizon only | yes | yes | yes | no | yes |
| Fisher-KPP | yes | yes | yes | yes | internal weak diagnostic only | yes |
| Advection-diffusion | yes | yes | yes | yes | no | yes |
| KS | no public runtime | no | no | diagnostic/no-go | no | no |

## Deferred Scope

- no `pdelie.reporting.summarize_workflow_readiness(...)`
- no new PDE
- no broad adapter or file-loader API
- no multidimensional, multivariable, or nonuniform-grid stable expansion
- no public KS runtime API
- no weak-form expansion
- no new train/test split or leakage-prevention policy
- no operator, neural, or callable generator API

## Milestone Status

- Milestone 0: COMPLETE
- Milestone 1: COMPLETE
- Milestone 2: COMPLETE
- Milestone 3: COMPLETE
- Milestone 4: COMPLETE
- Milestone 5: COMPLETE
- Milestone 6: COMPLETE
