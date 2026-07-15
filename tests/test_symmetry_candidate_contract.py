"""v0.30.1 SymmetryCandidate contract tests."""

from __future__ import annotations

import json

import numpy as np
import pytest

import pdelie
from pdelie.contracts import GeneratorFamily, InvariantMapSpec
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.symmetry import (
    REPRESENTATION_TYPES,
    SymmetryCandidate,
    build_symmetry_candidate,
    summarize_symmetry_candidate,
)
from pdelie.symmetry.formula import FormulaGeneratorFamily


def _minimal_generator_family() -> GeneratorFamily:
    """A minimal valid GeneratorFamily for candidate wrapping.

    Uses a single unit-norm vector (e_0) so the l2_unit normalization
    check passes.
    """
    from pdelie.contracts import _translation_generator_basis_spec

    basis = _translation_generator_basis_spec()
    width = len(basis["component_names"]) * len(basis["basis_terms"])
    coefficients = np.zeros((1, width))
    coefficients[0, 0] = 1.0  # unit vector along the first basis direction
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=coefficients,
        basis_spec=basis,
        normalization="l2_unit",
    )


def _minimal_formula_generator_family() -> FormulaGeneratorFamily:
    """A minimal valid FormulaGeneratorFamily for candidate wrapping."""
    return FormulaGeneratorFamily(
        formula_generators=[
            {
                "name": "translation_test",
                "components": {
                    "tau": {"node": "const", "value": 1.0},
                    "xi": {"node": "const", "value": 0.0},
                    "phi": {"node": "const", "value": 0.0},
                },
                "metadata": {"description": "test formula generator"},
            }
        ],
        diagnostics={},
    )


def _minimal_invariant_map_spec() -> InvariantMapSpec:
    """A minimal valid InvariantMapSpec for candidate wrapping."""
    return InvariantMapSpec(
        generator_metadata={"parameterization": "polynomial_translation_affine"},
        construction_method="polynomial_translation_svd",
        parameters={},
        domain_validity="global",
        inverse_available=True,
        diagnostics={},
    )


# ---------------------------------------------------------------------------
# 1. Each implemented representation round-trips.
# ---------------------------------------------------------------------------


def test_symmetry_candidate_wraps_generator_family() -> None:
    payload = _minimal_generator_family()
    candidate = build_symmetry_candidate(
        candidate_id="test-gf-1",
        representation_type="generator_family",
        payload=payload,
        source_method="polynomial_translation_svd",
    )
    assert candidate.representation_type == "generator_family"
    assert candidate.payload is payload
    summary = summarize_symmetry_candidate(candidate)
    assert summary["representation_type"] == "generator_family"
    assert summary["candidate_id"] == "test-gf-1"
    assert summary["source_method"] == "polynomial_translation_svd"
    # payload_summary must be strict-JSON.
    json.dumps(summary, allow_nan=False)


def test_symmetry_candidate_wraps_formula_generator_family() -> None:
    payload = _minimal_formula_generator_family()
    candidate = build_symmetry_candidate(
        candidate_id="test-fgf-1",
        representation_type="formula_generator_family",
        payload=payload,
        source_method="external_method_v0_30_1_prototype",
    )
    assert candidate.representation_type == "formula_generator_family"
    summary = summarize_symmetry_candidate(candidate)
    assert summary["payload_summary"]["parameterization"] == "formula_generator_family"
    json.dumps(summary, allow_nan=False)


def test_symmetry_candidate_wraps_invariant_map_spec() -> None:
    payload = _minimal_invariant_map_spec()
    candidate = build_symmetry_candidate(
        candidate_id="test-ims-1",
        representation_type="invariant_map_spec",
        payload=payload,
        source_method="polynomial_translation_svd",
    )
    assert candidate.representation_type == "invariant_map_spec"
    summary = summarize_symmetry_candidate(candidate)
    assert summary["payload_summary"]["construction_method"] == "polynomial_translation_svd"
    json.dumps(summary, allow_nan=False)


# ---------------------------------------------------------------------------
# 2. Invalid discriminator/payload combinations reject.
# ---------------------------------------------------------------------------


def test_symmetry_candidate_rejects_unknown_representation_type() -> None:
    payload = _minimal_generator_family()
    with pytest.raises(SchemaValidationError, match="representation_type"):
        SymmetryCandidate(
            candidate_id="bad",
            representation_type="totally_made_up",
            payload=payload,
            source_method="test",
        )


def test_symmetry_candidate_rejects_generator_family_payload_type_mismatch() -> None:
    with pytest.raises(SchemaValidationError, match="GeneratorFamily"):
        SymmetryCandidate(
            candidate_id="bad",
            representation_type="generator_family",
            payload={"not": "a generator family"},
            source_method="test",
        )


def test_symmetry_candidate_rejects_formula_generator_family_payload_type_mismatch() -> None:
    payload = _minimal_generator_family()  # wrong type
    with pytest.raises(SchemaValidationError, match="FormulaGeneratorFamily"):
        SymmetryCandidate(
            candidate_id="bad",
            representation_type="formula_generator_family",
            payload=payload,
            source_method="test",
        )


def test_symmetry_candidate_rejects_invariant_map_spec_payload_type_mismatch() -> None:
    payload = _minimal_generator_family()  # wrong type
    with pytest.raises(SchemaValidationError, match="InvariantMapSpec"):
        SymmetryCandidate(
            candidate_id="bad",
            representation_type="invariant_map_spec",
            payload=payload,
            source_method="test",
        )


def test_symmetry_candidate_rejects_empty_candidate_id() -> None:
    payload = _minimal_generator_family()
    with pytest.raises(SchemaValidationError, match="candidate_id"):
        SymmetryCandidate(
            candidate_id="",
            representation_type="generator_family",
            payload=payload,
            source_method="test",
        )


def test_symmetry_candidate_rejects_empty_source_method() -> None:
    payload = _minimal_generator_family()
    with pytest.raises(SchemaValidationError, match="source_method"):
        SymmetryCandidate(
            candidate_id="test",
            representation_type="generator_family",
            payload=payload,
            source_method="",
        )


def test_symmetry_candidate_rejects_bad_mathematical_status() -> None:
    payload = _minimal_generator_family()
    with pytest.raises(SchemaValidationError, match="mathematical_status"):
        SymmetryCandidate(
            candidate_id="test",
            representation_type="generator_family",
            payload=payload,
            source_method="test",
            mathematical_status="proven_by_group_theory",  # not allowed
        )


def test_symmetry_candidate_rejects_bad_executable_status() -> None:
    payload = _minimal_generator_family()
    with pytest.raises(SchemaValidationError, match="executable_status"):
        SymmetryCandidate(
            candidate_id="test",
            representation_type="generator_family",
            payload=payload,
            source_method="test",
            executable_status="maybe",  # not allowed
        )


# ---------------------------------------------------------------------------
# 3. Reserved representation types are not constructible with a payload.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "reserved_type",
    [
        "matrix_lie_algebra",
        "coordinate_vector_field",
        "finite_transform_spec",
        "latent_generator_reference",
    ],
)
def test_reserved_representation_types_are_in_the_set(reserved_type: str) -> None:
    assert reserved_type in REPRESENTATION_TYPES


@pytest.mark.parametrize(
    "reserved_type",
    [
        "matrix_lie_algebra",
        "coordinate_vector_field",
        "finite_transform_spec",
        "latent_generator_reference",
    ],
)
def test_reserved_representation_type_rejects_a_payload(reserved_type: str) -> None:
    """v0.32a hardening: reserved types raise on any public construction,
    regardless of whether ``payload`` is None or a real representation."""
    payload = _minimal_generator_family()
    with pytest.raises(ScopeValidationError, match="reserved"):
        SymmetryCandidate(
            candidate_id="reserved-test",
            representation_type=reserved_type,
            payload=payload,
            source_method="test",
        )


@pytest.mark.parametrize(
    "reserved_type",
    [
        "matrix_lie_algebra",
        "coordinate_vector_field",
        "finite_transform_spec",
        "latent_generator_reference",
    ],
)
def test_reserved_representation_type_rejects_none_payload_too(
    reserved_type: str,
) -> None:
    """v0.32a hardening: reserved+payload=None also raises. Previously a
    UserWarning-gated placeholder was permitted; that path produced a
    zombie candidate with ``payload_summary=None`` that leaked through
    downstream reporting. The v0.32a hardening removes it entirely.
    """
    with pytest.raises(ScopeValidationError, match="reserved"):
        SymmetryCandidate(
            candidate_id="reserved-none-test",
            representation_type=reserved_type,
            payload=None,
            source_method="test",
        )


@pytest.mark.parametrize(
    "reserved_type",
    [
        "matrix_lie_algebra",
        "coordinate_vector_field",
        "finite_transform_spec",
        "latent_generator_reference",
    ],
)
def test_build_symmetry_candidate_rejects_reserved_types(
    reserved_type: str,
) -> None:
    """The public :func:`build_symmetry_candidate` entry point rejects
    reserved types with the same guard as direct constructor use.
    """
    with pytest.raises(ScopeValidationError, match="reserved"):
        build_symmetry_candidate(
            candidate_id="reserved-build-test",
            representation_type=reserved_type,
            payload=None,
            source_method="test",
        )


def test_no_warning_only_zombie_candidate_for_reserved_types() -> None:
    """v0.32a: no code path may produce a serializable SymmetryCandidate
    with a reserved discriminator + ``payload=None`` outside the private
    test-only construction hook. Uses :mod:`warnings` catcher to verify
    the removed placeholder path does NOT emit a UserWarning (because it
    now raises before reaching the warn call).
    """
    import warnings as _warnings

    with _warnings.catch_warnings(record=True) as caught:
        _warnings.simplefilter("always")
        with pytest.raises(ScopeValidationError):
            build_symmetry_candidate(
                candidate_id="zombie-check",
                representation_type="matrix_lie_algebra",
                payload=None,
                source_method="test",
            )
    zombie_warnings = [
        w for w in caught if "reserved" in str(w.message).lower()
    ]
    assert not zombie_warnings, (
        f"v0.32a hardening removed the warning path; expected no reserved-"
        f"discriminator warning but got: {zombie_warnings!r}"
    )


# ---------------------------------------------------------------------------
# 4. NaN/Inf in provenance rejects.
# ---------------------------------------------------------------------------


def test_symmetry_candidate_provenance_rejects_nan() -> None:
    payload = _minimal_generator_family()
    with pytest.raises(SchemaValidationError):
        SymmetryCandidate(
            candidate_id="test",
            representation_type="generator_family",
            payload=payload,
            source_method="test",
            provenance={"score": float("nan")},
        )


def test_symmetry_candidate_provenance_rejects_inf() -> None:
    payload = _minimal_generator_family()
    with pytest.raises(SchemaValidationError):
        SymmetryCandidate(
            candidate_id="test",
            representation_type="generator_family",
            payload=payload,
            source_method="test",
            provenance={"score": float("inf")},
        )


# ---------------------------------------------------------------------------
# 5. No validation success is inferred.
# ---------------------------------------------------------------------------


def test_default_mathematical_status_is_candidate_only() -> None:
    """Wrapping does NOT imply the candidate has been validated."""
    payload = _minimal_generator_family()
    candidate = build_symmetry_candidate(
        candidate_id="test",
        representation_type="generator_family",
        payload=payload,
        source_method="test",
    )
    assert candidate.mathematical_status == "candidate_only"


def test_summary_carries_candidate_only_by_default() -> None:
    payload = _minimal_generator_family()
    candidate = build_symmetry_candidate(
        candidate_id="test",
        representation_type="generator_family",
        payload=payload,
        source_method="test",
    )
    summary = summarize_symmetry_candidate(candidate)
    assert summary["mathematical_status"] == "candidate_only"


# ---------------------------------------------------------------------------
# 6. Root exports absent.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "forbidden_name",
    [
        "SymmetryCandidate",
        "SymmetryMethod",
        "SymmetryMethodResult",
        "SymmetryMethodMetadata",
        "SymmetryMethodSpec",
        "build_symmetry_candidate",
        "summarize_symmetry_candidate",
        "REPRESENTATION_TYPES",
        "register_symmetry_method",
        "get_symmetry_method",
        "list_symmetry_methods",
        "run_symmetry_method",
        "discover_symmetries",
    ],
)
def test_no_root_pdelie_export_for_v0_30_1_names(forbidden_name: str) -> None:
    assert not hasattr(pdelie, forbidden_name), (
        f"root pdelie must not export {forbidden_name!r}"
    )


# ---------------------------------------------------------------------------
# 7. NumPy arrays are normalized safely.
# ---------------------------------------------------------------------------


def test_generator_family_summary_records_coefficients_shape() -> None:
    payload = _minimal_generator_family()
    candidate = build_symmetry_candidate(
        candidate_id="test",
        representation_type="generator_family",
        payload=payload,
        source_method="test",
    )
    summary = summarize_symmetry_candidate(candidate)
    assert summary["payload_summary"]["coefficients_shape"] == list(
        payload.coefficients.shape
    )
    assert summary["payload_summary"]["coefficients_finite"] is True


def test_generator_family_summary_is_strict_json() -> None:
    payload = _minimal_generator_family()
    candidate = build_symmetry_candidate(
        candidate_id="test",
        representation_type="generator_family",
        payload=payload,
        source_method="test",
    )
    summary = summarize_symmetry_candidate(candidate)
    roundtrip = json.loads(json.dumps(summary, allow_nan=False))
    assert roundtrip == summary
