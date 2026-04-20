from __future__ import annotations

from collections.abc import Mapping

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pdelie.errors import SchemaValidationError


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{name} must be a mapping.")
    return value


def _validate_closure_report(report: Mapping[str, object]) -> tuple[Mapping[str, object], Mapping[str, object], Mapping[str, object]]:
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
    if "summary" not in jacobi or "triple_residuals" not in jacobi:
        raise SchemaValidationError("Closure diagnostics section 'jacobi' must include 'summary' and 'triple_residuals'.")

    return closure, antisymmetry, jacobi


def plot_closure_diagnostics(report: Mapping[str, object]) -> Figure:
    """Plot summary heatmaps for an existing closure-diagnostics report."""

    if not isinstance(report, Mapping):
        raise SchemaValidationError("Closure diagnostics input must be a mapping.")

    closure, antisymmetry, jacobi = _validate_closure_report(report)
    closure_matrix = np.asarray(closure["pairwise_residuals"], dtype=float)
    antisymmetry_matrix = np.asarray(antisymmetry["pairwise_residuals"], dtype=float)
    jacobi_summary = float(jacobi["summary"])
    triple_residuals = np.asarray(jacobi["triple_residuals"], dtype=float)

    if closure_matrix.ndim != 2 or antisymmetry_matrix.ndim != 2:
        raise SchemaValidationError("Closure and antisymmetry pairwise_residuals must be two-dimensional.")
    if closure_matrix.shape != antisymmetry_matrix.shape:
        raise SchemaValidationError("Closure and antisymmetry pairwise_residuals must have matching shapes.")

    figure, axes = plt.subplots(1, 3, figsize=(12.0, 3.8))

    closure_axis, antisymmetry_axis, jacobi_axis = axes
    closure_axis.imshow(closure_matrix, cmap="viridis", aspect="auto")
    closure_axis.set_title("Closure")
    closure_axis.set_xlabel("j")
    closure_axis.set_ylabel("i")

    antisymmetry_axis.imshow(antisymmetry_matrix, cmap="viridis", aspect="auto")
    antisymmetry_axis.set_title("Antisymmetry")
    antisymmetry_axis.set_xlabel("j")
    antisymmetry_axis.set_ylabel("i")

    jacobi_axis.set_axis_off()
    jacobi_axis.set_title("Jacobi")
    jacobi_axis.text(0.02, 0.82, f"Summary: {jacobi_summary:.3g}", transform=jacobi_axis.transAxes, va="top")
    if triple_residuals.size > 0:
        jacobi_axis.text(
            0.02,
            0.62,
            f"Max triple residual: {float(np.max(triple_residuals)):.3g}",
            transform=jacobi_axis.transAxes,
            va="top",
        )
        jacobi_axis.text(
            0.02,
            0.42,
            f"Triple tensor shape: {tuple(int(dim) for dim in triple_residuals.shape)}",
            transform=jacobi_axis.transAxes,
            va="top",
        )
    else:
        jacobi_axis.text(0.02, 0.62, "No triple residuals", transform=jacobi_axis.transAxes, va="top")

    figure.tight_layout()
    return figure


__all__ = ["plot_closure_diagnostics"]
