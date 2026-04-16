from __future__ import annotations

import json

from pdelie.data import generate_heat_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.residuals import HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.symmetry.parameterization import translation_span_distance
from pdelie.verification import verify_translation_generator


def run_heat_vertical_slice_example() -> dict[str, object]:
    training = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=100)
    heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=101)

    derivatives = compute_spectral_fd_derivatives(training)
    residual_evaluator = HeatResidualEvaluator()
    residual = residual_evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, residual_evaluator, epsilon=1e-4)
    report = verify_translation_generator(heldout, generator, residual_evaluator)

    return {
        "backend": derivatives.backend,
        "max_abs_residual": residual.diagnostics["max_abs_residual"],
        "parameterization": generator.parameterization,
        "coefficients": generator.coefficients.tolist(),
        "span_distance": translation_span_distance(generator.coefficients),
        "verification_classification": report.classification,
        "epsilon_values": report.epsilon_values.tolist(),
        "error_curve": report.error_curve.tolist(),
    }


def main() -> None:
    print(json.dumps(run_heat_vertical_slice_example(), indent=2))


if __name__ == "__main__":
    main()
