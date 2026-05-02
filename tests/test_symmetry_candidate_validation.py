from __future__ import annotations

import json

import numpy as np
import pytest

import pdelie
from pdelie import GeneratorFamily, InvariantMapSpec
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.data import generate_heat_1d_field_batch, generate_kdv_1d_field_batch
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.residuals import HeatResidualEvaluator, KdVResidualEvaluator
from pdelie.symmetry import validate_symmetry_candidate


DOMAIN_LENGTH = 2.0 * np.pi


def _translation_generator(coefficients: list[float] | None = None) -> GeneratorFamily:
    coefficients = [1.0, 0.0, 0.0, 0.0] if coefficients is None else coefficients
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.asarray([coefficients], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )


def _legacy_translation_generator_payload() -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "parameterization": "polynomial_translation_affine",
        "coefficients": [1.0, 0.0, 0.0, 0.0],
        "normalization": "l2_unit",
        "diagnostics": {},
    }


def _translation_spec(shift: float = DOMAIN_LENGTH / 8.0) -> InvariantMapSpec:
    return InvariantMapSpec(
        generator_metadata=_translation_generator().to_dict(),
        construction_method="uniform_translation",
        parameters={"axis": "x", "shift": shift},
        domain_validity="global",
        inverse_available=True,
        diagnostics={},
    )


def _x_basis_spec() -> dict[str, object]:
    return {
        "variables": ["x"],
        "component_names": ["xi"],
        "basis_terms": [
            {"label": "1", "powers": [0]},
            {"label": "x", "powers": [1]},
        ],
        "component_ordering": ["xi"],
        "term_ordering": ["1", "x"],
        "layout": "component_major",
    }


def _closed_two_generator_family() -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="algebraic_fixture",
        coefficients=np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=float),
        basis_spec=_x_basis_spec(),
        normalization="runtime_fixture",
        diagnostics={},
    )


def _assert_json_plain(value: object) -> None:
    assert not isinstance(value, (np.ndarray, np.generic))
    if isinstance(value, dict):
        for key, item in value.items():
            assert isinstance(key, str)
            _assert_json_plain(item)
    elif isinstance(value, list):
        for item in value:
            _assert_json_plain(item)
    else:
        assert value is None or isinstance(value, (str, int, float, bool))


def test_validate_symmetry_candidate_accepts_heat_generator_family() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=9, num_points=32, seed=1601)
    report = validate_symmetry_candidate(
        field,
        _translation_generator(),
        residual_evaluator=HeatResidualEvaluator(),
        reference_generator=_translation_generator(),
        source_candidate_id={"source": "unit-test", "candidate": "heat-translation"},
    )

    assert json.loads(json.dumps(report)) == report
    _assert_json_plain(report)
    assert report["summary_schema_version"] == "0.1"
    assert report["summary_type"] == "symmetry_candidate_validation"
    assert report["candidate_kind"] == "generator_family"
    assert report["source_candidate_id"] == {"source": "unit-test", "candidate": "heat-translation"}
    assert report["empirical_interpretation"] == "configured_validation_not_mathematical_proof"
    assert report["conclusion"] == "validated"
    assert report["check_reports"]["finite_transform_verification"]["status"] == "passed"
    assert report["check_reports"]["finite_transform_verification"]["report"]["classification"] != "failed"
    assert report["check_reports"]["reference_span_comparison"]["status"] == "passed"


def test_validate_symmetry_candidate_accepts_kdv_generator_family() -> None:
    field = generate_kdv_1d_field_batch(batch_size=3, num_times=9, num_points=32, num_modes=1, seed=1602)
    report = validate_symmetry_candidate(
        field,
        _translation_generator(),
        residual_evaluator=KdVResidualEvaluator(),
    )

    assert report["candidate_kind"] == "generator_family"
    assert report["conclusion"] == "validated"
    assert report["check_reports"]["finite_transform_verification"]["report"]["classification"] != "failed"


def test_validate_symmetry_candidate_accepts_generator_family_payload() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=9, num_points=32, seed=1603)
    payload = _translation_generator().to_dict()

    report = validate_symmetry_candidate(field, payload, residual_evaluator=HeatResidualEvaluator())

    assert report["candidate_kind"] == "generator_family"
    assert report["conclusion"] == "validated"
    assert report["candidate_summary"]["parameterization"] == "polynomial_translation_affine"


def test_validate_symmetry_candidate_rejects_legacy_generator_family_payloads() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=9, num_points=32, seed=1612)
    legacy_payload = _legacy_translation_generator_payload()

    # The canonical object loader keeps the narrow legacy compatibility path,
    # but the v0.16 external validator only accepts current canonical payloads.
    assert GeneratorFamily.from_dict(legacy_payload).schema_version == GeneratorFamily.SCHEMA_VERSION

    with pytest.raises(SchemaValidationError, match="canonical GeneratorFamily schema_version"):
        validate_symmetry_candidate(
            field,
            legacy_payload,
            residual_evaluator=HeatResidualEvaluator(),
        )

    with pytest.raises(SchemaValidationError, match="canonical GeneratorFamily schema_version"):
        validate_symmetry_candidate(
            field,
            _translation_generator(),
            residual_evaluator=HeatResidualEvaluator(),
            reference_generator=legacy_payload,
        )


def test_validate_symmetry_candidate_reports_failed_wrong_span_generator() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=9, num_points=32, seed=1604)
    wrong = _translation_generator([0.0, 0.0, 1.0, 0.0])

    report = validate_symmetry_candidate(field, wrong, residual_evaluator=HeatResidualEvaluator())

    assert report["candidate_kind"] == "generator_family"
    assert report["conclusion"] == "failed"
    assert report["check_reports"]["finite_transform_verification"]["status"] == "failed"
    assert report["check_reports"]["finite_transform_verification"]["report"]["classification"] == "failed"


def test_validate_symmetry_candidate_runs_closure_for_multi_generator_family_only() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=9, num_points=32, seed=1605)

    report = validate_symmetry_candidate(
        field,
        _closed_two_generator_family(),
        residual_evaluator=HeatResidualEvaluator(),
    )

    assert report["candidate_kind"] == "generator_family"
    assert report["conclusion"] == "validated"
    assert "closure_diagnostics" in report["check_reports"]
    assert report["check_reports"]["closure_diagnostics"]["status"] == "passed"
    assert "finite_transform_verification" not in report["check_reports"]


def test_validate_symmetry_candidate_accepts_invariant_map_spec_object_and_payload() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=9, num_points=32, seed=1606)
    spec = _translation_spec()

    object_report = validate_symmetry_candidate(field, spec, residual_evaluator=HeatResidualEvaluator())
    payload_report = validate_symmetry_candidate(field, spec.to_dict(), residual_evaluator=HeatResidualEvaluator())

    for report in (object_report, payload_report):
        assert report["candidate_kind"] == "invariant_map_spec"
        assert report["conclusion"] == "validated"
        assert report["candidate_summary"]["construction_method"] == "uniform_translation"
        assert report["check_reports"]["residual_stability"]["status"] == "passed"
        assert report["check_reports"]["inverse_consistency"]["status"] == "passed"
        assert np.isfinite(report["check_reports"]["residual_stability"]["report"]["residual_rms_before"])
        assert np.isfinite(report["check_reports"]["residual_stability"]["report"]["residual_rms_after"])


def test_validate_symmetry_candidate_accepts_kdv_invariant_map_spec() -> None:
    field = generate_kdv_1d_field_batch(batch_size=3, num_times=9, num_points=32, num_modes=1, seed=1607)

    report = validate_symmetry_candidate(field, _translation_spec(), residual_evaluator=KdVResidualEvaluator())

    assert report["candidate_kind"] == "invariant_map_spec"
    assert report["conclusion"] == "validated"
    assert report["check_reports"]["residual_stability"]["status"] == "passed"


@pytest.mark.parametrize(
    ("spec_kwargs", "error_type", "match"),
    [
        ({"domain_validity": "local", "diagnostics": {"validity_note": "local fixture"}}, ScopeValidationError, "global"),
        ({"diagnostics": {"approximate": True, "approximation_note": "approximate fixture"}}, ScopeValidationError, "approximate"),
        ({"construction_method": "time_translation"}, ScopeValidationError, "uniform_translation"),
        ({"parameters": {"axis": "x"}}, SchemaValidationError, "shift"),
        ({"parameters": {"axis": "x", "shift": np.inf}}, SchemaValidationError, "finite"),
    ],
)
def test_validate_symmetry_candidate_rejects_unsupported_invariant_map_specs(
    spec_kwargs: dict[str, object],
    error_type: type[Exception],
    match: str,
) -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=9, num_points=32, seed=1608)
    base = _translation_spec().to_dict()
    base.update(spec_kwargs)
    if "parameters" in spec_kwargs:
        base["parameters"] = spec_kwargs["parameters"]

    with pytest.raises(error_type, match=match):
        validate_symmetry_candidate(field, base, residual_evaluator=HeatResidualEvaluator())


def test_validate_symmetry_candidate_rejects_callable_and_ambiguous_payloads() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=9, num_points=32, seed=1609)

    with pytest.raises(SchemaValidationError, match="Callable"):
        validate_symmetry_candidate(field, lambda value: value, residual_evaluator=HeatResidualEvaluator())

    payload = _translation_generator().to_dict()
    payload["construction_method"] = "uniform_translation"
    with pytest.raises(SchemaValidationError, match="ambiguous"):
        validate_symmetry_candidate(field, payload, residual_evaluator=HeatResidualEvaluator())


def test_validate_symmetry_candidate_rejects_malformed_payloads_with_typed_errors() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=9, num_points=32, seed=1610)

    with pytest.raises(SchemaValidationError, match="GeneratorFamily candidate payload is malformed"):
        validate_symmetry_candidate(
            field,
            {"parameterization": "polynomial_translation_affine"},
            residual_evaluator=HeatResidualEvaluator(),
        )

    with pytest.raises(SchemaValidationError, match="InvariantMapSpec candidate payload is malformed"):
        validate_symmetry_candidate(
            field,
            {"construction_method": "uniform_translation"},
            residual_evaluator=HeatResidualEvaluator(),
        )

    with pytest.raises(SchemaValidationError, match="reference_generator payload is malformed"):
        validate_symmetry_candidate(
            field,
            _translation_generator(),
            residual_evaluator=HeatResidualEvaluator(),
            reference_generator={"parameterization": "polynomial_translation_affine"},
        )


def test_validate_symmetry_candidate_rejects_bad_evaluator_epsilons_reference_and_scope() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=9, num_points=32, seed=1611)

    with pytest.raises(SchemaValidationError, match="residual_evaluator"):
        validate_symmetry_candidate(field, _translation_generator(), residual_evaluator=object())  # type: ignore[arg-type]

    with pytest.raises(SchemaValidationError, match="finite_transform_epsilons"):
        validate_symmetry_candidate(
            field,
            _translation_generator(),
            residual_evaluator=HeatResidualEvaluator(),
            finite_transform_epsilons=[1e-4, np.nan],
        )

    with pytest.raises(SchemaValidationError, match="reference_generator"):
        validate_symmetry_candidate(
            field,
            _translation_generator(),
            residual_evaluator=HeatResidualEvaluator(),
            reference_generator=object(),
        )

    nonperiodic = field.to_dict()
    nonperiodic["metadata"]["boundary_conditions"] = {"x": "dirichlet"}
    with pytest.raises(ScopeValidationError, match="periodic"):
        validate_symmetry_candidate(
            pdelie.FieldBatch.from_dict(nonperiodic),
            _translation_generator(),
            residual_evaluator=HeatResidualEvaluator(),
        )


def test_validate_symmetry_candidate_is_submodule_only() -> None:
    assert validate_symmetry_candidate is not None
    assert not hasattr(pdelie, "validate_symmetry_candidate")
