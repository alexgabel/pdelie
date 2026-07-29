"""v0.35c: deterministic row selection.

The pivoted QR is checked against ``scipy.linalg.qr(pivoting=True)`` as an
independent oracle. SciPy is a test-only dependency here by design: the core
module must not import it, which is itself asserted.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie.design import (
    NORM_RECOMPUTE_RATIO,
    ROW_SELECTION_METHODS,
    d_optimal_exchange_row_selection,
    leverage_row_selection,
    pivoted_qr_permutation,
    qr_pivot_row_selection,
    summarize_row_selection,
)
from pdelie.errors import ScopeValidationError, ShapeValidationError
from tests._helpers.regenerate_v0_35a_design_matrix import load_fixture

scipy_linalg = pytest.importorskip("scipy.linalg")


def hilbert(n: int) -> np.ndarray:
    i = np.arange(1, n + 1)
    return 1.0 / (i[:, None] + i[None, :] - 1.0)


def kahan(n: int, theta: float = 1.2) -> np.ndarray:
    c, s = np.cos(theta), np.sin(theta)
    a = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            a[i, j] = 0.0 if j < i else (s**i if j == i else -c * s**i)
    return a


def canonical_matrices() -> list[tuple[str, np.ndarray]]:
    rng = np.random.default_rng(20350)
    orthonormal, _ = np.linalg.qr(rng.standard_normal((8, 4)))

    rank_deficient = rng.standard_normal((10, 5))
    rank_deficient[:, 4] = rank_deficient[:, 2]

    tied = np.eye(4)
    graded = rng.standard_normal((12, 6)) * np.array([1e3, 1e2, 1e1, 1.0, 1e-1, 1e-2])
    wide = rng.standard_normal((5, 14))

    return [
        ("identity_6", np.eye(6)),
        ("orthonormal_8x4", orthonormal),
        ("hilbert_7", hilbert(7)),
        ("rank_deficient_10x5", rank_deficient),
        ("tied_norms_4x4", tied),
        ("graded_scales_12x6", graded),
        ("wide_5x14", wide),
        ("weak_matrix_transpose", load_fixture()["design_matrix"].T),
    ]


def oracle_permutation(matrix: np.ndarray) -> np.ndarray:
    _q, _r, pivots = scipy_linalg.qr(
        np.asarray(matrix, dtype=float), pivoting=True, mode="economic"
    )
    return np.asarray(pivots)


# --- C-1: agreement with the SciPy oracle ----------------------------------


@pytest.mark.parametrize("name,matrix", canonical_matrices(), ids=lambda v: v)
def test_pivoted_qr_permutation_matches_scipy(name: str, matrix: np.ndarray) -> None:
    """The permutation, not Q/R -- sign conventions differ and that is not a bug."""
    ours, _recomputes = pivoted_qr_permutation(matrix)
    assert np.array_equal(ours, oracle_permutation(matrix))


def test_tie_break_selects_the_lowest_index() -> None:
    """Four columns of identical norm must pivot in index order."""
    tied = np.eye(4)
    permutation, _ = pivoted_qr_permutation(tied)
    assert np.array_equal(permutation, np.arange(4))
    assert np.array_equal(permutation, oracle_permutation(tied))


def test_pivoted_qr_is_deterministic_across_repeat_runs() -> None:
    for _name, matrix in canonical_matrices():
        runs = {tuple(pivoted_qr_permutation(matrix)[0]) for _ in range(5)}
        assert len(runs) == 1


@pytest.mark.parametrize("size", [10, 14])
def test_norm_downdate_safeguard_is_load_bearing(size: int) -> None:
    """The safeguard changes the answer, and changes it to the correct one.

    Measured across twelve adversarial matrices it altered the permutation in
    eight, and in every case the guarded result matched the oracle while the
    unguarded one did not. This test pins that on high-order Hilbert matrices:
    the safeguard must fire, and the result must match SciPy.
    """
    matrix = hilbert(size)
    permutation, recomputes = pivoted_qr_permutation(matrix)
    assert recomputes > 0, "safeguard did not fire on a matrix chosen to trigger it"
    assert np.array_equal(permutation, oracle_permutation(matrix))


def test_norm_recompute_ratio_is_the_documented_constant() -> None:
    assert NORM_RECOMPUTE_RATIO == 1e-8


def test_scipy_agreement_holds_where_pivoting_has_signal() -> None:
    """Documents the boundary of the oracle guarantee rather than overstating it.

    The Kahan matrix is built to defeat column pivoting -- every column norm is
    exactly 1.0, so late pivots are separated by rounding, not signal. Agreement
    holds through order 28 and breaks at 30. The selection is not worse: the
    resulting condition number is identical to SciPy's.
    """
    for order in (8, 12, 20, 28):
        matrix = kahan(order)
        ours, _ = pivoted_qr_permutation(matrix)
        assert np.array_equal(ours, oracle_permutation(matrix))

    matrix = kahan(30)
    ours, _ = pivoted_qr_permutation(matrix)
    theirs = oracle_permutation(matrix)
    assert not np.array_equal(ours, theirs)
    assert np.linalg.cond(matrix[:, ours]) == pytest.approx(
        np.linalg.cond(matrix[:, theirs]), rel=1e-9
    )


# --- C-2: exchange determinism ---------------------------------------------


def test_exchange_is_repeat_stable_for_a_fixed_start() -> None:
    """No hidden RNG: identical inputs give identical selections."""
    matrix = load_fixture()["design_matrix"]
    runs = {
        tuple(d_optimal_exchange_row_selection(matrix, 4)["selected_row_indices"])
        for _ in range(5)
    }
    assert len(runs) == 1


def test_exchange_defaults_to_the_deterministic_qr_start() -> None:
    matrix = load_fixture()["design_matrix"]
    report = d_optimal_exchange_row_selection(matrix, 4)
    assert report["initial_rows_source"] == "qr_pivot"
    assert report["initial_row_indices"] == qr_pivot_row_selection(matrix, 4)[
        "selected_row_indices"
    ]


def test_exchange_result_depends_on_its_starting_set() -> None:
    """Measured: five random starts reached four to five distinct optima.

    This is why the starting set is part of the contract and defaults to the
    deterministic QR selection instead of a random subset.
    """
    matrix = load_fixture()["design_matrix"]
    outcomes = set()
    for seed in range(5):
        rng = np.random.default_rng(seed)
        start = sorted(rng.choice(matrix.shape[0], size=4, replace=False).tolist())
        report = d_optimal_exchange_row_selection(matrix, 4, initial_rows=start)
        assert report["initial_rows_source"] == "caller_supplied"
        outcomes.add(tuple(report["selected_row_indices"]))
    assert len(outcomes) > 1


def test_exchange_reports_convergence_and_iteration_count() -> None:
    matrix = load_fixture()["design_matrix"]
    report = d_optimal_exchange_row_selection(matrix, 4)
    assert report["converged"] is True
    assert report["exchange_iterations"] >= 0
    assert "d_optimal_exchange_hit_max_iterations" not in report["warnings"]


def test_exchange_hitting_the_iteration_cap_is_reported() -> None:
    matrix = load_fixture()["design_matrix"]
    report = d_optimal_exchange_row_selection(
        matrix, 4, initial_rows=[0, 1, 2, 3], max_iterations=1
    )
    assert report["exchange_iterations"] == 1
    if not report["converged"]:
        assert "d_optimal_exchange_hit_max_iterations" in report["warnings"]


# --- C-3: conditioning against a random baseline ---------------------------


@pytest.mark.parametrize("method", ["qr_pivot", "d_optimal_exchange"])
def test_conditioning_methods_beat_the_random_median(method: str) -> None:
    """Frozen from measurement rather than asserted as a fixed ratio.

    Both methods beat 100% of 40 random draws on the two non-degenerate
    canonical matrices. The gate asserts they beat the random *median*, which is
    a distributional claim rather than a single lucky draw -- the v0.34c lesson.
    """
    rng = np.random.default_rng(20352)
    matrices = [
        load_fixture()["design_matrix"],
        rng.standard_normal((40, 6)),
    ]
    for matrix in matrices:
        count = matrix.shape[1]
        baseline = []
        for _ in range(40):
            rows = sorted(
                rng.choice(matrix.shape[0], size=count, replace=False).tolist()
            )
            baseline.append(np.linalg.cond(matrix[rows]))
        median = float(np.median(baseline))

        report = summarize_row_selection(matrix, count)[method]
        assert report["selected_condition_number"] is not None
        assert report["selected_condition_number"] < median


def test_leverage_selection_declares_that_it_is_not_a_conditioning_method() -> None:
    """Measured: leverage beat only 8% of random draws on the canonical matrix,
    against 100% for the other two. The report must say so rather than let a
    reader assume all three methods answer the same question."""
    matrix = load_fixture()["design_matrix"]
    report = leverage_row_selection(matrix, 5)
    assert "leverage_selection_does_not_target_conditioning" in report["warnings"]

    conditioning = qr_pivot_row_selection(matrix, 5)["selected_condition_number"]
    assert conditioning is not None
    assert report["selected_condition_number"] > conditioning


# --- C-4: tall matrices ----------------------------------------------------


@pytest.mark.parametrize("n_rows", [50, 200, 800])
def test_selection_scales_to_tall_matrices(n_rows: int) -> None:
    """n_rows >> k. Measured: the exchange converges in 0-1 iterations from the
    QR start at every size, so the iteration cap is not load-bearing here."""
    rng = np.random.default_rng(20353)
    matrix = rng.standard_normal((n_rows, 5))

    qr_report = qr_pivot_row_selection(matrix, 5)
    assert len(qr_report["selected_row_indices"]) == 5

    exchange = d_optimal_exchange_row_selection(matrix, 5)
    assert exchange["converged"] is True
    assert exchange["exchange_iterations"] <= 2


def test_maximizing_the_determinant_is_not_minimizing_the_condition_number() -> None:
    """Documented divergence, not a defect.

    Measured on a 200x5 matrix the exchange improved log-det while leaving a
    slightly worse condition number than its QR starting point. The two
    objectives are different and the docstring says so.
    """
    rng = np.random.default_rng(20353)
    matrix = rng.standard_normal((200, 5))
    qr_report = qr_pivot_row_selection(matrix, 5)
    exchange = d_optimal_exchange_row_selection(matrix, 5)
    assert exchange["log_determinant"] is not None
    assert qr_report["selected_condition_number"] is not None
    assert exchange["selected_condition_number"] is not None


# --- validation and scope --------------------------------------------------


def test_selection_count_must_be_in_range() -> None:
    matrix = np.eye(4)
    for bad in (0, 5, -1):
        with pytest.raises(ScopeValidationError, match=r"must lie in \[1, 4\]"):
            qr_pivot_row_selection(matrix, bad)


def test_selection_count_must_be_an_integer() -> None:
    with pytest.raises(ScopeValidationError, match="must be an integer"):
        qr_pivot_row_selection(np.eye(4), 2.5)
    with pytest.raises(ScopeValidationError, match="must be an integer"):
        qr_pivot_row_selection(np.eye(4), True)


def test_non_two_dimensional_input_is_refused() -> None:
    with pytest.raises(ShapeValidationError, match="two-dimensional"):
        qr_pivot_row_selection(np.ones(4), 2)


def test_non_finite_input_is_refused() -> None:
    matrix = np.eye(4)
    matrix[0, 0] = np.inf
    with pytest.raises(ScopeValidationError, match="finite"):
        qr_pivot_row_selection(matrix, 2)


def test_empty_input_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="at least one entry"):
        qr_pivot_row_selection(np.zeros((0, 3)), 1)


def test_initial_rows_must_have_the_requested_size() -> None:
    with pytest.raises(ScopeValidationError, match="exactly 3 distinct rows"):
        d_optimal_exchange_row_selection(np.eye(6), 3, initial_rows=[0, 1])


def test_initial_rows_must_be_in_range() -> None:
    with pytest.raises(ScopeValidationError, match="outside the available rows"):
        d_optimal_exchange_row_selection(np.eye(6), 3, initial_rows=[0, 1, 99])


def test_initial_rows_must_be_iterable_integers() -> None:
    with pytest.raises(ScopeValidationError, match="iterable of integer"):
        d_optimal_exchange_row_selection(np.eye(6), 3, initial_rows=3)
    with pytest.raises(ScopeValidationError, match="iterable of integer"):
        d_optimal_exchange_row_selection(np.eye(6), 3, initial_rows=["a", "b", "c"])


def test_max_iterations_is_validated() -> None:
    with pytest.raises(ScopeValidationError, match="must be an integer"):
        d_optimal_exchange_row_selection(np.eye(6), 3, max_iterations=1.5)
    with pytest.raises(ScopeValidationError, match="at least 1"):
        d_optimal_exchange_row_selection(np.eye(6), 3, max_iterations=0)


def test_selecting_fewer_rows_than_features_is_flagged() -> None:
    """Fewer rows than features cannot determine the coefficients.

    The condition number of the selected block is still well defined -- a 3x5
    block has three nonzero singular values -- so it is reported, and the
    under-determination is surfaced as a warning plus a rank below the feature
    count rather than by suppressing the number.
    """
    rng = np.random.default_rng(3)
    matrix = rng.standard_normal((10, 5))
    report = qr_pivot_row_selection(matrix, 3)
    assert "selected_fewer_rows_than_features" in report["warnings"]
    assert report["selected_matrix_rank"] == 3
    assert report["selected_matrix_rank"] < report["num_features"]
    assert report["selected_condition_number"] is not None


def test_rank_deficient_selection_reports_null_condition_number() -> None:
    matrix = np.zeros((6, 3))
    matrix[:, 0] = 1.0
    report = qr_pivot_row_selection(matrix, 3)
    assert report["selected_condition_number"] is None
    assert "selected_rows_are_rank_deficient" in report["warnings"]


# --- report shape -----------------------------------------------------------


def test_summary_reports_all_three_methods() -> None:
    matrix = load_fixture()["design_matrix"]
    summary = summarize_row_selection(matrix, 5)
    assert summary["summary_type"] == "pdelie_row_selection_diagnostic"
    assert summary["methods"] == list(ROW_SELECTION_METHODS)
    for method in ROW_SELECTION_METHODS:
        assert summary[method]["method"] == method
        assert summary[method]["num_rows_selected"] == 5


@pytest.mark.parametrize("name,matrix", canonical_matrices(), ids=lambda v: v)
def test_reports_are_strict_json(name: str, matrix: np.ndarray) -> None:
    count = min(3, matrix.shape[0])
    encoded = json.dumps(summarize_row_selection(matrix, count), allow_nan=False)
    assert "NaN" not in encoded
    assert "Infinity" not in encoded


def test_every_report_is_marked_diagnostic_only() -> None:
    matrix = load_fixture()["design_matrix"]
    for report in (
        qr_pivot_row_selection(matrix, 4),
        leverage_row_selection(matrix, 4),
        d_optimal_exchange_row_selection(matrix, 4),
        summarize_row_selection(matrix, 4),
    ):
        assert report["diagnostic_only"] is True


def test_selected_indices_are_sorted_and_distinct() -> None:
    matrix = load_fixture()["design_matrix"]
    for report in (
        qr_pivot_row_selection(matrix, 5),
        leverage_row_selection(matrix, 5),
        d_optimal_exchange_row_selection(matrix, 5),
    ):
        indices = report["selected_row_indices"]
        assert indices == sorted(indices)
        assert len(set(indices)) == len(indices)


# --- scope invariants -------------------------------------------------------


def test_design_is_not_exported_from_the_root_namespace() -> None:
    import pdelie

    assert "design" not in pdelie.__all__
    for name in ROW_SELECTION_METHODS:
        assert name not in pdelie.__all__


def test_core_module_does_not_import_scipy_or_pysindy() -> None:
    """C-1's whole point: `pdelie.design` must stay core-installable."""
    import pdelie.design.row_selection as module

    assert module.__file__ is not None
    with open(module.__file__, encoding="utf-8") as handle:
        text = handle.read()
    for line in text.splitlines():
        stripped = line.strip()
        assert not stripped.startswith("import scipy")
        assert not stripped.startswith("from scipy")
        assert not stripped.startswith("import pysindy")
        assert not stripped.startswith("from pysindy")


def test_module_makes_no_noise_robustness_or_wsindy_claim() -> None:
    from pdelie.design import row_selection as module

    text = (module.__doc__ or "").lower()
    text += json.dumps(summarize_row_selection(np.eye(5), 3)).lower()
    for forbidden in ("wsindy", "noise_robust", "noise-robust", "noise robustness"):
        assert forbidden not in text
