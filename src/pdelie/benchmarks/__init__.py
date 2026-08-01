"""v0.37c: the six-case parameter-equivariant admissibility benchmark.

Submodule-only. Nothing here is exported from :mod:`pdelie`.
"""

from __future__ import annotations

from pdelie.benchmarks.parameter_equivariant import (
    CONFIRMATORY_ALPHA_GRID,
    EXPECTED_CLASSIFICATIONS,
    PILOT_ALPHA_GRID,
    PROFILE_REGISTRY,
    SIX_BENCHMARK_CASES,
    BenchmarkCase,
    CoefficientProfile,
    alpha_grid,
    build_coefficient_field,
    resolve_case,
    run_admissibility_benchmark,
)

__all__ = [
    "CONFIRMATORY_ALPHA_GRID",
    "EXPECTED_CLASSIFICATIONS",
    "PILOT_ALPHA_GRID",
    "PROFILE_REGISTRY",
    "SIX_BENCHMARK_CASES",
    "BenchmarkCase",
    "CoefficientProfile",
    "alpha_grid",
    "build_coefficient_field",
    "resolve_case",
    "run_admissibility_benchmark",
]
