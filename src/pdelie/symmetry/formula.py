from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, ClassVar

import numpy as np

from pdelie._boundary import is_x_periodic
from pdelie.contracts import FieldBatch, InvariantMapSpec
from pdelie.errors import SchemaValidationError, ScopeValidationError

_VARIABLES = ("t", "x", "u")
_COMPONENT_NAMES = ("tau", "xi", "phi")
_SUMMARY_SCHEMA_VERSION = "0.1"
_RECIPROCAL_DENOMINATOR_FLOOR = 1e-12
_MAX_INTEGER_POWER = 8
_EVALUABLE_NODES = frozenset({"const", "var", "add", "mul", "pow", "sin", "cos", "reciprocal"})
_SYMBOLIC_NODE = "symbolic_reference"
_SUPPORTED_NODES = _EVALUABLE_NODES.union({_SYMBOLIC_NODE})


class _FormulaEvaluationFailure(Exception):
    pass


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _validate_json_compatible(value: Any, *, name: str) -> Any:
    normalized = _json_safe(value)
    try:
        json.dumps(normalized, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{name} must be JSON-compatible.") from exc
    return normalized


def _mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{name} must be a mapping.")
    return value


def _reject_extra_keys(value: Mapping[str, Any], allowed: set[str], *, name: str) -> None:
    extra = sorted(set(value).difference(allowed))
    if extra:
        raise SchemaValidationError(f"{name} has unsupported fields {extra}.")


def _nonempty_string(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaValidationError(f"{name} must be a non-empty string.")
    return value


def _sequence(value: Any, *, name: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise SchemaValidationError(f"{name} must be a sequence.")
    return value


def _finite_float(value: Any, *, name: str) -> float:
    if isinstance(value, bool):
        raise SchemaValidationError(f"{name} must be a finite float.")
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{name} must be a finite float.") from exc
    if not np.isfinite(normalized):
        raise SchemaValidationError(f"{name} must be a finite float.")
    return normalized


def _integer_power(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise SchemaValidationError(f"{name} must be an integer.")
    normalized = int(value)
    if normalized < 0 or normalized > _MAX_INTEGER_POWER:
        raise SchemaValidationError(f"{name} must be between 0 and {_MAX_INTEGER_POWER}.")
    return normalized


def _normalize_expression(value: Any, *, name: str) -> dict[str, Any]:
    expression = dict(_mapping(value, name=name))
    node = _nonempty_string(expression.get("node"), name=f"{name}.node")
    if node not in _SUPPORTED_NODES:
        raise SchemaValidationError(f"{name}.node is unsupported: {node!r}.")

    if node == "const":
        _reject_extra_keys(expression, {"node", "value"}, name=name)
        return {"node": node, "value": _finite_float(expression.get("value"), name=f"{name}.value")}
    if node == "var":
        _reject_extra_keys(expression, {"node", "name"}, name=name)
        variable = _nonempty_string(expression.get("name"), name=f"{name}.name")
        if variable not in _VARIABLES:
            raise SchemaValidationError(f"{name}.name must be one of {_VARIABLES}.")
        return {"node": node, "name": variable}
    if node == "add":
        _reject_extra_keys(expression, {"node", "terms"}, name=name)
        terms = _sequence(expression.get("terms"), name=f"{name}.terms")
        if len(terms) == 0:
            raise SchemaValidationError(f"{name}.terms must be non-empty.")
        return {
            "node": node,
            "terms": [
                _normalize_expression(term, name=f"{name}.terms[{index}]")
                for index, term in enumerate(terms)
            ],
        }
    if node == "mul":
        _reject_extra_keys(expression, {"node", "factors"}, name=name)
        factors = _sequence(expression.get("factors"), name=f"{name}.factors")
        if len(factors) == 0:
            raise SchemaValidationError(f"{name}.factors must be non-empty.")
        return {
            "node": node,
            "factors": [
                _normalize_expression(factor, name=f"{name}.factors[{index}]")
                for index, factor in enumerate(factors)
            ],
        }
    if node == "pow":
        _reject_extra_keys(expression, {"node", "base", "exponent"}, name=name)
        return {
            "node": node,
            "base": _normalize_expression(expression.get("base"), name=f"{name}.base"),
            "exponent": _integer_power(expression.get("exponent"), name=f"{name}.exponent"),
        }
    if node in {"sin", "cos", "reciprocal"}:
        _reject_extra_keys(expression, {"node", "arg"}, name=name)
        return {"node": node, "arg": _normalize_expression(expression.get("arg"), name=f"{name}.arg")}

    _reject_extra_keys(expression, {"node", "label", "metadata"}, name=name)
    label = _nonempty_string(expression.get("label"), name=f"{name}.label")
    metadata = expression.get("metadata", {})
    metadata_mapping = dict(_mapping(metadata, name=f"{name}.metadata"))
    return {
        "node": _SYMBOLIC_NODE,
        "label": label,
        "metadata": _validate_json_compatible(metadata_mapping, name=f"{name}.metadata"),
    }


def _expression_contains_symbolic_reference(expression: Mapping[str, Any]) -> bool:
    node = expression["node"]
    if node == _SYMBOLIC_NODE:
        return True
    if node == "add":
        return any(_expression_contains_symbolic_reference(term) for term in expression["terms"])
    if node == "mul":
        return any(_expression_contains_symbolic_reference(factor) for factor in expression["factors"])
    if node == "pow":
        return _expression_contains_symbolic_reference(expression["base"])
    if node in {"sin", "cos", "reciprocal"}:
        return _expression_contains_symbolic_reference(expression["arg"])
    return False


def _symbolic_references(expression: Mapping[str, Any]) -> list[dict[str, Any]]:
    node = expression["node"]
    if node == _SYMBOLIC_NODE:
        return [{"label": expression["label"], "metadata": expression["metadata"]}]
    if node == "add":
        return [item for term in expression["terms"] for item in _symbolic_references(term)]
    if node == "mul":
        return [item for factor in expression["factors"] for item in _symbolic_references(factor)]
    if node == "pow":
        return _symbolic_references(expression["base"])
    if node in {"sin", "cos", "reciprocal"}:
        return _symbolic_references(expression["arg"])
    return []


def _eval_expression(expression: Mapping[str, Any], variables: Mapping[str, np.ndarray]) -> np.ndarray:
    node = expression["node"]
    if node == "const":
        return np.asarray(expression["value"], dtype=float)
    if node == "var":
        return np.asarray(variables[expression["name"]], dtype=float)
    if node == "add":
        result = np.asarray(0.0, dtype=float)
        for term in expression["terms"]:
            result = result + _eval_expression(term, variables)
        return result
    if node == "mul":
        result = np.asarray(1.0, dtype=float)
        for factor in expression["factors"]:
            result = result * _eval_expression(factor, variables)
        return result
    if node == "pow":
        return np.power(_eval_expression(expression["base"], variables), int(expression["exponent"]))
    if node == "sin":
        return np.sin(_eval_expression(expression["arg"], variables))
    if node == "cos":
        return np.cos(_eval_expression(expression["arg"], variables))
    if node == "reciprocal":
        denominator = _eval_expression(expression["arg"], variables)
        if np.any(np.abs(denominator) <= _RECIPROCAL_DENOMINATOR_FLOOR):
            raise _FormulaEvaluationFailure("reciprocal_denominator_floor_violation")
        return 1.0 / denominator
    raise _FormulaEvaluationFailure("symbolic_reference_not_evaluable")


def _field_variables(field: FieldBatch) -> dict[str, np.ndarray]:
    if not isinstance(field, FieldBatch):
        raise SchemaValidationError("field must be a FieldBatch.")
    field.validate()
    if field.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError("FormulaGeneratorFamily diagnostics require dims ('batch', 'time', 'x', 'var').")
    if len(field.var_names) != 1 or field.values.shape[-1] != 1:
        raise ScopeValidationError("FormulaGeneratorFamily diagnostics require a scalar field.")
    if not is_x_periodic(field):
        raise ScopeValidationError("FormulaGeneratorFamily diagnostics require periodic x boundary conditions.")
    if not np.all(np.isfinite(field.values)):
        raise ScopeValidationError("FormulaGeneratorFamily diagnostics require finite field values.")

    shape = field.values.shape
    time = np.asarray(field.coords["time"], dtype=float).reshape(1, shape[1], 1, 1)
    x = np.asarray(field.coords["x"], dtype=float).reshape(1, 1, shape[2], 1)
    return {
        "t": np.broadcast_to(time, shape),
        "x": np.broadcast_to(x, shape),
        "u": np.asarray(field.values, dtype=float),
    }


def _normalize_generator_record(value: Any, *, index: int) -> dict[str, Any]:
    record = dict(_mapping(value, name=f"formula_generators[{index}]"))
    _reject_extra_keys(record, {"name", "components", "metadata"}, name=f"formula_generators[{index}]")
    name = _nonempty_string(record.get("name"), name=f"formula_generators[{index}].name")
    components = dict(_mapping(record.get("components"), name=f"formula_generators[{index}].components"))
    missing = [component for component in _COMPONENT_NAMES if component not in components]
    extra = sorted(set(components).difference(_COMPONENT_NAMES))
    if missing:
        raise SchemaValidationError(f"formula_generators[{index}].components is missing {missing}.")
    if extra:
        raise SchemaValidationError(f"formula_generators[{index}].components has unsupported components {extra}.")
    metadata = record.get("metadata", {})
    metadata_mapping = dict(_mapping(metadata, name=f"formula_generators[{index}].metadata"))
    return {
        "name": name,
        "components": {
            component: _normalize_expression(
                components[component],
                name=f"formula_generators[{index}].components.{component}",
            )
            for component in _COMPONENT_NAMES
        },
        "metadata": _validate_json_compatible(metadata_mapping, name=f"formula_generators[{index}].metadata"),
    }


@dataclass(slots=True)
class FormulaGeneratorFamily:
    """Runtime-only formula-backed scalar 1D Lie-point generator record."""

    schema_version: str = "0.1"
    parameterization: str = "formula_generator_family"
    formula_generators: list[dict[str, Any]] = None  # type: ignore[assignment]
    variables: tuple[str, ...] = _VARIABLES
    component_names: tuple[str, ...] = _COMPONENT_NAMES
    finite_transform_spec: dict[str, Any] | None = None
    diagnostics: dict[str, Any] = None  # type: ignore[assignment]

    SCHEMA_VERSION: ClassVar[str] = "0.1"
    PARAMETERIZATION: ClassVar[str] = "formula_generator_family"
    RECIPROCAL_DENOMINATOR_FLOOR: ClassVar[float] = _RECIPROCAL_DENOMINATOR_FLOOR

    def __post_init__(self) -> None:
        self.schema_version = str(self.schema_version)
        self.parameterization = str(self.parameterization)
        self.variables = tuple(str(variable) for variable in self.variables)
        self.component_names = tuple(str(component) for component in self.component_names)
        if self.formula_generators is None:
            raise SchemaValidationError("formula_generators must be provided.")
        raw_generators = _sequence(self.formula_generators, name="formula_generators")
        if len(raw_generators) == 0:
            raise SchemaValidationError("formula_generators must be non-empty.")
        self.formula_generators = [
            _normalize_generator_record(record, index=index)
            for index, record in enumerate(raw_generators)
        ]
        if self.finite_transform_spec is not None:
            spec_mapping = dict(_mapping(self.finite_transform_spec, name="finite_transform_spec"))
            try:
                self.finite_transform_spec = InvariantMapSpec.from_dict(spec_mapping).to_dict()
            except KeyError as exc:
                raise SchemaValidationError("finite_transform_spec is malformed.") from exc
        if self.diagnostics is None:
            self.diagnostics = {}
        else:
            self.diagnostics = _validate_json_compatible(
                dict(_mapping(self.diagnostics, name="diagnostics")),
                name="diagnostics",
            )
        self.validate()

    def validate(self) -> None:
        if self.schema_version != self.SCHEMA_VERSION:
            raise SchemaValidationError("Unsupported FormulaGeneratorFamily schema_version.")
        if self.parameterization != self.PARAMETERIZATION:
            raise SchemaValidationError("FormulaGeneratorFamily parameterization must be 'formula_generator_family'.")
        if self.variables != _VARIABLES:
            raise SchemaValidationError(f"FormulaGeneratorFamily variables must be exactly {_VARIABLES}.")
        if self.component_names != _COMPONENT_NAMES:
            raise SchemaValidationError(f"FormulaGeneratorFamily component_names must be exactly {_COMPONENT_NAMES}.")
        _validate_json_compatible(self.to_dict(), name="FormulaGeneratorFamily payload")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "parameterization": self.parameterization,
            "variables": list(self.variables),
            "component_names": list(self.component_names),
            "formula_generators": _json_safe(self.formula_generators),
            "diagnostics": _json_safe(self.diagnostics),
        }
        if self.finite_transform_spec is not None:
            payload["finite_transform_spec"] = _json_safe(self.finite_transform_spec)
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FormulaGeneratorFamily:
        payload_mapping = dict(_mapping(payload, name="FormulaGeneratorFamily payload"))
        _reject_extra_keys(
            payload_mapping,
            {
                "schema_version",
                "parameterization",
                "variables",
                "component_names",
                "formula_generators",
                "finite_transform_spec",
                "diagnostics",
            },
            name="FormulaGeneratorFamily payload",
        )
        try:
            schema_version = payload_mapping["schema_version"]
            parameterization = payload_mapping["parameterization"]
            variables = _sequence(payload_mapping["variables"], name="FormulaGeneratorFamily payload.variables")
            component_names = _sequence(
                payload_mapping["component_names"],
                name="FormulaGeneratorFamily payload.component_names",
            )
            formula_generators = _sequence(
                payload_mapping["formula_generators"],
                name="FormulaGeneratorFamily payload.formula_generators",
            )
            diagnostics = dict(
                _mapping(
                    payload_mapping.get("diagnostics", {}),
                    name="FormulaGeneratorFamily payload.diagnostics",
                )
            )
            return cls(
                schema_version=str(schema_version),
                parameterization=str(parameterization),
                variables=tuple(variables),
                component_names=tuple(component_names),
                formula_generators=list(formula_generators),
                finite_transform_spec=payload_mapping.get("finite_transform_spec"),
                diagnostics=diagnostics,
            )
        except KeyError as exc:
            raise SchemaValidationError("FormulaGeneratorFamily payload is malformed.") from exc


def _diagnose_formula_generator_family_on_field(
    formula: FormulaGeneratorFamily,
    field: FieldBatch,
) -> dict[str, Any]:
    if not isinstance(formula, FormulaGeneratorFamily):
        raise SchemaValidationError("formula must be a FormulaGeneratorFamily.")
    formula.validate()
    variables = _field_variables(field)
    component_reports: list[dict[str, Any]] = []

    for generator_index, generator in enumerate(formula.formula_generators):
        for component in formula.component_names:
            expression = generator["components"][component]
            report: dict[str, Any] = {
                "generator_index": generator_index,
                "generator_name": generator["name"],
                "component": component,
                "expression_node": expression["node"],
            }
            if _expression_contains_symbolic_reference(expression):
                report.update(
                    {
                        "status": "unavailable",
                        "reason": "symbolic_reference_metadata_only",
                        "symbolic_references": _symbolic_references(expression),
                    }
                )
            else:
                try:
                    values = np.asarray(_eval_expression(expression, variables), dtype=float)
                    values = np.broadcast_to(values, field.values.shape)
                    if not np.all(np.isfinite(values)):
                        raise _FormulaEvaluationFailure("nonfinite_formula_values")
                except _FormulaEvaluationFailure as exc:
                    report.update({"status": "failed", "reason": str(exc)})
                else:
                    report.update(
                        {
                            "status": "passed",
                            "value_shape": list(values.shape),
                            "max_abs_value": float(np.max(np.abs(values))),
                            "rms_value": float(np.sqrt(np.mean(np.square(values)))),
                        }
                    )
            component_reports.append(report)

    statuses = [report["status"] for report in component_reports]
    return _validate_json_compatible(
        {
            "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
            "summary_type": "formula_evaluation_diagnostics",
            "field_shape": list(field.values.shape),
            "variables": list(formula.variables),
            "component_names": list(formula.component_names),
            "generator_count": len(formula.formula_generators),
            "reciprocal_denominator_floor": _RECIPROCAL_DENOMINATOR_FLOOR,
            "component_reports": component_reports,
            "evaluated_component_count": statuses.count("passed"),
            "failed_component_count": statuses.count("failed"),
            "unavailable_component_count": statuses.count("unavailable"),
        },
        name="FormulaGeneratorFamily evaluation diagnostics",
    )


__all__ = ["FormulaGeneratorFamily"]
