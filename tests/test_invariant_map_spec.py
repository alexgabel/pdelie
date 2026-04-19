from __future__ import annotations

import json

import numpy as np
import pytest

from pdelie import GeneratorFamily, InvariantMapSpec, SchemaValidationError


def translation_basis_spec() -> dict[str, object]:
    return {
        "variables": ["t", "x", "u"],
        "component_names": ["xi"],
        "basis_terms": [
            {"label": "1", "powers": [0, 0, 0]},
            {"label": "t", "powers": [1, 0, 0]},
            {"label": "x", "powers": [0, 1, 0]},
            {"label": "u", "powers": [0, 0, 1]},
        ],
        "component_ordering": ["xi"],
        "term_ordering": ["1", "t", "x", "u"],
        "layout": "component_major",
    }


def make_translation_generator() -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0]]),
        basis_spec=translation_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )


def make_invariant_map_spec(
    *,
    domain_validity: str = "global",
    diagnostics: dict[str, object] | None = None,
) -> InvariantMapSpec:
    return InvariantMapSpec(
        generator_metadata=make_translation_generator().to_dict(),
        construction_method="uniform_translation",
        parameters={"axis": "x", "shift": 0.25},
        domain_validity=domain_validity,
        inverse_available=True,
        diagnostics={} if diagnostics is None else diagnostics,
    )


def test_invariant_map_spec_round_trip_is_json_safe() -> None:
    spec = make_invariant_map_spec()
    payload = spec.to_dict()
    json.dumps(payload)

    round_trip = InvariantMapSpec.from_dict(payload)
    assert round_trip.construction_method == spec.construction_method
    assert round_trip.domain_validity == spec.domain_validity
    assert round_trip.inverse_available is spec.inverse_available
    assert round_trip.generator_metadata["parameterization"] == "polynomial_translation_affine"
    assert round_trip.parameters["shift"] == spec.parameters["shift"]


def test_invariant_map_spec_rejects_invalid_domain_validity() -> None:
    with pytest.raises(SchemaValidationError, match="Unsupported domain_validity"):
        make_invariant_map_spec(domain_validity="regional")


def test_invariant_map_spec_requires_validity_note_for_non_global_specs() -> None:
    with pytest.raises(SchemaValidationError, match="diagnostics\\['validity_note'\\]"):
        make_invariant_map_spec(domain_validity="local")


def test_invariant_map_spec_allows_non_global_specs_with_explicit_validity_note() -> None:
    spec = make_invariant_map_spec(
        domain_validity="local",
        diagnostics={"validity_note": "Only a local chart is established for this construction."},
    )

    assert spec.domain_validity == "local"
    assert spec.diagnostics["validity_note"] == "Only a local chart is established for this construction."


def test_invariant_map_spec_requires_approximation_note_for_approximate_specs() -> None:
    with pytest.raises(SchemaValidationError, match="diagnostics\\['approximation_note'\\]"):
        make_invariant_map_spec(diagnostics={"approximate": True})


def test_invariant_map_spec_allows_approximate_specs_with_explicit_approximation_note() -> None:
    spec = make_invariant_map_spec(
        diagnostics={
            "approximate": True,
            "approximation_note": "The invariant is only approximate under this fitted construction.",
        }
    )

    assert spec.diagnostics["approximate"] is True
    assert spec.diagnostics["approximation_note"] == "The invariant is only approximate under this fitted construction."


def test_invariant_map_spec_is_importable_from_package_root() -> None:
    assert InvariantMapSpec is not None
