from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import numpy as np

from pdelie.contracts import FieldBatch, GeneratorFamily, InvariantMapSpec
from pdelie.errors import PDELieValidationError, SchemaValidationError, ScopeValidationError
from pdelie.invariants import InvariantApplier
from pdelie.residuals.base import ResidualEvaluator
from pdelie.symmetry.closure import diagnose_generator_family_closure
from pdelie.symmetry.formula import (
    FormulaGeneratorFamily,
    _diagnose_formula_generator_family_on_field,
)
from pdelie.symmetry.parameterization.polynomial_translation import (
    _coerce_translation_coefficients,
)
from pdelie.symmetry.span import compare_generator_spans
from pdelie.verification import DEFAULT_EPSILON_VALUES, verify_translation_generator


_SUMMARY_SCHEMA_VERSION = "0.1"
_RESIDUAL_ABSOLUTE_TOLERANCE = 1e-8
_RESIDUAL_RELATIVE_TOLERANCE = 1e-6
_INVERSE_RELATIVE_L2_TOLERANCE = 1e-8
_SPAN_TOLERANCE = 1e-8
_CLOSURE_TOLERANCE = 1e-8
_RELATIVE_L2_EPS = 1e-12
_FORMULA_RECIPROCAL_DENOMINATOR_FLOOR = FormulaGeneratorFamily.RECIPROCAL_DENOMINATOR_FLOOR


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


def _validate_field(field: FieldBatch) -> None:
    if not isinstance(field, FieldBatch):
        raise SchemaValidationError("field must be a FieldBatch.")
    field.validate()
    if field.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError("validate_symmetry_candidate requires dims ('batch', 'time', 'x', 'var').")
    if len(field.var_names) != 1:
        raise ScopeValidationError("validate_symmetry_candidate requires a scalar field.")
    if field.metadata["boundary_conditions"].get("x") != "periodic":
        raise ScopeValidationError("validate_symmetry_candidate requires periodic x boundary conditions.")


def _validate_epsilon_values(values: Any | None) -> np.ndarray:
    if values is None:
        return np.asarray(DEFAULT_EPSILON_VALUES, dtype=float).copy()
    normalized = np.asarray(values, dtype=float)
    if normalized.ndim != 1 or normalized.size == 0:
        raise SchemaValidationError("finite_transform_epsilons must be a non-empty one-dimensional sequence.")
    if not np.all(np.isfinite(normalized)):
        raise SchemaValidationError("finite_transform_epsilons must contain only finite values.")
    if not np.all(normalized > 0.0):
        raise SchemaValidationError("finite_transform_epsilons must contain only positive values.")
    if not np.all(np.diff(normalized) > 0.0):
        raise SchemaValidationError("finite_transform_epsilons must be strictly increasing.")
    return normalized


def _is_generator_payload(payload: Mapping[str, Any]) -> bool:
    if any(key in payload for key in ("coefficients", "basis_spec", "normalization")):
        return True
    if payload.get("parameterization") == FormulaGeneratorFamily.PARAMETERIZATION:
        return False
    return any(key in payload for key in ("parameterization", "coefficients", "basis_spec", "normalization"))


def _is_invariant_map_payload(payload: Mapping[str, Any]) -> bool:
    return any(
        key in payload
        for key in (
            "generator_metadata",
            "construction_method",
            "parameters",
            "domain_validity",
            "inverse_available",
        )
    )


def _is_formula_payload(payload: Mapping[str, Any]) -> bool:
    return any(
        key in payload
        for key in (
            "formula_generators",
            "component_names",
            "finite_transform_spec",
        )
    ) or payload.get("parameterization") == FormulaGeneratorFamily.PARAMETERIZATION


def _coerce_generator_payload(payload: Mapping[str, Any], *, name: str) -> GeneratorFamily:
    try:
        schema_version = str(payload["schema_version"])
    except KeyError as exc:
        raise SchemaValidationError(f"{name} is malformed.") from exc
    if schema_version != GeneratorFamily.SCHEMA_VERSION:
        raise SchemaValidationError(
            f"{name} must use canonical GeneratorFamily schema_version "
            f"{GeneratorFamily.SCHEMA_VERSION!r}."
        )
    try:
        return GeneratorFamily.from_dict(payload)
    except KeyError as exc:
        raise SchemaValidationError(f"{name} is malformed.") from exc


def _coerce_formula_payload(payload: Mapping[str, Any], *, name: str) -> FormulaGeneratorFamily:
    try:
        return FormulaGeneratorFamily.from_dict(payload)
    except KeyError as exc:
        raise SchemaValidationError(f"{name} is malformed.") from exc


def _coerce_candidate(candidate: Any) -> tuple[str, GeneratorFamily | InvariantMapSpec | FormulaGeneratorFamily]:
    if isinstance(candidate, GeneratorFamily):
        candidate.validate()
        return "generator_family", candidate
    if isinstance(candidate, InvariantMapSpec):
        candidate.validate()
        return "invariant_map_spec", candidate
    if isinstance(candidate, FormulaGeneratorFamily):
        candidate.validate()
        return "formula_generator_family", candidate
    if callable(candidate):
        raise SchemaValidationError("Callable symmetry candidate descriptors are not supported.")
    if isinstance(candidate, Mapping):
        generator_payload = _is_generator_payload(candidate)
        invariant_payload = _is_invariant_map_payload(candidate)
        formula_payload = _is_formula_payload(candidate)
        if sum(bool(flag) for flag in (generator_payload, invariant_payload, formula_payload)) > 1:
            raise SchemaValidationError(
                "Symmetry candidate payload is ambiguous between GeneratorFamily, "
                "InvariantMapSpec, and FormulaGeneratorFamily."
            )
        if generator_payload:
            return "generator_family", _coerce_generator_payload(candidate, name="GeneratorFamily candidate payload")
        if invariant_payload:
            try:
                return "invariant_map_spec", InvariantMapSpec.from_dict(candidate)
            except KeyError as exc:
                raise SchemaValidationError("InvariantMapSpec candidate payload is malformed.") from exc
        if formula_payload:
            return "formula_generator_family", _coerce_formula_payload(
                candidate,
                name="FormulaGeneratorFamily candidate payload",
            )
        raise SchemaValidationError(
            "Symmetry candidate payload is not a recognized GeneratorFamily, "
            "InvariantMapSpec, or FormulaGeneratorFamily mapping."
        )
    raise SchemaValidationError(
        "candidate must be a GeneratorFamily, InvariantMapSpec, FormulaGeneratorFamily, or strict payload mapping."
    )


def _coerce_reference_generator(reference_generator: Any | None) -> GeneratorFamily | None:
    if reference_generator is None:
        return None
    if isinstance(reference_generator, GeneratorFamily):
        reference_generator.validate()
        return reference_generator
    if isinstance(reference_generator, Mapping):
        return _coerce_generator_payload(reference_generator, name="reference_generator payload")
    raise SchemaValidationError("reference_generator must be a GeneratorFamily, GeneratorFamily payload, or None.")


def _is_translation_compatible(generator: GeneratorFamily) -> bool:
    if generator.parameterization != "polynomial_translation_affine":
        return False
    try:
        _coerce_translation_coefficients(generator.coefficients)
    except PDELieValidationError:
        return False
    return True


def _relative_l2(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.linalg.norm(np.asarray(left, dtype=float) - np.asarray(right, dtype=float)) / (
        np.linalg.norm(np.asarray(right, dtype=float)) + _RELATIVE_L2_EPS
    ))


def _residual_rms(field: FieldBatch, residual_evaluator: ResidualEvaluator) -> float:
    residual = residual_evaluator.evaluate(field).residual
    normalized = np.asarray(residual, dtype=float)
    if not np.all(np.isfinite(normalized)):
        raise ScopeValidationError("residual_evaluator produced non-finite residual values.")
    return float(np.sqrt(np.mean(np.square(normalized))))


def _conclusion(checks: Mapping[str, Mapping[str, Any]]) -> str:
    required = [check for check in checks.values() if check.get("required") is True]
    optional = [check for check in checks.values() if check.get("required") is not True]
    if any(check.get("status") == "failed" for check in required):
        return "failed"
    if all(check.get("status") == "passed" for check in required + optional):
        return "validated"
    if any(check.get("status") == "passed" for check in required + optional):
        return "partially_validated"
    return "failed"


def _span_passed(report: Mapping[str, Any]) -> bool:
    angles = np.asarray(report["principal_angles_radians"], dtype=float)
    projection = report["projection_residual"]
    return bool(
        angles.size > 0
        and np.max(np.abs(angles)) <= _SPAN_TOLERANCE
        and float(projection["summary"]) <= _SPAN_TOLERANCE
    )


def _closure_passed(report: Mapping[str, Any]) -> bool:
    return bool(
        float(report["closure"]["summary"]) <= _CLOSURE_TOLERANCE
        and float(report["antisymmetry"]["summary"]) <= _CLOSURE_TOLERANCE
        and float(report["jacobi"]["summary"]) <= _CLOSURE_TOLERANCE
    )


def _validate_generator_candidate(
    field: FieldBatch,
    generator: GeneratorFamily,
    *,
    residual_evaluator: ResidualEvaluator,
    reference_generator: GeneratorFamily | None,
    finite_transform_epsilons: np.ndarray,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from pdelie.reporting import summarize_generator_family, summarize_verification_report

    checks: dict[str, dict[str, Any]] = {
        "schema": {"required": True, "status": "passed", "report": {"object": "GeneratorFamily"}}
    }

    if _is_translation_compatible(generator):
        verification = verify_translation_generator(
            field,
            generator,
            residual_evaluator,
            epsilon_values=finite_transform_epsilons,
        )
        passed = verification.classification != "failed"
        checks["finite_transform_verification"] = {
            "required": True,
            "status": "passed" if passed else "failed",
            "threshold": "classification != 'failed'",
            "report": summarize_verification_report(verification),
        }
    elif generator.coefficients.shape[0] == 1:
        checks["finite_transform_verification"] = {
            "required": False,
            "status": "unavailable",
            "reason": "candidate_is_not_single_uniform_translation",
        }

    if reference_generator is not None:
        span_report = compare_generator_spans(reference_generator, generator)
        checks["reference_span_comparison"] = {
            "required": True,
            "status": "passed" if _span_passed(span_report) else "failed",
            "threshold": {
                "max_principal_angle": _SPAN_TOLERANCE,
                "projection_residual_summary": _SPAN_TOLERANCE,
            },
            "report": span_report,
        }

    if generator.coefficients.shape[0] > 1:
        try:
            closure_report = diagnose_generator_family_closure(generator)
        except PDELieValidationError as exc:
            checks["closure_diagnostics"] = {
                "required": True,
                "status": "failed",
                "threshold": {
                    "closure": _CLOSURE_TOLERANCE,
                    "antisymmetry": _CLOSURE_TOLERANCE,
                    "jacobi": _CLOSURE_TOLERANCE,
                },
                "error": str(exc),
            }
        else:
            checks["closure_diagnostics"] = {
                "required": True,
                "status": "passed" if _closure_passed(closure_report) else "failed",
                "threshold": {
                    "closure": _CLOSURE_TOLERANCE,
                    "antisymmetry": _CLOSURE_TOLERANCE,
                    "jacobi": _CLOSURE_TOLERANCE,
                },
                "report": closure_report,
            }

    return summarize_generator_family(generator), checks


def _validate_invariant_map_scope(spec: InvariantMapSpec) -> float:
    if spec.construction_method != "uniform_translation":
        raise ScopeValidationError("validate_symmetry_candidate only supports uniform_translation InvariantMapSpec candidates.")
    if spec.domain_validity != "global":
        raise ScopeValidationError("validate_symmetry_candidate only supports global InvariantMapSpec candidates.")
    if spec.diagnostics.get("approximate", False):
        raise ScopeValidationError("validate_symmetry_candidate does not support approximate InvariantMapSpec candidates.")
    if spec.parameters.get("axis", "x") != "x":
        raise ScopeValidationError("validate_symmetry_candidate only supports InvariantMapSpec candidates with axis='x'.")
    if "shift" not in spec.parameters:
        raise SchemaValidationError("uniform_translation InvariantMapSpec candidates must include parameters['shift'].")
    try:
        shift = float(spec.parameters["shift"])
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError("uniform_translation InvariantMapSpec shift must be numeric.") from exc
    if not np.isfinite(shift):
        raise SchemaValidationError("uniform_translation InvariantMapSpec shift must be finite.")
    return shift


def _inverse_spec(spec: InvariantMapSpec, shift: float) -> InvariantMapSpec:
    parameters = dict(spec.parameters)
    parameters["shift"] = -shift
    return InvariantMapSpec(
        generator_metadata=dict(spec.generator_metadata),
        construction_method=spec.construction_method,
        parameters=parameters,
        domain_validity=spec.domain_validity,
        inverse_available=spec.inverse_available,
        diagnostics=dict(spec.diagnostics),
    )


def _validate_invariant_map_candidate(
    field: FieldBatch,
    spec: InvariantMapSpec,
    *,
    residual_evaluator: ResidualEvaluator,
) -> tuple[dict[str, Any], dict[str, Any]]:
    shift = _validate_invariant_map_scope(spec)
    applier = InvariantApplier()
    transformed = applier.apply(field, spec)
    before_rms = _residual_rms(field, residual_evaluator)
    after_rms = _residual_rms(transformed, residual_evaluator)
    absolute_delta = abs(after_rms - before_rms)
    relative_delta = absolute_delta / (abs(before_rms) + _RELATIVE_L2_EPS)
    residual_passed = absolute_delta <= _RESIDUAL_ABSOLUTE_TOLERANCE or relative_delta <= _RESIDUAL_RELATIVE_TOLERANCE

    checks: dict[str, dict[str, Any]] = {
        "schema": {"required": True, "status": "passed", "report": {"object": "InvariantMapSpec"}},
        "residual_stability": {
            "required": True,
            "status": "passed" if residual_passed else "failed",
            "threshold": {
                "absolute_delta": _RESIDUAL_ABSOLUTE_TOLERANCE,
                "relative_delta": _RESIDUAL_RELATIVE_TOLERANCE,
            },
            "report": {
                "residual_rms_before": before_rms,
                "residual_rms_after": after_rms,
                "residual_absolute_rms_delta": float(absolute_delta),
                "residual_relative_rms_delta": float(relative_delta),
                "preprocess_operation": transformed.preprocess_log[-1].get("operation"),
                "preprocess_construction_method": transformed.preprocess_log[-1].get("construction_method"),
            },
        },
    }

    if spec.inverse_available:
        inverted = applier.apply(transformed, _inverse_spec(spec, shift))
        inverse_error = _relative_l2(inverted.values, field.values)
        checks["inverse_consistency"] = {
            "required": True,
            "status": "passed" if inverse_error <= _INVERSE_RELATIVE_L2_TOLERANCE else "failed",
            "threshold": {"relative_l2": _INVERSE_RELATIVE_L2_TOLERANCE},
            "report": {"inverse_relative_l2_error": inverse_error},
        }
    else:
        checks["inverse_consistency"] = {
            "required": False,
            "status": "unavailable",
            "reason": "inverse_not_advertised",
        }

    return spec.to_dict(), checks


def _validate_formula_candidate(
    field: FieldBatch,
    formula: FormulaGeneratorFamily,
    *,
    residual_evaluator: ResidualEvaluator,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from pdelie.reporting import summarize_formula_generator_family

    checks: dict[str, dict[str, Any]] = {
        "schema": {"required": True, "status": "passed", "report": {"object": "FormulaGeneratorFamily"}}
    }

    evaluation_report = _diagnose_formula_generator_family_on_field(formula, field)
    if evaluation_report["failed_component_count"] > 0:
        evaluation_status = "failed"
        evaluation_required = True
    elif evaluation_report["evaluated_component_count"] > 0:
        evaluation_status = "passed"
        evaluation_required = True
    else:
        evaluation_status = "unavailable"
        evaluation_required = False
    checks["formula_evaluation_diagnostics"] = {
        "required": evaluation_required,
        "status": evaluation_status,
        "threshold": {
            "finite_values": True,
            "reciprocal_denominator_floor": _FORMULA_RECIPROCAL_DENOMINATOR_FLOOR,
        },
        "report": evaluation_report,
    }

    if formula.finite_transform_spec is None:
        checks["finite_transform_spec_validation"] = {
            "required": False,
            "status": "unavailable",
            "reason": "finite_transform_spec_not_provided",
        }
    else:
        spec = InvariantMapSpec.from_dict(formula.finite_transform_spec)
        _, finite_transform_checks = _validate_invariant_map_candidate(
            field,
            spec,
            residual_evaluator=residual_evaluator,
        )
        for name, check in finite_transform_checks.items():
            checks[f"finite_transform_{name}"] = check

    return summarize_formula_generator_family(formula), checks


def validate_symmetry_candidate(
    field: FieldBatch,
    candidate: Any,
    *,
    residual_evaluator: ResidualEvaluator,
    reference_generator: GeneratorFamily | Mapping[str, Any] | None = None,
    finite_transform_epsilons: Any | None = None,
    source_candidate_id: Any | None = None,
) -> dict[str, Any]:
    """Validate an externally supplied symmetry candidate under configured empirical checks."""

    _validate_field(field)
    if not isinstance(residual_evaluator, ResidualEvaluator):
        raise SchemaValidationError("residual_evaluator must be a ResidualEvaluator.")
    epsilons = _validate_epsilon_values(finite_transform_epsilons)
    normalized_source_id = _validate_json_compatible(source_candidate_id, name="source_candidate_id")
    normalized_reference = _coerce_reference_generator(reference_generator)
    candidate_kind, normalized_candidate = _coerce_candidate(candidate)

    if candidate_kind == "generator_family":
        assert isinstance(normalized_candidate, GeneratorFamily)
        candidate_summary, checks = _validate_generator_candidate(
            field,
            normalized_candidate,
            residual_evaluator=residual_evaluator,
            reference_generator=normalized_reference,
            finite_transform_epsilons=epsilons,
        )
    elif candidate_kind == "invariant_map_spec":
        assert isinstance(normalized_candidate, InvariantMapSpec)
        if normalized_reference is not None:
            raise SchemaValidationError("reference_generator is only supported for GeneratorFamily candidates.")
        candidate_summary, checks = _validate_invariant_map_candidate(
            field,
            normalized_candidate,
            residual_evaluator=residual_evaluator,
        )
    else:
        assert isinstance(normalized_candidate, FormulaGeneratorFamily)
        if normalized_reference is not None:
            raise SchemaValidationError("reference_generator is only supported for GeneratorFamily candidates.")
        candidate_summary, checks = _validate_formula_candidate(
            field,
            normalized_candidate,
            residual_evaluator=residual_evaluator,
        )

    return _validate_json_compatible(
        {
            "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
            "summary_type": "symmetry_candidate_validation",
            "candidate_kind": candidate_kind,
            "source_candidate_id": normalized_source_id,
            "empirical_interpretation": "configured_validation_not_mathematical_proof",
            "field_shape": list(field.values.shape),
            "equation": field.metadata["parameter_tags"].get("equation"),
            "residual_evaluator": type(residual_evaluator).__name__,
            "finite_transform_epsilons": epsilons.tolist(),
            "thresholds": {
                "invariant_map_residual_absolute_delta": _RESIDUAL_ABSOLUTE_TOLERANCE,
                "invariant_map_residual_relative_delta": _RESIDUAL_RELATIVE_TOLERANCE,
                "invariant_map_inverse_relative_l2": _INVERSE_RELATIVE_L2_TOLERANCE,
                "span_principal_angle": _SPAN_TOLERANCE,
                "span_projection_residual": _SPAN_TOLERANCE,
                "closure": _CLOSURE_TOLERANCE,
                "formula_reciprocal_denominator_floor": _FORMULA_RECIPROCAL_DENOMINATOR_FLOOR,
            },
            "candidate_summary": candidate_summary,
            "configured_validation_checks": list(checks.keys()),
            "check_reports": checks,
            "conclusion": _conclusion(checks),
        },
        name="symmetry candidate validation report",
    )


__all__ = ["validate_symmetry_candidate"]
