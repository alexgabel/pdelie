"""v0.31c compact JSON-only example — the downstream discovery task bridge.

Demonstrates both v0.31 downstream task paths side-by-side on one canonical
periodic scalar 1D field:

- ``pdelie.tasks.run_pysindy_pde_task`` (v0.31b1) — executable PySINDy
  ``PDELibrary``-backed sparse-discovery task returning a strict-JSON
  ``discovery_task_result``.
- ``pdelie.tasks.inspect_pysindy_weak_pde_library`` (v0.31b2) — diagnostic
  wrapper around PySINDy's ``WeakPDELibrary`` returning a strict-JSON
  ``pdelie_weak_pde_library_diagnostic`` (``diagnostic_only = True``).

The example is deterministic under the frozen seed and library configuration
below. It composes a single top-level object with ``summary_type =
"downstream_discovery_task_bridge_example"``. That top-level object is a
composed narrative wrapper — it is NOT a new report schema, and it does NOT
alter the 22-key ``discovery_task_result`` or the 27-key
``pdelie_weak_pde_library_diagnostic`` schemas produced by the underlying
task surfaces.

Scope boundaries encoded in the emitted payload:

- PDELibrary path is executable downstream sparse-discovery.
- WeakPDELibrary path is diagnostic-only.
- The example does not establish WSINDy performance.
- The example does not establish noise robustness.
- The example is periodic scalar 1D only.
- PySINDy 2.1.x is the supported downstream backend on v0.32+.

Submodule-only surface. No root ``pdelie`` re-export.
"""

from __future__ import annotations

import importlib.metadata as _importlib_metadata
import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import numpy as np

from pdelie.data import generate_heat_1d_field_batch
from pdelie.tasks import (
    WeakPDELibraryDiagnostic,
    inspect_pysindy_weak_pde_library,
    run_pysindy_pde_task,
)

_SUMMARY_TYPE = "downstream_discovery_task_bridge_example"
_SUMMARY_SCHEMA_VERSION = "0.1"

# Frozen configuration — do not tune. The example is deterministic under
# these constants; changes here are a public-surface change and must be
# discussed on the ROADMAP.
_SEED = 31_000
_BATCH_SIZE = 1
_NUM_TIMES = 64
_NUM_POINTS = 64
_TASK_NAME = "downstream_discovery_task_bridge_example_pde_library"
_WEAK_TASK_NAME = "downstream_discovery_task_bridge_example_weak_diagnostic"
_WEAK_K = 16
_POLYNOMIAL_DEGREE = 2
_DERIVATIVE_ORDER = 2

_INTERPRETATION: dict[str, str] = {
    "pde_library_path": (
        "PDELibrary path is an executable downstream sparse-discovery task; "
        "the returned payload is a strict-JSON discovery_task_result."
    ),
    "weak_pde_library_path": (
        "WeakPDELibrary path is diagnostic-only; the returned payload is a "
        "strict-JSON pdelie_weak_pde_library_diagnostic with "
        "diagnostic_only = True and is not a validated weak sparse-recovery "
        "result."
    ),
    "wsindy_claim": "The example does not establish WSINDy performance.",
    "noise_claim": "The example does not establish noise robustness.",
    "scope_boundary": "The example is periodic scalar 1D only.",
    "pysindy_version_policy": (
        "PySINDy 2.1.x is the supported downstream backend on the v0.32 "
        "modern line. The v0.31.x legacy line is maintained on a separate "
        "branch. See docs/design/RUNTIME_COMPATIBILITY_POLICY.md."
    ),
}

_SCOPE_BOUNDARIES: dict[str, bool] = {
    "periodic_scalar_1d_only": True,
    "wsindy_benchmark_claimed": False,
    "noise_robustness_claimed": False,
    "nonperiodic_discovery_claimed": False,
    "root_pdelie_export_added": False,
    "new_summary_type_introduced": False,
    "pysindy_2x_supported": False,
}


def _resolve_backend_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for dist_name, key in (
        ("pdelie", "pdelie"),
        ("pysindy", "pysindy"),
        ("scikit-learn", "sklearn"),
        ("scipy", "scipy"),
        ("numpy", "numpy"),
    ):
        try:
            versions[key] = _importlib_metadata.version(dist_name)
        except _importlib_metadata.PackageNotFoundError:
            continue
    return versions


@contextmanager
def _legacy_numpy_rng_seed_scope(seed: int) -> Iterator[None]:
    """Seed the LEGACY ``np.random`` global RNG for the duration of the
    context, then restore the caller's state on exit.

    PySINDy 2.1.x's ``WeakPDELibrary`` still randomizes K subdomain-center
    placement using ``np.random.*`` — the legacy global RNG — and does not
    accept a modern ``np.random.Generator`` (verified in the v0.32a
    preflight audit). Reproducing the example deterministically therefore
    requires seeding the legacy state and politely restoring it so we do
    not permanently perturb global RNG state for the caller.

    Not thread-safe: ``np.random.seed`` / ``get_state`` / ``set_state``
    mutate a process-global RNG. Concurrent calls from other threads (or
    other libraries reaching into the same legacy global) can interleave
    with this seeding. This example does not expose a concurrency API and
    is not intended to run in parallel. When PySINDy adds a
    ``Generator``-based seed API, this workaround retires.
    """
    _saved_state = np.random.get_state()  # noqa: NPY002 — PySINDy uses legacy RNG
    try:
        np.random.seed(seed)  # noqa: NPY002 — PySINDy uses legacy RNG
        yield
    finally:
        np.random.set_state(_saved_state)  # noqa: NPY002 — PySINDy uses legacy RNG


def _build_caller_configured_sindy() -> Any:
    try:
        import pysindy
    except ImportError as exc:  # pragma: no cover — surfaced via test 14
        raise ImportError(
            "pdelie.examples.downstream_discovery_task_bridge requires the "
            "[downstream] optional-dependency extra. Reinstall with "
            "`pip install pdelie[downstream]`."
        ) from exc

    optimizer = pysindy.STLSQ(threshold=0.1, alpha=0.05, max_iter=20)
    feature_library = pysindy.PolynomialLibrary(
        degree=_POLYNOMIAL_DEGREE, include_bias=True
    )
    differentiation_method = pysindy.FiniteDifference()
    return pysindy.SINDy(
        optimizer=optimizer,
        feature_library=feature_library,
        differentiation_method=differentiation_method,
    )


def run_downstream_discovery_task_bridge_example() -> dict[str, Any]:
    """Run both v0.31 downstream task paths on one canonical field.

    Returns
    -------
    A strict-JSON-compatible dict with:

    - ``summary_schema_version``
    - ``summary_type = "downstream_discovery_task_bridge_example"``
    - ``pde_library_task`` — the v0.31b1 ``discovery_task_result`` verbatim
    - ``weak_pde_library_diagnostic`` — the v0.31b2
      ``pdelie_weak_pde_library_diagnostic`` verbatim
    - ``interpretation`` — narrative field enumerating what the example does
      and does not claim
    - ``scope_boundaries`` — machine-readable non-claim flags
    - ``backend_versions`` — resolved installed versions
    """
    field = generate_heat_1d_field_batch(
        batch_size=_BATCH_SIZE,
        num_times=_NUM_TIMES,
        num_points=_NUM_POINTS,
        seed=_SEED,
    )

    sindy_model = _build_caller_configured_sindy()

    with _legacy_numpy_rng_seed_scope(_SEED):
        pde_library_task = run_pysindy_pde_task(
            field,
            task_name=_TASK_NAME,
            pysindy_model=sindy_model,
        )
        weak_diagnostic = inspect_pysindy_weak_pde_library(
            field,
            task_name=_WEAK_TASK_NAME,
            library_configuration=WeakPDELibraryDiagnostic(
                polynomial_degree=_POLYNOMIAL_DEGREE,
                derivative_order=_DERIVATIVE_ORDER,
                num_domain_centers_K=_WEAK_K,
            ),
        )

    payload: dict[str, Any] = {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": _SUMMARY_TYPE,
        "pde_library_task": pde_library_task,
        "weak_pde_library_diagnostic": weak_diagnostic,
        "interpretation": dict(_INTERPRETATION),
        "scope_boundaries": dict(_SCOPE_BOUNDARIES),
        "backend_versions": _resolve_backend_versions(),
    }

    # Strict-JSON boundary — json.dumps(..., allow_nan=False) rejects NaN/Inf.
    json.dumps(payload, allow_nan=False)
    return payload


def main() -> None:
    print(json.dumps(run_downstream_discovery_task_bridge_example(), indent=2))


if __name__ == "__main__":
    main()
