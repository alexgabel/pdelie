from __future__ import annotations

"""Runtime-only symbolic display helpers for GeneratorFamily.

This module intentionally operates on canonical GeneratorFamily objects without
changing their stored coefficients or normalization semantics.
"""

import importlib
from collections.abc import Mapping

import numpy as np

from pdelie.contracts import GeneratorFamily
from pdelie.errors import SchemaValidationError


_DISPLAY_ZERO_TOL = 1e-12
_DEFAULT_COMPONENT_DISPLAY_NAMES = {
    "tau": "\u2202t",
    "xi": "\u2202x",
    "phi": "\u2202u",
}
_SUPPORTED_DISPLAY_NORMALIZATIONS = frozenset({"anchor", "none"})


def _require_sympy():
    try:
        return importlib.import_module("sympy")
    except (ModuleNotFoundError, ImportError, ValueError) as exc:
        raise ImportError(
            "SymPy is required for to_sympy_component_expressions. Install sympy to use this runtime helper."
        ) from exc


def _normalize_display_normalization(display_normalization: str) -> str:
    if not isinstance(display_normalization, str):
        raise SchemaValidationError("display_normalization must be a string.")
    if display_normalization not in _SUPPORTED_DISPLAY_NORMALIZATIONS:
        raise SchemaValidationError(
            "display_normalization must be one of {'anchor', 'none'} for runtime symbolic rendering."
        )
    return display_normalization


def _normalize_component_display_names(
    component_display_names: Mapping[str, str] | None,
) -> dict[str, str]:
    if component_display_names is None:
        return {}
    if not isinstance(component_display_names, Mapping):
        raise SchemaValidationError("component_display_names must be a mapping when provided.")
    normalized: dict[str, str] = {}
    for component_name, token in component_display_names.items():
        normalized_name = str(component_name)
        normalized_token = str(token)
        if not normalized_name or not normalized_token:
            raise SchemaValidationError("component_display_names entries must be non-empty strings.")
        normalized[normalized_name] = normalized_token
    return normalized


def _ordered_basis_terms(generator: GeneratorFamily) -> list[dict[str, object]]:
    term_by_label = {
        str(term["label"]): {
            "label": str(term["label"]),
            "powers": [int(power) for power in term["powers"]],
        }
        for term in generator.basis_spec["basis_terms"]
    }
    return [term_by_label[str(label)] for label in generator.basis_spec["term_ordering"]]


def _display_normalized_row(row: np.ndarray, display_normalization: str) -> np.ndarray:
    normalized = np.asarray(row, dtype=float).copy()
    if display_normalization == "none":
        normalized[np.abs(normalized) <= _DISPLAY_ZERO_TOL] = 0.0
        return normalized

    for index, coefficient in enumerate(normalized):
        if abs(coefficient) <= _DISPLAY_ZERO_TOL:
            continue
        normalized = normalized / abs(coefficient)
        if normalized[index] < 0.0:
            normalized = -normalized
        normalized[np.abs(normalized) <= _DISPLAY_ZERO_TOL] = 0.0
        return normalized

    return np.zeros_like(normalized)


def _format_scalar(value: float) -> str:
    rounded = round(value)
    if np.isclose(value, rounded, atol=_DISPLAY_ZERO_TOL, rtol=0.0):
        return str(int(rounded))
    return f"{value:.12g}"


def _component_operator_token(component_name: str, component_display_names: Mapping[str, str]) -> str:
    if component_name in component_display_names:
        return component_display_names[component_name]
    return _DEFAULT_COMPONENT_DISPLAY_NAMES.get(component_name, f"D[{component_name}]")


def _format_term_body(coefficient: float, term_label: str, operator_token: str) -> str:
    magnitude = abs(float(coefficient))
    magnitude_is_one = np.isclose(magnitude, 1.0, atol=_DISPLAY_ZERO_TOL, rtol=0.0)
    if term_label == "1":
        if magnitude_is_one:
            return operator_token
        return f"{_format_scalar(magnitude)}{operator_token}"
    if magnitude_is_one:
        return f"{term_label}{operator_token}"
    return f"{_format_scalar(magnitude)}{term_label}{operator_token}"


def _render_row(
    row: np.ndarray,
    *,
    component_names: list[str],
    basis_terms: list[dict[str, object]],
    component_display_names: Mapping[str, str],
) -> str:
    rendered_terms: list[str] = []
    offset = 0
    for component_name in component_names:
        operator_token = _component_operator_token(component_name, component_display_names)
        for term in basis_terms:
            coefficient = float(row[offset])
            offset += 1
            if abs(coefficient) <= _DISPLAY_ZERO_TOL:
                continue
            rendered_terms.append(
                (
                    "-" if coefficient < 0.0 else "+"
                )
                + _format_term_body(coefficient, str(term["label"]), operator_token)
            )

    if not rendered_terms:
        return "0"

    head, *tail = rendered_terms
    expression = head[1:] if head.startswith("+") else head
    for term in tail:
        expression += f" {'-' if term.startswith('-') else '+'} {term[1:]}"
    return expression


def render_generator_family(
    generator: GeneratorFamily,
    *,
    display_normalization: str = "anchor",
    component_display_names: Mapping[str, str] | None = None,
) -> list[str]:
    """Render each stored generator row into a deterministic human-readable string."""

    display_normalization = _normalize_display_normalization(display_normalization)
    display_names = _normalize_component_display_names(component_display_names)
    component_names = list(generator.basis_spec["component_ordering"])
    basis_terms = _ordered_basis_terms(generator)

    return [
        f"X_{index} = "
        + _render_row(
            _display_normalized_row(row, display_normalization),
            component_names=component_names,
            basis_terms=basis_terms,
            component_display_names=display_names,
        )
        for index, row in enumerate(np.asarray(generator.coefficients, dtype=float), start=1)
    ]


def _sympy_coefficient(sympy_module, coefficient: float):
    rounded = round(coefficient)
    if np.isclose(coefficient, rounded, atol=_DISPLAY_ZERO_TOL, rtol=0.0):
        return sympy_module.Integer(int(rounded))
    return sympy_module.Float(float(coefficient))


def _sympy_term(sympy_module, symbols: list[object], powers: list[int]):
    term = sympy_module.Integer(1)
    for symbol, power in zip(symbols, powers):
        if power == 0:
            continue
        term *= symbol ** int(power)
    return term


def to_sympy_component_expressions(
    generator: GeneratorFamily,
    *,
    display_normalization: str = "anchor",
) -> list[dict[str, object]]:
    """Return display-normalized component polynomials as SymPy expressions."""

    sympy_module = _require_sympy()
    display_normalization = _normalize_display_normalization(display_normalization)
    component_names = list(generator.basis_spec["component_ordering"])
    basis_terms = _ordered_basis_terms(generator)
    variable_names = [str(name) for name in generator.basis_spec["variables"]]
    raw_symbols = sympy_module.symbols(" ".join(variable_names))
    if isinstance(raw_symbols, tuple):
        symbols = list(raw_symbols)
    else:
        symbols = [raw_symbols]

    expressions: list[dict[str, object]] = []
    for row in np.asarray(generator.coefficients, dtype=float):
        normalized_row = _display_normalized_row(row, display_normalization)
        component_expressions: dict[str, object] = {}
        offset = 0
        for component_name in component_names:
            expression = sympy_module.Integer(0)
            for term in basis_terms:
                coefficient = float(normalized_row[offset])
                offset += 1
                if abs(coefficient) <= _DISPLAY_ZERO_TOL:
                    continue
                expression += _sympy_coefficient(sympy_module, coefficient) * _sympy_term(
                    sympy_module,
                    symbols,
                    list(term["powers"]),
                )
            component_expressions[component_name] = sympy_module.expand(expression)
        expressions.append(component_expressions)
    return expressions


__all__ = [
    "render_generator_family",
    "to_sympy_component_expressions",
]
