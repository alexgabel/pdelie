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
    docs_readme = _repo_text("docs/README.md")
    notebooks_readme = _repo_text("notebooks/README.md")
    changelog = _repo_text("CHANGELOG.md")
    publishing = _repo_text("docs/releases/PUBLISHING.md")
    readiness = _repo_text("docs/releases/V0_29_RELEASE_READINESS.md")
    plan = _repo_text("docs/planning/PLAN.md")
    scope = _repo_text("docs/planning/V0_29_SCOPE.md")
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    planning_index = _repo_text("docs/planning/index.rst")
    releases_index = _repo_text("docs/releases/index.rst")
    release_gate_jobs = re.findall(r"^  (v0_\d+[a-z]?-release-gate):", workflow, flags=re.MULTILINE)

    assert pyproject["project"]["version"] == "0.29.0"
    assert 'release = "0.29.0"' in docs_conf
    assert 'version = "0.29"' in docs_conf
    assert release_gate_jobs == ["v0_30f-release-gate"]
    for invocation_fragment in (
        "tests/test_current_release_gate.py",
        "tests/test_release_gates.py",
        "tests/test_v0_29_release_gate.py",
    ):
        assert invocation_fragment in workflow, (
            f"v0.30f release-gate CI job must invoke {invocation_fragment!r}"
        )
    assert "docs-build:" in workflow
    assert "sphinx-build -b html -W --keep-going docs docs/_build/html" in workflow
    assert "v0_29-release-gate:" not in workflow
    assert "v0_28-release-gate" not in workflow

    assert "## 0.29.0" in changelog
    assert "V0.29" in readme
    assert "workflow-recipes and support-matrix release" in readme
    assert "docs/specs/SUPPORT_MATRIX.md" in readme
    assert "docs/workflows" in docs_readme
    assert "12_dataset_to_downstream_workflow.ipynb" in notebooks_readme
    assert "13_candidate_to_split_provenance_workflow.ipynb" in notebooks_readme

    assert "package version: `0.29.0`" in readiness
    assert "git tag: `v0.29.0`" in readiness
    assert "Do not publish to TestPyPI or PyPI for `v0.29.0`" in readiness
    assert "including `v0.29.0`" in publishing
    assert "V0.29 is complete" in plan
    assert "Milestone 6: COMPLETE" in plan
    assert "Milestone 6: COMPLETE" in scope
    assert "workflow_recipes_and_support_matrix_complete_no_new_numerical_scope" in scope
    assert "`v0.29` | Completed | Workflow recipes and support matrix" in roadmap
    assert "Decision-only note for the frozen `v0.29`" in api_stability

    assert "V0_29_SCOPE" in planning_index
    assert "archive/index" in planning_index
    assert "V0_29_RELEASE_READINESS" in releases_index
    assert "archive/index" in releases_index
