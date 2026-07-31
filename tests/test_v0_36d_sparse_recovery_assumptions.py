"""v0.36d: theoretical sparse-recovery assumption report.

References are hand-computed, not read off the implementation. Tolerances come
from the v0.36d pilot and are recorded in
``docs/planning/V0_36D_SPARSE_RECOVERY_FREEZE.md``.
"""

from __future__ import annotations

import ast
import itertools
import json
from pathlib import Path

import numpy as np
import pytest

from pdelie.diagnostics.sparse_recovery import (
    ACTIVE_SUPPORT_CONDITION_LIMIT,
    IRREPRESENTABILITY_THRESHOLD,
    SPARSE_RECOVERY_STATUSES,
    sparse_recovery_assumption_report,
)
from pdelie.errors import ScopeValidationError, ShapeValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Set by the pilot. Two of the three references are analytically zero, so a
#: relative tolerance compares nothing; the worst measured deviation from the
#: analytic value is 1.388e-16, four orders inside this bound.
REFERENCE_ATOL = 1e-12

#: The forbidden vocabulary. A diagnostic that says "recoverable" has made a
#: claim about an algorithm it never ran.
FORBIDDEN = (
    "recoverable",
    "not_recoverable",
    "recovery_guaranteed",
    "recovery_impossible",
    "ell1_recoverable",
    "ell1_not_recoverable",
)


def orthonormal_8x4() -> np.ndarray:
    rng = np.random.default_rng(20350)
    return np.linalg.qr(rng.standard_normal((8, 4)))[0]


def correlated_4x3() -> np.ndarray:
    """Off-support column 2 correlates 0.6 with column 0 after normalization."""
    return np.array(
        [[1.0, 0.0, 0.6], [0.0, 1.0, 0.0], [0.0, 0.0, 0.8], [0.0, 0.0, 0.0]]
    )


def sign_sensitive_4x3() -> np.ndarray:
    """The matrix on which signed and uniform measurably disagree."""
    return np.array(
        [[1.0, 0.0, 0.9], [0.0, 1.0, 0.9], [0.0, 0.0, 0.2], [0.5, -0.5, 0.0]]
    )


def entry(report: dict, index: int = 0) -> dict:
    return report["supports"][index]


# --- hand-computed references ----------------------------------------------


def test_identity_gives_exactly_zero_for_both_constants() -> None:
    """Orthogonal columns: no off-support column has any correlation with the support."""
    report = sparse_recovery_assumption_report(
        np.eye(4), candidate_supports=[[0, 1]], sign_patterns=[[1, 1]]
    )
    result = entry(report)
    assert result["rho_signed"] == pytest.approx(0.0, abs=REFERENCE_ATOL)
    assert result["rho_uniform"] == pytest.approx(0.0, abs=REFERENCE_ATOL)


def test_orthonormal_design_gives_zero_within_machine_epsilon() -> None:
    report = sparse_recovery_assumption_report(
        orthonormal_8x4(), candidate_supports=[[0, 1]], sign_patterns=[[1, 1]]
    )
    result = entry(report)
    assert result["rho_signed"] == pytest.approx(0.0, abs=REFERENCE_ATOL)
    assert result["rho_uniform"] == pytest.approx(0.0, abs=REFERENCE_ATOL)


def test_correlated_matrix_reproduces_the_hand_computed_zero_point_six() -> None:
    """0.6 is the off-support correlation, computable by hand from the matrix."""
    report = sparse_recovery_assumption_report(
        correlated_4x3(), candidate_supports=[[0]], sign_patterns=[[1]]
    )
    result = entry(report)
    assert result["rho_signed"] == pytest.approx(0.6, abs=REFERENCE_ATOL)
    assert result["rho_uniform"] == pytest.approx(0.6, abs=REFERENCE_ATOL)


def test_uniform_equals_the_brute_force_maximum_over_sign_patterns() -> None:
    """The two definitions must agree; computed independently here."""
    matrix = sign_sensitive_4x3()
    support = [0, 1]
    uniform = entry(
        sparse_recovery_assumption_report(matrix, candidate_supports=[support])
    )["rho_uniform"]

    brute = 0.0
    for signs in itertools.product([1, -1], repeat=len(support)):
        value = entry(
            sparse_recovery_assumption_report(
                matrix, candidate_supports=[support], sign_patterns=[list(signs)]
            )
        )["rho_signed"]
        brute = max(brute, value)
    assert uniform == pytest.approx(brute, abs=REFERENCE_ATOL)


# --- signed vs uniform is a real distinction --------------------------------


def test_signed_and_uniform_differ_where_the_sign_pattern_matters() -> None:
    """Measured by the pilot: [+,+] gives 1.562, [+,-] gives ~0.

    The sign pattern moves the constant across the threshold, so the two
    statuses are genuinely two statuses.
    """
    matrix = sign_sensitive_4x3()
    plus_plus = entry(
        sparse_recovery_assumption_report(
            matrix, candidate_supports=[[0, 1]], sign_patterns=[[1, 1]]
        )
    )
    plus_minus = entry(
        sparse_recovery_assumption_report(
            matrix, candidate_supports=[[0, 1]], sign_patterns=[[1, -1]]
        )
    )
    assert plus_plus["rho_signed"] == pytest.approx(1.56197280263, rel=1e-9)
    assert plus_minus["rho_signed"] == pytest.approx(0.0, abs=1e-9)
    assert plus_plus["rho_signed"] != pytest.approx(plus_minus["rho_signed"])

    assert "lasso_sign_consistency_condition_violated" in plus_plus["statuses"]
    assert "lasso_sign_consistency_condition_satisfied" in plus_minus["statuses"]


def test_uniform_is_at_least_every_signed_value() -> None:
    matrix = sign_sensitive_4x3()
    uniform = entry(
        sparse_recovery_assumption_report(matrix, candidate_supports=[[0, 1]])
    )["rho_uniform"]
    for signs in itertools.product([1, -1], repeat=2):
        signed = entry(
            sparse_recovery_assumption_report(
                matrix, candidate_supports=[[0, 1]], sign_patterns=[list(signs)]
            )
        )["rho_signed"]
        assert uniform >= signed - 1e-12


def test_missing_sign_pattern_reports_unavailable_and_leans_on_uniform() -> None:
    report = sparse_recovery_assumption_report(
        sign_sensitive_4x3(), candidate_supports=[[0, 1]]
    )
    result = entry(report)
    assert result["rho_signed"] is None
    assert result["rho_signed_available"] is False
    assert "sign_pattern_unavailable" in result["statuses"]
    assert "uniform_bound_is_the_only_actionable_statistic" in result["warnings"]
    assert result["rho_uniform_available"] is True


# --- degenerate supports ----------------------------------------------------


def test_rank_deficient_support_is_undefined_not_a_plausible_number() -> None:
    """v0.35a measured lstsq silently returning 0.4956551696 from such a system."""
    duplicate = np.array(
        [[1.0, 1.0, 0.3], [2.0, 2.0, 0.1], [3.0, 3.0, 0.7], [0.0, 0.0, 1.0]]
    )
    result = entry(
        sparse_recovery_assumption_report(
            duplicate, candidate_supports=[[0, 1]], sign_patterns=[[1, 1]]
        )
    )
    assert result["rho_signed"] is None
    assert result["rho_uniform"] is None
    assert "undefined_singular_support" in result["statuses"]
    assert "active_support_is_rank_deficient" in result["warnings"]
    assert result["active_support_rank"] == 1


def test_support_covering_every_column_has_no_condition_to_evaluate() -> None:
    result = entry(
        sparse_recovery_assumption_report(np.eye(4), candidate_supports=[[0, 1, 2, 3]])
    )
    assert result["statuses"] == ["insufficient_assumptions_for_recovery_claim"]
    assert result["off_support_size"] == 0
    assert result["rho_uniform"] is None


def test_the_conditioning_limit_sits_in_an_empty_gap() -> None:
    """Pilot: real supports reach 20.85; exact singularity sits at 1.39e17."""
    assert ACTIVE_SUPPORT_CONDITION_LIMIT == 1e12
    from tests._helpers.regenerate_v0_35a_design_matrix import load_fixture

    matrix = load_fixture()["design_matrix"]
    worst = 0.0
    for i in range(matrix.shape[1]):
        for j in range(i + 1, matrix.shape[1]):
            result = entry(
                sparse_recovery_assumption_report(matrix, candidate_supports=[[i, j]])
            )
            worst = max(worst, result["active_support_gram_condition_number"])
    assert worst < 1e3, worst
    assert worst < ACTIVE_SUPPORT_CONDITION_LIMIT / 1e9


def test_threshold_is_the_theorem_threshold_not_a_tunable() -> None:
    assert IRREPRESENTABILITY_THRESHOLD == 1.0


# --- forbidden vocabulary ---------------------------------------------------


def _code_surface(path: Path) -> str:
    """Identifiers and runtime string literals, excluding docstrings and comments.

    Two amendments to the plan's version of this scan, both forced by contact
    with the code:

    1. The plan iterates ``Path("...sparse_recovery.py").iterdir()``. ``iterdir()``
       on a *file* raises ``NotADirectoryError``, so the loop body would never
       run and the test would pass vacuously while asserting nothing.

    2. A flat text scan flags the module docstring, which explains *why* the
       vocabulary is refused. That is the third time this pattern has appeared
       in this repository -- the WSINDy disclaimers found at v0.36 day-zero, the
       "perfectly recoverable" comment in ``design_matrix.py``, and now this.
       The constraint is about what a module **claims**, not what it **mentions**;
       prose that explains a refusal is the opposite of a violation.

    So the scan covers the surface that can actually reach a caller: identifier
    names and non-docstring string literals.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = {
        node.body[0].value
        for node in ast.walk(tree)
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    }
    parts: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node not in docstrings:
                parts.append(node.value)
        elif isinstance(node, ast.Name):
            parts.append(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            parts.append(node.name)
        elif isinstance(node, ast.Attribute):
            parts.append(node.attr)
        elif isinstance(node, ast.arg):
            parts.append(node.arg)
    return "\n".join(parts).lower()


def test_no_forbidden_recovery_vocabulary_in_the_code_surface() -> None:
    path = REPO_ROOT / "src/pdelie/diagnostics/sparse_recovery.py"
    surface = _code_surface(path)
    for forbidden in FORBIDDEN:
        assert forbidden not in surface, (
            f"forbidden recovery vocabulary {forbidden!r} reaches the code surface "
            f"of {path.name}. Use theorem-specific status names instead."
        )


def test_the_code_surface_scan_would_catch_a_real_violation() -> None:
    """A guard that cannot fail is the defect it is meant to prevent."""
    import tempfile

    planted = (
        '"""A docstring that merely mentions recovery_guaranteed is fine."""\n'
        'STATUS = "recovery_guaranteed"\n'
    )
    innocent = '"""Explains why recovery_guaranteed is never claimed."""\nSTATUS = "ok"\n'
    with tempfile.TemporaryDirectory() as directory:
        bad = Path(directory) / "bad.py"
        bad.write_text(planted, encoding="utf-8")
        good = Path(directory) / "good.py"
        good.write_text(innocent, encoding="utf-8")
        assert "recovery_guaranteed" in _code_surface(bad)
        assert "recovery_guaranteed" not in _code_surface(good)


def test_no_forbidden_recovery_vocabulary_in_emitted_report() -> None:
    report = sparse_recovery_assumption_report(
        correlated_4x3(), candidate_supports=[[0]], sign_patterns=[[1]]
    )
    encoded = json.dumps(report, allow_nan=False).lower()
    for forbidden in FORBIDDEN:
        assert forbidden not in encoded


def test_every_status_name_is_theorem_specific() -> None:
    for status in SPARSE_RECOVERY_STATUSES:
        for forbidden in FORBIDDEN:
            assert forbidden not in status


# --- report shape -----------------------------------------------------------


def test_report_is_strict_json_and_fully_populated() -> None:
    report = sparse_recovery_assumption_report(
        correlated_4x3(), candidate_supports=[[0], [1]], sign_patterns=[[1], None]
    )
    encoded = json.dumps(report, allow_nan=False)
    assert "NaN" not in encoded and "Infinity" not in encoded

    required = {
        "summary_type", "schema_version", "num_rows", "num_features",
        "normalization_policy", "restricted_eigenvalue_definition",
        "irrepresentability_threshold", "active_support_condition_limit",
        "candidate_support_count", "sign_patterns_supplied", "zero_column_count",
        "supports", "status_vocabulary", "warnings", "diagnostic_only",
    }
    assert required <= set(report)
    for result in report["supports"]:
        assert {
            "support", "support_size", "off_support_size", "rho_signed",
            "rho_signed_available", "rho_uniform", "rho_uniform_available",
            "active_support_min_singular_value", "active_support_rank",
            "active_support_gram_condition_number", "statuses", "warnings",
        } <= set(result)


def test_availability_flags_track_the_values() -> None:
    report = sparse_recovery_assumption_report(
        correlated_4x3(), candidate_supports=[[0]], sign_patterns=[None]
    )
    result = entry(report)
    assert result["rho_signed_available"] is (result["rho_signed"] is not None)
    assert result["rho_uniform_available"] is (result["rho_uniform"] is not None)


def test_the_shipped_v0_35a_definition_is_not_redefined() -> None:
    """v0.35a's restricted_eigenvalue keeps its name and meaning."""
    from pdelie.diagnostics.design_matrix import RESTRICTED_EIGENVALUE_DEFINITION

    assert RESTRICTED_EIGENVALUE_DEFINITION == "support_restricted_min_gram_eigenvalue_over_n"
    report = sparse_recovery_assumption_report(np.eye(4), candidate_supports=[[0, 1]])
    assert report["restricted_eigenvalue_definition"] == "active_support_min_singular_value"


# --- validation -------------------------------------------------------------


def test_sampled_re_lower_bound_is_reserved_not_silently_wrong() -> None:
    with pytest.raises(ScopeValidationError, match="reserved and not implemented"):
        sparse_recovery_assumption_report(
            np.eye(4),
            candidate_supports=[[0, 1]],
            restricted_eigenvalue_definition="sampled_re_lower_bound",
        )


def test_empty_and_malformed_supports_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="must be non-empty"):
        sparse_recovery_assumption_report(np.eye(4), candidate_supports=[])
    with pytest.raises(ScopeValidationError, match="is empty"):
        sparse_recovery_assumption_report(np.eye(4), candidate_supports=[[]])
    with pytest.raises(ScopeValidationError, match="repeats"):
        sparse_recovery_assumption_report(np.eye(4), candidate_supports=[[0, 0]])
    with pytest.raises(ScopeValidationError, match="outside"):
        sparse_recovery_assumption_report(np.eye(4), candidate_supports=[[0, 9]])


def test_sign_pattern_shape_and_values_are_validated() -> None:
    with pytest.raises(ShapeValidationError, match="expected"):
        sparse_recovery_assumption_report(
            np.eye(4), candidate_supports=[[0, 1]], sign_patterns=[[1]]
        )
    with pytest.raises(ScopeValidationError, match=r"only \+1 and -1"):
        sparse_recovery_assumption_report(
            np.eye(4), candidate_supports=[[0, 1]], sign_patterns=[[1, 0]]
        )
    with pytest.raises(ScopeValidationError, match="positional"):
        sparse_recovery_assumption_report(
            np.eye(4), candidate_supports=[[0, 1]], sign_patterns=[[1, 1], [1, 1]]
        )


def test_invalid_matrix_and_policy_are_refused() -> None:
    with pytest.raises(ShapeValidationError, match="two-dimensional"):
        sparse_recovery_assumption_report(np.ones(4), candidate_supports=[[0]])
    bad = np.eye(4)
    bad[0, 0] = np.nan
    with pytest.raises(ScopeValidationError, match="finite"):
        sparse_recovery_assumption_report(bad, candidate_supports=[[0]])
    with pytest.raises(ScopeValidationError, match="normalization_policy"):
        sparse_recovery_assumption_report(
            np.eye(4), candidate_supports=[[0]], normalization_policy="whatever"
        )


def test_not_exported_from_the_root_namespace() -> None:
    import pdelie

    for name in ("sparse_recovery_assumption_report", "empirical_support_stability_report"):
        assert name not in pdelie.__all__
        assert not hasattr(pdelie, name)


def test_empty_and_malformed_matrix_inputs_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="at least one entry"):
        sparse_recovery_assumption_report(np.zeros((0, 3)), candidate_supports=[[0]])


def test_non_sequence_supports_and_patterns_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="sequence of supports"):
        sparse_recovery_assumption_report(np.eye(4), candidate_supports=3)
    with pytest.raises(ScopeValidationError, match="sequence of column indices"):
        sparse_recovery_assumption_report(np.eye(4), candidate_supports=[3])
    with pytest.raises(ScopeValidationError, match="must contain integers"):
        sparse_recovery_assumption_report(np.eye(4), candidate_supports=[["a"]])
    with pytest.raises(ScopeValidationError, match="sequence or None"):
        sparse_recovery_assumption_report(
            np.eye(4), candidate_supports=[[0]], sign_patterns=3
        )
    with pytest.raises(ScopeValidationError, match=r"\+1/-1 values or None"):
        sparse_recovery_assumption_report(
            np.eye(4), candidate_supports=[[0]], sign_patterns=[3]
        )


def test_normalization_policy_none_is_honoured() -> None:
    """With 'none', the raw matrix is used and the report says so."""
    scaled = correlated_4x3() * 1000.0
    normalized = sparse_recovery_assumption_report(
        scaled, candidate_supports=[[0]], normalization_policy="column_l2"
    )
    raw = sparse_recovery_assumption_report(
        scaled, candidate_supports=[[0]], normalization_policy="none"
    )
    assert normalized["normalization_policy"] == "column_l2"
    assert raw["normalization_policy"] == "none"
    assert entry(normalized)["rho_uniform"] == pytest.approx(0.6, abs=REFERENCE_ATOL)


def test_zero_columns_are_counted_and_warned() -> None:
    matrix = np.eye(4)
    matrix[:, 2] = 0.0
    report = sparse_recovery_assumption_report(matrix, candidate_supports=[[0, 1]])
    assert report["zero_column_count"] == 1
    assert "design_matrix_contains_zero_columns" in report["warnings"]


def test_multiple_supports_are_reported_independently() -> None:
    report = sparse_recovery_assumption_report(
        sign_sensitive_4x3(),
        candidate_supports=[[0], [0, 1], [1]],
        sign_patterns=[[1], [1, 1], None],
    )
    assert report["candidate_support_count"] == 3
    assert [item["support"] for item in report["supports"]] == [[0], [0, 1], [1]]
    assert report["supports"][2]["rho_signed"] is None
