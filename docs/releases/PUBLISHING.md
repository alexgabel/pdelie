# Publishing

This document defines the conservative release and publishing workflow for `pdelie`.

It is operational only. It does not change package semantics, release scope, or stable contracts.

## Source Of Truth

Release metadata comes from:

- `pyproject.toml` for the package version and package metadata
- `CHANGELOG.md` for release notes
- `docs/releases/V0_X_RELEASE_READINESS.md` for the release checklist and final release readiness

These files must be aligned before any release candidate or final release is published.

## Recommended Publishing Model

`pdelie` should use GitHub Actions trusted publishing with OIDC for both TestPyPI and PyPI.

Why this is the default:

- no long-lived API tokens need to be stored in repository secrets
- publication is tied to the repository workflow identity
- GitHub environments can add an extra approval layer for final PyPI publication

This repository does not store account-specific publishing credentials. The workflow assumes trusted publishing is configured externally.

## Release Policy

`pdelie` uses:

- release candidates: `X.Y.ZrcN`
- final releases: `X.Y.Z`

Guiding rules:

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
ls -1 dist
~~~

Expected local checks:

- the package builds successfully
- the stable example still runs
- `dist/` contains the expected `sdist` and wheel for the release version

For a stricter local smoke pass, install the wheel into a clean virtual environment before publishing.

## Release Candidate Flow

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

## Final Release Flow

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
