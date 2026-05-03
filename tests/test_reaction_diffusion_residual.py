from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from pdelie.contracts import DerivativeBatch, FieldBatch
from pdelie.data import generate_heat_1d_field_batch, generate_reaction_diffusion_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.residuals import HeatResidualEvaluator, ReactionDiffusionResidualEvaluator


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


def test_reaction_diffusion_residual_internal_and_explicit_derivatives_match() -> None:
    field = generate_reaction_diffusion_1d_field_batch(seed=18018)
    evaluator = ReactionDiffusionResidualEvaluator()
    derivatives = compute_spectral_fd_derivatives(field)

    internal = evaluator.evaluate(field)
    explicit = evaluator.evaluate(field, derivatives)

    internal.validate_against(field)
    explicit.validate_against(field)
    np.testing.assert_allclose(internal.residual, explicit.residual)
    assert explicit.definition_type == "analytic"
    assert explicit.normalization == "none"
    assert explicit.diagnostics["equation"] == "u_t - nu*u_xx - rho*u*(1-u) = 0"
    assert explicit.diagnostics["nu"] == 0.05
    assert explicit.diagnostics["rho"] == 1.0
    assert explicit.diagnostics["max_abs_residual"] < 5e-4
    assert explicit.diagnostics["rms_residual"] < 5e-5


@pytest.mark.parametrize("missing", ["u_t", "u_xx"])
def test_reaction_diffusion_residual_requires_derivative_keys(missing: str) -> None:
    field = generate_reaction_diffusion_1d_field_batch(seed=18018)
    derivatives = compute_spectral_fd_derivatives(field)

    with pytest.raises(SchemaValidationError, match=missing):
        ReactionDiffusionResidualEvaluator().evaluate(field, _drop_derivative(derivatives, missing))


def test_reaction_diffusion_residual_uses_explicit_parameters_when_supplied() -> None:
    field = generate_reaction_diffusion_1d_field_batch(diffusivity=0.02, reaction_rate=0.7, seed=18018)
    residual = ReactionDiffusionResidualEvaluator(diffusivity=0.02, reaction_rate=0.7).evaluate(field)

    assert residual.diagnostics["nu"] == 0.02
    assert residual.diagnostics["rho"] == 0.7
    assert residual.diagnostics["max_abs_residual"] < 5e-4
    assert residual.diagnostics["rms_residual"] < 5e-5


@pytest.mark.parametrize(
    "metadata_update",
    [
        {"parameter_tags": {"equation": "heat_1d", "nu": 0.05, "rho": 1.0}},
        {"parameter_tags": {"equation": "reaction_diffusion_fisher_kpp", "rho": 1.0}},
        {"parameter_tags": {"equation": "reaction_diffusion_fisher_kpp", "nu": 0.05}},
        {"boundary_conditions": {"x": "dirichlet"}},
    ],
)
def test_reaction_diffusion_residual_rejects_wrong_metadata(metadata_update: dict[str, object]) -> None:
    field = generate_reaction_diffusion_1d_field_batch(seed=18018)
    metadata = deepcopy(field.metadata)
    metadata.update(metadata_update)
    malformed = _copy_field(field, metadata=metadata)

    with pytest.raises((SchemaValidationError, ScopeValidationError)):
        ReactionDiffusionResidualEvaluator().evaluate(malformed)


def test_reaction_diffusion_residual_rejects_valid_looking_heat_field() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=7, num_points=16, seed=18018)

    with pytest.raises(ScopeValidationError, match="reaction_diffusion_fisher_kpp"):
        ReactionDiffusionResidualEvaluator().evaluate(field)
    assert HeatResidualEvaluator().evaluate(field).diagnostics["max_abs_residual"] >= 0.0


def test_reaction_diffusion_residual_rejects_multivariable_masked_and_nonfinite_fields() -> None:
    field = generate_reaction_diffusion_1d_field_batch(seed=18018)
    multivariable = _copy_field(
        field,
        values=np.concatenate([field.values, field.values], axis=-1),
        var_names=["u", "v"],
    )
    masked = _copy_field(field, mask=np.zeros_like(field.values, dtype=bool))
    nonfinite_values = field.values.copy()
    nonfinite_values[0, 0, 0, 0] = np.nan
    nonfinite = _copy_field(field, values=nonfinite_values)

    evaluator = ReactionDiffusionResidualEvaluator()
    with pytest.raises(ScopeValidationError, match="scalar"):
        evaluator.evaluate(multivariable)
    with pytest.raises(ScopeValidationError, match="masked"):
        evaluator.evaluate(masked)
    with pytest.raises(ScopeValidationError, match="finite"):
        evaluator.evaluate(nonfinite)
