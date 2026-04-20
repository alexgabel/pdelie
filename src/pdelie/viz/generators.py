from __future__ import annotations

from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pdelie.contracts import GeneratorFamily
from pdelie.symmetry import render_generator_family


def _flattened_basis_labels(generator: GeneratorFamily) -> list[str]:
    component_names = [str(name) for name in generator.basis_spec["component_ordering"]]
    term_names = [str(name) for name in generator.basis_spec["term_ordering"]]
    return [f"{component_name}:{term_name}" for component_name in component_names for term_name in term_names]


def _display_rows(coefficients: np.ndarray, *, normalize_for_display: bool) -> np.ndarray:
    rows = np.asarray(coefficients, dtype=float).copy()
    if not normalize_for_display:
        return rows

    for index, row in enumerate(rows):
        scale = float(np.max(np.abs(row))) if row.size else 0.0
        if scale > 0.0:
            rows[index] = row / scale
    return rows


def _subplot_titles(generator: GeneratorFamily) -> list[str]:
    if generator.generator_names is not None:
        return list(generator.generator_names)
    return [f"X_{index}" for index in range(1, generator.coefficients.shape[0] + 1)]


def plot_generator_coefficients(
    generator: GeneratorFamily,
    *,
    normalize_for_display: bool = False,
) -> Figure:
    """Plot stored generator coefficients as deterministic horizontal bar charts."""

    generator.validate()
    labels = _flattened_basis_labels(generator)
    rows = _display_rows(np.asarray(generator.coefficients, dtype=float), normalize_for_display=normalize_for_display)
    titles = _subplot_titles(generator)

    figure, axes = plt.subplots(
        nrows=rows.shape[0],
        ncols=1,
        squeeze=False,
        figsize=(8.0, max(2.5, 2.5 * rows.shape[0])),
    )
    y_positions = np.arange(len(labels), dtype=float)

    for row_index, axis in enumerate(axes[:, 0]):
        axis.barh(y_positions, rows[row_index], color="tab:blue")
        axis.axvline(0.0, color="black", linewidth=0.8)
        axis.set_yticks(y_positions)
        axis.set_yticklabels(labels)
        axis.set_title(titles[row_index])
        axis.set_xlabel("Display-normalized coefficient" if normalize_for_display else "Coefficient")
        axis.set_ylabel("Basis term")

    figure.tight_layout()
    return figure


def plot_generator_symbolic_summary(
    generator: GeneratorFamily,
    *,
    display_normalization: str = "anchor",
) -> Figure:
    """Render stored generators as symbolic text inside a simple figure."""

    generator.validate()
    lines: Sequence[str] = render_generator_family(generator, display_normalization=display_normalization)

    figure, axis = plt.subplots(figsize=(9.0, max(2.5, 0.9 * len(lines) + 1.0)))
    axis.set_axis_off()
    axis.set_title("Generator Summary")

    top = 0.92
    step = 0.75 / max(len(lines), 1)
    for index, line in enumerate(lines):
        axis.text(
            0.02,
            top - index * step,
            line,
            transform=axis.transAxes,
            fontsize=11,
            va="top",
            ha="left",
        )

    figure.tight_layout()
    return figure


__all__ = [
    "plot_generator_coefficients",
    "plot_generator_symbolic_summary",
]
