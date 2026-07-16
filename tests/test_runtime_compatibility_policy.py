"""v0.32a runtime-compatibility-policy tests.

The v0.31.1a research spike produced the SPEC 0 policy + migration audit.
v0.32a implements the migration and DELETES the private research
prototype. These tests preserve the durable policy-invariant checks and
drop the prototype-specific tests.

Retained invariants:

- ``configs/runtime_compatibility_matrix.json`` is strict-JSON compatible
  and carries the outcome-A designation.
- SPEC 0 policy years are declared.
- Every temporary exception has a named owner and a removed-by milestone.
- Every supported Python version has a CI-lane proposal.
- No public schema drift (22-key discovery_task_result; 27-key
  pdelie_weak_pde_library_diagnostic).
- No root ``pdelie`` export.
- NaN/Inf remains rejected by the strict-JSON validator.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import pdelie

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MATRIX_PATH = _REPO_ROOT / "configs" / "runtime_compatibility_matrix.json"
_POLICY_DOC_PATH = _REPO_ROOT / "docs" / "design" / "RUNTIME_COMPATIBILITY_POLICY.md"
_AUDIT_DOC_PATH = _REPO_ROOT / "docs" / "design" / "PYSINDY_2_MIGRATION_AUDIT.md"


def _matrix() -> dict:
    return json.loads(_MATRIX_PATH.read_text(encoding="utf-8"))


def _policy_text() -> str:
    return _POLICY_DOC_PATH.read_text(encoding="utf-8")


def _audit_text() -> str:
    return _AUDIT_DOC_PATH.read_text(encoding="utf-8")


def test_runtime_compatibility_matrix_is_strict_json() -> None:
    matrix = _matrix()
    assert json.loads(json.dumps(matrix, allow_nan=False)) == matrix
    assert matrix["summary_type"] == "pdelie_runtime_compatibility_matrix"
    assert matrix["summary_schema_version"] == "0.1"
    assert matrix["policy_outcome"] == "A_modern_only_future_line"


def test_runtime_compatibility_matrix_cross_references_policy_docs() -> None:
    matrix = _matrix()
    assert matrix["policy_document"] == "docs/design/RUNTIME_COMPATIBILITY_POLICY.md"
    assert matrix["audit_document"] == "docs/design/PYSINDY_2_MIGRATION_AUDIT.md"
    assert _POLICY_DOC_PATH.exists()
    assert _AUDIT_DOC_PATH.exists()


def test_every_supported_python_has_a_ci_lane_proposal() -> None:
    matrix = _matrix()
    supported_pythons = set(matrix["supported_python_versions"]["blocking"]) | set(
        matrix["supported_python_versions"]["advisory"]
    )
    ci_pythons = {job["python"] for job in matrix["ci_matrix_proposal_v0_32"]}
    missing = supported_pythons - ci_pythons
    assert not missing, (
        f"every supported Python version must appear in the CI proposal; "
        f"missing: {missing!r}"
    )


def test_every_supported_pysindy_generation_has_a_downstream_ci_lane() -> None:
    matrix = _matrix()
    downstream_lanes = [
        job for job in matrix["ci_matrix_proposal_v0_32"] if job.get("downstream")
    ]
    modern_ci_pysindys = {job.get("pysindy") for job in downstream_lanes}
    assert "2.1.x" in modern_ci_pysindys, (
        "v0.32 downstream lanes must include a pysindy 2.1.x line"
    )


def test_v0_32a_does_not_change_discovery_task_result_schema() -> None:
    from pdelie.tasks import discovery as discovery_module

    top_level = discovery_module._TASK_RESULT_TOP_LEVEL_KEYS
    assert len(top_level) == 22


def test_v0_32a_does_not_change_weak_diagnostic_schema() -> None:
    from pdelie.tasks import weak_pde_library as weak_module

    top_level = getattr(
        weak_module, "_DIAGNOSTIC_TOP_LEVEL_KEYS", None
    ) or getattr(weak_module, "_SUMMARY_TOP_LEVEL_KEYS", None)
    assert top_level is not None
    assert len(top_level) == 27


def test_v0_32a_public_schema_invariance_guarantee_recorded() -> None:
    guarantee = _matrix()["public_schema_invariance_guarantee"]
    assert guarantee["discovery_task_result_key_count"] == 22
    assert guarantee["pdelie_weak_pde_library_diagnostic_key_count"] == 27


def test_v0_32a_no_new_root_exports() -> None:
    for forbidden in (
        "_pysindy2_prototype",
        "UnsupportedPySINDyGenerationError",
        "_detect_pysindy_api_generation",
        "runtime_compatibility_matrix",
        "SUPPORTED_PYSINDY_GENERATIONS",
    ):
        assert not hasattr(pdelie, forbidden), (
            f"root pdelie must not export {forbidden!r} after v0.32a"
        )


def test_v0_32a_prototype_file_is_removed() -> None:
    """v0.32a deletes ``src/pdelie/discovery/_pysindy2_prototype.py`` and
    its companion test file. This test guards against reintroduction.
    """
    prototype_path = (
        _REPO_ROOT / "src" / "pdelie" / "discovery" / "_pysindy2_prototype.py"
    )
    assert not prototype_path.exists(), (
        "v0.32a chose outcome A (modern-only future line); the private "
        "prototype must not reappear."
    )
    companion_test = _REPO_ROOT / "tests" / "test_pysindy_2_migration_prototype.py"
    assert not companion_test.exists()


def test_strict_json_validator_still_rejects_nan_and_inf() -> None:
    from pdelie.errors import SchemaValidationError
    from pdelie.reporting.summaries import _validate_strict_json_compatible

    with pytest.raises(SchemaValidationError):
        _validate_strict_json_compatible(
            {"x": float("nan")}, name="v0_32a_nan_guard"
        )
    with pytest.raises(SchemaValidationError):
        _validate_strict_json_compatible(
            {"x": float("inf")}, name="v0_32a_inf_guard"
        )


def test_spec_0_policy_years_are_declared() -> None:
    matrix = _matrix()
    spec = matrix["spec_0_policy"]
    assert spec["python_support_years"] == 3
    assert spec["core_dependency_support_years"] == 2
    assert spec["temporary_exceptions_require_owner_and_removal"] is True

    text = _policy_text()
    assert "SPEC 0" in text
    assert "three years" in text.lower() or "3 years" in text.lower() or "~3 yr" in text.lower()
    assert "two years" in text.lower() or "2 years" in text.lower()


def test_every_temporary_exception_has_owner_and_removal_milestone() -> None:
    matrix = _matrix()
    exceptions = matrix.get("temporary_exceptions", [])
    for entry in exceptions:
        assert isinstance(entry["exception"], str) and entry["exception"]
        assert isinstance(entry["owner_milestone"], str) and entry["owner_milestone"]
        assert isinstance(entry["removed_by"], str) and entry["removed_by"]
        assert re.match(
            r"^v?0\.3[012](?:\.\d+|_.*)?$", entry["removed_by"]
        ), (
            f"temporary exception must retire by v0.32; got "
            f"{entry['removed_by']!r} for {entry['exception']!r}"
        )


def test_migration_audit_document_names_every_api_break_surface() -> None:
    audit_text = _audit_text()
    for surface_fragment in (
        "SINDy.__init__",
        "SINDy.fit",
        "SINDy.differentiate",
        "SINDy.model",
        "STLSQ.__init__",
        "PDELibrary.__init__",
        "WeakPDELibrary.__init__",
    ):
        assert surface_fragment in audit_text, (
            f"audit document must mention API surface {surface_fragment!r}"
        )
