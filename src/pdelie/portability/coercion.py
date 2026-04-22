from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pdelie.contracts import GeneratorFamily
from pdelie.errors import SchemaValidationError
from pdelie.portability.manifest import import_generator_family_manifest
from pdelie.portability._validation import _validate_supported_external_family


def coerce_generator_family(source: Any) -> GeneratorFamily:
    if isinstance(source, GeneratorFamily):
        source.validate()
        _validate_supported_external_family(source)
        return source

    if not isinstance(source, Mapping):
        raise SchemaValidationError(
            "coerce_generator_family supports only GeneratorFamily objects, canonical GeneratorFamily payloads, "
            "generator-family manifests, and the legacy 0.1 translation payload."
        )

    if "manifest_type" in source:
        return import_generator_family_manifest(source)

    if "schema_version" in source and "parameterization" in source:
        try:
            generator = GeneratorFamily.from_dict(source)
        except KeyError as exc:
            missing_key = exc.args[0] if exc.args else "<unknown>"
            raise SchemaValidationError(
                f"Invalid canonical GeneratorFamily payload: missing required field {missing_key!r}."
            ) from exc
        _validate_supported_external_family(generator)
        return generator

    raise SchemaValidationError(
        "coerce_generator_family supports only GeneratorFamily objects, canonical GeneratorFamily payloads, "
        "generator-family manifests, and the legacy 0.1 translation payload."
    )


__all__ = ["coerce_generator_family"]
