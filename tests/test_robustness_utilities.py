from __future__ import annotations

from copy import deepcopy

import numpy as np
import pytest

from pdelie import FieldBatch, SchemaValidationError, ScopeValidationError
from pdelie.data import add_gaussian_noise, split_batch_train_heldout, subsample_time, subsample_x
from pdelie.discovery import summarize_recovery_grid


def _make_metadata() -> dict[str, object]:
    return {
        "boundary_conditions": {"x": "periodic"},
        "coordinate_system": "cartesian",
        "grid_regularity": "uniform",
        "grid_type": "rectilinear",
        "parameter_tags": {"nu": 0.1, "nested": {"tag": "source"}},
    }


def _make_field(
    *,
    batch_size: int = 4,
    num_times: int = 5,
    num_points: int = 4,
    mask: np.ndarray | None = None,
    with_nan: bool = False,
) -> FieldBatch:
    values = np.arange(batch_size * num_times * num_points, dtype=float).reshape(batch_size, num_times, num_points, 1) + 1.0
    if with_nan:
        values[0, 0, 2, 0] = np.nan
    return FieldBatch(
        values=values,
        dims=("batch", "time", "x", "var"),
        coords={
            "time": np.linspace(0.0, 1.0, num_times, dtype=float),
            "x": np.linspace(0.0, 2.0 * np.pi, num_points, endpoint=False, dtype=float),
        },
        var_names=["u"],
        metadata=_make_metadata(),
        preprocess_log=[{"operation": "source", "parameters": {"nested": {"level": 1}}}],
        mask=None if mask is None else mask.copy(),
    )


def _make_reduced_field_without_time(field: FieldBatch) -> FieldBatch:
    return FieldBatch(
        values=field.values[:, 0, :, :].copy(),
        dims=("batch", "x", "var"),
        coords={"x": field.coords["x"].copy()},
        var_names=list(field.var_names),
        metadata=deepcopy(field.metadata),
        preprocess_log=deepcopy(field.preprocess_log),
        mask=None if field.mask is None else field.mask[:, 0, :, :].copy(),
    )


def _make_reduced_field_without_x(field: FieldBatch) -> FieldBatch:
    return FieldBatch(
        values=field.values[:, :, 0, :].copy(),
        dims=("batch", "time", "var"),
        coords={"time": field.coords["time"].copy()},
        var_names=list(field.var_names),
        metadata=deepcopy(field.metadata),
        preprocess_log=deepcopy(field.preprocess_log),
        mask=None if field.mask is None else field.mask[:, :, 0, :].copy(),
    )


def _make_reduced_field_without_batch(field: FieldBatch) -> FieldBatch:
    return FieldBatch(
        values=field.values[0].copy(),
        dims=("time", "x", "var"),
        coords={"time": field.coords["time"].copy(), "x": field.coords["x"].copy()},
        var_names=list(field.var_names),
        metadata=deepcopy(field.metadata),
        preprocess_log=deepcopy(field.preprocess_log),
        mask=None if field.mask is None else field.mask[0].copy(),
    )


def _make_recovery(
    *,
    classification: str = "exact",
    residuals: dict[str, float] | None = None,
) -> dict[str, object]:
    recovery: dict[str, object] = {
        "classification": classification,
        "support_precision": 1.0,
        "support_recall": 0.8,
        "support_f1": 0.888,
        "target_sparsity": 2.0,
        "discovered_sparsity": 3.0,
        "coefficient_l2_error": 0.1,
        "coefficient_relative_l2_error": 0.2,
        "coefficient_linf_error": 0.05,
        "equation_strings": {"target": "1*u_xx", "discovered": "1*u_xx"},
    }
    if residuals is not None:
        recovery.update(residuals)
    return recovery


def test_add_gaussian_noise_is_deterministic_for_a_fixed_seed() -> None:
    field = _make_field()

    first = add_gaussian_noise(field, std_fraction=0.1, seed=11)
    second = add_gaussian_noise(field, std_fraction=0.1, seed=11)

    np.testing.assert_allclose(first.values, second.values)
    assert first.preprocess_log[-1] == second.preprocess_log[-1]


def test_add_gaussian_noise_respects_mask_and_nonfinite_values() -> None:
    mask = np.zeros((2, 3, 4, 1), dtype=bool)
    mask[0, 0, 3, 0] = True
    field = _make_field(batch_size=2, num_times=3, num_points=4, mask=mask, with_nan=True)

    noisy = add_gaussian_noise(field, std_fraction=0.1, seed=3)
    changed = add_gaussian_noise(field, std_fraction=0.1, seed=4)

    assert np.isnan(noisy.values[0, 0, 2, 0])
    assert noisy.values[0, 0, 3, 0] == field.values[0, 0, 3, 0]
    assert changed.values[0, 0, 3, 0] == field.values[0, 0, 3, 0]
    assert not np.allclose(noisy.values[np.isfinite(noisy.values)], changed.values[np.isfinite(changed.values)])


def test_add_gaussian_noise_computes_noise_scale_from_finite_unmasked_rms_only() -> None:
    values = np.array([[[[3.0], [4.0], [np.nan], [100.0]]]], dtype=float)
    mask = np.array([[[[False], [False], [False], [True]]]], dtype=bool)
    field = FieldBatch(
        values=values,
        dims=("batch", "time", "x", "var"),
        coords={"time": np.array([0.0]), "x": np.linspace(0.0, 2.0 * np.pi, 4, endpoint=False)},
        var_names=["u"],
        metadata=_make_metadata(),
        preprocess_log=[],
        mask=mask,
    )

    noisy = add_gaussian_noise(field, std_fraction=0.5, seed=9)

    expected_rms = float(np.sqrt(np.mean(np.square(np.array([3.0, 4.0])))))
    assert noisy.preprocess_log[-1]["parameters"]["noise_std"] == pytest.approx(0.5 * expected_rms)
    assert np.isnan(noisy.values[0, 0, 2, 0])
    assert noisy.values[0, 0, 3, 0] == field.values[0, 0, 3, 0]


def test_add_gaussian_noise_with_zero_fraction_is_value_stable_and_appends_log() -> None:
    field = _make_field()

    noisy = add_gaussian_noise(field, std_fraction=0.0, seed=1)

    np.testing.assert_allclose(noisy.values, field.values)
    assert noisy.preprocess_log[-1]["operation"] == "add_gaussian_noise"


def test_add_gaussian_noise_rejects_missing_eligible_entries() -> None:
    field = _make_field(mask=np.ones((4, 5, 4, 1), dtype=bool))

    with pytest.raises(SchemaValidationError, match="finite unmasked"):
        add_gaussian_noise(field, std_fraction=0.1, seed=1)


@pytest.mark.parametrize(
    ("std_fraction", "seed"),
    [
        (-0.1, 1),
        (np.inf, 1),
        ("bad", 1),
        (0.1, 1.5),
        (0.1, True),
    ],
)
def test_add_gaussian_noise_rejects_invalid_parameter_types(std_fraction: object, seed: object) -> None:
    field = _make_field()

    with pytest.raises(SchemaValidationError):
        add_gaussian_noise(field, std_fraction=std_fraction, seed=seed)  # type: ignore[arg-type]


def test_subsample_time_slices_and_can_leave_one_time_point() -> None:
    mask = np.zeros((4, 5, 4, 1), dtype=bool)
    mask[1, 4, 2, 0] = True
    field = _make_field(mask=mask)

    reduced = subsample_time(field, stride=5)

    reduced.validate()
    assert reduced.values.shape == (4, 1, 4, 1)
    np.testing.assert_allclose(reduced.coords["time"], field.coords["time"][::5])
    np.testing.assert_allclose(reduced.values, field.values[:, ::5, :, :])
    np.testing.assert_array_equal(reduced.mask, field.mask[:, ::5, :, :])
    assert reduced.preprocess_log[-1]["operation"] == "subsample_time"


def test_subsample_x_slices_values_and_mask() -> None:
    mask = np.zeros((4, 5, 6, 1), dtype=bool)
    mask[2, 1, 4, 0] = True
    field = _make_field(num_points=6, mask=mask)

    reduced = subsample_x(field, stride=2)

    np.testing.assert_allclose(reduced.coords["x"], field.coords["x"][::2])
    np.testing.assert_allclose(reduced.values, field.values[:, :, ::2, :])
    np.testing.assert_array_equal(reduced.mask, field.mask[:, :, ::2, :])
    assert reduced.preprocess_log[-1]["operation"] == "subsample_x"


def test_subsample_x_rejects_stride_that_leaves_fewer_than_two_points() -> None:
    field = _make_field(num_points=4)

    with pytest.raises(ScopeValidationError, match="at least two x-points"):
        subsample_x(field, stride=4)


def test_subsample_helpers_reject_missing_required_dimensions() -> None:
    field = _make_field()

    with pytest.raises(ScopeValidationError, match="'time'"):
        subsample_time(_make_reduced_field_without_time(field), stride=2)
    with pytest.raises(ScopeValidationError, match="'x'"):
        subsample_x(_make_reduced_field_without_x(field), stride=2)


@pytest.mark.parametrize("stride", [0, -1, 1.5, True])
def test_subsample_helpers_reject_invalid_stride(stride: object) -> None:
    field = _make_field()

    with pytest.raises(SchemaValidationError):
        subsample_time(field, stride=stride)  # type: ignore[arg-type]
    with pytest.raises(SchemaValidationError):
        subsample_x(field, stride=stride)  # type: ignore[arg-type]


def test_split_batch_train_heldout_is_deterministic_and_preserves_original_order() -> None:
    field = _make_field(batch_size=5)

    train, heldout = split_batch_train_heldout(field, train_size=2, seed=13)

    permutation = np.random.default_rng(13).permutation(5)
    expected_train = sorted(int(index) for index in permutation[:2])
    expected_heldout = sorted(int(index) for index in permutation[2:])
    np.testing.assert_allclose(train.values, field.values[expected_train])
    np.testing.assert_allclose(heldout.values, field.values[expected_heldout])
    assert train.preprocess_log[-1]["parameters"]["selected_batch_indices"] == expected_train
    assert heldout.preprocess_log[-1]["parameters"]["selected_batch_indices"] == expected_heldout


@pytest.mark.parametrize("train_size", [0, 5, True, 1.5])
def test_split_batch_train_heldout_rejects_invalid_train_size(train_size: object) -> None:
    field = _make_field(batch_size=5)

    with pytest.raises((SchemaValidationError, ScopeValidationError)):
        split_batch_train_heldout(field, train_size=train_size, seed=7)  # type: ignore[arg-type]


def test_split_batch_train_heldout_rejects_bool_seed() -> None:
    field = _make_field(batch_size=5)

    with pytest.raises(SchemaValidationError):
        split_batch_train_heldout(field, train_size=2, seed=True)  # type: ignore[arg-type]


def test_split_batch_train_heldout_rejects_missing_batch_and_too_small_batch() -> None:
    field = _make_field(batch_size=1)

    with pytest.raises(SchemaValidationError, match="at least two batch items"):
        split_batch_train_heldout(field, train_size=1, seed=2)
    with pytest.raises(ScopeValidationError, match="'batch'"):
        split_batch_train_heldout(_make_reduced_field_without_batch(_make_field()), train_size=1, seed=2)


def test_field_returning_utilities_deep_copy_metadata_and_preprocess_log() -> None:
    field = _make_field()

    noisy = add_gaussian_noise(field, std_fraction=0.0, seed=1)
    reduced = subsample_time(field, stride=2)
    train, _ = split_batch_train_heldout(field, train_size=2, seed=5)

    noisy.metadata["boundary_conditions"]["x"] = "changed"
    reduced.preprocess_log[0]["parameters"]["nested"]["level"] = 99
    train.metadata["parameter_tags"]["nested"]["tag"] = "changed"

    assert field.metadata["boundary_conditions"]["x"] == "periodic"
    assert field.preprocess_log[0]["parameters"]["nested"]["level"] == 1
    assert field.metadata["parameter_tags"]["nested"]["tag"] == "source"


def test_field_returning_utilities_work_with_mask_none_and_nontrivial_masks() -> None:
    unmasked = _make_field(mask=None)
    masked = _make_field(mask=np.zeros((4, 5, 4, 1), dtype=bool))
    masked.mask[0, 0, 0, 0] = True

    assert add_gaussian_noise(unmasked, std_fraction=0.0, seed=1).mask is None
    assert subsample_time(unmasked, stride=2).mask is None
    assert split_batch_train_heldout(unmasked, train_size=2, seed=1)[0].mask is None
    assert add_gaussian_noise(masked, std_fraction=0.0, seed=1).mask is not None
    assert subsample_x(masked, stride=2).mask is not None
    assert split_batch_train_heldout(masked, train_size=2, seed=1)[1].mask is not None


def test_summarize_recovery_grid_groups_rows_and_sorts_with_typed_keys() -> None:
    records = [
        {
            "conditions": {"mode": 1},
            "recovery": _make_recovery(classification="partial", residuals={"heldout_residual_l2": 0.3}),
        },
        {
            "conditions": {"mode": True},
            "recovery": _make_recovery(classification="exact", residuals={"heldout_residual_l2": 0.1}),
        },
        {
            "conditions": {"mode": 1},
            "recovery": _make_recovery(classification="failed", residuals={"heldout_residual_l2": 0.5}),
        },
    ]

    rows = summarize_recovery_grid(records)

    assert [row["conditions"] for row in rows] == [{"mode": True}, {"mode": 1}]
    assert rows[1]["num_records"] == 2
    assert rows[1]["partial_count"] == 1
    assert rows[1]["failed_count"] == 1
    assert rows[1]["mean_heldout_residual_l2"] == pytest.approx(0.4)


def test_summarize_recovery_grid_computes_counts_rates_and_optional_residual_means() -> None:
    records = [
        {
            "conditions": {"noise_std_fraction": 0.1, "sample_count": 4},
            "recovery": _make_recovery(
                classification="exact",
                residuals={"train_residual_l2": 0.2, "heldout_residual_l2": 0.4, "heldout_residual_rms": 0.1},
            ),
        },
        {
            "conditions": {"sample_count": 4, "noise_std_fraction": 0.1},
            "recovery": _make_recovery(
                classification="partial",
                residuals={"train_residual_l2": 0.4, "heldout_residual_l2": 0.6, "heldout_residual_rms": 0.2},
            ),
        },
    ]

    row = summarize_recovery_grid(records)[0]

    assert row["exact_count"] == 1
    assert row["partial_count"] == 1
    assert row["failed_count"] == 0
    assert row["exact_rate"] == pytest.approx(0.5)
    assert row["partial_rate"] == pytest.approx(0.5)
    assert row["failed_rate"] == pytest.approx(0.0)
    assert row["mean_support_precision"] == pytest.approx(1.0)
    assert row["mean_train_residual_l2"] == pytest.approx(0.3)
    assert row["mean_heldout_residual_l2"] == pytest.approx(0.5)
    assert row["mean_heldout_residual_rms"] == pytest.approx(0.15)


def test_summarize_recovery_grid_omits_optional_residual_means_when_not_universal() -> None:
    records = [
        {"conditions": {"noise": 0.1}, "recovery": _make_recovery(classification="exact")},
        {
            "conditions": {"noise": 0.1},
            "recovery": _make_recovery(classification="failed", residuals={"heldout_residual_l2": 0.7}),
        },
    ]

    row = summarize_recovery_grid(records)[0]

    assert "mean_heldout_residual_l2" not in row


def test_summarize_recovery_grid_rejects_nonfinite_optional_residuals() -> None:
    records = [
        {
            "conditions": {"noise": 0.1},
            "recovery": _make_recovery(classification="exact", residuals={"heldout_residual_l2": np.nan}),
        }
    ]

    with pytest.raises(SchemaValidationError):
        summarize_recovery_grid(records)


@pytest.mark.parametrize(
    "records",
    [
        [{"conditions": {"noise": np.nan}, "recovery": _make_recovery()}],
        [{"conditions": {"noise": 0.1}, "recovery": {**_make_recovery(), "classification": "bad"}}],
        [{"conditions": {"noise": 0.1}, "recovery": {**_make_recovery(), "support_precision": np.inf}}],
        [{"conditions": {"noise": [1, 2]}, "recovery": _make_recovery()}],
        [{"recovery": _make_recovery()}],
    ],
)
def test_summarize_recovery_grid_rejects_invalid_records(records: list[dict[str, object]]) -> None:
    with pytest.raises(SchemaValidationError):
        summarize_recovery_grid(records)


def test_summarize_recovery_grid_returns_empty_list_for_empty_input() -> None:
    assert summarize_recovery_grid([]) == []
