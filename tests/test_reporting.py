from __future__ import annotations

import copy
import json

import numpy as np
import pytest

from pdelie.contracts import ResidualBatch
from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.reporting import (
    summarize_generator_family,
    summarize_residual_batch,
    summarize_verification_report,
    summarize_vertical_slice,
    summarize_weak_residual_report,
)
from pdelie.residuals import HeatResidualEvaluator, evaluate_weak_burgers_residual, evaluate_weak_heat_residual
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.symmetry.parameterization import translation_span_distance
from pdelie.verification import verify_translation_generator


_SUMMARY_PREFIX_KEYS = {"summary_schema_version", "summary_type"}


@pytest.fixture(scope="module")
def heat_artifacts() -> dict[str, object]:
    training = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=1010)
    heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=1011)
    derivatives = compute_spectral_fd_derivatives(training)
    evaluator = HeatResidualEvaluator()
    residual = evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, evaluator, epsilon=1e-4)
    verification = verify_translation_generator(heldout, generator, evaluator)
    return {
        "derivatives": derivatives,
        "residual": residual,
        "generator": generator,
        "verification": verification,
    }


def _assert_json_serializable(payload: dict[str, object]) -> None:
    assert json.loads(json.dumps(payload)) == payload


def test_summarize_residual_batch_returns_frozen_json_summary(heat_artifacts: dict[str, object]) -> None:
    residual = heat_artifacts["residual"]
    assert isinstance(residual, ResidualBatch)

    summary = summarize_residual_batch(residual)

    assert set(summary) == _SUMMARY_PREFIX_KEYS | {
        "residual_shape",
        "definition_type",
        "normalization",
        "max_abs_residual",
        "rms_residual",
        "diagnostics",
    }
    assert summary["summary_schema_version"] == "0.1"
    assert summary["summary_type"] == "residual_batch"
    assert summary["residual_shape"] == list(residual.residual.shape)
    assert summary["definition_type"] == residual.definition_type
    assert summary["normalization"] == residual.normalization
    assert summary["max_abs_residual"] == pytest.approx(float(np.max(np.abs(residual.residual))))
    assert summary["rms_residual"] == pytest.approx(float(np.sqrt(np.mean(np.square(residual.residual)))))
    assert summary["diagnostics"] == residual.diagnostics
    _assert_json_serializable(summary)


def test_summarize_weak_residual_report_accepts_frozen_heat_and_burgers_reports() -> None:
    heat = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=9, seed=1020)
    burgers = generate_burgers_1d_field_batch(batch_size=1, num_times=5, num_points=9, seed=1021)

    for report in (evaluate_weak_heat_residual(heat), evaluate_weak_burgers_residual(burgers)):
        summary = summarize_weak_residual_report(report)
        residuals = np.asarray(report["window_residuals"], dtype=float)

        assert set(summary) == _SUMMARY_PREFIX_KEYS | {
            "equation",
            "equation_form",
            "method_family",
            "normalization",
            "window_residual_shape",
            "max_abs_residual",
            "l2_residual",
            "diagnostics",
        }
        assert summary["summary_type"] == "weak_residual_report"
        assert summary["equation"] == report["equation"]
        assert summary["equation_form"] == report["equation_form"]
        assert summary["method_family"] == report["method_family"]
        assert summary["normalization"] == "none"
        assert summary["window_residual_shape"] == list(residuals.shape)
        assert summary["max_abs_residual"] == pytest.approx(float(np.max(np.abs(residuals))))
        assert summary["l2_residual"] == pytest.approx(float(np.linalg.norm(residuals.ravel(), ord=2)))
        _assert_json_serializable(summary)


def test_summarize_generator_family_reports_translation_fit_fields(heat_artifacts: dict[str, object]) -> None:
    generator = heat_artifacts["generator"]

    summary = summarize_generator_family(generator)

    assert set(summary) == _SUMMARY_PREFIX_KEYS | {
        "parameterization",
        "normalization",
        "coefficient_shape",
        "coefficients",
        "generator_names",
        "translation_span_distance",
        "fit_mode",
        "reference_fallback_used",
        "fallback_reason",
        "diagnostics",
    }
    assert summary["summary_type"] == "generator_family"
    assert summary["parameterization"] == generator.parameterization
    assert summary["normalization"] == generator.normalization
    assert summary["coefficient_shape"] == list(generator.coefficients.shape)
    assert summary["coefficients"] == generator.coefficients.tolist()
    assert summary["translation_span_distance"] == pytest.approx(translation_span_distance(generator.coefficients))
    assert summary["fit_mode"] == generator.diagnostics["fit_mode"]
    assert summary["reference_fallback_used"] == generator.diagnostics["reference_fallback_used"]
    assert summary["fallback_reason"] == generator.diagnostics["fallback_reason"]
    _assert_json_serializable(summary)


def test_summarize_verification_report_returns_sweep_metrics(heat_artifacts: dict[str, object]) -> None:
    report = heat_artifacts["verification"]

    summary = summarize_verification_report(report)

    assert set(summary) == _SUMMARY_PREFIX_KEYS | {
        "norm",
        "classification",
        "epsilon_values",
        "error_curve",
        "first_epsilon",
        "first_error",
        "max_error",
        "diagnostics",
    }
    assert summary["summary_type"] == "verification_report"
    assert summary["norm"] == report.norm
    assert summary["classification"] == report.classification
    assert summary["epsilon_values"] == report.epsilon_values.tolist()
    assert summary["error_curve"] == report.error_curve.tolist()
    assert summary["first_epsilon"] == pytest.approx(float(report.epsilon_values[0]))
    assert summary["first_error"] == pytest.approx(float(report.error_curve[0]))
    assert summary["max_error"] == pytest.approx(float(np.max(report.error_curve)))
    _assert_json_serializable(summary)


def test_summarize_vertical_slice_nests_summaries_and_derivative_metadata(heat_artifacts: dict[str, object]) -> None:
    summary = summarize_vertical_slice(
        derivatives=heat_artifacts["derivatives"],
        residual=heat_artifacts["residual"],
        generator=heat_artifacts["generator"],
        verification=heat_artifacts["verification"],
        extra_metrics={"numpy_scalar": np.float64(1.5), "numpy_array": np.asarray([1, 2])},
    )

    assert set(summary) == _SUMMARY_PREFIX_KEYS | {
        "derivative_backend",
        "derivative_keys",
        "derivative_config",
        "derivative_diagnostics",
        "residual",
        "generator",
        "verification",
        "extra_metrics",
    }
    assert summary["summary_type"] == "vertical_slice"
    assert summary["derivative_backend"] == "spectral_fd"
    assert summary["derivative_keys"] == sorted(heat_artifacts["derivatives"].derivatives)
    assert summary["residual"]["summary_type"] == "residual_batch"
    assert summary["generator"]["summary_type"] == "generator_family"
    assert summary["verification"]["summary_type"] == "verification_report"
    assert summary["extra_metrics"] == {"numpy_scalar": 1.5, "numpy_array": [1, 2]}
    _assert_json_serializable(summary)


def test_summarize_vertical_slice_defaults_extra_metrics_to_empty_mapping(heat_artifacts: dict[str, object]) -> None:
    summary = summarize_vertical_slice(
        derivatives=heat_artifacts["derivatives"],
        residual=heat_artifacts["residual"],
        generator=heat_artifacts["generator"],
        verification=heat_artifacts["verification"],
    )

    assert summary["extra_metrics"] == {}


@pytest.mark.parametrize(
    ("helper", "argument"),
    [
        (summarize_residual_batch, object()),
        (summarize_generator_family, object()),
        (summarize_verification_report, object()),
        (summarize_weak_residual_report, object()),
    ],
)
def test_reporting_helpers_reject_wrong_input_types(helper: object, argument: object) -> None:
    with pytest.raises(SchemaValidationError):
        helper(argument)  # type: ignore[misc]


def test_summarize_weak_residual_report_rejects_malformed_report() -> None:
    with pytest.raises(SchemaValidationError, match="missing required fields"):
        summarize_weak_residual_report({"equation": "heat_1d"})

    report = evaluate_weak_heat_residual(
        generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=9, seed=1030)
    )
    malformed = dict(report)
    malformed["window_residuals"] = np.asarray(report["window_residuals"], dtype=float)[..., 0]

    with pytest.raises(SchemaValidationError, match="window_residuals"):
        summarize_weak_residual_report(malformed)


def test_reporting_helpers_reject_nonfinite_metric_arrays(
    heat_artifacts: dict[str, object],
) -> None:
    residual = heat_artifacts["residual"]
    bad_residual = ResidualBatch(
        residual=np.full_like(residual.residual, np.nan),
        definition_type=residual.definition_type,
        normalization=residual.normalization,
        diagnostics=residual.diagnostics,
    )

    with pytest.raises(ScopeValidationError, match="finite"):
        summarize_residual_batch(bad_residual)

    report = evaluate_weak_heat_residual(
        generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=9, seed=1040)
    )
    bad_report = dict(report)
    bad_window_residuals = np.asarray(report["window_residuals"], dtype=float).copy()
    bad_window_residuals[0, 0, 0, 0] = np.nan
    bad_report["window_residuals"] = bad_window_residuals

    with pytest.raises(ScopeValidationError, match="finite"):
        summarize_weak_residual_report(bad_report)


def test_summarize_vertical_slice_rejects_malformed_extra_metrics(heat_artifacts: dict[str, object]) -> None:
    with pytest.raises(SchemaValidationError, match="extra_metrics"):
        summarize_vertical_slice(
            derivatives=heat_artifacts["derivatives"],
            residual=heat_artifacts["residual"],
            generator=heat_artifacts["generator"],
            verification=heat_artifacts["verification"],
            extra_metrics=["not", "a", "mapping"],  # type: ignore[arg-type]
        )

    with pytest.raises(SchemaValidationError, match="JSON-compatible"):
        summarize_vertical_slice(
            derivatives=heat_artifacts["derivatives"],
            residual=heat_artifacts["residual"],
            generator=heat_artifacts["generator"],
            verification=heat_artifacts["verification"],
            extra_metrics={"not_json": object()},
        )


def test_reporting_helpers_do_not_mutate_inputs(heat_artifacts: dict[str, object]) -> None:
    residual = heat_artifacts["residual"]
    generator = heat_artifacts["generator"]
    verification = heat_artifacts["verification"]
    weak_report = evaluate_weak_heat_residual(
        generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=9, seed=1050)
    )
    weak_snapshot = copy.deepcopy(weak_report)

    residual_snapshot = residual.to_dict()
    generator_snapshot = generator.to_dict()
    verification_snapshot = verification.to_dict()

    summarize_residual_batch(residual)
    summarize_generator_family(generator)
    summarize_verification_report(verification)
    summarize_weak_residual_report(weak_report)
    summarize_vertical_slice(
        derivatives=heat_artifacts["derivatives"],
        residual=residual,
        generator=generator,
        verification=verification,
        extra_metrics={"nested": {"array": np.asarray([1.0, 2.0])}},
    )

    assert residual.to_dict() == residual_snapshot
    assert generator.to_dict() == generator_snapshot
    assert verification.to_dict() == verification_snapshot
    for key, expected in weak_snapshot.items():
        if isinstance(expected, np.ndarray):
            np.testing.assert_allclose(np.asarray(weak_report[key]), expected, atol=0.0, rtol=0.0)
        elif isinstance(expected, dict):
            assert weak_report[key] == expected
        else:
            assert weak_report[key] == expected
