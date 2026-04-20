from __future__ import annotations

import numpy as np
import pytest

from pdelie import GeneratorFamily, ScopeValidationError, ShapeValidationError, VerificationReport
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.symmetry import diagnose_generator_family_closure


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


def _x_basis_spec(labels: list[str] | None = None, powers: list[list[int]] | None = None) -> dict[str, object]:
    powers = [[0], [1]] if powers is None else powers
    if labels is None:
        labels = ["1", "x"] if powers == [[0], [1]] else [("1" if item == [0] else f"x^{item[0]}") for item in powers]
    return {
        "variables": ["x"],
        "component_names": ["xi"],
        "basis_terms": [
            {"label": label, "powers": power}
            for label, power in zip(labels, powers)
        ],
        "component_ordering": ["xi"],
        "term_ordering": list(labels),
        "layout": "component_major",
    }


def _velocity_basis_spec(labels: list[str] | None = None) -> dict[str, object]:
    labels = ["1", "x"] if labels is None else labels
    return {
        "variables": ["x"],
        "component_names": ["velocity"],
        "basis_terms": [
            {"label": labels[0], "powers": [0]},
            {"label": labels[1], "powers": [1]},
        ],
        "component_ordering": ["velocity"],
        "term_ordering": list(labels),
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


def _make_verification_report(classification: str) -> VerificationReport:
    return VerificationReport(
        norm="relative_l2",
        epsilon_values=np.logspace(-4, -1, 7),
        error_curve=np.full(7, 1e-8 if classification != "failed" else 1.0, dtype=float),
        classification=classification,
        diagnostics={},
    )


def test_diagnose_generator_family_closure_commuting_family_is_closed() -> None:
    generator = _make_generator(
        np.array(
            [
                [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
            ],
            dtype=float,
        ),
        basis_spec=_txu_basis_spec(),
    )

    report = diagnose_generator_family_closure(generator)

    assert report["computation_mode"] == "exact_polynomial"
    assert report["interpretation_label"] == "vector_field_algebra_diagnostics"
    assert report["family_rank"] == 2
    assert report["closure"]["summary"] == pytest.approx(0.0, abs=1e-12)
    assert report["antisymmetry"]["summary"] == pytest.approx(0.0, abs=1e-12)
    assert report["jacobi"]["summary"] == pytest.approx(0.0, abs=1e-12)
    np.testing.assert_allclose(report["structure_constants"]["tensor"], np.zeros((2, 2, 2)), atol=1e-12)


def test_diagnose_generator_family_closure_reports_expected_affine_structure_constants() -> None:
    generator = _make_generator(
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float),
        basis_spec=_x_basis_spec(),
    )

    report = diagnose_generator_family_closure(generator)
    tensor = np.asarray(report["structure_constants"]["tensor"], dtype=float)

    assert report["closure"]["summary"] == pytest.approx(0.0, abs=1e-12)
    np.testing.assert_allclose(tensor[0, 1], [1.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(tensor[1, 0], [-1.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(tensor[0, 0], [0.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(tensor[1, 1], [0.0, 0.0], atol=1e-12)


def test_diagnose_generator_family_closure_reports_zero_structure_constant_jacobi_for_closed_three_generator_family() -> None:
    generator = _make_generator(
        np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
            ],
            dtype=float,
        ),
        basis_spec=_x_basis_spec(labels=["1", "x", "x^2"], powers=[[0], [1], [2]]),
    )

    report = diagnose_generator_family_closure(generator)

    assert report["closure"]["summary"] == pytest.approx(0.0, abs=1e-12)
    assert report["jacobi"]["mode"] == "structure_constants"
    assert report["jacobi"]["summary"] == pytest.approx(0.0, abs=1e-12)


def test_diagnose_generator_family_closure_handles_exact_brackets_outside_stored_basis_via_projection() -> None:
    generator = _make_generator(
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float),
        basis_spec=_x_basis_spec(labels=["x^2", "x^3"], powers=[[2], [3]]),
    )

    report = diagnose_generator_family_closure(generator)

    assert report["computation_mode"] == "exact_polynomial"
    assert report["closure"]["summary"] > 1e-6
    assert report["structure_constants"]["estimation_mode"] == "exact_polynomial"


def test_diagnose_generator_family_closure_component_targets_override_inference() -> None:
    generator = _make_generator(
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float),
        basis_spec=_velocity_basis_spec(),
    )

    report = diagnose_generator_family_closure(generator, component_targets={"velocity": "x"})

    assert report["component_targets"] == {"velocity": "x"}
    assert report["closure"]["summary"] == pytest.approx(0.0, abs=1e-12)


def test_diagnose_generator_family_closure_rejects_unresolved_component_targets() -> None:
    generator = _make_generator(
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float),
        basis_spec=_velocity_basis_spec(),
    )

    with pytest.raises(ScopeValidationError, match="resolved component targets"):
        diagnose_generator_family_closure(generator)


def test_diagnose_generator_family_closure_rejects_noncanonical_basis_labels_in_exact_mode_and_downgrades_in_auto() -> None:
    generator = _make_generator(
        np.array([[1.0, 0.0]], dtype=float),
        basis_spec=_velocity_basis_spec(labels=["offset", "linear"]),
    )

    with pytest.raises(ScopeValidationError, match="exact_polynomial"):
        diagnose_generator_family_closure(
            generator,
            component_targets={"velocity": "x"},
            computation_mode="exact_polynomial",
        )

    report = diagnose_generator_family_closure(
        generator,
        component_targets={"velocity": "x"},
        computation_mode="auto",
    )

    assert report["computation_mode"] == "sampled_projection"
    assert report["closure"]["summary"] == pytest.approx(0.0, abs=1e-12)


def test_diagnose_generator_family_closure_sampled_projection_is_deterministic() -> None:
    generator = _make_generator(
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float),
        basis_spec=_x_basis_spec(),
    )

    first = diagnose_generator_family_closure(generator, computation_mode="sampled_projection")
    second = diagnose_generator_family_closure(generator, computation_mode="sampled_projection")

    assert first["computation_mode"] == "sampled_projection"
    np.testing.assert_allclose(first["structure_constants"]["tensor"], second["structure_constants"]["tensor"], atol=1e-12)
    np.testing.assert_allclose(first["closure"]["pairwise_residuals"], second["closure"]["pairwise_residuals"], atol=1e-12)
    np.testing.assert_allclose(first["antisymmetry"]["pairwise_residuals"], second["antisymmetry"]["pairwise_residuals"], atol=1e-12)


@pytest.mark.parametrize(
    ("verification_reports", "expected_label", "expected_classifications"),
    [
        (None, "vector_field_algebra_diagnostics", None),
        ([], "vector_field_algebra_diagnostics", []),
        ([("failed")], "vector_field_algebra_diagnostics", ["failed"]),
        ([("exact"), ("approximate")], "symmetry_algebra_diagnostics", ["exact", "approximate"]),
        ([("exact"), ("failed")], "vector_field_algebra_diagnostics", ["exact", "failed"]),
    ],
)
def test_diagnose_generator_family_closure_uses_family_aware_interpretation_labels(
    verification_reports: list[str] | None,
    expected_label: str,
    expected_classifications: list[str] | None,
) -> None:
    generator = _make_generator(
        np.array([[1.0, 0.0]], dtype=float),
        basis_spec=_x_basis_spec(),
    )
    reports = (
        None
        if verification_reports is None
        else [_make_verification_report(classification) for classification in verification_reports]
    )

    report = diagnose_generator_family_closure(generator, verification_reports=reports)

    assert report["interpretation_label"] == expected_label
    assert report["verification_classifications"] == expected_classifications


def test_diagnose_generator_family_closure_rejects_rank_deficient_family_with_degeneracy_message() -> None:
    generator = _make_generator(
        np.array([[1.0, 0.0], [2.0, 0.0]], dtype=float),
        basis_spec=_x_basis_spec(),
    )

    with pytest.raises(ShapeValidationError, match="rank-deficient family"):
        diagnose_generator_family_closure(generator)


def test_diagnose_generator_family_closure_returns_required_core_report_schema() -> None:
    generator = _make_generator(
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float),
        basis_spec=_x_basis_spec(),
    )

    report = diagnose_generator_family_closure(generator)

    assert set(report) == {
        "interpretation_label",
        "verification_classifications",
        "inner_product",
        "computation_mode",
        "domain",
        "component_weights",
        "component_targets",
        "family_rank",
        "structure_constants",
        "closure",
        "antisymmetry",
        "jacobi",
        "conditioning",
    }
    assert set(report["structure_constants"]) == {"tensor", "estimation_mode", "conditioning"}
    assert set(report["closure"]) == {"summary", "pairwise_residuals"}
    assert set(report["antisymmetry"]) == {"summary", "pairwise_residuals"}
    assert set(report["jacobi"]) == {"summary", "triple_residuals", "mode"}
