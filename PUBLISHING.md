# Publishing PDELie

> **Status: prepared, not exercised.** The publish path is built, hardened and
> unit-tested, but **PDELie has not been published to TestPyPI or PyPI**, and
> publishing is deferred to v1.0. Nothing in this document has been run against
> a live index. Treat the "first run" checklist as genuinely first-run.

Everything here is `workflow_dispatch`-only. There is no tag-triggered publish
and no automatic upload on merge — a release is an action someone takes
deliberately, not a side effect of merging.

## The one workflow

`.github/workflows/publish.yml` handles both indices via a `target` input
(`testpypi` | `pypi`). There is deliberately **not** a separate
`publish-testpypi.yml`: two workflows that can both upload to an index is twice
the surface holding `id-token: write`, and they drift. The v0.36 plan called for
a second workflow; hardening the existing one was chosen instead, and the
security properties the plan asked for are asserted by
`tests/test_v0_36f_publish_contract.py`.

## What protects the publish path

| Property | How |
|---|---|
| No API tokens anywhere | OIDC trusted publishing via GitHub Environments. No `password:`, no `PYPI_API_TOKEN`. |
| `id-token: write` minimally scoped | Granted to `publish-testpypi` / `publish-pypi` only. The `build` job has `contents: read`. |
| Published artifact == built artifact | `build` writes `SHA256SUMS`; each publish job re-downloads it and runs `sha256sum -c` **before** upload. |
| Every action SHA-pinned | All five actions pinned to a 40-hex commit with a `# vX.Y.Z` comment. A floating tag on the job holding `id-token: write` is a supply-chain hole. |
| No silent no-op | **No `skip-existing`.** Index versions are immutable; a skip would report success having published nothing. A defect means rc2, never an overwrite. |
| PyPI needs a second key | `target: pypi` requires `confirm_pypi=publish-to-pypi` **and** rejects any ref containing `rc`. |

`SHA256SUMS` is uploaded as its own artifact, never into `dist/` — everything in
`dist/` is offered to the index, and a checksum manifest is not a distribution.

## One-time setup, before the first run

1. Register the **trusted publisher** on TestPyPI (and later PyPI): project
   `pdelie`, owner `alexgabel`, repository `pdelie`, workflow `publish.yml`,
   environment `testpypi` (resp. `pypi`).
2. Create the matching GitHub Environments. Add required reviewers on `pypi`.
3. Confirm no `PYPI_API_TOKEN`-style secret exists — trusted publishing does not
   use one, and a leftover token is a live credential nobody is watching.

Registering the publisher is the step most likely to be missed; without it the
upload fails at the end of an otherwise successful run.

## Releasing

```bash
# 1. Version bump + changelog on a release branch, merged as usual.
# 2. Tag the merge commit.
git tag -a v0.36.0 -m "PDELie v0.36.0" && git push origin v0.36.0

# 3. Dispatch. TestPyPI first, always.
gh workflow run publish.yml -f target=testpypi -f git_ref=v0.36.0rc1

# 4. Verify from OUTSIDE the checkout (see below), then:
gh workflow run publish.yml -f target=pypi -f git_ref=v0.36.0 \
  -f confirm_pypi=publish-to-pypi
```

## Post-publish verification

**Run this outside the source checkout.** A smoke test run from the repo root
can import the working tree instead of the installed wheel and prove nothing —
`pdelie/` sits on `sys.path` when the interpreter starts in the repo root, so
the import succeeds whether or not the install did.

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

`pdelie` exposes no `__version__` attribute — use
`importlib.metadata.version("pdelie")`. There are no console-script entry
points, so there is no CLI smoke to run.

### Last verified

Against a **locally built** wheel (not an index), py3.12 / numpy 2.5.1:

| Config | Install | `pip check` | Imported from |
|---|---|---|---|
| base | ok | OK | site-packages |
| `[downstream]` | ok | OK | site-packages |
| `[xarray]` | ok | OK | site-packages |
| `[viz]` | ok | OK | site-packages |
| `[pdebench]` | ok | OK | site-packages |
| `[test]` | ok | OK | site-packages |

## If a release is wrong

Bump to the next rc or patch and publish that. Do not delete and re-upload a
version: indices treat versions as immutable, and anyone who installed the
original keeps a copy that no longer matches the name.
