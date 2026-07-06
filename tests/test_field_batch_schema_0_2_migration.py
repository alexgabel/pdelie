"""Tests for v0.30b FieldBatch schema 0.1 -> 0.2 migration."""
from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie import FieldBatch
from pdelie._boundary import LEGACY_BOUNDARY_NORMALIZATION_OPERATION
from pdelie.data import generate_heat_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.errors import SchemaValidationError


def _legacy_payload(
    *,
    schema_version: str = "0.1",
    x_boundary: str | dict | None = "periodic",
    include_boundary_conditions: bool = True,
) -> dict:
    metadata = {
        "coordinate_system": "cartesian",
        "grid_regularity": "uniform",
        "grid_type": "rectilinear",
        "parameter_tags": {"nu": 0.1},
    }
    if include_boundary_conditions:
        metadata["boundary_conditions"] = {"x": x_boundary}
    x = np.linspace(0.0, 2.0 * np.pi, 8, endpoint=False, dtype=float)
    t = np.linspace(0.0, 0.2, 4, dtype=float)
    return {
        "schema_version": schema_version,
        "values": np.zeros((2, 4, 8, 1), dtype=float).tolist(),
        "dims": ["batch", "time", "x", "var"],
        "coords": {"time": t.tolist(), "x": x.tolist()},
        "var_names": ["u"],
        "metadata": metadata,
        "preprocess_log": [],
        "mask": None,
    }


# --- FieldBatch SCHEMA_VERSION is now 0.2 -------------------------------


def test_field_batch_class_var_schema_version_is_0_2() -> None:
    assert FieldBatch.SCHEMA_VERSION == "0.2"
    # Legacy 0.1 is still accepted by from_dict
    assert "0.1" in FieldBatch.LEGACY_SCHEMA_VERSIONS


def test_new_field_batch_default_schema_version_is_0_2() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=8, seed=0)
    assert field.schema_version == "0.2"


# --- Legacy 0.1 payloads load and validate ------------------------------


def test_from_dict_accepts_legacy_0_1_payload_with_periodic_string() -> None:
    payload = _legacy_payload(schema_version="0.1", x_boundary="periodic")
    field = FieldBatch.from_dict(payload)
    assert field.schema_version == "0.2"
    # Legacy periodic string is normalized to the structured form on load.
    bc = field.metadata["boundary_conditions"]["x"]
    assert isinstance(bc, dict)
    assert bc["type"] == "periodic"
    assert bc["specified"] is True
    # Migration provenance recorded.
    operations = [entry["operation"] for entry in field.preprocess_log]
    assert LEGACY_BOUNDARY_NORMALIZATION_OPERATION in operations


def test_from_dict_accepts_legacy_0_1_payload_with_dirichlet_string() -> None:
    payload = _legacy_payload(schema_version="0.1", x_boundary="dirichlet")
    field = FieldBatch.from_dict(payload)
    bc = field.metadata["boundary_conditions"]["x"]
    assert bc["type"] == "dirichlet"
    # Library does not invent values: specified=False after legacy-string migration.
    assert bc["specified"] is False
    assert bc["left"]["value"] is None
    assert bc["right"]["value"] is None
    operations = [entry["operation"] for entry in field.preprocess_log]
    assert LEGACY_BOUNDARY_NORMALIZATION_OPERATION in operations


def test_from_dict_accepts_legacy_0_1_payload_with_missing_boundary_conditions() -> None:
    payload = _legacy_payload(schema_version="0.1", include_boundary_conditions=False)
    field = FieldBatch.from_dict(payload)
    bc = field.metadata["boundary_conditions"]["x"]
    assert bc["type"] == "periodic"
    assert bc["specified"] is True
    operations = [entry["operation"] for entry in field.preprocess_log]
    assert LEGACY_BOUNDARY_NORMALIZATION_OPERATION in operations
    migration_entries = [
        entry for entry in field.preprocess_log
        if entry["operation"] == LEGACY_BOUNDARY_NORMALIZATION_OPERATION
    ]
    assert migration_entries[0]["parameters"]["default_x_boundary_string"] == "periodic"


def test_from_dict_rejects_unsupported_schema_version() -> None:
    payload = _legacy_payload(schema_version="9.9")
    with pytest.raises(SchemaValidationError, match="schema_version"):
        FieldBatch.from_dict(payload)


def test_from_dict_does_not_record_migration_for_already_0_2_payload() -> None:
    # Construct a 0.2 payload directly.
    field0 = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=8, seed=0)
    payload = field0.to_dict()
    assert payload["schema_version"] == "0.2"
    field1 = FieldBatch.from_dict(payload)
    operations = [entry["operation"] for entry in field1.preprocess_log]
    assert LEGACY_BOUNDARY_NORMALIZATION_OPERATION not in operations


# --- 0.2 round-trip preserves behavior ----------------------------------


def test_new_0_2_field_round_trip_preserves_values_and_metadata() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=8, seed=1)
    payload = field.to_dict()
    # Strict JSON: no NaN.
    json.dumps(payload, allow_nan=False)
    round_tripped = FieldBatch.from_dict(payload)
    np.testing.assert_allclose(round_tripped.values, field.values)
    assert round_tripped.schema_version == "0.2"


def test_generated_periodic_fields_still_pass_consumers() -> None:
    """Regression: generators still emit legacy "periodic" strings (no breakage)."""
    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=2)
    # Generators emit the legacy form for backwards compat. The consumers
    # use is_x_periodic which accepts both forms transparently.
    assert field.metadata["boundary_conditions"]["x"] == "periodic"
    derivatives = compute_spectral_fd_derivatives(field)
    assert "u_x" in derivatives.derivatives


def test_legacy_0_1_payload_with_structured_bc_passes_through_unchanged() -> None:
    """A 0.1 payload whose BC is already structured needs no normalization entry."""
    structured = {
        "type": "periodic",
        "left": None,
        "right": None,
        "specified": True,
        "notes": None,
    }
    payload = _legacy_payload(schema_version="0.1", x_boundary=structured)
    field = FieldBatch.from_dict(payload)
    assert field.metadata["boundary_conditions"]["x"]["type"] == "periodic"
    operations = [entry["operation"] for entry in field.preprocess_log]
    # No migration entry is recorded because no normalization was needed.
    assert LEGACY_BOUNDARY_NORMALIZATION_OPERATION not in operations


# --- Schema migration metadata ------------------------------------------


def test_migration_entry_records_from_and_to_schema_versions() -> None:
    payload = _legacy_payload(schema_version="0.1", x_boundary="dirichlet")
    field = FieldBatch.from_dict(payload)
    entries = [
        entry for entry in field.preprocess_log
        if entry["operation"] == LEGACY_BOUNDARY_NORMALIZATION_OPERATION
    ]
    assert len(entries) == 1
    params = entries[0]["parameters"]
    assert params["from_schema_version"] == "0.1"
    assert params["to_schema_version"] == "0.2"
    assert params["legacy_x_boundary_string"] == "dirichlet"
