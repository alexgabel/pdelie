from __future__ import annotations

import math

import numpy as np
import pytest

from pdelie import SchemaValidationError
from pdelie.discovery import evaluate_discovery_recovery


def test_evaluate_discovery_recovery_is_deterministic_and_support_based() -> None:
    target_terms = {"u": 1.0, "u_x": -2.0}
    discovered_terms = {"u": 1.5, "u_x": -2.0}

    first = evaluate_discovery_recovery(target_terms, discovered_terms)
    second = evaluate_discovery_recovery(target_terms, discovered_terms)

    assert first == second
    assert first["classification"] == "exact"
    assert first["classification_basis"] == "support"
    assert first["support_exact_match"] is True
    assert first["target_support_terms"] == ["u", "u_x"]
    assert first["discovered_support_terms"] == ["u", "u_x"]
    assert first["equation_strings"] == {
        "target": "1*u - 2*u_x",
        "discovered": "1.5*u - 2*u_x",
    }
    assert first["coefficient_l2_error"] == pytest.approx(0.5)
    assert first["coefficient_linf_error"] == pytest.approx(0.5)


def test_evaluate_discovery_recovery_handles_partial_and_failed_support() -> None:
    partial = evaluate_discovery_recovery(
        {"u": 1.0, "u_x": 2.0},
        {"u_x": 2.0, "u_xx": 3.0},
    )
    failed = evaluate_discovery_recovery(
        {"u": 1.0},
        {"u_x": 2.0},
    )

    assert partial["classification"] == "partial"
    assert partial["support_true_positives"] == 1
    assert partial["support_false_positives"] == 1
    assert partial["support_false_negatives"] == 1
    assert partial["support_precision"] == pytest.approx(0.5)
    assert partial["support_recall"] == pytest.approx(0.5)
    assert partial["support_f1"] == pytest.approx(0.5)

    assert failed["classification"] == "failed"
    assert failed["support_true_positives"] == 0
    assert failed["support_precision"] == pytest.approx(0.0)
    assert failed["support_recall"] == pytest.approx(0.0)
    assert failed["support_f1"] == pytest.approx(0.0)


def test_evaluate_discovery_recovery_handles_empty_support_edge_cases() -> None:
    empty_exact = evaluate_discovery_recovery({}, {})
    empty_target = evaluate_discovery_recovery({}, {"u_x": 2.0})
    empty_discovered = evaluate_discovery_recovery({"u_x": 2.0}, {})

    assert empty_exact["classification"] == "exact"
    assert empty_exact["support_precision"] == pytest.approx(1.0)
    assert empty_exact["support_recall"] == pytest.approx(1.0)
    assert empty_exact["support_f1"] == pytest.approx(1.0)
    assert empty_exact["union_terms"] == []
    assert empty_exact["coefficient_l2_error"] == pytest.approx(0.0)
    assert empty_exact["coefficient_relative_l2_error"] == pytest.approx(0.0)
    assert empty_exact["coefficient_linf_error"] == pytest.approx(0.0)
    assert empty_exact["equation_strings"] == {"target": "0", "discovered": "0"}

    assert empty_target["classification"] == "failed"
    assert empty_discovered["classification"] == "failed"


def test_evaluate_discovery_recovery_excludes_terms_at_or_below_support_threshold() -> None:
    result = evaluate_discovery_recovery(
        {"a": 1e-9, "b": 1.0},
        {"b": 1.0, "c": 1e-8},
        support_epsilon=1e-8,
    )

    assert result["target_support_terms"] == ["b"]
    assert result["discovered_support_terms"] == ["b"]
    assert result["union_terms"] == ["a", "b", "c"]
    assert result["classification"] == "exact"
    assert result["equation_strings"]["target"] == "1*b"
    assert result["equation_strings"]["discovered"] == "1*b"


def test_evaluate_discovery_recovery_uses_union_terms_for_coefficient_errors() -> None:
    result = evaluate_discovery_recovery(
        {"a": 0.0, "b": 1.0},
        {"b": 1.0, "c": 2.0},
    )

    assert result["union_terms"] == ["a", "b", "c"]
    assert result["coefficient_l2_error"] == pytest.approx(2.0)
    assert result["coefficient_linf_error"] == pytest.approx(2.0)


def test_evaluate_discovery_recovery_keeps_relative_l2_formula_for_zero_target_norm() -> None:
    result = evaluate_discovery_recovery({}, {"u_x": 2.0})

    assert result["coefficient_relative_l2_error"] == pytest.approx(2.0 / 1e-12)


def test_evaluate_discovery_recovery_equation_strings_use_support_terms_only_and_lexicographic_order() -> None:
    result = evaluate_discovery_recovery(
        {"z": 0.5, "a": 1e-12, "b": -2.0},
        {"b": -2.0, "z": 0.5},
    )

    assert result["union_terms"] == ["a", "b", "z"]
    assert result["equation_strings"]["target"] == "-2*b + 0.5*z"
    assert result["equation_strings"]["discovered"] == "-2*b + 0.5*z"
    assert "a" not in result["equation_strings"]["target"]


def test_evaluate_discovery_recovery_summarizes_residuals_for_scalar_and_array_inputs() -> None:
    result = evaluate_discovery_recovery(
        {"u": 1.0},
        {"u": 1.0},
        train_residual=3.0,
        heldout_residual=np.array([3.0, 4.0]),
    )

    assert result["train_residual_l2"] == pytest.approx(3.0)
    assert result["heldout_residual_l2"] == pytest.approx(5.0)
    assert result["heldout_residual_rms"] == pytest.approx(5.0 / math.sqrt(2.0))


@pytest.mark.parametrize(
    ("target_terms", "discovered_terms", "match"),
    (
        ({}, {"": 1.0}, "term keys must be non-empty strings"),
        ({1: 1.0}, {}, "term keys must be non-empty strings"),
        ({"u": np.inf}, {}, "coefficients must be finite scalar values"),
        ({}, {"u": np.nan}, "coefficients must be finite scalar values"),
    ),
)
def test_evaluate_discovery_recovery_rejects_invalid_terms_and_coefficients(
    target_terms: object,
    discovered_terms: object,
    match: str,
) -> None:
    with pytest.raises(SchemaValidationError, match=match):
        evaluate_discovery_recovery(target_terms, discovered_terms)


@pytest.mark.parametrize("support_epsilon", (np.nan, -1.0, np.inf, "bad"))
def test_evaluate_discovery_recovery_rejects_invalid_support_epsilon(support_epsilon: object) -> None:
    with pytest.raises(SchemaValidationError, match="support_epsilon must be a finite non-negative scalar"):
        evaluate_discovery_recovery({"u": 1.0}, {"u": 1.0}, support_epsilon=support_epsilon)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    (
        ({"train_residual": []}, "train_residual must be non-empty after flattening"),
        ({"heldout_residual": []}, "heldout_residual must be non-empty after flattening"),
        ({"train_residual": [1.0, np.nan]}, "train_residual must contain only finite values"),
        ({"heldout_residual": [1.0, np.inf]}, "heldout_residual must contain only finite values"),
    ),
)
def test_evaluate_discovery_recovery_rejects_invalid_residual_inputs(
    kwargs: dict[str, object],
    match: str,
) -> None:
    with pytest.raises(SchemaValidationError, match=match):
        evaluate_discovery_recovery({"u": 1.0}, {"u": 1.0}, **kwargs)


@pytest.mark.parametrize("invalid_mapping", ([], 1.0, "u"))
def test_evaluate_discovery_recovery_requires_term_mappings(invalid_mapping: object) -> None:
    with pytest.raises(SchemaValidationError, match="must be a mapping of canonical term strings to scalar coefficients"):
        evaluate_discovery_recovery(invalid_mapping, {})
