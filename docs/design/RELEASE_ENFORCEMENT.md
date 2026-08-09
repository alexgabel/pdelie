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

---

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
| **`release-gate`** | Release-gate manifest replay | **Stable name, no version.** See §4a |

**Not required (advisory):**

- `py314-core-only-advisory` — Python 3.14 forward-compat probe; may fail on
  ecosystem breakage without blocking merges.

The release-gate job name changes at each release. The renaming is itself
required: `v0_37_1-release-gate` → `v0_38_0a1-release-gate` →
The rename-at-each-release policy is **retired**; see §4a.
A protected-branch configuration that references an outdated job name silently
stops enforcing, which is the version-literal drift class this document exists
to prevent. Every release-close PR that renames the job must simultaneously
update the branch-protection required-checks list.

---

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

---

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
  -f 'required_status_checks[contexts][]=release-gate (3.12)' \
  -f 'required_status_checks[contexts][]=release-gate (3.13)' \
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

---

## 4a. Why the release-gate job name is no longer versioned

The job was named for the release — `v0_29-release-gate`, … ,
`v0_38_0b1-release-gate` — and renamed at each cut. The stated rationale was
that a stale required context proves the rename was skipped.

**It deadlocks the release instead.** GitHub matches required status checks by
exact string:

1. protection requires `v0_38_0b1-release-gate (3.12)` and `(3.13)`
2. the rc1 PR renames the job, so those two contexts never report again
3. the PR cannot merge — and `enforce_admins: true` means nobody can override,
   including the maintainer who configured it

Requiring both names does not help: every PR is then missing one. The only exit
was a three-step protection edit — drop the contexts, merge the rename, re-add
them — containing a window where the release gate was **not required at all**,
performed correctly, from memory, at every release.

That is a control whose failure mode is "the repository is bricked until someone
remembers an undocumented sequence of `gh api` calls."

**The name is now `release-gate`, permanently.** Protection never changes again.

The signal that was lost — *did the version get bumped everywhere?* — is better
served by `tests/test_current_release_gate.py`, which asserts `pyproject.toml`,
`docs/conf.py`, `ci.yml`, `README.md`, `CHANGELOG.md` and
`configs/release_gate_manifest.json` all agree. That runs **offline, on every
test invocation**. The protection audit it replaces is `network`-marked and
deselected by default, so it only ever ran when someone remembered — the same
weakness, one level up.

The three job-name guards now match versioned **and** stable forms deliberately,
so a regression surfaces as a wrong value rather than as an empty list. A guard
that reports `[]` when its target disappears is the vacuity defect this
repository has spent v0.38 removing.

---

## 4b. The gate does not pin its interpreter

`scripts/release_gate_local.sh` uses `PYTHON="${PYTHON:-python}"`. On a machine
where bare `python` is 3.11, every Python-dependent sub-gate fails, because the
package requires `>=3.12` — an environment fault presenting as three code
faults.

The cost is not the wasted run. It is that a gate failing for environment
reasons trains the operator to re-run it under a different environment until it
goes green, which is a selection effect operating on the release control itself.

**Closed 2026-08-09.** The gate now reads `requires-python` from
`pyproject.toml`, compares it to the running interpreter, and aborts with exit
**3** before any sub-gate runs — distinct from exit 2 (re-entry) and exit 1 (a
real gate failure). The abort message states *NOTHING WAS MEASURED*, because an
abort that merely prints an error reads like a partial result.

Asserted by `test_the_gate_checks_its_interpreter_before_running_any_subgate`,
including the ordering: the check must precede the first `run_gate` call.

---

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

---

## 6. Hooks are convenience, not enforcement

`.pre-commit-config.yaml` (existing, if present, else add) runs `ruff check` and
`ruff format --check` on staged files. Contributors install with
`pre-commit install`. This is:

- **Fast local feedback**, not a gate.
- **Skippable** with `git commit --no-verify`.
- **Redundant** with the required CI checks — if the hook fires, the CI
  wouldn't have passed anyway; if the hook is skipped, the CI catches it.

The hook is a courtesy to the maintainer. It is not the enforcement mechanism.

---

## 7. The release procedure that avoids the two recurring defects

A release PR runs a single command that produces the same result as CI:

```bash
./scripts/release_gate_local.sh          # exits 0 only if every gate passes
```

**Correction, made by exercising the script.** This section originally specified
the chain below, and two of its links are wrong for this repository:

```bash
python -m ruff check . && \
python -m mypy src/pdelie && \          # <- always exits 1 here
python -m pytest -q && \
python -m sphinx -W -b html docs /tmp/sphinx-out && \
python -m build --sdist --wheel && \
pip install --force-reinstall dist/*.whl && \   # <- clobbers the dev install
python -c "import pdelie; print(pdelie.__version__)"   # <- AttributeError
```

1. **`mypy` always exits 1.** The repository carries a ratcheted baseline of 147
   errors in 29 files, so a gate keyed on mypy's exit status is **permanently
   red** — and a gate that can never pass gets disabled, which is worse than no
   gate at all. The script checks the *fingerprint against the baseline*
   instead, which is the invariant that actually matters, and reports when the
   ratchet has improved so the baseline can be lowered deliberately.

2. **`pip install --force-reinstall` clobbers the editable install.** Run in the
   development environment it replaces the editable `pdelie` with the built
   wheel, and the next local test run then silently measures the wheel rather
   than the working tree. The script installs into a throwaway venv.

3. **`pdelie.__version__` does not exist.** The package exposes no such
   attribute, so the chain's final command raises `AttributeError`. Adding the
   attribute would widen the root surface the v0.38 API freeze locks, to satisfy
   a check; the script reads `importlib.metadata.version("pdelie")` from the
   *installed wheel* instead and compares it against `pyproject`, which is both
   canonical and a stronger assertion — it verifies the artifact carries the
   version the project declares, not merely that it imports.

**All three were found by running the script, not by reading it**, and together
they mean the chain as documented **could never have completed**: three of its
seven links fail on this repository. A procedure that has never been executed is
a proposal, and this one had been cited as a control.

The release-close PR body includes each command's output. The pre-release ritual
is not "I ran the tests"; it is "here is the paste of every gate command's exit
status." The v0.37 close and v0.38.0b1 close both failed because pytest was run
and lint was not — no single-command invariant existed.

A helper script committed to `scripts/release_gate_local.sh` bundles the seven
commands. The release checklist in the readiness doc references it.

---

## 8. Current gaps against this document

Recorded here rather than in the release-readiness doc, because they are
process gaps and not release gaps:

**Amended 2026-08-09**, after checking each against the live repository rather
than against this list. Three of the four were already closed and this section
had not been updated — a stale blocker list either blocks falsely or is ignored
wholesale, and this one was being read as gating rc1.

| gap | status |
|---|---|
| `main` branch protection not applied | **CLOSED** — `enforce_admins=true`, `allow_force_pushes=false`, `required_linear_history=true`, `strict=true`, audited by `tests/test_branch_protection_policy.py` |
| `scripts/release_gate_local.sh` does not exist | **CLOSED** — 138 lines, six sub-gates, contract asserted by `tests/test_release_gate_contract.py` |
| pre-existing pre-commit config not audited | **VOID** — there is no `.pre-commit-config.yaml` in this repository. The gap as written presumed a file that does not exist. If pre-commit is wanted, that is new work, not a reconciliation. |
| `release/*` pattern rule not applied | **OPEN** — only the "Protect main" ruleset exists |

Remaining before `v0.38.0rc1`: the `release/*` ruleset, and nothing else.

The release-gate interpreter gap (§4b) was **not** inherited from this list — it
was found by running the gate — and is now closed.

---

## The release gate is run externally, never from pytest

`scripts/release_gate_local.sh` is invoked **by a human or by CI, from a shell**,
before tagging. It is **never** invoked from inside the test suite.

The script runs the full test suite. A test that invoked it therefore ran the
suite, which ran that test, which invoked the script again. This happened:
`test_the_gate_actually_passes_on_this_tree` recursed **seven levels deep**, each
level loading numpy/scipy/pysindy, and exhausted system swap (40.9 of 42 GB)
before it was killed.

Three defences are in place, and all three are needed:

| | |
|---|---|
| `PDELIE_RELEASE_GATE_RUNNING` | the script refuses to re-enter, exit 2 |
| `test_no_test_executes_the_gate_script` | AST scan; no test may spawn it |
| `addopts = "-m 'not network'"` | markers do **not** deselect without it |

### The gap this leaves, stated plainly

Deleting that test removed the only automated assertion that *the gate passes on
this tree*. That claim genuinely cannot be made from inside the thing the gate
runs — it is not a check that was dropped for convenience, it is one that cannot
exist in that location.

So it is a **release-checklist step**, executed before tagging:

```sh
./scripts/release_gate_local.sh            # full run, no --skip-build
python -m pytest tests/test_branch_protection_policy.py -m network
python scripts/audit_replay_population.py <artifact-dir>
```

`--skip-build` prints `PASSED WITH SKIPS` and is explicitly *not sufficient for a
release tag*. The branch-protection audit is `network`-marked and does not run by
default; **a skipped audit is not a passing audit**, so it is named here rather
than assumed.

Anyone restoring an "assert the gate passes" test in good faith should read this
section first: the recursion is not hypothetical, and the fix is not to make the
test cheaper.

---

## 9. Signature

Written as a policy document. Amendments follow the same rules as
confirmatory-freeze amendments: dated entries, no restatement.
