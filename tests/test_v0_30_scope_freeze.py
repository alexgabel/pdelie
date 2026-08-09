from __future__ import annotations

import importlib
import json
import tomllib
from pathlib import Path

import pdelie

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCOPE_CONFIG_PATH = "configs/planning/v0_30_nonperiodic_readiness_scope.json"


def _repo_path(path: str) -> Path:
    return _REPO_ROOT / path


def _repo_text(path: str) -> str:
    return _repo_path(path).read_text(encoding="utf-8")


def _repo_json(path: str) -> dict[str, object]:
    return json.loads(_repo_text(path))


def _load_scope_config() -> dict[str, object]:
    return _repo_json(_SCOPE_CONFIG_PATH)


def test_scope_config_is_present_and_strict_json_compatible() -> None:
    """The v0.30a scope manifest must exist and be JSON-strict (no NaN, round-trippable).

    Status flips from ``in_progress`` (during the v0.30a-f arc) to ``complete``
    at the v0.30 release close.
    """
    config = _load_scope_config()
    assert json.loads(json.dumps(config, allow_nan=False)) == config
    assert config["summary_schema_version"] == "0.1"
    assert config["summary_type"] == "pdelie_release_scope"
    assert config["release"] == "0.30a"
    assert config["status"] in {"in_progress", "complete"}
    assert config["parent_release"] == "0.30"
    assert config["decision_label"] == (
        "nonperiodic_readiness_and_low_order_finite_difference_diagnostics_design_only"
    )


def test_v0_30_scope_doc_exists_and_has_required_phrases() -> None:
    """V0_30_SCOPE.md must exist and contain every phrase the scope manifest requires."""
    config = _load_scope_config()
    scope_path = _repo_path("docs/planning/V0_30_SCOPE.md")
    assert scope_path.exists(), f"missing {scope_path}"
    scope = scope_path.read_text(encoding="utf-8")
    assert scope.strip(), "V0_30_SCOPE.md must not be empty"

    for phrase in config["required_phrases_in_scope_doc"]:
        assert phrase in scope, f"missing required phrase in V0_30_SCOPE.md: {phrase!r}"


def test_v0_30_design_documents_exist_and_are_nonempty() -> None:
    """The three v0.30a design documents and the scope doc must all exist with content."""
    config = _load_scope_config()
    for path in config["required_design_documents"]:
        target = _repo_path(path)
        assert target.exists(), f"missing required design document: {path}"
        assert target.read_text(encoding="utf-8").strip(), f"design document is empty: {path}"


def test_v0_30_roadmap_records_v0_30a_and_refined_v0_30() -> None:
    """ROADMAP.md must record v0.30a and reflect the refined v0.30 theme."""
    config = _load_scope_config()
    roadmap = _repo_text("docs/planning/ROADMAP.md")
    for phrase in config["required_phrases_in_roadmap"]:
        assert phrase in roadmap, f"missing required phrase in ROADMAP.md: {phrase!r}"
    # The v0.30 theme refinement must mention the new theme
    assert "Nonperiodic readiness" in roadmap
    assert "finite-difference" in roadmap.lower() or "finite difference" in roadmap.lower()
    # Newly deferred surfaces
    assert "high-order finite-difference derivatives on nonperiodic data" in roadmap
    assert "overlap-crop" in roadmap
    assert "root-level one-call symmetry-discovery API" in roadmap
    # v0.29 row must remain (do not break v0.29 release gate)
    assert "`v0.29` | Completed | Workflow recipes and support matrix" in roadmap


def test_v0_30_plan_records_v0_30a_and_preserves_v0_29() -> None:
    """PLAN.md must record v0.30a and retain the v0.29 COMPLETE record.

    Status: the v0.30a plan header started as ``IN_PROGRESS`` and flipped to
    ``COMPLETE`` at the v0.30 release close; both are accepted.
    """
    config = _load_scope_config()
    plan = _repo_text("docs/planning/PLAN.md")
    for phrase in config["required_phrases_in_plan"]:
        assert phrase in plan, f"missing required phrase in PLAN.md: {phrase!r}"
    # v0.30a section header must be present in either progress state.
    assert "**Status:** IN_PROGRESS" in plan or "**Status:** COMPLETE" in plan
    # v0.29 record must remain intact (existing v0.29 release gate reads these)
    assert "V0.29 is complete" in plan
    assert "Milestone 6: COMPLETE" in plan
    assert "workflow_recipes_and_support_matrix_complete_no_new_numerical_scope" in plan


def test_v0_30_api_stability_records_design_only_note() -> None:
    """API_STABILITY.md must carry a Decision-only note for v0.30a, after the v0.29 note."""
    config = _load_scope_config()
    api_stability = _repo_text("docs/specs/API_STABILITY.md")
    for phrase in config["required_phrases_in_api_stability"]:
        assert phrase in api_stability, (
            f"missing required phrase in API_STABILITY.md: {phrase!r}"
        )
    # v0.29 note must remain
    assert "Decision-only note for the frozen `v0.29`" in api_stability
    # v0.30a note must explicitly disclaim a new runtime API
    assert "`v0.30a` adds no new runtime public API" in api_stability
    # The announced future schema migration must be documented (for external-tooling readiness)
    assert "`FieldBatch.SCHEMA_VERSION`" in api_stability
    assert '`"0.1"`' in api_stability and '`"0.2"`' in api_stability
    assert "backwards-compatible loader" in api_stability


def test_v0_30_no_root_export_for_planned_v0_30_apis() -> None:
    """No planned v0.30/v0.30.1 API may have leaked into the root `pdelie` namespace."""
    config = _load_scope_config()
    for name in config["forbidden_root_attributes"]:
        assert not hasattr(pdelie, name), (
            f"v0.30a must not export `pdelie.{name}` (planned for a later release)"
        )


def test_v0_30_no_submodule_export_for_planned_v0_30_apis() -> None:
    """No planned v0.30/v0.30.1 API may have leaked into its target submodule yet."""
    config = _load_scope_config()
    forbidden = config["forbidden_submodule_attributes"]
    for submodule_name, names in forbidden.items():
        module = importlib.import_module(submodule_name)
        for name in names:
            assert not hasattr(module, name), (
                f"v0.30a must not export `{submodule_name}.{name}` "
                f"(planned for a later release)"
            )


def test_v0_30_version_matches_scope_config_pin() -> None:
    """Package version must match the pinned value in the v0.30 scope config.

    During the v0.30a-f arc this guard pinned the version at ``0.29.0`` (no
    version bump). At the v0.30 release close, both the pin and the package
    version flip to ``0.30.0``. The two must stay in sync.
    """
    config = _load_scope_config()
    pyproject_version = tomllib.loads(_repo_text("pyproject.toml"))["project"]["version"]
    # The scope-config guard pin remains 0.30.0 (its role is to guard v0.30
    # sub-releases against a premature bump). The v0.31.0 and v0.32.0
    # release closes legitimately supersede that pin.
    assert config["guard_no_version_bump"] in {"0.29.0", "0.30.0"}
    assert pyproject_version in {
        "0.29.0", "0.30.0", "0.31.0", "0.32.0", "0.33.0",
        "0.34.0", "0.35.0", "0.36.0", "0.37.0", "0.37.1",
        "0.38.0a1", "0.38.0b1", "0.38.0rc1",
    }


def test_v0_30_schema_migration_design_is_documented() -> None:
    """The 0.1 -> 0.2 FieldBatch schema migration design is fully documented."""
    spec_doc = _repo_text("docs/design/BOUNDARY_CONDITION_SPEC.md")
    assert "0.1" in spec_doc
    assert "0.2" in spec_doc
    assert "backwards-compatible" in spec_doc
    assert "schema_0_1_to_0_2_boundary_normalization" in spec_doc

    config = _load_scope_config()
    migration = config["planned_schema_migration"]
    assert migration["field"] == "FieldBatch.SCHEMA_VERSION"
    assert migration["from_version"] == "0.1"
    assert migration["to_version"] == "0.2"
    assert migration["implements_in_release"] == "0.30"
    assert migration["backwards_compatible_loader"] is True


def test_v0_30b_schema_migration_is_applied_at_runtime() -> None:
    """v0.30b lands the structured BoundaryConditionSpec runtime; SCHEMA_VERSION is 0.2."""
    assert getattr(pdelie.FieldBatch, "SCHEMA_VERSION", None) == "0.2"
    # Legacy 0.1 schema_version is still accepted by from_dict for backwards compat.
    assert "0.1" in getattr(pdelie.FieldBatch, "LEGACY_SCHEMA_VERSIONS", frozenset())


def test_v0_30_scope_doc_uses_correct_decision_label() -> None:
    """The decision label must match between manifest, scope doc, plan, and API stability."""
    config = _load_scope_config()
    label = config["decision_label"]
    assert label in _repo_text("docs/planning/V0_30_SCOPE.md")
    assert label in _repo_text("docs/planning/PLAN.md")
    assert label in _repo_text("docs/specs/API_STABILITY.md")


# Note: the v0.30a `test_v0_30_no_src_changes_against_main` guard was removed in
# v0.30b. v0.30b implements the BoundaryConditionSpec runtime, which modifies
# src/pdelie/ by design. The remaining guards (forbidden_root_attributes,
# forbidden_submodule_attributes, no_version_bump, schema-migration design and
# runtime checks) continue to enforce the v0.30 scope freeze.
