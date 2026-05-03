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
