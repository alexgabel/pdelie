from __future__ import annotations

from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.residuals import BurgersResidualEvaluator, HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import verify_translation_generator


def test_full_vertical_slice_produces_exact_verification_report() -> None:
    training = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=30)
    heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=31)

    derivatives = compute_spectral_fd_derivatives(training)
    residual_evaluator = HeatResidualEvaluator()
    residual = residual_evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, residual_evaluator, epsilon=1e-4)
    report = verify_translation_generator(heldout, generator, residual_evaluator)

    assert derivatives.backend == "spectral_fd"
    assert residual.definition_type == "analytic"
    assert generator.parameterization == "polynomial_translation_affine"
    assert report.classification == "exact"


def test_burgers_vertical_slice_produces_exact_verification_report() -> None:
    training = generate_burgers_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=40)
    heldout = generate_burgers_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=41)

    derivatives = compute_spectral_fd_derivatives(training)
    residual_evaluator = BurgersResidualEvaluator()
    residual = residual_evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, residual_evaluator, epsilon=1e-4)
    report = verify_translation_generator(heldout, generator, residual_evaluator)

    assert derivatives.backend == "spectral_fd"
    assert residual.definition_type == "analytic"
    assert generator.parameterization == "polynomial_translation_affine"
    assert report.classification == "exact"


def test_heat_and_burgers_remain_clean_under_shared_translation_defaults() -> None:
    heat_training = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=50)
    heat_heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=51)
    burgers_training = generate_burgers_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=52)
    burgers_heldout = generate_burgers_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=53)

    heat_generator = fit_translation_generator(heat_training, HeatResidualEvaluator(), epsilon=1e-4)
    burgers_generator = fit_translation_generator(burgers_training, BurgersResidualEvaluator(), epsilon=1e-4)

    heat_report = verify_translation_generator(heat_heldout, heat_generator, HeatResidualEvaluator())
    burgers_report = verify_translation_generator(burgers_heldout, burgers_generator, BurgersResidualEvaluator())

    assert heat_report.classification == "exact"
    assert burgers_report.classification == "exact"
