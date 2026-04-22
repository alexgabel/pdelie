from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie import GeneratorFamily, SchemaValidationError, ScopeValidationError
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.portability import (
    export_generator_family_manifest,
    import_generator_family_manifest,
)


def _make_translation_family() -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={"source": "translation"},
    )


def _make_algebraic_family(*, parameterization: str = "polynomial_point_family") -> GeneratorFamily:
    return GeneratorFamily(
        parameterization=parameterization,
        coefficients=np.array(
            [
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 1.0],
            ],
            dtype=float,
        ),
        basis_spec={
            "variables": ["x"],
            "component_names": ["xi"],
            "basis_terms": [
                {"label": "1", "powers": [0]},
                {"label": "x", "powers": [1]},
                {"label": "x^2", "powers": [2]},
            ],
            "component_ordering": ["xi"],
            "term_ordering": ["1", "x", "x^2"],
            "layout": "component_major",
        },
        normalization="none",
        generator_names=["const", "affine_plus_quadratic"],
        diagnostics={"family": "algebraic"},
    )


def test_manifest_export_import_round_trip_for_translation_family() -> None:
    generator = _make_translation_family()

    manifest = export_generator_family_manifest(generator)
    imported = import_generator_family_manifest(manifest)

    assert manifest["manifest_schema_version"] == "0.1"
    assert manifest["manifest_type"] == "pdelie.generator_family_export"
    assert manifest["generator_family"] == generator.to_dict()
    assert imported.to_dict() == generator.to_dict()


def test_manifest_export_import_round_trip_for_non_translation_family() -> None:
    generator = _make_algebraic_family()

    manifest = export_generator_family_manifest(generator)
    imported = import_generator_family_manifest(manifest)

    assert manifest["generator_family"] == generator.to_dict()
    assert imported.to_dict() == generator.to_dict()


def test_manifest_export_rejects_well_formed_but_out_of_scope_parameterizations() -> None:
    generator = _make_algebraic_family(parameterization="affine_external_family")

    with pytest.raises(
        ScopeValidationError,
        match="only supports polynomial GeneratorFamily parameterizations",
    ):
        export_generator_family_manifest(generator)


def test_manifest_import_rejects_well_formed_but_out_of_scope_parameterizations() -> None:
    generator = _make_algebraic_family(parameterization="affine_external_family")
    manifest = {
        "manifest_schema_version": "0.1",
        "manifest_type": "pdelie.generator_family_export",
        "generator_family": generator.to_dict(),
    }

    with pytest.raises(
        ScopeValidationError,
        match="only supports polynomial GeneratorFamily parameterizations",
    ):
        import_generator_family_manifest(manifest)


def test_manifest_supports_literal_json_round_trip() -> None:
    generator = _make_translation_family()

    manifest = export_generator_family_manifest(
        generator,
        pdelie_version="0.5.0",
        symbolic=["xi = 1"],
        diagnostics={"stage": "m1"},
        provenance={"source": "unit-test"},
        compatibility_hints={"downstream": "narrow-translation"},
    )

    loaded_manifest = json.loads(json.dumps(manifest, allow_nan=False))
    imported = import_generator_family_manifest(loaded_manifest)

    assert loaded_manifest == manifest
    assert imported.to_dict() == generator.to_dict()


def test_manifest_optional_metadata_is_non_authoritative() -> None:
    generator = _make_translation_family()

    manifest_a = export_generator_family_manifest(
        generator,
        pdelie_version="0.5.0a1",
        symbolic=["xi = 1"],
        diagnostics={"tag": "a"},
        provenance={"source": "first"},
        compatibility_hints={"backend": "alpha"},
    )
    manifest_b = export_generator_family_manifest(
        generator,
        pdelie_version="0.5.0",
        symbolic=["translation"],
        diagnostics={"tag": "b"},
        provenance={"source": "second"},
        compatibility_hints={"backend": "beta"},
    )

    imported_a = import_generator_family_manifest(manifest_a)
    imported_b = import_generator_family_manifest(manifest_b)

    assert imported_a.to_dict() == generator.to_dict()
    assert imported_b.to_dict() == generator.to_dict()


@pytest.mark.parametrize(
    ("payload", "match"),
    [
        ({}, "missing required fields"),
        (
            {
                "manifest_type": "pdelie.generator_family_export",
                "generator_family": _make_translation_family().to_dict(),
            },
            "missing required fields",
        ),
        (
            {
                "manifest_schema_version": "0.1",
                "generator_family": _make_translation_family().to_dict(),
            },
            "missing required fields",
        ),
        (
            {
                "manifest_schema_version": "0.1",
                "manifest_type": "pdelie.generator_family_export",
            },
            "missing required fields",
        ),
        ("not-a-mapping", "payload must be a mapping"),
        (
            {
                "manifest_schema_version": "0.1",
                "manifest_type": "wrong.type",
                "generator_family": _make_translation_family().to_dict(),
            },
            "Unsupported manifest_type",
        ),
        (
            {
                "manifest_schema_version": "0.2",
                "manifest_type": "pdelie.generator_family_export",
                "generator_family": _make_translation_family().to_dict(),
            },
            "Unsupported manifest_schema_version",
        ),
    ],
)
def test_manifest_import_rejects_malformed_manifest_shapes(payload: object, match: str) -> None:
    with pytest.raises(SchemaValidationError, match=match):
        import_generator_family_manifest(payload)  # type: ignore[arg-type]


def test_manifest_import_rejects_unknown_top_level_fields() -> None:
    manifest = export_generator_family_manifest(_make_translation_family())
    manifest["unexpected"] = "field"

    with pytest.raises(SchemaValidationError, match="unknown top-level fields"):
        import_generator_family_manifest(manifest)


def test_manifest_import_rejects_legacy_nested_generator_family_payload() -> None:
    manifest = {
        "manifest_schema_version": "0.1",
        "manifest_type": "pdelie.generator_family_export",
        "generator_family": {
            "schema_version": "0.1",
            "parameterization": "polynomial_translation_affine",
            "coefficients": [1.0, 0.0, 0.0, 0.0],
            "normalization": "l2_unit",
            "diagnostics": {},
        },
    }

    with pytest.raises(SchemaValidationError, match="canonical GeneratorFamily payload"):
        import_generator_family_manifest(manifest)


def test_manifest_import_propagates_typed_canonical_nested_payload_errors() -> None:
    manifest = export_generator_family_manifest(_make_translation_family())
    manifest["generator_family"] = {
        "schema_version": "0.2",
        "parameterization": "polynomial_translation_affine",
        "coefficients": [[1.0, 0.0, 0.0, 0.0]],
        "basis_spec": _translation_generator_basis_spec(),
        "normalization": "l2_unit",
        "diagnostics": "not-a-mapping",
    }

    with pytest.raises(SchemaValidationError, match="diagnostics must be a mapping"):
        import_generator_family_manifest(manifest)


@pytest.mark.parametrize(
    "field_name,value,match",
    [
        ("diagnostics", {"bad": float("nan")}, "non-finite"),
        ("diagnostics", {1: "value"}, "keys must be strings"),
        ("provenance", {"ok": object()}, "not strict JSON-compatible"),
        ("compatibility_hints", ["not", "a", "mapping"], "must be a mapping"),
    ],
)
def test_manifest_import_rejects_invalid_recognized_optional_metadata(
    field_name: str,
    value: object,
    match: str,
) -> None:
    manifest = export_generator_family_manifest(_make_translation_family())
    manifest[field_name] = value

    with pytest.raises(SchemaValidationError, match=match):
        import_generator_family_manifest(manifest)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"diagnostics": {"bad": float("nan")}},
        {"diagnostics": {"bad": float("inf")}},
    ],
)
def test_manifest_export_rejects_non_finite_optional_metadata(kwargs: dict[str, object]) -> None:
    with pytest.raises(SchemaValidationError, match="non-finite"):
        export_generator_family_manifest(_make_translation_family(), **kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"diagnostics": {1: "value"}},
        {"provenance": {"ok": object()}},
        {"compatibility_hints": ["not", "a", "mapping"]},
    ],
)
def test_manifest_export_rejects_non_strict_json_optional_metadata(kwargs: dict[str, object]) -> None:
    with pytest.raises(SchemaValidationError):
        export_generator_family_manifest(_make_translation_family(), **kwargs)
