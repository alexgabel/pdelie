from __future__ import annotations

from pdelie.examples import run_heat_vertical_slice_example


def test_heat_vertical_slice_example_runs_end_to_end() -> None:
    result = run_heat_vertical_slice_example()
    assert result["backend"] == "spectral_fd"
    assert result["parameterization"] == "polynomial_translation_affine"
    assert result["verification_classification"] == "exact"


def test_heat_vertical_slice_example_is_deterministic() -> None:
    first = run_heat_vertical_slice_example()
    second = run_heat_vertical_slice_example()

    assert first["verification_classification"] == second["verification_classification"]
    assert first["backend"] == second["backend"]
    assert first["parameterization"] == second["parameterization"]
    assert first["coefficients"] == second["coefficients"]
    assert first["error_curve"] == second["error_curve"]
