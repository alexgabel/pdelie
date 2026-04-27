from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from pdelie import FieldBatch, SchemaValidationError, ScopeValidationError
from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.residuals import evaluate_weak_burgers_residual, evaluate_weak_heat_residual


_EXPECTED_REPORT_KEYS = {
    "equation",
    "equation_form",
    "method_family",
    "window_residuals",
    "time_window_centers",
    "x_window_centers",
    "normalization",
    "diagnostics",
}
_EXPECTED_DIAGNOSTICS_KEYS = {
    "strong_form",
    "weak_form",
    "diffusivity",
    "time_window_size",
    "x_window_size",
    "time_window_stride",
    "x_window_stride",
    "quadrature",
    "test_function",
    "periodic_x_wrapping",
    "window_counts",
    "max_abs_residual",
    "l2_residual",
}
_EXPECTED_METHOD_FAMILY = "local_separable_quartic_bump_trapezoid_v1"


def _make_multi_var_field(field: FieldBatch) -> FieldBatch:
    return FieldBatch(
        values=np.concatenate((field.values, field.values), axis=-1),
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=["u", "v"],
        metadata=deepcopy(field.metadata),
        preprocess_log=deepcopy(field.preprocess_log),
        mask=None,
    )


def _make_reduced_field(field: FieldBatch) -> FieldBatch:
    return FieldBatch(
        values=field.values[:, 0, :, :].copy(),
        dims=("batch", "x", "var"),
        coords={"x": field.coords["x"].copy()},
        var_names=list(field.var_names),
        metadata=deepcopy(field.metadata),
        preprocess_log=deepcopy(field.preprocess_log),
        mask=None,
    )


def _make_masked_field(field: FieldBatch) -> FieldBatch:
    return FieldBatch(
        values=field.values.copy(),
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=deepcopy(field.metadata),
        preprocess_log=deepcopy(field.preprocess_log),
        mask=np.zeros_like(field.values, dtype=bool),
    )


def _make_nonperiodic_field(field: FieldBatch) -> FieldBatch:
    metadata = deepcopy(field.metadata)
    metadata["boundary_conditions"]["x"] = "dirichlet"  # type: ignore[index]
    return FieldBatch(
        values=field.values.copy(),
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=metadata,
        preprocess_log=deepcopy(field.preprocess_log),
        mask=None,
    )


def _make_nonuniform_time_field(field: FieldBatch) -> FieldBatch:
    time = field.coords["time"].copy()
    time[2] = time[2] + 0.25 * float(time[1] - time[0])
    return FieldBatch(
        values=field.values.copy(),
        dims=field.dims,
        coords={"time": time, "x": field.coords["x"].copy()},
        var_names=list(field.var_names),
        metadata=deepcopy(field.metadata),
        preprocess_log=deepcopy(field.preprocess_log),
        mask=None,
    )


def _make_tightly_nonuniform_time_field(field: FieldBatch) -> FieldBatch:
    time = field.coords["time"].copy()
    time[2] = time[2] + 5e-11
    return FieldBatch(
        values=field.values.copy(),
        dims=field.dims,
        coords={"time": time, "x": field.coords["x"].copy()},
        var_names=list(field.var_names),
        metadata=deepcopy(field.metadata),
        preprocess_log=deepcopy(field.preprocess_log),
        mask=None,
    )


def _make_decreasing_time_field(field: FieldBatch) -> FieldBatch:
    return FieldBatch(
        values=field.values[:, ::-1, :, :].copy(),
        dims=field.dims,
        coords={"time": field.coords["time"][::-1].copy(), "x": field.coords["x"].copy()},
        var_names=list(field.var_names),
        metadata=deepcopy(field.metadata),
        preprocess_log=deepcopy(field.preprocess_log),
        mask=None,
    )


def _make_decreasing_x_field(field: FieldBatch) -> FieldBatch:
    return FieldBatch(
        values=field.values[:, :, ::-1, :].copy(),
        dims=field.dims,
        coords={"time": field.coords["time"].copy(), "x": field.coords["x"][::-1].copy()},
        var_names=list(field.var_names),
        metadata=deepcopy(field.metadata),
        preprocess_log=deepcopy(field.preprocess_log),
        mask=None,
    )


def _make_zero_spacing_x_field(field: FieldBatch) -> FieldBatch:
    return FieldBatch(
        values=field.values.copy(),
        dims=field.dims,
        coords={"time": field.coords["time"].copy(), "x": np.zeros_like(field.coords["x"], dtype=float)},
        var_names=list(field.var_names),
        metadata=deepcopy(field.metadata),
        preprocess_log=deepcopy(field.preprocess_log),
        mask=None,
    )


def _make_nonfinite_field(field: FieldBatch) -> FieldBatch:
    values = field.values.copy()
    values[0, 0, 0, 0] = np.nan
    return FieldBatch(
        values=values,
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=deepcopy(field.metadata),
        preprocess_log=deepcopy(field.preprocess_log),
        mask=None,
    )


def _make_missing_nu_field(field: FieldBatch) -> FieldBatch:
    metadata = deepcopy(field.metadata)
    metadata["parameter_tags"] = {}
    return FieldBatch(
        values=field.values.copy(),
        dims=field.dims,
        coords={name: coord.copy() for name, coord in field.coords.items()},
        var_names=list(field.var_names),
        metadata=metadata,
        preprocess_log=deepcopy(field.preprocess_log),
        mask=None,
    )


def _make_short_time_field() -> FieldBatch:
    return generate_heat_1d_field_batch(batch_size=2, num_times=4, num_points=64, seed=9101)


def _make_short_x_field() -> FieldBatch:
    return generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=8, seed=9102)


def _assert_report_schema(
    report: dict[str, object],
    *,
    equation: str,
    equation_form: str,
    strong_form: str,
    weak_form: str,
    batch_size: int,
    num_times: int,
    num_points: int,
) -> None:
    assert set(report) == _EXPECTED_REPORT_KEYS
    assert report["equation"] == equation
    assert report["equation_form"] == equation_form
    assert report["method_family"] == _EXPECTED_METHOD_FAMILY
    assert report["normalization"] == "none"

    window_residuals = report["window_residuals"]
    time_window_centers = report["time_window_centers"]
    x_window_centers = report["x_window_centers"]
    diagnostics = report["diagnostics"]

    assert isinstance(window_residuals, np.ndarray)
    assert isinstance(time_window_centers, np.ndarray)
    assert isinstance(x_window_centers, np.ndarray)
    assert isinstance(diagnostics, dict)
    assert set(diagnostics) == _EXPECTED_DIAGNOSTICS_KEYS

    assert window_residuals.shape == (batch_size, num_times - 4, num_points, 1)
    assert time_window_centers.shape == (num_times - 4,)
    assert x_window_centers.shape == (num_points,)
    assert diagnostics["strong_form"] == strong_form
    assert diagnostics["weak_form"] == weak_form
    assert diagnostics["time_window_size"] == 5
    assert diagnostics["x_window_size"] == 9
    assert diagnostics["time_window_stride"] == 1
    assert diagnostics["x_window_stride"] == 1
    assert diagnostics["periodic_x_wrapping"] is True
    assert diagnostics["window_counts"] == {"time": num_times - 4, "x": num_points}
    assert np.all(np.isfinite(window_residuals))
    assert np.isfinite(diagnostics["max_abs_residual"])
    assert np.isfinite(diagnostics["l2_residual"])


def test_weak_heat_residual_report_matches_frozen_schema_and_is_deterministic() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=33, num_points=64, seed=8001)

    first = evaluate_weak_heat_residual(field)
    second = evaluate_weak_heat_residual(field)
    explicit = evaluate_weak_heat_residual(field, diffusivity=0.1)

    _assert_report_schema(
        first,
        equation="heat_1d",
        equation_form="nonconservative",
        strong_form="u_t - nu u_xx = 0",
        weak_form="-u phi_t - nu u phi_xx",
        batch_size=2,
        num_times=33,
        num_points=64,
    )
    np.testing.assert_allclose(first["window_residuals"], second["window_residuals"])
    np.testing.assert_allclose(first["window_residuals"], explicit["window_residuals"])
    np.testing.assert_allclose(first["time_window_centers"], field.coords["time"][2:-2])
    np.testing.assert_allclose(first["x_window_centers"], field.coords["x"])
    assert first["diagnostics"]["diffusivity"] == pytest.approx(0.1)


def test_weak_burgers_residual_report_matches_frozen_schema_and_explicit_diffusivity() -> None:
    field = generate_burgers_1d_field_batch(batch_size=2, num_times=33, num_points=64, seed=8101)

    implicit = evaluate_weak_burgers_residual(field)
    explicit = evaluate_weak_burgers_residual(field, diffusivity=0.1)

    _assert_report_schema(
        implicit,
        equation="burgers_1d",
        equation_form="conservative",
        strong_form="u_t + 1/2 (u^2)_x - nu u_xx = 0",
        weak_form="-u phi_t - 1/2 u^2 phi_x - nu u phi_xx",
        batch_size=2,
        num_times=33,
        num_points=64,
    )
    np.testing.assert_allclose(implicit["window_residuals"], explicit["window_residuals"])
    np.testing.assert_allclose(implicit["time_window_centers"], field.coords["time"][2:-2])
    np.testing.assert_allclose(implicit["x_window_centers"], field.coords["x"])
    assert implicit["diagnostics"]["diffusivity"] == pytest.approx(0.1)


@pytest.mark.parametrize(
    ("function", "field_factory", "expected_message"),
    [
        (evaluate_weak_heat_residual, lambda: "bad-input", "FieldBatch input"),
        (evaluate_weak_burgers_residual, lambda: "bad-input", "FieldBatch input"),
    ],
)
def test_weak_residual_reports_reject_wrong_input_type(
    function,
    field_factory,
    expected_message: str,
) -> None:
    with pytest.raises(SchemaValidationError, match=expected_message):
        function(field_factory())  # type: ignore[arg-type]


@pytest.mark.parametrize("function", [evaluate_weak_heat_residual, evaluate_weak_burgers_residual])
@pytest.mark.parametrize(
    ("field_factory", "expected_message", "error_type"),
    [
        (lambda: _make_reduced_field(generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=9201)), "dims", ScopeValidationError),
        (lambda: _make_multi_var_field(generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=9202)), "single scalar variable", ScopeValidationError),
        (lambda: _make_masked_field(generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=9203)), "masked fields", ScopeValidationError),
        (lambda: _make_nonfinite_field(generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=9204)), "finite field values", ScopeValidationError),
        (lambda: _make_nonuniform_time_field(generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=9205)), "uniformly spaced time", ScopeValidationError),
        (lambda: _make_tightly_nonuniform_time_field(generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=9208)), "uniformly spaced time", ScopeValidationError),
        (lambda: _make_decreasing_time_field(generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=9209)), "strictly increasing time", ScopeValidationError),
        (lambda: _make_decreasing_x_field(generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=9210)), "strictly increasing x", ScopeValidationError),
        (lambda: _make_zero_spacing_x_field(generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=9211)), "strictly increasing x", ScopeValidationError),
        (lambda: _make_nonperiodic_field(generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=9206)), "periodic boundary conditions", ScopeValidationError),
        (_make_short_time_field, "at least 5 time points", ScopeValidationError),
        (_make_short_x_field, "at least 9 x-points", ScopeValidationError),
        (lambda: _make_missing_nu_field(generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=9207)), "parameter_tags'\\]\\['nu", SchemaValidationError),
    ],
)
def test_weak_residual_reports_reject_unsupported_inputs(
    function,
    field_factory,
    expected_message: str,
    error_type,
) -> None:
    field = field_factory()
    with pytest.raises(error_type, match=expected_message):
        function(field)


@pytest.mark.parametrize("function", [evaluate_weak_heat_residual, evaluate_weak_burgers_residual])
@pytest.mark.parametrize("diffusivity", [True, np.inf, "bad"])
def test_weak_residual_reports_reject_invalid_explicit_diffusivity(function, diffusivity: object) -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=17, num_points=16, seed=9301)
    with pytest.raises(SchemaValidationError, match="diffusivity"):
        function(field, diffusivity=diffusivity)  # type: ignore[arg-type]
