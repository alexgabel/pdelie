from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from pdelie.errors import SchemaValidationError

_ZERO_ANGLE_TOL = 1e-12


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

    principal_angles_degrees = np.degrees(np.asarray(report["principal_angles_radians"], dtype=float))
    positions = np.arange(1, principal_angles_degrees.size + 1, dtype=float)
    residual_summary = float(report["projection_residual"]["summary"])  # type: ignore[index]
    reference_rank = int(report["reference_rank"])
    candidate_rank = int(report["candidate_rank"])
    comparison_rank = int(report["comparison_rank"])
    max_angle_degrees = float(np.max(principal_angles_degrees)) if principal_angles_degrees.size else 0.0

    figure, (bars_axis, summary_axis) = plt.subplots(
        1,
        2,
        figsize=(8.5, 4.0),
        gridspec_kw={"width_ratios": [3.0, 1.5]},
    )
    if principal_angles_degrees.size > 0:
        bars_axis.bar(positions, principal_angles_degrees, color="tab:orange")
        bars_axis.set_xticks(positions)
        zero_mask = np.isclose(principal_angles_degrees, 0.0, atol=_ZERO_ANGLE_TOL)
        if np.any(zero_mask):
            bars_axis.scatter(
                positions[zero_mask],
                np.zeros(int(np.sum(zero_mask)), dtype=float),
                marker="o",
                s=26.0,
                facecolors="white",
                edgecolors="tab:orange",
                linewidths=1.2,
                zorder=3,
            )
    bars_axis.set_xlabel("Principal angle index")
    bars_axis.set_ylabel("Angle (degrees)")
    bars_axis.set_title("Span Diagnostics")

    summary_axis.set_axis_off()
    summary_axis.set_title("Summary")
    summary_axis.text(
        0.02,
        0.95,
        "\n".join(
            [
                f"Projection residual: {residual_summary:.3g}",
                f"Comparison rank: {comparison_rank}",
                f"Reference rank: {reference_rank}",
                f"Candidate rank: {candidate_rank}",
                f"Max angle (deg): {max_angle_degrees:.2f}",
            ]
        ),
        transform=summary_axis.transAxes,
        ha="left",
        va="top",
    )

    figure.tight_layout()
    return figure


__all__ = ["plot_span_diagnostics"]
