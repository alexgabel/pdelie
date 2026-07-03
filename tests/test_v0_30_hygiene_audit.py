from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_AUDIT_DOC_PATH = "docs/design/V0_30_HYGIENE_AUDIT.md"
_SCOPE_CONFIG_PATH = "configs/planning/v0_30_nonperiodic_readiness_scope.json"


def _repo_path(path: str) -> Path:
    return _REPO_ROOT / path


def _repo_text(path: str) -> str:
    return _repo_path(path).read_text(encoding="utf-8")


def _repo_json(path: str) -> dict[str, object]:
    return json.loads(_repo_text(path))


def _audit_text() -> str:
    return _repo_text(_AUDIT_DOC_PATH)


def test_v0_30_hygiene_audit_doc_exists_with_required_headings() -> None:
    """The hygiene audit document exists and covers every required section."""
    audit_path = _repo_path(_AUDIT_DOC_PATH)
    assert audit_path.exists(), f"missing {audit_path}"
    audit = _audit_text()
    required_headings = [
        "Lint status",
        "Type-checker status",
        "Coverage status",
        "Python version matrix",
        "NumPy upper bound",
        "Release-gate proliferation",
        "Optional-dependency import pattern",
        "Strict JSON",
        "Staged enforcement",
        "Release-gate consolidation",
    ]
    for heading in required_headings:
        assert heading in audit, f"hygiene audit missing required section: {heading!r}"


def test_v0_30_hygiene_audit_records_current_baseline() -> None:
    """The audit must record the current baseline accurately so we can detect drift."""
    audit = _audit_text()

    # Lint: ruff/black/flake8 absent
    assert "ruff" in audit.lower()
    assert "No `[tool.ruff]`" in audit or "no `[tool.ruff]`" in audit.lower()

    # Type-checker: mypy/pyright absent
    assert "mypy" in audit.lower()
    assert "No `[tool.mypy]`" in audit or "no `[tool.mypy]`" in audit.lower()

    # Coverage: absent
    assert "coverage" in audit.lower()
    assert "No `[tool.coverage]`" in audit or "no `[tool.coverage]`" in audit.lower()

    # Python matrix: 3.11 only
    assert "3.11" in audit
    assert "Python 3.11" in audit or "python-version" in audit.lower()

    # NumPy upper bound documented
    assert "numpy" in audit.lower()
    assert "<2" in audit or "1.24" in audit

    # Release-gate file count
    assert "26" in audit


def test_v0_30_hygiene_audit_documents_lazy_optional_import_policy() -> None:
    """The audit must reaffirm the lazy-import policy referenced by name."""
    audit = _audit_text()
    assert "_require_discovery_dependencies" in audit
    assert "importlib.import_module" in audit
    # The policy phrasing must be present
    assert "imported on first use" in audit or "imported on first invocation" in audit.lower()
    # The reference path is cited
    assert "src/pdelie/discovery/pysindy_adapter.py" in audit


def test_v0_30_hygiene_audit_documents_strict_json_policy() -> None:
    """The audit must record the JSON-strict / no-NaN policy with concrete references."""
    audit = _audit_text()
    assert "allow_nan=False" in audit
    assert "_validate_strict_json_compatible" in audit
    assert "_json_safe" in audit
    # No-NaN guidance for new outputs
    assert "float(\"nan\")" in audit or 'float("nan")' in audit


def test_v0_30_hygiene_audit_documents_release_gate_consolidation_proposal() -> None:
    """The audit must explain the manifest-driven parameterized release-gate plan."""
    audit = _audit_text()
    assert "parameterized" in audit.lower()
    assert "release_gate_manifest.json" in audit
    # The proposal must be scoped to v0.30 proper, not v0.30a
    assert "v0.30 proper" in audit
    assert "not v0.30a" in audit or "not in v0.30a" in audit.lower()


def test_v0_30_hygiene_audit_documents_staged_enforcement_phases() -> None:
    """The staged-enforcement plan must enumerate phases tied to specific releases."""
    audit = _audit_text()
    # Phase 0 is audit-only (v0.30a)
    assert "Phase 0" in audit
    assert "v0.30a" in audit
    # Phase 1 lands in v0.30 proper
    assert "Phase 1" in audit
    # Future phases referenced
    assert "Phase 2" in audit
    assert "Phase 3" in audit
    # NumPy 2.x lift deferred
    assert "numpy 2.x" in audit.lower() or "numpy 2" in audit.lower()


def test_v0_30_no_premature_pyproject_changes() -> None:
    """pyproject.toml must not yet contain lint/type/coverage sections in v0.30a."""
    pyproject_text = _repo_text("pyproject.toml")
    pyproject = tomllib.loads(pyproject_text)

    config = _repo_json(_SCOPE_CONFIG_PATH)
    forbidden_sections = config["guard_no_premature_pyproject_sections"]

    # Top-level [tool.*] sections must not include any forbidden one.
    tool_sections = pyproject.get("tool", {})
    for forbidden in forbidden_sections:
        # forbidden is e.g. "tool.ruff"; the leaf is "ruff"
        leaf = forbidden.split(".", 1)[1]
        assert leaf not in tool_sections, (
            f"v0.30a must not configure [{forbidden}] in pyproject.toml"
        )

    # numpy upper bound is still < 2
    deps = pyproject["project"]["dependencies"]
    numpy_dep = next((dep for dep in deps if dep.lower().startswith("numpy")), None)
    assert numpy_dep is not None
    assert "<2" in numpy_dep, f"numpy dep changed unexpectedly: {numpy_dep}"

    # requires-python is still >=3.11
    requires_python = pyproject["project"]["requires-python"]
    assert ">=3.11" in requires_python


def test_v0_30_no_premature_ci_changes() -> None:
    """CI workflow must retain exactly the four existing jobs and no premature additions."""
    workflow = _repo_text(".github/workflows/ci.yml")
    config = _repo_json(_SCOPE_CONFIG_PATH)

    expected_jobs = config["expected_ci_jobs"]
    for job in expected_jobs:
        assert f"{job}:" in workflow, f"expected CI job missing: {job}"

    # No premature additions
    for forbidden in config["guard_no_premature_ci_jobs"]:
        # Match as a job-name header to avoid false positives on shell commands
        # (job declarations sit at column 2 in this workflow file).
        pattern = rf"^  {re.escape(forbidden)}:\s*$"
        assert not re.search(pattern, workflow, flags=re.MULTILINE), (
            f"v0.30a must not add CI job: {forbidden}"
        )

    # The existing single release-gate job is unchanged
    release_gate_jobs = re.findall(r"^  (v0_\d+-release-gate):", workflow, flags=re.MULTILINE)
    assert release_gate_jobs == ["v0_29-release-gate"], (
        f"v0.30a must not add a v0_30-release-gate job (got: {release_gate_jobs})"
    )


def test_v0_30_release_gate_file_count_matches_audit() -> None:
    """The audit cites 26 release-gate files; assert that count is current."""
    files = sorted((_REPO_ROOT / "tests").glob("test_v0_*_release_gate.py"))
    assert len(files) == 26, (
        f"hygiene audit cites 26 release-gate files but found {len(files)}; "
        "update docs/design/V0_30_HYGIENE_AUDIT.md and this assertion together"
    )


def test_v0_30_no_new_optional_dependency_added() -> None:
    """v0.30a must not declare any new optional dependency."""
    pyproject = tomllib.loads(_repo_text("pyproject.toml"))
    optional = pyproject["project"].get("optional-dependencies", {})
    expected_extras = {"downstream", "xarray", "viz", "test"}
    assert set(optional.keys()) == expected_extras, (
        f"unexpected optional-dependency extras: {sorted(optional.keys())}"
    )
