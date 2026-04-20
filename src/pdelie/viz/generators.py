from __future__ import annotations

import math
from typing import TYPE_CHECKING, Sequence

import numpy as np

from pdelie.contracts import GeneratorFamily
from pdelie.symmetry import render_generator_family
from pdelie.viz._matplotlib import require_pyplot

if TYPE_CHECKING:
    from matplotlib.figure import Figure

_ZERO_DISPLAY_TOL = 1e-12


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


def _coefficient_tick_step(num_labels: int) -> int:
    return max(1, math.ceil(num_labels / 24))


def _ordinal(value: int) -> str:
    if 10 <= value % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(value % 10, "th")
    return f"{value}{suffix}"


def _coefficient_tick_fontsize(num_labels: int) -> float:
    return max(7.0, 10.0 - 0.06 * max(num_labels - 12, 0))


def _coefficient_row_height(num_labels: int) -> float:
    return min(5.5, max(2.5, 1.7 + 0.09 * num_labels))


def _symbolic_summary_fontsize(lines: Sequence[str]) -> float:
    max_line_length = max((len(line) for line in lines), default=0)
    line_count = len(lines)
    size = 11.0 - 0.22 * max(line_count - 4, 0) - 0.03 * max(max_line_length - 36, 0)
    return max(8.0, min(11.0, size))


def _symbolic_summary_figure_size(lines: Sequence[str]) -> tuple[float, float]:
    max_line_length = max((len(line) for line in lines), default=0)
    line_count = max(len(lines), 1)
    width = min(14.0, max(8.0, 7.5 + 0.045 * max_line_length))
    height = min(7.0, max(2.2, 1.15 + 0.42 * line_count))
    return width, height


def plot_generator_coefficients(
    generator: GeneratorFamily,
    *,
    normalize_for_display: bool = False,
) -> Figure:
    """Plot stored generator coefficients as deterministic horizontal bar charts."""

    plt = require_pyplot()
    generator.validate()
    labels = _flattened_basis_labels(generator)
    rows = _display_rows(np.asarray(generator.coefficients, dtype=float), normalize_for_display=normalize_for_display)
    titles = _subplot_titles(generator)
    num_labels = len(labels)
    tick_step = _coefficient_tick_step(num_labels)
    tick_fontsize = _coefficient_tick_fontsize(num_labels)
    displayed_labels = [label if index % tick_step == 0 else "" for index, label in enumerate(labels)]

    figure, axes = plt.subplots(
        nrows=rows.shape[0],
        ncols=1,
        squeeze=False,
        figsize=(8.0, _coefficient_row_height(num_labels) * rows.shape[0]),
    )
    y_positions = np.arange(len(labels), dtype=float)

    for row_index, axis in enumerate(axes[:, 0]):
        axis.barh(y_positions, rows[row_index], color="tab:blue")
        axis.axvline(0.0, color="black", linewidth=0.8)
        zero_mask = np.isclose(rows[row_index], 0.0, atol=_ZERO_DISPLAY_TOL)
        if np.any(zero_mask):
            axis.scatter(
                np.zeros(int(np.sum(zero_mask)), dtype=float),
                y_positions[zero_mask],
                marker="o",
                s=20.0,
                facecolors="white",
                edgecolors="tab:blue",
                linewidths=1.0,
                zorder=3,
            )
        axis.set_yticks(y_positions)
        axis.set_yticklabels(displayed_labels)
        axis.tick_params(axis="y", labelsize=tick_fontsize)
        axis.set_title(titles[row_index])
        axis.set_xlabel("Display-normalized coefficient" if normalize_for_display else "Coefficient")
        axis.set_ylabel("Basis term")
        if tick_step > 1:
            axis.text(
                0.99,
                0.02,
                f"Showing every {_ordinal(tick_step)} basis label",
                transform=axis.transAxes,
                ha="right",
                va="bottom",
                fontsize=8,
            )

    figure.tight_layout()
    return figure


def plot_generator_symbolic_summary(
    generator: GeneratorFamily,
    *,
    display_normalization: str = "anchor",
) -> Figure:
    """Render stored generators as symbolic text inside a simple figure."""

    plt = require_pyplot()
    generator.validate()
    lines: Sequence[str] = render_generator_family(generator, display_normalization=display_normalization)
    figure, axis = plt.subplots(figsize=_symbolic_summary_figure_size(lines))
    axis.set_axis_off()
    axis.set_title("Generator Summary")
    axis.text(
        0.02,
        0.90,
        "\n".join(lines),
        transform=axis.transAxes,
        fontsize=_symbolic_summary_fontsize(lines),
        fontfamily="monospace",
        linespacing=1.2,
        va="top",
        ha="left",
    )

    figure.subplots_adjust(top=0.86, bottom=0.06, left=0.04, right=0.98)
    return figure


__all__ = [
    "plot_generator_coefficients",
    "plot_generator_symbolic_summary",
]
