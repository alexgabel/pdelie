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

#: The release-gate job carries the release name, so it changes every release.
#: That is deliberate: renaming the job without updating protection is the
#: version-literal drift class applied to CI, and this prefix check catches the
#: rename while the exact-name assertion below catches a stale reference.
RELEASE_GATE_PREFIX = "v0_38_0b1-release-gate"


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
def test_the_release_gate_is_required_and_names_the_current_release() -> None:
    """Catches a renamed job left out of protection.

    The job name carries the release, so cutting rc1 renames it. If protection
    still lists the b1 name, the rc1 gate is not required and nothing says so --
    the drift class this repository has already hit twice with version literals.
    """
    contexts = set(_protection()["required_status_checks"]["contexts"])
    gate_contexts = {c for c in contexts if "release-gate" in c}
    assert gate_contexts, "no release-gate check is required on main"
    assert all(c.startswith(RELEASE_GATE_PREFIX) for c in gate_contexts), (
        f"protection requires {sorted(gate_contexts)} but this module expects "
        f"{RELEASE_GATE_PREFIX!r}. If the release was renamed, update both the "
        f"protection contexts and RELEASE_GATE_PREFIX in the same commit."
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


def test_the_release_gate_prefix_matches_the_packaged_version() -> None:
    """The prefix and pyproject must not drift apart."""
    import tomllib
    from pathlib import Path

    version = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()
    )["project"]["version"]
    # 0.38.0b1 -> v0_38_0b1-release-gate
    expected = "v" + version.replace(".", "_") + "-release-gate"
    assert RELEASE_GATE_PREFIX == expected, (
        f"RELEASE_GATE_PREFIX is {RELEASE_GATE_PREFIX!r} but pyproject says "
        f"{version!r}, which implies {expected!r}. Update both together."
    )
