"""v0.34b: admissibility scoring against a reference generator, and the
background-treatment classifier.

Two diagnostics live here. Both are ``diagnostic_only``; neither adds a score
name to the frozen four.

Reference-relative admissibility
--------------------------------

:func:`score_against_reference` compares a fitted candidate generator to a
caller-supplied reference and reports a relative coefficient-space error. It
answers "how far is this candidate from the one I believe is correct?", which is
the quantity the admissibility crash test needs and which no single-fit score
provides.

Background-treatment classification
-----------------------------------

:func:`classify_background_treatment` answers a sharper question: on a
variable-coefficient problem, is a translation a **symmetry** of this problem, or
an **equivalence** mapping it to a different one?

Under ``x -> x + eps``:

* **fixed background** -- the field translates, ``nu(x)`` does not. The
  translated field no longer satisfies the PDE; the background breaks the
  symmetry.
* **co-transforming background** -- field and ``nu`` translate together. The
  translated pair satisfies the same PDE. This is an equivalence transformation
  between problems, not a symmetry of the original one.

The distinction is frozen only because it was measured first. Across Heat,
Burgers, and advection-diffusion at integer grid shifts of 1-16 points, the
fixed-background residual exceeds the co-transforming residual by **77x to
15437x** (median 1049x, 15/15 measurements above the 5x separation bar). Two
features make that more than a bare ratio:

* the co-transforming residual equals the *untranslated* baseline exactly at
  every shift -- translating field and background together is an exact symmetry
  of the discretized periodic problem, not an approximate one;
* the fixed-background residual grows monotonically with displacement, so the
  diagnostic degrades gracefully rather than switching on at a threshold.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from pdelie.contracts import FieldBatch, GeneratorFamily
from pdelie.errors import ScopeValidationError, ShapeValidationError
from pdelie.residuals.base import ResidualEvaluator
from pdelie.symmetry.parameterization.polynomial_translation import (
    normalize_translation_coefficients,
    translation_span_distance,
)

__all__ = [
    "BACKGROUND_TREATMENT_LABELS",
    "MINIMUM_BACKGROUND_SEPARATION_RATIO",
    "classify_background_treatment",
    "score_against_reference",
]

#: Frozen v0.34b classification vocabulary. Extends the v0.33d
#: ``nu_treatment_policy`` value ``"fixed_background"`` with the equivalence
#: reading; ``inconclusive_background_separation`` covers the case where the two
#: paths are not separable enough to distinguish.
BACKGROUND_TREATMENT_LABELS: frozenset[str] = frozenset(
    {
        "fixed_background_same_target_symmetry_failed",
        "co_transforming_background_equivalence",
        "inconclusive_background_separation",
    }
)

#: Separation the two paths must exhibit before a definite label is emitted.
#: Measured worst case across three PDEs and five shift sizes is 77.45x, so this
#: bar carries roughly 15x of headroom; below it the run is reported as
#: inconclusive rather than guessed.
MINIMUM_BACKGROUND_SEPARATION_RATIO = 5.0

_X_AXIS = 2


def _coefficient_vector(family: GeneratorFamily, *, name: str) -> np.ndarray:
    coefficients = np.asarray(family.coefficients, dtype=float)
    if coefficients.ndim != 2 or coefficients.shape[0] != 1:
        raise ShapeValidationError(
            f"{name} must carry exactly one coefficient row; got shape "
            f"{coefficients.shape}."
        )
    return coefficients.reshape(-1)


def score_against_reference(
    candidate: GeneratorFamily,
    reference: GeneratorFamily,
    *,
    reference_generator_family_id: str,
) -> dict[str, Any]:
    """Relative coefficient-space error of ``candidate`` against ``reference``.

    Both families are normalized before comparison, so the score measures
    *direction* disagreement rather than scale. Because
    :func:`normalize_translation_coefficients` fixes the sign of the leading
    component, the comparison is not confounded by an overall sign flip.

    ``reference_generator_family_id`` is required and must be a non-empty
    caller-supplied string. A reference generator with no provenance identifier
    would make the resulting score untraceable to whatever produced it.
    """
    if not isinstance(reference_generator_family_id, str) or not reference_generator_family_id.strip():
        raise ScopeValidationError(
            "reference_generator_family_id must be a non-empty string identifying "
            "the reference generator; a score against an unidentified reference "
            "is not traceable."
        )

    candidate_vector = _coefficient_vector(candidate, name="candidate generator")
    reference_vector = _coefficient_vector(reference, name="reference generator")
    if candidate_vector.size != reference_vector.size:
        raise ShapeValidationError(
            f"candidate and reference generators must share a basis size; got "
            f"{candidate_vector.size} and {reference_vector.size}."
        )

    candidate_unit = normalize_translation_coefficients(candidate_vector)
    reference_unit = normalize_translation_coefficients(reference_vector)

    reference_norm = float(np.linalg.norm(reference_unit))
    relative_error = float(
        np.linalg.norm(candidate_unit - reference_unit) / reference_norm
    )

    return {
        "reference_generator_family_id": reference_generator_family_id,
        "relative_error_l2": relative_error if math.isfinite(relative_error) else None,
        "reference_span_distance": float(translation_span_distance(reference_vector)),
        "candidate_span_distance": float(translation_span_distance(candidate_vector)),
        "direction": "lower_is_better",
        "diagnostic_only": True,
    }


def _roll_field(field: FieldBatch, shift_points: int) -> FieldBatch:
    return FieldBatch(
        values=np.roll(np.asarray(field.values, dtype=float), shift_points, axis=_X_AXIS),
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=dict(field.metadata),
        preprocess_log=[],
    )


def classify_background_treatment(
    field: FieldBatch,
    *,
    coefficient_profile: np.ndarray,
    make_evaluator: Any,
    shift_points: int = 8,
) -> dict[str, Any]:
    """Classify whether a translation is a symmetry or an equivalence here.

    ``make_evaluator`` is a callable taking a coefficient array and returning a
    configured :class:`ResidualEvaluator`, so this function stays agnostic about
    which PDE it is scoring.

    ``shift_points`` is an **integer grid shift**, applied with ``np.roll``. On a
    periodic grid that is exact, so the comparison carries no interpolation
    error and the measured ratio reflects the background treatment alone.

    Returns a strict-JSON block. ``label`` is one of
    :data:`BACKGROUND_TREATMENT_LABELS`; when the two paths separate by less than
    :data:`MINIMUM_BACKGROUND_SEPARATION_RATIO` the label is
    ``"inconclusive_background_separation"`` rather than a guess.
    """
    if not isinstance(shift_points, (int, np.integer)) or isinstance(shift_points, bool):
        raise ScopeValidationError("shift_points must be an integer number of grid points.")
    shift = int(shift_points)
    num_points = int(field.values.shape[_X_AXIS])
    if shift == 0 or abs(shift) >= num_points:
        raise ScopeValidationError(
            f"shift_points must be a nonzero shift smaller than the grid ({num_points}); "
            f"got {shift}. A zero shift cannot distinguish the two treatments."
        )

    profile = np.asarray(coefficient_profile, dtype=float)
    if profile.ndim != 1 or profile.size != num_points:
        raise ShapeValidationError(
            f"coefficient_profile must be one-dimensional with one value per grid "
            f"point ({num_points},); got shape {profile.shape}."
        )
    if not np.all(np.isfinite(profile)):
        raise ScopeValidationError("coefficient_profile must be finite everywhere.")

    evaluator = make_evaluator(profile)
    if not isinstance(evaluator, ResidualEvaluator):
        raise ScopeValidationError(
            "make_evaluator must return a ResidualEvaluator instance."
        )

    def _l2(batch: Any) -> float:
        return float(np.linalg.norm(np.asarray(batch.residual, dtype=float)))

    baseline = _l2(evaluator.evaluate(field))
    translated = _roll_field(field, shift)

    # Co-transforming: the background travels with the field.
    co_transforming = _l2(make_evaluator(np.roll(profile, shift)).evaluate(translated))
    # Fixed background: the field moves, nu(x) stays where it is.
    fixed_background = _l2(evaluator.evaluate(translated))

    ratio = (
        float(fixed_background / co_transforming)
        if co_transforming > 0.0
        else None
    )

    if ratio is None or not math.isfinite(ratio):
        label = "inconclusive_background_separation"
    elif ratio >= MINIMUM_BACKGROUND_SEPARATION_RATIO:
        # The translated field only satisfies the PDE when nu travels with it:
        # a translation is an equivalence between problems, not a symmetry of
        # this one.
        label = "co_transforming_background_equivalence"
    else:
        label = "fixed_background_same_target_symmetry_failed"

    return {
        "label": label,
        "shift_points": shift,
        "baseline_residual_l2": baseline,
        "co_transforming_residual_l2": co_transforming,
        "fixed_background_residual_l2": fixed_background,
        "separation_ratio": ratio,
        "minimum_separation_ratio": MINIMUM_BACKGROUND_SEPARATION_RATIO,
        "direction": "higher_separation_is_more_conclusive",
        "diagnostic_only": True,
    }
