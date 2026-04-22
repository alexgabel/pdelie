from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from pdelie.contracts import GeneratorFamily
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.portability.manifest import import_generator_family_manifest


def _validate_supported_external_family(generator: GeneratorFamily) -> None:
    if not generator.parameterization.startswith("polynomial_"):
        raise ScopeValidationError(
            "coerce_generator_family only supports polynomial GeneratorFamily parameterizations in V0.5 Milestone 2."
        )


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
        generator = GeneratorFamily.from_dict(source)
        _validate_supported_external_family(generator)
        return generator

    raise SchemaValidationError(
        "coerce_generator_family supports only GeneratorFamily objects, canonical GeneratorFamily payloads, "
        "generator-family manifests, and the legacy 0.1 translation payload."
    )


__all__ = ["coerce_generator_family"]
