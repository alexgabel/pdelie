from __future__ import annotations

import numpy as np

from pdelie.data import generate_kdv_1d_field_batch, split_batch_train_heldout
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.residuals import KdVResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.symmetry.parameterization import translation_span_distance
from pdelie.verification import verify_translation_generator


def _mass_and_l2_drift(values: np.ndarray, *, dx: float) -> tuple[float, float]:
    values = np.asarray(values[..., 0], dtype=float)
    mass = dx * np.sum(values, axis=-1)
    l2 = np.sqrt(dx * np.sum(np.square(values), axis=-1))
    mass_drift = np.max(np.abs(mass - mass[:, [0]]))
    relative_l2_drift = np.max(np.abs(l2 - l2[:, [0]]) / np.maximum(np.abs(l2[:, [0]]), 1e-12))
    return float(mass_drift), float(relative_l2_drift)


def test_kdv_vertical_slice_frozen_fixture_passes_strong_path_thresholds() -> None:
    field = generate_kdv_1d_field_batch(batch_size=5, seed=9001)
    dx = float(field.coords["x"][1] - field.coords["x"][0])
    mass_drift, relative_l2_drift = _mass_and_l2_drift(field.values, dx=dx)
    training, heldout = split_batch_train_heldout(field, train_size=2, seed=9002)

    derivatives = compute_spectral_fd_derivatives(training, max_spatial_order=3)
    assert set(derivatives.derivatives) == {"u_x", "u_xx", "u_xxx", "u_t"}

    residual_evaluator = KdVResidualEvaluator()
    residual = residual_evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, residual_evaluator, epsilon=1e-4)
    report = verify_translation_generator(heldout, generator, residual_evaluator)

    assert residual.diagnostics["max_abs_residual"] < 1e-2
    assert residual.diagnostics["rms_residual"] < 2e-3
    assert mass_drift <= 1e-8
    assert relative_l2_drift <= 5e-3
    assert generator.parameterization == "polynomial_translation_affine"
    assert generator.diagnostics["fit_mode"] == "svd"
    assert generator.diagnostics["reference_fallback_used"] is False
    assert translation_span_distance(generator.coefficients) <= 5e-2
    assert report.error_curve[0] < 1e-4
    assert report.classification != "failed"
    assert report.diagnostics["transform_mode"] == "uniform_translation"
