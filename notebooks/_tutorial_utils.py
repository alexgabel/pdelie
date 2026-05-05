"""Small notebook-only display helpers for the PDELie tutorial notebooks.

These helpers are intentionally outside ``src/pdelie``. They make tutorial
cells shorter, but they are not runtime package APIs or stability contracts.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import numpy as np


def json_safe(value: Any) -> Any:
    """Convert common NumPy containers into JSON-compatible Python values."""
    if isinstance(value, np.ndarray):
        return [json_safe(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def pretty_json(value: Any, *, max_chars: int = 3000) -> str:
    """Return compact pretty JSON for notebook display."""
    text = json.dumps(json_safe(value), indent=2, sort_keys=True)
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}\n... <truncated {len(text) - max_chars} chars>"


def confidence_card(
    *,
    label: str,
    residual: Mapping[str, Any] | None = None,
    fit: Mapping[str, Any] | None = None,
    verification: Mapping[str, Any] | None = None,
    coverage: Mapping[str, Any] | None = None,
    consistency: Mapping[str, Any] | None = None,
    validation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Collect a compact display card from public runtime summaries.

    The package-level confidence report API is
    ``pdelie.reporting.summarize_generator_confidence``. This notebook helper
    remains display glue for concise tables.
    """
    card: dict[str, Any] = {"label": label}

    if residual is not None:
        card.update(
            residual_max_abs=residual.get("max_abs_residual"),
            residual_rms=residual.get("rms_residual"),
        )

    if fit is not None:
        singular_values = fit.get("singular_values")
        card.update(
            evidence_label=fit.get("evidence_label"),
            fit_mode=fit.get("fit_mode"),
            reference_fallback_used=fit.get("reference_fallback_used"),
            condition_number=fit.get("condition_number"),
            selected_span_distance=fit.get("selected_span_distance"),
            svd_span_distance=fit.get("svd_span_distance"),
            singular_value_count=len(singular_values) if isinstance(singular_values, list) else None,
        )

    if verification is not None:
        card.update(
            verification_classification=verification.get("classification"),
            first_epsilon=verification.get("first_epsilon"),
            first_error=verification.get("first_error"),
            max_error=verification.get("max_error"),
        )

    if coverage is not None:
        card.update(
            coverage_fraction=coverage.get("coverage_fraction"),
            min_coverage_count=coverage.get("min_coverage_count"),
            max_coverage_count=coverage.get("max_coverage_count"),
        )

    if consistency is not None:
        reports = consistency.get("shift_reports", [])
        if isinstance(reports, list) and reports:
            residual_pass = [
                bool(report.get("residual_stability_passed", True))
                for report in reports
                if isinstance(report, Mapping)
            ]
            card.update(
                consistency_shift_count=len(reports),
                consistency_all_passed=all(residual_pass),
            )

    if validation is not None:
        card.update(
            candidate_kind=validation.get("candidate_kind"),
            validation_conclusion=validation.get("conclusion"),
        )

    return json_safe(card)


def print_cards(cards: list[Mapping[str, Any]]) -> None:
    """Print one JSON array of confidence cards."""
    print(pretty_json(cards, max_chars=6000))


def field_snapshot(field: Any) -> dict[str, Any]:
    """Return a compact tutorial snapshot of a FieldBatch-like object."""
    return json_safe(
        {
            "dims": list(field.dims),
            "shape": list(field.values.shape),
            "time_points": len(field.coords["time"]),
            "x_points": len(field.coords["x"]),
            "var_names": list(field.var_names),
            "metadata_parameter_tags": field.metadata.get("parameter_tags", {}),
            "mask_present": field.mask is not None,
            "preprocess_steps": len(field.preprocess_log),
        }
    )


def plot_field_heatmap(field: Any, *, batch_index: int = 0, title: str = "field") -> None:
    """Visualize a scalar 1D FieldBatch trajectory as a time/x heatmap."""
    import matplotlib.pyplot as plt

    values = np.asarray(field.values[batch_index, :, :, 0], dtype=float)
    x = np.asarray(field.coords["x"], dtype=float)
    time = np.asarray(field.coords["time"], dtype=float)

    fig, ax = plt.subplots(figsize=(7, 3))
    image = ax.imshow(
        values,
        aspect="auto",
        origin="lower",
        extent=[float(x[0]), float(x[-1]), float(time[0]), float(time[-1])],
    )
    ax.set_title(title)
    ax.set_xlabel("x")
    ax.set_ylabel("time")
    fig.colorbar(image, ax=ax, label=field.var_names[0])
    plt.show()


def plot_verification_curve(summary: Mapping[str, Any], *, title: str = "verification") -> None:
    """Plot verification error as a function of transform epsilon."""
    import matplotlib.pyplot as plt

    eps = np.asarray(summary["epsilon_values"], dtype=float)
    err = np.asarray(summary["error_curve"], dtype=float)

    fig, ax = plt.subplots(figsize=(5, 3))
    ax.loglog(eps, err, marker="o")
    ax.set_title(title)
    ax.set_xlabel("epsilon")
    ax.set_ylabel(summary.get("norm", "error"))
    ax.grid(True, which="both", alpha=0.3)
    plt.show()


def plot_singular_values(fit_summary: Mapping[str, Any], *, title: str = "fit spectrum") -> None:
    """Plot singular values from a generator-fit diagnostic summary."""
    import matplotlib.pyplot as plt

    values = np.asarray(fit_summary.get("singular_values", []), dtype=float)
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.semilogy(np.arange(values.size), values, marker="o")
    ax.set_title(title)
    ax.set_xlabel("index")
    ax.set_ylabel("singular value")
    ax.grid(True, which="both", alpha=0.3)
    plt.show()


def plot_coverage_counts(coverage: Mapping[str, Any], *, title: str = "coverage") -> None:
    """Plot periodic grid-point coverage counts."""
    import matplotlib.pyplot as plt

    counts = np.asarray(coverage["coverage_counts"], dtype=float)
    x = np.asarray(coverage.get("grid_points", np.arange(counts.size)), dtype=float)

    fig, ax = plt.subplots(figsize=(7, 2.8))
    ax.step(x, counts, where="mid")
    ax.set_title(title)
    ax.set_xlabel("x")
    ax.set_ylabel("coverage count")
    ax.grid(True, alpha=0.3)
    plt.show()


def plot_component_statuses(report: Mapping[str, Any], *, title: str = "component statuses") -> None:
    """Plot reporting component statuses as a compact horizontal status strip."""
    import matplotlib.pyplot as plt

    statuses = report.get("component_statuses", {})
    if not isinstance(statuses, Mapping) or not statuses:
        print("No component_statuses found.")
        return

    palette = {
        "passed": "#2a9d8f",
        "warning": "#e9c46a",
        "failed": "#e76f51",
        "not_configured": "#8d99ae",
        "unavailable": "#adb5bd",
    }
    names = list(statuses)
    values = [str(statuses[name].get("status", "unavailable")) for name in names]
    colors = [palette.get(value, "#adb5bd") for value in values]

    fig, ax = plt.subplots(figsize=(max(6, 0.75 * len(names)), 2.4))
    ax.bar(np.arange(len(names)), np.ones(len(names)), color=colors)
    ax.set_xticks(np.arange(len(names)), names, rotation=35, ha="right")
    ax.set_yticks([])
    ax.set_ylim(0, 1.25)
    ax.set_title(title)
    for index, value in enumerate(values):
        ax.text(index, 0.5, value.replace("_", "\n"), ha="center", va="center", fontsize=8)
    plt.tight_layout()
    plt.show()


def plot_named_metrics(metrics: Mapping[str, float], *, title: str = "metrics", log: bool = False) -> None:
    """Plot a small named metric dictionary as a bar chart."""
    import matplotlib.pyplot as plt

    names = list(metrics)
    values = np.asarray([float(metrics[name]) for name in names], dtype=float)
    fig, ax = plt.subplots(figsize=(max(5, 0.85 * len(names)), 3))
    ax.bar(np.arange(len(names)), values, color="#457b9d")
    ax.set_xticks(np.arange(len(names)), names, rotation=25, ha="right")
    if log:
        ax.set_yscale("log")
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.3)
    plt.tight_layout()
    plt.show()


def plot_label_strip(labels: Mapping[str, str], *, title: str = "labels") -> None:
    """Plot named categorical labels as a quick visual dashboard."""
    import matplotlib.pyplot as plt

    palette = {
        "ready": "#2a9d8f",
        "strong": "#2a9d8f",
        "validated": "#2a9d8f",
        "supported_existing_slice": "#2a9d8f",
        "current_frozen_supported": "#2a9d8f",
        "multi_generator_diagnostics_feasible_fitting_deferred": "#2a9d8f",
        "needs_attention": "#e9c46a",
        "qualified": "#e9c46a",
        "partially_validated": "#e9c46a",
        "diagnostic_only": "#e9c46a",
        "current_no_go_reference_fallback": "#e76f51",
        "not_ready": "#e76f51",
        "failed": "#e76f51",
        "insufficient_evidence": "#8d99ae",
    }
    names = list(labels)
    values = [str(labels[name]) for name in names]
    colors = [palette.get(value, "#adb5bd") for value in values]

    fig, ax = plt.subplots(figsize=(max(6, 1.15 * len(names)), 2.6))
    ax.bar(np.arange(len(names)), np.ones(len(names)), color=colors)
    ax.set_xticks(np.arange(len(names)), names, rotation=25, ha="right")
    ax.set_yticks([])
    ax.set_ylim(0, 1.3)
    ax.set_title(title)
    for index, value in enumerate(values):
        ax.text(index, 0.52, value.replace("_", "\n"), ha="center", va="center", fontsize=8)
    plt.tight_layout()
    plt.show()
