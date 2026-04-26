from __future__ import annotations

import importlib
from typing import Any, Callable

import numpy as np
import pytest

from pdelie.data import (
    from_numpy,
    generate_burgers_1d_field_batch,
    generate_heat_1d_field_batch,
)
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.discovery import to_pysindy_trajectories
from pdelie.residuals import BurgersResidualEvaluator, HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import verify_translation_generator


_TRAINING_KWARGS = {"batch_size": 4, "num_times": 17, "num_points": 16}
_HELDOUT_KWARGS = {"batch_size": 3, "num_times": 17, "num_points": 16}
_PARITY_CASES = [
    ("heat", generate_heat_1d_field_batch, HeatResidualEvaluator, 7101, 7102),
    ("burgers", generate_burgers_1d_field_batch, BurgersResidualEvaluator, 7103, 7104),
]


def _require_xarray_or_skip():
    return pytest.importorskip(
        "xarray",
        reason="xarray is required for from_xarray parity tests (install pdelie[xarray] or pdelie[test]).",
    )


def _import_from_numpy(field):
    mask = None if field.mask is None else field.mask[..., 0]
    return from_numpy(
        field.values[..., 0],
        dims=("batch", "time", "x"),
        coords={"time": field.coords["time"], "x": field.coords["x"]},
        var_name=field.var_names[0],
        metadata=field.metadata,
        mask=mask,
        preprocess_log=field.preprocess_log,
    )


def _import_from_xarray(field):
    xr = _require_xarray_or_skip()
    coords = {
        "batch": np.arange(field.values.shape[0], dtype=int),
        "time": field.coords["time"],
        "x": field.coords["x"],
    }
    data_array = xr.DataArray(
        field.values[..., 0],
        dims=("batch", "time", "x"),
        coords=coords,
        name=field.var_names[0],
    )
    mask = None
    if field.mask is not None:
        mask = xr.DataArray(
            field.mask[..., 0],
            dims=("batch", "time", "x"),
            coords=coords,
        )
    from_xarray = importlib.import_module("pdelie.data").from_xarray
    return from_xarray(
        data_array,
        metadata=field.metadata,
        mask=mask,
        preprocess_log=field.preprocess_log,
    )


def _assert_numeric_mapping_allclose(first: dict[str, Any], second: dict[str, Any]) -> None:
    assert first.keys() == second.keys()
    for key in first:
        np.testing.assert_allclose(first[key], second[key], rtol=1e-9, atol=1e-12)


def _assert_field_parity(native, imported, *, importer_name: str) -> None:
    assert imported.dims == native.dims
    np.testing.assert_allclose(imported.values, native.values, rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(imported.coords["time"], native.coords["time"], rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(imported.coords["x"], native.coords["x"], rtol=1e-9, atol=1e-12)
    assert imported.var_names == native.var_names
    assert imported.metadata == native.metadata
    if native.mask is None:
        assert imported.mask is None
    else:
        assert imported.mask is not None
        np.testing.assert_array_equal(imported.mask, native.mask)

    assert len(imported.preprocess_log) == len(native.preprocess_log) + 1
    assert imported.preprocess_log[:-1] == native.preprocess_log
    final_entry = imported.preprocess_log[-1]
    assert final_entry["operation"] == importer_name
    assert final_entry["parameters"] == {
        "source_layout": ["batch", "time", "x"],
        "imported_shape": list(native.values.shape[:-1]),
        "canonical_shape": list(native.values.shape),
        "injected_batch_axis": False,
        "injected_var_axis": True,
        "mask_provided": native.mask is not None,
    }


def _assert_derivative_parity(native_derivatives, imported_derivatives) -> None:
    assert imported_derivatives.backend == native_derivatives.backend
    assert imported_derivatives.config == native_derivatives.config
    assert imported_derivatives.boundary_assumptions == native_derivatives.boundary_assumptions
    _assert_numeric_mapping_allclose(native_derivatives.derivatives, imported_derivatives.derivatives)
    assert imported_derivatives.diagnostics.keys() == native_derivatives.diagnostics.keys()
    assert imported_derivatives.diagnostics["x_points"] == native_derivatives.diagnostics["x_points"]
    assert imported_derivatives.diagnostics["time_points"] == native_derivatives.diagnostics["time_points"]
    np.testing.assert_allclose(
        [imported_derivatives.diagnostics["dx"], imported_derivatives.diagnostics["dt"]],
        [native_derivatives.diagnostics["dx"], native_derivatives.diagnostics["dt"]],
        rtol=1e-9,
        atol=1e-12,
    )


def _assert_residual_parity(native_residual, imported_residual) -> None:
    assert imported_residual.definition_type == native_residual.definition_type
    assert imported_residual.normalization == native_residual.normalization
    np.testing.assert_allclose(imported_residual.residual, native_residual.residual, rtol=1e-9, atol=1e-12)
    assert imported_residual.diagnostics.keys() == native_residual.diagnostics.keys()
    assert imported_residual.diagnostics["backend"] == native_residual.diagnostics["backend"]
    np.testing.assert_allclose(
        [imported_residual.diagnostics["nu"], imported_residual.diagnostics["max_abs_residual"]],
        [native_residual.diagnostics["nu"], native_residual.diagnostics["max_abs_residual"]],
        rtol=1e-9,
        atol=1e-12,
    )


def _assert_generator_parity(native_generator, imported_generator) -> None:
    assert imported_generator.parameterization == native_generator.parameterization
    assert imported_generator.basis_spec == native_generator.basis_spec
    assert imported_generator.normalization == native_generator.normalization
    assert imported_generator.generator_names == native_generator.generator_names
    np.testing.assert_allclose(imported_generator.coefficients, native_generator.coefficients, rtol=1e-9, atol=1e-12)

    assert imported_generator.diagnostics.keys() == native_generator.diagnostics.keys()
    for key in ("basis", "fallback_reason", "fit_mode", "min_delta_basis", "reference_fallback_used"):
        assert imported_generator.diagnostics[key] == native_generator.diagnostics[key]
    _assert_numeric_mapping_allclose(
        native_generator.diagnostics["basis_delta_norms"],
        imported_generator.diagnostics["basis_delta_norms"],
    )
    np.testing.assert_allclose(
        imported_generator.diagnostics["svd_coefficients"],
        native_generator.diagnostics["svd_coefficients"],
        rtol=1e-9,
        atol=1e-12,
    )
    np.testing.assert_allclose(
        [
            imported_generator.diagnostics["svd_span_distance"],
            imported_generator.diagnostics["fit_residual"],
            imported_generator.diagnostics["training_epsilon"],
        ],
        [
            native_generator.diagnostics["svd_span_distance"],
            native_generator.diagnostics["fit_residual"],
            native_generator.diagnostics["training_epsilon"],
        ],
        rtol=1e-9,
        atol=1e-12,
    )


def _assert_report_parity(native_report, imported_report) -> None:
    assert imported_report.norm == native_report.norm
    assert imported_report.classification == native_report.classification
    np.testing.assert_allclose(imported_report.epsilon_values, native_report.epsilon_values, rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(imported_report.error_curve, native_report.error_curve, rtol=1e-9, atol=1e-12)
    assert imported_report.diagnostics.keys() == native_report.diagnostics.keys()
    assert imported_report.diagnostics["heldout_initial_conditions"] == native_report.diagnostics["heldout_initial_conditions"]
    assert imported_report.diagnostics["transform_mode"] == native_report.diagnostics["transform_mode"]
    np.testing.assert_allclose(
        [
            imported_report.diagnostics["span_distance"],
            imported_report.diagnostics["span_tolerance"],
        ],
        [
            native_report.diagnostics["span_distance"],
            native_report.diagnostics["span_tolerance"],
        ],
        rtol=1e-9,
        atol=1e-12,
    )
    np.testing.assert_allclose(
        imported_report.diagnostics["batch_errors"],
        native_report.diagnostics["batch_errors"],
        rtol=1e-9,
        atol=1e-12,
    )


def _assert_bridge_parity(native_field, imported_field) -> None:
    native_trajectories, native_time_values, native_feature_names = to_pysindy_trajectories(native_field)
    imported_trajectories, imported_time_values, imported_feature_names = to_pysindy_trajectories(imported_field)

    assert imported_feature_names == native_feature_names
    np.testing.assert_allclose(imported_time_values, native_time_values, rtol=1e-9, atol=1e-12)
    assert len(imported_trajectories) == len(native_trajectories)
    for imported_trajectory, native_trajectory in zip(imported_trajectories, native_trajectories):
        np.testing.assert_allclose(imported_trajectory, native_trajectory, rtol=1e-9, atol=1e-12)


def _assert_vertical_slice_and_bridge_parity(
    native_training,
    imported_training,
    native_heldout,
    imported_heldout,
    residual_evaluator_factory: Callable[[], Any],
    *,
    importer_name: str,
) -> None:
    _assert_field_parity(native_training, imported_training, importer_name=importer_name)
    _assert_field_parity(native_heldout, imported_heldout, importer_name=importer_name)

    native_derivatives = compute_spectral_fd_derivatives(native_training)
    imported_derivatives = compute_spectral_fd_derivatives(imported_training)
    _assert_derivative_parity(native_derivatives, imported_derivatives)

    native_residual = residual_evaluator_factory().evaluate(native_training, native_derivatives)
    imported_residual = residual_evaluator_factory().evaluate(imported_training, imported_derivatives)
    _assert_residual_parity(native_residual, imported_residual)

    native_generator = fit_translation_generator(native_training, residual_evaluator_factory(), epsilon=1e-4)
    imported_generator = fit_translation_generator(imported_training, residual_evaluator_factory(), epsilon=1e-4)
    _assert_generator_parity(native_generator, imported_generator)

    native_report = verify_translation_generator(native_heldout, native_generator, residual_evaluator_factory())
    imported_report = verify_translation_generator(imported_heldout, imported_generator, residual_evaluator_factory())
    _assert_report_parity(native_report, imported_report)

    _assert_bridge_parity(native_training, imported_training)


@pytest.mark.parametrize(("name", "factory", "residual_evaluator_factory", "training_seed", "heldout_seed"), _PARITY_CASES)
def test_from_numpy_imports_preserve_vertical_slice_and_bridge_parity(
    name: str,
    factory,
    residual_evaluator_factory,
    training_seed: int,
    heldout_seed: int,
) -> None:
    native_training = factory(seed=training_seed, **_TRAINING_KWARGS)
    native_heldout = factory(seed=heldout_seed, **_HELDOUT_KWARGS)

    imported_training = _import_from_numpy(native_training)
    imported_heldout = _import_from_numpy(native_heldout)

    _assert_vertical_slice_and_bridge_parity(
        native_training,
        imported_training,
        native_heldout,
        imported_heldout,
        residual_evaluator_factory,
        importer_name="from_numpy",
    )


@pytest.mark.parametrize(("name", "factory", "residual_evaluator_factory", "training_seed", "heldout_seed"), _PARITY_CASES)
def test_from_xarray_imports_preserve_vertical_slice_and_bridge_parity(
    name: str,
    factory,
    residual_evaluator_factory,
    training_seed: int,
    heldout_seed: int,
) -> None:
    native_training = factory(seed=training_seed, **_TRAINING_KWARGS)
    native_heldout = factory(seed=heldout_seed, **_HELDOUT_KWARGS)

    imported_training = _import_from_xarray(native_training)
    imported_heldout = _import_from_xarray(native_heldout)

    _assert_vertical_slice_and_bridge_parity(
        native_training,
        imported_training,
        native_heldout,
        imported_heldout,
        residual_evaluator_factory,
        importer_name="from_xarray",
    )
