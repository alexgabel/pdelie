from __future__ import annotations

from typing import Any

import numpy as np

from pdelie.contracts import FieldBatch, GeneratorFamily, InvariantMapSpec
from pdelie.discovery.pysindy_bridge import to_pysindy_trajectories
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.invariants import InvariantApplier
from pdelie.symmetry.parameterization.polynomial_translation import (
    DEFAULT_TRANSLATION_SPAN_TOLERANCE,
    _coerce_translation_coefficients,
    translation_span_distance,
)


_ALIGNMENT_POLICY = {
    "kind": "heuristic_peak_alignment",
    "axis": "x",
    "time_index": 0,
    "var_index": 0,
    "tie_break": "first_index",
    "shift_formula": "x[0] - x[argmax(values[batch, 0, :, 0])]",
}


def _copy_mapping(value: dict[str, Any]) -> dict[str, Any]:
    return {str(key): item for key, item in value.items()}


def _validate_supported_field(field: FieldBatch) -> None:
    field.validate()
    if field.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError(
            "build_translation_canonical_discovery_inputs only supports dims ('batch', 'time', 'x', 'var') in V0.6 Milestone 3."
        )
    if len(field.var_names) != 1:
        raise ScopeValidationError(
            "build_translation_canonical_discovery_inputs only supports a single scalar variable in V0.6 Milestone 3."
        )
    if field.metadata["boundary_conditions"].get("x") != "periodic":
        raise ScopeValidationError(
            "build_translation_canonical_discovery_inputs requires periodic boundary conditions in x."
        )
    if field.mask is not None:
        raise ScopeValidationError(
            "build_translation_canonical_discovery_inputs does not support masked fields in V0.6 Milestone 3."
        )
    if field.values.shape[field.dims.index("batch")] == 0:
        raise SchemaValidationError(
            "build_translation_canonical_discovery_inputs requires at least one batch sample."
        )


def _validate_translation_generator(generator: GeneratorFamily) -> GeneratorFamily:
    generator.validate()
    if generator.parameterization != "polynomial_translation_affine":
        raise ScopeValidationError(
            "build_translation_canonical_discovery_inputs only supports polynomial_translation_affine generators."
        )

    coefficients = _coerce_translation_coefficients(generator.coefficients)
    span_distance = translation_span_distance(coefficients)
    if span_distance > DEFAULT_TRANSLATION_SPAN_TOLERANCE:
        raise ScopeValidationError(
            "build_translation_canonical_discovery_inputs requires a generator within the stable translation-span tolerance."
        )
    return generator


def _normalize_generator_family(generator_family: object) -> tuple[GeneratorFamily, str]:
    if not isinstance(generator_family, GeneratorFamily):
        raise SchemaValidationError("generator_family must be a GeneratorFamily object.")
    return _validate_translation_generator(generator_family), "generator_family"


def _normalize_invariant_spec_template(
    invariant_spec_template: object,
) -> tuple[GeneratorFamily, str]:
    if not isinstance(invariant_spec_template, InvariantMapSpec):
        raise SchemaValidationError("invariant_spec_template must be an InvariantMapSpec object.")

    invariant_spec_template.validate()
    if invariant_spec_template.construction_method != "uniform_translation":
        raise ScopeValidationError(
            "build_translation_canonical_discovery_inputs only supports 'uniform_translation' invariant templates."
        )
    if invariant_spec_template.domain_validity != "global":
        raise ScopeValidationError(
            "build_translation_canonical_discovery_inputs only supports global invariant templates."
        )
    if invariant_spec_template.diagnostics.get("approximate", False):
        raise ScopeValidationError(
            "build_translation_canonical_discovery_inputs does not support approximate invariant templates."
        )

    parameters = dict(invariant_spec_template.parameters)
    if "shift" in parameters:
        raise SchemaValidationError(
            "invariant_spec_template parameters must not include 'shift' in V0.6 Milestone 3."
        )
    unsupported_keys = sorted(key for key in parameters if key != "axis")
    if unsupported_keys:
        raise SchemaValidationError(
            f"invariant_spec_template parameters include unsupported keys: {unsupported_keys}."
        )
    axis = parameters.get("axis", "x")
    if axis != "x":
        raise ScopeValidationError(
            "build_translation_canonical_discovery_inputs only supports invariant templates along x."
        )

    try:
        generator = GeneratorFamily.from_dict(invariant_spec_template.generator_metadata)
    except KeyError as exc:
        missing_key = exc.args[0] if exc.args else "<unknown>"
        raise SchemaValidationError(
            f"invariant_spec_template.generator_metadata is missing required GeneratorFamily field {missing_key!r}."
        ) from exc

    return _validate_translation_generator(generator), "invariant_spec_template"


def _single_sample_fields(field: FieldBatch) -> list[FieldBatch]:
    return [
        FieldBatch(
            values=field.values[index : index + 1].copy(),
            dims=field.dims,
            coords={name: coord.copy() for name, coord in field.coords.items()},
            var_names=list(field.var_names),
            metadata=dict(field.metadata),
            preprocess_log=list(field.preprocess_log),
            mask=None,
        )
        for index in range(field.values.shape[0])
    ]


def _compute_alignment_shift(sample: FieldBatch) -> float:
    x = np.asarray(sample.coords["x"], dtype=float)
    peak_index = int(np.argmax(np.asarray(sample.values[0, 0, :, 0], dtype=float)))
    return float(x[0] - x[peak_index])


def _make_internal_spec(generator_metadata: dict[str, object], shift: float) -> InvariantMapSpec:
    return InvariantMapSpec(
        generator_metadata=generator_metadata,
        construction_method="uniform_translation",
        parameters={"axis": "x", "shift": float(shift)},
        domain_validity="global",
        inverse_available=True,
        diagnostics={},
    )


def _reassemble_transformed_field(
    field: FieldBatch,
    transformed_samples: list[FieldBatch],
    *,
    input_mode: str,
    alignment_shifts: list[float],
) -> FieldBatch:
    values = np.concatenate([sample.values for sample in transformed_samples], axis=field.dims.index("batch"))
    preprocess_entry = {
        "operation": "translation_canonical_discovery_inputs",
        "construction_method": "uniform_translation",
        "alignment_policy": dict(_ALIGNMENT_POLICY),
        "alignment_shifts": [float(shift) for shift in alignment_shifts],
        "input_mode": input_mode,
    }
    return FieldBatch(
        values=values,
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=dict(field.metadata),
        preprocess_log=[*field.preprocess_log, preprocess_entry],
        mask=None,
    )


def build_translation_canonical_discovery_inputs(
    field: FieldBatch,
    *,
    generator_family: GeneratorFamily | None = None,
    invariant_spec_template: InvariantMapSpec | None = None,
) -> dict[str, object]:
    _validate_supported_field(field)

    if (generator_family is None) == (invariant_spec_template is None):
        raise SchemaValidationError(
            "Exactly one of generator_family or invariant_spec_template must be provided."
        )

    if generator_family is not None:
        generator, input_mode = _normalize_generator_family(generator_family)
    else:
        generator, input_mode = _normalize_invariant_spec_template(invariant_spec_template)

    generator_metadata = generator.to_dict()
    applier = InvariantApplier()
    transformed_samples: list[FieldBatch] = []
    alignment_shifts: list[float] = []
    for sample in _single_sample_fields(field):
        shift = _compute_alignment_shift(sample)
        transformed_samples.append(applier.apply(sample, _make_internal_spec(generator_metadata, shift)))
        alignment_shifts.append(shift)

    transformed_field = _reassemble_transformed_field(
        field,
        transformed_samples,
        input_mode=input_mode,
        alignment_shifts=alignment_shifts,
    )
    trajectories, time_values, feature_names = to_pysindy_trajectories(transformed_field)

    return {
        "transformed_field": transformed_field,
        "trajectories": trajectories,
        "time_values": time_values,
        "feature_names": feature_names,
        "generator_metadata": _copy_mapping(generator_metadata),
        "construction_method": "uniform_translation",
        "alignment_policy": dict(_ALIGNMENT_POLICY),
        "alignment_shifts": [float(shift) for shift in alignment_shifts],
        "provenance": {
            "input_mode": input_mode,
            "bridge": "to_pysindy_trajectories",
            "runtime_only": True,
        },
    }
