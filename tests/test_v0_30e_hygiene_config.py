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
    assert ruff.get("target-version") == "py311"
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
    assert mypy.get("python_version") == "3.11"
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
    deps = _pyproject()["project"]["dependencies"]
    numpy_dep = next((dep for dep in deps if dep.lower().startswith("numpy")), None)
    assert numpy_dep is not None
    assert "<2" in numpy_dep


def test_requires_python_is_still_gte_3_11() -> None:
    assert _pyproject()["project"]["requires-python"] == ">=3.11"


def test_package_version_is_still_0_29_0() -> None:
    assert _pyproject()["project"]["version"] == "0.29.0"


# --- CI workflow: lint / typecheck / coverage jobs ------------------------


def test_ci_workflow_has_lint_typecheck_coverage_jobs() -> None:
    jobs = _ci_workflow()["jobs"]
    for job_name in ("lint", "typecheck", "coverage"):
        assert job_name in jobs, f"CI job {job_name!r} missing"


def test_lint_typecheck_coverage_jobs_are_non_blocking() -> None:
    jobs = _ci_workflow()["jobs"]
    for job_name in ("lint", "typecheck", "coverage"):
        job = jobs[job_name]
        # Either the job-level continue-on-error is true, or every action step
        # that runs the tool has continue-on-error: true.
        job_level = job.get("continue-on-error") is True
        step_level = all(
            step.get("continue-on-error") is True
            for step in job.get("steps", [])
            if "run" in step
            and ("ruff" in step.get("run", "") or "mypy" in step.get("run", "") or "pytest" in step.get("run", ""))
        )
        assert job_level or step_level, (
            f"job {job_name!r} must be non-blocking (job-level or step-level continue-on-error: true)"
        )


def test_ci_workflow_preserves_existing_jobs() -> None:
    """The non-release-gate jobs must survive intact.

    v0.30f renames the single release-gate job from ``v0_29-release-gate``
    to ``v0_30f-release-gate``, so this guard covers only the surrounding
    jobs.
    """
    jobs = _ci_workflow()["jobs"]
    for job_name in ("docs-build", "editable-tests", "package-smoke"):
        assert job_name in jobs, f"pre-existing job {job_name!r} disappeared"


def test_ci_workflow_release_gate_job_matches_v0_30f() -> None:
    """After v0.30f the CI workflow carries exactly one release-gate job.

    Inverted from the v0.30e-era ``test_ci_workflow_has_no_v0_30_release_gate_job_yet``
    guard, which asserted that v0.30e had not preempted v0.30f.
    """
    jobs = _ci_workflow()["jobs"]
    release_gate_jobs = [n for n in jobs if re.match(r"^v0_\d+[a-z]?-release-gate$", n)]
    assert release_gate_jobs == ["v0_30f-release-gate"], (
        f"v0.30f consolidates the release-gate job under a single name; got: {release_gate_jobs}"
    )
