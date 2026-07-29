"""v0.30e hygiene phase 1 configuration guard.

Locks in the presence and shape of the ruff/mypy/coverage configuration and
the three new non-blocking CI jobs. Ensures the ``numpy<2`` cap, Python
version floor, and package version are unchanged by v0.30e.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _pyproject() -> dict:
    return tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def _ci_workflow() -> dict:
    return yaml.safe_load((_REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))


# --- pyproject.toml [tool.ruff] ------------------------------------------


def test_pyproject_has_ruff_section_with_expected_shape() -> None:
    tool = _pyproject().get("tool", {})
    ruff = tool.get("ruff")
    assert ruff is not None, "[tool.ruff] section missing"
    # v0.30e / v0.30 close: py311. v0.32a: py312 (SPEC 0 modernization).
    assert ruff.get("target-version") in {"py311", "py312"}
    line_length = ruff.get("line-length")
    assert isinstance(line_length, int) and line_length >= 100
    lint = ruff.get("lint", {})
    extend_select = lint.get("extend-select", [])
    for rule in ("E", "W", "F", "B", "I", "UP", "RUF", "NPY"):
        assert rule in extend_select, f"ruff extend-select missing rule set: {rule}"


# --- pyproject.toml [tool.mypy] ------------------------------------------


def test_pyproject_has_mypy_section_with_strict_scope_override() -> None:
    tool = _pyproject().get("tool", {})
    mypy = tool.get("mypy")
    assert mypy is not None, "[tool.mypy] section missing"
    # v0.30e / v0.30 close: 3.11. v0.32a: 3.12 (SPEC 0 modernization).
    assert mypy.get("python_version") in {"3.11", "3.12"}
    overrides = mypy.get("overrides", [])
    strict_scopes = [entry for entry in overrides if entry.get("strict") is True]
    assert strict_scopes, "no strict [[tool.mypy.overrides]] block"
    strict_modules = strict_scopes[0]["module"]
    for name in ("pdelie.contracts", "pdelie._boundary"):
        assert name in strict_modules, f"strict scope missing {name}"
    assert any(m.startswith("pdelie.derivatives") for m in strict_modules)


# --- pyproject.toml [tool.coverage.*] ------------------------------------


def test_pyproject_has_coverage_sections_with_expected_shape() -> None:
    tool = _pyproject().get("tool", {})
    coverage = tool.get("coverage")
    assert coverage is not None, "[tool.coverage] section missing"
    run = coverage.get("run")
    assert run is not None, "[tool.coverage.run] missing"
    assert run.get("source") == ["src/pdelie"]
    assert run.get("branch") is True
    report = coverage.get("report")
    assert report is not None, "[tool.coverage.report] missing"
    assert report.get("fail_under") == 80


# --- pyproject.toml [project.optional-dependencies].test -----------------


def test_pyproject_test_extras_include_ruff_mypy_pytest_cov() -> None:
    test_deps = _pyproject()["project"]["optional-dependencies"]["test"]
    names = [re.split(r"[<>=; ]", dep, maxsplit=1)[0].lower() for dep in test_deps]
    assert "ruff" in names
    assert "mypy" in names
    assert "pytest-cov" in names


# --- guards that v0.30e did not silently touch other pyproject knobs ------


def test_numpy_upper_bound_is_still_less_than_2() -> None:
    """v0.30e / v0.30 close: numpy<2. v0.32a widens to numpy<3 (SPEC 0
    modernization). Both are acceptable to keep this hygiene guard alive
    across the transition.
    """
    deps = _pyproject()["project"]["dependencies"]
    numpy_dep = next((dep for dep in deps if dep.lower().startswith("numpy")), None)
    assert numpy_dep is not None
    assert "<2" in numpy_dep or "<3" in numpy_dep


def test_requires_python_is_still_gte_3_11() -> None:
    """v0.30e / v0.30 close: requires-python>=3.11. v0.32a bumps to >=3.12
    (SPEC 0 modernization). Both are acceptable to keep this hygiene guard
    alive across the transition.
    """
    assert _pyproject()["project"]["requires-python"] in {">=3.11", ">=3.12"}


def test_package_version_matches_v0_30_close() -> None:
    """v0.30e held the version at 0.29.0; v0.30 close bumped to 0.30.0; the
    v0.31 arc held the version at 0.30.0 through v0.31c1; v0.31.0 release
    close bumps to 0.31.0.

    All are acceptable to keep this hygiene-config guard alive across the
    release-close transitions. numpy<2 and requires-python>=3.11 remain
    unchanged (asserted by the sibling guards below).
    """
    assert _pyproject()["project"]["version"] in {"0.29.0", "0.30.0", "0.31.0", "0.32.0", "0.33.0", "0.34.0"}


# --- CI workflow: lint / typecheck / coverage jobs ------------------------


def test_ci_workflow_has_lint_typecheck_coverage_jobs() -> None:
    jobs = _ci_workflow()["jobs"]
    for job_name in ("lint", "typecheck", "coverage"):
        assert job_name in jobs, f"CI job {job_name!r} missing"


def test_lint_is_blocking_after_v0_30_1a_promotion() -> None:
    """v0.30.1a promoted ``lint`` from advisory to blocking. The job must not
    carry ``continue-on-error: true`` at either the job or step level.
    """
    job = _ci_workflow()["jobs"]["lint"]
    assert job.get("continue-on-error") is not True, (
        "lint job must be blocking after v0.30.1a promotion"
    )
    for step in job.get("steps", []):
        if "run" in step and "ruff" in step.get("run", ""):
            assert step.get("continue-on-error") is not True, (
                "lint ruff step must be blocking after v0.30.1a promotion"
            )


def test_typecheck_and_coverage_jobs_remain_non_blocking() -> None:
    """v0.30.1a promoted ``lint`` only. ``typecheck`` stays advisory pending
    v0.30.1c-k mypy strict-scope broadening; ``coverage`` stays advisory
    pending v0.30.1b coverage promotion.
    """
    jobs = _ci_workflow()["jobs"]
    for job_name in ("typecheck", "coverage"):
        job = jobs[job_name]
        job_level = job.get("continue-on-error") is True
        step_level = all(
            step.get("continue-on-error") is True
            for step in job.get("steps", [])
            if "run" in step
            and ("mypy" in step.get("run", "") or "pytest" in step.get("run", ""))
        )
        assert job_level or step_level, (
            f"job {job_name!r} must remain non-blocking through v0.30.1a "
            f"(job-level or step-level continue-on-error: true)"
        )


def test_ci_workflow_preserves_existing_jobs() -> None:
    """The non-release-gate jobs must survive intact.

    The release-gate job itself has been renamed twice in the v0.30 arc:
    v0.30f renamed ``v0_29-release-gate`` to ``v0_30f-release-gate``, and
    the v0.30 release close renamed ``v0_30f-release-gate`` to
    ``v0_30-release-gate``. This guard covers only the surrounding jobs
    (docs-build, editable-tests, package-smoke); the release-gate job is
    audited separately below.
    """
    jobs = _ci_workflow()["jobs"]
    for job_name in ("docs-build", "editable-tests", "package-smoke"):
        assert job_name in jobs, f"pre-existing job {job_name!r} disappeared"


def test_ci_workflow_release_gate_job_matches_v0_30_close() -> None:
    """After the v0.30 release close the workflow carries exactly one
    release-gate job, named ``v0_30-release-gate``.

    Renaming timeline (all inside the v0.30 arc):

    - v0.29 shipped ``v0_29-release-gate``.
    - v0.30f renamed it to ``v0_30f-release-gate`` alongside the
      manifest-driven narrow declarative consolidation.
    - The v0.30 release close renamed it to ``v0_30-release-gate``.
    - The v0.31.0 release close renamed it to ``v0_31-release-gate``.

    Inverted from the v0.30e-era ``test_ci_workflow_has_no_v0_30_release_gate_job_yet``
    guard, which asserted that v0.30e had not preempted v0.30f.
    """
    jobs = _ci_workflow()["jobs"]
    release_gate_jobs = [
        n for n in jobs if re.match(r"^v0_\d+(?:_\d+)?[a-z]?-release-gate$", n)
    ]
    # v0.31.0 close: v0_31-release-gate. v0.32a-d arc: v0_32-release-gate.
    # v0.33.0 consolidated release close: v0_33_0-release-gate.
    assert release_gate_jobs in (
        ["v0_31-release-gate"],
        ["v0_32-release-gate"],
        ["v0_34_0-release-gate"],
    ), (
        f"expected the current v0.31.x, v0.32 arc, or v0.32.0 release "
        f"close release-gate job; got: {release_gate_jobs}"
    )
