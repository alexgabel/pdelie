"""Every SHA-pinned action's version comment must match its SHA.

The defect this exists for
==========================

``astral-sh/setup-uv`` was pinned at ``# v5.1.0`` while its SHA was actually
``v5.3.1``, and a Dependabot bump to ``v5.4.2`` moved the SHA and left the
comment untouched -- because Dependabot only rewrites a comment it recognises,
and this one had already drifted.

The workflow therefore misstated its own supply chain **by three minor
versions**, and every reader of that line believed something false. It is the
same declaration-versus-execution class as the v0.37 C-5 defect and the v0.38e
equation-form defect, sitting in CI rather than in the library.

What is checked offline, and what needs the network
===================================================

Offline (always): the workflows agree with ``configs/github_action_pins.json``,
one SHA maps to one version, and one version maps to one SHA. That makes a
partial bump -- some occurrences updated, others not -- impossible to merge.

Online (``pytest -m network``): the manifest agrees with GitHub. That is the
only check that can catch a manifest and a workflow being *consistently* wrong,
which is exactly the state this defect was in.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO_ROOT / ".github/workflows"
MANIFEST = REPO_ROOT / "configs/github_action_pins.json"

#: ``uses: owner/repo@<40-hex> # vX.Y.Z``
_PIN = re.compile(
    r"uses:\s*([\w.-]+/[\w.-]+(?:/[\w.-]+)?)@([0-9a-f]{40})\s*#\s*(v[\w.\-+]+)"
)
_USES = re.compile(r"uses:\s*(\S+)")


def _workflow_pins() -> dict[str, str]:
    pins: dict[str, str] = {}
    for path in sorted(WORKFLOWS.rglob("*.yml")):
        for action, sha, version in _PIN.findall(path.read_text()):
            pins[f"{action}@{sha}"] = version
    return pins


def _manifest_pins() -> dict[str, str]:
    return json.loads(MANIFEST.read_text())["pins"]


def test_the_manifest_exists_and_is_strict_json() -> None:
    assert MANIFEST.exists()
    json.dumps(json.loads(MANIFEST.read_text()), allow_nan=False)


def test_every_action_is_sha_pinned() -> None:
    """A floating tag can be repointed by the upstream owner at any time."""
    unpinned: list[str] = []
    for path in sorted(WORKFLOWS.rglob("*.yml")):
        for reference in _USES.findall(path.read_text()):
            if "@" not in reference or not re.fullmatch(r"[0-9a-f]{40}", reference.split("@", 1)[1]):
                unpinned.append(f"{path.name}: {reference}")
    assert not unpinned, f"actions not pinned to a full SHA: {unpinned}"


def test_every_pin_carries_a_version_comment() -> None:
    """A bare SHA is unreadable; the comment is what makes review possible."""
    missing: list[str] = []
    for path in sorted(WORKFLOWS.rglob("*.yml")):
        text = path.read_text()
        for line in text.splitlines():
            if "uses:" not in line or "@" not in line:
                continue
            reference = _USES.search(line)
            if reference is None:
                continue
            target = reference.group(1)
            if (
                "@" in target
                and re.fullmatch(r"[0-9a-f]{40}", target.split("@", 1)[1])
                and not re.search(r"#\s*v[\w.\-+]+", line)
            ):
                missing.append(f"{path.name}: {line.strip()}")
    assert not missing, f"SHA pins with no version comment: {missing}"


def test_the_workflows_match_the_manifest() -> None:
    """A bump must update the manifest in the same commit."""
    workflow = _workflow_pins()
    manifest = _manifest_pins()
    assert workflow == manifest, (
        "the workflows and configs/github_action_pins.json disagree.\n"
        f"  only in workflows: {sorted(set(workflow) - set(manifest))}\n"
        f"  only in manifest : {sorted(set(manifest) - set(workflow))}\n"
        f"  differing comment: "
        f"{sorted(k for k in set(workflow) & set(manifest) if workflow[k] != manifest[k])}\n"
        "Update the manifest in the same commit as the pin bump."
    )


def test_one_sha_maps_to_one_version() -> None:
    """Catches a partial bump: some occurrences updated, others left behind."""
    by_sha: dict[str, set[str]] = {}
    for path in sorted(WORKFLOWS.rglob("*.yml")):
        for action, sha, version in _PIN.findall(path.read_text()):
            by_sha.setdefault(f"{action}@{sha}", set()).add(version)
    conflicting = {key: sorted(v) for key, v in by_sha.items() if len(v) > 1}
    assert not conflicting, (
        f"the same SHA is labelled with different versions: {conflicting}. One of "
        f"them is wrong, and a reader cannot tell which."
    )


def test_one_version_maps_to_one_sha() -> None:
    """Catches the inverse: two SHAs both claiming to be the same release."""
    by_version: dict[tuple[str, str], set[str]] = {}
    for path in sorted(WORKFLOWS.rglob("*.yml")):
        for action, sha, version in _PIN.findall(path.read_text()):
            by_version.setdefault((action, version), set()).add(sha)
    conflicting = {
        f"{action} {version}": sorted(s[:12] for s in shas)
        for (action, version), shas in by_version.items()
        if len(shas) > 1
    }
    assert not conflicting, (
        f"one version label points at two different SHAs: {conflicting}. At most "
        f"one can be that release."
    )


def test_the_manifest_records_why_it_exists() -> None:
    """Without the incident, this file reads as bookkeeping and gets deleted."""
    note = json.loads(MANIFEST.read_text())["note"]
    assert "setup-uv" in note and "v5.1.0" in note, (
        "the manifest no longer records the drift that motivated it"
    )


def test_the_offline_checks_cannot_catch_a_consistently_wrong_pin() -> None:
    """State the limitation, so the network check is not treated as optional.

    Every check above compares the workflows against the manifest and against
    each other. If both are wrong in the same way -- which is exactly the state
    setup-uv was in -- they all pass. Only the network check resolves a SHA to
    its real tag.
    """
    manifest = _manifest_pins()
    assert manifest == _workflow_pins(), "premise: they agree"
    # And that agreement is not evidence about GitHub. Asserted as a statement
    # rather than left implicit in a docstring.
    assert MANIFEST.read_text().count("astral-sh/setup-uv") >= 1


@pytest.mark.network
def test_every_pin_resolves_to_the_version_it_claims() -> None:
    """The only check that can catch a consistently wrong pin.

    Skipped without network. Run it before a release: it is what turns the
    manifest from an internal-consistency record into a true statement.
    """
    import urllib.error
    import urllib.request

    mismatches: list[str] = []
    for key, claimed in sorted(_manifest_pins().items()):
        action, sha = key.rsplit("@", 1)
        owner_repo = "/".join(action.split("/")[:2])
        url = f"https://api.github.com/repos/{owner_repo}/tags?per_page=100"
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                tags = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError) as exc:  # pragma: no cover
            pytest.skip(f"network unavailable: {exc}")
        names = {tag["name"] for tag in tags if tag["commit"]["sha"] == sha}
        if names and claimed not in names:
            mismatches.append(f"{action}@{sha[:12]} claims {claimed}, is {sorted(names)}")
    assert not mismatches, "\n".join(mismatches)
