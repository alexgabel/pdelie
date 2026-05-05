# V0.29.0 Release Readiness

## Decision

`v0.29.0` is ready as a Git-tag-only release.

Release conclusion:

```text
workflow_recipes_and_support_matrix_complete_no_new_numerical_scope
```

## Package Metadata

- package version: `0.29.0`
- git tag: `v0.29.0`
- PyPI/TestPyPI: deferred until `v1.0` or later

Do not publish to TestPyPI or PyPI for `v0.29.0`.

## Public Surface

No runtime API was added.

Documentation and tutorial additions:

- `docs/workflows/`
- `docs/specs/support_matrix.v0_29.json`
- `docs/specs/SUPPORT_MATRIX.md`
- `notebooks/12_dataset_to_downstream_workflow.ipynb`
- `notebooks/13_candidate_to_split_provenance_workflow.ipynb`

## Deferred Scope Confirmed

- no `pdelie.reporting.summarize_workflow_readiness(...)`
- no new numerical scope
- no new runtime helper
- no new PDE
- no file loader or broad adapter
- no multidimensional or nonuniform stable API
- no train/test or leakage-prevention policy
- no KS runtime promotion

## Validation Checklist

Expected release validation:

```bash
python scripts/check_notebooks.py
python -m pytest tests/test_examples.py tests/test_public_api.py tests/test_api_stability_audit.py tests/test_v0_29_release_gate.py -q
sphinx-build -b html -W --keep-going docs docs/_build/html
python -m build --sdist --wheel
git diff --check
```
