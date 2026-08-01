"""v0.37c: the parameter-equivariant admissibility benchmark.

Submodule-only. Nothing here is exported from :mod:`pdelie`.
"""

from __future__ import annotations

from pdelie.benchmarks.parameter_equivariant import (
    BENCHMARK_CASES,
    CONFIRMATORY_ALPHA_GRID,
    DEFAULT_TRANSLATION_CELLS,
    EXPECTED_CLASSIFICATIONS,
    PILOT_ALPHA_GRID,
    PROFILE_REGISTRY,
    BenchmarkCase,
    CoefficientProfile,
    alpha_grid,
    build_coefficient_field,
    resolve_case,
    run_admissibility_benchmark,
)

__all__ = [
    "BENCHMARK_CASES",
    "CONFIRMATORY_ALPHA_GRID",
    "DEFAULT_TRANSLATION_CELLS",
    "EXPECTED_CLASSIFICATIONS",
    "PILOT_ALPHA_GRID",
    "PROFILE_REGISTRY",
    "BenchmarkCase",
    "CoefficientProfile",
    "alpha_grid",
    "build_coefficient_field",
    "resolve_case",
    "run_admissibility_benchmark",
]
