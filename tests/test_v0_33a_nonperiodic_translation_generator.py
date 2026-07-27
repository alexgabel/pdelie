"""v0.33a nonperiodic ``fit_translation_generator`` + ``polynomial_translation_svd``.

Two frozen decisions in this sub-milestone came from measurement, not from the
planning draft, and both are pinned here so a regression is loud:

**The interior shave is ``boundary_trim_width``, not one row.** The draft froze a
1-row shave. Measured across all four supported PDEs, a shave of 1 or 2 leaves
``span_distance`` near its ``sqrt(2)`` ceiling (1.13-1.40) because the residual
evaluator already trims 4 rows and translation corrupts the edge further --
contaminated rows then dominate the SVD. At shave = ``boundary_trim_width`` (4)
Heat collapses from 1.13 to 4.3e-3. The shave is read from the residual
diagnostics rather than hardcoded so it tracks the FD stencil.

**The reference fallback is suppressed off the periodic branch.** It drives the
emitted ``span_distance`` to exactly 0.0 regardless of the true drift. Measured
at N=128 it fired on 3 of 4 PDEs, reporting a *perfect* translation generator
where the honest SVD values were 0.24-0.64.
"""

from __future__ import annotations

import itertools
import warnings

import numpy as np
import pytest

from pdelie.contracts import FieldBatch
from pdelie.data import (
    generate_advection_diffusion_1d_field_batch,
    generate_burgers_1d_field_batch,
    generate_heat_1d_field_batch,
    generate_reaction_diffusion_1d_field_batch,
)
from pdelie.residuals import (
    AdvectionDiffusionResidualEvaluator,
    BurgersResidualEvaluator,
    HeatResidualEvaluator,
    ReactionDiffusionResidualEvaluator,
)
from pdelie.symmetry.fitting.translation_baseline import (
    MINIMUM_INTERIOR_ROW_COUNT,
    fit_translation_generator,
)
from pdelie.symmetry.methods.polynomial_translation_svd import PolynomialTranslationSvdMethod

_FROZEN_FOUR_SCORE_NAMES = {
    "span_distance",
    "residual_l2",
    "error_curve_max",
    "svd_condition_number",
}


def _restrict_to_nonperiodic_window(
    field: FieldBatch, boundary_type: str, *, keep: float = 0.6
) -> FieldBatch:
    """Restrict a periodic solution to an interior window and relabel the BC.

    The result is a genuine solution of the same PDE on the sub-domain, which is
    exactly the situation of a caller holding nonperiodic data. Manufacturing it
    this way keeps the physics honest -- the field really does solve the
    equation there -- so a poor fit is attributable to the dispatch, not to
    feeding the fitter a non-solution.
    """
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


# (boundary_type, label, generator, kwargs, evaluator factory)
_NONPERIODIC_CASES = [
    (
        "dirichlet", "heat_1d", generate_heat_1d_field_batch,
        {"batch_size": 1, "num_times": 17, "num_points": 128, "seed": 0},
        lambda: HeatResidualEvaluator(diffusivity=0.1),
    ),
    (
        "neumann", "burgers_1d", generate_burgers_1d_field_batch,
        {"batch_size": 1, "num_times": 33, "num_points": 128, "seed": 0},
        lambda: BurgersResidualEvaluator(diffusivity=0.1),
    ),
    (
        "open_unknown", "reaction_diffusion_1d", generate_reaction_diffusion_1d_field_batch,
        {"batch_size": 1, "num_times": 33, "num_points": 128, "seed": 0},
        lambda: ReactionDiffusionResidualEvaluator(),
    ),
    (
        "open_unknown", "advection_diffusion_1d", generate_advection_diffusion_1d_field_batch,
        {"batch_size": 1, "num_times": 65, "num_points": 128, "seed": 0},
        lambda: AdvectionDiffusionResidualEvaluator(advection_speed=0.75, diffusivity=0.05),
    ),
]
_NONPERIODIC_IDS = [f"{bc}-{label}" for bc, label, *_ in _NONPERIODIC_CASES]

_PERIODIC_CASES = [
    (
        "heat_1d", generate_heat_1d_field_batch,
        {"batch_size": 1, "num_times": 17, "num_points": 64, "seed": 0},
        lambda: HeatResidualEvaluator(diffusivity=0.1),
    ),
    (
        "burgers_1d", generate_burgers_1d_field_batch,
        {"batch_size": 1, "num_times": 33, "num_points": 64, "seed": 0},
        lambda: BurgersResidualEvaluator(diffusivity=0.1),
    ),
    (
        "reaction_diffusion_1d", generate_reaction_diffusion_1d_field_batch,
        {"batch_size": 1, "num_times": 33, "num_points": 64, "seed": 0},
        lambda: ReactionDiffusionResidualEvaluator(),
    ),
]
_PERIODIC_IDS = [case[0] for case in _PERIODIC_CASES]


# --------------------------------------------------------------------------
# Periodic branch: unchanged
# --------------------------------------------------------------------------


@pytest.mark.parametrize(("label", "generator", "kwargs", "evaluator"), _PERIODIC_CASES, ids=_PERIODIC_IDS)
def test_periodic_branch_takes_no_interior_shave(label, generator, kwargs, evaluator) -> None:
    """Exit gate: interior_only_row_count equals the full row count on periodic."""
    field = generator(**kwargs)
    diagnostics = fit_translation_generator(field, evaluator()).diagnostics

    assert diagnostics["boundary_condition_x"] == "periodic"
    assert diagnostics["boundary_condition_dispatch_reason"] == "is_x_periodic_true"
    assert diagnostics["interior_only_reduction_applied"] is False
    assert diagnostics["interior_only_trim_width"] == 0
    assert diagnostics["interior_only_row_count"] == kwargs["num_points"]


@pytest.mark.parametrize(("label", "generator", "kwargs", "evaluator"), _PERIODIC_CASES, ids=_PERIODIC_IDS)
def test_periodic_branch_keeps_the_reference_fallback(label, generator, kwargs, evaluator) -> None:
    """Fallback suppression is nonperiodic-only; the periodic path is untouched."""
    field = generator(**kwargs)
    diagnostics = fit_translation_generator(field, evaluator()).diagnostics
    assert diagnostics["fallback_reason"] != "reference_fallback_suppressed_on_nonperiodic_branch"


@pytest.mark.parametrize(("label", "generator", "kwargs", "evaluator"), _PERIODIC_CASES, ids=_PERIODIC_IDS)
def test_periodic_method_scores_are_preserved(label, generator, kwargs, evaluator) -> None:
    """Exit gate: periodic method_scores unchanged, and the frozen four hold.

    Absolute pinning of the underlying numerics lives in the v0.33e golden gate;
    this asserts the score surface and that the values are finite and stable
    across repeat evaluation.
    """
    method = PolynomialTranslationSvdMethod()
    field = generator(**kwargs)
    first = method.fit(field, residual_evaluator=evaluator()).method_scores
    second = method.fit(field, residual_evaluator=evaluator()).method_scores

    assert set(first) == _FROZEN_FOUR_SCORE_NAMES
    for name in _FROZEN_FOUR_SCORE_NAMES:
        if first[name] is None:
            assert second[name] is None
        else:
            assert first[name] == pytest.approx(second[name], rel=1e-8)


# --------------------------------------------------------------------------
# Nonperiodic branch: dispatch on all four boundary types
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("boundary_type", "label", "generator", "kwargs", "evaluator"),
    _NONPERIODIC_CASES,
    ids=_NONPERIODIC_IDS,
)
def test_nonperiodic_dispatch_reports_boundary_and_shave(
    boundary_type, label, generator, kwargs, evaluator
) -> None:
    field = _restrict_to_nonperiodic_window(generator(**kwargs), boundary_type)
    diagnostics = fit_translation_generator(field, evaluator()).diagnostics

    assert diagnostics["boundary_condition_x"] == boundary_type
    assert diagnostics["boundary_condition_dispatch_reason"] == "is_x_periodic_false_field_metadata"
    assert diagnostics["interior_only_reduction_applied"] is True

    trim = diagnostics["interior_only_trim_width"]
    assert trim > 0
    assert diagnostics["interior_only_row_count"] == field.values.shape[2] - 2 * trim


@pytest.mark.parametrize(
    ("boundary_type", "label", "generator", "kwargs", "evaluator"),
    _NONPERIODIC_CASES,
    ids=_NONPERIODIC_IDS,
)
def test_interior_shave_matches_the_residual_boundary_trim_width(
    boundary_type, label, generator, kwargs, evaluator
) -> None:
    """The shave must track the FD stencil, not a hardcoded constant.

    A fixed shave that drifts from ``boundary_trim_width`` silently reintroduces
    contaminated boundary rows into the SVD.
    """
    field = _restrict_to_nonperiodic_window(generator(**kwargs), boundary_type)
    residual_trim = evaluator().evaluate(field).diagnostics["boundary_trim_width"]
    diagnostics = fit_translation_generator(field, evaluator()).diagnostics

    assert diagnostics["interior_only_trim_width"] == residual_trim


@pytest.mark.parametrize(
    ("boundary_type", "label", "generator", "kwargs", "evaluator"),
    _NONPERIODIC_CASES,
    ids=_NONPERIODIC_IDS,
)
def test_nonperiodic_branch_suppresses_the_reference_fallback(
    boundary_type, label, generator, kwargs, evaluator
) -> None:
    """The emitted span must be the honest SVD value, never a masked 0.0."""
    field = _restrict_to_nonperiodic_window(generator(**kwargs), boundary_type)
    diagnostics = fit_translation_generator(field, evaluator()).diagnostics

    assert diagnostics["reference_fallback_used"] is False
    assert diagnostics["fit_mode"] == "svd"
    assert (
        diagnostics["fallback_reason"] == "reference_fallback_suppressed_on_nonperiodic_branch"
    )
    assert diagnostics["selected_span_distance"] == diagnostics["svd_span_distance"]


def test_suppression_actually_changes_a_case_that_would_have_fallen_back() -> None:
    """Pin a configuration where the fallback would fire and mask the failure.

    Advection-diffusion at this grid has ``min_delta_basis == "1"`` and an SVD
    span well past the fallback tolerance -- both fallback triggers. With
    suppression the honest span is reported; without it the emitted value would
    be exactly 0.0, i.e. a perfect translation generator on a fit that drifted
    by more than half the available range.
    """
    boundary_type, _label, generator, kwargs, evaluator = _NONPERIODIC_CASES[3]
    field = _restrict_to_nonperiodic_window(generator(**kwargs), boundary_type)
    diagnostics = fit_translation_generator(field, evaluator()).diagnostics

    assert diagnostics["min_delta_basis"] == "1"
    assert diagnostics["svd_span_distance"] > 0.05
    assert diagnostics["selected_span_distance"] > 0.05
    assert diagnostics["selected_span_distance"] != 0.0


@pytest.mark.parametrize(
    ("boundary_type", "label", "generator", "kwargs", "evaluator"),
    _NONPERIODIC_CASES,
    ids=_NONPERIODIC_IDS,
)
def test_nonperiodic_symmetry_claim_never_asserts_bvp_preservation(
    boundary_type, label, generator, kwargs, evaluator
) -> None:
    """No v0.33 code path may emit ``boundary_value_problem_preserved``."""
    field = _restrict_to_nonperiodic_window(generator(**kwargs), boundary_type)
    diagnostics = fit_translation_generator(field, evaluator()).diagnostics

    claim = diagnostics["symmetry_claim"]
    assert claim != "boundary_value_problem_preserved"
    expected = (
        "inconclusive_boundary_metadata"
        if boundary_type == "open_unknown"
        else "equation_symmetry_candidate"
    )
    assert claim == expected


def test_no_code_path_emits_boundary_value_problem_preserved() -> None:
    """The reserved-but-unemittable invariant, asserted across every case."""
    emitted = set()
    for boundary_type, _label, generator, kwargs, evaluator in _NONPERIODIC_CASES:
        field = _restrict_to_nonperiodic_window(generator(**kwargs), boundary_type)
        emitted.add(fit_translation_generator(field, evaluator()).diagnostics["symmetry_claim"])
    for _label, generator, kwargs, evaluator in _PERIODIC_CASES:
        emitted.add(
            fit_translation_generator(generator(**kwargs), evaluator()).diagnostics["symmetry_claim"]
        )

    assert "boundary_value_problem_preserved" not in emitted


# --------------------------------------------------------------------------
# Method adapter forwarding
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("boundary_type", "label", "generator", "kwargs", "evaluator"),
    _NONPERIODIC_CASES,
    ids=_NONPERIODIC_IDS,
)
def test_method_adapter_forwards_dispatch_diagnostics_verbatim(
    boundary_type, label, generator, kwargs, evaluator
) -> None:
    method = PolynomialTranslationSvdMethod()
    field = _restrict_to_nonperiodic_window(generator(**kwargs), boundary_type)

    family_diagnostics = fit_translation_generator(field, evaluator()).diagnostics
    result = method.fit(field, residual_evaluator=evaluator())

    for key in (
        "boundary_condition_x",
        "boundary_condition_dispatch_reason",
        "interior_only_reduction_applied",
        "interior_only_row_count",
        "symmetry_claim",
    ):
        assert result.fit_diagnostics[key] == family_diagnostics[key]

    assert set(result.method_scores) == _FROZEN_FOUR_SCORE_NAMES


def test_method_adapter_accepts_nonperiodic_input() -> None:
    """The pre-v0.33a periodic guard on the adapter is gone."""
    boundary_type, _label, generator, kwargs, evaluator = _NONPERIODIC_CASES[0]
    field = _restrict_to_nonperiodic_window(generator(**kwargs), boundary_type)
    result = method_result = PolynomialTranslationSvdMethod().fit(
        field, residual_evaluator=evaluator()
    )
    assert result.method_scores["residual_l2"] is not None
    assert method_result.fit_diagnostics["interior_only_reduction_applied"] is True


# --------------------------------------------------------------------------
# Conditioning warning
# --------------------------------------------------------------------------


def test_warning_emitted_when_interior_rows_fall_below_threshold() -> None:
    """The interior shave costs 2*trim rows; below the floor the SVD is unusable."""
    field = _restrict_to_nonperiodic_window(
        generate_heat_1d_field_batch(batch_size=1, num_times=17, num_points=32, seed=0),
        "dirichlet",
        keep=0.5,
    )
    with pytest.warns(UserWarning, match="interior rows"):
        diagnostics = fit_translation_generator(field, HeatResidualEvaluator(diffusivity=0.1)).diagnostics

    assert diagnostics["interior_only_row_count"] < MINIMUM_INTERIOR_ROW_COUNT


def test_no_warning_on_a_comfortably_resolved_nonperiodic_grid() -> None:
    field = _restrict_to_nonperiodic_window(
        generate_heat_1d_field_batch(batch_size=1, num_times=17, num_points=128, seed=0),
        "dirichlet",
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        diagnostics = fit_translation_generator(field, HeatResidualEvaluator(diffusivity=0.1)).diagnostics

    assert diagnostics["interior_only_row_count"] >= MINIMUM_INTERIOR_ROW_COUNT


def test_no_warning_on_the_periodic_branch() -> None:
    """The periodic branch takes no shave, so the row floor cannot trip."""
    field = generate_heat_1d_field_batch(batch_size=1, num_times=17, num_points=16, seed=0)
    with warnings.catch_warnings():
        warnings.simplefilter("error", UserWarning)
        diagnostics = fit_translation_generator(field, HeatResidualEvaluator(diffusivity=0.1)).diagnostics

    assert diagnostics["interior_only_reduction_applied"] is False


# --------------------------------------------------------------------------
# Resolution behaviour
# --------------------------------------------------------------------------


def test_nonperiodic_heat_fit_converges_with_resolution() -> None:
    """The interior-only fit must improve as the grid refines.

    A fit that does not converge would indicate the shave is discarding the
    wrong rows rather than removing contamination.
    """
    spans = []
    for num_points in (64, 128, 256):
        field = _restrict_to_nonperiodic_window(
            generate_heat_1d_field_batch(
                batch_size=1, num_times=17, num_points=num_points, seed=0
            ),
            "dirichlet",
        )
        spans.append(
            fit_translation_generator(
                field, HeatResidualEvaluator(diffusivity=0.1)
            ).diagnostics["svd_span_distance"]
        )

    assert all(later < earlier for earlier, later in itertools.pairwise(spans)), spans
    assert spans[-1] < 1e-2


def test_nonperiodic_diagnostics_round_trip_through_strict_json() -> None:
    import json

    boundary_type, _label, generator, kwargs, evaluator = _NONPERIODIC_CASES[0]
    field = _restrict_to_nonperiodic_window(generator(**kwargs), boundary_type)
    result = PolynomialTranslationSvdMethod().fit(field, residual_evaluator=evaluator())

    payload = {
        "method_scores": result.method_scores,
        "fit_diagnostics": result.fit_diagnostics,
    }
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload
    assert np.isfinite(result.method_scores["residual_l2"])
