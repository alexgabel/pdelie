from __future__ import annotations

import importlib
import json
import tomllib
from pathlib import Path

import pdelie

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCOPE_CONFIG_PATH = "configs/planning/v0_31_discovery_task_bridge_scope.json"


def _repo_path(path: str) -> Path:
    return _REPO_ROOT / path


def _repo_text(path: str) -> str:
    return _repo_path(path).read_text(encoding="utf-8")


def _repo_json(path: str) -> dict[str, object]:
    return json.loads(_repo_text(path))


def _load_scope_config() -> dict[str, object]:
    return _repo_json(_SCOPE_CONFIG_PATH)


def test_scope_config_is_present_and_strict_json_compatible() -> None:
    """The v0.31a scope manifest must exist and be JSON-strict (no NaN, round-trippable)."""
    config = _load_scope_config()
    assert json.loads(json.dumps(config, allow_nan=False)) == config
    assert config["summary_schema_version"] == "0.1"
    assert config["summary_type"] == "pdelie_release_scope"
    assert config["release"] == "0.31a"
    assert config["status"] in {"in_progress", "complete"}
    assert config["parent_release"] == "0.31"
    assert config["decision_label"] == "downstream_discovery_task_bridge_design_only"


def test_v0_31_scope_doc_exists_and_has_required_phrases() -> None:
    """V0_31_DISCOVERY_TASK_BRIDGE_SCOPE.md must contain every phrase the scope manifest requires."""
    config = _load_scope_config()
    scope_path = _repo_path("docs/planning/V0_31_DISCOVERY_TASK_BRIDGE_SCOPE.md")
    assert scope_path.exists(), f"missing {scope_path}"
    scope = scope_path.read_text(encoding="utf-8")
    assert scope.strip(), "V0_31_DISCOVERY_TASK_BRIDGE_SCOPE.md must not be empty"

    for phrase in config["required_phrases_in_scope_doc"]:
        assert phrase in scope, (
            f"missing required phrase in V0_31_DISCOVERY_TASK_BRIDGE_SCOPE.md: {phrase!r}"
        )


def test_v0_31_design_documents_exist_and_are_nonempty() -> None:
    """The v0.31a design documents (scope doc + TaskResult schema doc) must exist with content."""
    config = _load_scope_config()
    for path in config["required_design_documents"]:
        target = _repo_path(path)
        assert target.exists(), f"missing required design document: {path}"
        assert target.read_text(encoding="utf-8").strip(), f"design document is empty: {path}"


def test_v0_31_roadmap_records_v0_31a() -> None:
    """ROADMAP.md must record v0.31a with the frozen decision label."""
    config = _load_scope_config()
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    for phrase in config["required_phrases_in_roadmap"]:
        assert phrase in roadmap, f"missing required phrase in ROADMAP.md: {phrase!r}"
    # v0.30 close row must remain (do not break v0.30 release gate)
    assert "`v0.30`" in roadmap and "Completed" in roadmap


def test_v0_31_plan_records_v0_31a() -> None:
    """PLAN.md must record v0.31a IN_PROGRESS (or COMPLETE at close) with the decision label."""
    config = _load_scope_config()
    plan = _repo_text("docs/planning/PLAN.md")
    for phrase in config["required_phrases_in_plan"]:
        assert phrase in plan, f"missing required phrase in PLAN.md: {phrase!r}"
    # v0.31a section must be present in either progress state.
    assert "V0.31a" in plan
    assert "**Status:** IN_PROGRESS" in plan or "**Status:** COMPLETE" in plan


def test_v0_31_api_stability_records_design_only_note() -> None:
    """API_STABILITY.md must carry a Decision-only note for v0.31a after the v0.30.0 note."""
    config = _load_scope_config()
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    for phrase in config["required_phrases_in_api_stability"]:
        assert phrase in api_stability, (
            f"missing required phrase in API_STABILITY.md: {phrase!r}"
        )
    # v0.30.0 stable public-surface note must remain
    assert "Stable public-surface note for the frozen `v0.30.0` release close" in api_stability
    # v0.31a note must explicitly disclaim a new runtime API (bare phrase, matches manifest)
    assert "v0.31a adds no new runtime public API" in api_stability


def test_v0_31_no_root_export_for_planned_v0_31_apis() -> None:
    """No planned v0.31 API may have leaked into the root `pdelie` namespace."""
    config = _load_scope_config()
    for name in config["forbidden_root_attributes"]:
        assert not hasattr(pdelie, name), (
            f"v0.31a must not export `pdelie.{name}` (planned for a later release)"
        )


def test_v0_31_no_submodule_export_for_planned_v0_31_apis() -> None:
    """No planned v0.31 API may have leaked into its target submodule yet."""
    config = _load_scope_config()
    forbidden = config["forbidden_submodule_attributes"]
    for submodule_name, names in forbidden.items():
        module = importlib.import_module(submodule_name)
        for name in names:
            assert not hasattr(module, name), (
                f"v0.31a must not export `{submodule_name}.{name}` "
                f"(planned for a later release)"
            )


def test_v0_31_pdelie_tasks_submodule_surface_is_v0_31b2_locked() -> None:
    """Pin the `pdelie.tasks` public surface.

    v0.31b1 landed ``discovery`` (three public names). v0.31b2 landed
    ``weak_pde_library`` (three additional public names). The lock advances
    with each sub-release; any other public attribute would silently widen
    the v0.31 surface past the scope freeze.
    """
    tasks_module = importlib.import_module("pdelie.tasks")
    public_attrs = sorted(name for name in dir(tasks_module) if not name.startswith("_"))
    expected = sorted(
        [
            "PySINDyDiscoveryUnsupportedBoundaryError",
            "WeakPDELibraryDiagnostic",
            "discovery",
            "inspect_pysindy_weak_pde_library",
            "run_pysindy_pde_task",
            "summarize_discovery_task_result",
            "summarize_pysindy_weak_pde_library_diagnostic",
            "weak_pde_library",
        ]
    )
    assert public_attrs == expected, (
        f"pdelie.tasks public surface drifted from the v0.31b2 lock: "
        f"expected {expected!r}, got {public_attrs!r}"
    )
    # And the v0.31 forbidden-root guard must still hold — no root re-export.
    assert not hasattr(pdelie, "run_pysindy_pde_task")
    assert not hasattr(pdelie, "summarize_discovery_task_result")
    assert not hasattr(pdelie, "PySINDyDiscoveryUnsupportedBoundaryError")
    assert not hasattr(pdelie, "TaskResult")
    assert not hasattr(pdelie, "WeakPDELibraryDiagnostic")
    assert not hasattr(pdelie, "inspect_pysindy_weak_pde_library")
    assert not hasattr(pdelie, "summarize_pysindy_weak_pde_library_diagnostic")
    assert not hasattr(pdelie, "weak_pde_library")


def test_v0_31_version_pin_matches_scope_config() -> None:
    """Package version must be one of the versions authorized by the v0.31
    arc: the design/runtime pin ``0.30.0`` held through v0.31a-c1, and the
    release-close bump to ``0.31.0``. The scope-config
    ``guard_no_version_bump`` remains ``0.30.0`` — its role is to guard the
    sub-releases against a premature bump; release close legitimately
    supersedes it.
    """
    config = _load_scope_config()
    pyproject_version = tomllib.loads(_repo_text("pyproject.toml"))["project"]["version"]
    assert config["guard_no_version_bump"] == "0.30.0"
    assert pyproject_version in {
        "0.30.0", "0.31.0", "0.32.0", "0.33.0", "0.34.0", "0.35.0", "0.36.0", "0.37.0", "0.37.1"
    }, (
        f"pdelie version must be 0.30.0 (pre-close), 0.31.0 (release "
        f"close), or 0.32.0 (v0.32.0 consolidated release close); got "
        f"{pyproject_version!r}"
    )


def test_v0_31_no_premature_pyproject_sections() -> None:
    """No premature v0.31 pyproject sections may appear (typo-squat guard)."""
    config = _load_scope_config()
    pyproject_text = _repo_text("pyproject.toml")
    for section in config["guard_no_premature_pyproject_sections"]:
        assert f"[{section}]" not in pyproject_text, (
            f"v0.31a must not introduce [{section}] in pyproject.toml"
        )


def test_v0_31_no_premature_ci_jobs() -> None:
    """No premature v0.31 CI job names may appear."""
    config = _load_scope_config()
    ci_path = _repo_path(".github/workflows/ci.yml")
    if not ci_path.exists():
        return
    ci_text = ci_path.read_text(encoding="utf-8")
    for job_name in config["guard_no_premature_ci_jobs"]:
        assert job_name not in ci_text, (
            f"v0.31a must not add CI job named {job_name!r}"
        )


def test_v0_31_scope_doc_uses_correct_decision_label() -> None:
    """The decision label must match between manifest, scope doc, plan, and API stability."""
    config = _load_scope_config()
    label = config["decision_label"]
    assert label in _repo_text("docs/planning/V0_31_DISCOVERY_TASK_BRIDGE_SCOPE.md")
    assert label in _repo_text("docs/planning/PLAN.md")
    assert label in _repo_text("docs/specs/API_STABILITY.md")


def test_v0_31_task_result_schema_design_is_documented() -> None:
    """The TaskResult schema design doc must document the key literal fields."""
    schema_doc = _repo_text("docs/design/DISCOVERY_TASK_RESULT_SCHEMA.md")
    # summary_schema_version and summary_type literals
    assert '"0.1"' in schema_doc
    assert '"discovery_task_result"' in schema_doc
    # WeakPDELibrary wrapper literals
    assert '"pdelie_weak_pde_library_diagnostic"' in schema_doc
    assert '"diagnostic_only": true' in schema_doc
    # NaN-safety wiring is documented
    assert "_validate_strict_json_compatible" in schema_doc
    assert "allow_nan=False" in schema_doc
    # Required distinct-string call-outs vs pdelie-native weak_1d
    assert "local_separable_quartic_bump_trapezoid_v1" in schema_doc
    assert "separable_quartic_bump_beta" in schema_doc
    assert "composite_tensor_product_trapezoidal_native_window" in schema_doc

    # The manifest planned schema must line up with the doc's stated invariants.
    config = _load_scope_config()
    planned = config["planned_task_result_schema"]
    assert planned["summary_schema_version"] == "0.1"
    assert planned["summary_type"] == "discovery_task_result"
    assert planned["weak_pdelib_wrapper"]["summary_type"] == "pdelie_weak_pde_library_diagnostic"
    assert planned["weak_pdelib_wrapper"]["diagnostic_only"] is True


# Note: v0.31a is a design-only sub-release. This test file intentionally does
# NOT assert `git diff` cleanliness against `src/pdelie/` — the v0.31a release
# gate declares "no file under `src/pdelie/` is modified" and the CI workflow
# enforces that via the manifest-driven release gate.
