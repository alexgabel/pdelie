"""The branch-protection configuration is audited against the GitHub API.

Why this is a test and not a paragraph in CONTRIBUTING.md
========================================================

A release-enforcement fix was pushed **directly to main** during the v0.38.0b1
close. The change itself was right; the push bypassed exactly the control the
change was about. A prose statement would not have prevented it and would not
have detected it afterwards.

The settings below are the control. This module checks they are still in place,
so a silent relaxation -- someone disabling ``enforce_admins`` to unblock
themselves and forgetting to restore it -- fails a test rather than going
unnoticed until the next incident.

Network, and why it is not skipped silently
===========================================

This needs the GitHub API, so it carries ``@pytest.mark.network`` and does not
run by default. **A skipped audit is not a passing audit**, and the release
procedure requires running it -- ``scripts/release_gate_local.sh`` does not
invoke it, so it is named explicitly in the release checklist instead of being
assumed.
"""

from __future__ import annotations

import json
import subprocess

import pytest

REPO = "alexgabel/pdelie"

#: Checks that must pass before anything merges to main.
#:
#: Deliberately excludes ``replay (...)`` -- those are ``workflow_dispatch``
#: only, so requiring them would block every PR on a lane that never runs for a
#: PR. It also excludes ``py314-core-only-advisory``, which is advisory by name.
REQUIRED_CHECKS = {
    "lint",
    "typecheck",
    "coverage",
    "docs-build",
    "package-smoke",
    "editable-tests (3.12)",
    "editable-tests (3.13)",
}

#: The release-gate job name is **stable** and carries no version.
#:
#: It used to be versioned -- ``v0_38_0b1-release-gate`` -- on the theory that a
#: stale required context would prove a rename had been skipped. In practice it
#: created a deadlock at every release cut:
#:
#:   1. protection requires ``v0_38_0b1-release-gate (3.12)`` and ``(3.13)``
#:   2. the rc1 PR renames the job, so those contexts never report again
#:   3. the PR cannot merge, and ``enforce_admins: true`` means nobody can
#:      override it -- including the maintainer who set the rule
#:
#: Requiring both names does not help: every PR is then missing one. The only
#: exit was a three-step protection edit with a window where the release gate
#: was not required at all, performed correctly, every release, from memory.
#:
#: The signal that was lost -- "did the version get bumped everywhere?" -- is
#: better served by ``tests/test_current_release_gate.py``, which asserts
#: pyproject, ``docs/conf.py``, ``ci.yml`` and the release-gate manifest agree.
#: That runs offline on every test invocation, where this audit is
#: ``network``-marked and deselected by default.
RELEASE_GATE_JOB = "release-gate"


def _protection() -> dict:
    result = subprocess.run(
        ["gh", "api", f"repos/{REPO}/branches/main/protection"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"GitHub API unavailable: {result.stderr.strip()[:120]}")
    return json.loads(result.stdout)


@pytest.mark.network
def test_admins_cannot_bypass_protection() -> None:
    """The load-bearing setting.

    Without it the maintainer's admin privilege silently bypasses the
    protection they configured, and the enforcement is theatrical. This is the
    specific control the direct-to-main push would have hit.
    """
    assert _protection()["enforce_admins"]["enabled"] is True


@pytest.mark.network
def test_every_required_check_is_required() -> None:
    contexts = set(_protection()["required_status_checks"]["contexts"])
    missing = REQUIRED_CHECKS - contexts
    assert not missing, f"no longer required on main: {sorted(missing)}"


@pytest.mark.network
def test_the_release_gate_is_required_under_its_stable_name() -> None:
    """And that no *versioned* gate context has crept back in.

    A versioned context is not merely untidy: protection matches by exact
    string, so the moment the job is renamed the required check stops reporting
    and every PR blocks with no override available.
    """
    contexts = set(_protection()["required_status_checks"]["contexts"])
    gate_contexts = {c for c in contexts if "release-gate" in c}
    assert gate_contexts, "no release-gate check is required on main"

    versioned = {c for c in gate_contexts if not c.startswith(RELEASE_GATE_JOB)}
    assert not versioned, (
        f"protection requires versioned release-gate contexts {sorted(versioned)}. "
        f"These deadlock the next release cut: renaming the job stops them "
        f"reporting, and enforce_admins leaves no way through. Replace them with "
        f"{RELEASE_GATE_JOB!r}."
    )


@pytest.mark.network
def test_history_cannot_be_rewritten() -> None:
    """A force push to main would destroy the tagged release evidence."""
    protection = _protection()
    assert protection["allow_force_pushes"]["enabled"] is False
    assert protection["allow_deletions"]["enabled"] is False


@pytest.mark.network
def test_linear_history_is_required() -> None:
    assert _protection()["required_linear_history"]["enabled"] is True


@pytest.mark.network
def test_a_branch_must_be_current_before_merging() -> None:
    """Otherwise a PR can pass against a main it has not seen."""
    assert _protection()["required_status_checks"]["strict"] is True


# --------------------------------------------------------------------------
# Offline: the expectations themselves must stay coherent
# --------------------------------------------------------------------------


def test_the_required_set_excludes_dispatch_only_lanes() -> None:
    """Requiring a dispatch-only lane would block every PR permanently.

    Asserted offline so the reasoning survives even when the audit is skipped.
    """
    for name in REQUIRED_CHECKS:
        assert not name.startswith("replay "), (
            f"{name!r} is a workflow_dispatch lane; requiring it would block "
            f"every PR on a job that never runs for a PR"
        )
        assert "advisory" not in name, f"{name!r} is advisory and must not gate"


def test_the_release_gate_job_name_carries_no_version() -> None:
    """Offline, so the reasoning holds even when the network audit is skipped.

    This is the assertion that replaces the old
    ``RELEASE_GATE_PREFIX == "v" + version + "-release-gate"`` check. That one
    kept two version literals in step with each other; it did not ask whether
    having a version there was a good idea. It was not.
    """
    import re
    from pathlib import Path

    assert RELEASE_GATE_JOB == "release-gate"
    assert not re.search(r"v?0[._]\d+", RELEASE_GATE_JOB), (
        "the release-gate job name must not carry a version"
    )

    workflow = (
        Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml"
    ).read_text()
    assert f"\n  {RELEASE_GATE_JOB}:\n" in workflow, (
        f"ci.yml does not define a job named {RELEASE_GATE_JOB!r}, so the "
        f"required context can never report"
    )


@pytest.mark.network
def test_a_substantive_review_concern_cannot_be_merged_past() -> None:
    """`required_conversation_resolution`, which §3 claimed and did not have.

    The policy document specified it; the repository had it set to ``false``.
    A control that exists only in prose is the same failure as a gate that
    exists only in prose, and this module exists because of the last one.
    """
    assert _protection()["required_conversation_resolution"]["enabled"] is True


def _rulesets() -> list[dict]:
    result = subprocess.run(
        ["gh", "api", f"repos/{REPO}/rulesets"],
        capture_output=True, text=True, check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"GitHub API unavailable: {result.stderr.strip()[:120]}")
    return json.loads(result.stdout)


def _release_ruleset() -> dict:
    for ruleset in _rulesets():
        detail = subprocess.run(
            ["gh", "api", f"repos/{REPO}/rulesets/{ruleset['id']}"],
            capture_output=True, text=True, check=False,
        )
        if detail.returncode != 0:
            continue
        payload = json.loads(detail.stdout)
        includes = payload.get("conditions", {}).get("ref_name", {}).get("include", [])
        if any("release/" in ref for ref in includes):
            return payload
    pytest.fail("no ruleset targets refs/heads/release/*")


@pytest.mark.network
def test_release_branches_cannot_be_deleted_or_force_pushed() -> None:
    """`release/v0.31.x` is the live 3.11 maintenance branch.

    Losing it would strand the legacy users the README points at, and a force
    push would rewrite security-fix history.
    """
    rules = {rule["type"] for rule in _release_ruleset()["rules"]}
    assert "deletion" in rules
    assert "non_fast_forward" in rules
    assert "pull_request" in rules


@pytest.mark.network
def test_the_release_ruleset_does_not_require_mains_status_checks() -> None:
    """The deadlock lesson, applied one branch over.

    `release/v0.31.x` runs Python 3.11 with PySINDy 1.7.5. Requiring
    `release-gate (3.12)` there would demand a context that branch can never
    produce -- bricking the maintenance line exactly as the versioned job name
    bricked `main`, and for the same reason: a required context matched by
    exact string against a job that does not exist.
    """
    for rule in _release_ruleset()["rules"]:
        assert rule["type"] != "required_status_checks", (
            "the release/* ruleset requires status checks. The 3.11 maintenance "
            "branch cannot produce main's 3.12/3.13 contexts, so this would "
            "block it permanently with no override."
        )
