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


def _wide_x_basis_spec(num_terms: int = 32) -> dict[str, object]:
    basis_terms: list[dict[str, object]] = []
    term_ordering: list[str] = []
    for power in range(num_terms):
        label = "1" if power == 0 else "x" if power == 1 else f"x^{power}"
        basis_terms.append({"label": label, "powers": [power]})
        term_ordering.append(label)

    return {
        "variables": ["x"],
        "component_names": ["xi"],
        "basis_terms": basis_terms,
        "component_ordering": ["xi"],
        "term_ordering": term_ordering,
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
    assert len(figure.axes[0].texts) == 1
    summary_text = figure.axes[0].texts[0].get_text()
    assert "X_1 = ∂x" in summary_text
    assert "X_2 = t∂x" in summary_text
    assert "monospace" in [family.lower() for family in figure.axes[0].texts[0].get_fontfamily()]


def test_plot_generator_symbolic_summary_scales_for_denser_families() -> None:
    dense_generator = _make_generator(
        np.array(
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 1.0],
                [1.0, 1.0, 0.0, 0.0],
                [1.0, 0.0, 1.0, 1.0],
            ],
            dtype=float,
        ),
        basis_spec=_translation_generator_basis_spec(),
        normalization="runtime_fixture",
        parameterization="polynomial_translation_affine",
    )

    figure = plot_generator_symbolic_summary(dense_generator)

    assert isinstance(figure, Figure)
    assert len(figure.axes[0].texts) == 1
    assert figure.axes[0].texts[0].get_fontsize() < 11.0
    assert figure.get_size_inches()[1] < 4.0


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
    assert len(figure.axes) == 2
    assert len(figure.axes[0].patches) == report["comparison_rank"]
    assert "degrees" in figure.axes[0].get_ylabel().lower()
    assert any("Projection residual" in text.get_text() for text in figure.axes[1].texts)


def test_plot_span_diagnostics_marks_zero_angle_bars_intentionally() -> None:
    basis_spec = _x_basis_spec()
    reference = _make_generator(
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float),
        basis_spec=basis_spec,
    )
    candidate = _make_generator(
        np.array([[1.0, 0.0], [1.0, 1.0]], dtype=float),
        basis_spec=basis_spec,
    )

    figure = plot_span_diagnostics(compare_generator_spans(reference, candidate))

    assert isinstance(figure, Figure)
    assert len(figure.axes[0].collections) == 1


def test_plot_closure_diagnostics_accepts_frozen_m4_report_shape() -> None:
    generator = _make_generator(
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float),
        basis_spec=_x_basis_spec(),
    )
    report = diagnose_generator_family_closure(generator)

    figure = plot_closure_diagnostics(report)

    assert isinstance(figure, Figure)
    assert len(figure.axes) == 4
    assert [axis.get_title() for axis in figure.axes[:3]] == ["Closure", "Antisymmetry", "Jacobi"]
    assert figure.axes[3].get_ylabel() == "Residual"
    assert figure.axes[0].images[0].get_clim() == (0.0, 1.0)
    assert figure.axes[1].images[0].get_clim() == (0.0, 1.0)


def test_plot_generator_coefficients_decimates_labels_for_wide_bases() -> None:
    basis_spec = _wide_x_basis_spec()
    generator = _make_generator(
        np.arange(len(basis_spec["term_ordering"]), dtype=float).reshape(1, -1),
        basis_spec=basis_spec,
    )

    figure = plot_generator_coefficients(generator)

    assert isinstance(figure, Figure)
    assert len(figure.axes) == 1
    assert len(figure.axes[0].patches) == 32
    assert len(figure.axes[0].collections) == 1
    visible_labels = [label.get_text() for label in figure.axes[0].get_yticklabels() if label.get_text()]
    expected_labels = [f"xi:{label}" for index, label in enumerate(basis_spec["term_ordering"]) if index % 2 == 0]
    assert visible_labels == expected_labels
    assert any("Showing every 2nd basis label" in text.get_text() for text in figure.axes[0].texts)


def test_plot_span_diagnostics_rejects_malformed_report() -> None:
    with pytest.raises(SchemaValidationError, match="missing required keys"):
        plot_span_diagnostics({})


def test_plot_closure_diagnostics_rejects_malformed_report() -> None:
    with pytest.raises(SchemaValidationError, match="missing required keys"):
        plot_closure_diagnostics({})
