"""v0.31b1 submodule-only discovery task-bridge surface.

Exports the ``run_pysindy_pde_task`` runtime, the strict-JSON payload
assembler ``summarize_discovery_task_result``, and the runtime BC-guard
exception ``PySINDyDiscoveryUnsupportedBoundaryError``. No root ``pdelie``
re-export is added — v0.31 keeps this surface submodule-only per the frozen
scope in ``docs/planning/V0_31_DISCOVERY_TASK_BRIDGE_SCOPE.md``.
"""

from pdelie.tasks.discovery import (
    PySINDyDiscoveryUnsupportedBoundaryError,
    run_pysindy_pde_task,
    summarize_discovery_task_result,
)

__all__ = [
    "PySINDyDiscoveryUnsupportedBoundaryError",
    "run_pysindy_pde_task",
    "summarize_discovery_task_result",
]
