"""v0.31.1a runtime-compatibility-policy tests.

The v0.31.1a research spike ships:

- ``docs/design/RUNTIME_COMPATIBILITY_POLICY.md`` (SPEC 0 alignment).
- ``docs/design/PYSINDY_2_MIGRATION_AUDIT.md`` (per-delta API audit).
- ``configs/runtime_compatibility_matrix.json`` (strict-JSON machine-
  readable form of the above).
- ``src/pdelie/discovery/_pysindy2_prototype.py`` (private prototype).

These tests assert the durable invariants without spinning up any of the
multi-Python venvs at test-collection time. The full environment matrix
audit is exercised out-of-band in the spike itself; the in-repo tests
below verify the policy shape, the no-schema-drift invariants, and the
prototype's non-interference with the legacy 1.x lane.
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


# ---------------------------------------------------------------------------
# 1. Compatibility matrix is strict JSON.
# ---------------------------------------------------------------------------


def test_runtime_compatibility_matrix_is_strict_json() -> None:
    matrix = _matrix()
    # allow_nan=False + roundtrip inequality-check is the canonical
    # strict-JSON assertion PDELie uses across all specs.
    assert json.loads(json.dumps(matrix, allow_nan=False)) == matrix
    assert matrix["summary_type"] == "pdelie_runtime_compatibility_matrix"
    assert matrix["summary_schema_version"] == "0.1"
    assert matrix["policy_outcome"] == "A_modern_only_future_line"


def test_runtime_compatibility_matrix_cross_references_policy_docs() -> None:
    matrix = _matrix()
    assert matrix["policy_document"] == "docs/design/RUNTIME_COMPATIBILITY_POLICY.md"
    assert matrix["audit_document"] == "docs/design/PYSINDY_2_MIGRATION_AUDIT.md"
    # Both cross-referenced documents must actually exist.
    assert _POLICY_DOC_PATH.exists()
    assert _AUDIT_DOC_PATH.exists()


# ---------------------------------------------------------------------------
# 2. Every supported version has a CI-lane proposal.
# ---------------------------------------------------------------------------


def test_every_supported_python_has_a_ci_lane_proposal() -> None:
    """Every Python version declared blocking or advisory in
    supported_python_versions must appear at least once in ci_matrix_proposal_v0_32.
    """
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
    # PySINDy 2.1.x must be covered.
    modern_ci_pysindys = {job.get("pysindy") for job in downstream_lanes}
    assert "2.1.x" in modern_ci_pysindys, (
        "v0.32 downstream lanes must include a pysindy 2.1.x line"
    )


# ---------------------------------------------------------------------------
# 3. Every unsupported version has an actionable message path.
# ---------------------------------------------------------------------------


def test_unsupported_python_generation_message_path_exists_in_source() -> None:
    """The v0.31.0 targeted 3.12+ message in ``pdelie.discovery.pysindy_adapter``
    and ``pdelie.tasks.weak_pde_library`` continues to name Python 3.12+
    and the v0.31.1 deferral. This is what the release-close committed for
    the Python 3.12+ downstream-UX preflight.
    """
    for source_relpath in (
        "src/pdelie/discovery/pysindy_adapter.py",
        "src/pdelie/tasks/weak_pde_library.py",
    ):
        text = (_REPO_ROOT / source_relpath).read_text(encoding="utf-8")
        assert "3.12" in text, (
            f"{source_relpath} must retain the Python 3.12+ actionable message"
        )
        assert "v0.31.1" in text, (
            f"{source_relpath} must name the v0.31.1 deferral"
        )


def test_unsupported_pysindy_generation_message_path_exists_in_prototype() -> None:
    """The private prototype's unsupported-generation guard raises with a
    message that names the observed pysindy version and points at the
    migration audit document.
    """
    from pdelie.discovery import _pysindy2_prototype

    class _FakePysindy:
        __version__ = "3.0.0"

    with pytest.raises(_pysindy2_prototype.UnsupportedPySINDyGenerationError) as excinfo:
        _pysindy2_prototype._detect_pysindy_api_generation(_FakePysindy())
    assert "3" in str(excinfo.value)
    assert "PYSINDY_2_MIGRATION_AUDIT" in str(excinfo.value)


# ---------------------------------------------------------------------------
# 4. No public schema changed by the research spike.
# ---------------------------------------------------------------------------


def test_v0_31_1a_does_not_change_discovery_task_result_schema() -> None:
    """discovery_task_result stays 22 keys per the v0.31.0 release close."""
    from pdelie.tasks import discovery as discovery_module

    top_level = discovery_module._TASK_RESULT_TOP_LEVEL_KEYS
    assert len(top_level) == 22


def test_v0_31_1a_does_not_change_weak_diagnostic_schema() -> None:
    """pdelie_weak_pde_library_diagnostic stays 27 keys."""
    from pdelie.tasks import weak_pde_library as weak_module

    top_level = getattr(
        weak_module, "_DIAGNOSTIC_TOP_LEVEL_KEYS", None
    ) or getattr(weak_module, "_SUMMARY_TOP_LEVEL_KEYS", None)
    assert top_level is not None
    assert len(top_level) == 27


def test_v0_31_1a_public_schema_invariance_guarantee_recorded() -> None:
    """The compatibility matrix's ``public_schema_invariance_guarantee`` block
    documents both key counts. If either drifts, this assertion fires.
    """
    guarantee = _matrix()["public_schema_invariance_guarantee"]
    assert guarantee["discovery_task_result_key_count"] == 22
    assert guarantee["pdelie_weak_pde_library_diagnostic_key_count"] == 27


# ---------------------------------------------------------------------------
# 5. No root export changed by the research spike.
# ---------------------------------------------------------------------------


def test_v0_31_1a_no_new_root_exports() -> None:
    """The research spike must not leak any new attribute to root ``pdelie``.

    In particular, none of the prototype module or its symbols may be
    exposed at package root.
    """
    for forbidden in (
        "_pysindy2_prototype",
        "_detect_pysindy_api_generation",
        "UnsupportedPySINDyGenerationError",
        "runtime_compatibility_matrix",
        "SUPPORTED_PYSINDY_GENERATIONS",
    ):
        assert not hasattr(pdelie, forbidden), (
            f"root pdelie must not export {forbidden!r} after v0.31.1a"
        )


# ---------------------------------------------------------------------------
# 6. Legacy and modern results use the same canonical term mapping.
# ---------------------------------------------------------------------------


def test_legacy_and_modern_share_the_term_mapping_anchor() -> None:
    """The v0.31b0 golden fixture pinning the pysindy feature-name grammar
    (``x0``, ``x0^2``, ``x0_1``, ``x0x0_1``, ...) is documented as
    byte-identical across pysindy 1.x and 2.x. This test verifies the
    golden fixture module exists and can be imported — the actual
    per-generation replay lives in the v0.32 migration PR.
    """
    golden_path = _REPO_ROOT / "tests" / "test_v0_31b0_pysindy_term_mapping_golden.py"
    assert golden_path.exists(), (
        "v0.31b0 term-mapping golden fixture is the anchor across "
        "pysindy generations; must remain present"
    )
    # Cross-reference in the migration audit document.
    assert "v0_31b0_pysindy_term_mapping_golden" in _audit_text()


# ---------------------------------------------------------------------------
# 7. NaN/Inf remains rejected — the strict-JSON boundary is unchanged.
# ---------------------------------------------------------------------------


def test_strict_json_validator_still_rejects_nan_and_inf() -> None:
    """The v0.31b1/b2 composition boundary continues to reject NaN/Inf.

    This is a smoke check that the research spike did not remove or
    weaken the strict-JSON validator on which both v0.31 report schemas
    depend.
    """
    from pdelie.errors import SchemaValidationError
    from pdelie.reporting.summaries import _validate_strict_json_compatible

    with pytest.raises(SchemaValidationError):
        _validate_strict_json_compatible(
            {"x": float("nan")}, name="v0_31_1a_nan_guard"
        )
    with pytest.raises(SchemaValidationError):
        _validate_strict_json_compatible(
            {"x": float("inf")}, name="v0_31_1a_inf_guard"
        )


# ---------------------------------------------------------------------------
# 8. Prototype generation-detection does not silently catch arbitrary
# exceptions.
# ---------------------------------------------------------------------------


def test_prototype_generation_detection_does_not_catch_arbitrary_exceptions() -> None:
    """AST-inspect the prototype module and assert it does NOT use
    ``except Exception`` / ``except BaseException`` clauses.

    The v0.31c1 policy tests apply the same invariant to any future
    ``_pysindy_compat.py``. v0.31.1a extends it to the prototype so a
    future rewrite of the shim cannot silently regress.
    """
    import ast

    prototype_path = (
        _REPO_ROOT / "src" / "pdelie" / "discovery" / "_pysindy2_prototype.py"
    )
    tree = ast.parse(prototype_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            # A bare `except:` has no `type`; a broad `except Exception:` /
            # `except BaseException:` has an `ast.Name` type. Reject both.
            if node.type is None:
                pytest.fail("prototype uses a bare `except:` clause")
            if isinstance(node.type, ast.Name) and node.type.id in (
                "Exception",
                "BaseException",
            ):
                pytest.fail(
                    f"prototype uses a broad `except {node.type.id}:` clause"
                )


# ---------------------------------------------------------------------------
# 9. Prototype does not affect legacy 1.x behavior.
# ---------------------------------------------------------------------------


def test_prototype_is_not_imported_by_any_production_module() -> None:
    """The prototype must not be imported by any non-test module today.

    We enforce this by grepping the source tree; if a v0.31.1 / v0.32
    implementation PR wires the shim in, that PR must also delete or
    promote the prototype (and this assertion will need updating in the
    same PR).
    """
    src_dir = _REPO_ROOT / "src"
    offenders: list[str] = []
    for path in src_dir.rglob("*.py"):
        if path.name == "_pysindy2_prototype.py":
            continue
        text = path.read_text(encoding="utf-8")
        if "_pysindy2_prototype" in text:
            offenders.append(str(path.relative_to(_REPO_ROOT)))
    assert not offenders, (
        f"prototype must not be imported by any production module; "
        f"offenders: {offenders!r}"
    )


def test_prototype_module_is_private() -> None:
    """The prototype module lives under a leading-underscore filename (so it
    is private by convention) and is NOT re-exported as a public name from
    ``pdelie.discovery.__init__`` or ``pdelie.tasks.__init__``. It is
    normal Python for the submodule attribute ``_pysindy2_prototype`` to
    appear in ``dir(pdelie.discovery)`` — the underscore is the private
    marker. What must NOT happen is a public alias (no leading underscore)
    that resolves to the prototype's symbols.
    """
    from pdelie import discovery as discovery_pkg
    from pdelie import tasks as tasks_pkg

    for pkg in (discovery_pkg, tasks_pkg):
        public_names = [
            name for name in dir(pkg) if not name.startswith("_")
        ]
        # No public alias may resolve to the prototype's symbols.
        for public_name in public_names:
            value = getattr(pkg, public_name)
            module_name = getattr(value, "__module__", "") or ""
            assert not module_name.endswith("_pysindy2_prototype"), (
                f"public name {pkg.__name__}.{public_name!r} resolves to "
                f"a symbol from the private prototype module "
                f"({module_name!r}); prototype must stay private"
            )
        # Belt-and-suspenders: the exception class must not appear under a
        # public alias either.
        assert "UnsupportedPySINDyGenerationError" not in public_names, (
            f"UnsupportedPySINDyGenerationError leaked to public surface "
            f"on {pkg.__name__}"
        )


# ---------------------------------------------------------------------------
# 10. SPEC 0 policy statements are recorded.
# ---------------------------------------------------------------------------


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
    exceptions = matrix["temporary_exceptions"]
    assert len(exceptions) >= 1
    for entry in exceptions:
        assert isinstance(entry["exception"], str) and entry["exception"]
        assert isinstance(entry["owner_milestone"], str) and entry["owner_milestone"]
        assert isinstance(entry["removed_by"], str) and entry["removed_by"]
        # No exception may live past v0.32.
        assert re.match(r"^v?0\.3[12](?:\.\d+|_.*)?$", entry["removed_by"]), (
            f"temporary exception must retire by v0.32; got "
            f"{entry['removed_by']!r} for {entry['exception']!r}"
        )
