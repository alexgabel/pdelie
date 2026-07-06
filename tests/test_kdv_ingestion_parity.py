from __future__ import annotations

import importlib
from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from pdelie.data import from_numpy, generate_kdv_1d_field_batch, split_batch_train_heldout
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.residuals import KdVResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.symmetry.parameterization import translation_span_distance
from pdelie.verification import verify_translation_generator


def _require_xarray_or_skip():
    return pytest.importorskip(
        "xarray",
        reason="xarray is required for KdV from_xarray parity tests (install pdelie[xarray] or pdelie[test]).",
    )


def _frozen_kdv_train_heldout():
    field = generate_kdv_1d_field_batch(batch_size=5, seed=9001)
    return split_batch_train_heldout(field, train_size=2, seed=9002)


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


def _assert_imported_field_parity(native, imported, *, importer_name: str) -> None:
    assert imported.dims == native.dims
    assert imported.var_names == native.var_names
    assert imported.metadata == native.metadata
    assert imported.metadata["parameter_tags"] == {"equation": "kdv_normalized"}
    np.testing.assert_allclose(imported.values, native.values, rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(imported.coords["time"], native.coords["time"], rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(imported.coords["x"], native.coords["x"], rtol=1e-9, atol=1e-12)
    if native.mask is None:
        assert imported.mask is None
    else:
        assert imported.mask is not None
        np.testing.assert_array_equal(imported.mask, native.mask)

    assert imported.preprocess_log[:-1] == native.preprocess_log
    final_entry = imported.preprocess_log[-1]
    assert final_entry["operation"] == importer_name
    assert final_entry["parameters"]["source_layout"] == ["batch", "time", "x"]
    assert final_entry["parameters"]["imported_shape"] == list(native.values.shape[:-1])
    assert final_entry["parameters"]["canonical_shape"] == list(native.values.shape)
    assert final_entry["parameters"]["injected_batch_axis"] is False
    assert final_entry["parameters"]["injected_var_axis"] is True
    assert final_entry["parameters"]["mask_provided"] is (native.mask is not None)
    imported.validate()


def _run_kdv_strong_path(training, heldout) -> dict[str, Any]:
    residual_evaluator = KdVResidualEvaluator()
    derivatives = compute_spectral_fd_derivatives(training, max_spatial_order=3)
    residual = residual_evaluator.evaluate(training, derivatives)
    generator = fit_translation_generator(training, residual_evaluator, epsilon=1e-4)
    report = verify_translation_generator(heldout, generator, residual_evaluator)
    return {
        "derivatives": derivatives,
        "residual": residual,
        "generator": generator,
        "report": report,
        "span_distance": float(translation_span_distance(generator.coefficients)),
    }


def _assert_derivative_parity(native, imported) -> None:
    assert set(imported.derivatives) == set(native.derivatives) == {"u_x", "u_xx", "u_t", "u_xxx"}
    assert imported.backend == native.backend
    assert imported.config == native.config
    assert imported.boundary_assumptions == native.boundary_assumptions
    for name in native.derivatives:
        np.testing.assert_allclose(imported.derivatives[name], native.derivatives[name], rtol=1e-9, atol=1e-12)
    for key in ("x_points", "time_points"):
        assert imported.diagnostics[key] == native.diagnostics[key]
    np.testing.assert_allclose(
        [imported.diagnostics["dx"], imported.diagnostics["dt"]],
        [native.diagnostics["dx"], native.diagnostics["dt"]],
        rtol=1e-9,
        atol=1e-12,
    )


def _assert_residual_parity(native, imported) -> None:
    assert imported.definition_type == native.definition_type
    assert imported.normalization == native.normalization
    np.testing.assert_allclose(imported.residual, native.residual, rtol=1e-9, atol=1e-12)
    for key in ("backend", "equation"):
        assert imported.diagnostics[key] == native.diagnostics[key]
    np.testing.assert_allclose(
        [imported.diagnostics["max_abs_residual"], imported.diagnostics["rms_residual"]],
        [native.diagnostics["max_abs_residual"], native.diagnostics["rms_residual"]],
        rtol=1e-9,
        atol=1e-12,
    )


def _assert_generator_parity(native, imported) -> None:
    assert imported.parameterization == native.parameterization
    assert imported.basis_spec == native.basis_spec
    assert imported.normalization == native.normalization
    assert imported.generator_names == native.generator_names
    np.testing.assert_allclose(imported.coefficients, native.coefficients, rtol=1e-9, atol=1e-12)
    for key in ("fit_mode", "fallback_reason", "reference_fallback_used"):
        assert imported.diagnostics[key] == native.diagnostics[key]
    np.testing.assert_allclose(
        imported.diagnostics["svd_span_distance"],
        native.diagnostics["svd_span_distance"],
        rtol=1e-9,
        atol=1e-12,
    )


def _assert_report_parity(native, imported) -> None:
    assert imported.norm == native.norm
    assert imported.classification == native.classification
    assert imported.diagnostics["transform_mode"] == native.diagnostics["transform_mode"]
    np.testing.assert_allclose(imported.epsilon_values, native.epsilon_values, rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(imported.error_curve, native.error_curve, rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(
        [imported.diagnostics["span_distance"], imported.diagnostics["span_tolerance"]],
        [native.diagnostics["span_distance"], native.diagnostics["span_tolerance"]],
        rtol=1e-9,
        atol=1e-12,
    )
    np.testing.assert_allclose(
        imported.diagnostics["batch_errors"],
        native.diagnostics["batch_errors"],
        rtol=1e-9,
        atol=1e-12,
    )


def _assert_kdv_path_parity(native_summary: dict[str, Any], imported_summary: dict[str, Any]) -> None:
    _assert_derivative_parity(native_summary["derivatives"], imported_summary["derivatives"])
    _assert_residual_parity(native_summary["residual"], imported_summary["residual"])
    _assert_generator_parity(native_summary["generator"], imported_summary["generator"])
    _assert_report_parity(native_summary["report"], imported_summary["report"])
    np.testing.assert_allclose(
        imported_summary["span_distance"],
        native_summary["span_distance"],
        rtol=1e-9,
        atol=1e-12,
    )


@pytest.mark.parametrize(
    ("importer_name", "importer"),
    [
        ("from_numpy", _import_from_numpy),
        ("from_xarray", _import_from_xarray),
    ],
)
def test_kdv_imported_fields_preserve_train_and_heldout_strong_path_parity(
    importer_name: str,
    importer: Callable[[Any], Any],
) -> None:
    native_training, native_heldout = _frozen_kdv_train_heldout()
    imported_training = importer(native_training)
    imported_heldout = importer(native_heldout)

    _assert_imported_field_parity(native_training, imported_training, importer_name=importer_name)
    _assert_imported_field_parity(native_heldout, imported_heldout, importer_name=importer_name)

    native_summary = _run_kdv_strong_path(native_training, native_heldout)
    imported_summary = _run_kdv_strong_path(imported_training, imported_heldout)
    _assert_kdv_path_parity(native_summary, imported_summary)
