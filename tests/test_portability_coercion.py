from __future__ import annotations

import importlib

import matplotlib

matplotlib.use("Agg", force=True)

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.figure import Figure

from pdelie import GeneratorFamily, SchemaValidationError, ScopeValidationError, ShapeValidationError
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.portability import (
    coerce_generator_family,
    export_generator_family_manifest,
)
from pdelie.symmetry import (
    compare_generator_spans,
    diagnose_generator_family_closure,
    render_generator_family,
    to_sympy_component_expressions,
)
from pdelie.viz import (
    plot_closure_diagnostics,
    plot_generator_coefficients,
    plot_generator_symbolic_summary,
    plot_span_diagnostics,
)


@pytest.fixture(autouse=True)
def _close_figures() -> None:
    yield
    plt.close("all")


def _make_translation_family() -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={"source": "translation"},
    )


def _x_basis_spec(*, labels: list[str], powers: list[list[int]]) -> dict[str, object]:
    return {
        "variables": ["x"],
        "component_names": ["xi"],
        "basis_terms": [
            {"label": label, "powers": power}
            for label, power in zip(labels, powers)
        ],
        "component_ordering": ["xi"],
        "term_ordering": list(labels),
        "layout": "component_major",
    }


def _velocity_basis_spec(labels: list[str]) -> dict[str, object]:
    return {
        "variables": ["x"],
        "component_names": ["velocity"],
        "basis_terms": [
            {"label": labels[0], "powers": [0]},
            {"label": labels[1], "powers": [1]},
        ],
        "component_ordering": ["velocity"],
        "term_ordering": list(labels),
        "layout": "component_major",
    }


def _make_polynomial_family(
    coefficients: np.ndarray,
    *,
    basis_spec: dict[str, object],
    normalization: str = "runtime_fixture",
    parameterization: str = "polynomial_point_family",
) -> GeneratorFamily:
    return GeneratorFamily(
        parameterization=parameterization,
        coefficients=np.asarray(coefficients, dtype=float),
        basis_spec=basis_spec,
        normalization=normalization,
        diagnostics={},
    )


def test_coerce_generator_family_returns_same_canonical_object_for_in_memory_input() -> None:
    generator = _make_translation_family()

    coerced = coerce_generator_family(generator)

    assert coerced is generator


def test_coerce_generator_family_accepts_canonical_family_payload() -> None:
    generator = _make_polynomial_family(
        np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 1.0]], dtype=float),
        basis_spec=_x_basis_spec(labels=["1", "x", "x^2"], powers=[[0], [1], [2]]),
    )

    coerced = coerce_generator_family(generator.to_dict())

    assert coerced.to_dict() == generator.to_dict()


def test_coerce_generator_family_accepts_manifest_payload() -> None:
    generator = _make_translation_family()
    manifest = export_generator_family_manifest(generator, symbolic=["xi = 1"])

    coerced = coerce_generator_family(manifest)

    assert coerced.to_dict() == generator.to_dict()


def test_coerce_generator_family_upgrades_legacy_translation_payload() -> None:
    legacy_payload = {
        "schema_version": "0.1",
        "parameterization": "polynomial_translation_affine",
        "coefficients": [1.0, 0.0, 0.0, 0.0],
        "normalization": "l2_unit",
        "diagnostics": {},
    }

    coerced = coerce_generator_family(legacy_payload)

    assert coerced.schema_version == "0.2"
    assert coerced.to_dict()["basis_spec"]["variables"] == ["t", "x", "u"]
    np.testing.assert_allclose(coerced.coefficients, np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float))


@pytest.mark.parametrize("value", ["not-a-mapping", 123, 1.5, ["x"]])
def test_coerce_generator_family_rejects_non_mapping_non_family_inputs(value: object) -> None:
    with pytest.raises(SchemaValidationError, match="supports only GeneratorFamily objects"):
        coerce_generator_family(value)


def test_coerce_generator_family_treats_manifest_like_payload_only_as_manifest() -> None:
    payload = {
        "manifest_type": "pdelie.generator_family_export",
        "schema_version": "0.2",
        "parameterization": "polynomial_translation_affine",
        "coefficients": [[1.0, 0.0, 0.0, 0.0]],
        "basis_spec": _translation_generator_basis_spec(),
        "normalization": "l2_unit",
        "diagnostics": {},
    }

    with pytest.raises(SchemaValidationError, match="unknown top-level fields|missing required fields"):
        coerce_generator_family(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"schema_version": "0.2"},
        {"parameterization": "polynomial_translation_affine"},
        {"generator_family": _make_translation_family().to_dict()},
    ],
)
def test_coerce_generator_family_rejects_partial_or_discriminator_free_payloads(
    payload: dict[str, object],
) -> None:
    with pytest.raises(SchemaValidationError, match="supports only GeneratorFamily objects"):
        coerce_generator_family(payload)


def test_coerce_generator_family_rejects_well_formed_but_out_of_scope_parameterizations() -> None:
    payload = {
        "schema_version": "0.2",
        "parameterization": "affine_external_family",
        "coefficients": [[1.0, 0.0]],
        "basis_spec": _x_basis_spec(labels=["1", "x"], powers=[[0], [1]]),
        "normalization": "runtime_fixture",
        "diagnostics": {},
    }

    with pytest.raises(ScopeValidationError, match="only supports polynomial GeneratorFamily parameterizations"):
        coerce_generator_family(payload)


def test_coerce_generator_family_preserves_shape_validation_errors() -> None:
    payload = {
        "schema_version": "0.2",
        "parameterization": "polynomial_translation_affine",
        "coefficients": [1.0, 0.0, 0.0, 0.0],
        "basis_spec": _translation_generator_basis_spec(),
        "normalization": "l2_unit",
        "diagnostics": {},
    }

    with pytest.raises(ShapeValidationError, match="coefficients must be a non-empty two-dimensional array"):
        coerce_generator_family(payload)


def test_coerce_generator_family_rejects_incomplete_canonical_payload_with_typed_schema_error() -> None:
    payload = {
        "schema_version": "0.2",
        "parameterization": "polynomial_translation_affine",
    }

    with pytest.raises(SchemaValidationError, match="missing required field 'coefficients'"):
        coerce_generator_family(payload)


def test_coerced_translation_family_matches_canonical_symbolic_rendering() -> None:
    canonical = _make_translation_family()
    from_dict = coerce_generator_family(canonical.to_dict())
    from_manifest = coerce_generator_family(export_generator_family_manifest(canonical))
    from_legacy = coerce_generator_family(
        {
            "schema_version": "0.1",
            "parameterization": "polynomial_translation_affine",
            "coefficients": [1.0, 0.0, 0.0, 0.0],
            "normalization": "l2_unit",
            "diagnostics": {},
        }
    )

    expected = render_generator_family(canonical)

    assert render_generator_family(from_dict) == expected
    assert render_generator_family(from_manifest) == expected
    assert render_generator_family(from_legacy) == expected


def test_coerced_translation_family_matches_canonical_sympy_expressions_when_available() -> None:
    if importlib.util.find_spec("sympy") is None:
        pytest.skip("sympy is not installed")

    canonical = _make_translation_family()
    coerced = coerce_generator_family(export_generator_family_manifest(canonical))

    assert to_sympy_component_expressions(coerced) == to_sympy_component_expressions(canonical)


def test_coerced_polynomial_family_matches_canonical_span_diagnostics() -> None:
    canonical = _make_polynomial_family(
        np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 1.0]], dtype=float),
        basis_spec=_x_basis_spec(labels=["1", "x", "x^2"], powers=[[0], [1], [2]]),
    )
    coerced = coerce_generator_family(canonical.to_dict())

    report = compare_generator_spans(canonical, coerced)

    assert report["comparison_rank"] == 2
    np.testing.assert_allclose(report["principal_angles_radians"], [0.0, 0.0], atol=1e-7)
    assert report["projection_residual"]["summary"] == pytest.approx(0.0, abs=1e-12)


def test_coerced_fallback_closure_fixture_matches_canonical_closure_diagnostics() -> None:
    canonical = _make_polynomial_family(
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float),
        basis_spec=_velocity_basis_spec(["offset", "linear"]),
    )
    coerced = coerce_generator_family(export_generator_family_manifest(canonical))

    canonical_report = diagnose_generator_family_closure(
        canonical,
        component_targets={"velocity": "x"},
        computation_mode="auto",
    )
    coerced_report = diagnose_generator_family_closure(
        coerced,
        component_targets={"velocity": "x"},
        computation_mode="auto",
    )

    assert coerced_report["computation_mode"] == canonical_report["computation_mode"] == "sampled_projection"
    assert coerced_report["family_rank"] == canonical_report["family_rank"]
    assert coerced_report["closure"]["summary"] == pytest.approx(canonical_report["closure"]["summary"], abs=1e-12)
    assert coerced_report["antisymmetry"]["summary"] == pytest.approx(
        canonical_report["antisymmetry"]["summary"],
        abs=1e-12,
    )
    assert coerced_report["jacobi"]["summary"] == pytest.approx(canonical_report["jacobi"]["summary"], abs=1e-12)
    np.testing.assert_allclose(
        coerced_report["structure_constants"]["tensor"],
        canonical_report["structure_constants"]["tensor"],
        atol=1e-12,
    )


def test_coerced_families_work_with_existing_viz_helpers() -> None:
    translation = _make_translation_family()
    translation_coerced = coerce_generator_family(export_generator_family_manifest(translation))

    span_reference = _make_polynomial_family(
        np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 1.0]], dtype=float),
        basis_spec=_x_basis_spec(labels=["1", "x", "x^2"], powers=[[0], [1], [2]]),
    )
    span_candidate = coerce_generator_family(span_reference.to_dict())
    span_report = compare_generator_spans(span_reference, span_candidate)

    closure_family = _make_polynomial_family(
        np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float),
        basis_spec=_velocity_basis_spec(["offset", "linear"]),
    )
    closure_report = diagnose_generator_family_closure(
        coerce_generator_family(export_generator_family_manifest(closure_family)),
        component_targets={"velocity": "x"},
        computation_mode="auto",
    )

    figures = [
        plot_generator_coefficients(translation_coerced),
        plot_generator_symbolic_summary(translation_coerced),
        plot_span_diagnostics(span_report),
        plot_closure_diagnostics(closure_report),
    ]

    assert all(isinstance(figure, Figure) for figure in figures)
