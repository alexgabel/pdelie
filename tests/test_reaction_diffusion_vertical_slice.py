from __future__ import annotations

import json

import numpy as np

import pdelie
from pdelie.data import generate_reaction_diffusion_1d_field_batch, split_batch_train_heldout
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.examples import run_reaction_diffusion_vertical_slice_example
from pdelie.reporting import summarize_vertical_slice
from pdelie.residuals import ReactionDiffusionResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import verify_translation_generator


def _run_vertical_slice() -> dict[str, object]:
    field = generate_reaction_diffusion_1d_field_batch(batch_size=5, seed=18018)
    training, heldout = split_batch_train_heldout(field, train_size=2, seed=18019)
    derivatives = compute_spectral_fd_derivatives(training)
    residual_evaluator = ReactionDiffusionResidualEvaluator()
    residual = residual_evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, residual_evaluator, epsilon=1e-4)
    verification = verify_translation_generator(heldout, generator, residual_evaluator)
    return summarize_vertical_slice(
        derivatives=derivatives,
        residual=residual,
        generator=generator,
        verification=verification,
        extra_metrics={"equation": "reaction_diffusion_fisher_kpp"},
    )


def test_reaction_diffusion_vertical_slice_direct_svd_feasibility() -> None:
    summary = _run_vertical_slice()

    assert json.loads(json.dumps(summary)) == summary
    assert summary["summary_type"] == "vertical_slice"
    assert summary["derivative_keys"] == ["u_t", "u_x", "u_xx"]
    assert summary["residual"]["max_abs_residual"] < 5e-4
    assert summary["residual"]["rms_residual"] < 5e-5
    assert summary["generator"]["parameterization"] == "polynomial_translation_affine"
    assert summary["generator"]["fit_mode"] == "svd"
    assert summary["generator"]["reference_fallback_used"] is False
    assert summary["generator"]["fallback_reason"] is None
    assert summary["generator"]["translation_span_distance"] <= 5e-2
    assert summary["generator"]["diagnostics"]["evidence_label"] == "direct_svd_in_tolerance"
    assert summary["generator"]["diagnostics"]["svd_span_distance"] <= 5e-2
    assert summary["verification"]["classification"] != "failed"
    assert summary["verification"]["first_error"] < 5e-4
    assert summary["verification"]["diagnostics"]["transform_mode"] == "uniform_translation"


def test_reaction_diffusion_vertical_slice_example_runs_end_to_end() -> None:
    result = run_reaction_diffusion_vertical_slice_example()

    assert json.loads(json.dumps(result)) == result
    assert result["summary_schema_version"] == "0.1"
    assert result["summary_type"] == "vertical_slice"
    assert result["extra_metrics"]["example_name"] == "reaction_diffusion_vertical_slice"
    assert result["extra_metrics"]["equation"] == "reaction_diffusion_fisher_kpp"
    assert result["residual"]["max_abs_residual"] < 5e-4
    assert result["residual"]["rms_residual"] < 5e-5
    assert result["generator"]["fit_mode"] == "svd"
    assert result["generator"]["reference_fallback_used"] is False
    assert result["generator"]["translation_span_distance"] <= 5e-2
    assert result["verification"]["classification"] != "failed"
    assert result["verification"]["first_error"] < 5e-4
    assert np.isfinite(float(result["extra_metrics"]["mean_drift_diagnostic"]))
    assert np.isfinite(float(result["extra_metrics"]["relative_l2_drift_diagnostic"]))
    assert not hasattr(pdelie, "run_reaction_diffusion_vertical_slice_example")
