"""v0.33b overlap-crop finite-transform verification.

Three decisions here came from measurement rather than the planning draft:

**``domain_length`` is ``x[-1] - x[0] + dx`` (N*dx), not ``x[-1] - x[0]``.** Only
that convention makes ``overlap_fraction`` exactly equal ``retained_rows /
num_points``: a shift of ``k*dx`` retains ``N - k`` rows, so the fraction must be
``1 - k/N``. The span convention gives ``1 - k/(N-1)`` -- 0.5733 versus 0.5789 at
``k=32, N=76`` -- which would make the reported fraction disagree with the
reported row count. It is also the convention ``apply_pointwise_translation``
already uses for the periodic period.

**The comparison is overlap AND interior.** On nonperiodic data the residual near
a boundary is dominated by finite-difference stencil error, so an untrimmed
comparison lets stencil error drive the classification. Measured at the default
epsilon sweep the interior trim is in fact the *binding* constraint: the overlap
crop removes at most 3 rows while the trim removes 8, and the crop first binds
only above ``|shift| > boundary_trim_width * dx``, which is twice the largest
default epsilon. ``compared_row_count`` therefore reports what was actually
measured rather than the geometric overlap.

**Neither boundary-value-problem label is emitted.** A failed classification on
the overlap means the *interior* verification failed; the crop has removed
exactly the rows that would settle a boundary question. So a failure reports
``equation_symmetry_candidate`` (still just a candidate), not
``boundary_value_problem_not_preserved``.
"""

from __future__ import annotations

import itertools
import warnings

import numpy as np
import pytest

from pdelie import GeneratorFamily
from pdelie.contracts import FieldBatch, _translation_generator_basis_spec
from pdelie.data import (
    generate_burgers_1d_field_batch,
    generate_heat_1d_field_batch,
)
from pdelie.residuals import BurgersResidualEvaluator, HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator  # noqa: F401  (import order)
from pdelie.verification import verify_translation_generator
from pdelie.verification.finite_transform import (
    DISPATCH_PATH_OVERLAP_CROP,
    DISPATCH_PATH_PERIODIC,
    MINIMUM_OVERLAP_FRACTION,
    _apply_overlap_crop_translation,
    _domain_length,
    _overlap_row_indices,
)

_CLASSIFICATION_VOCABULARY = {"exact", "approximate", "failed"}


def _restrict_to_nonperiodic_window(
    field: FieldBatch, boundary_type: str, *, keep: float = 0.6
) -> FieldBatch:
    num_points = field.values.shape[2]
    width = int(num_points * keep)
    low = (num_points - width) // 2
    metadata = dict(field.metadata)
    metadata["boundary_conditions"] = {"x": boundary_type}
    return FieldBatch(
        values=field.values[:, :, low : low + width, :].copy(),
        dims=field.dims,
        coords={
            "time": field.coords["time"].copy(),
            "x": field.coords["x"][low : low + width].copy(),
        },
        var_names=list(field.var_names),
        metadata=metadata,
        preprocess_log=[],
    )


def _generator(coefficients) -> GeneratorFamily:
    values = np.asarray(coefficients, dtype=float)
    values = values / np.linalg.norm(values)
    if values[0] < 0:
        values = -values
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=values.reshape(1, -1),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )


_PURE_TRANSLATION = _generator([1.0, 0.0, 0.0, 0.0])
_WRONG_BASIS = _generator([0.0, 0.0, 0.0, 1.0])


def _heat_field(num_points: int = 128):
    return generate_heat_1d_field_batch(
        batch_size=4, num_times=17, num_points=num_points, seed=0
    )


def _nonperiodic_heat(boundary_type: str = "dirichlet"):
    return _restrict_to_nonperiodic_window(_heat_field(), boundary_type)


_NONPERIODIC_CASES = [
    ("dirichlet", _nonperiodic_heat("dirichlet"), lambda: HeatResidualEvaluator(diffusivity=0.1)),
    (
        "neumann",
        _restrict_to_nonperiodic_window(
            generate_burgers_1d_field_batch(batch_size=4, num_times=33, num_points=128, seed=0),
            "neumann",
        ),
        lambda: BurgersResidualEvaluator(diffusivity=0.1),
    ),
    ("open_unknown", _nonperiodic_heat("open_unknown"), lambda: HeatResidualEvaluator(diffusivity=0.1)),
]
_NONPERIODIC_IDS = [case[0] for case in _NONPERIODIC_CASES]


# --------------------------------------------------------------------------
# Geometry: the domain-length convention
# --------------------------------------------------------------------------


def test_domain_length_uses_the_period_convention() -> None:
    """``x[-1] - x[0] + dx``, i.e. N*dx -- not the (N-1)*dx span."""
    field = _nonperiodic_heat()
    x = field.coords["x"]
    dx = float(x[1] - x[0])
    num_points = x.size

    assert _domain_length(field) == pytest.approx(num_points * dx)
    assert _domain_length(field) != pytest.approx(float(x[-1] - x[0]))


@pytest.mark.parametrize("k", [0, 4, 8, 16, 32])
def test_overlap_fraction_equals_retained_row_fraction(k: int) -> None:
    """The invariant that forces the domain-length convention.

    If these disagreed, the reported ``overlap_fraction`` and the reported
    ``overlap_row_count`` would describe different crops.
    """
    field = _nonperiodic_heat()
    x = field.coords["x"]
    dx = float(x[1] - x[0])
    num_points = x.size

    retained = _overlap_row_indices(field, k * dx).size
    fraction = max(0.0, 1.0 - abs(k * dx) / _domain_length(field))

    assert retained == num_points - k
    assert fraction == pytest.approx(retained / num_points)


@pytest.mark.parametrize("k", [4, 8, 16, 32])
def test_overlap_row_count_is_symmetric_in_shift_sign(k: int) -> None:
    """Row count is sign-symmetric even though the retained region flips.

    A positive shift keeps the right portion of the domain, a negative shift the
    left. The helper must handle both; the public API only produces non-negative
    shifts (see the sign-convention test below).
    """
    field = _nonperiodic_heat()
    dx = float(field.coords["x"][1] - field.coords["x"][0])

    positive = _overlap_row_indices(field, k * dx)
    negative = _overlap_row_indices(field, -k * dx)

    assert positive.size == negative.size == field.values.shape[2] - k
    # Same count, different region: the positive shift keeps higher indices.
    assert positive[0] > negative[0]
    assert positive[-1] > negative[-1]


def test_public_api_cannot_produce_a_negative_shift() -> None:
    """The frozen sign convention: shifts are non-negative through the API.

    ``normalize_translation_coefficients`` forces a non-negative leading
    component and ``epsilon_values`` must be strictly increasing, so
    ``shift = epsilon * coefficients[0]`` cannot be driven negative by a caller.
    The helper is nonetheless sign-safe.
    """
    assert _PURE_TRANSLATION.coefficients[0][0] > 0.0

    field = _nonperiodic_heat()
    dx = float(field.coords["x"][1] - field.coords["x"][0])
    with pytest.raises(Exception, match="strictly increasing"):
        verify_translation_generator(
            field,
            _PURE_TRANSLATION,
            HeatResidualEvaluator(diffusivity=0.1),
            epsilon_values=-np.array([1e-9, 4 * dx, 8 * dx, 16 * dx, 32 * dx]),
        )


def test_overlap_crop_translation_does_not_wrap() -> None:
    """The distinguishing property versus the periodic FFT path."""
    field = _nonperiodic_heat()
    dx = float(field.coords["x"][1] - field.coords["x"][0])
    translated, indices = _apply_overlap_crop_translation(field, 8 * dx)

    assert indices.size == field.values.shape[2] - 8
    assert translated.values.shape == field.values.shape
    # Rows outside the overlap are clamped to the edge value, not wrapped from
    # the far side of the domain.
    outside = np.setdiff1d(np.arange(field.values.shape[2]), indices)
    assert outside.size == 8
    edge_value = field.values[0, 0, 0, 0]
    assert translated.values[0, 0, outside, 0] == pytest.approx(edge_value)


# --------------------------------------------------------------------------
# Periodic branch: unchanged
# --------------------------------------------------------------------------


def test_periodic_branch_reports_full_overlap_and_no_trim() -> None:
    report = verify_translation_generator(
        _heat_field(num_points=64), _PURE_TRANSLATION, HeatResidualEvaluator(diffusivity=0.1)
    )
    diagnostics = report.diagnostics

    assert diagnostics["dispatch_path"] == DISPATCH_PATH_PERIODIC
    assert diagnostics["boundary_condition_x"] == "periodic"
    assert diagnostics["overlap_fraction"] == 1.0
    assert diagnostics["overlap_row_count"] == 64
    assert diagnostics["compared_row_count"] == 64
    assert diagnostics["interior_only_trim_width"] == 0
    assert report.classification in _CLASSIFICATION_VOCABULARY


def test_periodic_branch_still_classifies_a_valid_translation_as_exact() -> None:
    report = verify_translation_generator(
        _heat_field(num_points=64), _PURE_TRANSLATION, HeatResidualEvaluator(diffusivity=0.1)
    )
    assert report.classification == "exact"


def test_periodic_branch_emits_no_small_overlap_warning() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        verify_translation_generator(
            _heat_field(num_points=64), _PURE_TRANSLATION, HeatResidualEvaluator(diffusivity=0.1)
        )


# --------------------------------------------------------------------------
# Nonperiodic branch: dispatch and diagnostics
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("boundary_type", "field", "evaluator"), _NONPERIODIC_CASES, ids=_NONPERIODIC_IDS)
def test_nonperiodic_dispatch_reports_overlap_crop(boundary_type, field, evaluator) -> None:
    report = verify_translation_generator(field, _PURE_TRANSLATION, evaluator())
    diagnostics = report.diagnostics

    assert diagnostics["dispatch_path"] == DISPATCH_PATH_OVERLAP_CROP
    assert diagnostics["boundary_condition_x"] == boundary_type
    assert 0.0 <= diagnostics["overlap_fraction"] <= 1.0
    assert diagnostics["interior_only_trim_width"] > 0
    assert report.classification in _CLASSIFICATION_VOCABULARY


@pytest.mark.parametrize(("boundary_type", "field", "evaluator"), _NONPERIODIC_CASES, ids=_NONPERIODIC_IDS)
def test_compared_row_count_never_exceeds_either_constraint(
    boundary_type, field, evaluator
) -> None:
    """``compared_row_count`` reports what was measured, not the geometric overlap."""
    diagnostics = verify_translation_generator(field, _PURE_TRANSLATION, evaluator()).diagnostics

    assert diagnostics["compared_row_count"] <= diagnostics["overlap_row_count"]
    assert diagnostics["compared_row_count"] <= diagnostics["interior_only_row_count"]


def test_interior_trim_is_the_binding_constraint_at_default_epsilons() -> None:
    """Pin the measured fact that the crop is a no-op under default settings.

    The default sweep tops out at 2.04*dx while the trim removes 4 rows per side,
    so the overlap crop never binds. If a future change to ``DEFAULT_EPSILON_VALUES``
    or to the stencil width alters this, the docs claiming it should be revisited.
    """
    field = _nonperiodic_heat()
    diagnostics = verify_translation_generator(
        field, _PURE_TRANSLATION, HeatResidualEvaluator(diffusivity=0.1)
    ).diagnostics

    assert diagnostics["compared_row_count"] == diagnostics["interior_only_row_count"]
    assert diagnostics["overlap_row_count"] > diagnostics["interior_only_row_count"]


def test_overlap_fraction_is_strictly_decreasing_in_shift() -> None:
    field = _nonperiodic_heat()
    dx = float(field.coords["x"][1] - field.coords["x"][0])
    epsilon_values = np.array([1e-9, 4 * dx, 8 * dx, 16 * dx, 32 * dx])

    report = verify_translation_generator(
        field, _PURE_TRANSLATION, HeatResidualEvaluator(diffusivity=0.1),
        epsilon_values=epsilon_values,
    )
    fractions = report.diagnostics["overlap_fraction_by_epsilon"]

    assert len(fractions) == len(epsilon_values)
    assert fractions[0] == pytest.approx(1.0)
    assert all(later < earlier for earlier, later in itertools.pairwise(fractions))
    # The scalar summary is the worst case across the sweep.
    assert report.diagnostics["overlap_fraction"] == pytest.approx(min(fractions))


def test_reported_overlap_fraction_matches_reported_row_count() -> None:
    """The two diagnostics must describe the same crop."""
    field = _nonperiodic_heat()
    dx = float(field.coords["x"][1] - field.coords["x"][0])
    num_points = field.values.shape[2]

    report = verify_translation_generator(
        field, _PURE_TRANSLATION, HeatResidualEvaluator(diffusivity=0.1),
        epsilon_values=np.array([1e-9, 4 * dx, 8 * dx, 16 * dx, 32 * dx]),
    )
    diagnostics = report.diagnostics
    assert diagnostics["overlap_fraction"] == pytest.approx(
        diagnostics["overlap_row_count"] / num_points
    )


# --------------------------------------------------------------------------
# Classification and claims
# --------------------------------------------------------------------------


def test_nonperiodic_dirichlet_heat_with_a_valid_generator_is_not_failed() -> None:
    """Exit gate: a known-valid translation classifies exact or approximate."""
    report = verify_translation_generator(
        _nonperiodic_heat("dirichlet"), _PURE_TRANSLATION, HeatResidualEvaluator(diffusivity=0.1)
    )
    assert report.classification in {"exact", "approximate"}
    assert report.diagnostics["symmetry_claim"] == "interior_overlap_verified"


def test_nonperiodic_neumann_burgers_with_an_invalid_generator_fails() -> None:
    """Exit gate: a wrong-basis generator classifies failed.

    Note this fires via the pre-existing ``span_distance > span_tolerance``
    check, not via the overlap-crop error curve -- on the error curve alone a
    wrong-basis generator scores in the approximate band.
    """
    field = _restrict_to_nonperiodic_window(
        generate_burgers_1d_field_batch(batch_size=4, num_times=33, num_points=128, seed=0),
        "neumann",
    )
    report = verify_translation_generator(
        field, _WRONG_BASIS, BurgersResidualEvaluator(diffusivity=0.1)
    )

    assert report.classification == "failed"
    assert report.diagnostics["span_distance"] > report.diagnostics["span_tolerance"]


def test_open_unknown_boundary_reports_inconclusive_metadata() -> None:
    report = verify_translation_generator(
        _nonperiodic_heat("open_unknown"), _PURE_TRANSLATION, HeatResidualEvaluator(diffusivity=0.1)
    )
    assert report.diagnostics["symmetry_claim"] == "inconclusive_boundary_metadata"


def test_no_boundary_value_problem_label_is_ever_emitted() -> None:
    """Neither BVP label is reachable in v0.33b.

    ``boundary_value_problem_preserved`` was reserved-but-unemittable by the
    v0.33 scope amendment. ``boundary_value_problem_not_preserved`` is equally
    unreachable here: the overlap crop discards exactly the boundary rows, so a
    failed classification says nothing about the boundary -- it reports the
    candidate as still unverified instead.
    """
    emitted = set()
    for _boundary_type, field, evaluator in _NONPERIODIC_CASES:
        for generator in (_PURE_TRANSLATION, _WRONG_BASIS):
            report = verify_translation_generator(field, generator, evaluator())
            emitted.add(report.diagnostics["symmetry_claim"])

    assert "boundary_value_problem_preserved" not in emitted
    assert "boundary_value_problem_not_preserved" not in emitted


def test_failed_nonperiodic_verification_reports_candidate_not_boundary_violation() -> None:
    field = _restrict_to_nonperiodic_window(
        generate_burgers_1d_field_batch(batch_size=4, num_times=33, num_points=128, seed=0),
        "neumann",
    )
    report = verify_translation_generator(
        field, _WRONG_BASIS, BurgersResidualEvaluator(diffusivity=0.1)
    )
    assert report.classification == "failed"
    assert report.diagnostics["symmetry_claim"] == "equation_symmetry_candidate"


@pytest.mark.parametrize(("boundary_type", "field", "evaluator"), _NONPERIODIC_CASES, ids=_NONPERIODIC_IDS)
def test_classification_vocabulary_is_unchanged(boundary_type, field, evaluator) -> None:
    for generator in (_PURE_TRANSLATION, _WRONG_BASIS):
        report = verify_translation_generator(field, generator, evaluator())
        assert report.classification in _CLASSIFICATION_VOCABULARY


# --------------------------------------------------------------------------
# Small-overlap warning
# --------------------------------------------------------------------------


def test_small_overlap_emits_a_warning_and_still_classifies() -> None:
    field = _nonperiodic_heat()
    dx = float(field.coords["x"][1] - field.coords["x"][0])
    epsilon_values = np.array([1e-9, 10 * dx, 25 * dx, 40 * dx, 50 * dx])

    with pytest.warns(UserWarning, match="overlap fraction"):
        report = verify_translation_generator(
            field, _PURE_TRANSLATION, HeatResidualEvaluator(diffusivity=0.1),
            epsilon_values=epsilon_values,
        )

    assert report.diagnostics["overlap_fraction"] < MINIMUM_OVERLAP_FRACTION
    assert report.classification in _CLASSIFICATION_VOCABULARY


def test_comfortable_overlap_emits_no_warning() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        report = verify_translation_generator(
            _nonperiodic_heat(), _PURE_TRANSLATION, HeatResidualEvaluator(diffusivity=0.1)
        )
    assert report.diagnostics["overlap_fraction"] >= MINIMUM_OVERLAP_FRACTION


def test_verification_report_round_trips_through_strict_json() -> None:
    import json

    report = verify_translation_generator(
        _nonperiodic_heat(), _PURE_TRANSLATION, HeatResidualEvaluator(diffusivity=0.1)
    )
    payload = report.to_dict()
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload
