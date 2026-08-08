# Release Enforcement

**Purpose.** Prevent the two recurring pre-release defect classes:

1. A release commit that builds but fails the repository's own lint/type/test
   contract (v0.37 close, v0.38.0b1 close).
2. A hard-coded active-version literal drifting between releases (v0.33 README
   pin, v0.38.0b1 release-gate literals).

Local pre-commit hooks were the previously-proposed fix. They are not the
enforcement boundary because a hook is skippable and a checklist is ignorable.
The enforcement boundary is a **protected branch with required status checks
enforced against every writer, including administrators**.

This document specifies the protection settings, the required checks, and the
`gh api` invocation that installs them. Pre-commit/pre-push hooks are retained
as developer convenience only.

## 1. Scope

Branches protected:

- `main`
- `release/*` (matched by the pattern `release/*`)

Direct push refused for all non-admin contributors. Direct push refused for
admin contributors by `enforce_admins: true` — the maintainer's admin privilege
does not silently bypass the protection they configured.

## 2. Required status checks

The following checks must report success on the PR head SHA before a merge is
permitted. Check names match the canonical CI job names in
[`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).

| Check | Enforces | Notes |
|---|---|---|
| `lint` | `ruff check .` | Repeated defect: release commit not gated on lint |
| `typecheck` | `mypy src/pdelie` at ratchet 147/29 | Fingerprint ratchet |
| `coverage` | `pytest --cov` at fail_under ≥ 85 | Blocking since v0.37 |
| `docs-build` | `sphinx -W -b html` | Warnings-as-errors |
| `editable-tests` | Full suite in editable install | Cross-check against wheel behavior |
| `package-smoke` | Clean-env wheel install + import | Distribution-shape check |
| **`<current>-release-gate`** | Release-gate manifest replay | Current name is `v0_38_0b1-release-gate`; renamed at each release |

**Not required (advisory):**

- `py314-core-only-advisory` — Python 3.14 forward-compat probe; may fail on
  ecosystem breakage without blocking merges.

The release-gate job name changes at each release. The renaming is itself
required: `v0_37_1-release-gate` → `v0_38_0a1-release-gate` →
`v0_38_0b1-release-gate` → `v0_38_0rc1-release-gate` → `v0_38_0-release-gate`.
A protected-branch configuration that references an outdated job name silently
stops enforcing, which is the version-literal drift class this document exists
to prevent. Every release-close PR that renames the job must simultaneously
update the branch-protection required-checks list.

## 3. Additional required conditions

- `require_pull_request_reviews`: for a solo-maintainer project, this is set
  with `required_approving_review_count: 0` and `dismiss_stale_reviews: true`.
  The workflow is that CI is the gatekeeper, not human review. The setting
  exists so that direct push is refused; it is not a human-review requirement.
- `require_linear_history: true`. Merge commits into `main` allowed only via
  the PR merge queue or squash-merge; no direct pushes, no force-pushes.
- `allow_force_pushes: false`. Absolute.
- `allow_deletions: false`. Absolute for `main`; also for `release/*` until the
  next release cycle opens.
- `required_conversation_resolution: true`. Review comments must be resolved
  before merge, so a substantive concern raised in a PR cannot be merged past.

## 4. Installation via `gh api`

Executed by the maintainer against the current repository. Requires the
authenticated user to have admin rights on the repository.

```bash
# Set the required checks for main.
gh api \
  -X PUT \
  repos/alexgabel/pdelie/branches/main/protection \
  -f required_status_checks[strict]=true \
  -f 'required_status_checks[contexts][]=lint' \
  -f 'required_status_checks[contexts][]=typecheck' \
  -f 'required_status_checks[contexts][]=coverage' \
  -f 'required_status_checks[contexts][]=docs-build' \
  -f 'required_status_checks[contexts][]=editable-tests' \
  -f 'required_status_checks[contexts][]=package-smoke' \
  -f 'required_status_checks[contexts][]=v0_38_0b1-release-gate' \
  -f enforce_admins=true \
  -f required_pull_request_reviews[required_approving_review_count]=0 \
  -f required_pull_request_reviews[dismiss_stale_reviews]=true \
  -f 'restrictions=' \
  -f required_linear_history=true \
  -f allow_force_pushes=false \
  -f allow_deletions=false \
  -f required_conversation_resolution=true
```

For `release/*` branches, apply the same via a branch-protection rule keyed to
the pattern `release/*` (GitHub web UI or the equivalent `gh api` call against
the `rulesets` endpoint).

## 5. What this does NOT enforce

- **The commit itself failing lint locally.** If the maintainer runs
  `git commit` on a dirty tree and the pre-push hook is skipped, the commit
  exists locally with lint failures. It does not reach `main` because required
  status checks refuse the PR merge. The local commit's defective state does
  not enter the release history. If a release process depends on a local
  commit-SHA before it reaches CI (e.g., tagging a local commit and pushing
  the tag), that process must itself run the required checks locally first —
  see §7.

- **Force-pushing a release tag.** Tags are not branches. GitHub does not
  provide native branch-style protection for tags. Tag hygiene is enforced by
  convention (`git tag -F <file>` for annotations, no `--force`), by the release
  workflow, and by the tag-pointing invariants required in the release-readiness
  doc (support-matrix entry, CHANGELOG entry, readiness file, exact
  dereferenced commit). A rewritten tag is caught by the release-close PR's
  cross-reference audit.

## 6. Hooks are convenience, not enforcement

`.pre-commit-config.yaml` (existing, if present, else add) runs `ruff check` and
`ruff format --check` on staged files. Contributors install with
`pre-commit install`. This is:

- **Fast local feedback**, not a gate.
- **Skippable** with `git commit --no-verify`.
- **Redundant** with the required CI checks — if the hook fires, the CI
  wouldn't have passed anyway; if the hook is skipped, the CI catches it.

The hook is a courtesy to the maintainer. It is not the enforcement mechanism.

## 7. The release procedure that avoids the two recurring defects

A release PR runs a single command that produces the same result as CI:

```bash
# Runs the same checks CI runs, in the same order, exits nonzero on any failure.
python -m ruff check . && \
python -m mypy src/pdelie && \
python -m pytest -q && \
python -m sphinx -W -b html docs /tmp/sphinx-out && \
python -m build --sdist --wheel && \
pip install --force-reinstall dist/*.whl && \
python -c "import pdelie; print(pdelie.__version__)"
```

The release-close PR body includes each command's output. The pre-release ritual
is not "I ran the tests"; it is "here is the paste of every gate command's exit
status." The v0.37 close and v0.38.0b1 close both failed because pytest was run
and lint was not — no single-command invariant existed.

A helper script committed to `scripts/release_gate_local.sh` bundles the seven
commands. The release checklist in the readiness doc references it.

## 8. Current gaps against this document

Recorded here rather than in the release-readiness doc, because they are
process gaps and not release gaps:

- **`main` branch protection not currently applied** as specified in §4. To be
  applied by the maintainer via `gh api` before the next release-close PR
  merges.
- **`release/*` pattern rule not currently applied.** To be added via the
  rulesets endpoint or web UI.
- **`scripts/release_gate_local.sh` does not exist.** To be added as a small,
  reviewable script.
- **Pre-existing pre-commit config not audited** against the ruff/mypy versions
  the CI uses. To be reconciled.

None of these gaps affect the v0.38.0b1 tag. They must be closed before
`v0.38.0-rc1` is cut, per Blocker 2 of the leadership counter-assessment.

## 9. Signature

Written as a policy document. Amendments follow the same rules as
confirmatory-freeze amendments: dated entries, no restatement.
