"""Tests for the v0.30b BoundaryConditionSpec helpers."""
from __future__ import annotations

import json

import pytest

from pdelie._boundary import (
    ALLOWED_BOUNDARY_FACE_SOURCES,
    ALLOWED_X_BOUNDARY_TYPES,
    BoundaryConditionSpec,
    BoundaryFace,
    get_x_boundary_type,
    is_x_periodic,
    normalize_x_boundary_condition,
)
from pdelie.errors import SchemaValidationError, ScopeValidationError


# --- normalize_x_boundary_condition --------------------------------------


def test_normalize_legacy_periodic_string_yields_structured_periodic() -> None:
    result = normalize_x_boundary_condition("periodic")
    assert result["type"] == "periodic"
    assert result["left"] is None
    assert result["right"] is None
    assert result["specified"] is True


def test_normalize_legacy_open_string_renames_to_open_unknown() -> None:
    result = normalize_x_boundary_condition("open")
    assert result["type"] == "open_unknown"
    assert result["left"] is None
    assert result["right"] is None
    assert result["specified"] is False
    assert "normalized from legacy 0.1 string" in result["notes"]


def test_normalize_legacy_open_unknown_string_yields_open_unknown() -> None:
    result = normalize_x_boundary_condition("open_unknown")
    assert result["type"] == "open_unknown"
    assert result["specified"] is False


def test_normalize_legacy_dirichlet_string_marks_specified_false() -> None:
    """The library never invents boundary values: legacy "dirichlet" → specified=False."""
    result = normalize_x_boundary_condition("dirichlet")
    assert result["type"] == "dirichlet"
    assert result["specified"] is False
    for face in (result["left"], result["right"]):
        assert face["value"] is None
        assert face["source"] == "inferred_unspecified"


def test_normalize_legacy_neumann_string_marks_specified_false() -> None:
    result = normalize_x_boundary_condition("neumann")
    assert result["type"] == "neumann"
    assert result["specified"] is False


def test_normalize_rejects_unsupported_legacy_string() -> None:
    with pytest.raises(ScopeValidationError, match="Unsupported x boundary string"):
        normalize_x_boundary_condition("insulating")


def test_normalize_rejects_non_string_non_mapping() -> None:
    for bad_value in (42, 3.14, True, None, ["periodic"]):
        with pytest.raises(SchemaValidationError):
            normalize_x_boundary_condition(bad_value)


def test_normalize_structured_periodic_round_trips() -> None:
    structured = {
        "type": "periodic",
        "left": None,
        "right": None,
        "specified": True,
        "notes": None,
    }
    result = normalize_x_boundary_condition(structured)
    assert result["type"] == "periodic"
    assert result["specified"] is True


def test_normalize_structured_dirichlet_with_user_values_marks_specified_true() -> None:
    structured = {
        "type": "dirichlet",
        "left": {"value": 0.0, "time_dependent": False, "source": "user_supplied"},
        "right": {"value": 1.0, "time_dependent": False, "source": "user_supplied"},
    }
    result = normalize_x_boundary_condition(structured)
    assert result["type"] == "dirichlet"
    assert result["specified"] is True
    assert result["left"]["value"] == 0.0
    assert result["right"]["value"] == 1.0


def test_normalize_structured_dirichlet_without_values_marks_specified_false() -> None:
    structured = {
        "type": "dirichlet",
        "left": {"value": None, "time_dependent": False, "source": "inferred_unspecified"},
        "right": {"value": None, "time_dependent": False, "source": "inferred_unspecified"},
    }
    result = normalize_x_boundary_condition(structured)
    assert result["specified"] is False


def test_normalize_structured_periodic_rejects_left_or_right_face() -> None:
    bad = {"type": "periodic", "left": {"value": 0.0, "time_dependent": False, "source": "user_supplied"}, "right": None}
    with pytest.raises(SchemaValidationError, match="Periodic boundary spec"):
        normalize_x_boundary_condition(bad)


def test_normalize_structured_open_unknown_rejects_faces() -> None:
    bad = {
        "type": "open_unknown",
        "left": {"value": 0.0, "time_dependent": False, "source": "user_supplied"},
        "right": None,
    }
    with pytest.raises(SchemaValidationError, match="open_unknown"):
        normalize_x_boundary_condition(bad)


def test_normalize_rejects_unsupported_type_key() -> None:
    with pytest.raises(ScopeValidationError, match="BoundaryConditionSpec.type"):
        normalize_x_boundary_condition({"type": "robin"})


# --- BoundaryFace dataclass ----------------------------------------------


def test_boundary_face_to_dict_and_from_dict_round_trip() -> None:
    face = BoundaryFace(value=2.5, time_dependent=False, source="user_supplied")
    payload = face.to_dict()
    assert payload == {"value": 2.5, "time_dependent": False, "source": "user_supplied"}
    rebuilt = BoundaryFace.from_dict(payload)
    assert rebuilt == face


def test_boundary_face_accepts_none_value() -> None:
    face = BoundaryFace(value=None, time_dependent=False, source="inferred_unspecified")
    payload = face.to_dict()
    assert payload["value"] is None
    rebuilt = BoundaryFace.from_dict(payload)
    assert rebuilt.value is None


def test_boundary_face_rejects_non_finite_value() -> None:
    with pytest.raises(SchemaValidationError, match="finite"):
        BoundaryFace.from_dict({"value": float("inf"), "time_dependent": False, "source": "user_supplied"})


def test_boundary_face_rejects_unknown_source() -> None:
    with pytest.raises(SchemaValidationError, match="BoundaryFace.source"):
        BoundaryFace.from_dict({"value": 0.0, "time_dependent": False, "source": "guessed"})


# --- BoundaryConditionSpec dataclass --------------------------------------


def test_boundary_condition_spec_to_dict_and_from_dict_round_trip() -> None:
    face = BoundaryFace(value=0.0, time_dependent=False, source="user_supplied")
    spec = BoundaryConditionSpec(
        type="dirichlet", left=face, right=face, specified=True, notes="test"
    )
    payload = spec.to_dict()
    rebuilt = BoundaryConditionSpec.from_dict(payload)
    assert rebuilt == spec


# --- get_x_boundary_type / is_x_periodic ----------------------------------


def test_get_x_boundary_type_accepts_legacy_string_and_returns_canonical() -> None:
    for legacy, canonical in (
        ("periodic", "periodic"),
        ("dirichlet", "dirichlet"),
        ("neumann", "neumann"),
        ("open", "open_unknown"),
        ("open_unknown", "open_unknown"),
    ):
        metadata = {"boundary_conditions": {"x": legacy}}
        assert get_x_boundary_type(metadata) == canonical


def test_get_x_boundary_type_accepts_structured_dict() -> None:
    metadata = {"boundary_conditions": {"x": {"type": "dirichlet", "specified": False}}}
    assert get_x_boundary_type(metadata) == "dirichlet"


def test_get_x_boundary_type_accepts_field_like_object_with_metadata_attr() -> None:
    class _Stub:
        metadata = {"boundary_conditions": {"x": "periodic"}}

    assert get_x_boundary_type(_Stub()) == "periodic"


def test_get_x_boundary_type_rejects_unsupported_string() -> None:
    metadata = {"boundary_conditions": {"x": "robin"}}
    with pytest.raises(ScopeValidationError, match="Unsupported x boundary string"):
        get_x_boundary_type(metadata)


def test_get_x_boundary_type_rejects_unsupported_structured_type() -> None:
    metadata = {"boundary_conditions": {"x": {"type": "robin"}}}
    with pytest.raises(ScopeValidationError, match="BoundaryConditionSpec.type"):
        get_x_boundary_type(metadata)


def test_get_x_boundary_type_rejects_malformed_metadata() -> None:
    with pytest.raises(SchemaValidationError):
        get_x_boundary_type({"boundary_conditions": "periodic"})
    with pytest.raises(SchemaValidationError):
        get_x_boundary_type({"boundary_conditions": {"x": 42}})


def test_is_x_periodic_returns_true_for_legacy_and_structured_periodic() -> None:
    assert is_x_periodic({"boundary_conditions": {"x": "periodic"}}) is True
    assert is_x_periodic({"boundary_conditions": {"x": {"type": "periodic", "left": None, "right": None, "specified": True}}}) is True


def test_is_x_periodic_returns_false_for_supported_nonperiodic() -> None:
    for non_periodic in ("dirichlet", "neumann", "open", "open_unknown"):
        assert is_x_periodic({"boundary_conditions": {"x": non_periodic}}) is False


# --- strict JSON ---------------------------------------------------------


def test_normalize_output_is_strict_json_compatible() -> None:
    for x_bc in ("periodic", "dirichlet", "neumann", "open_unknown"):
        result = normalize_x_boundary_condition(x_bc)
        # Strict round-trip with allow_nan=False is the project's reporting discipline.
        assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_allowed_constants_are_frozen_and_match_documented_set() -> None:
    assert isinstance(ALLOWED_X_BOUNDARY_TYPES, frozenset)
    assert ALLOWED_X_BOUNDARY_TYPES == frozenset(
        {"periodic", "dirichlet", "neumann", "open_unknown"}
    )
    assert isinstance(ALLOWED_BOUNDARY_FACE_SOURCES, frozenset)
    assert ALLOWED_BOUNDARY_FACE_SOURCES == frozenset(
        {"user_supplied", "default", "inferred_unspecified"}
    )
