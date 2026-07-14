"""v0.31 submodule-only task-bridge surface.

v0.31b1 introduced the ``pdelie.tasks.discovery`` runtime — the
``run_pysindy_pde_task`` runner, the strict-JSON payload assembler
``summarize_discovery_task_result``, and the runtime BC-guard exception
``PySINDyDiscoveryUnsupportedBoundaryError``.

v0.31b2 adds the diagnostic wrapper in ``pdelie.tasks.weak_pde_library``:
``inspect_pysindy_weak_pde_library`` (the diagnostic runner),
``summarize_pysindy_weak_pde_library_diagnostic`` (the strict-JSON payload
assembler), and the ``WeakPDELibraryDiagnostic`` library-configuration
dataclass. The wrapper is deliberately diagnostic-only; it does not
constitute a WSINDy benchmark, a validated weak sparse recovery claim, or
any noise-robustness certification.

No root ``pdelie`` re-export is added — v0.31 keeps this surface
submodule-only per the frozen scope in
``docs/planning/V0_31_DISCOVERY_TASK_BRIDGE_SCOPE.md``.
"""

from pdelie.tasks.discovery import (
    PySINDyDiscoveryUnsupportedBoundaryError,
    run_pysindy_pde_task,
    summarize_discovery_task_result,
)
from pdelie.tasks.weak_pde_library import (
    WeakPDELibraryDiagnostic,
    inspect_pysindy_weak_pde_library,
    summarize_pysindy_weak_pde_library_diagnostic,
)

__all__ = [
    "PySINDyDiscoveryUnsupportedBoundaryError",
    "WeakPDELibraryDiagnostic",
    "inspect_pysindy_weak_pde_library",
    "run_pysindy_pde_task",
    "summarize_discovery_task_result",
    "summarize_pysindy_weak_pde_library_diagnostic",
]
