from __future__ import annotations

import copy
import inspect

import numpy as np
import pytest

from pdelie import FieldBatch, PDELieValidationError, SchemaValidationError
from pdelie.contracts import DerivativeBatch
from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch, generate_kdv_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.residuals import KdVResidualEvaluator


def _copy_field(
    field: FieldBatch,
    *,
    values: np.ndarray | None = None,
    dims: tuple[str, ...] | None = None,
    coords: dict[str, np.ndarray] | None = None,
    var_names: list[str] | None = None,
    metadata: dict[str, object] | None = None,
    mask: np.ndarray | None = None,
) -> FieldBatch:
    return FieldBatch(
        values=np.asarray(field.values if values is None else values, dtype=float).copy(),
        dims=field.dims if dims is None else dims,
        coords={name: coord.copy() for name, coord in (field.coords if coords is None else coords).items()},
        var_names=list(field.var_names if var_names is None else var_names),
        metadata=copy.deepcopy(field.metadata if metadata is None else metadata),
        preprocess_log=[dict(entry) for entry in field.preprocess_log],
        mask=mask,
    )


def test_kdv_residual_internal_derivative_path_returns_valid_residual_batch() -> None:
    field = generate_kdv_1d_field_batch(seed=9200)
    residual = KdVResidualEvaluator().evaluate(field)

    residual.validate_against(field)
    assert residual.residual.shape == field.values.shape
    assert residual.definition_type == "analytic"
    assert residual.normalization == "none"
    assert residual.diagnostics["equation"] == "u_t + 6*u*u_x + u_xxx = 0"
    assert residual.diagnostics["backend"] == "spectral_fd"
    assert np.isfinite(float(residual.diagnostics["max_abs_residual"]))
    assert np.isfinite(float(residual.diagnostics["rms_residual"]))


def test_kdv_residual_explicit_max_order_three_derivatives_match_internal_path() -> None:
    field = generate_kdv_1d_field_batch(seed=9201)
    derivatives = compute_spectral_fd_derivatives(field, max_spatial_order=3)

    internal = KdVResidualEvaluator().evaluate(field)
    explicit = KdVResidualEvaluator().evaluate(field, derivatives)

    np.testing.assert_allclose(explicit.residual, internal.residual, rtol=0.0, atol=0.0)
    assert explicit.diagnostics["backend"] == derivatives.backend


def test_kdv_residual_explicit_max_order_two_derivatives_fail_with_missing_u_xxx() -> None:
    field = generate_kdv_1d_field_batch(seed=9202)
    derivatives = compute_spectral_fd_derivatives(field, max_spatial_order=2)

    with pytest.raises(SchemaValidationError, match="u_xxx"):
        KdVResidualEvaluator().evaluate(field, derivatives)


def test_kdv_default_fixture_residual_thresholds_are_within_frozen_m3_gate() -> None:
    field = generate_kdv_1d_field_batch(seed=9203)
    residual = KdVResidualEvaluator().evaluate(field)

    assert residual.diagnostics["max_abs_residual"] < 1e-2
    assert residual.diagnostics["rms_residual"] < 2e-3


def test_kdv_residual_rejects_mismatched_derivative_shapes() -> None:
    field = generate_kdv_1d_field_batch(seed=9204)
    derivatives = compute_spectral_fd_derivatives(field, max_spatial_order=3)
    mismatched = DerivativeBatch(
        derivatives={name: array[:, :-1, :, :].copy() for name, array in derivatives.derivatives.items()},
        backend=derivatives.backend,
        config=derivatives.config.copy(),
        boundary_assumptions=derivatives.boundary_assumptions,
        diagnostics=derivatives.diagnostics.copy(),
    )

    with pytest.raises(PDELieValidationError, match="FieldBatch shape"):
        KdVResidualEvaluator().evaluate(field, mismatched)


@pytest.mark.parametrize(
    "make_field, match",
    [
        (
            lambda base: _copy_field(
                base,
                values=base.values[0],
                dims=("time", "x", "var"),
                coords={"time": base.coords["time"], "x": base.coords["x"]},
            ),
            "dims",
        ),
        (
            lambda base: _copy_field(
                base,
                values=np.concatenate([base.values, base.values], axis=-1),
                var_names=["u", "v"],
            ),
            "scalar",
        ),
        (
            lambda base: _copy_field(
                base,
                metadata={**copy.deepcopy(base.metadata), "boundary_conditions": {"x": "dirichlet"}},
            ),
            "periodic",
        ),
        (
            lambda base: _copy_field(base, mask=np.zeros_like(base.values, dtype=bool)),
            "masked",
        ),
        (
            lambda base: _copy_field(
                base,
                values=np.where(
                    np.indices(base.values.shape).sum(axis=0) == 0,
                    np.nan,
                    base.values,
                ),
            ),
            "finite",
        ),
        (
            lambda base: _copy_field(
                base,
                metadata={**copy.deepcopy(base.metadata), "parameter_tags": {}},
            ),
            "kdv_normalized",
        ),
        (
            lambda base: _copy_field(
                base,
                metadata={**copy.deepcopy(base.metadata), "parameter_tags": {"equation": "kdv_other"}},
            ),
            "kdv_normalized",
        ),
    ],
)
def test_kdv_residual_rejects_unsupported_fields(
    make_field: object,
    match: str,
) -> None:
    base = generate_kdv_1d_field_batch(seed=9205)
    field = make_field(base)  # type: ignore[operator]

    with pytest.raises(PDELieValidationError, match=match):
        KdVResidualEvaluator().evaluate(field)


@pytest.mark.parametrize(
    "field",
    [
        generate_heat_1d_field_batch(seed=9206),
        generate_burgers_1d_field_batch(seed=9207),
    ],
)
def test_kdv_residual_rejects_valid_looking_non_kdv_fields(field: FieldBatch) -> None:
    with pytest.raises(PDELieValidationError, match="kdv_normalized"):
        KdVResidualEvaluator().evaluate(field)


def test_kdv_residual_evaluator_exposes_no_coefficient_customization_surface() -> None:
    assert list(inspect.signature(KdVResidualEvaluator).parameters) == []

    with pytest.raises(TypeError):
        KdVResidualEvaluator(alpha=1.0)  # type: ignore[call-arg]
