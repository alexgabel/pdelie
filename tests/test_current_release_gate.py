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
    readiness = _repo_text("docs/releases/V0_38_0_RELEASE_READINESS.md")
    plan = _repo_text("docs/planning/PLAN.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    planning_index = _repo_text("docs/planning/index.rst")
    releases_index = _repo_text("docs/releases/index.rst")
    # The release-gate job name is STABLE: `release-gate`, with no version in
    # it. A versioned name deadlocked branch protection at every cut --
    # protection required `v0_38_0b1-release-gate`, the rename PR produced
    # `v0_38_0rc1-release-gate`, the required context never reported again, and
    # `enforce_admins: true` left no way through.
    #
    # This regex matches BOTH forms deliberately. Matching only the stable name
    # would make a regression to a versioned name show up as an empty list --
    # a guard failing for a reason unrelated to what it checks, which is the
    # defect class this repository has now hit repeatedly.
    release_gate_jobs = re.findall(
        r"^  ((?:v0_\d+(?:_\d+)?(?:[a-z]|a\d+|b\d+|rc\d+)?-)?release-gate):",
        workflow,
        flags=re.MULTILINE,
    )

    assert pyproject["project"]["version"] == "0.38.0"
    assert 'release = "0.38.0"' in docs_conf
    assert 'version = "0.38"' in docs_conf
    assert release_gate_jobs == ["release-gate"], (
        f"expected exactly one release-gate job named 'release-gate', found "
        f"{release_gate_jobs}. If this is a versioned name, it must not be "
        f"reintroduced: it deadlocks branch protection at every release cut."
    )
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
        "v0_38_0a1-release-gate:",
        "v0_38_0b1-release-gate:",
        "v0_37_0-release-gate:",
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

    assert "## 0.38.0a1" in changelog

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

    # The pattern accepts a PEP 440 prerelease suffix. Without it a prerelease
    # tag matches nothing, `readme_install_pins` is empty, and the assertion
    # below fires with a message about missing examples rather than about the
    # version -- a guard failing for a reason unrelated to its claim.
    readme_install_pins = set(
        re.findall(r"pdelie\.git@v(\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?)", readme)
    )
    assert readme_install_pins, (
        "README must show at least one pinned git+https install example"
    )
    assert readme_install_pins == {current_version}, (
        f"README pip-install examples pin {sorted(readme_install_pins)}; expected "
        f"every pin to name the current release {current_version}"
    )

    # Derived from pyproject rather than written twice. The literal form drifted
    # once already at this bump -- the version was updated everywhere except the
    # two backticked strings here, which a quoted search-and-replace missed.
    assert f"package version: `{current_version}`" in readiness
    assert f"git tag: `v{current_version}`" in readiness
    assert "Do not publish to TestPyPI or PyPI for `v0.38`" in readiness
    # rc1 must state, in the readiness document itself, that every gate is met
    # -- and must name the gate that previously was not, so the claim it
    # discharges is legible from the tag rather than from a PR description.
    assert "Gate F closed" in readiness
    assert "31328966332" in readiness
    assert "defect corrections only" in readiness
    assert "`v0.37.0`" in publishing
    assert (
        "V0.37.0 Release Close" in plan
        or "V0.37.0 is complete" in plan
        or "V0.37.0)" in plan
    )
    assert "v0.37.0" in roadmap and "release/v0.31.x" in roadmap
    assert "Stable public-surface note for the v0.37.0 release close" in api_stability

    assert "archive/index" in planning_index
    assert "V0_38_0_RELEASE_READINESS" in releases_index
    assert "V0_38_0RC1_RELEASE_READINESS" in releases_index
    assert "V0_38_0B1_RELEASE_READINESS" in releases_index, (
        "the b1 readiness document must stay indexed: it records why that "
        "tag withheld the RC designation, which is the claim rc1 discharges"
    )
    assert "archive/index" in releases_index


def test_every_deferral_target_has_a_roadmap_row() -> None:
    """A deferral pointing at a release that does not exist is a dropped item.

    v0.38 deferred nonperiodic domains and monotone coefficients to `v0.41`,
    and the roadmap had no v0.41 row -- nor a v0.38 row for the arc being
    released. Both were invisible to planning while reading as scheduled.
    """
    import re

    roadmap = _repo_text("docs/planning/ROADMAP.md")
    rows = set(re.findall(r"^\| `(v\d+\.\d+)` \|", roadmap, flags=re.MULTILINE))

    targets: set[str] = set()
    for name in (
        "docs/design/V0_38_BINDING_DESIGN_CONSTRAINTS.md",
        "docs/planning/PLAN.md",
    ):
        targets |= set(re.findall(r"Deferred to \[?(v\d+\.\d+)", _repo_text(name)))

    assert targets, "no deferrals found; this guard would pass vacuously"
    missing = sorted(t for t in targets if t not in rows)
    assert not missing, (
        f"work is deferred to {missing}, which has no roadmap row. A deferral "
        f"to a nonexistent release reads as scheduled and is not."
    )


def test_the_release_under_development_has_a_roadmap_row() -> None:
    """v0.38 shipped a1 and b1 with no row in the roadmap at all."""
    import re
    import tomllib

    version = tomllib.loads(_repo_text("pyproject.toml"))["project"]["version"]
    minor = "v" + ".".join(version.split(".")[:2])
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    rows = set(re.findall(r"^\| `(v\d+\.\d+)` \|", roadmap, flags=re.MULTILINE))
    assert minor in rows, (
        f"pyproject declares {version!r} but the roadmap has no {minor} row"
    )


def test_the_documented_contributor_environment_can_install_the_package() -> None:
    """environment.yml pinned 3.11 while the package required >=3.12.

    A contributor following the documented setup got an environment in which
    `pip install -e .` fails. The blind spot was exact: this module aligned
    version strings across README, CHANGELOG, CI and the readiness docs, and
    never looked at the interpreter the environment file pins.
    """
    import re
    import tomllib

    requires = tomllib.loads(_repo_text("pyproject.toml"))["project"]["requires-python"]
    floor = tuple(int(p) for p in re.search(r">=\s*(\d+\.\d+)", requires).group(1).split("."))

    pinned = re.search(r"python\s*=\s*(\d+\.\d+)", _repo_text("environment.yml"))
    assert pinned, "environment.yml does not pin a Python version"
    assert tuple(int(p) for p in pinned.group(1).split(".")) >= floor, (
        f"environment.yml pins python={pinned.group(1)} but the package "
        f"requires {requires}; the documented contributor environment cannot "
        f"install the package"
    )


def test_every_workflow_builds_on_a_supported_interpreter() -> None:
    """The publish lane built the release artifact on 3.11.

    Checked across all workflows rather than the one that was wrong, because a
    guard written against a specific defect only catches that defect.
    """
    import re
    import tomllib
    from pathlib import Path

    requires = tomllib.loads(_repo_text("pyproject.toml"))["project"]["requires-python"]
    floor = tuple(int(p) for p in re.search(r">=\s*(\d+\.\d+)", requires).group(1).split("."))

    root = Path(__file__).resolve().parents[1]
    workflows = sorted((root / ".github/workflows").glob("*.yml"))
    assert workflows, "no workflows found; this guard would pass vacuously"

    offenders: list[str] = []
    checked = 0
    for path in workflows:
        lines = path.read_text().splitlines()
        for index, line in enumerate(lines):
            match = re.search(r'python-version:\s*"?(\d+\.\d+)(?:\.\d+)?"?', line)
            if not match:
                continue
            checked += 1
            if tuple(int(p) for p in match.group(1).split(".")) >= floor:
                continue
            # A sub-floor pin is permitted only where it is DECLARED. The
            # migration lanes provision a v0.22.0-era 3.11 environment on
            # purpose. Keying the exception on the marker rather than the
            # filename means a NEW undeclared sub-floor pin in those same files
            # is still caught.
            window = "\n".join(lines[max(0, index - 5):index])
            if "legacy-interpreter:" in window:
                continue
            offenders.append(f"{path.name}:{index + 1}: {match.group(1)}")

    assert checked > 0, (
        "no python-version pins found in any workflow; this guard would pass "
        "having checked nothing"
    )
    assert not offenders, (
        f"workflows target interpreters below requires-python {requires}: {offenders}"
    )


def test_the_readme_badges_track_the_packaged_version() -> None:
    """The badge sat at 0.29.0 across nine releases.

    A reader sees the badge before the prose, so a stale badge misinforms
    first.
    """
    import re
    import tomllib

    version = tomllib.loads(_repo_text("pyproject.toml"))["project"]["version"]
    readme = _repo_text("README.md")

    badge = re.search(r"badge/version-([0-9][^-\s)]*)-", readme)
    assert badge, "no version badge found in README"
    assert badge.group(1) == version, (
        f"README badge says {badge.group(1)}, pyproject says {version}"
    )

    requires = tomllib.loads(_repo_text("pyproject.toml"))["project"]["requires-python"]
    floor = re.search(r">=\s*(\d+\.\d+)", requires).group(1)
    py_badge = re.search(r"badge/python-%3E%3D([0-9.]+)-", readme)
    assert py_badge, "no python badge found in README"
    assert py_badge.group(1) == floor, (
        f"README python badge says >={py_badge.group(1)}, pyproject says {requires}"
    )
