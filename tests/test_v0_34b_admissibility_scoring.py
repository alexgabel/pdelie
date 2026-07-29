"""v0.34b admissibility scoring and background-treatment classification.

The classification vocabulary was frozen only after measurement, per the v0.34
process amendment. Across Heat, Burgers, and advection-diffusion at integer grid
shifts of 1-16 points, the fixed-background residual exceeds the co-transforming
residual by **77x to 15437x** (median 1049x); all 15 measurements cleared the 5x
separation bar, giving roughly 15x of headroom at the worst case.

Two properties make that more than a bare ratio, and both are pinned below:

* the co-transforming residual equals the *untranslated* baseline exactly at
  every shift -- translating field and background together is an exact symmetry
  of the discretized periodic problem;
* the fixed-background residual grows monotonically with displacement.

The frozen four ``method_scores`` names are unchanged: admissibility is a nested
diagnostic block, deliberately **not** a fifth score.
"""

from __future__ import annotations

import itertools
import json

import numpy as np
import pytest

from pdelie.contracts import GeneratorFamily, _translation_generator_basis_spec
from pdelie.data import (
    generate_advection_diffusion_1d_field_batch,
    generate_burgers_1d_field_batch,
    generate_heat_1d_field_batch,
)
from pdelie.data.heat_1d import DEFAULT_DOMAIN_LENGTH
from pdelie.errors import ScopeValidationError, ShapeValidationError
from pdelie.residuals import (
    AdvectionDiffusionResidualEvaluator,
    BurgersResidualEvaluator,
    HeatResidualEvaluator,
)
from pdelie.symmetry.admissibility import (
    BACKGROUND_TREATMENT_LABELS,
    MINIMUM_BACKGROUND_SEPARATION_RATIO,
    classify_background_treatment,
    score_against_reference,
)
from pdelie.symmetry.methods.polynomial_translation_svd import PolynomialTranslationSvdMethod

_NUM_POINTS = 64
_SEED = 0
_FROZEN_FOUR = {"span_distance", "residual_l2", "error_curve_max", "svd_condition_number"}


def _profile(base: float) -> np.ndarray:
    x = np.linspace(0.0, DEFAULT_DOMAIN_LENGTH, _NUM_POINTS, endpoint=False, dtype=float)
    return base * (1.0 + 0.5 * np.sin(2.0 * np.pi * x / DEFAULT_DOMAIN_LENGTH))


def _family(coefficients) -> GeneratorFamily:
    values = np.asarray(coefficients, dtype=float)
    values = values / np.linalg.norm(values)
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=values.reshape(1, -1),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )


_PURE_TRANSLATION = _family([1.0, 0.0, 0.0, 0.0])
_PURE_U = _family([0.0, 0.0, 0.0, 1.0])


def _heat_field(**kwargs):
    return generate_heat_1d_field_batch(
        batch_size=1, num_times=17, num_points=_NUM_POINTS, seed=_SEED, **kwargs
    )


# (label, generator, kwargs, base, evaluator factory)
_PDE_CASES = [
    (
        "heat_1d", generate_heat_1d_field_batch,
        {"batch_size": 1, "num_times": 17, "num_points": _NUM_POINTS, "seed": _SEED},
        0.1, lambda nu: HeatResidualEvaluator(diffusivity=nu),
    ),
    (
        "burgers_1d", generate_burgers_1d_field_batch,
        {"batch_size": 1, "num_times": 33, "num_points": _NUM_POINTS, "seed": _SEED},
        0.1, lambda nu: BurgersResidualEvaluator(diffusivity=nu),
    ),
    (
        "advection_diffusion_1d", generate_advection_diffusion_1d_field_batch,
        {"batch_size": 1, "num_times": 65, "num_points": _NUM_POINTS, "seed": _SEED},
        0.05, lambda nu: AdvectionDiffusionResidualEvaluator(advection_speed=0.75, diffusivity=nu),
    ),
]
_PDE_IDS = [case[0] for case in _PDE_CASES]


# --------------------------------------------------------------------------
# Frozen-four invariant
# --------------------------------------------------------------------------


def test_no_reference_leaves_the_block_none() -> None:
    result = PolynomialTranslationSvdMethod().fit(
        _heat_field(), residual_evaluator=HeatResidualEvaluator(diffusivity=0.1)
    )
    assert result.fit_diagnostics["variable_coefficient_admissibility"] is None
    assert set(result.method_scores) == _FROZEN_FOUR


def test_supplying_a_reference_does_not_add_a_fifth_score() -> None:
    """Admissibility is a diagnostic block, explicitly not a score name."""
    result = PolynomialTranslationSvdMethod().fit(
        _heat_field(),
        residual_evaluator=HeatResidualEvaluator(diffusivity=0.1),
        reference_generator_family=_PURE_TRANSLATION,
        reference_generator_family_id="pure_translation_x",
    )
    assert set(result.method_scores) == _FROZEN_FOUR
    assert result.fit_diagnostics["variable_coefficient_admissibility"] is not None


def test_symmetry_candidate_discriminators_are_unchanged() -> None:
    result = PolynomialTranslationSvdMethod().fit(
        _heat_field(),
        residual_evaluator=HeatResidualEvaluator(diffusivity=0.1),
        reference_generator_family=_PURE_TRANSLATION,
        reference_generator_family_id="pure_translation_x",
    )
    candidate = result.candidates[0]
    assert candidate.representation_type == "generator_family"
    assert candidate.mathematical_status == "candidate_only"


# --------------------------------------------------------------------------
# Reference scoring
# --------------------------------------------------------------------------


def test_matching_reference_scores_near_zero() -> None:
    result = PolynomialTranslationSvdMethod().fit(
        _heat_field(),
        residual_evaluator=HeatResidualEvaluator(diffusivity=0.1),
        reference_generator_family=_PURE_TRANSLATION,
        reference_generator_family_id="pure_translation_x",
    )
    block = result.fit_diagnostics["variable_coefficient_admissibility"]

    assert block["reference_generator_family_id"] == "pure_translation_x"
    assert block["relative_error_l2"] < 1e-3
    assert block["direction"] == "lower_is_better"
    assert block["diagnostic_only"] is True


def test_orthogonal_reference_saturates_at_root_two() -> None:
    """Both vectors are unit-normalized, so the error is bounded by sqrt(2).

    A wrong-basis reference should sit at that ceiling rather than producing an
    unbounded number that would make thresholds meaningless.
    """
    block = score_against_reference(
        _PURE_TRANSLATION, _PURE_U, reference_generator_family_id="pure_u"
    )
    assert block["relative_error_l2"] == pytest.approx(np.sqrt(2.0), rel=1e-9)


def test_reference_and_candidate_spans_are_both_reported() -> None:
    block = score_against_reference(
        _family([1.0, 0.05, 0.0, 0.0]),
        _PURE_TRANSLATION,
        reference_generator_family_id="pure_translation_x",
    )
    assert block["reference_span_distance"] == pytest.approx(0.0, abs=1e-12)
    assert block["candidate_span_distance"] > 0.0


def test_reference_score_is_sign_invariant() -> None:
    """Coefficient normalization fixes the leading sign, so a flipped reference
    must not read as maximally wrong."""
    flipped = GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[-1.0, 0.0, 0.0, 0.0]]),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )
    block = score_against_reference(
        _PURE_TRANSLATION, flipped, reference_generator_family_id="flipped"
    )
    assert block["relative_error_l2"] == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("bad_id", ["", "   ", None], ids=["empty", "blank", "none"])
def test_reference_requires_a_non_empty_identifier(bad_id) -> None:
    with pytest.raises(ScopeValidationError, match="non-empty string"):
        score_against_reference(
            _PURE_TRANSLATION, _PURE_TRANSLATION, reference_generator_family_id=bad_id
        )


def test_fit_requires_both_reference_arguments_or_neither() -> None:
    method = PolynomialTranslationSvdMethod()
    evaluator = HeatResidualEvaluator(diffusivity=0.1)

    with pytest.raises(ScopeValidationError, match="requires reference_generator_family_id"):
        method.fit(
            _heat_field(), residual_evaluator=evaluator,
            reference_generator_family=_PURE_TRANSLATION,
        )
    with pytest.raises(ScopeValidationError, match="without reference_generator_family"):
        method.fit(
            _heat_field(), residual_evaluator=evaluator,
            reference_generator_family_id="orphaned",
        )


def test_multi_row_generator_family_is_rejected() -> None:
    """The score compares a single generator direction, not a family of them.

    A multi-row family has no unambiguous single direction to compare, so it is
    refused rather than silently reduced to its first row.
    """
    multi = GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]]),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )
    with pytest.raises(ShapeValidationError, match="exactly one coefficient row"):
        score_against_reference(_PURE_TRANSLATION, multi, reference_generator_family_id="multi")
    with pytest.raises(ShapeValidationError, match="exactly one coefficient row"):
        score_against_reference(multi, _PURE_TRANSLATION, reference_generator_family_id="ref")


def test_admissibility_block_round_trips_through_strict_json() -> None:
    result = PolynomialTranslationSvdMethod().fit(
        _heat_field(),
        residual_evaluator=HeatResidualEvaluator(diffusivity=0.1),
        reference_generator_family=_PURE_TRANSLATION,
        reference_generator_family_id="pure_translation_x",
    )
    block = result.fit_diagnostics["variable_coefficient_admissibility"]
    assert json.loads(json.dumps(block, allow_nan=False)) == block


# --------------------------------------------------------------------------
# Background-treatment classification: the measured discriminator
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("label", "generator", "kwargs", "base", "make"), _PDE_CASES, ids=_PDE_IDS)
def test_co_transforming_background_is_classified_as_equivalence(
    label, generator, kwargs, base, make
) -> None:
    profile = _profile(base)
    field = generator(**kwargs, diffusivity_profile=profile)
    block = classify_background_treatment(
        field, coefficient_profile=profile, make_evaluator=make, shift_points=8
    )

    assert block["label"] == "co_transforming_background_equivalence"
    assert block["label"] in BACKGROUND_TREATMENT_LABELS
    assert block["separation_ratio"] >= MINIMUM_BACKGROUND_SEPARATION_RATIO


@pytest.mark.parametrize(("label", "generator", "kwargs", "base", "make"), _PDE_CASES, ids=_PDE_IDS)
def test_co_transforming_residual_equals_the_untranslated_baseline(
    label, generator, kwargs, base, make
) -> None:
    """The strongest evidence that this is an exact equivalence, not an approximate one.

    Translating field and background together on a periodic grid is an exact
    symmetry of the discretized problem, so the residual must be unchanged --
    not merely small.
    """
    profile = _profile(base)
    field = generator(**kwargs, diffusivity_profile=profile)
    block = classify_background_treatment(
        field, coefficient_profile=profile, make_evaluator=make, shift_points=8
    )
    assert block["co_transforming_residual_l2"] == pytest.approx(
        block["baseline_residual_l2"], rel=1e-9
    )


def test_fixed_background_residual_grows_monotonically_with_displacement() -> None:
    """The symmetry break scales with how far the field moved.

    A diagnostic that switched on at a threshold rather than degrading smoothly
    would be far harder to interpret at intermediate shifts.
    """
    profile = _profile(0.1)
    field = _heat_field(diffusivity_profile=profile)
    residuals = [
        classify_background_treatment(
            field, coefficient_profile=profile,
            make_evaluator=lambda nu: HeatResidualEvaluator(diffusivity=nu),
            shift_points=shift,
        )["fixed_background_residual_l2"]
        for shift in (1, 2, 4, 8, 16)
    ]
    assert all(later > earlier for earlier, later in itertools.pairwise(residuals)), residuals


def test_separation_exceeds_the_frozen_bar_by_a_wide_margin() -> None:
    """Pin the measured headroom that justified freezing the vocabulary.

    Worst measured case across three PDEs and five shifts was 77.45x against a
    5x bar. Asserting a floor well above the bar but well below the measured
    minimum keeps this meaningful without being brittle.
    """
    profile = _profile(0.1)
    field = _heat_field(diffusivity_profile=profile)
    block = classify_background_treatment(
        field, coefficient_profile=profile,
        make_evaluator=lambda nu: HeatResidualEvaluator(diffusivity=nu),
        shift_points=1,
    )
    assert block["separation_ratio"] >= 20.0


def test_classification_block_round_trips_through_strict_json() -> None:
    profile = _profile(0.1)
    field = _heat_field(diffusivity_profile=profile)
    block = classify_background_treatment(
        field, coefficient_profile=profile,
        make_evaluator=lambda nu: HeatResidualEvaluator(diffusivity=nu),
    )
    assert json.loads(json.dumps(block, allow_nan=False)) == block
    assert block["diagnostic_only"] is True


# --------------------------------------------------------------------------
# Classifier guards
# --------------------------------------------------------------------------


@pytest.mark.parametrize("shift", [0, _NUM_POINTS, _NUM_POINTS + 5],
                         ids=["zero", "full-grid", "beyond-grid"])
def test_degenerate_shifts_are_rejected(shift) -> None:
    profile = _profile(0.1)
    field = _heat_field(diffusivity_profile=profile)
    with pytest.raises(ScopeValidationError, match="nonzero shift"):
        classify_background_treatment(
            field, coefficient_profile=profile,
            make_evaluator=lambda nu: HeatResidualEvaluator(diffusivity=nu),
            shift_points=shift,
        )


def test_non_integer_shift_is_rejected() -> None:
    """np.roll is exact only for integer shifts; a float would silently truncate."""
    profile = _profile(0.1)
    field = _heat_field(diffusivity_profile=profile)
    with pytest.raises(ScopeValidationError, match="integer number of grid points"):
        classify_background_treatment(
            field, coefficient_profile=profile,
            make_evaluator=lambda nu: HeatResidualEvaluator(diffusivity=nu),
            shift_points=2.5,
        )


@pytest.mark.parametrize(
    ("bad", "error"),
    [
        (np.ones(_NUM_POINTS + 3), ShapeValidationError),
        (np.ones((2, _NUM_POINTS)), ShapeValidationError),
        (np.full(_NUM_POINTS, np.nan), ScopeValidationError),
    ],
    ids=["wrong-length", "two-dimensional", "non-finite"],
)
def test_malformed_coefficient_profile_is_rejected(bad, error) -> None:
    field = _heat_field(diffusivity_profile=_profile(0.1))
    with pytest.raises(error):
        classify_background_treatment(
            field, coefficient_profile=bad,
            make_evaluator=lambda nu: HeatResidualEvaluator(diffusivity=nu),
        )


def test_make_evaluator_must_return_a_residual_evaluator() -> None:
    profile = _profile(0.1)
    field = _heat_field(diffusivity_profile=profile)
    with pytest.raises(ScopeValidationError, match="ResidualEvaluator"):
        classify_background_treatment(
            field, coefficient_profile=profile, make_evaluator=lambda nu: "not an evaluator"
        )


def test_vocabulary_is_exactly_the_frozen_three() -> None:
    assert BACKGROUND_TREATMENT_LABELS == {
        "fixed_background_same_target_symmetry_failed",
        "co_transforming_background_equivalence",
        "inconclusive_background_separation",
    }
