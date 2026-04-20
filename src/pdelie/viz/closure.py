from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

import numpy as np

from pdelie.errors import SchemaValidationError
from pdelie.viz._matplotlib import require_pyplot

if TYPE_CHECKING:
    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

_ZERO_RESIDUAL_TOL = 1e-12
_NEAR_ZERO_RESIDUAL_TOL = 1e-6
_ANNOTATION_CELL_LIMIT = 25


def _format_residual(value: float) -> str:
    absolute = abs(float(value))
    if absolute <= _ZERO_RESIDUAL_TOL:
        return "0"
    if absolute < 1e-3:
        return f"{float(value):.1e}"
    return f"{float(value):.3f}"


def _matrix_status(matrix: np.ndarray) -> str:
    max_value = float(np.max(matrix)) if matrix.size else 0.0
    if max_value <= _ZERO_RESIDUAL_TOL:
        return "All entries = 0"
    if max_value <= _NEAR_ZERO_RESIDUAL_TOL:
        return f"Near-zero residuals (max {_format_residual(max_value)})"
    return f"Nonzero residuals present (max {_format_residual(max_value)})"


def _annotate_residual_matrix(axis: Axes, matrix: np.ndarray) -> None:
    if matrix.size > _ANNOTATION_CELL_LIMIT:
        return
    threshold = 0.5
    for row_index in range(matrix.shape[0]):
        for col_index in range(matrix.shape[1]):
            value = float(matrix[row_index, col_index])
            axis.text(
                col_index,
                row_index,
                _format_residual(value),
                ha="center",
                va="center",
                fontsize=8,
                color="white" if value >= threshold else "black",
            )


def _require_structure_constants(report: Mapping[str, object]) -> Mapping[str, object]:
    structure_constants = _require_mapping(report["structure_constants"], "structure_constants")
    if "tensor" not in structure_constants:
        raise SchemaValidationError("Closure diagnostics field 'structure_constants' must include 'tensor'.")
    return structure_constants


def _jacobi_summary_lines(
    *,
    jacobi_summary: float,
    triple_residuals: np.ndarray,
    jacobi_mode: str,
    structure_tensor: np.ndarray,
) -> list[str]:
    lines = [f"Mode: {jacobi_mode}", f"Summary: {_format_residual(jacobi_summary)}"]
    if triple_residuals.size == 0:
        lines.append("No triple residuals reported")
    else:
        max_triple = float(np.max(triple_residuals))
        near_zero_count = int(np.count_nonzero(triple_residuals <= _NEAR_ZERO_RESIDUAL_TOL))
        total_count = int(triple_residuals.size)
        lines.extend(
            [
                f"Max triple residual: {_format_residual(max_triple)}",
                f"Triple tensor shape: {tuple(int(dim) for dim in triple_residuals.shape)}",
                f"Near-zero triples: {near_zero_count}/{total_count}",
            ]
        )
    nonzero_structure_constants = int(np.count_nonzero(np.abs(structure_tensor) > _ZERO_RESIDUAL_TOL))
    max_structure_constant = float(np.max(np.abs(structure_tensor))) if structure_tensor.size else 0.0
    lines.extend(
        [
            f"Nonzero structure constants: {nonzero_structure_constants}",
            f"Max |c_ijk|: {_format_residual(max_structure_constant)}",
        ]
    )
    return lines


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{name} must be a mapping.")
    return value


def _validate_closure_report(
    report: Mapping[str, object],
) -> tuple[Mapping[str, object], Mapping[str, object], Mapping[str, object], Mapping[str, object]]:
    required_keys = {
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
    missing = sorted(required_keys.difference(report))
    if missing:
        raise SchemaValidationError(f"Closure diagnostics report is missing required keys: {missing}.")

    closure = _require_mapping(report["closure"], "closure")
    antisymmetry = _require_mapping(report["antisymmetry"], "antisymmetry")
    jacobi = _require_mapping(report["jacobi"], "jacobi")

    for section_name, section in (("closure", closure), ("antisymmetry", antisymmetry)):
        if "summary" not in section or "pairwise_residuals" not in section:
            raise SchemaValidationError(
                f"Closure diagnostics section '{section_name}' must include 'summary' and 'pairwise_residuals'."
            )
    if "summary" not in jacobi or "triple_residuals" not in jacobi or "mode" not in jacobi:
        raise SchemaValidationError(
            "Closure diagnostics section 'jacobi' must include 'summary', 'triple_residuals', and 'mode'."
        )
    if not isinstance(jacobi["mode"], str) or not jacobi["mode"]:
        raise SchemaValidationError("Closure diagnostics section 'jacobi' field 'mode' must be a non-empty string.")

    structure_constants = _require_structure_constants(report)
    return closure, antisymmetry, jacobi, structure_constants


def plot_closure_diagnostics(report: Mapping[str, object]) -> Figure:
    """Plot summary heatmaps for an existing closure-diagnostics report."""

    plt = require_pyplot()
    if not isinstance(report, Mapping):
        raise SchemaValidationError("Closure diagnostics input must be a mapping.")

    closure, antisymmetry, jacobi, structure_constants = _validate_closure_report(report)
    closure_matrix = np.asarray(closure["pairwise_residuals"], dtype=float)
    antisymmetry_matrix = np.asarray(antisymmetry["pairwise_residuals"], dtype=float)
    jacobi_summary = float(jacobi["summary"])
    triple_residuals = np.asarray(jacobi["triple_residuals"], dtype=float)
    jacobi_mode = str(jacobi["mode"])
    structure_tensor = np.asarray(structure_constants["tensor"], dtype=float)

    if closure_matrix.ndim != 2 or antisymmetry_matrix.ndim != 2:
        raise SchemaValidationError("Closure and antisymmetry pairwise_residuals must be two-dimensional.")
    if closure_matrix.shape != antisymmetry_matrix.shape:
        raise SchemaValidationError("Closure and antisymmetry pairwise_residuals must have matching shapes.")

    figure, axes = plt.subplots(1, 3, figsize=(12.0, 3.8), constrained_layout=True)

    closure_axis, antisymmetry_axis, jacobi_axis = axes
    closure_image = closure_axis.imshow(closure_matrix, cmap="viridis", aspect="auto", vmin=0.0, vmax=1.0)
    closure_axis.set_title("Closure")
    closure_axis.set_xlabel("j")
    closure_axis.set_ylabel("i")
    closure_axis.set_xticks(np.arange(closure_matrix.shape[1], dtype=float))
    closure_axis.set_yticks(np.arange(closure_matrix.shape[0], dtype=float))
    closure_axis.text(0.02, 0.98, _matrix_status(closure_matrix), transform=closure_axis.transAxes, va="top", fontsize=9)
    _annotate_residual_matrix(closure_axis, closure_matrix)

    antisymmetry_axis.imshow(antisymmetry_matrix, cmap="viridis", aspect="auto", vmin=0.0, vmax=1.0)
    antisymmetry_axis.set_title("Antisymmetry")
    antisymmetry_axis.set_xlabel("j")
    antisymmetry_axis.set_ylabel("i")
    antisymmetry_axis.set_xticks(np.arange(antisymmetry_matrix.shape[1], dtype=float))
    antisymmetry_axis.set_yticks(np.arange(antisymmetry_matrix.shape[0], dtype=float))
    antisymmetry_axis.text(
        0.02,
        0.98,
        _matrix_status(antisymmetry_matrix),
        transform=antisymmetry_axis.transAxes,
        va="top",
        fontsize=9,
    )
    _annotate_residual_matrix(antisymmetry_axis, antisymmetry_matrix)

    shared_colorbar = figure.colorbar(closure_image, ax=[closure_axis, antisymmetry_axis], fraction=0.046, pad=0.04)
    shared_colorbar.set_label("Residual")
    shared_colorbar.set_ticks([0.0, 0.25, 0.5, 0.75, 1.0])

    jacobi_axis.set_axis_off()
    jacobi_axis.set_title("Jacobi")
    jacobi_axis.text(
        0.02,
        0.92,
        "\n".join(
            _jacobi_summary_lines(
                jacobi_summary=jacobi_summary,
                triple_residuals=triple_residuals,
                jacobi_mode=jacobi_mode,
                structure_tensor=structure_tensor,
            )
        ),
        transform=jacobi_axis.transAxes,
        va="top",
        fontsize=9.5,
        linespacing=1.35,
    )

    return figure


__all__ = ["plot_closure_diagnostics"]
