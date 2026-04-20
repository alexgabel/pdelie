from __future__ import annotations

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.figure import Figure

from pdelie import GeneratorFamily, SchemaValidationError, VerificationReport
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.symmetry import compare_generator_spans, diagnose_generator_family_closure
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


def _make_verification_report() -> VerificationReport:
    return VerificationReport(
        norm="relative_l2",
        epsilon_values=np.logspace(-4, -1, 7),
        error_curve=np.logspace(-7, -4, 7),
        classification="exact",
        diagnostics={},
    )


def test_plot_generator_coefficients_returns_figure_with_deterministic_bar_count() -> None:
    generator = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        parameterization="polynomial_translation_affine",
    )

    figure = plot_generator_coefficients(generator)

    assert isinstance(figure, Figure)
    assert len(figure.axes) == 2
    assert sum(len(axis.patches) for axis in figure.axes) == 8


def test_plot_generator_symbolic_summary_contains_rendered_generator_strings() -> None:
    generator = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        parameterization="polynomial_translation_affine",
    )

    figure = plot_generator_symbolic_summary(generator)

    assert isinstance(figure, Figure)
    texts = [text.get_text() for text in figure.axes[0].texts]
    assert "X_1 = ∂x" in texts
    assert "X_2 = t∂x" in texts


def test_plot_verification_curve_returns_log_scaled_figure() -> None:
    report = _make_verification_report()

    figure = plot_verification_curve(report)

    assert isinstance(figure, Figure)
    assert len(figure.axes) == 1
    assert figure.axes[0].get_xscale() == "log"
    assert "exact" in figure.axes[0].get_title().lower()


def test_plot_span_diagnostics_accepts_frozen_m3_report_shape() -> None:
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

    figure = plot_span_diagnostics(report)

    assert isinstance(figure, Figure)
    assert len(figure.axes) == 1
    assert len(figure.axes[0].patches) == report["comparison_rank"]
    assert any("Projection residual" in text.get_text() for text in figure.axes[0].texts)


def test_plot_closure_diagnostics_accepts_frozen_m4_report_shape() -> None:
    generator = _make_generator(
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float),
        basis_spec=_x_basis_spec(),
    )
    report = diagnose_generator_family_closure(generator)

    figure = plot_closure_diagnostics(report)

    assert isinstance(figure, Figure)
    assert len(figure.axes) == 3
    assert [axis.get_title() for axis in figure.axes] == ["Closure", "Antisymmetry", "Jacobi"]


def test_plot_span_diagnostics_rejects_malformed_report() -> None:
    with pytest.raises(SchemaValidationError, match="missing required keys"):
        plot_span_diagnostics({})


def test_plot_closure_diagnostics_rejects_malformed_report() -> None:
    with pytest.raises(SchemaValidationError, match="missing required keys"):
        plot_closure_diagnostics({})
