from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from pdelie.contracts import DerivativeBatch, FieldBatch
from pdelie.data import (
    generate_advection_diffusion_1d_field_batch,
    generate_burgers_1d_field_batch,
    generate_heat_1d_field_batch,
    generate_kdv_1d_field_batch,
    generate_reaction_diffusion_1d_field_batch,
)
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.residuals import (
    AdvectionDiffusionResidualEvaluator,
    BurgersResidualEvaluator,
    HeatResidualEvaluator,
    KdVResidualEvaluator,
    ReactionDiffusionResidualEvaluator,
)


def _copy_field(field: FieldBatch, **overrides: object) -> FieldBatch:
    values = overrides.get("values", field.values.copy())
    dims = overrides.get("dims", field.dims)
    coords = overrides.get("coords", {name: coord.copy() for name, coord in field.coords.items()})
    var_names = overrides.get("var_names", list(field.var_names))
    metadata = overrides.get("metadata", deepcopy(field.metadata))
    preprocess_log = overrides.get("preprocess_log", list(field.preprocess_log))
    mask = overrides.get("mask", None if field.mask is None else field.mask.copy())
    return FieldBatch(
        values=values,  # type: ignore[arg-type]
        dims=dims,  # type: ignore[arg-type]
        coords=coords,  # type: ignore[arg-type]
        var_names=var_names,  # type: ignore[arg-type]
        metadata=metadata,  # type: ignore[arg-type]
        preprocess_log=preprocess_log,  # type: ignore[arg-type]
        mask=mask,  # type: ignore[arg-type]
    )


def _drop_derivative(derivatives: DerivativeBatch, name: str) -> DerivativeBatch:
    return DerivativeBatch(
        derivatives={
            derivative_name: values
            for derivative_name, values in derivatives.derivatives.items()
            if derivative_name != name
        },
        backend=derivatives.backend,
        config=dict(derivatives.config),
        boundary_assumptions=derivatives.boundary_assumptions,
        diagnostics=dict(derivatives.diagnostics),
    )


def test_advection_diffusion_residual_internal_and_explicit_derivatives_match() -> None:
    field = generate_advection_diffusion_1d_field_batch(seed=19018)
    evaluator = AdvectionDiffusionResidualEvaluator()
    derivatives = compute_spectral_fd_derivatives(field)

    internal = evaluator.evaluate(field)
    explicit = evaluator.evaluate(field, derivatives)

    internal.validate_against(field)
    explicit.validate_against(field)
    np.testing.assert_allclose(internal.residual, explicit.residual)
    assert explicit.definition_type == "analytic"
    assert explicit.normalization == "none"
    assert explicit.diagnostics["equation"] == "u_t + c*u_x - nu*u_xx = 0"
    assert explicit.diagnostics["c"] == 0.75
    assert explicit.diagnostics["nu"] == 0.05
    assert explicit.diagnostics["max_abs_residual"] < 5e-4
    assert explicit.diagnostics["rms_residual"] < 5e-5


@pytest.mark.parametrize("missing", ["u_t", "u_x", "u_xx"])
def test_advection_diffusion_residual_requires_derivative_keys(missing: str) -> None:
    field = generate_advection_diffusion_1d_field_batch(seed=19018)
    derivatives = compute_spectral_fd_derivatives(field)

    with pytest.raises(SchemaValidationError, match=missing):
        AdvectionDiffusionResidualEvaluator().evaluate(field, _drop_derivative(derivatives, missing))


def test_advection_diffusion_residual_uses_explicit_parameters_when_supplied() -> None:
    field = generate_advection_diffusion_1d_field_batch(advection_speed=-0.4, diffusivity=0.02, seed=19018)
    residual = AdvectionDiffusionResidualEvaluator(advection_speed=-0.4, diffusivity=0.02).evaluate(field)

    assert residual.diagnostics["c"] == -0.4
    assert residual.diagnostics["nu"] == 0.02
    assert residual.diagnostics["max_abs_residual"] < 5e-4
    assert residual.diagnostics["rms_residual"] < 5e-5


@pytest.mark.parametrize(
    "metadata_update",
    [
        {"parameter_tags": {"equation": "heat_1d", "c": 0.75, "nu": 0.05}},
        {"parameter_tags": {"equation": "advection_diffusion_constant_coefficient", "nu": 0.05}},
        {"parameter_tags": {"equation": "advection_diffusion_constant_coefficient", "c": 0.75}},
        {"parameter_tags": {"equation": "advection_diffusion_constant_coefficient", "c": 0.75, "nu": 0.0}},
        {"boundary_conditions": {"x": "dirichlet"}},
    ],
)
def test_advection_diffusion_residual_rejects_wrong_metadata(metadata_update: dict[str, object]) -> None:
    field = generate_advection_diffusion_1d_field_batch(seed=19018)
    metadata = deepcopy(field.metadata)
    metadata.update(metadata_update)
    malformed = _copy_field(field, metadata=metadata)

    with pytest.raises((SchemaValidationError, ScopeValidationError)):
        AdvectionDiffusionResidualEvaluator().evaluate(malformed)


def test_advection_diffusion_residual_rejects_valid_looking_other_pde_fields() -> None:
    heat = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=32, seed=19018)
    burgers = generate_burgers_1d_field_batch(batch_size=2, num_times=17, num_points=32, seed=19018)
    kdv = generate_kdv_1d_field_batch(batch_size=2, num_times=17, num_points=32, seed=19018)
    reaction = generate_reaction_diffusion_1d_field_batch(batch_size=2, num_times=17, num_points=32, seed=19018)

    evaluator = AdvectionDiffusionResidualEvaluator()
    for field in (heat, burgers, kdv, reaction):
        with pytest.raises(ScopeValidationError, match="advection_diffusion_constant_coefficient"):
            evaluator.evaluate(field)

    assert HeatResidualEvaluator().evaluate(heat).diagnostics["max_abs_residual"] >= 0.0
    assert BurgersResidualEvaluator().evaluate(burgers).diagnostics["max_abs_residual"] >= 0.0
    assert KdVResidualEvaluator().evaluate(kdv).diagnostics["max_abs_residual"] >= 0.0
    assert ReactionDiffusionResidualEvaluator().evaluate(reaction).diagnostics["max_abs_residual"] >= 0.0


def test_advection_diffusion_residual_rejects_multivariable_masked_and_nonfinite_fields() -> None:
    field = generate_advection_diffusion_1d_field_batch(seed=19018)
    multivariable = _copy_field(
        field,
        values=np.concatenate([field.values, field.values], axis=-1),
        var_names=["u", "v"],
    )
    masked = _copy_field(field, mask=np.zeros_like(field.values, dtype=bool))
    nonfinite_values = field.values.copy()
    nonfinite_values[0, 0, 0, 0] = np.nan
    nonfinite = _copy_field(field, values=nonfinite_values)

    evaluator = AdvectionDiffusionResidualEvaluator()
    with pytest.raises(ScopeValidationError, match="scalar"):
        evaluator.evaluate(multivariable)
    with pytest.raises(ScopeValidationError, match="masked"):
        evaluator.evaluate(masked)
    with pytest.raises(ScopeValidationError, match="finite"):
        evaluator.evaluate(nonfinite)
