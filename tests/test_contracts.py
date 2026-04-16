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
            coefficients=np.array([2.0, 0.0, 0.0, 0.0]),
            normalization="l2_unit",
            diagnostics={"basis": ["1", "t", "x", "u"]},
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
