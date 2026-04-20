from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pdelie.errors import SchemaValidationError


def _validate_span_report(report: Mapping[str, object]) -> None:
    required_keys = {
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
    missing = sorted(required_keys.difference(report))
    if missing:
        raise SchemaValidationError(f"Span diagnostics report is missing required keys: {missing}.")

    projection_residual = report["projection_residual"]
    if not isinstance(projection_residual, Mapping):
        raise SchemaValidationError("Span diagnostics report field 'projection_residual' must be a mapping.")
    if "summary" not in projection_residual:
        raise SchemaValidationError("Span diagnostics report field 'projection_residual' must include 'summary'.")


def plot_span_diagnostics(report: Mapping[str, object]) -> Figure:
    """Plot principal angles and projection-residual summary from an existing span report."""

    if not isinstance(report, Mapping):
        raise SchemaValidationError("Span diagnostics input must be a mapping.")
    _validate_span_report(report)

    principal_angles = np.asarray(report["principal_angles_radians"], dtype=float)
    positions = np.arange(1, principal_angles.size + 1, dtype=float)
    residual_summary = float(report["projection_residual"]["summary"])  # type: ignore[index]

    figure, axis = plt.subplots(figsize=(6.5, 4.0))
    if principal_angles.size > 0:
        axis.bar(positions, principal_angles, color="tab:orange")
        axis.set_xticks(positions)
    axis.set_xlabel("Principal angle index")
    axis.set_ylabel("Angle (radians)")
    axis.set_title("Span Diagnostics")
    axis.text(
        0.98,
        0.98,
        f"Projection residual: {residual_summary:.3g}",
        transform=axis.transAxes,
        ha="right",
        va="top",
    )

    figure.tight_layout()
    return figure


__all__ = ["plot_span_diagnostics"]
