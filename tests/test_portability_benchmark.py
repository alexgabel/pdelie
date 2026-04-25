from __future__ import annotations

import importlib

import numpy as np
import pytest

from pdelie import GeneratorFamily, SchemaValidationError, ScopeValidationError
from pdelie.portability import coerce_generator_family, export_generator_family_manifest, import_generator_family_manifest
from tests._helpers.portability_benchmark import run_portability_benchmark


def _assert_trajectories_allclose(first: list[np.ndarray], second: list[np.ndarray]) -> None:
    assert len(first) == len(second)
    for first_trajectory, second_trajectory in zip(first, second):
        np.testing.assert_allclose(first_trajectory, second_trajectory, rtol=1e-9, atol=1e-12)


def test_portability_benchmark_is_reproducible() -> None:
    first = run_portability_benchmark()
    second = run_portability_benchmark()

    assert first["settings"] == second["settings"]
    assert first["branch_names"] == second["branch_names"]
    assert first["translation"]["legacy_rendered"] == second["translation"]["legacy_rendered"]
    assert first["downstream"]["shift"] == pytest.approx(second["downstream"]["shift"])

    for branch_name in first["branch_names"]:
        assert first["translation"]["rendered"][branch_name] == second["translation"]["rendered"][branch_name]

        first_span = first["span"]["reports"][branch_name]
        second_span = second["span"]["reports"][branch_name]
        assert first_span["comparison_rank"] == second_span["comparison_rank"]
        np.testing.assert_allclose(
            first_span["principal_angles_radians"],
            second_span["principal_angles_radians"],
            rtol=1e-9,
            atol=1e-12,
        )
        assert first_span["projection_residual"]["summary"] == pytest.approx(
            second_span["projection_residual"]["summary"],
            abs=1e-12,
        )

        first_closure = first["closure"]["reports"][branch_name]
        second_closure = second["closure"]["reports"][branch_name]
        assert first_closure["computation_mode"] == second_closure["computation_mode"]
        assert first_closure["family_rank"] == second_closure["family_rank"]
        assert first_closure["closure"]["summary"] == pytest.approx(
            second_closure["closure"]["summary"],
            abs=1e-12,
        )
        assert first_closure["antisymmetry"]["summary"] == pytest.approx(
            second_closure["antisymmetry"]["summary"],
            abs=1e-12,
        )
        assert first_closure["jacobi"]["summary"] == pytest.approx(
            second_closure["jacobi"]["summary"],
            abs=1e-12,
        )
        np.testing.assert_allclose(
            first_closure["structure_constants"]["tensor"],
            second_closure["structure_constants"]["tensor"],
            rtol=1e-9,
            atol=1e-12,
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


def test_portability_benchmark_positive_branches_preserve_semantics() -> None:
    benchmark = run_portability_benchmark()

    expected_render = benchmark["translation"]["rendered"]["in_memory"]
    for branch_name in benchmark["branch_names"]:
        assert benchmark["translation"]["rendered"][branch_name] == expected_render

        span_report = benchmark["span"]["reports"][branch_name]
        assert span_report["comparison_rank"] == 2
        np.testing.assert_allclose(span_report["principal_angles_radians"], [0.0, 0.0], atol=1e-7)
        assert span_report["projection_residual"]["summary"] == pytest.approx(0.0, abs=1e-12)

    reference_closure = benchmark["closure"]["reports"]["in_memory"]
    for branch_name in benchmark["branch_names"]:
        report = benchmark["closure"]["reports"][branch_name]
        assert report["computation_mode"] == reference_closure["computation_mode"] == "sampled_projection"
        assert report["family_rank"] == reference_closure["family_rank"]
        assert report["closure"]["summary"] == pytest.approx(
            reference_closure["closure"]["summary"],
            abs=1e-12,
        )
        assert report["antisymmetry"]["summary"] == pytest.approx(
            reference_closure["antisymmetry"]["summary"],
            abs=1e-12,
        )
        assert report["jacobi"]["summary"] == pytest.approx(
            reference_closure["jacobi"]["summary"],
            abs=1e-12,
        )
        np.testing.assert_allclose(
            report["structure_constants"]["tensor"],
            reference_closure["structure_constants"]["tensor"],
            atol=1e-12,
        )


def test_portability_benchmark_legacy_translation_branch_preserves_downstream_behavior() -> None:
    benchmark = run_portability_benchmark()

    expected_render = benchmark["translation"]["rendered"]["in_memory"]
    assert benchmark["translation"]["legacy_rendered"] == expected_render

    reference = benchmark["downstream"]["branches"]["in_memory"]
    legacy = benchmark["downstream"]["legacy"]

    assert legacy["feature_names"] == reference["feature_names"]
    np.testing.assert_allclose(legacy["time_values"], reference["time_values"], rtol=1e-9, atol=1e-12)
    np.testing.assert_allclose(legacy["transformed"].values, reference["transformed"].values, rtol=1e-9, atol=1e-12)
    _assert_trajectories_allclose(legacy["trajectories"], reference["trajectories"])


def test_portability_benchmark_negative_controls_remain_typed() -> None:
    manifest = export_generator_family_manifest(run_portability_benchmark()["translation"]["families"]["in_memory"])
    manifest["unexpected"] = "field"

    with pytest.raises(SchemaValidationError, match="unknown top-level fields"):
        import_generator_family_manifest(manifest)

    unsupported_payload = GeneratorFamily(
        parameterization="affine_external_family",
        coefficients=np.array([[1.0, 0.0]], dtype=float),
        basis_spec={
            "variables": ["x"],
            "component_names": ["xi"],
            "basis_terms": [
                {"label": "1", "powers": [0]},
                {"label": "x", "powers": [1]},
            ],
            "component_ordering": ["xi"],
            "term_ordering": ["1", "x"],
            "layout": "component_major",
        },
        normalization="runtime_fixture",
        diagnostics={},
    ).to_dict()

    with pytest.raises(ScopeValidationError, match="only supports polynomial GeneratorFamily parameterizations"):
        coerce_generator_family(unsupported_payload)


def test_portability_benchmark_viz_smoke_is_optional() -> None:
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg", force=True)
    plt = importlib.import_module("matplotlib.pyplot")
    Figure = importlib.import_module("matplotlib.figure").Figure
    from pdelie.viz import (
        plot_closure_diagnostics,
        plot_generator_coefficients,
        plot_generator_symbolic_summary,
        plot_span_diagnostics,
    )

    benchmark = run_portability_benchmark()
    figures = [
        plot_generator_coefficients(benchmark["translation"]["families"]["in_memory"]),
        plot_generator_symbolic_summary(benchmark["translation"]["families"]["manifest"]),
        plot_span_diagnostics(benchmark["span"]["reports"]["manifest"]),
        plot_closure_diagnostics(benchmark["closure"]["reports"]["manifest"]),
    ]

    try:
        assert all(isinstance(figure, Figure) for figure in figures)
    finally:
        plt.close("all")
