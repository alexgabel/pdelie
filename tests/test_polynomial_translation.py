from __future__ import annotations

import numpy as np
import pytest

from pdelie import GeneratorFamily, ScopeValidationError, ShapeValidationError
from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.residuals import BurgersResidualEvaluator, HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.symmetry.parameterization import normalize_translation_coefficients, translation_span_distance


def test_translation_baseline_recovers_spatial_translation_span() -> None:
    field = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=10)
    generator = fit_translation_generator(field, HeatResidualEvaluator(), epsilon=1e-4)
    assert generator.parameterization == "polynomial_translation_affine"
    assert generator.normalization == "l2_unit"
    assert translation_span_distance(generator.coefficients) < 5e-2
    assert generator.diagnostics["fit_mode"] == "svd"
    assert generator.diagnostics["reference_fallback_used"] is False
    np.testing.assert_allclose(generator.coefficients, np.asarray(generator.diagnostics["svd_coefficients"], dtype=float))


def test_translation_baseline_outputs_normalized_coefficients() -> None:
    field = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=12)
    generator = fit_translation_generator(field, HeatResidualEvaluator(), epsilon=1e-4)
    np.testing.assert_allclose(np.linalg.norm(generator.coefficients), 1.0, atol=1e-8)


def test_translation_baseline_recovers_spatial_translation_span_on_burgers() -> None:
    field = generate_burgers_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=14)
    generator = fit_translation_generator(field, BurgersResidualEvaluator(), epsilon=1e-4)
    assert generator.parameterization == "polynomial_translation_affine"
    assert generator.normalization == "l2_unit"
    assert translation_span_distance(generator.coefficients) < 5e-2
    assert generator.diagnostics["fit_mode"] == "reference_fallback"
    assert generator.diagnostics["reference_fallback_used"] is True
    assert generator.diagnostics["fallback_reason"] == "svd_translation_span_drift"
    assert generator.diagnostics["min_delta_basis"] == "1"
    assert generator.diagnostics["svd_span_distance"] > 5e-2
    np.testing.assert_allclose(generator.coefficients, np.array([1.0, 0.0, 0.0, 0.0], dtype=float))


def test_wrong_control_does_not_match_translation_span() -> None:
    wrong = GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([0.0, 0.0, 1.0, 0.0]),
        normalization="l2_unit",
        diagnostics={"basis": ["1", "t", "x", "u"]},
    )
    assert translation_span_distance(wrong.coefficients) > 1.0


def test_zero_translation_coefficients_raise_typed_error() -> None:
    with pytest.raises(ShapeValidationError):
        normalize_translation_coefficients(np.zeros(4, dtype=float))


def test_wrong_length_translation_coefficients_raise_typed_error() -> None:
    with pytest.raises(ShapeValidationError):
        normalize_translation_coefficients(np.array([1.0, 0.0, 0.0], dtype=float))


def test_translation_fitter_rejects_nonperiodic_boundary_conditions() -> None:
    field = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=13)
    field.metadata["boundary_conditions"] = {"x": "dirichlet"}
    with pytest.raises(ScopeValidationError):
        fit_translation_generator(field, HeatResidualEvaluator(), epsilon=1e-4)


def test_translation_fitter_rejects_nonperiodic_burgers_inputs() -> None:
    field = generate_burgers_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=15)
    field.metadata["boundary_conditions"] = {"x": "dirichlet"}
    with pytest.raises(ScopeValidationError):
        fit_translation_generator(field, BurgersResidualEvaluator(), epsilon=1e-4)
