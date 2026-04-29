from __future__ import annotations

import importlib

import numpy as np
import pytest

import pdelie
from pdelie import DerivativeBatch, FieldBatch, PDELieValidationError
from pdelie.data import generate_heat_1d_field_batch, generate_kdv_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from tests._helpers.ks_feasibility import (
    KS_FEASIBILITY_CONFIG,
    KSFeasibilityResidualEvaluator,
    generate_ks_feasibility_field_batch,
)


def test_ks_residual_internal_derivative_path_returns_valid_residual_batch() -> None:
    field = generate_ks_feasibility_field_batch()

    residual = KSFeasibilityResidualEvaluator().evaluate(field)

    assert residual.definition_type == "analytic"
    assert residual.normalization == "none"
    assert residual.residual.shape == field.values.shape
    assert set(residual.diagnostics) == {"equation", "backend", "max_abs_residual", "rms_residual"}
    assert residual.diagnostics["equation"] == KS_FEASIBILITY_CONFIG["equation"]
    assert residual.diagnostics["backend"] == "spectral_fd"
    assert residual.diagnostics["max_abs_residual"] < 5e-2
    assert residual.diagnostics["rms_residual"] < 1e-2
    residual.validate_against(field)


def test_ks_residual_explicit_order_four_derivatives_match_internal_path() -> None:
    field = generate_ks_feasibility_field_batch()
    derivatives = compute_spectral_fd_derivatives(field, max_spatial_order=4)

    internal = KSFeasibilityResidualEvaluator().evaluate(field)
    explicit = KSFeasibilityResidualEvaluator().evaluate(field, derivatives)

    np.testing.assert_allclose(explicit.residual, internal.residual, rtol=0.0, atol=0.0)
    assert explicit.diagnostics == internal.diagnostics


def test_ks_residual_explicit_order_three_derivatives_fail_for_missing_uxxxx() -> None:
    field = generate_ks_feasibility_field_batch()
    derivatives = compute_spectral_fd_derivatives(field, max_spatial_order=3)

    with pytest.raises(PDELieValidationError, match="u_xxxx"):
        KSFeasibilityResidualEvaluator().evaluate(field, derivatives)


def test_ks_residual_does_not_depend_on_uxxx() -> None:
    field = generate_ks_feasibility_field_batch()
    derivatives = compute_spectral_fd_derivatives(field, max_spatial_order=4)
    without_uxxx = DerivativeBatch(
        derivatives={key: value for key, value in derivatives.derivatives.items() if key != "u_xxx"},
        backend=derivatives.backend,
        config=derivatives.config,
        boundary_assumptions=derivatives.boundary_assumptions,
        diagnostics=derivatives.diagnostics,
    )

    with_uxxx = KSFeasibilityResidualEvaluator().evaluate(field, derivatives)
    without = KSFeasibilityResidualEvaluator().evaluate(field, without_uxxx)

    np.testing.assert_allclose(without.residual, with_uxxx.residual, rtol=0.0, atol=0.0)


def _base_ks_field() -> FieldBatch:
    return generate_ks_feasibility_field_batch(batch_size=1)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda field: setattr(field, "dims", ("batch", "x", "time", "var")),
        lambda field: field.metadata["boundary_conditions"].__setitem__("x", "dirichlet"),
        lambda field: setattr(field, "mask", np.zeros(field.values.shape, dtype=bool)),
        lambda field: field.values.__setitem__((0, 0, 0, 0), np.nan),
        lambda field: field.metadata.__setitem__("parameter_tags", {}),
        lambda field: field.metadata.__setitem__("parameter_tags", {"equation": "heat_1d"}),
    ],
)
def test_ks_residual_rejects_unsupported_fields(mutate: object) -> None:
    field = _base_ks_field()
    mutate(field)

    with pytest.raises(PDELieValidationError):
        KSFeasibilityResidualEvaluator().evaluate(field)


def test_ks_residual_rejects_multivariable_field() -> None:
    field = _base_ks_field()
    field.values = np.repeat(field.values, 2, axis=-1)
    field.var_names = ["u", "v"]

    with pytest.raises(PDELieValidationError):
        KSFeasibilityResidualEvaluator().evaluate(field)


def test_ks_residual_rejects_malformed_parameter_tags() -> None:
    field = _base_ks_field()
    field.metadata["parameter_tags"] = "ks_normalized"

    with pytest.raises(PDELieValidationError):
        KSFeasibilityResidualEvaluator().evaluate(field)


def test_ks_residual_rejects_valid_looking_heat_and_kdv_fields() -> None:
    heat = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=11131)
    kdv = generate_kdv_1d_field_batch(batch_size=1, num_times=5, num_points=16, num_modes=1, seed=11132)

    with pytest.raises(PDELieValidationError, match="ks_normalized"):
        KSFeasibilityResidualEvaluator().evaluate(heat)
    with pytest.raises(PDELieValidationError, match="ks_normalized"):
        KSFeasibilityResidualEvaluator().evaluate(kdv)


def test_ks_residual_feasibility_adds_no_public_ks_surface() -> None:
    data_module = importlib.import_module("pdelie.data")
    residuals_module = importlib.import_module("pdelie.residuals")

    assert not hasattr(pdelie, "KSResidualEvaluator")
    assert not hasattr(pdelie, "KuramotoSivashinskyResidualEvaluator")
    assert not hasattr(pdelie, "generate_ks_1d_field_batch")
    assert not hasattr(data_module, "generate_ks_1d_field_batch")
    assert not hasattr(data_module, "generate_ks_feasibility_field_batch")
    assert not hasattr(residuals_module, "KSResidualEvaluator")
    assert not hasattr(residuals_module, "KuramotoSivashinskyResidualEvaluator")
