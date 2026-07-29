"""v0.35a: design-matrix diagnostics.

References are hand-computed or closed-form wherever one exists. Asserting
against library output would let a NumPy release silently move the "reference";
asserting against ``leverage(I_4) == 1`` cannot drift.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie.diagnostics import (
    COLUMN_SCALING_CONVENTION,
    RESTRICTED_EIGENVALUE_DEFINITION,
    irrepresentability_constant,
    leverage_scores,
    mutual_coherence,
    restricted_eigenvalue,
    summarize_design_matrix_diagnostics,
)
from pdelie.errors import ScopeValidationError, ShapeValidationError
from tests._helpers.regenerate_v0_35a_design_matrix import (
    DESIGN_MATRIX_SEED,
    build_design_matrix,
    load_fixture,
    matrix_properties,
)

RTOL = 1e-6


def hilbert(n: int) -> np.ndarray:
    i = np.arange(1, n + 1)
    return 1.0 / (i[:, None] + i[None, :] - 1.0)


def orthonormal_8x4() -> np.ndarray:
    rng = np.random.default_rng(20350)
    q, _ = np.linalg.qr(rng.standard_normal((8, 4)))
    return q


def rank_deficient_8x4() -> np.ndarray:
    rng = np.random.default_rng(20350)
    rng.standard_normal((8, 4))  # advance to match the prototype's draw order
    a = rng.standard_normal((8, 4))
    a[:, 3] = a[:, 1]
    return a


# --- A-1: closed-form references -------------------------------------------


def test_identity_has_zero_coherence() -> None:
    """Orthogonal columns have no pairwise correlation. Analytic value: 0."""
    assert mutual_coherence(np.eye(4))["metric_value"] == 0.0


def test_identity_has_unit_leverage_everywhere() -> None:
    """A square full-rank matrix has hat matrix I, so every leverage is 1."""
    report = leverage_scores(np.eye(4))
    assert report["leverage_scores"] == pytest.approx([1.0, 1.0, 1.0, 1.0])
    assert report["max_leverage"] == pytest.approx(1.0)


def test_leverage_sums_to_rank() -> None:
    """sum(h_i) == rank(A) is an identity, not an approximation."""
    for matrix in (np.eye(4), orthonormal_8x4(), hilbert(5), rank_deficient_8x4()):
        report = leverage_scores(matrix)
        assert report["leverage_sum"] == pytest.approx(float(report["matrix_rank"]))


def test_leverage_entries_lie_in_the_unit_interval() -> None:
    for matrix in (np.eye(4), orthonormal_8x4(), hilbert(5), rank_deficient_8x4()):
        scores = leverage_scores(matrix)["leverage_scores"]
        assert all(-1e-12 <= value <= 1.0 + 1e-12 for value in scores)


def test_orthonormal_design_has_vanishing_coherence_and_irrepresentability() -> None:
    """Columns outside the support are orthogonal to it, so both are ~0."""
    q = orthonormal_8x4()
    assert mutual_coherence(q)["metric_value"] == pytest.approx(0.0, abs=1e-12)
    report = irrepresentability_constant(q, support=[0, 1])
    assert report["metric_value"] == pytest.approx(0.0, abs=1e-12)
    assert report["condition_satisfied"] is True


def test_identity_restricted_eigenvalue_is_one_over_n() -> None:
    """A_S^T A_S = I_2 for the identity, so lambda_min / n = 1/4 at n = 4."""
    report = restricted_eigenvalue(np.eye(4), support=[0, 1])
    assert report["metric_value"] == pytest.approx(0.25)
    assert report["sqrt_n_convention_multiplier"] == 4


def test_collinear_columns_give_unit_coherence() -> None:
    matrix = np.array([[1.0, 2.0], [2.0, 4.0], [3.0, 6.0]])
    report = mutual_coherence(matrix)
    assert report["metric_value"] == pytest.approx(1.0)
    assert "mutual_coherence_indicates_collinear_columns" in report["warnings"]


# --- A-1 finding 1: leverage must not use the hat-matrix route -------------


@pytest.mark.parametrize("size", [5, 8, 10])
def test_leverage_is_exact_on_ill_conditioned_square_matrices(size: int) -> None:
    """Regression guard for the hat-matrix route.

    A square full-rank matrix has leverage exactly 1.0 everywhere regardless of
    conditioning. Computing it as ``diag(A (A^T A)^-1 A^T)`` squares the
    condition number; measured error on Hilbert(8) was 5.634e-01 and on
    Hilbert(10) 6.258e-01, against a quantity bounded in [0, 1]. The SVD route
    holds at machine epsilon. This test fails loudly if the route ever changes.
    """
    report = leverage_scores(hilbert(size))
    assert report["leverage_scores"] == pytest.approx([1.0] * size, abs=1e-9)


# --- A-3: the column-scaling contract --------------------------------------


def test_coherence_and_leverage_are_scale_invariant() -> None:
    matrix, _target, _names = build_design_matrix()
    rng = np.random.default_rng(7)
    rescaled = matrix * rng.uniform(0.1, 10.0, size=matrix.shape[1])

    assert mutual_coherence(matrix)["metric_value"] == pytest.approx(
        mutual_coherence(rescaled)["metric_value"], rel=1e-9
    )
    assert leverage_scores(matrix)["max_leverage"] == pytest.approx(
        leverage_scores(rescaled)["max_leverage"], rel=1e-9
    )


def test_normalization_makes_the_scale_dependent_metrics_reproducible() -> None:
    """The whole reason the scaling is frozen.

    Measured on the raw canonical matrix, an arbitrary column rescaling moved
    the irrepresentability constant from 1.129160013 to 0.2955377896 -- across
    the 1.0 threshold, flipping the reported verdict on identical data. Because
    every metric is computed after normalization, a rescaled matrix must now
    report the same value.
    """
    matrix, _target, _names = build_design_matrix()
    rng = np.random.default_rng(7)
    rescaled = matrix * rng.uniform(0.1, 10.0, size=matrix.shape[1])

    for support in ([0, 1], [1, 2]):
        base = irrepresentability_constant(matrix, support=support)["metric_value"]
        moved = irrepresentability_constant(rescaled, support=support)["metric_value"]
        assert base == pytest.approx(moved, rel=1e-9)

        base_re = restricted_eigenvalue(matrix, support=support)["metric_value"]
        moved_re = restricted_eigenvalue(rescaled, support=support)["metric_value"]
        assert base_re == pytest.approx(moved_re, rel=1e-9)


def test_every_report_names_its_column_scaling() -> None:
    matrix = orthonormal_8x4()
    for report in (
        mutual_coherence(matrix),
        leverage_scores(matrix),
        irrepresentability_constant(matrix, support=[0, 1]),
        restricted_eigenvalue(matrix, support=[0, 1]),
    ):
        assert report["column_scaling"] == COLUMN_SCALING_CONVENTION


def test_restricted_eigenvalue_names_the_definition_it_reports() -> None:
    """It is not the full cone-constrained BRT constant; the payload says so."""
    report = restricted_eigenvalue(np.eye(4), support=[0, 1])
    assert report["restricted_eigenvalue_definition"] == RESTRICTED_EIGENVALUE_DEFINITION
    assert "support_restricted" in RESTRICTED_EIGENVALUE_DEFINITION


# --- A-4: degenerate cases return sentinels, never NaN ----------------------


def test_empty_support_is_refused() -> None:
    """Measured: an empty support summed over an empty axis and returned 0.0,
    which reads as 'perfectly recoverable' when there is no condition at all."""
    with pytest.raises(ScopeValidationError, match="at least one column"):
        irrepresentability_constant(np.eye(4), support=[])
    with pytest.raises(ScopeValidationError, match="at least one column"):
        restricted_eigenvalue(np.eye(4), support=[])


def test_support_covering_all_columns_reports_null_with_a_named_cause() -> None:
    report = irrepresentability_constant(np.eye(4), support=[0, 1, 2, 3])
    assert report["metric_value"] is None
    assert report["condition_satisfied"] is None
    assert "irrepresentability_support_covers_all_columns" in report["warnings"]


def test_rank_deficient_support_reports_null_rather_than_a_plausible_number() -> None:
    """The dangerous case.

    On a support whose columns are exact duplicates the Gram matrix is singular,
    and a least-squares solve silently returns the minimum-norm solution --
    measured as 0.4956551696, which reads as 'recovery guaranteed' from a system
    that determines nothing.
    """
    matrix = rank_deficient_8x4()
    report = irrepresentability_constant(matrix, support=[1, 3])
    assert report["metric_value"] is None
    assert "irrepresentability_support_is_rank_deficient" in report["warnings"]


def test_rank_deficient_support_is_flagged_on_the_restricted_eigenvalue_too() -> None:
    """A degenerate support and a merely ill-conditioned one both give a
    near-zero value (measured 0.0 vs 2.162100e-12); only the rank check
    separates them."""
    report = restricted_eigenvalue(rank_deficient_8x4(), support=[1, 3])
    assert report["metric_value"] == pytest.approx(0.0, abs=1e-12)
    assert "restricted_eigenvalue_support_is_rank_deficient" in report["warnings"]
    assert report["support_rank"] == 1


def test_ill_conditioned_but_full_rank_support_is_not_flagged_degenerate() -> None:
    report = restricted_eigenvalue(hilbert(5), support=[0, 1, 2, 3, 4])
    assert "restricted_eigenvalue_support_is_rank_deficient" not in report["warnings"]
    assert report["metric_value"] > 0.0


def test_zero_columns_are_counted_not_inferred() -> None:
    matrix = np.eye(4)
    matrix[:, 2] = 0.0
    report = mutual_coherence(matrix)
    assert report["zero_column_count"] == 1
    assert "design_matrix_contains_zero_columns" in report["warnings"]
    assert np.isfinite(report["metric_value"])


def test_single_column_matrix_reports_null_coherence_with_a_cause() -> None:
    report = mutual_coherence(np.ones((4, 1)))
    assert report["metric_value"] is None
    assert "mutual_coherence_requires_at_least_two_columns" in report["warnings"]


@pytest.mark.parametrize(
    "matrix",
    [np.eye(4), orthonormal_8x4(), hilbert(5), rank_deficient_8x4()],
)
def test_no_report_field_is_nan_or_infinite(matrix: np.ndarray) -> None:
    summary = summarize_design_matrix_diagnostics(matrix, support=[0, 1])
    encoded = json.dumps(summary, allow_nan=False)
    assert "NaN" not in encoded
    assert "Infinity" not in encoded


# --- input validation -------------------------------------------------------


def test_non_two_dimensional_input_is_refused() -> None:
    with pytest.raises(ShapeValidationError, match="two-dimensional"):
        mutual_coherence(np.ones(4))


def test_non_finite_input_is_refused() -> None:
    matrix = np.eye(4)
    matrix[0, 0] = np.nan
    with pytest.raises(ScopeValidationError, match="finite"):
        mutual_coherence(matrix)


def test_support_index_out_of_range_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="outside the feature range"):
        irrepresentability_constant(np.eye(4), support=[0, 9])


def test_repeated_support_index_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="repeat"):
        irrepresentability_constant(np.eye(4), support=[1, 1])


def test_empty_matrix_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="at least one entry"):
        mutual_coherence(np.zeros((0, 3)))


def test_non_iterable_support_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="iterable of integer"):
        irrepresentability_constant(np.eye(4), support=3)


def test_support_of_non_integer_entries_is_refused() -> None:
    """Iterable, but the entries do not convert -- a distinct failure path."""
    with pytest.raises(ScopeValidationError, match="iterable of integer"):
        irrepresentability_constant(np.eye(4), support=["first", "second"])


def test_zero_columns_are_reported_by_every_metric() -> None:
    """The zero-column count is surfaced consistently, not only by coherence."""
    matrix = np.eye(4)
    matrix[:, 2] = 0.0
    for report in (
        mutual_coherence(matrix),
        leverage_scores(matrix),
        irrepresentability_constant(matrix, support=[0, 1]),
        restricted_eigenvalue(matrix, support=[0, 1]),
    ):
        assert "design_matrix_contains_zero_columns" in report["warnings"]


def test_restricted_eigenvalue_never_reports_a_negative_value() -> None:
    """``eigvalsh`` on a positive-semidefinite Gram can return a small negative
    value from rounding; a negative eigenvalue must never reach the payload."""
    candidates = [
        rank_deficient_8x4(),
        hilbert(10),
        np.array([[1.0, 1.0], [1.0, 1.0 + 1e-13]]),
    ]
    for matrix in candidates:
        support = list(range(min(3, matrix.shape[1])))
        value = restricted_eigenvalue(matrix, support=support)["metric_value"]
        assert value is not None
        assert value >= 0.0


# --- A-2: the canonical fixture --------------------------------------------


def test_fixture_reloads_bit_identically_to_a_fresh_build() -> None:
    fixture = load_fixture()
    rebuilt, _target, names = build_design_matrix()
    assert np.array_equal(fixture["design_matrix"], rebuilt)
    assert fixture["feature_names"] == names


def test_fixture_properties_match_the_pinned_values() -> None:
    fixture = load_fixture()
    measured = matrix_properties(fixture["design_matrix"])
    pinned = fixture["provenance"]["properties"]
    for name, value in pinned.items():
        assert measured[name] == pytest.approx(value, rel=RTOL)


def test_fixture_records_why_the_seed_is_required() -> None:
    provenance = load_fixture()["provenance"]
    assert provenance["seed"] == DESIGN_MATRIX_SEED
    assert provenance["seed_is_required_for_reproducibility"] is True
    assert "global NumPy RNG" in provenance["seed_rationale"]


def test_diagnostics_run_on_the_canonical_fixture() -> None:
    """The realistic case: a genuine weak-form design matrix.

    Measured at the pinned seed, the irrepresentability constant on this design
    exceeds 1.0 -- Lasso support recovery is *not* guaranteed here. That is a
    property of the matrix worth reporting, not a defect.
    """
    matrix = load_fixture()["design_matrix"]
    summary = summarize_design_matrix_diagnostics(matrix, support=[0, 1])

    assert summary["summary_type"] == "pdelie_design_matrix_diagnostic"
    assert summary["num_rows"] == 16
    assert summary["num_features"] == 5
    assert summary["mutual_coherence"]["metric_value"] == pytest.approx(
        0.908451212112, rel=RTOL
    )
    assert summary["irrepresentability_constant"]["metric_value"] == pytest.approx(
        2.742717168, rel=RTOL
    )
    assert summary["irrepresentability_constant"]["condition_satisfied"] is False
    assert summary["restricted_eigenvalue"]["metric_value"] == pytest.approx(
        0.006509027033, rel=RTOL
    )
    assert summary["leverage_scores"]["leverage_sum"] == pytest.approx(5.0, rel=RTOL)


# --- scope and invariants ---------------------------------------------------


def test_summary_requires_an_explicit_support() -> None:
    """Two of the four metrics are undefined without one; no silent default."""
    with pytest.raises(TypeError):
        summarize_design_matrix_diagnostics(np.eye(4))  # type: ignore[call-arg]


def test_every_report_is_marked_diagnostic_only() -> None:
    matrix = orthonormal_8x4()
    for report in (
        mutual_coherence(matrix),
        leverage_scores(matrix),
        irrepresentability_constant(matrix, support=[0, 1]),
        restricted_eigenvalue(matrix, support=[0, 1]),
        summarize_design_matrix_diagnostics(matrix, support=[0, 1]),
    ):
        assert report["diagnostic_only"] is True


def test_diagnostics_are_not_exported_from_the_root_namespace() -> None:
    """v0.35 is submodule-only: nothing new joins the root public surface.

    ``pdelie.diagnostics`` becomes an *attribute* of the package once imported --
    that is ordinary submodule binding, not an export. The invariant is that
    ``pdelie.__all__`` is unchanged and no diagnostic name is re-exported at the
    root.
    """
    import pdelie

    assert "diagnostics" not in pdelie.__all__
    for name in (
        "mutual_coherence",
        "leverage_scores",
        "irrepresentability_constant",
        "restricted_eigenvalue",
        "summarize_design_matrix_diagnostics",
    ):
        assert name not in pdelie.__all__
        assert not hasattr(pdelie, name)


def test_module_makes_no_noise_robustness_or_wsindy_claim() -> None:
    from pdelie.diagnostics import design_matrix as module

    text = (module.__doc__ or "").lower()
    for report in (
        mutual_coherence(np.eye(4)),
        leverage_scores(np.eye(4)),
        irrepresentability_constant(np.eye(4), support=[0, 1]),
        restricted_eigenvalue(np.eye(4), support=[0, 1]),
    ):
        text += json.dumps(report).lower()
    for forbidden in ("wsindy", "noise_robust", "noise-robust", "noise robustness"):
        assert forbidden not in text


def test_diagnostics_import_without_scipy_or_pysindy() -> None:
    """Core-installable: the module must not reach for an optional dependency."""
    import pdelie.diagnostics.design_matrix as module

    source = module.__file__
    assert source is not None
    with open(source, encoding="utf-8") as handle:
        text = handle.read()
    assert "import scipy" not in text
    assert "import pysindy" not in text
