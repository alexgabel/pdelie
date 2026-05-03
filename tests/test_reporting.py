from __future__ import annotations

import copy
import json

import numpy as np
import pytest

from pdelie.contracts import GeneratorFamily, ResidualBatch, _translation_generator_basis_spec
from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.reporting import (
    summarize_formula_generator_family,
    summarize_generator_confidence,
    summarize_generator_fit_diagnostics,
    summarize_generator_family,
    summarize_invariant_workflow,
    summarize_residual_batch,
    summarize_verification_report,
    summarize_vertical_slice,
    summarize_weak_residual_report,
)
from pdelie.symmetry import FormulaGeneratorFamily
from pdelie.residuals import (
    BurgersResidualEvaluator,
    HeatResidualEvaluator,
    evaluate_weak_burgers_residual,
    evaluate_weak_heat_residual,
)
from pdelie.invariants import (
    compute_periodic_window_coverage,
    diagnose_uniform_translation_consistency,
    summarize_uniform_translation_orbit,
)
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.symmetry.parameterization import translation_span_distance
from pdelie.verification import verify_translation_generator


_SUMMARY_PREFIX_KEYS = {"summary_schema_version", "summary_type"}
_FIT_DIAGNOSTIC_SUMMARY_KEYS = _SUMMARY_PREFIX_KEYS | {
    "parameterization",
    "fit_mode",
    "training_epsilon",
    "basis",
    "basis_delta_norms",
    "design_column_norms",
    "singular_values",
    "condition_number",
    "fit_residual",
    "min_delta_basis",
    "selected_coefficients",
    "svd_coefficients",
    "selected_span_distance",
    "svd_span_distance",
    "reference_fallback_used",
    "fallback_reason",
    "evidence_label",
}
_FORMULA_GENERATOR_SUMMARY_KEYS = _SUMMARY_PREFIX_KEYS | {
    "parameterization",
    "schema_version",
    "variables",
    "component_names",
    "generator_count",
    "generator_names",
    "formula_kinds",
    "component_nodes",
    "finite_transform_available",
    "finite_transform_construction_method",
    "symbolic_references",
    "reciprocal_denominator_floor",
    "diagnostics",
}
_GENERATOR_CONFIDENCE_SUMMARY_KEYS = _SUMMARY_PREFIX_KEYS | {
    "confidence_label",
    "component_statuses",
    "residual",
    "generator",
    "fit_diagnostics",
    "verification",
    "candidate_validation",
    "coverage",
    "consistency",
    "orbit",
    "thresholds",
    "missing_evidence",
    "extra_metrics",
}


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


def _candidate_validation_summary(conclusion: str) -> dict[str, object]:
    return {
        "summary_schema_version": "0.1",
        "summary_type": "symmetry_candidate_validation",
        "candidate_kind": "generator_family",
        "source_candidate_id": "reporting-test",
        "conclusion": conclusion,
        "check_reports": {},
    }


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


def test_summarize_formula_generator_family_reports_safe_formula_metadata() -> None:
    formula = FormulaGeneratorFamily(
        formula_generators=[
            {
                "name": "formula_fixture",
                "components": {
                    "tau": {"node": "const", "value": 0.0},
                    "xi": {
                        "node": "sin",
                        "arg": {"node": "var", "name": "x"},
                    },
                    "phi": {
                        "node": "symbolic_reference",
                        "label": "external_phi",
                        "metadata": {"source": "unit-test"},
                    },
                },
            }
        ],
        diagnostics={"status": "fixture"},
    )

    summary = summarize_formula_generator_family(formula)

    assert set(summary) == _FORMULA_GENERATOR_SUMMARY_KEYS
    assert summary["summary_schema_version"] == "0.1"
    assert summary["summary_type"] == "formula_generator_family"
    assert summary["parameterization"] == "formula_generator_family"
    assert summary["generator_count"] == 1
    assert summary["generator_names"] == ["formula_fixture"]
    assert summary["formula_kinds"]["sin"] == 1
    assert summary["formula_kinds"]["symbolic_reference"] == 1
    assert summary["finite_transform_available"] is False
    assert summary["symbolic_references"][0]["label"] == "external_phi"
    assert summary["diagnostics"] == {"status": "fixture"}
    _assert_json_serializable(summary)


def test_summarize_generator_fit_diagnostics_reports_direct_svd_fit(heat_artifacts: dict[str, object]) -> None:
    generator = heat_artifacts["generator"]

    summary = summarize_generator_fit_diagnostics(generator)

    assert set(summary) == _FIT_DIAGNOSTIC_SUMMARY_KEYS
    assert summary["summary_schema_version"] == "0.1"
    assert summary["summary_type"] == "generator_fit_diagnostics"
    assert summary["parameterization"] == generator.parameterization
    assert summary["fit_mode"] == "svd"
    assert summary["training_epsilon"] == pytest.approx(1e-4)
    assert summary["basis"] == generator.diagnostics["basis"]
    assert summary["basis_delta_norms"] == generator.diagnostics["basis_delta_norms"]
    assert summary["design_column_norms"] == generator.diagnostics["design_column_norms"]
    assert np.all(np.isfinite(summary["singular_values"]))
    assert summary["condition_number"] > 0.0
    assert summary["fit_residual"] == pytest.approx(generator.diagnostics["fit_residual"])
    assert summary["min_delta_basis"] == generator.diagnostics["min_delta_basis"]
    assert summary["selected_coefficients"] == pytest.approx(generator.coefficients[0].tolist())
    assert summary["svd_coefficients"] == pytest.approx(generator.diagnostics["svd_coefficients"])
    assert summary["selected_span_distance"] == pytest.approx(translation_span_distance(generator.coefficients))
    assert summary["svd_span_distance"] == pytest.approx(generator.diagnostics["svd_span_distance"])
    assert summary["reference_fallback_used"] is False
    assert summary["fallback_reason"] is None
    assert summary["evidence_label"] == "direct_svd_in_tolerance"
    _assert_json_serializable(summary)


def test_summarize_generator_fit_diagnostics_reports_reference_fallback_fit() -> None:
    field = generate_burgers_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=2010)
    generator = fit_translation_generator(field, BurgersResidualEvaluator(), epsilon=1e-4)

    summary = summarize_generator_fit_diagnostics(generator)

    assert summary["fit_mode"] == "reference_fallback"
    assert summary["reference_fallback_used"] is True
    assert summary["fallback_reason"] == "svd_translation_span_drift"
    assert summary["evidence_label"] == "reference_fallback"
    assert summary["selected_span_distance"] <= 5e-2
    assert summary["svd_span_distance"] > 5e-2
    _assert_json_serializable(summary)


def test_summarize_generator_fit_diagnostics_reports_unavailable_for_sparse_diagnostics() -> None:
    generator = GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={"singular_values": [2.0, 0.0]},
    )

    summary = summarize_generator_fit_diagnostics(generator)

    assert set(summary) == _FIT_DIAGNOSTIC_SUMMARY_KEYS
    assert summary["condition_number"] is None
    assert summary["evidence_label"] == "unavailable"
    assert summary["selected_coefficients"] == [1.0, 0.0, 0.0, 0.0]
    assert summary["selected_span_distance"] == pytest.approx(0.0)
    _assert_json_serializable(summary)


def test_summarize_generator_fit_diagnostics_normalizes_nonfinite_optional_scalars() -> None:
    generator = GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={
            "training_epsilon": np.inf,
            "fit_residual": np.nan,
            "singular_values": [2.0, 1.0],
        },
    )

    summary = summarize_generator_fit_diagnostics(generator)

    assert summary["training_epsilon"] is None
    assert summary["fit_residual"] is None
    assert summary["condition_number"] == pytest.approx(2.0)
    _assert_json_serializable(summary)


def test_summarize_generator_fit_diagnostics_rejects_non_scalar_mapping_values() -> None:
    generator = GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={
            "basis_delta_norms": {"1": [1.0, 2.0]},
            "singular_values": [2.0, 1.0],
        },
    )

    with pytest.raises(SchemaValidationError, match=r"basis_delta_norms\.1"):
        summarize_generator_fit_diagnostics(generator)


def test_summarize_generator_fit_diagnostics_rejects_non_floatlike_mapping_values() -> None:
    generator = GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={
            "design_column_norms": {"1": "not-a-number"},
            "singular_values": [2.0, 1.0],
        },
    )

    with pytest.raises(SchemaValidationError, match=r"design_column_norms\.1"):
        summarize_generator_fit_diagnostics(generator)


def test_summarize_generator_fit_diagnostics_computes_condition_number_from_unsorted_singular_values() -> None:
    generator = GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={
            "singular_values": [1.0, 4.0, 2.0],
            "condition_number": 99.0,
        },
    )

    summary = summarize_generator_fit_diagnostics(generator)

    assert summary["condition_number"] == pytest.approx(4.0)
    assert summary["singular_values"] == [1.0, 4.0, 2.0]
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


def test_summarize_invariant_workflow_combines_reports_and_canonical_objects(
    heat_artifacts: dict[str, object],
) -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=14020)
    domain_length = 2.0 * np.pi
    shifts = [0.0, domain_length / 16.0, domain_length]
    coverage = compute_periodic_window_coverage(
        x=field.coords["x"],
        windows=[{"start": 0.0, "width": domain_length / 4.0}],
        shifts=shifts,
        domain_length=domain_length,
    )
    consistency = diagnose_uniform_translation_consistency(
        field,
        shifts=shifts,
        residual_evaluator=HeatResidualEvaluator(),
    )
    orbit = summarize_uniform_translation_orbit(
        field,
        shifts=shifts,
        windows=[{"start": 0.0, "width": domain_length / 4.0}],
        residual_evaluator=HeatResidualEvaluator(),
        source_field_id="heat-reporting-fixture",
    )

    summary = summarize_invariant_workflow(
        orbit=orbit,
        coverage=[coverage],
        consistency=consistency,
        generator=heat_artifacts["generator"],
        verification=heat_artifacts["verification"],
        extra_metrics={"numpy_array": np.asarray([1.0, 2.0])},
    )

    assert set(summary) == _SUMMARY_PREFIX_KEYS | {
        "orbit",
        "coverage",
        "consistency",
        "generator",
        "fit_diagnostics",
        "verification",
        "extra_metrics",
    }
    assert summary["summary_schema_version"] == "0.1"
    assert summary["summary_type"] == "invariant_workflow"
    assert summary["orbit"]["summary_type"] == "uniform_translation_orbit"
    assert summary["coverage"][0]["summary_type"] == "periodic_window_coverage"
    assert summary["consistency"]["summary_type"] == "uniform_translation_consistency"
    assert summary["generator"]["summary_type"] == "generator_family"
    assert summary["fit_diagnostics"]["summary_type"] == "generator_fit_diagnostics"
    assert summary["verification"]["summary_type"] == "verification_report"
    assert summary["extra_metrics"] == {"numpy_array": [1.0, 2.0]}
    _assert_json_serializable(summary)


def test_summarize_invariant_workflow_accepts_precomputed_fit_summary(
    heat_artifacts: dict[str, object],
) -> None:
    fit_summary = summarize_generator_fit_diagnostics(heat_artifacts["generator"])
    verification_summary = summarize_verification_report(heat_artifacts["verification"])

    summary = summarize_invariant_workflow(
        fit_diagnostics=fit_summary,
        verification=verification_summary,
    )

    assert summary["orbit"] is None
    assert summary["coverage"] is None
    assert summary["consistency"] is None
    assert summary["generator"] is None
    assert summary["fit_diagnostics"] == fit_summary
    assert summary["verification"] == verification_summary
    assert summary["extra_metrics"] == {}
    _assert_json_serializable(summary)


def test_summarize_invariant_workflow_rejects_malformed_reports() -> None:
    with pytest.raises(SchemaValidationError, match="orbit"):
        summarize_invariant_workflow(orbit={"summary_type": "periodic_window_coverage"})

    with pytest.raises(SchemaValidationError, match="coverage"):
        summarize_invariant_workflow(coverage={"summary_type": "uniform_translation_orbit"})

    with pytest.raises(SchemaValidationError, match="report mapping"):
        summarize_invariant_workflow(consistency=object())

    with pytest.raises(SchemaValidationError, match="extra_metrics"):
        summarize_invariant_workflow(extra_metrics=["not", "a", "mapping"])  # type: ignore[arg-type]


def test_summarize_generator_confidence_reports_strong_direct_svd_case(
    heat_artifacts: dict[str, object],
) -> None:
    summary = summarize_generator_confidence(
        residual=heat_artifacts["residual"],
        generator=heat_artifacts["generator"],
        verification=heat_artifacts["verification"],
        thresholds={
            "residual_max_abs": 1e-3,
            "residual_rms": 1e-4,
            "verification_first_error": 1e-5,
            "verification_max_error": 1e-4,
        },
        extra_metrics={"case": np.asarray(["heat"])},
    )

    assert set(summary) == _GENERATOR_CONFIDENCE_SUMMARY_KEYS
    assert summary["summary_schema_version"] == "0.1"
    assert summary["summary_type"] == "generator_confidence"
    assert summary["confidence_label"] == "strong"
    assert summary["component_statuses"]["residual"]["status"] == "passed"
    assert summary["component_statuses"]["fit"]["status"] == "passed"
    assert summary["component_statuses"]["verification"]["status"] == "passed"
    assert summary["component_statuses"]["candidate_validation"]["status"] == "unavailable"
    assert summary["fit_diagnostics"]["summary_type"] == "generator_fit_diagnostics"
    assert summary["generator"]["summary_type"] == "generator_family"
    assert summary["residual"]["summary_type"] == "residual_batch"
    assert summary["verification"]["summary_type"] == "verification_report"
    assert summary["thresholds"]["residual_max_abs"] == 1e-3
    assert summary["extra_metrics"] == {"case": ["heat"]}
    _assert_json_serializable(summary)


def test_summarize_generator_confidence_accepts_precomputed_reports(
    heat_artifacts: dict[str, object],
) -> None:
    residual_summary = summarize_residual_batch(heat_artifacts["residual"])
    fit_summary = summarize_generator_fit_diagnostics(heat_artifacts["generator"])
    verification_summary = summarize_verification_report(heat_artifacts["verification"])

    summary = summarize_generator_confidence(
        residual=residual_summary,
        fit_diagnostics=fit_summary,
        verification=verification_summary,
        thresholds={"residual_max_abs": 1e-3, "residual_rms": 1e-4},
    )

    assert summary["confidence_label"] == "strong"
    assert summary["residual"] == residual_summary
    assert summary["fit_diagnostics"] == fit_summary
    assert summary["verification"] == verification_summary
    assert summary["generator"] is None
    _assert_json_serializable(summary)


def test_summarize_generator_confidence_reports_qualified_reference_fallback() -> None:
    field = generate_burgers_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=2011)
    generator = fit_translation_generator(field, BurgersResidualEvaluator(), epsilon=1e-4)

    summary = summarize_generator_confidence(generator=generator)

    assert summary["confidence_label"] == "qualified"
    assert summary["component_statuses"]["fit"]["status"] == "warning"
    assert summary["fit_diagnostics"]["evidence_label"] == "reference_fallback"
    assert summary["missing_evidence"] == [
        "residual",
        "verification",
        "candidate_validation",
        "coverage",
        "consistency",
        "orbit",
    ]
    _assert_json_serializable(summary)


def test_summarize_generator_confidence_reports_qualified_partial_candidate() -> None:
    summary = summarize_generator_confidence(candidate_validation=_candidate_validation_summary("partially_validated"))

    assert summary["confidence_label"] == "qualified"
    assert summary["component_statuses"]["candidate_validation"]["status"] == "warning"
    assert summary["candidate_validation"]["conclusion"] == "partially_validated"
    _assert_json_serializable(summary)


def test_summarize_generator_confidence_reports_failed_candidate() -> None:
    summary = summarize_generator_confidence(candidate_validation=_candidate_validation_summary("failed"))

    assert summary["confidence_label"] == "failed"
    assert summary["component_statuses"]["candidate_validation"]["status"] == "failed"
    _assert_json_serializable(summary)


def test_summarize_generator_confidence_reports_failed_residual_threshold(
    heat_artifacts: dict[str, object],
) -> None:
    summary = summarize_generator_confidence(
        residual=heat_artifacts["residual"],
        generator=heat_artifacts["generator"],
        verification=heat_artifacts["verification"],
        thresholds={"residual_max_abs": 1e-12},
    )

    assert summary["confidence_label"] == "failed"
    assert summary["component_statuses"]["residual"]["status"] == "failed"
    assert summary["component_statuses"]["fit"]["status"] == "passed"
    _assert_json_serializable(summary)


def test_summarize_generator_confidence_reports_insufficient_evidence() -> None:
    summary = summarize_generator_confidence()

    assert summary["confidence_label"] == "insufficient_evidence"
    assert all(status["status"] == "unavailable" for status in summary["component_statuses"].values())
    assert summary["missing_evidence"] == [
        "residual",
        "fit",
        "verification",
        "candidate_validation",
        "coverage",
        "consistency",
        "orbit",
    ]
    _assert_json_serializable(summary)


def test_summarize_generator_confidence_handles_coverage_consistency_and_orbit_reports(
    heat_artifacts: dict[str, object],
) -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=9, num_points=16, seed=1220)
    coverage = compute_periodic_window_coverage(
        x=field.coords["x"],
        windows=[{"start": 0.0, "width": np.pi / 2}],
        shifts=[0.0, np.pi / 2, np.pi, 3 * np.pi / 2],
    )
    consistency = diagnose_uniform_translation_consistency(
        field,
        shifts=[0.0, float(field.coords["x"][1] - field.coords["x"][0])],
        residual_evaluator=HeatResidualEvaluator(),
    )
    orbit = summarize_uniform_translation_orbit(
        field,
        shifts=[0.0, float(field.coords["x"][1] - field.coords["x"][0])],
        residual_evaluator=HeatResidualEvaluator(),
    )

    summary = summarize_generator_confidence(
        generator=heat_artifacts["generator"],
        verification=heat_artifacts["verification"],
        coverage=coverage,
        consistency=consistency,
        orbit=orbit,
        thresholds={"coverage_fraction_min": 0.25},
    )

    assert summary["confidence_label"] == "strong"
    assert summary["component_statuses"]["coverage"]["status"] == "passed"
    assert summary["component_statuses"]["consistency"]["status"] == "passed"
    assert summary["component_statuses"]["orbit"]["status"] == "passed"
    _assert_json_serializable(summary)


def test_summarize_generator_confidence_rejects_malformed_inputs(
    heat_artifacts: dict[str, object],
) -> None:
    with pytest.raises(SchemaValidationError, match="residual"):
        summarize_generator_confidence(residual={"summary_type": "verification_report"})
    with pytest.raises(SchemaValidationError, match="fit_diagnostics"):
        summarize_generator_confidence(fit_diagnostics=object())  # type: ignore[arg-type]
    with pytest.raises(SchemaValidationError, match="thresholds contains unsupported keys"):
        summarize_generator_confidence(thresholds={"score": 1.0})
    with pytest.raises(SchemaValidationError, match="extra_metrics"):
        summarize_generator_confidence(extra_metrics=["not", "mapping"])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("helper", "argument"),
    [
        (summarize_residual_batch, object()),
        (summarize_generator_fit_diagnostics, object()),
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
    summarize_generator_fit_diagnostics(generator)
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
    summarize_generator_confidence(
        residual=residual,
        generator=generator,
        verification=verification,
        thresholds={"residual_max_abs": 1e-3, "residual_rms": 1e-4},
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
