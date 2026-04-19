from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie import (
    DerivativeBatch,
    FieldBatch,
    GeneratorFamily,
    ResidualBatch,
    SchemaValidationError,
    ScopeValidationError,
    ShapeValidationError,
    VerificationReport,
)
from pdelie.contracts import _translation_generator_basis_spec


def make_field_batch(*, x_coords: np.ndarray | None = None) -> FieldBatch:
    x = np.linspace(0.0, 2.0 * np.pi, 8, endpoint=False) if x_coords is None else x_coords
    t = np.linspace(0.0, 0.2, 4)
    values = np.zeros((2, 4, 8, 1), dtype=float)
    return FieldBatch(
        values=values,
        dims=("batch", "time", "x", "var"),
        coords={"time": t, "x": x},
        var_names=["u"],
        metadata={
            "boundary_conditions": {"x": "periodic"},
            "coordinate_system": "cartesian",
            "grid_regularity": "uniform",
            "grid_type": "rectilinear",
            "parameter_tags": {"nu": 0.1},
        },
        preprocess_log=[],
    )
def test_field_batch_round_trip_is_json_safe() -> None:
    field = make_field_batch()
    payload = field.to_dict()
    json.dumps(payload)
    round_trip = FieldBatch.from_dict(payload)
    assert round_trip.dims == field.dims
    assert round_trip.var_names == field.var_names
    np.testing.assert_allclose(round_trip.values, field.values)
    np.testing.assert_allclose(round_trip.coords["x"], field.coords["x"])


def test_field_batch_rejects_nonuniform_grid() -> None:
    with pytest.raises(ScopeValidationError):
        make_field_batch(x_coords=np.array([0.0, 0.5, 1.0, 1.6, 2.4, 3.2, 4.1, 5.0]))


def test_field_batch_rejects_var_not_last() -> None:
    with pytest.raises(SchemaValidationError):
        FieldBatch(
            values=np.zeros((2, 1, 4, 8), dtype=float),
            dims=("batch", "var", "time", "x"),
            coords={"time": np.linspace(0.0, 0.2, 4), "x": np.linspace(0.0, 2.0 * np.pi, 8, endpoint=False)},
            var_names=["u"],
            metadata={
                "boundary_conditions": {"x": "periodic"},
                "coordinate_system": "cartesian",
                "grid_regularity": "uniform",
                "grid_type": "rectilinear",
                "parameter_tags": {"nu": 0.1},
            },
            preprocess_log=[],
        )


def test_derivative_batch_validates_against_field() -> None:
    field = make_field_batch()
    derivatives = DerivativeBatch(
        derivatives={
            "u_x": np.zeros_like(field.values),
            "u_xx": np.zeros_like(field.values),
            "u_t": np.zeros_like(field.values),
        },
        backend="spectral_fd",
        config={"spatial_method": "spectral", "temporal_method": "finite_difference"},
        boundary_assumptions="periodic in x",
        diagnostics={},
    )
    derivatives.validate_against(field)


def test_derivative_batch_raises_shape_error() -> None:
    field = make_field_batch()
    derivatives = DerivativeBatch(
        derivatives={"u_x": np.zeros((2, 4, 8), dtype=float)},
        backend="spectral_fd",
        config={"spatial_method": "spectral", "temporal_method": "finite_difference"},
        boundary_assumptions="periodic in x",
        diagnostics={},
    )
    with pytest.raises(ShapeValidationError):
        derivatives.validate_against(field)


def test_residual_batch_rejects_shape_mismatch() -> None:
    field = make_field_batch()
    residual = ResidualBatch(
        residual=np.zeros((2, 4, 8), dtype=float),
        definition_type="analytic",
        normalization="none",
        diagnostics={},
    )
    with pytest.raises(ShapeValidationError):
        residual.validate_against(field)


def test_generator_family_requires_unit_norm_when_marked_l2_unit() -> None:
    with pytest.raises(ShapeValidationError):
        GeneratorFamily(
            parameterization="polynomial_translation_affine",
            coefficients=np.array([[2.0, 0.0, 0.0, 0.0]]),
            basis_spec=_translation_generator_basis_spec(),
            normalization="l2_unit",
            diagnostics={},
        )


def test_generator_family_from_dict_upgrades_legacy_translation_payload_to_canonical_family() -> None:
    legacy_payload = {
        "schema_version": "0.1",
        "parameterization": "polynomial_translation_affine",
        "coefficients": [1.0, 0.0, 0.0, 0.0],
        "normalization": "l2_unit",
        "diagnostics": {"basis": ["1", "t", "x", "u"]},
    }

    generator = GeneratorFamily.from_dict(legacy_payload)
    payload = generator.to_dict()

    assert generator.schema_version == "0.2"
    np.testing.assert_allclose(generator.coefficients, np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float))
    assert generator.basis_spec == _translation_generator_basis_spec()
    assert generator.generator_names is None
    assert payload["schema_version"] == "0.2"
    assert payload["coefficients"] == [[1.0, 0.0, 0.0, 0.0]]
    assert payload["basis_spec"] == _translation_generator_basis_spec()
    json.dumps(payload)


def test_generator_family_accepts_canonical_family_payload() -> None:
    payload = {
        "schema_version": "0.2",
        "parameterization": "polynomial_translation_affine",
        "coefficients": [[1.0, 0.0, 0.0, 0.0]],
        "basis_spec": _translation_generator_basis_spec(),
        "normalization": "l2_unit",
        "diagnostics": {},
    }

    generator = GeneratorFamily.from_dict(payload)

    assert generator.schema_version == "0.2"
    np.testing.assert_allclose(generator.coefficients, np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float))
    assert generator.basis_spec == _translation_generator_basis_spec()


def test_generator_family_rejects_missing_basis_spec_on_direct_construction() -> None:
    with pytest.raises(SchemaValidationError, match="basis_spec must be provided"):
        GeneratorFamily(
            parameterization="polynomial_translation_affine",
            coefficients=np.array([[1.0, 0.0, 0.0, 0.0]]),
            normalization="l2_unit",
            diagnostics={},
        )


def test_generator_family_rejects_missing_basis_spec_on_non_legacy_payload() -> None:
    with pytest.raises(SchemaValidationError, match="basis_spec is required"):
        GeneratorFamily.from_dict(
            {
                "schema_version": "0.2",
                "parameterization": "polynomial_translation_affine",
                "coefficients": [[1.0, 0.0, 0.0, 0.0]],
                "normalization": "l2_unit",
                "diagnostics": {},
            }
        )


def test_generator_family_rejects_incompatible_coefficient_shape_for_basis_spec() -> None:
    with pytest.raises(ShapeValidationError, match="coefficients width must match"):
        GeneratorFamily(
            parameterization="polynomial_translation_affine",
            coefficients=np.array([[1.0, 0.0, 0.0]]),
            basis_spec=_translation_generator_basis_spec(),
            normalization="l2_unit",
            diagnostics={},
        )


def test_generator_family_rejects_invalid_component_ordering() -> None:
    basis_spec = _translation_generator_basis_spec()
    basis_spec["component_ordering"] = ["tau"]

    with pytest.raises(SchemaValidationError, match="component_ordering"):
        GeneratorFamily(
            parameterization="polynomial_translation_affine",
            coefficients=np.array([[1.0, 0.0, 0.0, 0.0]]),
            basis_spec=basis_spec,
            normalization="l2_unit",
            diagnostics={},
        )


def test_generator_family_rejects_invalid_term_ordering() -> None:
    basis_spec = _translation_generator_basis_spec()
    basis_spec["term_ordering"] = ["t", "1", "x", "u"]

    with pytest.raises(SchemaValidationError, match="term_ordering"):
        GeneratorFamily(
            parameterization="polynomial_translation_affine",
            coefficients=np.array([[1.0, 0.0, 0.0, 0.0]]),
            basis_spec=basis_spec,
            normalization="l2_unit",
            diagnostics={},
        )


def test_generator_family_rejects_duplicate_component_names() -> None:
    basis_spec = _translation_generator_basis_spec()
    basis_spec["component_names"] = ["xi", "xi"]

    with pytest.raises(SchemaValidationError, match="component_names"):
        GeneratorFamily(
            parameterization="polynomial_translation_affine",
            coefficients=np.array([[1.0] * 8]),
            basis_spec=basis_spec,
            normalization="l2_unit",
            diagnostics={},
        )


def test_generator_family_rejects_duplicate_basis_term_labels() -> None:
    basis_spec = _translation_generator_basis_spec()
    basis_spec["basis_terms"][1]["label"] = "1"
    basis_spec["term_ordering"] = ["1", "1", "x", "u"]

    with pytest.raises(SchemaValidationError, match="labels must be unique"):
        GeneratorFamily(
            parameterization="polynomial_translation_affine",
            coefficients=np.array([[1.0, 0.0, 0.0, 0.0]]),
            basis_spec=basis_spec,
            normalization="l2_unit",
            diagnostics={},
        )


def test_generator_family_rejects_negative_basis_term_power() -> None:
    basis_spec = _translation_generator_basis_spec()
    basis_spec["basis_terms"][0]["powers"] = [-1, 0, 0]

    with pytest.raises(SchemaValidationError, match="nonnegative integers"):
        GeneratorFamily(
            parameterization="polynomial_translation_affine",
            coefficients=np.array([[1.0, 0.0, 0.0, 0.0]]),
            basis_spec=basis_spec,
            normalization="l2_unit",
            diagnostics={},
        )


def test_generator_family_rejects_mismatched_generator_names_length() -> None:
    with pytest.raises(ShapeValidationError, match="generator_names length must match"):
        GeneratorFamily(
            parameterization="polynomial_translation_affine",
            coefficients=np.array([[1.0, 0.0, 0.0, 0.0]]),
            basis_spec=_translation_generator_basis_spec(),
            normalization="l2_unit",
            generator_names=["g0", "g1"],
            diagnostics={},
        )


def test_verification_report_requires_increasing_epsilon_values() -> None:
    with pytest.raises(ShapeValidationError):
        VerificationReport(
            norm="relative_l2",
            epsilon_values=np.array([1e-3, 1e-4, 1e-2, 1e-1, 2e-1]),
            error_curve=np.zeros(5, dtype=float),
            classification="failed",
            diagnostics={},
        )
