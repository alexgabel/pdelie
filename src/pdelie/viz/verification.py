from __future__ import annotations

from typing import TYPE_CHECKING

from pdelie.contracts import VerificationReport
from pdelie.viz._matplotlib import require_pyplot

if TYPE_CHECKING:
    from matplotlib.figure import Figure


def plot_verification_curve(report: VerificationReport) -> Figure:
    """Plot the held-out verification curve for an existing VerificationReport."""

    plt = require_pyplot()
    report.validate()

    figure, axis = plt.subplots(figsize=(6.5, 4.0))
    axis.plot(report.epsilon_values, report.error_curve, marker="o", color="tab:blue")
    axis.set_xscale("log")
    axis.set_xlabel("epsilon")
    axis.set_ylabel(report.norm)
    axis.set_title(f"Verification Curve ({report.classification})")
    axis.grid(True, alpha=0.3)

    figure.tight_layout()
    return figure


__all__ = ["plot_verification_curve"]
