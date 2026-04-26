from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from pdelie.errors import SchemaValidationError


def _validate_support_epsilon(support_epsilon: object) -> float:
    try:
        epsilon = float(support_epsilon)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError("support_epsilon must be a finite non-negative scalar.") from exc
    if not np.isfinite(epsilon) or epsilon < 0.0:
        raise SchemaValidationError("support_epsilon must be a finite non-negative scalar.")
    return epsilon


def _validate_term_mapping(name: str, value: object) -> dict[str, float]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{name} must be a mapping of canonical term strings to scalar coefficients.")

    normalized: dict[str, float] = {}
    for term, coefficient in value.items():
        if not isinstance(term, str) or not term:
            raise SchemaValidationError(f"{name} term keys must be non-empty strings.")
        try:
            coefficient_value = float(coefficient)
        except (TypeError, ValueError) as exc:
            raise SchemaValidationError(f"{name} coefficients must be finite scalar values.") from exc
        if not np.isfinite(coefficient_value):
            raise SchemaValidationError(f"{name} coefficients must be finite scalar values.")
        normalized[term] = coefficient_value
    return normalized


def _coerce_residual(name: str, residual: object) -> np.ndarray:
    try:
        array = np.asarray(residual, dtype=float).reshape(-1)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{name} must be a finite numeric scalar or array-like.") from exc
    if array.size == 0:
        raise SchemaValidationError(f"{name} must be non-empty after flattening.")
    if not np.all(np.isfinite(array)):
        raise SchemaValidationError(f"{name} must contain only finite values.")
    return array


def _support_terms(terms: Mapping[str, float], support_epsilon: float) -> list[str]:
    return sorted(term for term, coefficient in terms.items() if abs(coefficient) > support_epsilon)


def _safe_precision_recall_f1(
    target_support: set[str],
    discovered_support: set[str],
    true_positives: int,
) -> tuple[float, float, float]:
    if not target_support and not discovered_support:
        return 1.0, 1.0, 1.0

    precision = float(true_positives / len(discovered_support)) if discovered_support else 0.0
    recall = float(true_positives / len(target_support)) if target_support else 0.0
    if precision + recall == 0.0:
        return precision, recall, 0.0
    return precision, recall, float((2.0 * precision * recall) / (precision + recall))


def _equation_string(terms: Mapping[str, float], support_terms: list[str]) -> str:
    if not support_terms:
        return "0"

    parts: list[str] = []
    for index, term in enumerate(support_terms):
        coefficient = float(terms[term])
        if index == 0:
            parts.append(f"{coefficient:.12g}*{term}")
            continue
        if coefficient < 0.0:
            parts.append(f"- {abs(coefficient):.12g}*{term}")
        else:
            parts.append(f"+ {coefficient:.12g}*{term}")
    return " ".join(parts)


def evaluate_discovery_recovery(
    target_terms: object,
    discovered_terms: object,
    *,
    support_epsilon: float = 1e-8,
    train_residual: object | None = None,
    heldout_residual: object | None = None,
) -> dict[str, object]:
    epsilon = _validate_support_epsilon(support_epsilon)
    normalized_target = _validate_term_mapping("target_terms", target_terms)
    normalized_discovered = _validate_term_mapping("discovered_terms", discovered_terms)

    target_support_terms = _support_terms(normalized_target, epsilon)
    discovered_support_terms = _support_terms(normalized_discovered, epsilon)
    union_terms = sorted(set(normalized_target) | set(normalized_discovered))

    target_support = set(target_support_terms)
    discovered_support = set(discovered_support_terms)
    true_positives = len(target_support & discovered_support)
    false_positives = len(discovered_support - target_support)
    false_negatives = len(target_support - discovered_support)

    if target_support == discovered_support:
        classification = "exact"
    elif true_positives > 0:
        classification = "partial"
    else:
        classification = "failed"

    precision, recall, f1 = _safe_precision_recall_f1(target_support, discovered_support, true_positives)

    target_vector = np.asarray([normalized_target.get(term, 0.0) for term in union_terms], dtype=float)
    discovered_vector = np.asarray([normalized_discovered.get(term, 0.0) for term in union_terms], dtype=float)
    difference = discovered_vector - target_vector

    coefficient_l2_error = float(np.linalg.norm(difference))
    target_norm = float(np.linalg.norm(target_vector))
    coefficient_relative_l2_error = float(coefficient_l2_error / (target_norm + 1e-12))
    coefficient_linf_error = 0.0 if difference.size == 0 else float(np.max(np.abs(difference)))

    result: dict[str, object] = {
        "support_epsilon": epsilon,
        "classification": classification,
        "classification_basis": "support",
        "target_support_terms": target_support_terms,
        "discovered_support_terms": discovered_support_terms,
        "union_terms": union_terms,
        "support_true_positives": true_positives,
        "support_false_positives": false_positives,
        "support_false_negatives": false_negatives,
        "support_precision": precision,
        "support_recall": recall,
        "support_f1": f1,
        "support_exact_match": target_support == discovered_support,
        "target_sparsity": len(target_support_terms),
        "discovered_sparsity": len(discovered_support_terms),
        "coefficient_l2_error": coefficient_l2_error,
        "coefficient_relative_l2_error": coefficient_relative_l2_error,
        "coefficient_linf_error": coefficient_linf_error,
        "equation_strings": {
            "target": _equation_string(normalized_target, target_support_terms),
            "discovered": _equation_string(normalized_discovered, discovered_support_terms),
        },
    }

    if train_residual is not None:
        train_residual_array = _coerce_residual("train_residual", train_residual)
        result["train_residual_l2"] = float(np.linalg.norm(train_residual_array))

    if heldout_residual is not None:
        heldout_residual_array = _coerce_residual("heldout_residual", heldout_residual)
        heldout_residual_l2 = float(np.linalg.norm(heldout_residual_array))
        result["heldout_residual_l2"] = heldout_residual_l2
        result["heldout_residual_rms"] = float(heldout_residual_l2 / np.sqrt(float(heldout_residual_array.size)))

    return result
