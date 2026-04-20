from __future__ import annotations

"""Runtime-only closure diagnostics for canonical GeneratorFamily objects."""

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from pdelie.contracts import GeneratorFamily, VerificationReport
from pdelie.errors import SchemaValidationError, ScopeValidationError, ShapeValidationError


_SUPPORTED_INNER_PRODUCTS = frozenset({"normalized_polynomial_l2"})
_SUPPORTED_COMPUTATION_MODES = frozenset({"auto", "exact_polynomial", "sampled_projection"})
_RANK_TOL = 1e-10
_METRIC_EIGEN_TOL = 1e-12
_RESIDUAL_EPS = 1e-12
_SAMPLED_GRID_POINTS_PER_AXIS = 5
_FALLBACK_DOMAIN_BOUND = 1.0
_SYMMETRY_ALGEBRA_CLASSIFICATIONS = frozenset({"exact", "approximate"})

_Polynomial = dict[tuple[int, ...], float]
_VectorField = dict[str, _Polynomial]


def _validate_component_targets(
    generator: GeneratorFamily,
    component_targets: Mapping[str, str] | None,
) -> dict[str, str]:
    component_names = [str(name) for name in generator.basis_spec["component_ordering"]]
    variables = [str(name) for name in generator.basis_spec["variables"]]
    resolved: dict[str, str] = {}

    if component_targets is not None:
        if not isinstance(component_targets, Mapping):
            raise SchemaValidationError("component_targets must be a mapping when provided.")
        for component_name, target_name in component_targets.items():
            normalized_component = str(component_name)
            normalized_target = str(target_name)
            if normalized_component not in component_names:
                raise SchemaValidationError(
                    f"component_targets includes unknown component '{normalized_component}'."
                )
            if normalized_target not in variables:
                raise SchemaValidationError(
                    f"component_targets maps component '{normalized_component}' to unknown variable '{normalized_target}'."
                )
            resolved[normalized_component] = normalized_target

    if component_names == variables:
        for component_name in component_names:
            resolved.setdefault(component_name, component_name)

    if variables == ["t", "x", "u"]:
        special_defaults = {"tau": "t", "xi": "x", "phi": "u"}
        for component_name, target_name in special_defaults.items():
            if component_name in component_names:
                resolved.setdefault(component_name, target_name)

    if "x" in variables and "xi" in component_names:
        resolved.setdefault("xi", "x")

    for component_name in component_names:
        if component_name in resolved:
            continue
        if "_" in component_name:
            suffix = component_name.rsplit("_", 1)[1]
            if suffix in variables:
                resolved[component_name] = suffix

    missing = [component_name for component_name in component_names if component_name not in resolved]
    if missing:
        raise ScopeValidationError(
            "diagnose_generator_family_closure requires resolved component targets for all components."
        )

    return {component_name: resolved[component_name] for component_name in component_names}


def _canonical_monomial_label(variables: Sequence[str], powers: Sequence[int]) -> str:
    parts: list[str] = []
    for variable_name, power in zip(variables, powers):
        if power == 0:
            continue
        if power == 1:
            parts.append(str(variable_name))
        else:
            parts.append(f"{variable_name}^{int(power)}")
    return "1" if not parts else "*".join(parts)


def _supports_exact_polynomial_terms(generator: GeneratorFamily) -> bool:
    variables = [str(name) for name in generator.basis_spec["variables"]]
    for term in generator.basis_spec["basis_terms"]:
        powers = [int(power) for power in term["powers"]]
        if str(term["label"]) != _canonical_monomial_label(variables, powers):
            return False
    return True


def _resolve_computation_mode(
    generator: GeneratorFamily,
    *,
    component_targets_resolved: bool,
    inner_product: str,
    computation_mode: str,
) -> str:
    if inner_product not in _SUPPORTED_INNER_PRODUCTS:
        raise SchemaValidationError(
            "diagnose_generator_family_closure only supports inner_product='normalized_polynomial_l2' in V0.4 Milestone 4."
        )
    if computation_mode not in _SUPPORTED_COMPUTATION_MODES:
        raise SchemaValidationError(
            "computation_mode must be one of {'auto', 'exact_polynomial', 'sampled_projection'}."
        )
    if not component_targets_resolved:
        raise ScopeValidationError(
            "diagnose_generator_family_closure requires resolved component targets for both exact and sampled modes."
        )

    exact_supported = _supports_exact_polynomial_terms(generator)
    if computation_mode == "sampled_projection":
        return "sampled_projection"
    if computation_mode == "exact_polynomial":
        if not exact_supported:
            raise ScopeValidationError(
                "exact_polynomial closure diagnostics only support the current canonical monomial polynomial basis_terms in V0.4 Milestone 4."
            )
        return "exact_polynomial"
    if exact_supported:
        return "exact_polynomial"
    return "sampled_projection"


def _ordered_basis_terms(generator: GeneratorFamily) -> list[dict[str, Any]]:
    return [
        {"label": str(term["label"]), "powers": [int(power) for power in term["powers"]]}
        for term in generator.basis_spec["basis_terms"]
    ]


def _row_to_vector_field(generator: GeneratorFamily, row: np.ndarray) -> _VectorField:
    component_names = [str(name) for name in generator.basis_spec["component_ordering"]]
    basis_terms = _ordered_basis_terms(generator)
    vector_field: _VectorField = {component_name: {} for component_name in component_names}
    offset = 0
    for component_name in component_names:
        component_polynomial = vector_field[component_name]
        for term in basis_terms:
            coefficient = float(row[offset])
            offset += 1
            if abs(coefficient) <= _RESIDUAL_EPS:
                continue
            component_polynomial[tuple(int(power) for power in term["powers"])] = coefficient
    return vector_field


def _clean_polynomial(polynomial: _Polynomial) -> _Polynomial:
    return {
        tuple(int(power) for power in powers): float(value)
        for powers, value in polynomial.items()
        if abs(float(value)) > _RESIDUAL_EPS
    }


def _poly_add_scaled(target: _Polynomial, source: _Polynomial, scale: float) -> None:
    for powers, coefficient in source.items():
        updated = float(target.get(powers, 0.0)) + float(scale) * float(coefficient)
        if abs(updated) <= _RESIDUAL_EPS:
            target.pop(powers, None)
        else:
            target[powers] = updated


def _differentiate_polynomial(polynomial: _Polynomial, variable_index: int) -> _Polynomial:
    derivative: _Polynomial = {}
    for powers, coefficient in polynomial.items():
        power = int(powers[variable_index])
        if power == 0:
            continue
        new_powers = list(powers)
        new_powers[variable_index] -= 1
        derivative[tuple(new_powers)] = float(derivative.get(tuple(new_powers), 0.0)) + float(coefficient) * power
    return _clean_polynomial(derivative)


def _multiply_polynomials(left: _Polynomial, right: _Polynomial) -> _Polynomial:
    product: _Polynomial = {}
    for left_powers, left_coefficient in left.items():
        for right_powers, right_coefficient in right.items():
            powers = tuple(int(a) + int(b) for a, b in zip(left_powers, right_powers))
            product[powers] = float(product.get(powers, 0.0)) + float(left_coefficient) * float(right_coefficient)
    return _clean_polynomial(product)


def _lie_bracket(
    left: _VectorField,
    right: _VectorField,
    *,
    component_names: Sequence[str],
    component_targets: Mapping[str, str],
    variable_indices: Mapping[str, int],
) -> _VectorField:
    bracket: _VectorField = {component_name: {} for component_name in component_names}
    for output_component in component_names:
        component_bracket: _Polynomial = {}
        for derivative_component in component_names:
            variable_index = int(variable_indices[component_targets[derivative_component]])
            _poly_add_scaled(
                component_bracket,
                _multiply_polynomials(
                    left[derivative_component],
                    _differentiate_polynomial(right[output_component], variable_index),
                ),
                1.0,
            )
            _poly_add_scaled(
                component_bracket,
                _multiply_polynomials(
                    right[derivative_component],
                    _differentiate_polynomial(left[output_component], variable_index),
                ),
                -1.0,
            )
        bracket[output_component] = _clean_polynomial(component_bracket)
    return bracket


def _monomial_average_inner_product(powers_a: tuple[int, ...], powers_b: tuple[int, ...]) -> float:
    value = 1.0
    for power_a, power_b in zip(powers_a, powers_b):
        total_power = int(power_a) + int(power_b)
        if total_power % 2 == 1:
            return 0.0
        value *= 1.0 / float(total_power + 1)
    return value


def _polynomial_inner_product(left: _Polynomial, right: _Polynomial) -> float:
    total = 0.0
    for left_powers, left_coefficient in left.items():
        for right_powers, right_coefficient in right.items():
            total += (
                float(left_coefficient)
                * float(right_coefficient)
                * _monomial_average_inner_product(tuple(left_powers), tuple(right_powers))
            )
    return float(total)


def _vector_field_inner_product(
    left: _VectorField,
    right: _VectorField,
    *,
    component_names: Sequence[str],
    component_weights: Mapping[str, float],
) -> float:
    total = 0.0
    for component_name in component_names:
        total += float(component_weights[component_name]) * _polynomial_inner_product(
            left[component_name],
            right[component_name],
        )
    return float(total)


def _condition_number(values: np.ndarray) -> float:
    positive = np.asarray(values, dtype=float)
    positive = positive[positive > 0.0]
    if positive.size == 0:
        return float("inf")
    minimum = float(np.min(positive))
    maximum = float(np.max(positive))
    if minimum == 0.0:
        return float("inf")
    return maximum / minimum


def _family_metric_summary(metric_matrix: np.ndarray) -> tuple[int, float]:
    symmetric = 0.5 * (np.asarray(metric_matrix, dtype=float) + np.asarray(metric_matrix, dtype=float).T)
    eigenvalues = np.linalg.eigvalsh(symmetric)
    max_abs = float(np.max(np.abs(eigenvalues))) if eigenvalues.size else 0.0
    threshold = max(_RANK_TOL * max_abs, _METRIC_EIGEN_TOL)
    if np.any(eigenvalues < -threshold):
        raise ShapeValidationError("Closure diagnostics require a positive semidefinite family metric.")
    positive = eigenvalues[eigenvalues > threshold]
    return int(positive.size), _condition_number(positive)


def _solve_projection_coefficients(metric_matrix: np.ndarray, rhs: np.ndarray) -> tuple[np.ndarray, float]:
    coefficients, _, _, singular_values = np.linalg.lstsq(metric_matrix, rhs, rcond=None)
    return np.asarray(coefficients, dtype=float), _condition_number(np.asarray(singular_values, dtype=float))


def _normalized_domain(variables: Sequence[str]) -> dict[str, object]:
    return {
        "kind": "normalized_hypercube",
        "variables": [str(name) for name in variables],
        "bounds": [[-_FALLBACK_DOMAIN_BOUND, _FALLBACK_DOMAIN_BOUND] for _ in variables],
    }


def _tensor_grid(variables: Sequence[str]) -> np.ndarray:
    axes = [
        np.linspace(-_FALLBACK_DOMAIN_BOUND, _FALLBACK_DOMAIN_BOUND, _SAMPLED_GRID_POINTS_PER_AXIS, dtype=float)
        for _ in variables
    ]
    mesh = np.meshgrid(*axes, indexing="ij")
    return np.stack([axis.reshape(-1) for axis in mesh], axis=1)


def _evaluate_polynomial(polynomial: _Polynomial, points: np.ndarray) -> np.ndarray:
    values = np.zeros(points.shape[0], dtype=float)
    for powers, coefficient in polynomial.items():
        term = np.full(points.shape[0], float(coefficient), dtype=float)
        for variable_index, power in enumerate(powers):
            if int(power) == 0:
                continue
            term *= points[:, variable_index] ** int(power)
        values += term
    return values


def _evaluate_vector_field(
    vector_field: _VectorField,
    *,
    component_names: Sequence[str],
    points: np.ndarray,
) -> np.ndarray:
    return np.vstack([
        _evaluate_polynomial(vector_field[component_name], points)
        for component_name in component_names
    ])


def _sampled_inner_product(
    left: np.ndarray,
    right: np.ndarray,
    *,
    component_names: Sequence[str],
    component_weights: Mapping[str, float],
) -> float:
    total = 0.0
    for component_index, component_name in enumerate(component_names):
        total += float(component_weights[component_name]) * float(
            np.mean(left[component_index] * right[component_index])
        )
    return float(total)


def _normalize_verification_reports(
    verification_reports: Sequence[VerificationReport] | None,
) -> list[VerificationReport] | None:
    if verification_reports is None:
        return None
    if isinstance(verification_reports, (str, bytes)) or not isinstance(verification_reports, Sequence):
        raise SchemaValidationError("verification_reports must be a sequence of VerificationReport objects.")
    normalized: list[VerificationReport] = []
    for index, report in enumerate(verification_reports):
        if not isinstance(report, VerificationReport):
            raise SchemaValidationError(
                f"verification_reports[{index}] must be a VerificationReport instance."
            )
        report.validate()
        normalized.append(report)
    return normalized


def _interpretation_label(verification_reports: list[VerificationReport] | None) -> tuple[str, list[str] | None]:
    if verification_reports is None:
        return "vector_field_algebra_diagnostics", None
    classifications = [report.classification for report in verification_reports]
    if classifications and all(
        classification in _SYMMETRY_ALGEBRA_CLASSIFICATIONS for classification in classifications
    ):
        return "symmetry_algebra_diagnostics", classifications
    return "vector_field_algebra_diagnostics", classifications


def diagnose_generator_family_closure(
    generator: GeneratorFamily,
    *,
    verification_reports: Sequence[VerificationReport] | None = None,
    component_targets: Mapping[str, str] | None = None,
    inner_product: str = "normalized_polynomial_l2",
    computation_mode: str = "auto",
) -> dict[str, object]:
    """Diagnose runtime closure properties for a canonical polynomial GeneratorFamily."""

    generator.validate()

    normalized_reports = _normalize_verification_reports(verification_reports)
    interpretation_label, verification_classifications = _interpretation_label(normalized_reports)

    resolved_component_targets = _validate_component_targets(generator, component_targets)
    resolved_mode = _resolve_computation_mode(
        generator,
        component_targets_resolved=True,
        inner_product=inner_product,
        computation_mode=computation_mode,
    )

    component_names = [str(name) for name in generator.basis_spec["component_ordering"]]
    variables = [str(name) for name in generator.basis_spec["variables"]]
    variable_indices = {variable_name: index for index, variable_name in enumerate(variables)}
    component_weights = {component_name: 1.0 for component_name in component_names}
    family_fields = [
        _row_to_vector_field(generator, row)
        for row in np.asarray(generator.coefficients, dtype=float)
    ]
    family_size = len(family_fields)

    if resolved_mode == "exact_polynomial":
        metric_matrix = np.empty((family_size, family_size), dtype=float)
        for row_index, left in enumerate(family_fields):
            for col_index, right in enumerate(family_fields):
                metric_matrix[row_index, col_index] = _vector_field_inner_product(
                    left,
                    right,
                    component_names=component_names,
                    component_weights=component_weights,
                )
        sampled_points = None
        family_evaluations = None
        domain: dict[str, object] = _normalized_domain(variables)
    else:
        sampled_points = _tensor_grid(variables)
        family_evaluations = [
            _evaluate_vector_field(field, component_names=component_names, points=sampled_points)
            for field in family_fields
        ]
        metric_matrix = np.empty((family_size, family_size), dtype=float)
        for row_index, left in enumerate(family_evaluations):
            for col_index, right in enumerate(family_evaluations):
                metric_matrix[row_index, col_index] = _sampled_inner_product(
                    left,
                    right,
                    component_names=component_names,
                    component_weights=component_weights,
                )
        domain = _normalized_domain(variables)
        domain["grid_points_per_axis"] = _SAMPLED_GRID_POINTS_PER_AXIS

    family_rank, family_condition = _family_metric_summary(metric_matrix)
    if family_rank != family_size:
        raise ShapeValidationError(
            "diagnose_generator_family_closure requires full effective family rank under the runtime metric policy; structure constants are not uniquely defined for a rank-deficient family."
        )

    structure_tensor = np.zeros((family_size, family_size, family_size), dtype=float)
    closure_residuals = np.zeros((family_size, family_size), dtype=float)
    antisymmetry_residuals = np.zeros((family_size, family_size), dtype=float)
    solve_condition = family_condition

    for left_index, left in enumerate(family_fields):
        for right_index, right in enumerate(family_fields):
            raw_bracket = _lie_bracket(
                left,
                right,
                component_names=component_names,
                component_targets=resolved_component_targets,
                variable_indices=variable_indices,
            )
            if resolved_mode == "exact_polynomial":
                rhs = np.asarray(
                    [
                        _vector_field_inner_product(
                            raw_bracket,
                            family_field,
                            component_names=component_names,
                            component_weights=component_weights,
                        )
                        for family_field in family_fields
                    ],
                    dtype=float,
                )
                raw_norm_sq = _vector_field_inner_product(
                    raw_bracket,
                    raw_bracket,
                    component_names=component_names,
                    component_weights=component_weights,
                )
            else:
                assert sampled_points is not None
                assert family_evaluations is not None
                raw_evaluation = _evaluate_vector_field(
                    raw_bracket,
                    component_names=component_names,
                    points=sampled_points,
                )
                rhs = np.asarray(
                    [
                        _sampled_inner_product(
                            raw_evaluation,
                            family_evaluation,
                            component_names=component_names,
                            component_weights=component_weights,
                        )
                        for family_evaluation in family_evaluations
                    ],
                    dtype=float,
                )
                raw_norm_sq = _sampled_inner_product(
                    raw_evaluation,
                    raw_evaluation,
                    component_names=component_names,
                    component_weights=component_weights,
                )

            structure_coefficients, current_solve_condition = _solve_projection_coefficients(metric_matrix, rhs)
            solve_condition = max(solve_condition, current_solve_condition)
            structure_tensor[left_index, right_index, :] = structure_coefficients

            projected_norm_sq = float(structure_coefficients @ metric_matrix @ structure_coefficients)
            residual_sq = max(
                float(raw_norm_sq) - 2.0 * float(structure_coefficients @ rhs) + projected_norm_sq,
                0.0,
            )
            closure_residuals[left_index, right_index] = float(
                np.sqrt(residual_sq) / (np.sqrt(max(float(raw_norm_sq), 0.0)) + _RESIDUAL_EPS)
            )

    for left_index in range(family_size):
        for right_index in range(left_index, family_size):
            antisymmetry_numerator = np.linalg.norm(
                structure_tensor[left_index, right_index, :] + structure_tensor[right_index, left_index, :]
            )
            antisymmetry_denominator = (
                np.linalg.norm(structure_tensor[left_index, right_index, :])
                + np.linalg.norm(structure_tensor[right_index, left_index, :])
                + _RESIDUAL_EPS
            )
            antisymmetry_value = float(antisymmetry_numerator / antisymmetry_denominator)
            antisymmetry_residuals[left_index, right_index] = antisymmetry_value
            antisymmetry_residuals[right_index, left_index] = antisymmetry_value

    jacobi_residuals: list[list[list[float]]] | list[object]
    if family_size < 3:
        jacobi_residuals = []
        jacobi_summary = 0.0
    else:
        jacobi_array = np.zeros((family_size, family_size, family_size), dtype=float)
        for i in range(family_size):
            for j in range(family_size):
                for k in range(family_size):
                    first = np.zeros(family_size, dtype=float)
                    second = np.zeros(family_size, dtype=float)
                    third = np.zeros(family_size, dtype=float)
                    for ell in range(family_size):
                        first += structure_tensor[i, j, ell] * structure_tensor[ell, k, :]
                        second += structure_tensor[j, k, ell] * structure_tensor[ell, i, :]
                        third += structure_tensor[k, i, ell] * structure_tensor[ell, j, :]
                    numerator = np.linalg.norm(first + second + third)
                    denominator = np.linalg.norm(first) + np.linalg.norm(second) + np.linalg.norm(third) + _RESIDUAL_EPS
                    jacobi_array[i, j, k] = float(numerator / denominator)
        jacobi_residuals = jacobi_array.tolist()
        jacobi_summary = float(np.max(jacobi_array))

    conditioning = {
        "family_gram": family_condition,
        "structure_constant_solve": solve_condition,
    }

    return {
        "interpretation_label": interpretation_label,
        "verification_classifications": verification_classifications,
        "inner_product": inner_product,
        "computation_mode": resolved_mode,
        "domain": domain,
        "component_weights": component_weights,
        "component_targets": resolved_component_targets,
        "family_rank": family_rank,
        "structure_constants": {
            "tensor": structure_tensor.tolist(),
            "estimation_mode": resolved_mode,
            "conditioning": {
                "family_gram": family_condition,
                "structure_constant_solve": solve_condition,
            },
        },
        "closure": {
            "summary": float(np.max(closure_residuals)),
            "pairwise_residuals": closure_residuals.tolist(),
        },
        "antisymmetry": {
            "summary": float(np.max(antisymmetry_residuals)),
            "pairwise_residuals": antisymmetry_residuals.tolist(),
        },
        "jacobi": {
            "summary": jacobi_summary,
            "triple_residuals": jacobi_residuals,
            "mode": "structure_constants",
        },
        "conditioning": conditioning,
    }


__all__ = ["diagnose_generator_family_closure"]
