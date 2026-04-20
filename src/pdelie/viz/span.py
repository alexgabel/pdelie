from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

import numpy as np

from pdelie.errors import SchemaValidationError
from pdelie.viz._matplotlib import require_pyplot

if TYPE_CHECKING:
    from matplotlib.figure import Figure

_ZERO_ANGLE_TOL = 1e-12
_ANGLE_LABEL_MAX_COUNT = 10


def _format_float(value: float) -> str:
    return f"{float(value):.3g}"


def _angle_label_fontsize(count: int) -> float:
    return max(7.0, 9.0 - 0.15 * max(count - 4, 0))


def _require_float(value: object, name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"Span diagnostics report field '{name}' must be numeric.") from exc


def _summary_lines(
    *,
    principal_angles_degrees: np.ndarray,
    residual_summary: float,
    reference_to_candidate: float | None,
    candidate_to_reference: float | None,
    comparison_rank: int,
    reference_rank: int,
    candidate_rank: int,
    conditioning: Mapping[str, object] | None,
) -> list[str]:
    if principal_angles_degrees.size == 0:
        min_angle = median_angle = max_angle = 0.0
        zero_count = 0
    else:
        min_angle = float(np.min(principal_angles_degrees))
        median_angle = float(np.median(principal_angles_degrees))
        max_angle = float(np.max(principal_angles_degrees))
        zero_count = int(np.count_nonzero(np.isclose(principal_angles_degrees, 0.0, atol=_ZERO_ANGLE_TOL)))

    lines = [
        f"Projection residual: {_format_float(residual_summary)}",
    ]
    if reference_to_candidate is not None and candidate_to_reference is not None:
        lines.extend(
            [
                f"Ref -> Cand: {_format_float(reference_to_candidate)}",
                f"Cand -> Ref: {_format_float(candidate_to_reference)}",
            ]
        )
    lines.extend(
        [
            f"Ranks: {reference_rank} ref / {candidate_rank} cand / {comparison_rank} cmp",
            f"Angles (deg): min {min_angle:.2f}, median {median_angle:.2f}, max {max_angle:.2f}",
            f"Zero angles: {zero_count}",
        ]
    )
    if conditioning is not None:
        ambient_metric = conditioning.get("ambient_metric")
        reference_span = conditioning.get("reference_span")
        candidate_span = conditioning.get("candidate_span")
        lines.append(
            "Conditioning: "
            f"{_format_float(float(ambient_metric))} ambient, "
            f"{_format_float(float(reference_span))} ref, "
            f"{_format_float(float(candidate_span))} cand"
        )
    if 0 < principal_angles_degrees.size <= _ANGLE_LABEL_MAX_COUNT:
        angle_list = ", ".join(f"{angle:.2f}" for angle in principal_angles_degrees)
        lines.append(f"Angle list: [{angle_list}]")
    return lines


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

    conditioning = report["conditioning"]
    if not isinstance(conditioning, Mapping):
        raise SchemaValidationError("Span diagnostics report field 'conditioning' must be a mapping.")
    required_conditioning_keys = ("ambient_metric", "reference_span", "candidate_span")
    missing_conditioning = [key for key in required_conditioning_keys if key not in conditioning]
    if missing_conditioning:
        raise SchemaValidationError(
            "Span diagnostics report field 'conditioning' is missing required keys: "
            f"{missing_conditioning}."
        )
    for key in required_conditioning_keys:
        _require_float(conditioning[key], f"conditioning.{key}")


def plot_span_diagnostics(report: Mapping[str, object]) -> Figure:
    """Plot principal angles and projection-residual summary from an existing span report."""

    plt = require_pyplot()
    if not isinstance(report, Mapping):
        raise SchemaValidationError("Span diagnostics input must be a mapping.")
    _validate_span_report(report)

    principal_angles_degrees = np.degrees(np.asarray(report["principal_angles_radians"], dtype=float))
    positions = np.arange(1, principal_angles_degrees.size + 1, dtype=float)
    residual_summary = float(report["projection_residual"]["summary"])  # type: ignore[index]
    reference_to_candidate = report["projection_residual"].get("reference_to_candidate")  # type: ignore[index]
    candidate_to_reference = report["projection_residual"].get("candidate_to_reference")  # type: ignore[index]
    reference_rank = int(report["reference_rank"])
    candidate_rank = int(report["candidate_rank"])
    comparison_rank = int(report["comparison_rank"])
    conditioning = report["conditioning"] if isinstance(report["conditioning"], Mapping) else None

    figure, (bars_axis, summary_axis) = plt.subplots(
        2,
        1,
        figsize=(max(7.5, min(12.0, 6.5 + 0.45 * max(comparison_rank - 1, 0))), 5.4),
        gridspec_kw={"height_ratios": [3.4, 1.5]},
    )
    if principal_angles_degrees.size > 0:
        bars_axis.bar(positions, principal_angles_degrees, color="tab:orange", edgecolor="tab:orange", width=0.72)
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
        label_fontsize = _angle_label_fontsize(principal_angles_degrees.size)
        for position, angle in zip(positions, principal_angles_degrees):
            y_value = max(float(angle), 0.0) + (2.0 if angle > _ZERO_ANGLE_TOL else 1.5)
            bars_axis.text(
                float(position),
                y_value,
                f"{float(angle):.1f}",
                ha="center",
                va="bottom",
                fontsize=label_fontsize,
            )
    bars_axis.set_xlabel("Principal angle index")
    bars_axis.set_ylabel("Angle (degrees)")
    bars_axis.set_title("Span Diagnostics")
    bars_axis.set_ylim(0.0, 95.0)
    bars_axis.set_yticks([0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0])
    bars_axis.grid(axis="y", linestyle="--", linewidth=0.6, alpha=0.5)
    bars_axis.set_axisbelow(True)

    summary_axis.set_axis_off()
    summary_axis.set_title("Summary")
    summary_axis.text(
        0.02,
        0.98,
        "\n".join(
            _summary_lines(
                principal_angles_degrees=principal_angles_degrees,
                residual_summary=residual_summary,
                reference_to_candidate=(
                    float(reference_to_candidate) if reference_to_candidate is not None else None
                ),
                candidate_to_reference=(
                    float(candidate_to_reference) if candidate_to_reference is not None else None
                ),
                comparison_rank=comparison_rank,
                reference_rank=reference_rank,
                candidate_rank=candidate_rank,
                conditioning=conditioning,
            )
        ),
        transform=summary_axis.transAxes,
        ha="left",
        va="top",
        fontsize=9,
    )

    figure.tight_layout()
    return figure


__all__ = ["plot_span_diagnostics"]
