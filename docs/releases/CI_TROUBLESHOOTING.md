# CI Troubleshooting

Operational reference for common CI failure modes. This document is advisory; it does not change package semantics, release scope, or stable contracts.

## `Failed to resolve action download info. Error: Service Unavailable`

**What it looks like:** an early job log that reaches `Prepare all required actions` → `Getting action download info` and then reports `503 Service Unavailable` after two retries.

**What it means:** transient outage on GitHub's Actions infrastructure. The runner has already provisioned the OS image and the `GITHUB_TOKEN` — the failure is at the step where it fetches the tarball metadata for an action referenced in the workflow (`actions/checkout@...`, `actions/setup-python@...`, `actions/upload-artifact@...`). None of those actions live in this repo; the 503 comes from GitHub's marketplace/registry endpoint.

**What it is not:** a bug in `.github/workflows/ci.yml`. The workflow file is fine. Editing it will not resolve the outage.

**How to respond, in order:**

1. **Check GitHub status.** Visit https://www.githubstatus.com/ and look at the "Actions" component. If it's degraded or an incident is open, that is the confirmed cause; wait for the incident to close.
2. **Re-run the failed jobs.** Once the incident clears, from the PR page click "Re-run failed jobs", or from the CLI:
   ```bash
   gh run list --workflow=ci.yml --branch=<branch> --limit=3
   gh run rerun <run-id> --failed
   ```
3. **Do not force-push to re-trigger.** A force-push closes the current run and starts a fresh one, which is more expensive and identical in outcome to a re-run. Force-push only if a real code change is needed.
4. **Do not disable job dependencies to work around it.** If `docs-build` blocks a merge and it 503s at action resolution, the answer is a re-run, not to skip the check.

## Why the workflow pins actions by SHA

Every first-party action referenced in `.github/workflows/ci.yml` is pinned by full commit SHA with a trailing `# vX.Y.Z` version comment:

```yaml
- uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1
- uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0
- uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4.6.2
```

Reasons:

- **Security hardening.** A moving tag like `@v4` can be re-pointed to a different commit by the action's maintainer. SHA pinning removes that trust surface. GitHub's official guidance recommends this for third-party actions and treats it as best practice for first-party ones as well.
- **Reproducibility.** Two runs of the same commit resolve to the same action bytes forever, regardless of upstream retagging.
- **Modest resilience against tag-resolution outages.** When GitHub's tag-resolution endpoint 503s, a SHA-pinned reference can (sometimes) skip that lookup step. It does not help if the tarball-download endpoint itself is down.

The pins are kept fresh by Dependabot per `.github/dependabot.yml` — a weekly Monday PR opens whenever a pinned action publishes a new **patch or minor** release. Major-version bumps (`X.0.0` breaks) are explicitly ignored by the Dependabot config and stay a manual maintenance task, because GitHub Actions major bumps have a history of cross-API breaks (`upload-artifact` v3 → v4 broke the artifact API in Dec 2024; `checkout` v3 → v4 required a Node 20 runner). To take a major bump, a maintainer reads the action's changelog, updates the SHA and version comment in `.github/workflows/ci.yml` directly, and reviews the PR themselves.

## Other common CI failure modes

- **`pip install` hangs or 5xxs.** The workflow already wraps installs in a `retry 3` shell function. If that runs out of retries, the fix is the same: check status, re-run the failed job.
- **`docs-build` fails with `WARNING: document isn't included in any toctree`.** Sphinx is built with `-W --keep-going`, so any new markdown doc must be added to the appropriate `docs/*/index.rst` toctree in the same PR.
- **`lint` (blocking as of v0.30.1a) reports ruff violations.** Reproduce locally with `python -m ruff check .` and either fix the code or add a documented per-file ignore to `[tool.ruff.lint.per-file-ignores]` in `pyproject.toml`.
- **Advisory `typecheck` or `coverage` red.** Both are `continue-on-error: true` through v0.30.1a and do not block merges. Promotion to blocking is scheduled per `docs/design/V0_30_HYGIENE_AUDIT.md` (`v0.30.1b` for coverage; `v0.30.1c-k` for mypy scope broadening).

## Related documents

- `.github/workflows/ci.yml` — the workflow itself.
- `.github/dependabot.yml` — the automated action-pin refresh.
- `docs/design/V0_30_HYGIENE_AUDIT.md` — advisory-to-blocking promotion schedule for `lint` / `typecheck` / `coverage`.
- `docs/releases/PUBLISHING.md` — release cadence and Git-tag-only policy.
