from __future__ import annotations

import re
import tomllib
from pathlib import Path


def _repo_text(path: str) -> str:
    return (Path(__file__).resolve().parents[1] / path).read_text(encoding="utf-8")


def test_current_release_metadata_docs_and_ci_are_aligned() -> None:
    pyproject = tomllib.loads(_repo_text("pyproject.toml"))
    docs_conf = _repo_text("docs/conf.py")
    workflow = _repo_text(".github/workflows/ci.yml")
    readme = _repo_text("README.md")
    changelog = _repo_text("CHANGELOG.md")
    publishing = _repo_text("docs/releases/PUBLISHING.md")
    readiness = _repo_text("docs/releases/V0_37_RELEASE_READINESS.md")
    plan = _repo_text("docs/planning/PLAN.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    planning_index = _repo_text("docs/planning/index.rst")
    releases_index = _repo_text("docs/releases/index.rst")
    release_gate_jobs = re.findall(
        r"^  (v0_\d+(?:_\d+)?[a-z]?-release-gate):",
        workflow,
        flags=re.MULTILINE,
    )

    assert pyproject["project"]["version"] == "0.37.0"
    assert 'release = "0.37.0"' in docs_conf
    assert 'version = "0.37"' in docs_conf
    # v0.33.0 release close: v0_33_0-release-gate (a single consolidated
    # release-gate job for the five v0.33 sub-milestones).
    assert release_gate_jobs == ["v0_37_0-release-gate"], release_gate_jobs
    for invocation_fragment in (
        "tests/test_current_release_gate.py",
        "tests/test_release_gates.py",
        "tests/test_v0_29_release_gate.py",
    ):
        assert invocation_fragment in workflow, (
            f"v0.37.0 release-gate CI job must invoke {invocation_fragment!r}"
        )
    assert "docs-build:" in workflow
    assert "sphinx-build -b html -W --keep-going docs docs/_build/html" in workflow
    # Guard against regression to earlier release-gate job names.
    for stale in (
        "v0_29-release-gate:",
        "v0_30-release-gate:",
        "v0_30f-release-gate:",
        "v0_28-release-gate",
        "v0_31-release-gate:",
        "v0_32-release-gate:",
        "v0_32_0-release-gate:",
        "v0_33_0-release-gate:",
        "v0_34_0-release-gate:",
        "v0_35_0-release-gate:",
        "v0_36_0-release-gate:",
    ):
        assert stale not in workflow, (
            f"stale release-gate job name remained in CI workflow: {stale}"
        )

    assert "## 0.37.0" in changelog

    # README/release alignment, derived from pyproject rather than hard-coded.
    #
    # The prior form accepted any of "V0.33"/"v0.33"/"V0.34"/"v0.34", so a README
    # advertising the *previous* release line satisfied it. That is not
    # hypothetical: v0.33.0 shipped with a README still advertising v0.32.0 and
    # this assertion passed. Deriving the expected line from
    # pyproject["project"]["version"] means the guard cannot drift out of step
    # with the package again.
    #
    # The staleness was two-dimensional -- v0.33.0's README was behind in both
    # the prose mention and the pip-install pins -- so both are checked.
    current_version = pyproject["project"]["version"]
    major_minor = ".".join(current_version.split(".")[:2])
    assert f"v{major_minor}" in readme or f"V{major_minor}" in readme, (
        f"README does not advertise the current release line v{major_minor}"
    )

    readme_install_pins = set(
        re.findall(r"pdelie\.git@v(\d+\.\d+\.\d+)", readme)
    )
    assert readme_install_pins, (
        "README must show at least one pinned git+https install example"
    )
    assert readme_install_pins == {current_version}, (
        f"README pip-install examples pin {sorted(readme_install_pins)}; expected "
        f"every pin to name the current release {current_version}"
    )

    assert "package version: `0.37.0`" in readiness
    assert "git tag: `v0.37.0`" in readiness
    assert "Do not publish to TestPyPI or PyPI for `v0.37`" in readiness
    assert "`v0.37.0`" in publishing
    assert (
        "V0.37.0 Release Close" in plan
        or "V0.37.0 is complete" in plan
        or "V0.37.0)" in plan
    )
    assert "v0.37.0" in roadmap and "release/v0.31.x" in roadmap
    assert "Stable public-surface note for the v0.37.0 release close" in api_stability

    assert "archive/index" in planning_index
    assert "V0_37_RELEASE_READINESS" in releases_index
    assert "archive/index" in releases_index
