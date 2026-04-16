from __future__ import annotations

import numpy as np
import pytest

from pdelie import GeneratorFamily, ScopeValidationError
from pdelie.data import generate_heat_1d_field_batch
from pdelie.residuals import HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import DEFAULT_EPSILON_VALUES, verify_translation_generator


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
        coefficients=np.array([0.0, 0.0, 1.0, 0.0]),
        normalization="l2_unit",
        diagnostics={"basis": ["1", "t", "x", "u"]},
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
    with pytest.raises(ScopeValidationError):
        verify_translation_generator(heldout, generator, HeatResidualEvaluator())
