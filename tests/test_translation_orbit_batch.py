from __future__ import annotations

import json

import numpy as np
import pytest

import pdelie
from pdelie.contracts import FieldBatch
from pdelie.data import generate_heat_1d_field_batch, generate_kdv_1d_field_batch
from pdelie.derivatives import compute_spectral_fd_derivatives
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.invariants import OrbitBatchResult, build_uniform_translation_orbit_batch
from pdelie.residuals import HeatResidualEvaluator, KdVResidualEvaluator

DOMAIN_LENGTH = 2.0 * np.pi


def _assert_json_plain(value: object) -> None:
    assert not isinstance(value, (np.ndarray, np.generic, FieldBatch))
    if isinstance(value, dict):
        for key, item in value.items():
            assert isinstance(key, str)
            _assert_json_plain(item)
    elif isinstance(value, list):
        for item in value:
            _assert_json_plain(item)
    else:
        assert value is None or isinstance(value, (str, bool, int, float))


def test_build_uniform_translation_orbit_batch_materializes_shift_major_batch() -> None:
    field = generate_heat_1d_field_batch(batch_size=2, num_times=7, num_points=16, seed=1501)
    snapshot = field.to_dict()
    shifts = [0.0, DOMAIN_LENGTH / 16.0, DOMAIN_LENGTH / 16.0, DOMAIN_LENGTH]

    result = build_uniform_translation_orbit_batch(
        field,
        shifts=shifts,
        source_field_id={"fixture": "heat", "seed": 1501},
    )

    assert isinstance(result, OrbitBatchResult)
    assert result.field.dims == field.dims
    assert result.field.values.shape[0] == field.values.shape[0] * len(shifts)
    assert result.field.values.shape[1:] == field.values.shape[1:]
    result.field.validate()

    assert np.allclose(result.field.values[0:2], field.values)
    assert np.allclose(result.field.values[2:4], result.field.values[4:6])
    assert np.allclose(result.field.values[6:8], field.values, atol=1e-10)

    report = result.report
    assert json.loads(json.dumps(report)) == report
    _assert_json_plain(report)
    assert report["summary_schema_version"] == "0.1"
    assert report["summary_type"] == "uniform_translation_orbit_batch"
    assert report["source_field_id"] == {"fixture": "heat", "seed": 1501}
    assert report["source_field_shape"] == list(field.values.shape)
    assert report["output_field_shape"] == list(result.field.values.shape)
    assert report["source_batch_size"] == 2
    assert report["shift_count"] == len(shifts)
    assert report["output_batch_size"] == 8
    assert report["ordering"] == "shift_major"
    assert report["raw_shifts"] == pytest.approx(shifts)
    assert report["normalized_shifts"] == pytest.approx([shift % DOMAIN_LENGTH for shift in shifts])
    assert report["duplicate_shifts_preserved"] is True
    assert report["source_batch_indices"] == [0, 1, 0, 1, 0, 1, 0, 1]
    assert report["shift_indices"] == [0, 0, 1, 1, 2, 2, 3, 3]
    assert [record["output_batch_index"] for record in report["batch_records"]] == list(range(8))
    assert [record["source_batch_index"] for record in report["batch_records"]] == report["source_batch_indices"]
    assert [record["shift_index"] for record in report["batch_records"]] == report["shift_indices"]

    metadata = result.field.metadata["orbit_materialization"]
    assert metadata["operation"] == "materialize_uniform_translation_orbit_batch"
    assert metadata["construction_method"] == "uniform_translation"
    assert metadata["ordering"] == "shift_major"
    assert metadata["source_field_id"] == {"fixture": "heat", "seed": 1501}
    assert result.field.preprocess_log[-1]["operation"] == "materialize_uniform_translation_orbit_batch"
    assert len(result.field.preprocess_log) == len(field.preprocess_log) + 1
    assert field.to_dict() == snapshot
    assert not hasattr(pdelie, "build_uniform_translation_orbit_batch")
    assert not hasattr(pdelie, "OrbitBatchResult")


def test_build_uniform_translation_orbit_batch_preserves_optional_index_policy() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=1502)

    result = build_uniform_translation_orbit_batch(
        field,
        shifts=[0.0, DOMAIN_LENGTH],
        keep_source_index=False,
        keep_shift_index=False,
    )

    assert result.report["source_batch_indices"] is None
    assert result.report["shift_indices"] is None
    for record in result.report["batch_records"]:
        assert "source_batch_index" not in record
        assert "shift_index" not in record
        assert "shift" in record
        assert "normalized_shift" in record


def test_build_uniform_translation_orbit_batch_concatenates_masks() -> None:
    base = generate_heat_1d_field_batch(batch_size=2, num_times=5, num_points=8, seed=1503)
    mask = np.zeros_like(base.values, dtype=bool)
    mask[1, :, ::2, :] = True
    field = FieldBatch(
        values=base.values,
        dims=base.dims,
        coords=base.coords,
        var_names=base.var_names,
        metadata=base.metadata,
        preprocess_log=base.preprocess_log,
        mask=mask,
    )

    result = build_uniform_translation_orbit_batch(field, shifts=[0.0, DOMAIN_LENGTH / 8.0, DOMAIN_LENGTH / 8.0])

    assert result.field.mask is not None
    expected = np.concatenate([mask, mask, mask], axis=0)
    assert np.array_equal(result.field.mask, expected)
    assert np.array_equal(result.field.mask[2:4], result.field.mask[4:6])


def test_materialized_heat_and_kdv_batches_support_derivatives_and_residuals() -> None:
    heat = generate_heat_1d_field_batch(batch_size=1, num_times=9, num_points=16, seed=1504)
    heat_orbit = build_uniform_translation_orbit_batch(heat, shifts=[0.0, DOMAIN_LENGTH / 16.0]).field
    heat_derivatives = compute_spectral_fd_derivatives(heat_orbit)
    heat_residual = HeatResidualEvaluator().evaluate(heat_orbit, heat_derivatives)
    assert np.isfinite(float(heat_residual.diagnostics["max_abs_residual"]))

    kdv = generate_kdv_1d_field_batch(batch_size=1, num_times=9, num_points=16, num_modes=1, seed=1505)
    kdv_orbit = build_uniform_translation_orbit_batch(kdv, shifts=[0.0, DOMAIN_LENGTH / 16.0]).field
    kdv_derivatives = compute_spectral_fd_derivatives(kdv_orbit, max_spatial_order=3)
    kdv_residual = KdVResidualEvaluator().evaluate(kdv_orbit, kdv_derivatives)
    assert np.isfinite(float(kdv_residual.diagnostics["max_abs_residual"]))
    assert np.isfinite(float(kdv_residual.diagnostics["rms_residual"]))


@pytest.mark.parametrize(
    ("kwargs", "error_type", "match"),
    [
        ({"shifts": []}, SchemaValidationError, "non-empty"),
        ({"shifts": [np.nan]}, SchemaValidationError, "finite"),
        ({"shifts": [0.0], "keep_source_index": 1}, SchemaValidationError, "keep_source_index"),
        ({"shifts": [0.0], "keep_shift_index": 0}, SchemaValidationError, "keep_shift_index"),
        ({"shifts": [0.0], "copy": 1}, SchemaValidationError, "copy"),
        ({"shifts": [0.0], "source_field_id": object()}, SchemaValidationError, "source_field_id"),
    ],
)
def test_build_uniform_translation_orbit_batch_rejects_invalid_inputs(
    kwargs: dict[str, object],
    error_type: type[Exception],
    match: str,
) -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=1506)

    with pytest.raises(error_type, match=match):
        build_uniform_translation_orbit_batch(field, **kwargs)


def test_build_uniform_translation_orbit_batch_rejects_unsupported_fields() -> None:
    field = generate_heat_1d_field_batch(batch_size=1, num_times=5, num_points=16, seed=1507)
    nonperiodic = FieldBatch(
        values=field.values,
        dims=field.dims,
        coords=field.coords,
        var_names=field.var_names,
        metadata={**field.metadata, "boundary_conditions": {"x": "dirichlet"}},
        preprocess_log=field.preprocess_log,
    )

    with pytest.raises(ScopeValidationError, match="build_uniform_translation_orbit_batch.*periodic"):
        build_uniform_translation_orbit_batch(nonperiodic, shifts=[0.0])
