"""v0.36a-beta: which (PDE x boundary x path) combinations are actually auditable.

A migration audit can only compare what both versions can produce. This module
enumerates the combinations the v0.36 plan named for beta and records, for each,
whether the legacy side can produce it at all -- so the scope is a measured fact
rather than an aspiration, and an unaudited combination is visibly unaudited.

What was measured against ``v0.22.0``
=====================================

**All five PDE generators exist.** ``heat``, ``burgers``,
``advection_diffusion``, ``reaction_diffusion``, and ``kdv`` are all present, so
the PDE axis widens from alpha's one to beta's five.

**No generator accepts a boundary condition.** Not one of the five takes a
``boundary_condition_x`` parameter, and ``pdelie._boundary`` does not exist in
v0.22.0 -- boundary-condition dispatch arrived in v0.30d and the nonperiodic
generator layer in v0.33. Nonperiodic *data* can still be manufactured on both
sides by cropping a periodic field, but the legacy side has no boundary-aware
*processing* to compare against, so a nonperiodic stage would compare a modern
boundary-aware pipeline to a legacy one that does not know boundaries exist.
That is not a like-for-like comparison, and the axis is blocked rather than
faked.

**The weak-form path does not exist.** ``pdelie.tasks`` is absent in v0.22.0, so
both the 27-key default and the 28-key normalized weak diagnostics are
modern-only.

**The PySINDy path does exist, on both sides.** ``to_pysindy_trajectories`` and
``fit_pysindy_discovery`` are present in v0.22.0 and produce coefficients of the
same shape as the modern versions. **This is the axis beta exists to audit** -- alpha
deliberately routed stages 9-16 around PySINDy so that its numerical baseline
would not be confounded by the PySINDy 1.7.5 to 2.1.x version delta. beta audits it
against that baseline; see the beta preconditions in
``docs/planning/V0_36A_ALPHA_TO_BETA_RUNBOOK.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from pdelie.errors import ScopeValidationError

__all__ = [
    "AUDITABILITY",
    "BETA_PDE_NAMES",
    "BOUNDARY_CONDITIONS",
    "PIPELINE_PATHS",
    "ScopeEntry",
    "enumerate_scope",
    "summarize_scope",
]

Auditability = Literal["auditable", "blocked_missing_legacy_dependency"]

#: The five 1-D PDEs. All five generators exist in v0.22.0.
BETA_PDE_NAMES: tuple[str, ...] = (
    "heat_1d",
    "burgers_1d",
    "advection_diffusion_1d",
    "reaction_diffusion_1d",
    "kdv_1d",
)

#: Boundary conditions the modern layer supports. Only ``periodic`` has a legacy
#: counterpart.
BOUNDARY_CONDITIONS: tuple[str, ...] = (
    "periodic",
    "dirichlet",
    "neumann",
    "open_unknown",
)

#: Pipeline paths a stage set can route through.
PIPELINE_PATHS: tuple[str, ...] = (
    "derivative_batch",
    "pysindy_discovery",
    "weak_default",
    "weak_normalized",
    "row_selection_diagnostics",
)

AUDITABILITY: tuple[str, ...] = ("auditable", "blocked_missing_legacy_dependency")

#: Why each blocked axis is blocked, and the release that introduced it.
_BLOCK_REASONS: dict[str, tuple[str, str]] = {
    "nonperiodic_boundary": (
        (
            "v0.22.0 has no pdelie._boundary module and no generator accepts "
            "boundary_condition_x. Boundary-condition dispatch arrived in v0.30d "
            "and the nonperiodic generator layer in v0.33. Nonperiodic data can "
            "be manufactured on both sides by cropping, but the legacy side has "
            "no boundary-aware processing to compare against."
        ),
        "docs/releases/V0_33_RELEASE_READINESS.md",
    ),
    "weak_default": (
        (
            "pdelie.tasks does not exist in v0.22.0; the weak-form diagnostic "
            "arrived in v0.31b2."
        ),
        "docs/releases/V0_33_RELEASE_READINESS.md",
    ),
    "weak_normalized": (
        (
            "Column normalization of the weak-form design matrix arrived in "
            "v0.34c and has no v0.22.0 counterpart."
        ),
        "docs/releases/V0_34_RELEASE_READINESS.md",
    ),
    "row_selection_diagnostics": (
        (
            "Row-selection diagnostics arrived in v0.35c and have no v0.22.0 "
            "counterpart."
        ),
        "docs/releases/V0_35_RELEASE_READINESS.md",
    ),
    "kdv_nonperiodic": (
        (
            "Nonperiodic KdV has been explicitly deferred since v0.30 and "
            "remains out of scope; it is not a migration finding."
        ),
        "docs/planning/ROADMAP.md",
    ),
}


@dataclass(frozen=True)
class ScopeEntry:
    """One (PDE, boundary, path) combination and whether beta can audit it."""

    pde_name: str
    boundary_condition: str
    pipeline_path: str
    auditability: str
    reason: str | None = None
    release_note: str | None = None

    def __post_init__(self) -> None:
        if self.pde_name not in BETA_PDE_NAMES:
            raise ScopeValidationError(
                f"pde_name {self.pde_name!r} is not one of {list(BETA_PDE_NAMES)}."
            )
        if self.boundary_condition not in BOUNDARY_CONDITIONS:
            raise ScopeValidationError(
                f"boundary_condition {self.boundary_condition!r} is not one of "
                f"{list(BOUNDARY_CONDITIONS)}."
            )
        if self.pipeline_path not in PIPELINE_PATHS:
            raise ScopeValidationError(
                f"pipeline_path {self.pipeline_path!r} is not one of "
                f"{list(PIPELINE_PATHS)}."
            )
        if self.auditability not in AUDITABILITY:
            raise ScopeValidationError(
                f"auditability {self.auditability!r} is not one of {list(AUDITABILITY)}."
            )
        if self.auditability != "auditable" and not (self.reason or "").strip():
            raise ScopeValidationError(
                f"{self.pde_name}/{self.boundary_condition}/{self.pipeline_path} is "
                f"blocked but carries no reason. An unaudited combination must say "
                f"why, or its absence is unjustified rather than justified."
            )

    @property
    def is_auditable(self) -> bool:
        return self.auditability == "auditable"

    def as_dict(self) -> dict[str, Any]:
        return {
            "pde_name": self.pde_name,
            "boundary_condition": self.boundary_condition,
            "pipeline_path": self.pipeline_path,
            "auditability": self.auditability,
            "reason": self.reason,
            "release_note": self.release_note,
        }


def _classify(pde: str, boundary: str, path: str) -> tuple[str, str | None, str | None]:
    if boundary != "periodic":
        if pde == "kdv_1d":
            reason, note = _BLOCK_REASONS["kdv_nonperiodic"]
            return "blocked_missing_legacy_dependency", reason, note
        reason, note = _BLOCK_REASONS["nonperiodic_boundary"]
        return "blocked_missing_legacy_dependency", reason, note
    if path in ("weak_default", "weak_normalized", "row_selection_diagnostics"):
        reason, note = _BLOCK_REASONS[path]
        return "blocked_missing_legacy_dependency", reason, note
    return "auditable", None, None


def enumerate_scope() -> tuple[ScopeEntry, ...]:
    """Every combination the beta plan names, classified by measured availability."""
    return tuple(
        ScopeEntry(
            pde_name=pde,
            boundary_condition=boundary,
            pipeline_path=path,
            auditability=auditability,
            reason=reason,
            release_note=note,
        )
        for pde in BETA_PDE_NAMES
        for boundary in BOUNDARY_CONDITIONS
        for path in PIPELINE_PATHS
        for auditability, reason, note in (_classify(pde, boundary, path),)
    )


def summarize_scope() -> dict[str, Any]:
    """The scope as a strict-JSON report."""
    entries = enumerate_scope()
    auditable = [entry for entry in entries if entry.is_auditable]
    blocked = [entry for entry in entries if not entry.is_auditable]

    by_path: dict[str, int] = {}
    for entry in auditable:
        by_path[entry.pipeline_path] = by_path.get(entry.pipeline_path, 0) + 1

    return {
        "summary_type": "pdelie_full_migration_scope",
        "schema_version": "0.1",
        "combination_count": len(entries),
        "auditable_count": len(auditable),
        "blocked_count": len(blocked),
        "auditable_by_pipeline_path": by_path,
        "pde_names": list(BETA_PDE_NAMES),
        "boundary_conditions": list(BOUNDARY_CONDITIONS),
        "pipeline_paths": list(PIPELINE_PATHS),
        # The obligation alpha's scope decision created. Recorded in the report
        # so it is visible to anyone reading a beta result, not only to someone
        # who read the runbook.
        "pysindy_path_is_a_beta_obligation": True,
        "pysindy_path_rationale": (
            "alpha deliberately routed stages 9-16 around PySINDy so its "
            "numerical baseline would not be confounded by the PySINDy 1.7.5 to "
            "2.1.x version delta. beta MUST audit that path; beta close is "
            "blocked without it. Any delta found there, given alpha's clean "
            "close, is attributable to the PySINDy version delta rather than to "
            "migration numerical drift."
        ),
        "entries": [entry.as_dict() for entry in entries],
        "diagnostic_only": True,
    }
