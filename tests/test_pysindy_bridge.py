from __future__ import annotations

import importlib

import numpy as np
import pytest

from pdelie import FieldBatch, InvariantMapSpec, ScopeValidationError
from pdelie.errors import SchemaValidationError
from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.discovery import to_pysindy_trajectories
from pdelie.invariants import InvariantApplier
from pdelie.residuals import BurgersResidualEvaluator, HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator


def _make_invariant_spec(generator_metadata: dict[str, object], shift: float) -> InvariantMapSpec:
    return InvariantMapSpec(
        generator_metadata=generator_metadata,
        construction_method="uniform_translation",
        parameters={"axis": "x", "shift": shift},
        domain_validity="global",
        inverse_available=True,
        diagnostics={},
    )


def test_to_pysindy_trajectories_converts_heat_field_deterministically() -> None:
    field = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=80)

    first_trajectories, first_time_values, first_feature_names = to_pysindy_trajectories(field)
    second_trajectories, second_time_values, second_feature_names = to_pysindy_trajectories(field)

    assert len(first_trajectories) == 3
    assert len(second_trajectories) == 3
    for first, second in zip(first_trajectories, second_trajectories):
        assert first.shape == (33, 64)
        np.testing.assert_allclose(first, second)
    np.testing.assert_allclose(first_time_values, field.coords["time"])
    np.testing.assert_allclose(first_time_values, second_time_values)
    assert first_feature_names == second_feature_names
    assert first_feature_names[0] == "u__x_index_0"
    assert first_feature_names[-1] == "u__x_index_63"


def test_to_pysindy_trajectories_converts_burgers_field_deterministically() -> None:
    field = generate_burgers_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=81)

    trajectories, time_values, feature_names = to_pysindy_trajectories(field)

    assert len(trajectories) == 2
    for trajectory in trajectories:
        assert trajectory.shape == (17, 16)
    np.testing.assert_allclose(time_values, field.coords["time"])
    assert feature_names == [f"u__x_index_{index}" for index in range(16)]


def test_to_pysindy_trajectories_rejects_non_periodic_fields() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=82)
    field.metadata["boundary_conditions"] = {"x": "dirichlet"}

    with pytest.raises(ScopeValidationError, match="requires periodic boundary conditions in x"):
        to_pysindy_trajectories(field)


def test_to_pysindy_trajectories_rejects_unsupported_dims() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=83)
    reduced_field = FieldBatch(
        values=field.values[:, 0, :, :],
        dims=("batch", "x", "var"),
        coords={"x": field.coords["x"].copy()},
        var_names=list(field.var_names),
        metadata=dict(field.metadata),
        preprocess_log=list(field.preprocess_log),
        mask=None if field.mask is None else field.mask[:, 0, :, :].copy(),
    )

    with pytest.raises(ScopeValidationError, match="only supports dims"):
        to_pysindy_trajectories(reduced_field)


def test_to_pysindy_trajectories_rejects_multi_variable_fields() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=84)
    stacked_values = np.concatenate((field.values, field.values), axis=-1)
    multi_var_field = FieldBatch(
        values=stacked_values,
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=["u", "v"],
        metadata=dict(field.metadata),
        preprocess_log=list(field.preprocess_log),
        mask=None if field.mask is None else np.concatenate((field.mask, field.mask), axis=-1),
    )

    with pytest.raises(ScopeValidationError, match="only supports a single scalar variable"):
        to_pysindy_trajectories(multi_var_field)


def test_to_pysindy_trajectories_requires_time_coordinates() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=87)
    invalid_field = FieldBatch.from_dict(field.to_dict())
    del invalid_field.coords["time"]

    with pytest.raises(SchemaValidationError, match=r"Missing coordinate arrays for dims: \['time'\]"):
        to_pysindy_trajectories(invalid_field)


def test_pysindy_smoke_helper_raises_clear_error_when_dependency_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    bridge_module = importlib.import_module("pdelie.discovery.pysindy_bridge")
    real_import_module = importlib.import_module

    def _fake_import_module(name: str, package: str | None = None):
        if name == "pysindy":
            raise ModuleNotFoundError("No module named 'pysindy'")
        return real_import_module(name, package)

    monkeypatch.setattr(bridge_module.importlib, "import_module", _fake_import_module)

    with pytest.raises(ImportError, match=r"Install pdelie\[downstream\] or pdelie\[test\]"):
        bridge_module._fit_pysindy_smoke(
            np.zeros((4, 3), dtype=float),
            np.linspace(0.0, 0.3, 4),
            ["u__x_index_0", "u__x_index_1", "u__x_index_2"],
        )


@pytest.mark.parametrize(
    ("field_factory", "residual_evaluator", "seed"),
    (
        (generate_heat_1d_field_batch, HeatResidualEvaluator(), 85),
        (generate_burgers_1d_field_batch, BurgersResidualEvaluator(), 86),
    ),
)
def test_invariant_path_feeds_minimal_pysindy_fit_smoke(
    field_factory,
    residual_evaluator,
    seed: int,
) -> None:
    bridge_module = importlib.import_module("pdelie.discovery.pysindy_bridge")
    try:
        bridge_module._require_pysindy()
    except ImportError as exc:
        pytest.skip(str(exc))

    field = field_factory(batch_size=2, num_times=17, num_points=16, seed=seed)
    generator = fit_translation_generator(field, residual_evaluator, epsilon=1e-4)
    spec = _make_invariant_spec(generator.to_dict(), shift=float(field.coords["x"][1]))
    transformed = InvariantApplier().apply(field, spec)
    trajectories, time_values, feature_names = to_pysindy_trajectories(transformed)

    first_model, first_coefficients = bridge_module._fit_pysindy_smoke(
        trajectories[0],
        time_values,
        feature_names,
    )
    second_model, second_coefficients = bridge_module._fit_pysindy_smoke(
        trajectories[0],
        time_values,
        feature_names,
    )

    assert first_model is not None
    assert second_model is not None
    assert first_coefficients.size > 0
    assert second_coefficients.size > 0
    assert np.all(np.isfinite(first_coefficients))
    assert np.all(np.isfinite(second_coefficients))
    np.testing.assert_allclose(first_coefficients, second_coefficients)
