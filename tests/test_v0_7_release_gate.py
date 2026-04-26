from __future__ import annotations

import importlib

import numpy as np
import pytest

from pdelie.data import from_numpy, generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.discovery import fit_pysindy_discovery, to_pysindy_trajectories
from pdelie.residuals import BurgersResidualEvaluator, HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import verify_translation_generator


_VERTICAL_SLICE_TRAINING_KWARGS = {"batch_size": 4, "num_times": 33, "num_points": 64}
_VERTICAL_SLICE_HELDOUT_KWARGS = {"batch_size": 3, "num_times": 33, "num_points": 64}
_DISCOVERY_KWARGS = {"batch_size": 2, "num_times": 17, "num_points": 16}


def _require_xarray_or_skip():
    return pytest.importorskip(
        "xarray",
        reason="v0.7 release gate xarray path requires optional xarray support (install pdelie[xarray] or pdelie[test]).",
    )


def _require_downstream_or_skip() -> None:
    pytest.importorskip(
        "pysindy",
        reason="v0.7 release gate downstream fit requires optional downstream dependencies (install pdelie[test] or pdelie[downstream]).",
    )
    pytest.importorskip(
        "sklearn.metrics",
        reason="v0.7 release gate downstream fit requires optional downstream dependencies (install pdelie[test] or pdelie[downstream]).",
    )


def _import_from_numpy(field):
    return from_numpy(
        field.values[..., 0],
        dims=("batch", "time", "x"),
        coords={"time": field.coords["time"], "x": field.coords["x"]},
        var_name=field.var_names[0],
        metadata=field.metadata,
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
    from_xarray = importlib.import_module("pdelie.data").from_xarray
    return from_xarray(
        data_array,
        metadata=field.metadata,
        preprocess_log=field.preprocess_log,
    )


def _run_vertical_slice(field, heldout, residual_evaluator):
    derivatives = compute_spectral_fd_derivatives(field)
    residual = residual_evaluator.evaluate(field, derivatives)
    generator = fit_translation_generator(field, residual_evaluator, epsilon=1e-4)
    report = verify_translation_generator(heldout, generator, residual_evaluator)
    return derivatives, residual, generator, report


def _assert_structural_fit_success(result: dict[str, object], feature_names: list[str]) -> None:
    assert result["status"] == "success"
    assert result["backend"] == "pysindy"
    assert result["feature_names"] == feature_names
    coefficients = result["coefficients"]
    library_feature_names = result["library_feature_names"]
    assert isinstance(library_feature_names, list)
    assert coefficients.shape == (len(feature_names), len(library_feature_names))
    assert np.all(np.isfinite(coefficients))


def test_v0_7_release_gate_from_numpy_heat_vertical_slice_matches_native_path() -> None:
    native_training = generate_heat_1d_field_batch(seed=30, **_VERTICAL_SLICE_TRAINING_KWARGS)
    native_heldout = generate_heat_1d_field_batch(seed=31, **_VERTICAL_SLICE_HELDOUT_KWARGS)
    imported_training = _import_from_numpy(native_training)
    imported_heldout = _import_from_numpy(native_heldout)

    native_derivatives, native_residual, native_generator, native_report = _run_vertical_slice(
        native_training,
        native_heldout,
        HeatResidualEvaluator(),
    )
    imported_derivatives, imported_residual, imported_generator, imported_report = _run_vertical_slice(
        imported_training,
        imported_heldout,
        HeatResidualEvaluator(),
    )

    assert imported_derivatives.backend == native_derivatives.backend
    assert imported_residual.definition_type == native_residual.definition_type
    assert imported_report.classification == native_report.classification == "exact"
    np.testing.assert_allclose(imported_generator.coefficients, native_generator.coefficients, rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(imported_report.error_curve, native_report.error_curve, rtol=1e-9, atol=1e-12)


def test_v0_7_release_gate_from_xarray_burgers_vertical_slice_matches_native_path() -> None:
    native_training = generate_burgers_1d_field_batch(seed=40, **_VERTICAL_SLICE_TRAINING_KWARGS)
    native_heldout = generate_burgers_1d_field_batch(seed=41, **_VERTICAL_SLICE_HELDOUT_KWARGS)
    imported_training = _import_from_xarray(native_training)
    imported_heldout = _import_from_xarray(native_heldout)

    native_derivatives, native_residual, native_generator, native_report = _run_vertical_slice(
        native_training,
        native_heldout,
        BurgersResidualEvaluator(),
    )
    imported_derivatives, imported_residual, imported_generator, imported_report = _run_vertical_slice(
        imported_training,
        imported_heldout,
        BurgersResidualEvaluator(),
    )

    assert imported_derivatives.backend == native_derivatives.backend
    assert imported_residual.definition_type == native_residual.definition_type
    assert imported_report.classification == native_report.classification == "exact"
    np.testing.assert_allclose(imported_generator.coefficients, native_generator.coefficients, rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(imported_report.error_curve, native_report.error_curve, rtol=1e-9, atol=1e-12)


def test_v0_7_release_gate_imported_bridge_and_downstream_fit_are_structurally_valid() -> None:
    _require_downstream_or_skip()

    native_field = generate_heat_1d_field_batch(seed=7205, **_DISCOVERY_KWARGS)
    imported_field = _import_from_xarray(native_field)

    native_trajectories, native_time_values, native_feature_names = to_pysindy_trajectories(native_field)
    imported_trajectories, imported_time_values, imported_feature_names = to_pysindy_trajectories(imported_field)

    assert imported_feature_names == native_feature_names
    np.testing.assert_allclose(imported_time_values, native_time_values, rtol=1e-9, atol=1e-12)
    for imported_trajectory, native_trajectory in zip(imported_trajectories, native_trajectories):
        np.testing.assert_allclose(imported_trajectory, native_trajectory, rtol=1e-9, atol=1e-12)

    result = fit_pysindy_discovery(imported_trajectories, imported_time_values, imported_feature_names)
    _assert_structural_fit_success(result, imported_feature_names)
