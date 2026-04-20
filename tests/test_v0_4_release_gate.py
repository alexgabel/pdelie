from __future__ import annotations

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.figure import Figure

from pdelie import GeneratorFamily, SchemaValidationError, VerificationReport
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.residuals import BurgersResidualEvaluator, HeatResidualEvaluator
from pdelie.symmetry import (
    compare_generator_spans,
    diagnose_generator_family_closure,
    render_generator_family,
)
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import verify_translation_generator
from pdelie.viz import (
    plot_closure_diagnostics,
    plot_generator_coefficients,
    plot_generator_symbolic_summary,
    plot_span_diagnostics,
    plot_verification_curve,
)


@pytest.fixture(autouse=True)
def _close_figures() -> None:
    yield
    plt.close("all")


def _translation_generator(coefficients: np.ndarray) -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.asarray(coefficients, dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )


def _x_basis_spec(*, labels: list[str], powers: list[list[int]]) -> dict[str, object]:
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


def _velocity_basis_spec(labels: list[str]) -> dict[str, object]:
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


def _algebraic_generator(coefficients: np.ndarray, *, basis_spec: dict[str, object]) -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="algebraic_fixture",
        coefficients=np.asarray(coefficients, dtype=float),
        basis_spec=basis_spec,
        normalization="runtime_fixture",
        diagnostics={},
    )


def _verification_report() -> VerificationReport:
    return VerificationReport(
        norm="relative_l2",
        epsilon_values=np.logspace(-4, -1, 7),
        error_curve=np.logspace(-7, -4, 7),
        classification="exact",
        diagnostics={},
    )


def test_v0_4_release_gate_migration_and_canonical_translation_serialization() -> None:
    legacy_payload = {
        "schema_version": "0.1",
        "parameterization": "polynomial_translation_affine",
        "coefficients": [1.0, 0.0, 0.0, 0.0],
        "normalization": "l2_unit",
        "diagnostics": {},
    }

    generator = GeneratorFamily.from_dict(legacy_payload)
    payload = generator.to_dict()
    basis_spec = generator.basis_spec

    assert generator.schema_version == "0.2"
    assert generator.parameterization == "polynomial_translation_affine"
    assert generator.coefficients.shape == (1, 4)
    np.testing.assert_allclose(generator.coefficients, np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float))
    assert basis_spec["variables"] == ["t", "x", "u"]
    assert basis_spec["component_names"] == ["xi"]
    assert basis_spec["term_ordering"] == ["1", "t", "x", "u"]
    assert basis_spec["layout"] == "component_major"
    assert payload["schema_version"] == "0.2"
    assert payload["coefficients"] == [[1.0, 0.0, 0.0, 0.0]]
    assert payload["basis_spec"]["variables"] == ["t", "x", "u"]
    assert payload["basis_spec"]["component_names"] == ["xi"]
    assert payload["basis_spec"]["term_ordering"] == ["1", "t", "x", "u"]
    assert payload["basis_spec"]["layout"] == "component_major"

    with pytest.raises(SchemaValidationError, match="basis_spec is required"):
        GeneratorFamily.from_dict(
            {
                "schema_version": "0.2",
                "parameterization": "algebraic_fixture",
                "coefficients": [[1.0, 0.0]],
                "normalization": "runtime_fixture",
                "diagnostics": {},
            }
        )


def test_v0_4_release_gate_symbolic_rendering_is_deterministic_for_translation_slice() -> None:
    canonical = _translation_generator(np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float))
    legacy = GeneratorFamily.from_dict(
        {
            "schema_version": "0.1",
            "parameterization": "polynomial_translation_affine",
            "coefficients": [1.0, 0.0, 0.0, 0.0],
            "normalization": "l2_unit",
            "diagnostics": {},
        }
    )

    first = render_generator_family(canonical)
    second = render_generator_family(canonical)
    upgraded = render_generator_family(legacy)

    assert first == ["X_1 = ∂x"]
    assert second == first
    assert upgraded == first


def test_v0_4_release_gate_span_diagnostics_are_reproducible_on_multi_rank_fixture() -> None:
    reference = _translation_generator(
        np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=float)
    )
    candidate = _translation_generator(
        np.array([[1.0, 1.0, 0.0, 0.0], [1.0, -1.0, 0.0, 0.0]], dtype=float) / np.sqrt(2.0)
    )

    first = compare_generator_spans(reference, candidate)
    second = compare_generator_spans(reference, candidate)

    assert first["inner_product"] == "normalized_polynomial_l2"
    assert first["evaluation_mode"] == "exact_polynomial"
    assert first["reference_rank"] == 2
    assert first["candidate_rank"] == 2
    assert first["comparison_rank"] == 2
    assert second["reference_rank"] == first["reference_rank"]
    assert second["candidate_rank"] == first["candidate_rank"]
    assert second["comparison_rank"] == first["comparison_rank"]
    np.testing.assert_allclose(first["principal_angles_radians"], [0.0, 0.0], atol=1e-12)
    np.testing.assert_allclose(first["principal_angles_radians"], second["principal_angles_radians"], atol=1e-12)
    assert first["projection_residual"]["summary"] == pytest.approx(0.0, abs=1e-12)
    assert second["projection_residual"]["summary"] == pytest.approx(
        first["projection_residual"]["summary"],
        abs=1e-12,
    )
    assert "ambient_metric" in first["conditioning"]
    assert "reference_span" in first["conditioning"]
    assert "candidate_span" in first["conditioning"]


def test_v0_4_release_gate_closure_diagnostics_are_reproducible_in_exact_and_fallback_modes() -> None:
    exact_generator = _algebraic_generator(
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
    fallback_generator = _algebraic_generator(
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float),
        basis_spec=_velocity_basis_spec(["offset", "linear"]),
    )

    exact_first = diagnose_generator_family_closure(exact_generator)
    exact_second = diagnose_generator_family_closure(exact_generator)
    fallback_first = diagnose_generator_family_closure(
        fallback_generator,
        component_targets={"velocity": "x"},
        computation_mode="auto",
    )
    fallback_second = diagnose_generator_family_closure(
        fallback_generator,
        component_targets={"velocity": "x"},
        computation_mode="auto",
    )

    assert exact_first["computation_mode"] == "exact_polynomial"
    assert exact_first["family_rank"] == 3
    assert exact_first["closure"]["summary"] == pytest.approx(0.0, abs=1e-12)
    assert exact_first["antisymmetry"]["summary"] == pytest.approx(0.0, abs=1e-12)
    assert exact_first["jacobi"]["summary"] == pytest.approx(0.0, abs=1e-12)
    assert np.asarray(exact_first["structure_constants"]["tensor"], dtype=float).shape == (3, 3, 3)
    np.testing.assert_allclose(
        exact_first["structure_constants"]["tensor"],
        exact_second["structure_constants"]["tensor"],
        atol=1e-12,
    )
    assert exact_second["closure"]["summary"] == pytest.approx(exact_first["closure"]["summary"], abs=1e-12)
    assert exact_second["antisymmetry"]["summary"] == pytest.approx(
        exact_first["antisymmetry"]["summary"],
        abs=1e-12,
    )
    assert exact_second["jacobi"]["summary"] == pytest.approx(exact_first["jacobi"]["summary"], abs=1e-12)

    assert fallback_first["computation_mode"] == "sampled_projection"
    assert fallback_first["family_rank"] == 2
    np.testing.assert_allclose(
        fallback_first["structure_constants"]["tensor"],
        fallback_second["structure_constants"]["tensor"],
        atol=1e-12,
    )
    np.testing.assert_allclose(
        fallback_first["closure"]["pairwise_residuals"],
        fallback_second["closure"]["pairwise_residuals"],
        atol=1e-12,
    )
    assert fallback_second["closure"]["summary"] == pytest.approx(
        fallback_first["closure"]["summary"],
        abs=1e-12,
    )
    assert fallback_second["antisymmetry"]["summary"] == pytest.approx(
        fallback_first["antisymmetry"]["summary"],
        abs=1e-12,
    )
    assert fallback_second["jacobi"]["summary"] == pytest.approx(
        fallback_first["jacobi"]["summary"],
        abs=1e-12,
    )


def test_v0_4_release_gate_heat_and_burgers_translation_paths_remain_exact() -> None:
    heat_training = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=50)
    heat_heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=51)
    burgers_training = generate_burgers_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=52)
    burgers_heldout = generate_burgers_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=53)

    heat_generator = fit_translation_generator(heat_training, HeatResidualEvaluator(), epsilon=1e-4)
    burgers_generator = fit_translation_generator(burgers_training, BurgersResidualEvaluator(), epsilon=1e-4)
    heat_report = verify_translation_generator(heat_heldout, heat_generator, HeatResidualEvaluator())
    burgers_report = verify_translation_generator(burgers_heldout, burgers_generator, BurgersResidualEvaluator())

    for generator in (heat_generator, burgers_generator):
        assert generator.parameterization == "polynomial_translation_affine"
        assert generator.coefficients.shape == (1, 4)
        assert generator.basis_spec["variables"] == ["t", "x", "u"]
        assert generator.basis_spec["component_names"] == ["xi"]
        assert generator.basis_spec["term_ordering"] == ["1", "t", "x", "u"]
        assert generator.basis_spec["layout"] == "component_major"

    assert heat_report.classification == "exact"
    assert burgers_report.classification == "exact"


def test_v0_4_release_gate_viz_smoke_returns_figures_with_noninteractive_backend() -> None:
    generator = _translation_generator(
        np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=float)
    )
    span_reference = _translation_generator(np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float))
    span_candidate = _translation_generator(np.array([[0.0, 1.0, 0.0, 0.0]], dtype=float))
    closure_generator = _algebraic_generator(
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float),
        basis_spec=_x_basis_spec(labels=["1", "x"], powers=[[0], [1]]),
    )
    verification_report = _verification_report()
    span_report = compare_generator_spans(span_reference, span_candidate)
    closure_report = diagnose_generator_family_closure(closure_generator)

    figures = [
        plot_generator_coefficients(generator),
        plot_generator_symbolic_summary(generator),
        plot_verification_curve(verification_report),
        plot_span_diagnostics(span_report),
        plot_closure_diagnostics(closure_report),
    ]

    assert matplotlib.get_backend().lower() == "agg"
    assert all(isinstance(figure, Figure) for figure in figures)
