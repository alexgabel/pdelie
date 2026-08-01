"""v0.37d: routing a discovery task through a declared action bundle.

Submodule-only. Nothing here is exported from :mod:`pdelie`.
"""

from __future__ import annotations

from pdelie.downstream.action_bundle_bridge import (
    AUGMENTED_TASK_SUMMARY_TYPE,
    BLOCK_STATUSES,
    BRANCHES,
    BUNDLE_RELATION_STATUSES,
    augmented_key_count,
    classify_branch,
    run_downstream_with_action_bundle,
)

__all__ = [
    "AUGMENTED_TASK_SUMMARY_TYPE",
    "BLOCK_STATUSES",
    "BRANCHES",
    "BUNDLE_RELATION_STATUSES",
    "augmented_key_count",
    "classify_branch",
    "run_downstream_with_action_bundle",
]
