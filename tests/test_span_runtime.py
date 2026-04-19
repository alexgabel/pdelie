from __future__ import annotations

import numpy as np
import pytest

from pdelie import GeneratorFamily, SchemaValidationError, ShapeValidationError
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.symmetry import compare_generator_spans


def _txu_basis_spec() -> dict[str, object]:
    return {
        "variables": ["t", "x", "u"],
        "component_names": ["tau", "xi", "phi"],
        "basis_terms": [
            {"label": "1", "powers": [0, 0, 0]},
            {"label": "t", "powers": [1, 0, 0]},
            {"label": "x", "powers": [0, 1, 0]},
            {"label": "u", "powers": [0, 0, 1]},
        ],
        "component_ordering": ["tau", "xi", "phi"],
        "term_ordering": ["1", "t", "x", "u"],
        "layout": "component_major",
    }


def _make_generator(
    coefficients: np.ndarray,
    *,
    basis_spec: dict[str, object],
    normalization: str = "runtime_fixture",
    parameterization: str = "algebraic_fixture",
) -> GeneratorFamily:
    return GeneratorFamily(
        parameterization=parameterization,
        coefficients=np.asarray(coefficients, dtype=float),
        basis_spec=basis_spec,
        normalization=normalization,
        diagnostics={},
    )


def test_compare_generator_spans_matches_identical_translation_spans() -> None:
    reference = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        parameterization="polynomial_translation_affine",
    )
    candidate = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        parameterization="polynomial_translation_affine",
    )

    report = compare_generator_spans(reference, candidate)

    assert report["inner_product"] == "normalized_polynomial_l2"
    assert report["evaluation_mode"] == "exact_polynomial"
    assert report["reference_rank"] == 1
    assert report["candidate_rank"] == 1
    assert report["comparison_rank"] == 1
    np.testing.assert_allclose(report["principal_angles_radians"], [0.0], atol=1e-12)
    assert report["projection_residual"]["summary"] == pytest.approx(0.0, abs=1e-12)
    assert report["projection_residual"]["reference_to_candidate"] == pytest.approx(0.0, abs=1e-12)
    assert report["projection_residual"]["candidate_to_reference"] == pytest.approx(0.0, abs=1e-12)


def test_compare_generator_spans_matches_legacy_upgraded_translation_against_canonical() -> None:
    legacy = GeneratorFamily.from_dict(
        {
            "schema_version": "0.1",
            "parameterization": "polynomial_translation_affine",
            "coefficients": [1.0, 0.0, 0.0, 0.0],
            "normalization": "l2_unit",
            "diagnostics": {},
        }
    )
    canonical = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        parameterization="polynomial_translation_affine",
    )

    report = compare_generator_spans(legacy, canonical)

    np.testing.assert_allclose(report["principal_angles_radians"], [0.0], atol=1e-12)
    assert report["projection_residual"]["summary"] == pytest.approx(0.0, abs=1e-12)


def test_compare_generator_spans_matches_same_span_under_basis_change() -> None:
    reference = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        parameterization="polynomial_translation_affine",
    )
    candidate = _make_generator(
        np.array([[1.0, 1.0, 0.0, 0.0], [1.0, -1.0, 0.0, 0.0]], dtype=float) / np.sqrt(2.0),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        parameterization="polynomial_translation_affine",
    )

    report = compare_generator_spans(reference, candidate)

    np.testing.assert_allclose(report["principal_angles_radians"], [0.0, 0.0], atol=1e-12)
    assert report["projection_residual"]["summary"] == pytest.approx(0.0, abs=1e-12)


def test_compare_generator_spans_reports_nonzero_angle_for_distinct_one_dimensional_spans() -> None:
    reference = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        parameterization="polynomial_translation_affine",
    )
    candidate = _make_generator(
        np.array([[0.0, 1.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        parameterization="polynomial_translation_affine",
    )

    report = compare_generator_spans(reference, candidate)
    angle = float(report["principal_angles_radians"][0])

    assert angle > 0.1
    assert report["projection_residual"]["summary"] > 0.0


def test_compare_generator_spans_reports_directional_residual_for_strict_containment() -> None:
    reference = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        parameterization="polynomial_translation_affine",
    )
    candidate = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        parameterization="polynomial_translation_affine",
    )

    report = compare_generator_spans(reference, candidate)

    np.testing.assert_allclose(report["principal_angles_radians"], [0.0], atol=1e-12)
    assert report["projection_residual"]["reference_to_candidate"] == pytest.approx(0.0, abs=1e-12)
    assert report["projection_residual"]["candidate_to_reference"] > 0.0
    assert report["projection_residual"]["summary"] == pytest.approx(
        report["projection_residual"]["candidate_to_reference"],
        rel=0.0,
        abs=1e-12,
    )


def test_compare_generator_spans_accepts_structurally_equivalent_basis_specs() -> None:
    reordered_basis_spec = {
        "layout": "component_major",
        "term_ordering": ["1", "t", "x", "u"],
        "basis_terms": [
            {"powers": [0, 0, 0], "label": "1"},
            {"powers": [1, 0, 0], "label": "t"},
            {"powers": [0, 1, 0], "label": "x"},
            {"powers": [0, 0, 1], "label": "u"},
        ],
        "component_ordering": ["xi"],
        "component_names": ["xi"],
        "variables": ["t", "x", "u"],
    }
    reference = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        parameterization="polynomial_translation_affine",
    )
    candidate = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=reordered_basis_spec,
        parameterization="polynomial_translation_affine",
    )

    report = compare_generator_spans(reference, candidate)

    np.testing.assert_allclose(report["principal_angles_radians"], [0.0], atol=1e-12)


def test_compare_generator_spans_rejects_non_equivalent_basis_semantics() -> None:
    mismatched = {
        "variables": ["x", "t", "u"],
        "component_names": ["xi"],
        "basis_terms": [
            {"label": "1", "powers": [0, 0, 0]},
            {"label": "t", "powers": [0, 1, 0]},
            {"label": "x", "powers": [1, 0, 0]},
            {"label": "u", "powers": [0, 0, 1]},
        ],
        "component_ordering": ["xi"],
        "term_ordering": ["1", "t", "x", "u"],
        "layout": "component_major",
    }

    reference = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        parameterization="polynomial_translation_affine",
    )
    candidate = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=mismatched,
        parameterization="polynomial_translation_affine",
    )

    with pytest.raises(SchemaValidationError, match="structurally equivalent basis_spec"):
        compare_generator_spans(reference, candidate)


def test_compare_generator_spans_rejects_zero_rank_spans() -> None:
    reference = _make_generator(
        np.zeros((1, 4), dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        parameterization="polynomial_translation_affine",
    )
    candidate = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        parameterization="polynomial_translation_affine",
    )

    with pytest.raises(ShapeValidationError, match="nonzero rank"):
        compare_generator_spans(reference, candidate)


def test_compare_generator_spans_returns_required_core_report_schema() -> None:
    reference = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        parameterization="polynomial_translation_affine",
    )
    candidate = _make_generator(
        np.array([[0.0, 1.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        parameterization="polynomial_translation_affine",
    )

    report = compare_generator_spans(reference, candidate)

    assert set(report) == {
        "inner_product",
        "evaluation_mode",
        "domain",
        "component_weights",
        "reference_rank",
        "candidate_rank",
        "comparison_rank",
        "principal_angles_radians",
        "projection_residual",
        "conditioning",
    }
    assert set(report["projection_residual"]) == {
        "summary",
        "reference_to_candidate",
        "candidate_to_reference",
    }
    assert set(report["conditioning"]) == {
        "ambient_metric",
        "reference_span",
        "candidate_span",
    }


def test_compare_generator_spans_supports_multi_component_polynomial_fixtures() -> None:
    reference = _make_generator(
        np.array([[0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -1.0]], dtype=float),
        basis_spec=_txu_basis_spec(),
    )
    candidate = _make_generator(
        np.array([[0.0, 2.0, 0.0, 0.0, 0.0, 0.0, 2.0, 0.0, 0.0, 0.0, 0.0, -2.0]], dtype=float),
        basis_spec=_txu_basis_spec(),
    )

    report = compare_generator_spans(reference, candidate)

    np.testing.assert_allclose(report["principal_angles_radians"], [0.0], atol=1e-12)
