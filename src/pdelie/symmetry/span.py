from __future__ import annotations

"""Runtime-only span diagnostics for canonical GeneratorFamily objects."""

from typing import Any, Mapping

import numpy as np

from pdelie.contracts import GeneratorFamily
from pdelie.errors import SchemaValidationError, ShapeValidationError


_SUPPORTED_INNER_PRODUCTS = frozenset({"normalized_polynomial_l2"})
_RANK_TOL = 1e-10
_GRAM_EIGEN_TOL = 1e-12


def _basis_spec_signature(basis_spec: Mapping[str, Any]) -> tuple[Any, ...]:
    basis_terms = tuple(
        (str(term["label"]), tuple(int(power) for power in term["powers"]))
        for term in basis_spec["basis_terms"]
    )
    return (
        tuple(str(name) for name in basis_spec["variables"]),
        tuple(str(name) for name in basis_spec["component_names"]),
        tuple(str(name) for name in basis_spec["component_ordering"]),
        tuple(str(name) for name in basis_spec["term_ordering"]),
        str(basis_spec["layout"]),
        basis_terms,
    )


def _require_structurally_equivalent_basis_spec(
    reference: GeneratorFamily,
    candidate: GeneratorFamily,
) -> None:
    if _basis_spec_signature(reference.basis_spec) != _basis_spec_signature(candidate.basis_spec):
        raise SchemaValidationError(
            "compare_generator_spans requires structurally equivalent basis_spec semantics."
        )


def _monomial_average_inner_product(powers_a: tuple[int, ...], powers_b: tuple[int, ...]) -> float:
    value = 1.0
    for power_a, power_b in zip(powers_a, powers_b):
        total_power = int(power_a) + int(power_b)
        if total_power % 2 == 1:
            return 0.0
        value *= 1.0 / float(total_power + 1)
    return value


def _basis_term_gram_matrix(generator: GeneratorFamily) -> np.ndarray:
    basis_terms = [
        tuple(int(power) for power in term["powers"])
        for term in generator.basis_spec["basis_terms"]
    ]
    size = len(basis_terms)
    gram = np.empty((size, size), dtype=float)
    for row_index, powers_a in enumerate(basis_terms):
        for col_index, powers_b in enumerate(basis_terms):
            gram[row_index, col_index] = _monomial_average_inner_product(powers_a, powers_b)
    return gram


def _ambient_gram_matrix(generator: GeneratorFamily) -> tuple[np.ndarray, dict[str, float]]:
    num_components = len(generator.basis_spec["component_names"])
    term_gram = _basis_term_gram_matrix(generator)
    component_weights = {str(name): 1.0 for name in generator.basis_spec["component_names"]}
    block_weights = np.diag([component_weights[str(name)] for name in generator.basis_spec["component_names"]])
    ambient_gram = np.kron(block_weights, term_gram)
    return ambient_gram, component_weights


def _condition_number_from_values(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return float("inf")
    positive = values[values > 0.0]
    if positive.size == 0:
        return float("inf")
    minimum = float(np.min(positive))
    maximum = float(np.max(positive))
    if minimum == 0.0:
        return float("inf")
    return maximum / minimum


def _metric_transform(ambient_gram: np.ndarray) -> tuple[np.ndarray, float]:
    eigenvalues, eigenvectors = np.linalg.eigh(np.asarray(ambient_gram, dtype=float))
    max_abs_eigenvalue = float(np.max(np.abs(eigenvalues))) if eigenvalues.size else 0.0
    floor = max(_GRAM_EIGEN_TOL * max_abs_eigenvalue, _GRAM_EIGEN_TOL)
    adjusted = np.where(np.abs(eigenvalues) <= floor, 0.0, eigenvalues)
    if np.any(adjusted < 0.0):
        raise ShapeValidationError("Span comparison ambient Gram matrix must be positive semidefinite.")
    positive_mask = adjusted > 0.0
    transform = eigenvectors[:, positive_mask] * np.sqrt(adjusted[positive_mask])[None, :]
    condition_number = _condition_number_from_values(adjusted[positive_mask])
    return transform, condition_number


def _orthonormal_row_span(matrix: np.ndarray) -> tuple[np.ndarray, int, float]:
    _, singular_values, vh = np.linalg.svd(np.asarray(matrix, dtype=float), full_matrices=False)
    if singular_values.size == 0:
        return np.empty((0, matrix.shape[1]), dtype=float), 0, float("inf")
    threshold = max(float(singular_values[0]) * _RANK_TOL, _RANK_TOL)
    rank = int(np.count_nonzero(singular_values > threshold))
    if rank == 0:
        return np.empty((0, matrix.shape[1]), dtype=float), 0, float("inf")
    retained = singular_values[:rank]
    return vh[:rank], rank, _condition_number_from_values(retained)


def _projection_residual(source_basis: np.ndarray, target_basis: np.ndarray) -> float:
    projector = target_basis.T @ target_basis
    residual = source_basis - source_basis @ projector
    return float(np.linalg.norm(residual, ord="fro") / np.sqrt(float(source_basis.shape[0])))


def compare_generator_spans(
    reference: GeneratorFamily,
    candidate: GeneratorFamily,
    *,
    inner_product: str = "normalized_polynomial_l2",
) -> dict[str, object]:
    """Compare generator-family row spans under the frozen M3 polynomial inner product.

    Raises:
        SchemaValidationError: for unsupported inner products or non-equivalent basis semantics.
        ShapeValidationError: if either effective span has zero numerical rank.
    """

    reference.validate()
    candidate.validate()

    if inner_product not in _SUPPORTED_INNER_PRODUCTS:
        raise SchemaValidationError(
            "compare_generator_spans only supports inner_product='normalized_polynomial_l2' in V0.4 Milestone 3."
        )

    _require_structurally_equivalent_basis_spec(reference, candidate)

    ambient_gram, component_weights = _ambient_gram_matrix(reference)
    transform, ambient_condition_number = _metric_transform(ambient_gram)

    reference_transformed = np.asarray(reference.coefficients, dtype=float) @ transform
    candidate_transformed = np.asarray(candidate.coefficients, dtype=float) @ transform

    reference_basis, reference_rank, reference_condition = _orthonormal_row_span(reference_transformed)
    candidate_basis, candidate_rank, candidate_condition = _orthonormal_row_span(candidate_transformed)

    if reference_rank == 0 or candidate_rank == 0:
        raise ShapeValidationError("compare_generator_spans requires both generator families to have nonzero rank.")

    comparison_rank = min(reference_rank, candidate_rank)
    singular_values = np.linalg.svd(reference_basis @ candidate_basis.T, compute_uv=False)
    principal_angles = np.arccos(np.clip(singular_values[:comparison_rank], -1.0, 1.0))

    reference_to_candidate = _projection_residual(reference_basis, candidate_basis)
    candidate_to_reference = _projection_residual(candidate_basis, reference_basis)

    return {
        "inner_product": inner_product,
        "evaluation_mode": "exact_polynomial",
        "domain": {
            "kind": "normalized_hypercube",
            "variables": list(reference.basis_spec["variables"]),
            "bounds": [[-1.0, 1.0] for _ in reference.basis_spec["variables"]],
        },
        "component_weights": component_weights,
        "reference_rank": reference_rank,
        "candidate_rank": candidate_rank,
        "comparison_rank": comparison_rank,
        "principal_angles_radians": principal_angles.tolist(),
        "projection_residual": {
            "summary": float(max(reference_to_candidate, candidate_to_reference)),
            "reference_to_candidate": reference_to_candidate,
            "candidate_to_reference": candidate_to_reference,
        },
        "conditioning": {
            "ambient_metric": ambient_condition_number,
            "reference_span": reference_condition,
            "candidate_span": candidate_condition,
        },
    }


__all__ = ["compare_generator_spans"]
