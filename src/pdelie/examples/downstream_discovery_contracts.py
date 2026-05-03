from __future__ import annotations

import json

import numpy as np

from pdelie.data import generate_heat_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.discovery import (
    summarize_discovery_bridge_output,
    summarize_discovery_result,
    to_pysindy_trajectories,
)
from pdelie.invariants import build_uniform_translation_orbit_batch
from pdelie.reporting import (
    summarize_downstream_discovery_workflow,
    summarize_field_batch_readiness,
    summarize_generator_confidence,
)
from pdelie.residuals import HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import verify_translation_generator


_SUMMARY_SCHEMA_VERSION = "0.1"
_SHIFTS = (0.0, float(2.0 * np.pi), float(np.pi / 4.0))


def _manual_discovery_result() -> dict[str, object]:
    return {
        "status": "success",
        "backend": "manual_backend_neutral",
        "feature_names": ["u"],
        "library_feature_names": ["u_xx"],
        "coefficients": [[0.1]],
        "equation_terms": {"u": {"u_xx": 0.1}},
        "equation_strings": {"u": "0.1*u_xx"},
        "fit_diagnostics": {
            "terms_are_backend_native": False,
            "canonicalized": True,
            "purpose": "contract_smoke_not_backend_benchmark",
        },
    }


def run_downstream_discovery_contracts_example() -> dict[str, object]:
    training = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=48, seed=22001)
    heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=48, seed=22002)
    evaluator = HeatResidualEvaluator()

    derivatives = compute_spectral_fd_derivatives(training)
    residual = evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, evaluator, epsilon=1e-4)
    verification = verify_translation_generator(heldout, generator, evaluator)
    readiness = summarize_field_batch_readiness(
        training,
        residual_evaluator=evaluator,
    )
    confidence = summarize_generator_confidence(
        residual=residual,
        generator=generator,
        verification=verification,
        thresholds={"residual_max_abs": 1e-3, "residual_rms": 1e-4},
    )

    trajectories, time_values, feature_names = to_pysindy_trajectories(training)
    discovery_inputs = summarize_discovery_bridge_output(
        trajectories,
        time_values,
        feature_names,
        source_field_id="heat-training-field",
        provenance={"bridge": "to_pysindy_trajectories", "example": "downstream_discovery_contracts"},
    )
    discovery_result = summarize_discovery_result(
        _manual_discovery_result(),
        target_terms={"u": {"u_xx": 0.1}},
        source_result_id="manual-heat-reference-result",
    )
    orbit_batch = build_uniform_translation_orbit_batch(
        training,
        shifts=_SHIFTS,
        source_field_id="heat-training-field",
    )
    workflow = summarize_downstream_discovery_workflow(
        field_readiness=readiness,
        generator_confidence=confidence,
        orbit_batch=orbit_batch,
        discovery_inputs=discovery_inputs,
        discovery_result=discovery_result,
        extra_metrics={"example_name": "downstream_discovery_contracts"},
    )

    return {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": "downstream_discovery_contracts_example",
        "field_readiness": readiness,
        "generator_confidence": confidence,
        "discovery_inputs": discovery_inputs,
        "discovery_result": discovery_result,
        "workflow": workflow,
        "extra_metrics": {
            "example_name": "downstream_discovery_contracts",
            "workflow_label": workflow["workflow_label"],
            "recovery_classification": discovery_result["recovery"]["by_feature"]["u"]["classification"],
            "orbit_output_batch_size": orbit_batch.report["output_batch_size"],
            "split_policy": "not_managed_by_pdelie",
        },
    }


def main() -> None:
    print(json.dumps(run_downstream_discovery_contracts_example(), indent=2))


if __name__ == "__main__":
    main()
