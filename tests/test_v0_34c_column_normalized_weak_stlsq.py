"""v0.34c column-normalized weak-form design matrices.

Two things here came from measurement rather than the plan.

**The weak diagnostic was nondeterministic.** ``pysindy.WeakPDELibrary`` places
its ``K`` domain centers by drawing from the global NumPy RNG and exposes no seed
parameter, so back-to-back identical calls produced different ``column_norms``
and different ``matrix_condition_number`` (measured 7.69 vs 11.42). v0.34c adds
an opt-in ``seed`` kwarg; without it no number in this sub-milestone could be
pinned, and the plan's requirement that the default path "byte-preserve the
v0.31b2 golden report" was unachievable because the report did not reproduce
against itself.

**The planned 87x / 111.8 / 3.77 figures do not reproduce.** They could not be
matched on any of 48 swept configurations. Across 12 unseeded draws of the
canonical fixture, ``condition_number_before_normalization`` ranged 5.03-14.44
and ``column_scale_ratio`` ranged 3.93-6.64 -- the figures were one draw from a
distribution. At the pinned seed the canonical fixture improves by **1.79x**, and
the improvement across fixtures ranges 1.79x-48.34x with a median of 4.51x.

The gate is therefore a universal invariant (normalization never *worsens*
conditioning) plus per-fixture pinned values, not a single headline threshold. A
single threshold would either fail on the canonical fixture or be chosen to pass
on one that clears it.
"""

from __future__ import annotations

import json
import warnings

import numpy as np
import pytest

from pdelie.data import generate_heat_1d_field_batch
from pdelie.discovery.column_normalize import (
    column_normalize_design_matrix,
    rescale_coefficients,
    summarize_column_normalization,
)
from pdelie.errors import ScopeValidationError, ShapeValidationError

pysindy = pytest.importorskip(
    "pysindy",
    reason="pysindy is an optional backend; v0.34c tests are skipped when unavailable.",
)

from pdelie.tasks.weak_pde_library import (  # noqa: E402 — post-importorskip
    WeakPDELibraryDiagnostic,
    inspect_pysindy_weak_pde_library,
)
from tests._helpers.conditioning_ratios import (  # noqa: E402
    CONDITIONING_ATOL,
    CONDITIONING_FIXTURE_NAMES,
    CONDITIONING_FIXTURE_PATH,
    CONDITIONING_RTOL,
    CONDITIONING_SEED,
    MINIMUM_IMPROVEMENT_RATIO,
    PINNED_METRIC_NAMES,
    load_fixture,
    measure_conditioning,
)

_EXPECTED_DEFAULT_KEY_COUNT = 27
_CANONICAL_CONFIG = WeakPDELibraryDiagnostic(
    polynomial_degree=2, derivative_order=2, num_domain_centers_K=16
)


def _field():
    return generate_heat_1d_field_batch(
        batch_size=1, num_times=64, num_points=64, seed=3120
    )


def _run(**kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return inspect_pysindy_weak_pde_library(
            _field(),
            task_name="v0_34c",
            library_configuration=_CANONICAL_CONFIG,
            **kwargs,
        )


# --------------------------------------------------------------------------
# The pure-numpy helper
# --------------------------------------------------------------------------


def test_column_normalize_gives_unit_norm_columns() -> None:
    rng = np.random.default_rng(0)
    matrix = rng.normal(size=(40, 6)) * np.array([1.0, 10.0, 100.0, 0.1, 5.0, 50.0])
    normalized, scaling, zero_count = column_normalize_design_matrix(matrix)

    assert zero_count == 0
    np.testing.assert_allclose(np.linalg.norm(normalized, axis=0), 1.0, rtol=1e-12)
    np.testing.assert_allclose(normalized * scaling, matrix, rtol=1e-12)


def test_zero_norm_column_is_not_divided_by_zero() -> None:
    """A zero column carries no information; its scale is 1.0 and it is counted."""
    matrix = np.ones((10, 3))
    matrix[:, 1] = 0.0
    normalized, scaling, zero_count = column_normalize_design_matrix(matrix)

    assert zero_count == 1
    assert scaling[1] == 1.0
    assert np.all(np.isfinite(normalized))
    np.testing.assert_array_equal(normalized[:, 1], 0.0)


def test_rescale_coefficients_inverts_the_scaling() -> None:
    """Fitting on M/s and rescaling must recover the raw-space coefficients."""
    rng = np.random.default_rng(1)
    matrix = rng.normal(size=(60, 4)) * np.array([1.0, 20.0, 0.5, 8.0])
    truth = np.array([0.3, -1.2, 4.0, 0.05])
    target = matrix @ truth

    normalized, scaling, _ = column_normalize_design_matrix(matrix)
    normalized_coefficients, *_ = np.linalg.lstsq(normalized, target, rcond=None)
    recovered = rescale_coefficients(normalized_coefficients, scaling)

    np.testing.assert_allclose(recovered, truth, rtol=1e-8, atol=1e-10)


def test_rescale_coefficients_supports_two_dimensional_coefficients() -> None:
    scaling = np.array([2.0, 4.0])
    coefficients = np.array([[2.0, 8.0], [6.0, 4.0]])
    np.testing.assert_allclose(
        rescale_coefficients(coefficients, scaling), np.array([[1.0, 2.0], [3.0, 1.0]])
    )


@pytest.mark.parametrize(
    ("bad", "error"),
    [
        (np.array([1.0, 2.0]), ShapeValidationError),
        (np.zeros((0, 3)), ShapeValidationError),
        (np.array([[1.0, np.nan]]), ScopeValidationError),
        (np.array([[1.0, np.inf]]), ScopeValidationError),
    ],
    ids=["one-dimensional", "empty", "nan", "inf"],
)
def test_malformed_design_matrix_is_rejected(bad, error) -> None:
    with pytest.raises(error):
        column_normalize_design_matrix(bad)


def test_rescale_rejects_mismatched_scaling_length() -> None:
    with pytest.raises(ShapeValidationError, match="must match the scaling"):
        rescale_coefficients(np.ones(3), np.ones(4))


def test_summary_block_is_strict_json_and_diagnostic_only() -> None:
    rng = np.random.default_rng(2)
    block = summarize_column_normalization(rng.normal(size=(30, 5)))

    assert json.loads(json.dumps(block, allow_nan=False)) == block
    assert block["applied"] is True
    assert block["diagnostic_only"] is True


# --------------------------------------------------------------------------
# The seed kwarg: the prerequisite for pinning anything
# --------------------------------------------------------------------------


def test_seeded_runs_are_reproducible() -> None:
    assert _run(seed=1234) == _run(seed=1234)


def test_different_seeds_give_different_reports() -> None:
    """Confirms the diagnostic genuinely depends on the RNG draw."""
    assert _run(seed=1234) != _run(seed=99)


def test_unseeded_default_behaviour_is_unchanged() -> None:
    """The default path is left exactly as nondeterministic as it was.

    This is deliberate: seeding by default would silently change every existing
    caller's output. The opt-in seed is what makes reproducibility available.
    """
    assert _run() != _run()


def test_seeding_does_not_perturb_the_callers_global_rng() -> None:
    # NPY002 suppressed deliberately: the point of this test is that seeding
    # inside the diagnostic does not disturb the LEGACY global stream, which is
    # the one PySINDy consumes. A Generator would not exercise the risk.
    np.random.seed(7)  # noqa: NPY002
    before = np.random.rand()  # noqa: NPY002
    np.random.seed(7)  # noqa: NPY002
    _run(seed=1234)
    after = np.random.rand()  # noqa: NPY002
    assert before == after


# --------------------------------------------------------------------------
# Report shape
# --------------------------------------------------------------------------


def test_default_path_keeps_exactly_the_frozen_27_keys() -> None:
    report = _run()
    assert len(report) == _EXPECTED_DEFAULT_KEY_COUNT
    assert "column_normalization" not in report


def test_opt_in_path_adds_exactly_one_key() -> None:
    report = _run(column_normalize=True)
    assert len(report) == _EXPECTED_DEFAULT_KEY_COUNT + 1
    assert "column_normalization" in report


def test_opt_in_differs_from_default_only_by_the_block() -> None:
    """Everything outside the new block must be untouched by the flag."""
    default = _run(seed=555)
    opted_in = _run(seed=555, column_normalize=True)
    assert {k: v for k, v in opted_in.items() if k != "column_normalization"} == default


def test_report_round_trips_through_strict_json() -> None:
    report = _run(seed=555, column_normalize=True)
    assert json.loads(json.dumps(report, allow_nan=False)) == report


def test_diagnostic_only_and_method_family_are_unchanged() -> None:
    report = _run(seed=555, column_normalize=True)
    assert report["diagnostic_only"] is True
    assert report["method_family"] == "pysindy_weak_pde_library_polynomial_gauss_v1"


# --------------------------------------------------------------------------
# The conditioning claim
# --------------------------------------------------------------------------


@pytest.mark.parametrize("fixture_name", CONDITIONING_FIXTURE_NAMES)
def test_normalization_never_worsens_conditioning(fixture_name: str) -> None:
    """The universal invariant, and the only threshold asserted everywhere.

    A single headline threshold is not asserted because the improvement is
    strongly fixture-dependent: 1.79x on the canonical fixture versus 48.34x on
    advection-diffusion at the pinned seed.
    """
    measured = {entry["name"]: entry for entry in measure_conditioning()}
    ratio = measured[fixture_name]["condition_number_improvement_ratio"]
    assert ratio >= MINIMUM_IMPROVEMENT_RATIO


@pytest.mark.parametrize("fixture_name", CONDITIONING_FIXTURE_NAMES)
def test_conditioning_values_match_the_pinned_fixture(fixture_name: str) -> None:
    expected = {entry["name"]: entry for entry in load_fixture()["fixtures"]}[fixture_name]
    observed = {entry["name"]: entry for entry in measure_conditioning()}[fixture_name]

    for metric in PINNED_METRIC_NAMES:
        tolerance = CONDITIONING_ATOL + CONDITIONING_RTOL * abs(expected[metric])
        assert abs(observed[metric] - expected[metric]) <= tolerance, (
            f"{fixture_name}.{metric} drifted: expected {expected[metric]!r}, "
            f"observed {observed[metric]!r}. Regenerate with a named cause via "
            "python -m tests._helpers.conditioning_ratios --reason '<cause>'."
        )


def test_fixture_records_why_the_seed_is_required() -> None:
    """The seed rationale is load-bearing provenance, not a comment.

    Without it a future reader would reasonably assume these numbers could be
    reproduced by calling the diagnostic directly, which is false.
    """
    payload = load_fixture()
    assert payload["seed"] == CONDITIONING_SEED
    assert payload["seed_is_required_for_reproducibility"] is True
    assert "no seed parameter" in payload["seed_rationale"]
    assert payload["last_regeneration_reason"].strip()


def test_fixture_is_strict_json() -> None:
    payload = json.loads(CONDITIONING_FIXTURE_PATH.read_text(encoding="utf-8"))
    json.dumps(payload, allow_nan=False)


def test_canonical_fixture_improvement_is_modest_and_pinned_as_such() -> None:
    """Pin the fact that the canonical fixture improves by under 2x.

    The v0.34 plan carried an 87x column-scale ratio and a 111.8 -> 3.77
    condition drop. Neither reproduces. Recording the real canonical number here
    prevents the planned figures from creeping back into docs or a release note.
    """
    entry = {e["name"]: e for e in load_fixture()["fixtures"]}["canonical"]
    assert entry["condition_number_improvement_ratio"] < 2.0
    assert entry["column_scale_ratio"] < 10.0
    assert entry["condition_number_before_normalization"] < 20.0


# --------------------------------------------------------------------------
# Explicit non-claims
# --------------------------------------------------------------------------


def test_report_makes_no_wsindy_or_noise_robustness_claim() -> None:
    payload = json.dumps(_run(seed=555, column_normalize=True)).lower()
    for forbidden in ("wsindy", "noise_robust", "noise-robust", "noise robustness"):
        assert forbidden not in payload


def test_module_documents_this_as_a_conditioning_fix() -> None:
    from pdelie.discovery import column_normalize as module

    docstring = (module.__doc__ or "").lower()
    assert "conditioning" in docstring
    assert "not a noise-robustness fix" in docstring
    assert "not wsindy" in docstring
