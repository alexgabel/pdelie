"""v0.37b: fit an operator relating two residuals, advisorily and only advisorily.

Given ``R`` and ``R'``, this estimates the best scalar ``c`` with ``R' ~ c*R``,
reports how well that fits, and **never decides anything**.

Why the output is inert
=======================

A fit will always produce a number. Least squares returns a coefficient whether
or not the two residuals are related at all, and an :math:`r^2` close to 1 means
"a line through these points is a good line", not "a symmetry holds". The
failure mode this module is built against is the sentence *"the fit told us it
was a symmetry"*.

So :class:`FittedOperatorDiagnostic` carries no status field, no boolean verdict
and no threshold. It reports the coefficient, the fit quality, and the residual
of the fit itself. Whether a relation holds is decided analytically in
:mod:`pdelie.actions.commutation_report`, before this is called and without
reference to it, and two adversarial tests assert that an excellent fit does not
move a ``violated`` verdict.

The asymmetry that makes this safe
==================================

For ``scalar_multiplier``, ``affine`` and ``linear_combination_of_derivatives``,
a relation *was* declared, so a fit is a **check** -- it can agree or disagree
with something. For ``diagnostic_fitted``, nothing was declared, so a fit is
**exploration**: there is nothing for it to agree with, which is why R-A13
restricts that family's observed status to ``no_relation_declared``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from pdelie.errors import ScopeValidationError, ShapeValidationError

__all__ = ["FittedOperatorDiagnostic", "fit_diagnostic_operator"]


@dataclass(frozen=True)
class FittedOperatorDiagnostic:
    """The result of a fit. Deliberately carries no verdict.

    There is no ``status``, no ``holds``, and no threshold. Adding one would
    make it possible for a fit to contradict an analytical decision, which is
    the thing this type exists to prevent.
    """

    fitted_family: str
    fitted_multiplier: float | None
    fit_r_squared: float | None
    fit_residual_l2: float | None
    sample_count: int
    degenerate_reason: str | None = None

    @property
    def is_advisory(self) -> bool:
        """Always True. Present so the property can be asserted, not consulted."""
        return True

    def as_dict(self) -> dict[str, Any]:
        return {
            "fitted_family": self.fitted_family,
            "fitted_multiplier": self.fitted_multiplier,
            "fit_r_squared": self.fit_r_squared,
            "fit_residual_l2": self.fit_residual_l2,
            "sample_count": self.sample_count,
            "degenerate_reason": self.degenerate_reason,
            "advisory_only": True,
        }


def fit_diagnostic_operator(
    original: np.ndarray, transformed: np.ndarray
) -> FittedOperatorDiagnostic:
    """Least-squares ``c`` in ``transformed ~ c * original``. Advisory.

    Degenerate cases return ``None`` values with a named reason rather than a
    fabricated coefficient. ``None`` is not ``0.0``: a fit that could not be
    performed and a fit that returned zero are different facts.
    """
    left = np.asarray(original, dtype=float).ravel()
    right = np.asarray(transformed, dtype=float).ravel()
    if left.shape != right.shape:
        raise ShapeValidationError(
            f"original and transformed have {left.shape} and {right.shape}; a fit "
            f"between differently-shaped residuals is not meaningful."
        )
    if left.size == 0:
        raise ScopeValidationError("cannot fit an operator on an empty residual.")
    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        return FittedOperatorDiagnostic(
            fitted_family="scalar_multiplier",
            fitted_multiplier=None,
            fit_r_squared=None,
            fit_residual_l2=None,
            sample_count=int(left.size),
            degenerate_reason="non_finite_input",
        )

    denominator = float(left @ left)
    if denominator == 0.0:
        return FittedOperatorDiagnostic(
            fitted_family="scalar_multiplier",
            fitted_multiplier=None,
            fit_r_squared=None,
            fit_residual_l2=None,
            sample_count=int(left.size),
            degenerate_reason="original_residual_is_identically_zero",
        )

    multiplier = float(left @ right) / denominator
    fit_residual = right - multiplier * left
    fit_residual_l2 = float(np.sqrt(float(fit_residual @ fit_residual)))

    centred = right - right.mean()
    total = float(centred @ centred)
    r_squared = (
        None
        if total == 0.0
        else float(1.0 - float(fit_residual @ fit_residual) / total)
    )

    return FittedOperatorDiagnostic(
        fitted_family="scalar_multiplier",
        fitted_multiplier=multiplier,
        fit_r_squared=r_squared,
        fit_residual_l2=fit_residual_l2,
        sample_count=int(left.size),
        degenerate_reason=None if total != 0.0 else "transformed_residual_is_constant",
    )
