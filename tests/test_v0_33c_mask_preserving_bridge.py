"""v0.33c mask-preserving discovery bridge.

Three things here came from measuring the bridge rather than from the draft.

**Design-matrix rows are TIME samples, not spatial points.**
``to_pysindy_trajectories`` emits ``(num_times, num_points)`` arrays in which each
x point is a PySINDy *feature*. The derivative-stencil erosion the mask contract
describes is therefore temporal, and a mask that removes some but not all cells
of a time row is feature removal rather than row selection. Such masks are
refused: honoring them would change the model shape, ``feature_names``, and the
coefficient dimensions. Measured, a single fully-masked x column reduces the
observation row count to **zero**.

**The correct path requires precomputed ``x_dot``.** Differentiating a
row-selected array computes a derivative across the removed rows -- the exact
leakage being closed. Measured, that naive path differs from the correct one by
7.2e-5 relative on smooth heat data. PySINDy 2.1 accepts ``x_dot`` on ``fit``,
so the task differentiates on the full trajectory and row-selects afterwards.

**The spectral rejection inspects the caller's model.** PDELie's
``compute_derivatives`` backend resolution is not in this code path at all;
differentiation is performed by ``pysindy_model.differentiation_method``.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np
import pytest

from pdelie.contracts import FieldBatch
from pdelie.errors import ScopeValidationError
from pdelie.tasks.discovery import (
    PDELIE_MASK_DIAGNOSTICS_KEY,
    run_pysindy_pde_task,
)

pysindy = pytest.importorskip(
    "pysindy",
    reason="pysindy is an optional backend; v0.33c bridge tests are skipped when unavailable.",
)

from pdelie.data import generate_heat_1d_field_batch  # noqa: E402 — post-importorskip

_NUM_TIMES = 33
_NUM_POINTS = 16
_SEED = 0
_EXPECTED_TOP_LEVEL_KEY_COUNT = 22


def _field(mask: np.ndarray | None = None, *, batch_size: int = 1) -> FieldBatch:
    base = generate_heat_1d_field_batch(
        batch_size=batch_size, num_times=_NUM_TIMES, num_points=_NUM_POINTS, seed=_SEED
    )
    return FieldBatch(
        values=base.values,
        dims=base.dims,
        coords=base.coords,
        var_names=base.var_names,
        metadata=base.metadata,
        preprocess_log=[],
        mask=mask,
    )


def _model(differentiation: Any = None) -> Any:
    return pysindy.SINDy(
        optimizer=pysindy.STLSQ(threshold=0.1, alpha=0.05, max_iter=20),
        feature_library=pysindy.PolynomialLibrary(degree=2, include_bias=True),
        differentiation_method=differentiation or pysindy.FiniteDifference(),
    )


def _full_mask(*, batch_size: int = 1) -> np.ndarray:
    return np.ones((batch_size, _NUM_TIMES, _NUM_POINTS, 1), dtype=bool)


def _contiguous_time_mask(*, start: int = 10, width: int = 4) -> np.ndarray:
    mask = _full_mask()
    mask[:, start : start + width, :, :] = False
    return mask


def _diagnostics(result: dict[str, Any]) -> dict[str, Any]:
    return result["underlying_discovery_result"]["fit_diagnostics"][
        PDELIE_MASK_DIAGNOSTICS_KEY
    ]


def _run(mask: np.ndarray | None = None, **kwargs: Any) -> dict[str, Any]:
    return run_pysindy_pde_task(
        _field(mask), task_name="v0_33c", pysindy_model=_model(), **kwargs
    )


# --------------------------------------------------------------------------
# Schema invariants
# --------------------------------------------------------------------------


def test_top_level_key_count_is_still_exactly_22() -> None:
    """Exit gate: the mask diagnostics must not widen the top-level schema."""
    assert len(_run()) == _EXPECTED_TOP_LEVEL_KEY_COUNT
    assert len(_run(_contiguous_time_mask())) == _EXPECTED_TOP_LEVEL_KEY_COUNT


def test_mask_diagnostics_are_namespaced_inside_the_embedded_sibling() -> None:
    """Placement is constrained: no top-level ``fit_diagnostics`` exists.

    The diagnostics live under one namespaced key so the verbatim guarantee on
    ``underlying_discovery_result`` still covers every backend-native field.
    """
    result = _run(_contiguous_time_mask())
    assert "fit_diagnostics" not in result
    fit_diagnostics = result["underlying_discovery_result"]["fit_diagnostics"]
    assert PDELIE_MASK_DIAGNOSTICS_KEY in fit_diagnostics
    # No mask key leaked into the backend-native namespace.
    for key in fit_diagnostics:
        if key != PDELIE_MASK_DIAGNOSTICS_KEY:
            assert "mask" not in key


def test_result_round_trips_through_strict_json() -> None:
    import json

    result = _run(_contiguous_time_mask())
    assert json.loads(json.dumps(result, allow_nan=False)) == result


# --------------------------------------------------------------------------
# The three-mask decomposition
# --------------------------------------------------------------------------


def test_unmasked_field_reports_stage_none_and_full_counts() -> None:
    diagnostics = _diagnostics(_run())

    assert diagnostics["mask_application_stage"] == "none"
    assert diagnostics["observation_mask_row_count"] == _NUM_TIMES
    assert diagnostics["derivative_validity_mask_row_count"] == _NUM_TIMES
    assert diagnostics["regression_row_mask_row_count"] == _NUM_TIMES
    assert diagnostics["unmasked_row_count"] == _NUM_TIMES
    assert diagnostics["mask_row_count_reduction_from_derivative_stencil"] == 0


@pytest.mark.parametrize(
    "mask_builder",
    [
        pytest.param(lambda: _contiguous_time_mask(start=10, width=4), id="interior-block"),
        pytest.param(lambda: _contiguous_time_mask(start=0, width=1), id="first-row"),
        pytest.param(lambda: _contiguous_time_mask(start=_NUM_TIMES - 1, width=1), id="last-row"),
        pytest.param(lambda: _contiguous_time_mask(start=5, width=1), id="single-interior"),
    ],
)
def test_three_mask_nesting_invariant_holds(mask_builder) -> None:
    """``regression_row`` subset of ``derivative_validity`` subset of ``observation``.

    Asserted against PySINDy's own stencil rather than assumed: the erosion is
    by a footprint the bridge does not control.
    """
    diagnostics = _diagnostics(_run(mask_builder()))

    observation = diagnostics["observation_mask_row_count"]
    validity = diagnostics["derivative_validity_mask_row_count"]
    regression = diagnostics["regression_row_mask_row_count"]

    assert regression <= validity <= observation <= diagnostics["unmasked_row_count"]


def test_masked_after_differentiation_erodes_by_the_stencil() -> None:
    """Exit gate: the reduction matches the differentiation stencil footprint."""
    diagnostics = _diagnostics(_run(_contiguous_time_mask(start=10, width=4)))

    assert diagnostics["mask_application_stage"] == "after_differentiation"
    assert diagnostics["observation_mask_row_count"] == _NUM_TIMES - 4
    assert (
        diagnostics["derivative_validity_mask_row_count"]
        < diagnostics["observation_mask_row_count"]
    )
    # A contiguous interior block erodes one row on each side at half-width 1.
    half_width = diagnostics["derivative_stencil_half_width"]
    assert half_width >= 1
    assert diagnostics["mask_row_count_reduction_from_derivative_stencil"] == 2 * half_width


def test_scattered_mask_erodes_more_than_a_contiguous_one() -> None:
    """More mask boundaries mean more stencil contamination."""
    contiguous = _diagnostics(_run(_contiguous_time_mask(start=10, width=4)))

    scattered = _full_mask()
    scattered[:, ::7, :, :] = False
    scattered_diagnostics = _diagnostics(_run(scattered))

    assert (
        scattered_diagnostics["mask_row_count_reduction_from_derivative_stencil"]
        > contiguous["mask_row_count_reduction_from_derivative_stencil"]
    )


# --------------------------------------------------------------------------
# mask_application semantics
# --------------------------------------------------------------------------


def test_before_differentiation_warns_and_names_the_leakage_risk() -> None:
    """Exit gate: the opt-in legacy path warns."""
    with pytest.warns(UserWarning, match="leakage"):
        result = _run(_contiguous_time_mask(), mask_application="before_differentiation")

    diagnostics = _diagnostics(result)
    assert diagnostics["mask_application_stage"] == "before_differentiation"
    # The legacy path applies no stencil erosion -- that is the leakage.
    assert diagnostics["mask_row_count_reduction_from_derivative_stencil"] == 0
    assert (
        diagnostics["derivative_validity_mask_row_count"]
        == diagnostics["observation_mask_row_count"]
    )


def test_after_differentiation_is_the_default() -> None:
    assert _diagnostics(_run(_contiguous_time_mask()))["mask_application_stage"] == (
        "after_differentiation"
    )


def test_default_path_emits_no_leakage_warning() -> None:
    """The correct-by-construction path must be silent about leakage.

    Recorded rather than raised, because PySINDy emits unrelated STLSQ warnings
    that this assertion is not about.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _run(_contiguous_time_mask())
    assert not [w for w in caught if "leakage" in str(w.message)]


def test_unknown_mask_application_raises() -> None:
    with pytest.raises(ScopeValidationError, match="mask_application must be one of"):
        _run(mask_application="sideways")


def test_unmasked_field_never_warns_about_leakage_even_on_the_legacy_path() -> None:
    """With no mask there is nothing to leak, so the warning must stay silent."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = _run(mask_application="before_differentiation")
    assert not [w for w in caught if "leakage" in str(w.message)]
    assert _diagnostics(result)["mask_application_stage"] == "none"


# --------------------------------------------------------------------------
# Rejections
# --------------------------------------------------------------------------


def test_partial_time_row_mask_is_rejected() -> None:
    """A spatial mask is feature removal, not row selection.

    Measured: a single fully-masked x column drives the observation row count to
    zero, because a row is observable only when all of its x features are. That
    would silently hand the optimizer an empty design matrix, so it is refused.
    """
    mask = _full_mask()
    mask[:, :, 3, :] = False
    with pytest.raises(ScopeValidationError, match="whole time rows"):
        _run(mask)


def test_partial_row_rejection_names_the_offending_indices() -> None:
    mask = _full_mask()
    mask[:, 7, 2, :] = False
    with pytest.raises(ScopeValidationError, match=r"\[7\]"):
        _run(mask)


def test_spectral_differentiation_on_a_masked_field_is_rejected() -> None:
    """Globally-coupled differentiation leaks unobserved rows into observed ones."""
    with pytest.raises(ScopeValidationError, match="globally coupled"):
        run_pysindy_pde_task(
            _field(_contiguous_time_mask()),
            task_name="v0_33c",
            pysindy_model=_model(pysindy.SpectralDerivative()),
        )


def test_spectral_differentiation_without_a_mask_is_allowed() -> None:
    """The rejection is about masked data, not about spectral methods per se."""
    result = run_pysindy_pde_task(
        _field(),
        task_name="v0_33c",
        pysindy_model=_model(pysindy.SpectralDerivative()),
    )
    assert len(result) == _EXPECTED_TOP_LEVEL_KEY_COUNT


def test_mask_validation_precedes_any_fitting() -> None:
    """Both rejections must fire before the backend is touched.

    A model that would explode if fitted proves nothing ran.
    """

    class _ExplodingModel:
        differentiation_method = pysindy.FiniteDifference()

        def fit(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover
            raise AssertionError("fit must not be reached")

    mask = _full_mask()
    mask[:, :, 3, :] = False
    with pytest.raises(ScopeValidationError, match="whole time rows"):
        run_pysindy_pde_task(
            _field(mask), task_name="v0_33c", pysindy_model=_ExplodingModel()
        )


# --------------------------------------------------------------------------
# Preserved invariants
# --------------------------------------------------------------------------


def test_nonperiodic_boundary_gate_still_fires() -> None:
    """v0.33c is orthogonal to the boundary gate; it must not have loosened it."""
    from pdelie.tasks.discovery import PySINDyDiscoveryUnsupportedBoundaryError

    field = _field(_contiguous_time_mask())
    field.metadata["boundary_conditions"] = {"x": "dirichlet"}
    with pytest.raises(PySINDyDiscoveryUnsupportedBoundaryError):
        run_pysindy_pde_task(field, task_name="v0_33c", pysindy_model=_model())


def test_multi_trajectory_batch_still_executes() -> None:
    """v0.32.0 release-close invariant: batch_size > 1 runs cleanly."""
    result = run_pysindy_pde_task(
        _field(batch_size=2), task_name="v0_33c", pysindy_model=_model()
    )
    assert len(result) == _EXPECTED_TOP_LEVEL_KEY_COUNT
    assert _diagnostics(result)["mask_application_stage"] == "none"


def test_summary_type_is_unchanged() -> None:
    result = _run(_contiguous_time_mask())
    assert result["summary_type"] == "discovery_task_result"
    assert result["summary_schema_version"] == "0.1"
