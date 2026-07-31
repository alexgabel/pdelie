"""v0.36f contract tests: the publish path, asserted without publishing.

PDELie has not been published. Every property the v0.36 plan asked of the
publish workflow is therefore checked statically here, because the alternative
-- finding out during the first real upload -- is the one run where a defect is
least recoverable: index versions are immutable.

Two of these encode findings rather than preferences.

``publish.yml`` was the only workflow in the repository using floating action
tags, and it is the only one granted ``id-token: write``. A floating tag on the
job that can publish is a supply-chain hole in exactly the wrong place.

``skip-existing`` is asserted absent. It turns "this version already exists"
into a green run, which is indistinguishable from a successful publish in every
place a human would look.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github/workflows"
PUBLISH = WORKFLOW_DIR / "publish.yml"
PUBLISHING_DOC = REPO_ROOT / "PUBLISHING.md"

#: ``uses:`` lines must look like this: a 40-hex commit plus a version comment.
_PINNED = re.compile(r"uses:\s+[^@\s]+@[0-9a-f]{40}\s+#\s*\S+")
_ANY_USES = re.compile(r"uses:\s+\S+")

#: The publish jobs. The build job is deliberately not among them.
_PUBLISH_JOBS = ("publish-testpypi", "publish-pypi")


def _strip_comments(source: str) -> str:
    """Drop ``#`` comments so a scan reads directives, not prose about them.

    Every one of these assertions is about what the workflow *does*. A comment
    explaining why ``skip-existing`` is absent contains the string
    ``skip-existing``; a comment explaining that the build job must not hold
    ``id-token: write`` contains ``id-token: write``. Scanning raw text flags
    the explanation as the violation, which is the same mistake
    ``tests/test_forbidden_language.py`` documents at length -- the constraint
    is about what a file *declares*, not what it *mentions*.
    """
    return "\n".join(line.split("#", 1)[0].rstrip() for line in source.splitlines())


def _publish_source() -> str:
    """Directives only. Use :func:`_publish_raw` when comments are the subject."""
    return _strip_comments(PUBLISH.read_text())


def _publish_raw() -> str:
    """Comments included -- the SHA pins are only valid *with* their annotation."""
    return PUBLISH.read_text()


def _job_block(source: str, job: str) -> str:
    """The YAML block for one top-level job, by indentation."""
    lines = source.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"  {job}:"))
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line.strip() and not line.startswith("    ") and not line.startswith("\t"):
            end = index
            break
    return "\n".join(lines[start:end])


# --- supply chain -----------------------------------------------------------


@pytest.mark.parametrize(
    "workflow", sorted(p.name for p in WORKFLOW_DIR.glob("*.yml")), ids=lambda n: n
)
def test_every_action_is_sha_pinned(workflow: str) -> None:
    """Repo-wide. publish.yml was the last holdout and had the most to lose."""
    source = (WORKFLOW_DIR / workflow).read_text()  # raw: the pin needs its comment
    for line in source.splitlines():
        stripped = line.strip()
        if not _ANY_USES.match(stripped):
            continue
        if stripped.startswith("uses: ./"):
            continue  # a local composite action is not a third-party pin
        assert _PINNED.match(stripped), (
            f"{workflow}: not SHA-pinned with a version comment -> {stripped}"
        )


def test_publish_workflow_holds_no_credentials() -> None:
    """Trusted publishing uses OIDC; a token here would be a live credential."""
    source = _publish_source().lower()
    for forbidden in ("password:", "api_token", "api-token", "pypi_token", "twine_password"):
        assert forbidden not in source, f"publish.yml references {forbidden!r}"


def test_id_token_is_scoped_to_the_publishing_jobs_only() -> None:
    source = _publish_source()
    assert "id-token: write" not in _job_block(source, "build"), (
        "the build job must not be able to mint an OIDC token"
    )
    for job in _PUBLISH_JOBS:
        assert "id-token: write" in _job_block(source, job), job


def test_no_skip_existing() -> None:
    """A skipped upload is a green run that published nothing."""
    assert "skip-existing" not in _publish_source()
    assert "skip_existing" not in _publish_source()


# --- artifact integrity -----------------------------------------------------


def test_build_job_hashes_its_artifacts() -> None:
    build = _job_block(_publish_source(), "build")
    assert "sha256sum dist/*" in build
    assert "SHA256SUMS" in build


def test_checksum_manifest_is_not_shipped_inside_dist() -> None:
    """Everything in dist/ is offered to the index; a manifest is not a dist."""
    build = _job_block(_publish_source(), "build")
    assert "path: SHA256SUMS" in build
    assert "path: dist/SHA256SUMS" not in build


@pytest.mark.parametrize("job", _PUBLISH_JOBS)
def test_publish_jobs_verify_hashes_before_upload(job: str) -> None:
    """The uploaded artifact must be the built artifact, checked not assumed."""
    block = _job_block(_publish_source(), job)
    assert "sha256sum -c SHA256SUMS" in block, job
    verify = block.index("sha256sum -c SHA256SUMS")
    publish = block.index("gh-action-pypi-publish")
    assert verify < publish, f"{job}: hash check must precede the upload"


@pytest.mark.parametrize("job", _PUBLISH_JOBS)
def test_publish_jobs_download_both_artifacts(job: str) -> None:
    block = _job_block(_publish_source(), job)
    assert "name: dist" in block, job
    assert "name: checksums" in block, job


# --- release-shape guards ---------------------------------------------------


def test_pypi_requires_confirmation_and_rejects_release_candidates() -> None:
    source = _publish_source()
    assert "publish-to-pypi" in source
    assert "*rc*" in source, "an rc ref must not reach production PyPI"


def test_publish_is_manual_only() -> None:
    """No tag trigger, no publish-on-merge."""
    source = _publish_source()
    header = source.split("jobs:", 1)[0]
    assert "workflow_dispatch:" in header
    assert "push:" not in header
    assert "release:" not in header


# --- documentation ----------------------------------------------------------


def test_publishing_doc_exists_and_states_the_unpublished_status() -> None:
    """The doc must not read as though the path has been exercised."""
    text = PUBLISHING_DOC.read_text()
    assert "has not been published" in text
    assert "deferred to v1.0" in text


def test_publishing_doc_enumerates_every_extra() -> None:
    """Six install configurations: base plus every declared extra.

    If an extra is added and the verification list is not, the release is
    verified against a subset of what it ships.
    """
    metadata = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
    extras = set(metadata["project"].get("optional-dependencies", {}))
    text = PUBLISHING_DOC.read_text()
    for extra in extras:
        assert f"[{extra}]" in text, f"PUBLISHING.md does not verify the {extra!r} extra"
    assert len(extras) + 1 == 6, (
        f"the documented 'six install configurations' is now {len(extras) + 1}; "
        f"update PUBLISHING.md and this assertion together"
    )


def test_publishing_doc_warns_against_verifying_inside_the_checkout() -> None:
    """The failure mode that makes a smoke test prove nothing."""
    text = PUBLISHING_DOC.read_text()
    assert "outside the source checkout" in text
    assert "site-packages" in text
