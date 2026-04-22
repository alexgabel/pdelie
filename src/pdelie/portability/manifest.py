from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any

from pdelie.contracts import GeneratorFamily
from pdelie.errors import SchemaValidationError
from pdelie.portability._validation import _validate_supported_external_family


MANIFEST_SCHEMA_VERSION = "0.1"
MANIFEST_TYPE = "pdelie.generator_family_export"
_REQUIRED_MANIFEST_FIELDS = frozenset({"manifest_schema_version", "manifest_type", "generator_family"})
_OPTIONAL_MANIFEST_FIELDS = frozenset(
    {"pdelie_version", "symbolic", "diagnostics", "provenance", "compatibility_hints"}
)
_ALLOWED_MANIFEST_FIELDS = _REQUIRED_MANIFEST_FIELDS | _OPTIONAL_MANIFEST_FIELDS


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


def _validate_manifest_top_level_fields(manifest: Mapping[str, Any]) -> None:
    unknown_fields = sorted(set(manifest) - _ALLOWED_MANIFEST_FIELDS)
    if unknown_fields:
        raise SchemaValidationError(
            f"Manifest payload includes unknown top-level fields: {unknown_fields}."
        )


def _validate_manifest_optional_metadata(manifest: Mapping[str, Any]) -> None:
    if "pdelie_version" in manifest:
        value = manifest["pdelie_version"]
        if not isinstance(value, str) or not value:
            raise SchemaValidationError("pdelie_version must be a non-empty string when provided.")

    if "symbolic" in manifest:
        _validate_json_compatible(manifest["symbolic"], "manifest['symbolic']")

    for name in ("diagnostics", "provenance", "compatibility_hints"):
        if name not in manifest:
            continue
        value = manifest[name]
        if not isinstance(value, Mapping):
            raise SchemaValidationError(f"{name} must be a mapping when provided.")
        _validate_json_compatible(value, f"manifest['{name}']")


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
    _validate_supported_external_family(generator)

    manifest: dict[str, Any] = {
        "manifest_schema_version": MANIFEST_SCHEMA_VERSION,
        "manifest_type": MANIFEST_TYPE,
        "generator_family": generator.to_dict(),
    }

    if pdelie_version is not None:
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

    _validate_manifest_top_level_fields(manifest)
    _validate_manifest_optional_metadata(manifest)
    _validate_json_compatible(manifest, "manifest")
    _validate_json_dump(manifest)
    return manifest


def import_generator_family_manifest(payload: Mapping[str, Any]) -> GeneratorFamily:
    manifest = _require_mapping(payload, "payload")
    _validate_manifest_top_level_fields(manifest)

    missing_fields = [
        field
        for field in _REQUIRED_MANIFEST_FIELDS
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

    _validate_manifest_optional_metadata(manifest)
    generator_family_payload = _validate_manifest_generator_family_payload(manifest["generator_family"])
    generator = GeneratorFamily.from_dict(generator_family_payload)
    _validate_supported_external_family(generator)
    return generator
