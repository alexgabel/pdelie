from __future__ import annotations

import importlib
import json

import numpy as np
import pytest

import pdelie
from pdelie import GeneratorFamily, SchemaValidationError, ScopeValidationError
from pdelie.contracts import _translation_generator_basis_spec
from pdelie.data import generate_burgers_1d_field_batch, generate_heat_1d_field_batch
from pdelie.portability import (
    coerce_generator_family,
    export_generator_family_manifest,
    import_generator_family_manifest,
)
from pdelie.residuals import BurgersResidualEvaluator, HeatResidualEvaluator
from pdelie.symmetry.fitting import fit_translation_generator
from pdelie.verification import verify_translation_generator
from tests._helpers.kdv_feasibility import (
    KDV_FEASIBILITY_CONFIG,
    compute_kdv_feasibility_derivatives,
    compute_l2_norm,
    compute_mass,
    evaluate_kdv_feasibility_residual,
    exact_fourier_third_derivative,
    generate_kdv_1d_field_batch,
    sample_kdv_mode_coefficients,
)
from tests._helpers.portability_benchmark import (
    PORTABILITY_BENCHMARK_BRANCHES,
    run_portability_benchmark,
)


def _make_translation_family() -> GeneratorFamily:
    return GeneratorFamily(
        parameterization="polynomial_translation_affine",
        coefficients=np.array([[1.0, 0.0, 0.0, 0.0]], dtype=float),
        basis_spec=_translation_generator_basis_spec(),
        normalization="l2_unit",
        diagnostics={"source": "v0_5_release_gate"},
    )


def _x_basis_spec(*, labels: list[str], powers: list[list[int]]) -> dict[str, object]:
    return {
        "variables": ["x"],
        "component_names": ["xi"],
        "basis_terms": [
            {"label": label, "powers": power}
            for label, power in zip(labels, powers)
        ],
        "component_ordering": ["xi"],
        "term_ordering": list(labels),
        "layout": "component_major",
    }


def _make_polynomial_family(*, parameterization: str = "polynomial_point_family") -> GeneratorFamily:
    return GeneratorFamily(
        parameterization=parameterization,
        coefficients=np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 1.0]], dtype=float),
        basis_spec=_x_basis_spec(labels=["1", "x", "x^2"], powers=[[0], [1], [2]]),
        normalization="runtime_fixture",
        diagnostics={},
    )


def _legacy_translation_payload() -> dict[str, object]:
    return {
        "schema_version": "0.1",
        "parameterization": "polynomial_translation_affine",
        "coefficients": [1.0, 0.0, 0.0, 0.0],
        "normalization": "l2_unit",
        "diagnostics": {},
    }


def _canonical_family_meaning(generator: GeneratorFamily) -> dict[str, object]:
    payload = generator.to_dict()
    return {
        "schema_version": payload["schema_version"],
        "parameterization": payload["parameterization"],
        "coefficients": payload["coefficients"],
        "basis_spec": payload["basis_spec"],
        "normalization": payload["normalization"],
        "generator_names": payload.get("generator_names"),
    }


def _assert_trajectories_allclose(first: list[np.ndarray], second: list[np.ndarray]) -> None:
    assert len(first) == len(second)
    for first_trajectory, second_trajectory in zip(first, second):
        np.testing.assert_allclose(first_trajectory, second_trajectory, rtol=1e-9, atol=1e-12)


def _kdv_generation_kwargs() -> dict[str, object]:
    return {
        key: KDV_FEASIBILITY_CONFIG[key]
        for key in ("batch_size", "num_times", "num_points", "max_time", "num_modes", "amplitude", "num_substeps")
    }


def _make_kdv_fourier_mode_field() -> pdelie.FieldBatch:
    x = np.linspace(
        0.0,
        float(KDV_FEASIBILITY_CONFIG["domain_length"]),
        int(KDV_FEASIBILITY_CONFIG["num_points"]),
        endpoint=False,
        dtype=float,
    )
    t = np.linspace(0.0, 0.1, 3, dtype=float)
    cosine, sine = sample_kdv_mode_coefficients(
        batch_size=1,
        num_modes=2,
        seed=7,
        amplitude=0.08,
    )
    modes = np.arange(1, 3, dtype=float)
    spatial_values = np.sum(
        cosine[:, :, None] * np.cos(np.outer(modes, x))[None, :, :]
        + sine[:, :, None] * np.sin(np.outer(modes, x))[None, :, :],
        axis=1,
    )
    values = np.repeat(spatial_values[:, None, :, None], t.size, axis=1)
    field = pdelie.FieldBatch(
        values=values,
        dims=("batch", "time", "x", "var"),
        coords={"time": t, "x": x},
        var_names=["u"],
        metadata={
            "boundary_conditions": {"x": "periodic"},
            "coordinate_system": "cartesian",
            "grid_regularity": "uniform",
            "grid_type": "rectilinear",
            "parameter_tags": {"equation": "kdv_normalized"},
        },
        preprocess_log=[],
    )
    return field


def test_v0_5_release_gate_manifest_and_coercion_representative_slice() -> None:
    translation = _make_translation_family()
    translation_manifest = export_generator_family_manifest(translation)
    translation_loaded = json.loads(json.dumps(translation_manifest, allow_nan=False))
    expected_translation = _canonical_family_meaning(translation)

    assert _canonical_family_meaning(import_generator_family_manifest(translation_loaded)) == expected_translation
    assert _canonical_family_meaning(coerce_generator_family(translation.to_dict())) == expected_translation
    assert _canonical_family_meaning(coerce_generator_family(translation_manifest)) == expected_translation
    assert _canonical_family_meaning(coerce_generator_family(_legacy_translation_payload())) == expected_translation

    non_translation = _make_polynomial_family()
    non_translation_manifest = export_generator_family_manifest(non_translation)
    expected_non_translation = _canonical_family_meaning(non_translation)

    assert _canonical_family_meaning(import_generator_family_manifest(non_translation_manifest)) == expected_non_translation
    assert _canonical_family_meaning(coerce_generator_family(non_translation.to_dict())) == expected_non_translation
    assert _canonical_family_meaning(coerce_generator_family(non_translation_manifest)) == expected_non_translation

    malformed_manifest = dict(translation_manifest)
    malformed_manifest["unexpected"] = "field"
    with pytest.raises(SchemaValidationError, match="unknown top-level fields"):
        import_generator_family_manifest(malformed_manifest)

    unsupported_payload = _make_polynomial_family(parameterization="affine_external_family").to_dict()
    with pytest.raises(
        ScopeValidationError,
        match="only supports polynomial GeneratorFamily parameterizations",
    ):
        coerce_generator_family(unsupported_payload)


def test_v0_5_release_gate_portability_benchmark_representative_slice_is_stable() -> None:
    first = run_portability_benchmark()
    second = run_portability_benchmark()

    assert first["branch_names"] == list(PORTABILITY_BENCHMARK_BRANCHES)
    assert second["branch_names"] == list(PORTABILITY_BENCHMARK_BRANCHES)

    expected_render = first["translation"]["rendered"]["in_memory"]
    reference_closure = first["closure"]["reports"]["in_memory"]
    for branch_name in PORTABILITY_BENCHMARK_BRANCHES:
        assert first["translation"]["rendered"][branch_name] == expected_render
        assert second["translation"]["rendered"][branch_name] == expected_render

        first_span = first["span"]["reports"][branch_name]
        second_span = second["span"]["reports"][branch_name]
        assert first_span["comparison_rank"] == second_span["comparison_rank"] == 2
        np.testing.assert_allclose(first_span["principal_angles_radians"], [0.0, 0.0], atol=1e-7)
        np.testing.assert_allclose(
            first_span["principal_angles_radians"],
            second_span["principal_angles_radians"],
            rtol=1e-9,
            atol=1e-12,
        )
        assert first_span["projection_residual"]["summary"] == pytest.approx(0.0, abs=1e-12)
        assert second_span["projection_residual"]["summary"] == pytest.approx(0.0, abs=1e-12)

        first_closure = first["closure"]["reports"][branch_name]
        second_closure = second["closure"]["reports"][branch_name]
        assert first_closure["computation_mode"] == reference_closure["computation_mode"]
        assert second_closure["computation_mode"] == reference_closure["computation_mode"]
        assert first_closure["family_rank"] == reference_closure["family_rank"]
        assert second_closure["family_rank"] == reference_closure["family_rank"]
        assert first_closure["closure"]["summary"] == pytest.approx(
            reference_closure["closure"]["summary"],
            abs=1e-12,
        )
        assert second_closure["closure"]["summary"] == pytest.approx(
            reference_closure["closure"]["summary"],
            abs=1e-12,
        )

        first_downstream = first["downstream"]["branches"][branch_name]
        second_downstream = second["downstream"]["branches"][branch_name]
        assert first_downstream["feature_names"] == second_downstream["feature_names"]
        np.testing.assert_allclose(
            first_downstream["time_values"],
            second_downstream["time_values"],
            rtol=1e-9,
            atol=1e-12,
        )
        np.testing.assert_allclose(
            first_downstream["transformed"].values,
            second_downstream["transformed"].values,
            rtol=1e-9,
            atol=1e-12,
        )
        _assert_trajectories_allclose(
            first_downstream["trajectories"],
            second_downstream["trajectories"],
        )


def test_v0_5_release_gate_heat_and_burgers_representative_slice_remains_exact() -> None:
    heat_training = generate_heat_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=50)
    heat_heldout = generate_heat_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=51)
    burgers_training = generate_burgers_1d_field_batch(batch_size=4, num_times=33, num_points=64, seed=52)
    burgers_heldout = generate_burgers_1d_field_batch(batch_size=3, num_times=33, num_points=64, seed=53)

    heat_generator = fit_translation_generator(heat_training, HeatResidualEvaluator(), epsilon=1e-4)
    burgers_generator = fit_translation_generator(burgers_training, BurgersResidualEvaluator(), epsilon=1e-4)
    heat_report = verify_translation_generator(heat_heldout, heat_generator, HeatResidualEvaluator())
    burgers_report = verify_translation_generator(burgers_heldout, burgers_generator, BurgersResidualEvaluator())

    for generator in (heat_generator, burgers_generator):
        assert generator.schema_version == "0.2"
        assert generator.parameterization == "polynomial_translation_affine"
        assert generator.coefficients.shape == (1, 4)
        assert generator.basis_spec["variables"] == ["t", "x", "u"]
        assert generator.basis_spec["component_names"] == ["xi"]
        assert generator.basis_spec["term_ordering"] == ["1", "t", "x", "u"]
        assert generator.basis_spec["layout"] == "component_major"

    assert heat_report.classification == "exact"
    assert burgers_report.classification == "exact"


def test_v0_5_release_gate_kdv_representative_outcome_remains_gated() -> None:
    field = _make_kdv_fourier_mode_field()
    derivatives = compute_kdv_feasibility_derivatives(field)
    cosine, sine = sample_kdv_mode_coefficients(
        batch_size=1,
        num_modes=2,
        seed=7,
        amplitude=0.08,
    )
    expected_u_xxx = exact_fourier_third_derivative(
        x=np.asarray(field.coords["x"], dtype=float),
        cosine_coefficients=cosine,
        sine_coefficients=sine,
    )
    np.testing.assert_allclose(
        derivatives.derivatives["u_xxx"][:, 0, :, 0],
        expected_u_xxx,
        atol=1e-9,
        rtol=1e-9,
    )

    rollout = generate_kdv_1d_field_batch(seed=13, **_kdv_generation_kwargs())
    residual = evaluate_kdv_feasibility_residual(rollout)
    mass = compute_mass(rollout)
    l2 = compute_l2_norm(rollout)
    mass_drift = np.max(np.abs(mass - mass[:, [0]]))
    relative_l2_drift = np.max(np.abs(l2 - l2[:, [0]]) / np.maximum(np.abs(l2[:, [0]]), 1e-12))

    assert residual.definition_type == "analytic"
    assert np.max(np.abs(residual.residual)) < 1e-2
    assert mass_drift <= 1e-8
    assert relative_l2_drift <= 5e-3

    assert not hasattr(pdelie, "KdVResidualEvaluator")
    assert not hasattr(pdelie, "generate_kdv_1d_field_batch")

    data_module = importlib.import_module("pdelie.data")
    residuals_module = importlib.import_module("pdelie.residuals")
    assert not hasattr(data_module, "generate_kdv_1d_field_batch")
    assert not hasattr(residuals_module, "KdVResidualEvaluator")
