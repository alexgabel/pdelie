from __future__ import annotations

import numpy as np
import pytest

from pdelie import GeneratorFamily, ScopeValidationError
from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.residuals import BurgersResidualEvaluator, HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.symmetry.fitting.translation_baseline import TRANSLATION_FALLBACK_SPAN_TOLERANCE
from pdelie.symmetry.parameterization.polynomial_translation import DEFAULT_TRANSLATION_SPAN_TOLERANCE
from pdelie.verification import DEFAULT_EPSILON_VALUES, verify_translation_generator


def translation_basis_spec() -> dict[str, object]:
    return {
        "variables": ["t", "x", "u"],
        "component_names": ["xi"],
        "basis_terms": [
            {"label": "1", "powers": [0, 0, 0]},
            {"label": "t", "powers": [1, 0, 0]},
            {"label": "x", "powers": [0, 1, 0]},
            {"label": "u", "powers": [0, 0, 1]},
        ],
        "component_ordering": ["xi"],
        "term_ordering": ["1", "t", "x", "u"],
        "layout": "component_major",
    }


def test_translation_span_tolerance_defaults_are_shared() -> None:
    assert TRANSLATION_FALLBACK_SPAN_TOLERANCE == DEFAULT_TRANSLATION_SPAN_TOLERANCE

    heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=20)
    wrong = GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[0.0, 0.0, 1.0, 0.0]]),
        basis_spec=translation_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )
    report = verify_translation_generator(heldout, wrong, HeatResidualEvaluator())
    assert report.diagnostics["span_tolerance"] == DEFAULT_TRANSLATION_SPAN_TOLERANCE


def test_translation_verification_is_exact_on_heldout_heat_data() -> None:
    training = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=21)
    heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=22)
    generator = fit_translation_generator(training, HeatResidualEvaluator(), epsilon=1e-4)
    report = verify_translation_generator(heldout, generator, HeatResidualEvaluator())
    assert report.classification == "exact"
    np.testing.assert_allclose(report.epsilon_values, DEFAULT_EPSILON_VALUES)
    assert report.diagnostics["heldout_initial_conditions"] == 3


def test_translation_verification_fails_for_wrong_generator() -> None:
    heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=23)
    wrong = GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[0.0, 0.0, 1.0, 0.0]]),
        basis_spec=translation_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )
    report = verify_translation_generator(heldout, wrong, HeatResidualEvaluator())
    assert report.classification == "failed"
    assert report.diagnostics["span_distance"] > report.diagnostics["span_tolerance"]


def test_translation_verification_is_reproducible() -> None:
    training = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=24)
    heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=25)
    generator = fit_translation_generator(training, HeatResidualEvaluator(), epsilon=1e-4)
    first = verify_translation_generator(heldout, generator, HeatResidualEvaluator())
    second = verify_translation_generator(heldout, generator, HeatResidualEvaluator())
    np.testing.assert_allclose(first.error_curve, second.error_curve)
    assert first.classification == second.classification


def test_translation_verification_requires_three_heldout_initial_conditions() -> None:
    training = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=26)
    heldout = generate_heat_1d_field_batch(batch_size=2, num_times=33, num_points=64, seed=27)
    generator = fit_translation_generator(training, HeatResidualEvaluator(), epsilon=1e-4)
    with pytest.raises(ScopeValidationError, match="at least 3 unseen initial conditions"):
        verify_translation_generator(heldout, generator, HeatResidualEvaluator())


def test_translation_verification_reports_custom_heldout_requirement() -> None:
    training = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=28)
    heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=29)
    generator = fit_translation_generator(training, HeatResidualEvaluator(), epsilon=1e-4)
    with pytest.raises(ScopeValidationError, match="at least 4 unseen initial conditions"):
        verify_translation_generator(
            heldout,
            generator,
            HeatResidualEvaluator(),
            min_heldout_initial_conditions=4,
        )


def test_translation_verification_rejects_nonperiodic_boundary_conditions() -> None:
    heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=30)
    heldout.metadata["boundary_conditions"] = {"x": "dirichlet"}
    generator = GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0]]),
        basis_spec=translation_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )
    with pytest.raises(ScopeValidationError, match="periodic boundary conditions in x"):
        verify_translation_generator(heldout, generator, HeatResidualEvaluator())


def test_translation_verification_is_exact_on_heldout_burgers_data() -> None:
    training = generate_burgers_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=31)
    heldout = generate_burgers_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=32)
    generator = fit_translation_generator(training, BurgersResidualEvaluator(), epsilon=1e-4)
    assert generator.diagnostics["reference_fallback_used"] is True
    report = verify_translation_generator(heldout, generator, BurgersResidualEvaluator())
    assert report.classification == "exact"
    np.testing.assert_allclose(report.epsilon_values, DEFAULT_EPSILON_VALUES)
    assert report.diagnostics["heldout_initial_conditions"] == 3


def test_translation_verification_fails_for_wrong_burgers_generator() -> None:
    heldout = generate_burgers_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=33)
    wrong = GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[0.0, 0.0, 1.0, 0.0]]),
        basis_spec=translation_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )
    report = verify_translation_generator(heldout, wrong, BurgersResidualEvaluator())
    assert report.classification == "failed"
    assert report.diagnostics["span_distance"] > report.diagnostics["span_tolerance"]


def test_translation_verification_is_reproducible_on_burgers() -> None:
    training = generate_burgers_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=34)
    heldout = generate_burgers_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=35)
    generator = fit_translation_generator(training, BurgersResidualEvaluator(), epsilon=1e-4)
    first = verify_translation_generator(heldout, generator, BurgersResidualEvaluator())
    second = verify_translation_generator(heldout, generator, BurgersResidualEvaluator())
    np.testing.assert_allclose(first.error_curve, second.error_curve)
    assert first.classification == second.classification
