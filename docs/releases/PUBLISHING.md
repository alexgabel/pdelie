# Publishing

This document defines the conservative release and publishing workflow for `pdelie`.

It is operational only. It does not change package semantics, release scope, or stable contracts.

## Source Of Truth

Release metadata comes from:

- `pyproject.toml` for the package version and package metadata
- `CHANGELOG.md` for release notes
- `docs/releases/V0_X_RELEASE_READINESS.md` for the release checklist and final release readiness

These files must be aligned before any release candidate or final release is published.

## V0.x Package-Index Deferral

For the current `v0.x` series, including `v0.29.0`, `v0.30.0`, `v0.31.0`, `v0.32.0`, `v0.33.0`, `v0.34.0`, `v0.35.0`, and `v0.36.0`, release completion means:

- metadata, docs, tests, build, and wheel-smoke checks pass
- the release PR is merged
- the merged commit is tagged in Git as the final version

`v0.29.0` through `v0.36.0` are intentionally Git-tag-only releases.
Do not publish to TestPyPI or PyPI for any of them.

**v0.36 note.** An earlier plan targeted TestPyPI at `v0.36`. That was
superseded: publication stays deferred to `v1.0`. v0.36f built and hardened
the path without exercising it — see *Publish-path hardening* below.

Package-index publishing through TestPyPI or PyPI is deferred until `v1.0` or later.
The publishing model below remains the intended future package-index workflow once publication is re-enabled.

## Future Publishing Model (`v1.0` Or Later)

`pdelie` should use GitHub Actions trusted publishing with OIDC for both TestPyPI and PyPI.

Why this is the default:

- no long-lived API tokens need to be stored in repository secrets
- publication is tied to the repository workflow identity
- GitHub environments can add an extra approval layer for final PyPI publication

This repository does not store account-specific publishing credentials. The workflow assumes trusted publishing is configured externally.

## Future Package-Index Release Policy (`v1.0` Or Later)

`pdelie` uses:

- release candidates: `X.Y.ZrcN`
- final releases: `X.Y.Z`

Guiding rules once package-index publishing is re-enabled:

- release candidates go to **TestPyPI only**
- final releases go to **PyPI only**
- a final release should be functionally identical to its most recent release candidate unless a real release blocker was found

## Trigger Policy

Publishing is manual-only.

This repository does **not** publish on ordinary `push` or `pull_request` events.

The publishing workflow uses `workflow_dispatch` only, with these targets:

- `target=testpypi`
  - intended for release candidates and pre-release validation
  - requires an explicit `git_ref`
- `target=pypi`
  - intended for final releases only
  - requires an explicit final tag/ref plus an explicit confirmation input

PyPI publication is therefore guarded in two ways:

- the ref must be a final tag/ref, not an `rc` tag
- the manual dispatch must include the expected confirmation phrase

## What Is Automated vs Manual

Automated by workflow:

- checkout of the requested git ref
- one build of `sdist` and `wheel`
- artifact upload
- publication to the selected package index

Manual outside the workflow:

- choose and create the release candidate or final release ref/tag
- verify release metadata is aligned
- invoke the workflow with the correct target and ref
- configure trusted publishing on TestPyPI and PyPI
- create GitHub environments and reviewers if desired

## Local Release Path

From a clean checkout of the intended release commit:

~~~bash
git checkout <release-ref>
git clean -fdx

python -m pytest
python -m build --sdist --wheel
python -m pdelie.examples.heat_vertical_slice
python -m pdelie.examples.kdv_vertical_slice
python -m pdelie.examples.kdv_scope_decision
python -m pdelie.examples.data_ecosystem_feasibility
python -m pdelie.examples.orbit_coverage_diagnostics
python -m pdelie.examples.invariant_workflow_summary
python -m pdelie.examples.split_leakage_provenance
python -m pdelie.examples.weak_form_supportability
ls -1 dist
~~~

Expected local checks:

- the package builds successfully
- the stable examples still run
- `dist/` contains the expected `sdist` and wheel for the release version

For a stricter local smoke pass, install the wheel into a clean virtual environment before publishing.

## Future Release Candidate Flow (`v1.0` Or Later)

Use this for `X.Y.ZrcN` releases:

1. align `pyproject.toml`, `CHANGELOG.md`, and the relevant release-readiness note
2. run the local release path
3. merge the release-hardening PR
4. create the release-candidate tag
5. run the publish workflow manually with:
   - `target=testpypi`
   - `git_ref=<rc tag>`
6. verify installation from TestPyPI
7. hold the soak window

Normal policy:

- do **not** publish release candidates to PyPI

## Future Final Release Flow (`v1.0` Or Later)

Use this for `X.Y.Z` releases:

1. confirm the final release metadata is aligned
2. confirm the release candidate soak window is complete or the release blocker is resolved
3. run the local release path again on the final release commit/tag if needed
4. create the final release tag
5. run the publish workflow manually with:
   - `target=pypi`
   - `git_ref=<final tag>`
   - `confirm_pypi=publish-to-pypi`
6. verify installation from PyPI

Normal policy:

- publish final releases to PyPI only after tag creation and release checks pass

## GitHub Actions Workflow Shape

The repository should contain one publishing workflow:

- `.github/workflows/publish.yml`

Expected behavior:

- `workflow_dispatch` only
- build once
- upload `dist/` artifacts
- publish to TestPyPI or PyPI in separate guarded jobs
- use trusted publishing via `pypa/gh-action-pypi-publish`

This workflow is release infrastructure, not a general CI job.

## Publish-Path Hardening (v0.36f)

The path below was built, hardened and unit-tested in v0.36f. **It has never been
run against a live index.** Treat the first run as genuinely first-run.

One workflow, not two. The v0.36 plan called for a separate
`publish-testpypi.yml`; that was rejected in favour of hardening `publish.yml`,
consistent with the single-workflow shape this document already required. Two
workflows able to upload is twice the surface holding `id-token: write`, and
they drift.

| Property | How |
|---|---|
| No API tokens | OIDC trusted publishing via GitHub Environments. No `password:`, no `PYPI_API_TOKEN`. |
| `id-token: write` minimally scoped | Publish jobs only. The `build` job has `contents: read`. |
| Published artifact == built artifact | `build` writes `SHA256SUMS`; each publish job re-downloads it and runs `sha256sum -c` **before** upload. |
| Every action SHA-pinned | All five pinned to a 40-hex commit with a `# vX.Y.Z` comment. `publish.yml` was the last workflow on floating tags and the only one with `id-token: write`. |
| No silent no-op | **No `skip-existing`.** Index versions are immutable; a skip reports success having published nothing. A defect means rc2, never an overwrite. |
| PyPI needs a second key | `target: pypi` requires `confirm_pypi=publish-to-pypi` and rejects any ref containing `rc`. |

`SHA256SUMS` is uploaded as its own artifact, never into `dist/` — everything in
`dist/` is offered to the index, and a checksum manifest is not a distribution.

`tests/test_v0_36f_publish_contract.py` asserts all of the above. The assertions
are mutation-tested: adding `skip-existing`, unpinning an action, granting
`id-token` to the build job, or removing the hash verification each fail exactly
one test.

## Post-Publish Verification

**Run this outside the source checkout.** A smoke test run from the repo root
imports the working tree instead of the installed wheel and proves nothing —
`pdelie/` is on `sys.path` when the interpreter starts there, so the import
succeeds whether or not the install did.

All six install configurations must pass on a fresh interpreter:

```bash
cd "$(mktemp -d)"                     # <- outside the checkout
for cfg in "" "[downstream]" "[xarray]" "[viz]" "[pdebench]" "[test]"; do
  uv venv --python 3.12 --seed ./v --quiet
  uv pip install --python ./v/bin/python -q "pdelie${cfg}==<version>"
  ./v/bin/python -m pip check
  ./v/bin/python -c "
import importlib.metadata as m, pdelie, pathlib
p = pathlib.Path(pdelie.__file__).resolve()
assert 'site-packages' in p.parts, f'imported the working tree: {p}'
print(m.version('pdelie'))"
  rm -rf ./v
done
```

Two things the v0.36 plan assumed that are not true: `pdelie` exposes no
`__version__` attribute — use `importlib.metadata.version` — and there are no
console-script entry points, so there is no CLI smoke to run.

### Last verified

Against a **locally built** wheel, not an index. py3.12 / numpy 2.5.1:

| Config | Install | `pip check` | Imported from |
|---|---|---|---|
| base | ok | OK | site-packages |
| `[downstream]` | ok | OK | site-packages |
| `[xarray]` | ok | OK | site-packages |
| `[viz]` | ok | OK | site-packages |
| `[pdebench]` | ok | OK | site-packages |
| `[test]` | ok | OK | site-packages |

## Required External Setup

Trusted publishing cannot be completed from repository files alone.

Manual setup still required:

### TestPyPI

- create the `pdelie` project on TestPyPI if it does not already exist
- configure a trusted publisher for this repository and workflow
- if using a GitHub environment, create `testpypi`

### PyPI

- create the `pdelie` project on PyPI if it does not already exist
- configure a trusted publisher for this repository and workflow
- create the GitHub environment `pypi`
- optionally require reviewers for the `pypi` environment

### GitHub

- ensure Actions and OIDC are available for the repository
- if environment protection is desired, configure it in repository settings

This repo intentionally does not document account-specific IDs, usernames, or secrets.

## Branch Protection And Required Checks

No branch-protection update is needed by default for the publishing workflow.

Reason:

- the publishing workflow is manual-only
- it is not a pull-request merge gate

If stronger control is desired later, use GitHub environment protection and reviewers for `pypi` rather than making the publishing workflow a required branch check.
