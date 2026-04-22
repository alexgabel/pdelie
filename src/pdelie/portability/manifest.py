from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any

from pdelie.contracts import GeneratorFamily
from pdelie.errors import SchemaValidationError


MANIFEST_SCHEMA_VERSION = "0.1"
MANIFEST_TYPE = "pdelie.generator_family_export"


def _require_mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SchemaValidationError(f"{name} must be a mapping.")
    return value


def _validate_json_compatible(value: Any, path: str) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise SchemaValidationError(f"{path} keys must be strings.")
            _validate_json_compatible(item, f"{path}[{key!r}]")
        return

    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _validate_json_compatible(item, f"{path}[{index}]")
        return

    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return

    if isinstance(value, float):
        if not math.isfinite(value):
            raise SchemaValidationError(f"{path} must not contain non-finite floats.")
        return

    raise SchemaValidationError(f"{path} is not strict JSON-compatible.")


def _validate_json_dump(payload: dict[str, Any]) -> None:
    try:
        json.dumps(payload, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError("Manifest payload must be strict JSON-compatible.") from exc


def _validate_manifest_generator_family_payload(payload: Any) -> Mapping[str, Any]:
    generator_family_payload = _require_mapping(payload, "generator_family")

    if "schema_version" not in generator_family_payload:
        raise SchemaValidationError(
            "generator_family is missing required canonical GeneratorFamily fields: ['schema_version']."
        )
    if str(generator_family_payload["schema_version"]) != GeneratorFamily.SCHEMA_VERSION:
        raise SchemaValidationError(
            "generator_family must be a canonical GeneratorFamily payload with "
            f"schema_version '{GeneratorFamily.SCHEMA_VERSION}'."
        )

    missing_fields = [
        field
        for field in ("schema_version", "parameterization", "coefficients", "basis_spec", "normalization")
        if field not in generator_family_payload
    ]
    if missing_fields:
        raise SchemaValidationError(
            "generator_family is missing required canonical GeneratorFamily fields: "
            f"{missing_fields}."
        )
    return generator_family_payload


def export_generator_family_manifest(
    generator: GeneratorFamily,
    *,
    pdelie_version: str | None = None,
    symbolic: Any | None = None,
    diagnostics: Mapping[str, Any] | None = None,
    provenance: Mapping[str, Any] | None = None,
    compatibility_hints: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not isinstance(generator, GeneratorFamily):
        raise SchemaValidationError("generator must be an in-memory GeneratorFamily.")
    generator.validate()

    manifest: dict[str, Any] = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_type": MANIFEST_TYPE,
        "generator_family": generator.to_dict(),
    }

    if pdelie_version is not None:
        if not isinstance(pdelie_version, str) or not pdelie_version:
            raise SchemaValidationError("pdelie_version must be a non-empty string when provided.")
        manifest["pdelie_version"] = pdelie_version

    if symbolic is not None:
        manifest["symbolic"] = symbolic

    for name, value in (
        ("diagnostics", diagnostics),
        ("provenance", provenance),
        ("compatibility_hints", compatibility_hints),
    ):
        if value is None:
            continue
        if not isinstance(value, Mapping):
            raise SchemaValidationError(f"{name} must be a mapping when provided.")
        manifest[name] = value

    _validate_json_compatible(manifest, "manifest")
    _validate_json_dump(manifest)
    return manifest


def import_generator_family_manifest(payload: Mapping[str, Any]) -> GeneratorFamily:
    manifest = _require_mapping(payload, "payload")

    missing_fields = [
        field
        for field in ("manifest_schema_version", "manifest_type", "generator_family")
        if field not in manifest
    ]
    if missing_fields:
        raise SchemaValidationError(f"Manifest payload is missing required fields: {missing_fields}.")

    manifest_schema_version = str(manifest["manifest_schema_version"])
    manifest_type = str(manifest["manifest_type"])

    if manifest_schema_version != MANIFEST_SCHEMA_VERSION:
        raise SchemaValidationError(
            f"Unsupported manifest_schema_version: {manifest_schema_version}."
        )
    if manifest_type != MANIFEST_TYPE:
        raise SchemaValidationError(f"Unsupported manifest_type: {manifest_type}.")

    generator_family_payload = _validate_manifest_generator_family_payload(manifest["generator_family"])
    return GeneratorFamily.from_dict(generator_family_payload)
