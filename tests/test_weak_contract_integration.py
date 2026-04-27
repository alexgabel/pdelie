from __future__ import annotations

import importlib
import inspect

import numpy as np

import pdelie
from pdelie import GeneratorFamily, ResidualEvaluator
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.residuals import evaluate_weak_burgers_residual, evaluate_weak_heat_residual
from pdelie.symmetry.parameterization.polynomial_translation import (
    DEFAULT_TRANSLATION_SPAN_TOLERANCE,
    _coerce_translation_coefficients,
    translation_reference_coefficients,
    translation_span_distance,
)
from tests._helpers.weak_contract_integration import (
    fit_translation_generator_from_weak_reports,
    verify_translation_generator_from_weak_reports,
)


_TRAINING_KWARGS = {"batch_size": 4, "num_times": 33, "num_points": 64}
_HELDOUT_KWARGS = {"batch_size": 3, "num_times": 33, "num_points": 64}
_EXPECTED_METHOD_FAMILY = "local_separable_quartic_bump_trapezoid_v1"
_EXPECTED_RESIDUALS_EXPORTS = {
    "BurgersResidualEvaluator",
    "HeatResidualEvaluator",
    "ResidualEvaluator",
    "evaluate_weak_burgers_residual",
    "evaluate_weak_heat_residual",
}
_WRONG_TRANSLATION_COEFFICIENTS = np.array([[0.0, 0.0, 1.0, 0.0]], dtype=float)


def _make_wrong_generator() -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=_WRONG_TRANSLATION_COEFFICIENTS.copy(),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )


def _assert_layout_matches_heldout(result: dict[str, object], heldout) -> None:
    assert result["report_shape"] == (heldout.values.shape[0], heldout.values.shape[1] - 4, heldout.values.shape[2], 1)
    np.testing.assert_allclose(result["time_window_centers"], heldout.coords["time"][2:-2], rtol=0.0, atol=1e-12)
    np.testing.assert_allclose(result["x_window_centers"], heldout.coords["x"], rtol=0.0, atol=1e-12)
    assert result["method_family"] == _EXPECTED_METHOD_FAMILY


def test_clean_heat_report_space_fit_recovers_translation_within_stable_span_tolerance() -> None:
    training = generate_heat_1d_field_batch(seed=21, **_TRAINING_KWARGS)

    result = fit_translation_generator_from_weak_reports(training, evaluate_weak_heat_residual, epsilon=1e-4)
    generator = result["generator"]
    coefficients = _coerce_translation_coefficients(generator.coefficients)

    assert isinstance(generator, GeneratorFamily)
    generator.validate()
    if result["reference_fallback_used"]:
        np.testing.assert_allclose(coefficients, translation_reference_coefficients(), rtol=0.0, atol=1e-12)
    else:
        assert translation_span_distance(coefficients) <= DEFAULT_TRANSLATION_SPAN_TOLERANCE
    assert result["method_family"] == _EXPECTED_METHOD_FAMILY
    assert result["rank_estimate"] >= 1
    assert result["smallest_singular_value"] >= 0.0
    assert result["condition_number"] >= 1.0
    assert result["singular_values"].shape == (4,)
    assert result["selected_span_distance"] <= DEFAULT_TRANSLATION_SPAN_TOLERANCE
    assert result["fallback_reason"] in {None, "svd_translation_span_drift", "weak_report_contract_span_drift"}


def test_clean_burgers_report_space_fit_recovers_translation_or_uses_reference_fallback() -> None:
    training = generate_burgers_1d_field_batch(seed=31, **_TRAINING_KWARGS)

    result = fit_translation_generator_from_weak_reports(training, evaluate_weak_burgers_residual, epsilon=1e-4)
    generator = result["generator"]
    coefficients = _coerce_translation_coefficients(generator.coefficients)

    assert isinstance(generator, GeneratorFamily)
    generator.validate()
    if result["reference_fallback_used"]:
        np.testing.assert_allclose(coefficients, translation_reference_coefficients(), rtol=0.0, atol=1e-12)
    else:
        assert translation_span_distance(coefficients) <= DEFAULT_TRANSLATION_SPAN_TOLERANCE
    assert result["method_family"] == _EXPECTED_METHOD_FAMILY
    assert result["rank_estimate"] >= 1
    assert result["smallest_singular_value"] >= 0.0
    assert result["condition_number"] >= 1.0
    assert result["singular_values"].shape == (4,)
    assert result["selected_span_distance"] <= DEFAULT_TRANSLATION_SPAN_TOLERANCE
    assert result["fallback_reason"] in {None, "svd_translation_span_drift", "weak_report_contract_span_drift"}


def test_clean_heat_report_space_verification_is_reproducible() -> None:
    training = generate_heat_1d_field_batch(seed=21, **_TRAINING_KWARGS)
    heldout = generate_heat_1d_field_batch(seed=22, **_HELDOUT_KWARGS)
    fit_result = fit_translation_generator_from_weak_reports(training, evaluate_weak_heat_residual, epsilon=1e-4)

    first = verify_translation_generator_from_weak_reports(
        heldout,
        fit_result["generator"],
        evaluate_weak_heat_residual,
    )
    second = verify_translation_generator_from_weak_reports(
        heldout,
        fit_result["generator"],
        evaluate_weak_heat_residual,
    )

    np.testing.assert_allclose(first["relative_to_field_norm_error_curve"], second["relative_to_field_norm_error_curve"])
    np.testing.assert_allclose(
        first["relative_to_baseline_report_norm_error_curve"],
        second["relative_to_baseline_report_norm_error_curve"],
    )
    np.testing.assert_allclose(
        np.asarray(first["relative_to_field_norm_batch_errors"], dtype=float),
        np.asarray(second["relative_to_field_norm_batch_errors"], dtype=float),
    )
    _assert_layout_matches_heldout(first, heldout)


def test_clean_burgers_report_space_verification_is_reproducible() -> None:
    training = generate_burgers_1d_field_batch(seed=31, **_TRAINING_KWARGS)
    heldout = generate_burgers_1d_field_batch(seed=32, **_HELDOUT_KWARGS)
    fit_result = fit_translation_generator_from_weak_reports(training, evaluate_weak_burgers_residual, epsilon=1e-4)

    first = verify_translation_generator_from_weak_reports(
        heldout,
        fit_result["generator"],
        evaluate_weak_burgers_residual,
    )
    second = verify_translation_generator_from_weak_reports(
        heldout,
        fit_result["generator"],
        evaluate_weak_burgers_residual,
    )

    np.testing.assert_allclose(first["relative_to_field_norm_error_curve"], second["relative_to_field_norm_error_curve"])
    np.testing.assert_allclose(
        first["relative_to_baseline_report_norm_error_curve"],
        second["relative_to_baseline_report_norm_error_curve"],
    )
    np.testing.assert_allclose(
        np.asarray(first["relative_to_field_norm_batch_errors"], dtype=float),
        np.asarray(second["relative_to_field_norm_batch_errors"], dtype=float),
    )
    _assert_layout_matches_heldout(first, heldout)


def test_wrong_generator_verification_is_materially_worse_than_fitted_generator_on_first_epsilon() -> None:
    for training_seed, heldout_seed, field_factory, evaluator in (
        (21, 22, generate_heat_1d_field_batch, evaluate_weak_heat_residual),
        (31, 32, generate_burgers_1d_field_batch, evaluate_weak_burgers_residual),
    ):
        training = field_factory(seed=training_seed, **_TRAINING_KWARGS)
        heldout = field_factory(seed=heldout_seed, **_HELDOUT_KWARGS)
        fitted = fit_translation_generator_from_weak_reports(training, evaluator, epsilon=1e-4)
        fitted_report = verify_translation_generator_from_weak_reports(heldout, fitted["generator"], evaluator)
        wrong_report = verify_translation_generator_from_weak_reports(heldout, _make_wrong_generator(), evaluator)
        assert wrong_report["relative_to_field_norm_error_curve"][0] > 3.0 * fitted_report["relative_to_field_norm_error_curve"][0]


def test_transformed_reports_preserve_shape_and_window_centers_across_the_epsilon_sweep() -> None:
    for training_seed, heldout_seed, field_factory, evaluator in (
        (21, 22, generate_heat_1d_field_batch, evaluate_weak_heat_residual),
        (31, 32, generate_burgers_1d_field_batch, evaluate_weak_burgers_residual),
    ):
        training = field_factory(seed=training_seed, **_TRAINING_KWARGS)
        heldout = field_factory(seed=heldout_seed, **_HELDOUT_KWARGS)
        fitted = fit_translation_generator_from_weak_reports(training, evaluator, epsilon=1e-4)
        verification = verify_translation_generator_from_weak_reports(heldout, fitted["generator"], evaluator)
        _assert_layout_matches_heldout(verification, heldout)


def test_m3_contract_integration_adds_no_public_surface() -> None:
    residuals_module = importlib.import_module("pdelie.residuals")
    weak_module = importlib.import_module("pdelie.residuals.weak_1d")

    assert set(residuals_module.__all__) == _EXPECTED_RESIDUALS_EXPORTS
    assert not hasattr(pdelie, "fit_translation_generator_from_weak_reports")
    assert not hasattr(pdelie, "verify_translation_generator_from_weak_reports")
    assert not hasattr(residuals_module, "fit_translation_generator_from_weak_reports")
    assert not hasattr(residuals_module, "verify_translation_generator_from_weak_reports")

    weak_evaluator_subclasses = [
        name
        for name, value in vars(weak_module).items()
        if inspect.isclass(value) and issubclass(value, ResidualEvaluator) and value is not ResidualEvaluator
    ]
    assert weak_evaluator_subclasses == []
    assert "ResidualBatch" not in weak_module.__dict__
