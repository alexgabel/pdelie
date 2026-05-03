from __future__ import annotations

import json

import numpy as np

from pdelie.data import generate_advection_diffusion_1d_field_batch, split_batch_train_heldout
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.reporting import summarize_vertical_slice
from pdelie.residuals import AdvectionDiffusionResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import verify_translation_generator


_GENERATOR_SEED = 19018
_BATCH_SIZE = 5
_TRAIN_SIZE = 2
_SPLIT_SEED = 19019


def _mean_and_l2_drift(values: np.ndarray, *, dx: float) -> tuple[float, float]:
    values = np.asarray(values[..., 0], dtype=float)
    mean = dx * np.sum(values, axis=-1)
    l2 = np.sqrt(dx * np.sum(np.square(values), axis=-1))
    mean_drift = np.max(np.abs(mean - mean[:, [0]]))
    relative_l2_drift = np.max(np.abs(l2 - l2[:, [0]]) / np.maximum(np.abs(l2[:, [0]]), 1e-12))
    return float(mean_drift), float(relative_l2_drift)


def run_advection_diffusion_vertical_slice_example() -> dict[str, object]:
    field = generate_advection_diffusion_1d_field_batch(batch_size=_BATCH_SIZE, seed=_GENERATOR_SEED)
    dx = float(field.coords["x"][1] - field.coords["x"][0])
    mean_drift, relative_l2_drift = _mean_and_l2_drift(field.values, dx=dx)
    training, heldout = split_batch_train_heldout(field, train_size=_TRAIN_SIZE, seed=_SPLIT_SEED)

    derivatives = compute_spectral_fd_derivatives(training)
    residual_evaluator = AdvectionDiffusionResidualEvaluator()
    residual = residual_evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, residual_evaluator, epsilon=1e-4)
    report = verify_translation_generator(heldout, generator, residual_evaluator)

    return summarize_vertical_slice(
        derivatives=derivatives,
        residual=residual,
        generator=generator,
        verification=report,
        extra_metrics={
            "example_name": "advection_diffusion_vertical_slice",
            "equation": "advection_diffusion_constant_coefficient",
            "generator_seed": _GENERATOR_SEED,
            "batch_size": _BATCH_SIZE,
            "split_seed": _SPLIT_SEED,
            "train_size": _TRAIN_SIZE,
            "mean_drift_diagnostic": mean_drift,
            "relative_l2_drift_diagnostic": relative_l2_drift,
        },
    )


def main() -> None:
    print(json.dumps(run_advection_diffusion_vertical_slice_example(), indent=2))


if __name__ == "__main__":
    main()
