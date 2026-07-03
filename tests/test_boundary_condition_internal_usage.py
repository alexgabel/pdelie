"""Tests for v0.30b internal boundary-condition usage policy.

These tests verify three properties:

1. Downstream periodic-only consumers (spectral_fd, translation basis,
   weak_1d, finite-transform verification, etc.) still reject nonperiodic
   inputs — preserving v0.29 behavior.

2. The ingestion adapters (`from_numpy`, `from_xarray`) now accept structured
   nonperiodic specs and supported legacy nonperiodic strings, but downstream
   consumers continue to reject the resulting FieldBatch when they need
   periodic data.

3. No source file under `src/pdelie/` reintroduces a direct
   `metadata["boundary_conditions"]["x"] == "periodic"` comparison outside the
   `_boundary` helper module. New consumers must go through `is_x_periodic`
   or `get_x_boundary_type`.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pytest

import pdelie
from pdelie._boundary import normalize_x_boundary_condition
from pdelie.data import from_numpy, generate_heat_1d_field_batch
from pdelie.data.numpy_adapter import from_numpy as from_numpy_module_level
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.errors import ScopeValidationError
from pdelie.residuals import HeatResidualEvaluator, evaluate_weak_heat_residual
from pdelie.symmetry.parameterization.polynomial_translation import build_translation_basis
from pdelie.verification import verify_translation_generator


_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_ROOT = _REPO_ROOT / "src" / "pdelie"


def _periodic_metadata(*, nu: float = 0.1) -> dict:
    return {
        "boundary_conditions": {"x": "periodic"},
        "coordinate_system": "cartesian",
        "grid_regularity": "uniform",
        "grid_type": "rectilinear",
        "parameter_tags": {"nu": nu},
    }


def _nonperiodic_metadata(*, x_boundary: str | dict = "dirichlet", nu: float = 0.1) -> dict:
    return {
        "boundary_conditions": {"x": x_boundary},
        "coordinate_system": "cartesian",
        "grid_regularity": "uniform",
        "grid_type": "rectilinear",
        "parameter_tags": {"nu": nu},
    }


def _make_nonperiodic_field(x_boundary: str | dict = "dirichlet"):
    values = np.zeros((1, 4, 16), dtype=float)
    t = np.linspace(0.0, 0.2, 4, dtype=float)
    x = np.linspace(0.0, 1.0, 16, endpoint=False, dtype=float)
    return from_numpy(
        values,
        dims=("batch", "time", "x"),
        coords={"time": t, "x": x},
        var_name="u",
        metadata=_nonperiodic_metadata(x_boundary=x_boundary),
    )


# --- Consumers still reject nonperiodic ---------------------------------


def test_spectral_fd_still_rejects_nonperiodic() -> None:
    field = _make_nonperiodic_field("dirichlet")
    with pytest.raises(ScopeValidationError, match="periodic"):
        compute_spectral_fd_derivatives(field)


def test_polynomial_translation_basis_still_rejects_nonperiodic() -> None:
    field = _make_nonperiodic_field("dirichlet")
    with pytest.raises(ScopeValidationError, match="periodic"):
        build_translation_basis(field)


def test_weak_heat_residual_still_rejects_nonperiodic() -> None:
    # Use a larger field so weak_1d's minimum-window constraints would have been satisfiable.
    values = np.zeros((1, 8, 16), dtype=float)
    t = np.linspace(0.0, 0.7, 8, dtype=float)
    x = np.linspace(0.0, 1.0, 16, endpoint=False, dtype=float)
    field = from_numpy(
        values,
        dims=("batch", "time", "x"),
        coords={"time": t, "x": x},
        var_name="u",
        metadata=_nonperiodic_metadata(x_boundary="dirichlet"),
    )
    with pytest.raises(ScopeValidationError, match="periodic"):
        evaluate_weak_heat_residual(field)


def test_heat_residual_evaluator_now_handles_nonperiodic_via_fd_dispatch() -> None:
    """v0.30d: HeatResidualEvaluator routes through compute_derivatives(backend='auto').

    Dirichlet-tagged data now flows through the finite_difference backend, and the
    ResidualBatch diagnostics record interior-only domain policy. This test asserts
    the v0.30d behavior explicitly to guard against regressions.
    """
    field = _make_nonperiodic_field("dirichlet")
    residual = HeatResidualEvaluator(diffusivity=0.1).evaluate(field)
    assert residual.diagnostics["backend"] == "finite_difference"
    assert residual.diagnostics["residual_domain_policy"] == "interior_only"
    assert residual.diagnostics["boundary_trim_width"] >= 0
    assert "full_grid_diagnostic" in residual.diagnostics


def test_finite_transform_verification_still_rejects_nonperiodic() -> None:
    # Build a periodic generator on a periodic field
    periodic = generate_heat_1d_field_batch(batch_size=3, num_times=5, num_points=16, seed=0)
    from pdelie.symmetry import fit_translation_generator

    generator = fit_translation_generator(periodic, HeatResidualEvaluator())
    # Make the heldout-target field large enough to pass the size precheck so the
    # BC rejection is what surfaces.
    values = np.zeros((3, 4, 16), dtype=float)
    t = np.linspace(0.0, 0.2, 4, dtype=float)
    x = np.linspace(0.0, 1.0, 16, endpoint=False, dtype=float)
    nonperiodic = from_numpy(
        values,
        dims=("batch", "time", "x"),
        coords={"time": t, "x": x},
        var_name="u",
        metadata=_nonperiodic_metadata(x_boundary="dirichlet"),
    )
    with pytest.raises(ScopeValidationError, match="periodic"):
        verify_translation_generator(nonperiodic, generator, HeatResidualEvaluator())


# --- Adapters accept structured nonperiodic --------------------------------


def test_from_numpy_accepts_structured_dirichlet_spec() -> None:
    structured = normalize_x_boundary_condition({
        "type": "dirichlet",
        "left": {"value": 0.0, "time_dependent": False, "source": "user_supplied"},
        "right": {"value": 1.0, "time_dependent": False, "source": "user_supplied"},
    })
    field = _make_nonperiodic_field(x_boundary=structured)
    bc = field.metadata["boundary_conditions"]["x"]
    assert bc["type"] == "dirichlet"
    assert bc["specified"] is True


def test_from_numpy_accepts_legacy_dirichlet_string() -> None:
    field = _make_nonperiodic_field(x_boundary="dirichlet")
    # The legacy string is preserved in metadata (not auto-normalized) for adapter outputs.
    assert field.metadata["boundary_conditions"]["x"] == "dirichlet"


def test_from_numpy_accepts_open_unknown() -> None:
    field = _make_nonperiodic_field(x_boundary="open_unknown")
    assert field.metadata["boundary_conditions"]["x"] == "open_unknown"


def test_from_numpy_rejects_unsupported_string() -> None:
    values = np.zeros((1, 4, 16), dtype=float)
    t = np.linspace(0.0, 0.2, 4, dtype=float)
    x = np.linspace(0.0, 1.0, 16, endpoint=False, dtype=float)
    with pytest.raises(ScopeValidationError, match="Unsupported x boundary string"):
        from_numpy(
            values,
            dims=("batch", "time", "x"),
            coords={"time": t, "x": x},
            var_name="u",
            metadata=_nonperiodic_metadata(x_boundary="insulating"),
        )


# --- Static guard: no new direct periodic compares -----------------------


_ALLOWED_DIRECT_PERIODIC_COMPARE_FILES: frozenset[str] = frozenset({
    # _boundary itself is the central helper; it canonically encodes "periodic".
    str(_SRC_ROOT / "_boundary.py"),
    # PDE data generators set "boundary_conditions": {"x": "periodic"} on output
    # (this is assignment, not comparison, but the regex below is liberal — the
    # assignment form is still allowed).
    str(_SRC_ROOT / "data" / "heat_1d.py"),
    str(_SRC_ROOT / "data" / "burgers_1d.py"),
    str(_SRC_ROOT / "data" / "kdv_1d.py"),
    str(_SRC_ROOT / "data" / "reaction_diffusion_1d.py"),
    str(_SRC_ROOT / "data" / "advection_diffusion_1d.py"),
    # v0.30c: reporting/summaries.py now goes through get_x_boundary_type for
    # the readiness checks; the only "periodic" literal there is the
    # metadata_suggestions output dict and the boundary-warnings vocabulary,
    # neither of which is a direct compare. No allowlist entry needed.
})


_DIRECT_COMPARE_PATTERN = re.compile(
    r'boundary_conditions[^=]*\.\s*get\s*\(\s*["\']x["\']\s*\)\s*!=\s*["\']periodic["\']'
    r'|boundary_conditions\s*\[\s*["\']x["\']\s*\]\s*(==|!=)\s*["\']periodic["\']'
)


def test_no_new_direct_periodic_compares_outside_boundary_helper() -> None:
    """Any direct `metadata['boundary_conditions']['x'] != 'periodic'` style check
    must be replaced by `is_x_periodic`/`get_x_boundary_type` from `pdelie._boundary`."""
    violations: list[str] = []
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        if _DIRECT_COMPARE_PATTERN.search(text):
            if str(path) not in _ALLOWED_DIRECT_PERIODIC_COMPARE_FILES:
                violations.append(str(path.relative_to(_REPO_ROOT)))
    assert violations == [], (
        "v0.30b policy: new sites must use is_x_periodic() / get_x_boundary_type() "
        "from pdelie._boundary. Direct compares found in: " + ", ".join(violations)
    )


def test_boundary_helper_module_is_imported_by_all_runtime_consumers() -> None:
    """Each module that previously did direct `!= 'periodic'` checks now imports
    from pdelie._boundary to demonstrate the migration."""
    must_import_helper = [
        _SRC_ROOT / "derivatives" / "spectral_fd.py",
        _SRC_ROOT / "derivatives" / "finite_difference.py",  # v0.30c
        _SRC_ROOT / "derivatives" / "__init__.py",  # v0.30c dispatcher
        _SRC_ROOT / "residuals" / "weak_1d.py",
        _SRC_ROOT / "residuals" / "kdv_1d.py",
        # v0.30d: advection_diffusion_1d.py and reaction_diffusion_1d.py no longer need
        # is_x_periodic — their BC gate is delegated to compute_derivatives(backend="auto").
        # They still route through the boundary helper transitively via the derivatives
        # dispatcher, but no direct is_x_periodic import remains.
        _SRC_ROOT / "discovery" / "translation_canonical.py",
        _SRC_ROOT / "discovery" / "pysindy_bridge.py",
        _SRC_ROOT / "invariants" / "diagnostics.py",
        _SRC_ROOT / "invariants" / "apply.py",
        _SRC_ROOT / "symmetry" / "formula.py",
        _SRC_ROOT / "symmetry" / "candidate_validation.py",
        _SRC_ROOT / "symmetry" / "parameterization" / "polynomial_translation.py",
        _SRC_ROOT / "verification" / "finite_transform.py",
        _SRC_ROOT / "data" / "numpy_adapter.py",
        _SRC_ROOT / "data" / "xarray_adapter.py",
        _SRC_ROOT / "reporting" / "summaries.py",  # v0.30c
    ]
    missing = []
    for path in must_import_helper:
        text = path.read_text(encoding="utf-8")
        if "from pdelie._boundary import" not in text:
            missing.append(str(path.relative_to(_REPO_ROOT)))
    assert missing == [], (
        "v0.30b consumers must import the boundary helper. Missing in: "
        + ", ".join(missing)
    )
