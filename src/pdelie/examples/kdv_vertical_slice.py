from __future__ import annotations

import json

import numpy as np

from pdelie.data import generate_kdv_1d_field_batch, split_batch_train_heldout
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.reporting import summarize_vertical_slice
from pdelie.residuals import KdVResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import verify_translation_generator


_GENERATOR_SEED = 9001
_BATCH_SIZE = 5
_TRAIN_SIZE = 2
_SPLIT_SEED = 9002


def _mass_and_l2_drift(values: np.ndarray, *, dx: float) -> tuple[float, float]:
    values = np.asarray(values[..., 0], dtype=float)
    mass = dx * np.sum(values, axis=-1)
    l2 = np.sqrt(dx * np.sum(np.square(values), axis=-1))
    mass_drift = np.max(np.abs(mass - mass[:, [0]]))
    relative_l2_drift = np.max(np.abs(l2 - l2[:, [0]]) / np.maximum(np.abs(l2[:, [0]]), 1e-12))
    return float(mass_drift), float(relative_l2_drift)


def run_kdv_vertical_slice_example() -> dict[str, object]:
    field = generate_kdv_1d_field_batch(batch_size=_BATCH_SIZE, seed=_GENERATOR_SEED)
    dx = float(field.coords["x"][1] - field.coords["x"][0])
    mass_drift, relative_l2_drift = _mass_and_l2_drift(field.values, dx=dx)
    training, heldout = split_batch_train_heldout(field, train_size=_TRAIN_SIZE, seed=_SPLIT_SEED)

    derivatives = compute_spectral_fd_derivatives(training, max_spatial_order=3)
    residual_evaluator = KdVResidualEvaluator()
    residual = residual_evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, residual_evaluator, epsilon=1e-4)
    report = verify_translation_generator(heldout, generator, residual_evaluator)

    return summarize_vertical_slice(
        derivatives=derivatives,
        residual=residual,
        generator=generator,
        verification=report,
        extra_metrics={
            "example_name": "kdv_vertical_slice",
            "equation": "kdv_normalized",
            "generator_seed": _GENERATOR_SEED,
            "batch_size": _BATCH_SIZE,
            "split_seed": _SPLIT_SEED,
            "train_size": _TRAIN_SIZE,
            "mass_drift": mass_drift,
            "relative_l2_drift": relative_l2_drift,
        },
    )


def main() -> None:
    print(json.dumps(run_kdv_vertical_slice_example(), indent=2))


if __name__ == "__main__":
    main()
