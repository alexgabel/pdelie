from __future__ import annotations

import importlib

import numpy as np
import pytest

import pdelie
from pdelie import GeneratorFamily
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.data import (
    add_gaussian_noise,
    generate_burgers_1d_field_batch,
    generate_heat_1d_field_batch,
    split_batch_train_heldout,
    subsample_time,
    subsample_x,
)
from pdelie.discovery import (
    build_translation_canonical_discovery_inputs,
    evaluate_discovery_recovery,
    fit_pysindy_discovery,
    summarize_recovery_grid,
    to_pysindy_trajectories,
)
from pdelie.portability import coerce_generator_family, export_generator_family_manifest


_DISCOVERY_KWARGS = {"batch_size": 2, "num_times": 17, "num_points": 16}
_ROBUSTNESS_KWARGS = {"batch_size": 4, "num_times": 17, "num_points": 16}


def _require_downstream_or_skip() -> None:
    pytest.importorskip(
        "pysindy",
        reason="v0.6 release gate requires optional downstream dependencies (install pdelie[test] or pdelie[downstream]).",
    )
    pytest.importorskip(
        "sklearn.metrics",
        reason="v0.6 release gate requires optional downstream dependencies (install pdelie[test] or pdelie[downstream]).",
    )


def _make_translation_generator() -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={},
    )


def _assert_structural_fit_success(result: dict[str, object], feature_names: list[str]) -> None:
    assert result["status"] == "success"
    assert result["backend"] == "pysindy"
    assert result["feature_names"] == feature_names

    coefficients = result["coefficients"]
    library_feature_names = result["library_feature_names"]
    assert isinstance(library_feature_names, list)
    assert coefficients.shape == (len(feature_names), len(library_feature_names))
    assert np.all(np.isfinite(coefficients))


def _assert_trajectories_allclose(first: list[np.ndarray], second: list[np.ndarray]) -> None:
    assert len(first) == len(second)
    for first_trajectory, second_trajectory in zip(first, second):
        np.testing.assert_allclose(first_trajectory, second_trajectory, rtol=1e-9, atol=1e-12)


def test_v0_6_release_gate_metrics_slice_is_deterministic_and_typed() -> None:
    exact_target = {"u_xx": 1.0}
    exact_discovered = {"u_xx": 1.0}
    partial_target = {"u_xx": 1.0, "u": 2.0}
    partial_discovered = {"u_xx": 1.0, "u_x": 3.0}
    failed_target = {"u": 1.0}
    failed_discovered = {"u_x": 2.0}

    exact_first = evaluate_discovery_recovery(exact_target, exact_discovered)
    exact_second = evaluate_discovery_recovery(exact_target, exact_discovered)
    partial = evaluate_discovery_recovery(partial_target, partial_discovered)
    failed = evaluate_discovery_recovery(failed_target, failed_discovered)

    assert exact_first == exact_second
    assert exact_first["classification"] == "exact"
    assert exact_first["classification_basis"] == "support"
    assert partial["classification"] == "partial"
    assert failed["classification"] == "failed"

    for result in (exact_first, partial, failed):
        for key in (
            "support_precision",
            "support_recall",
            "support_f1",
            "coefficient_l2_error",
            "coefficient_relative_l2_error",
            "coefficient_linf_error",
        ):
            assert np.isfinite(result[key])


def test_v0_6_release_gate_heat_smoke_fit_is_structurally_valid() -> None:
    _require_downstream_or_skip()

    field = generate_heat_1d_field_batch(seed=6001, **_DISCOVERY_KWARGS)
    trajectories, time_values, feature_names = to_pysindy_trajectories(field)

    result = fit_pysindy_discovery(trajectories, time_values, feature_names)

    _assert_structural_fit_success(result, feature_names)


def test_v0_6_release_gate_burgers_smoke_fit_is_structurally_valid() -> None:
    _require_downstream_or_skip()

    field = generate_burgers_1d_field_batch(seed=6002, **_DISCOVERY_KWARGS)
    trajectories, time_values, feature_names = to_pysindy_trajectories(field)

    result = fit_pysindy_discovery(trajectories, time_values, feature_names)

    _assert_structural_fit_success(result, feature_names)


def test_v0_6_release_gate_translation_input_representative_slices_are_deterministic() -> None:
    _require_downstream_or_skip()

    field = generate_heat_1d_field_batch(seed=6003, **_DISCOVERY_KWARGS)
    raw_trajectories, raw_time_values, raw_feature_names = to_pysindy_trajectories(field)
    raw_result = fit_pysindy_discovery(raw_trajectories, raw_time_values, raw_feature_names)
    _assert_structural_fit_success(raw_result, raw_feature_names)

    generator = _make_translation_generator()
    known = build_translation_canonical_discovery_inputs(field, generator_family=generator)
    known_result = fit_pysindy_discovery(
        known["trajectories"],
        known["time_values"],
        known["feature_names"],
    )
    _assert_structural_fit_success(known_result, known["feature_names"])
    assert known["provenance"]["input_mode"] == "generator_family"

    manifest = export_generator_family_manifest(generator)
    coerced = coerce_generator_family(manifest)
    imported = build_translation_canonical_discovery_inputs(field, generator_family=coerced)
    imported_result = fit_pysindy_discovery(
        imported["trajectories"],
        imported["time_values"],
        imported["feature_names"],
    )
    _assert_structural_fit_success(imported_result, imported["feature_names"])

    assert known["generator_metadata"] == imported["generator_metadata"] == generator.to_dict()
    np.testing.assert_allclose(known["alignment_shifts"], imported["alignment_shifts"], rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(known["time_values"], imported["time_values"], rtol=1e-9, atol=1e-12)
    assert known["feature_names"] == imported["feature_names"]
    _assert_trajectories_allclose(known["trajectories"], imported["trajectories"])


def test_v0_6_release_gate_robustness_slice_and_no_kdv_public_surface() -> None:
    field = generate_heat_1d_field_batch(seed=6004, **_ROBUSTNESS_KWARGS)

    noisy = add_gaussian_noise(field, std_fraction=1e-3, seed=6005)
    time_subsampled = subsample_time(noisy, stride=2)
    x_subsampled = subsample_x(time_subsampled, stride=2)
    train_field, heldout_field = split_batch_train_heldout(x_subsampled, train_size=2, seed=6006)

    train_field.validate()
    heldout_field.validate()

    expected_operations = [
        "add_gaussian_noise",
        "subsample_time",
        "subsample_x",
        "split_batch_train_heldout",
    ]
    assert [entry["operation"] for entry in train_field.preprocess_log] == expected_operations
    assert [entry["operation"] for entry in heldout_field.preprocess_log] == expected_operations

    records = [
        {
            "conditions": {"noise_std_fraction": 1e-3, "time_stride": 2, "x_stride": 2},
            "recovery": evaluate_discovery_recovery({"u_xx": 1.0}, {"u_xx": 1.0}),
        },
        {
            "conditions": {"noise_std_fraction": 1e-3, "time_stride": 2, "x_stride": 2},
            "recovery": evaluate_discovery_recovery({"u_xx": 1.0, "u": 2.0}, {"u_xx": 1.0, "u_x": 3.0}),
        },
    ]
    rows = summarize_recovery_grid(records)

    assert len(rows) == 1
    row = rows[0]
    assert row["num_records"] == 2
    assert row["exact_count"] == 1
    assert row["partial_count"] == 1
    assert row["failed_count"] == 0
    for key, value in row.items():
        if key == "conditions":
            continue
        if isinstance(value, (int, float)):
            assert np.isfinite(value)

    data_module = importlib.import_module("pdelie.data")
    residuals_module = importlib.import_module("pdelie.residuals")

    for name in ("generate_kdv_1d_field_batch", "sample_kdv_mode_coefficients", "KDVResidualEvaluator", "KdVResidualEvaluator"):
        assert not hasattr(pdelie, name)
    for name in ("generate_kdv_1d_field_batch", "sample_kdv_mode_coefficients"):
        assert not hasattr(data_module, name)
    for name in ("KDVResidualEvaluator", "KdVResidualEvaluator", "KdvResidualEvaluator"):
        assert not hasattr(residuals_module, name)
