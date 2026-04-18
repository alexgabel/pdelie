from __future__ import annotations

import numpy as np
import pytest

from tests._helpers.downstream_benchmark import DOWNSTREAM_BENCHMARK_CONFIG, run_downstream_benchmark


def _run_benchmark_or_skip():
    try:
        return run_downstream_benchmark()
    except ImportError as exc:
        pytest.skip(str(exc))


def _assert_trajectories_allclose(first: list[np.ndarray], second: list[np.ndarray]) -> None:
    assert len(first) == len(second)
    for first_trajectory, second_trajectory in zip(first, second):
        np.testing.assert_allclose(first_trajectory, second_trajectory, rtol=1e-9, atol=1e-12)


@pytest.fixture(scope="module")
def downstream_benchmark():
    return _run_benchmark_or_skip()


def test_downstream_benchmark_is_reproducible() -> None:
    first = _run_benchmark_or_skip()
    second = _run_benchmark_or_skip()

    for pde_name in ("heat", "burgers"):
        first_result = first[pde_name]
        second_result = second[pde_name]
        assert first_result["settings"] == second_result["settings"]
        assert first_result["data_seeds"] == second_result["data_seeds"]
        np.testing.assert_allclose(first_result["time_values"], second_result["time_values"], rtol=1e-9, atol=1e-12)
        assert first_result["feature_names"] == second_result["feature_names"]

        for branch_name in DOWNSTREAM_BENCHMARK_CONFIG["branch_names"]:
            first_branch = first_result["branches"][branch_name]
            second_branch = second_result["branches"][branch_name]
            assert first_branch["train_shift_seed"] == second_branch["train_shift_seed"]
            assert first_branch["heldout_shift_seed"] == second_branch["heldout_shift_seed"]
            assert first_branch["train_shifts"] == second_branch["train_shifts"]
            assert first_branch["heldout_shifts"] == second_branch["heldout_shifts"]
            assert first_branch["score"] == pytest.approx(second_branch["score"])
            _assert_trajectories_allclose(first_branch["train_trajectories"], second_branch["train_trajectories"])
            _assert_trajectories_allclose(first_branch["heldout_trajectories"], second_branch["heldout_trajectories"])


def test_downstream_benchmark_uses_matched_settings_and_branch_structure(downstream_benchmark) -> None:
    expected_branches = tuple(DOWNSTREAM_BENCHMARK_CONFIG["branch_names"])
    assert downstream_benchmark["heat"]["settings"] == downstream_benchmark["burgers"]["settings"]

    for pde_name in ("heat", "burgers"):
        result = downstream_benchmark[pde_name]
        assert result["pde_name"] == pde_name
        assert tuple(result["branches"]) == expected_branches
        assert len(result["time_values"]) == int(DOWNSTREAM_BENCHMARK_CONFIG["num_times"])
        assert len(result["feature_names"]) == int(DOWNSTREAM_BENCHMARK_CONFIG["num_points"])

        for branch_name in expected_branches:
            branch = result["branches"][branch_name]
            assert len(branch["train_trajectories"]) == int(DOWNSTREAM_BENCHMARK_CONFIG["train_batch_size"])
            assert len(branch["heldout_trajectories"]) == int(DOWNSTREAM_BENCHMARK_CONFIG["heldout_batch_size"])
            for trajectory in branch["train_trajectories"]:
                assert trajectory.shape == (
                    int(DOWNSTREAM_BENCHMARK_CONFIG["num_times"]),
                    int(DOWNSTREAM_BENCHMARK_CONFIG["num_points"]),
                )
            for trajectory in branch["heldout_trajectories"]:
                assert trajectory.shape == (
                    int(DOWNSTREAM_BENCHMARK_CONFIG["num_times"]),
                    int(DOWNSTREAM_BENCHMARK_CONFIG["num_points"]),
                )


def test_downstream_benchmark_known_and_discovered_branches_are_equivalent(downstream_benchmark) -> None:
    for pde_name in ("heat", "burgers"):
        known = downstream_benchmark[pde_name]["branches"]["known_invariant"]
        discovered = downstream_benchmark[pde_name]["branches"]["discovered_invariant"]

        assert known["train_shifts"] == discovered["train_shifts"]
        assert known["heldout_shifts"] == discovered["heldout_shifts"]
        assert known["score"] == pytest.approx(discovered["score"])
        _assert_trajectories_allclose(known["train_trajectories"], discovered["train_trajectories"])
        _assert_trajectories_allclose(known["heldout_trajectories"], discovered["heldout_trajectories"])


def test_downstream_benchmark_nuisance_branch_is_reproducible_and_distinct(downstream_benchmark) -> None:
    for pde_name in ("heat", "burgers"):
        known = downstream_benchmark[pde_name]["branches"]["known_invariant"]
        nuisance = downstream_benchmark[pde_name]["branches"]["nuisance"]

        assert nuisance["train_shift_seed"] is not None
        assert nuisance["heldout_shift_seed"] is not None
        assert nuisance["train_shifts"] != known["train_shifts"]
        assert nuisance["heldout_shifts"] != known["heldout_shifts"]
        assert any(
            not np.allclose(known_trajectory, nuisance_trajectory)
            for known_trajectory, nuisance_trajectory in zip(
                known["train_trajectories"],
                nuisance["train_trajectories"],
            )
        )
        assert any(
            not np.allclose(known_trajectory, nuisance_trajectory)
            for known_trajectory, nuisance_trajectory in zip(
                known["heldout_trajectories"],
                nuisance["heldout_trajectories"],
            )
        )


def test_downstream_benchmark_release_gate_is_satisfied(downstream_benchmark) -> None:
    for pde_name in ("heat", "burgers"):
        for branch_name in DOWNSTREAM_BENCHMARK_CONFIG["branch_names"]:
            branch = downstream_benchmark[pde_name]["branches"][branch_name]
            assert np.isfinite(branch["score"])

    heat_known = downstream_benchmark["heat"]["branches"]["known_invariant"]["score"]
    heat_discovered = downstream_benchmark["heat"]["branches"]["discovered_invariant"]["score"]
    assert heat_known == pytest.approx(heat_discovered)

    burgers_known = downstream_benchmark["burgers"]["branches"]["known_invariant"]["score"]
    burgers_discovered = downstream_benchmark["burgers"]["branches"]["discovered_invariant"]["score"]
    burgers_nuisance = downstream_benchmark["burgers"]["branches"]["nuisance"]["score"]

    assert burgers_known == pytest.approx(burgers_discovered)
    assert burgers_known > burgers_nuisance
    assert burgers_discovered > burgers_nuisance
