from __future__ import annotations

import numpy as np
import pytest

from pdelie import GeneratorFamily, ShapeValidationError
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.residuals import BurgersResidualEvaluator, HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.symmetry.parameterization import normalize_translation_coefficients, translation_span_distance


def _assert_common_fit_diagnostics(generator: GeneratorFamily) -> None:
    diagnostics = generator.diagnostics
    for key in (
        "basis",
        "basis_delta_norms",
        "condition_number",
        "design_column_norms",
        "evidence_label",
        "fit_residual",
        "selected_coefficients",
        "selected_span_distance",
        "singular_values",
        "svd_coefficients",
        "svd_span_distance",
        "training_epsilon",
    ):
        assert key in diagnostics

    assert diagnostics["design_column_norms"] == diagnostics["basis_delta_norms"]
    assert diagnostics["condition_number"] > 0.0
    assert np.all(np.isfinite(np.asarray(diagnostics["singular_values"], dtype=float)))
    np.testing.assert_allclose(
        np.asarray(diagnostics["selected_coefficients"], dtype=float),
        generator.coefficients[0],
    )
    assert diagnostics["selected_span_distance"] == pytest.approx(translation_span_distance(generator.coefficients))


def test_translation_baseline_recovers_spatial_translation_span() -> None:
    field = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=10)
    generator = fit_translation_generator(field, HeatResidualEvaluator(), epsilon=1e-4)
    assert generator.parameterization == "polynomial_translation_affine"
    assert generator.normalization == "l2_unit"
    assert generator.coefficients.shape == (1, 4)
    assert generator.basis_spec == _translation_generator_basis_spec()
    assert translation_span_distance(generator.coefficients) < 5e-2
    assert generator.diagnostics["fit_mode"] == "svd"
    assert generator.diagnostics["reference_fallback_used"] is False
    assert generator.diagnostics["evidence_label"] == "direct_svd_in_tolerance"
    _assert_common_fit_diagnostics(generator)
    np.testing.assert_allclose(generator.coefficients[0], np.asarray(generator.diagnostics["svd_coefficients"], dtype=float))


def test_translation_baseline_outputs_normalized_coefficients() -> None:
    field = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=12)
    generator = fit_translation_generator(field, HeatResidualEvaluator(), epsilon=1e-4)
    np.testing.assert_allclose(np.linalg.norm(generator.coefficients, axis=1), np.array([1.0]), atol=1e-8)


def test_translation_baseline_recovers_spatial_translation_span_on_burgers() -> None:
    field = generate_burgers_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=14)
    generator = fit_translation_generator(field, BurgersResidualEvaluator(), epsilon=1e-4)
    assert generator.parameterization == "polynomial_translation_affine"
    assert generator.normalization == "l2_unit"
    assert translation_span_distance(generator.coefficients) < 5e-2
    assert generator.diagnostics["fit_mode"] == "reference_fallback"
    assert generator.diagnostics["reference_fallback_used"] is True
    assert generator.diagnostics["fallback_reason"] == "svd_translation_span_drift"
    assert generator.diagnostics["evidence_label"] == "reference_fallback"
    assert generator.diagnostics["min_delta_basis"] == "1"
    _assert_common_fit_diagnostics(generator)
    assert generator.diagnostics["svd_span_distance"] > 5e-2
    np.testing.assert_allclose(generator.coefficients, np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float))


def test_wrong_control_does_not_match_translation_span() -> None:
    wrong = GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[0.0, 0.0, 1.0, 0.0]]),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )
    assert translation_span_distance(wrong.coefficients) > 1.0


def test_zero_translation_coefficients_raise_typed_error() -> None:
    with pytest.raises(ShapeValidationError):
        normalize_translation_coefficients(np.zeros(4, dtype=float))


def test_wrong_length_translation_coefficients_raise_typed_error() -> None:
    with pytest.raises(ShapeValidationError):
        normalize_translation_coefficients(np.array([1.0, 0.0, 0.0], dtype=float))


def test_translation_fitter_dispatches_nonperiodic_since_v0_33a() -> None:
    """v0.33a: nonperiodic input dispatches to the interior-only branch.

    Supersedes the pre-v0.33a rejection. The claim the nonperiodic branch
    supports is narrower than the periodic one and is carried by
    ``symmetry_claim``, not by acceptance alone.
    """
    field = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=13)
    field.metadata["boundary_conditions"] = {"x": "dirichlet"}

    diagnostics = fit_translation_generator(
        field, HeatResidualEvaluator(), epsilon=1e-4
    ).diagnostics

    assert diagnostics["boundary_condition_x"] == "dirichlet"
    assert diagnostics["boundary_condition_dispatch_reason"] == "is_x_periodic_false_field_metadata"
    assert diagnostics["interior_only_reduction_applied"] is True
    assert diagnostics["interior_only_row_count"] < 64
    # The reference fallback is suppressed off the periodic branch, so the
    # emitted span is the honest SVD value rather than a masked 0.0.
    assert diagnostics["reference_fallback_used"] is False
    assert diagnostics["selected_span_distance"] == diagnostics["svd_span_distance"]


def test_translation_fitter_dispatches_nonperiodic_burgers_inputs_since_v0_33a() -> None:
    field = generate_burgers_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=15)
    field.metadata["boundary_conditions"] = {"x": "dirichlet"}

    diagnostics = fit_translation_generator(
        field, BurgersResidualEvaluator(), epsilon=1e-4
    ).diagnostics

    assert diagnostics["boundary_condition_x"] == "dirichlet"
    assert diagnostics["interior_only_reduction_applied"] is True
    assert diagnostics["reference_fallback_used"] is False
