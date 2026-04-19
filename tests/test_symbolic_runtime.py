from __future__ import annotations

import importlib

import numpy as np
import pytest

from pdelie import GeneratorFamily
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.symmetry import render_generator_family, to_sympy_component_expressions


PARTIAL_T = "\u2202t"
PARTIAL_X = "\u2202x"
PARTIAL_U = "\u2202u"


def _txu_basis_spec() -> dict[str, object]:
    return {
        "variables": ["t", "x", "u"],
        "component_names": ["tau", "xi", "phi"],
        "basis_terms": [
            {"label": "1", "powers": [0, 0, 0]},
            {"label": "t", "powers": [1, 0, 0]},
            {"label": "x", "powers": [0, 1, 0]},
            {"label": "u", "powers": [0, 0, 1]},
        ],
        "component_ordering": ["tau", "xi", "phi"],
        "term_ordering": ["1", "t", "x", "u"],
        "layout": "component_major",
    }


def _rotation_basis_spec() -> dict[str, object]:
    return {
        "variables": ["x", "y"],
        "component_names": ["xi_x", "xi_y"],
        "basis_terms": [
            {"label": "x", "powers": [1, 0]},
            {"label": "y", "powers": [0, 1]},
        ],
        "component_ordering": ["xi_x", "xi_y"],
        "term_ordering": ["x", "y"],
        "layout": "component_major",
    }


def _make_generator(
    coefficients: np.ndarray,
    *,
    basis_spec: dict[str, object],
    normalization: str = "runtime_fixture",
    parameterization: str = "algebraic_fixture",
) -> GeneratorFamily:
    return GeneratorFamily(
        parameterization=parameterization,
        coefficients=np.asarray(coefficients, dtype=float),
        basis_spec=basis_spec,
        normalization=normalization,
        diagnostics={},
    )


def test_render_generator_family_renders_canonical_translation_deterministically() -> None:
    generator = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        parameterization="polynomial_translation_affine",
    )

    assert render_generator_family(generator) == [f"X_1 = {PARTIAL_X}"]


def test_render_generator_family_renders_legacy_upgraded_translation_like_canonical_family() -> None:
    legacy_payload = {
        "schema_version": "0.1",
        "parameterization": "polynomial_translation_affine",
        "coefficients": [1.0, 0.0, 0.0, 0.0],
        "normalization": "l2_unit",
        "diagnostics": {},
    }
    legacy_generator = GeneratorFamily.from_dict(legacy_payload)
    canonical_generator = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        parameterization="polynomial_translation_affine",
    )

    assert render_generator_family(legacy_generator) == render_generator_family(canonical_generator)


def test_render_generator_family_supports_family_shaped_two_row_coefficients() -> None:
    generator = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        parameterization="polynomial_translation_affine",
    )

    assert render_generator_family(generator) == [
        f"X_1 = {PARTIAL_X}",
        f"X_2 = t{PARTIAL_X}",
    ]


def test_render_generator_family_renders_scaling_and_mixed_affine_fixtures_deterministically() -> None:
    scaling = _make_generator(
        np.array([[0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -1.0]], dtype=float),
        basis_spec=_txu_basis_spec(),
    )
    mixed_affine = _make_generator(
        np.array([[0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_txu_basis_spec(),
    )

    assert render_generator_family(scaling) == [f"X_1 = t{PARTIAL_T} + x{PARTIAL_X} - u{PARTIAL_U}"]
    assert render_generator_family(mixed_affine) == [f"X_1 = x{PARTIAL_T} + {PARTIAL_X}"]


def test_render_generator_family_respects_anchor_and_none_display_normalization() -> None:
    generator = _make_generator(
        np.array([[-2.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        parameterization="polynomial_translation_affine",
    )

    assert render_generator_family(generator, display_normalization="anchor") == [f"X_1 = {PARTIAL_X}"]
    assert render_generator_family(generator, display_normalization="none") == [f"X_1 = -2{PARTIAL_X}"]


def test_render_generator_family_uses_zero_tolerance_deterministically() -> None:
    generator = _make_generator(
        np.array([[1e-13, 1.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        parameterization="polynomial_translation_affine",
    )

    assert render_generator_family(generator, display_normalization="anchor") == [f"X_1 = t{PARTIAL_X}"]
    assert render_generator_family(generator, display_normalization="none") == [f"X_1 = t{PARTIAL_X}"]


def test_render_generator_family_renders_zero_generator() -> None:
    generator = _make_generator(
        np.zeros((1, 4), dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        parameterization="polynomial_translation_affine",
    )

    assert render_generator_family(generator) == ["X_1 = 0"]


def test_render_generator_family_allows_component_display_name_overrides_for_algebraic_fixtures() -> None:
    generator = _make_generator(
        np.array([[0.0, 1.0, -1.0, 0.0]], dtype=float),
        basis_spec=_rotation_basis_spec(),
    )

    assert render_generator_family(
        generator,
        component_display_names={"xi_x": PARTIAL_X, "xi_y": "\u2202y"},
    ) == [f"X_1 = y{PARTIAL_X} - x\u2202y"]


def test_to_sympy_component_expressions_raises_clear_error_when_sympy_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    symbolic_module = importlib.import_module("pdelie.symmetry.symbolic")
    real_import_module = importlib.import_module

    def _fake_import_module(name: str, package: str | None = None):
        if name == "sympy":
            raise ModuleNotFoundError("No module named 'sympy'")
        return real_import_module(name, package)

    monkeypatch.setattr(symbolic_module.importlib, "import_module", _fake_import_module)
    generator = _make_generator(
        np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        parameterization="polynomial_translation_affine",
    )

    with pytest.raises(ImportError, match="SymPy is required for to_sympy_component_expressions"):
        to_sympy_component_expressions(generator)


def test_to_sympy_component_expressions_returns_per_component_expressions_when_available() -> None:
    sympy = pytest.importorskip("sympy")
    generator = _make_generator(
        np.array([[0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, -1.0]], dtype=float),
        basis_spec=_txu_basis_spec(),
    )

    expressions = to_sympy_component_expressions(generator)

    assert list(expressions[0].keys()) == ["tau", "xi", "phi"]
    assert expressions[0]["tau"] == sympy.Symbol("t")
    assert expressions[0]["xi"] == sympy.Symbol("x")
    assert expressions[0]["phi"] == -sympy.Symbol("u")
