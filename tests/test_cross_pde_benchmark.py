from __future__ import annotations

import numpy as np

from pdelie.verification import DEFAULT_EPSILON_VALUES, DEFAULT_RELATIVE_L2_NORM
from tests._helpers.cross_pde_benchmark import (
    CROSS_PDE_BENCHMARK_CONFIG,
    run_clean_cross_pde_benchmark,
    run_noisy_cross_pde_benchmark,
)


def test_clean_cross_pde_benchmark_is_exact_for_heat_and_burgers() -> None:
    benchmark = run_clean_cross_pde_benchmark()
    assert benchmark["heat"]["report"].classification == "exact"
    assert benchmark["burgers"]["report"].classification == "exact"


def test_noisy_cross_pde_benchmark_requires_approximate_or_exact_for_heat_and_burgers() -> None:
    benchmark = run_noisy_cross_pde_benchmark()
    assert benchmark["heat"]["report"].classification in {"exact", "approximate"}
    assert benchmark["burgers"]["report"].classification in {"exact", "approximate"}
    assert benchmark["heat"]["noise_std_fraction"] == benchmark["burgers"]["noise_std_fraction"]
    assert benchmark["heat"]["noise_std_fraction"] == 2e-4
    assert benchmark["heat"]["noise_std_fraction"] == CROSS_PDE_BENCHMARK_CONFIG["noise_std_fraction"]


def test_cross_pde_benchmark_reuses_shared_verification_defaults() -> None:
    benchmark = run_clean_cross_pde_benchmark()
    for key in ("heat", "burgers"):
        result = benchmark[key]
        settings = result["settings"]
        assert settings["backend"] == "spectral_fd"
        assert settings["norm"] == DEFAULT_RELATIVE_L2_NORM
        assert settings["min_heldout_initial_conditions"] == 3
        np.testing.assert_allclose(result["epsilon_values"], DEFAULT_EPSILON_VALUES)
        np.testing.assert_allclose(result["report"].epsilon_values, DEFAULT_EPSILON_VALUES)
    assert benchmark["heat"]["settings"] == benchmark["burgers"]["settings"]


def test_cross_pde_benchmark_is_reproducible() -> None:
    first_clean = run_clean_cross_pde_benchmark()
    second_clean = run_clean_cross_pde_benchmark()
    first_noisy = run_noisy_cross_pde_benchmark()
    second_noisy = run_noisy_cross_pde_benchmark()

    for first, second in ((first_clean, second_clean), (first_noisy, second_noisy)):
        for key in ("heat", "burgers"):
            first_result = first[key]
            second_result = second[key]
            assert first_result["report"].classification == second_result["report"].classification
            assert first_result["settings"] == second_result["settings"]
            assert first_result["noise_seed"] == second_result["noise_seed"]
            np.testing.assert_allclose(
                first_result["report"].error_curve,
                second_result["report"].error_curve,
                rtol=1e-9,
                atol=1e-12,
            )
