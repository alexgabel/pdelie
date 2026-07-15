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
    """The audit must explain the manifest-driven parameterized release-gate plan.

    v0.30a specified the consolidation contract; v0.30f implemented it narrowly
    (manifest + parameterized test, zero file deletions). The audit must
    describe both the contract and the shipping shape.
    """
    audit = _audit_text()
    assert "parameterized" in audit.lower()
    assert "release_gate_manifest.json" in audit
    # v0.30a specified the consolidation contract; the audit records this.
    assert "v0.30a" in audit
    # v0.30f is where the consolidation actually shipped — assert the doc
    # records that landing rather than still calling it a proposal.
    assert "v0.30f" in audit
    assert "IMPLEMENTED" in audit or "implemented" in audit


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


def test_v0_30e_pyproject_now_configures_ruff_mypy_coverage() -> None:
    """v0.30e ships the ruff/mypy/coverage config that v0.30a's scope had
    left as an audit-only proposal. Inverted from the earlier
    ``test_v0_30_no_premature_pyproject_changes`` guard.

    numpy<2 and requires-python>=3.11 must not have changed.
    """
    pyproject_text = _repo_text("pyproject.toml")
    pyproject = tomllib.loads(pyproject_text)

    tool_sections = pyproject.get("tool", {})
    # These three sections are now expected present under v0.30e.
    for expected in ("ruff", "mypy", "coverage"):
        assert expected in tool_sections, (
            f"v0.30e must configure [tool.{expected}] in pyproject.toml"
        )

    # numpy upper bound: v0.30e held <2. v0.32a widened to <3 (SPEC 0
    # modernization). Both are acceptable to keep this v0.30e audit alive
    # across the transition.
    deps = pyproject["project"]["dependencies"]
    numpy_dep = next((dep for dep in deps if dep.lower().startswith("numpy")), None)
    assert numpy_dep is not None
    assert "<2" in numpy_dep or "<3" in numpy_dep, (
        f"numpy cap must be <2 (v0.30e) or <3 (v0.32a); got: {numpy_dep}"
    )

    # requires-python: v0.30e held >=3.11. v0.32a bumped to >=3.12.
    requires_python = pyproject["project"]["requires-python"]
    assert ">=3.11" in requires_python or ">=3.12" in requires_python

    # Package version is 0.29.0 during the v0.30a-f arc, 0.30.0 at v0.30 close
    # (which held through the v0.31a-c1 runtime sub-releases), and 0.31.0 at
    # the v0.31.0 release close.
    assert pyproject["project"]["version"] in {"0.29.0", "0.30.0", "0.31.0"}


def test_v0_30e_ci_workflow_now_has_lint_typecheck_coverage_jobs_nonblocking() -> None:
    """v0.30e adds the lint/typecheck/coverage jobs as non-blocking. Inverted
    from the earlier ``test_v0_30_no_premature_ci_changes`` guard.

    The pre-existing four jobs must survive intact. v0.30e does not add a
    v0_30* release-gate job — that comes with v0.30f.
    """
    workflow = _repo_text(".github/workflows/ci.yml")
    config = _repo_json(_SCOPE_CONFIG_PATH)

    # Pre-existing jobs still present.
    for job in config["expected_ci_jobs"]:
        assert f"{job}:" in workflow, f"pre-existing CI job disappeared: {job}"

    # v0.30e's three new jobs are present and non-blocking.
    for job in ("lint", "typecheck", "coverage"):
        pattern = rf"^  {re.escape(job)}:\s*$"
        assert re.search(pattern, workflow, flags=re.MULTILINE), (
            f"v0.30e must add CI job: {job}"
        )
    # Blocking / non-blocking state after v0.30.1a lint promotion:
    #   lint      -> BLOCKING (promoted in v0.30.1a)
    #   typecheck -> non-blocking (promoted in v0.30.1c-k, per subpackage)
    #   coverage  -> non-blocking (promoted in v0.30.1b)
    import yaml  # local import: yaml is already a v0.30e test dep

    parsed_jobs = yaml.safe_load(workflow)["jobs"]
    lint_body = parsed_jobs["lint"]
    assert lint_body.get("continue-on-error") is not True, (
        "v0.30.1a promoted the lint job to blocking; it must not carry job-level continue-on-error: true"
    )
    for step in lint_body.get("steps", []):
        if "run" in step and "ruff" in step.get("run", ""):
            assert step.get("continue-on-error") is not True, (
                "v0.30.1a promoted the lint ruff step to blocking"
            )
    for job in ("typecheck", "coverage"):
        job_body = parsed_jobs[job]
        job_level = job_body.get("continue-on-error") is True
        step_level = any(
            step.get("continue-on-error") is True
            for step in job_body.get("steps", [])
            if "run" in step
        )
        assert job_level or step_level, (
            f"v0.30.1a advisory CI job {job!r} must remain non-blocking pending its own promotion"
        )

    # Release-gate job name across the v0.30 / v0.31 arcs:
    # v0.29 shipped ``v0_29-release-gate``; v0.30f renamed it to
    # ``v0_30f-release-gate``; the v0.30 release close renamed it to
    # ``v0_30-release-gate``; the v0.31.0 release close renamed it to
    # ``v0_31-release-gate``. This guard tracks the current name.
    release_gate_jobs = re.findall(r"^  (v0_\d+[a-z]?-release-gate):", workflow, flags=re.MULTILINE)
    assert release_gate_jobs in (
        ["v0_31-release-gate"],
        ["v0_32-release-gate"],
    ), (
        f"expected the current v0.31.x or v0.32 release-gate job; got: "
        f"{release_gate_jobs}"
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


_SUPPORTED_MANIFEST_CLASSES = frozenset({
    "required_phrases_in_scope_doc",
    "required_phrases_in_api_stability",
    "required_phrases_in_roadmap",
    "required_phrases_in_plan",
    "required_phrases_in_readiness_doc",
    "forbidden_root_attributes",
    "forbidden_submodule_attributes",
    "required_root_attributes",
    "required_submodule_attributes",
    "strict_json_manifests",
    "notebook_structural_checks",
})
_MANIFEST_METADATA_KEYS = frozenset({"release", "source_file"})


def test_v0_30f_release_gate_consolidation_manifest_exists() -> None:
    """v0.30f ships a strict-JSON declarative release-gate manifest."""
    manifest_path = _repo_path("configs/release_gate_manifest.json")
    assert manifest_path.exists(), f"missing {manifest_path}"

    manifest = _repo_json("configs/release_gate_manifest.json")
    # strict-JSON: no NaN / infinity permitted.
    assert json.loads(json.dumps(manifest, allow_nan=False)) == manifest

    assert manifest["summary_type"] == "pdelie_declarative_release_gate_manifest"
    assert manifest["scope"] == "declarative_release_gate_checks_only"
    # Release-gate job name lineage: v0_30-release-gate (v0.30 close) →
    # v0_31-release-gate (v0.31.0 close) → v0_32-release-gate (v0.32a
    # migration).
    assert manifest["current_release_gate_job_name"] in {
        "v0_30-release-gate",
        "v0_31-release-gate",
        "v0_32-release-gate",
    }
    assert manifest["release_count"] == len(manifest["releases"])

    for row in manifest["releases"]:
        assert "release" in row
        for key in row:
            if key in _MANIFEST_METADATA_KEYS:
                continue
            assert key in _SUPPORTED_MANIFEST_CLASSES, (
                f"release {row['release']!r} uses unsupported class {key!r}"
            )


def test_v0_30f_all_release_gate_files_are_retained() -> None:
    """v0.30f consolidates by manifest addition, not by file deletion.

    All 26 tests/test_v0_*_release_gate.py files (v0.4-v0.29 plus v0.30e's
    hygiene-config test) stay in place. The parameterized replay in
    tests/test_release_gates.py runs alongside them.
    """
    files = sorted((_REPO_ROOT / "tests").glob("test_v0_*_release_gate.py"))
    assert len(files) == 26, (
        f"expected 26 per-version release-gate files after v0.30f (no deletions); "
        f"found {len(files)}"
    )
    assert (_REPO_ROOT / "tests" / "test_release_gates.py").exists(), (
        "v0.30f must add tests/test_release_gates.py alongside the per-version files"
    )


def test_v0_30f_hygiene_audit_records_consolidation_landed() -> None:
    """The hygiene audit must record that v0.30f delivered the manifest."""
    audit = _audit_text()
    assert "v0.30f" in audit, "hygiene audit must reference v0.30f"
    assert "release_gate_manifest.json" in audit
    # The audit must acknowledge that the per-version files are retained,
    # not falsely claim they were all removed.
    assert "retained" in audit.lower() or "kept" in audit.lower()
    # The excluded functional/mixed files should be listed with reasons.
    for excluded_release in ("v0.4", "v0.6", "v0.7", "v0.8", "v0.9", "v0.11", "v0.12", "v0.26"):
        assert excluded_release in audit, (
            f"hygiene audit must list excluded release-gate file for {excluded_release}"
        )
