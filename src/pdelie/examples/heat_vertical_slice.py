from __future__ import annotations

import json

from pdelie.data import generate_heat_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.reporting import summarize_vertical_slice
from pdelie.residuals import HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import verify_translation_generator


_TRAINING_SEED = 100
_HELDOUT_SEED = 101
_TRAINING_BATCH_SIZE = 4
_HELDOUT_BATCH_SIZE = 3


def run_heat_vertical_slice_example() -> dict[str, object]:
    training = generate_heat_1d_field_batch(
        batch_size=_TRAINING_BATCH_SIZE,
        num_times=33,
        num_points=64,
        seed=_TRAINING_SEED,
    )
    heldout = generate_heat_1d_field_batch(
        batch_size=_HELDOUT_BATCH_SIZE,
        num_times=33,
        num_points=64,
        seed=_HELDOUT_SEED,
    )

    derivatives = compute_spectral_fd_derivatives(training)
    residual_evaluator = HeatResidualEvaluator()
    residual = residual_evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, residual_evaluator, epsilon=1e-4)
    report = verify_translation_generator(heldout, generator, residual_evaluator)

    return summarize_vertical_slice(
        derivatives=derivatives,
        residual=residual,
        generator=generator,
        verification=report,
        extra_metrics={
            "example_name": "heat_vertical_slice",
            "equation": "heat_1d",
            "training_seed": _TRAINING_SEED,
            "heldout_seed": _HELDOUT_SEED,
            "training_batch_size": _TRAINING_BATCH_SIZE,
            "heldout_batch_size": _HELDOUT_BATCH_SIZE,
        },
    )


def main() -> None:
    print(json.dumps(run_heat_vertical_slice_example(), indent=2))


if __name__ == "__main__":
    main()
