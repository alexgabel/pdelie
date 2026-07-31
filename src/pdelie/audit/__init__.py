"""v0.36a-alpha: pipeline migration audit.

**Experimental.** This package compares a legacy pipeline run against a modern
one, stage by stage, and reports whether each paper-critical result survived the
migration. It is a diagnostic over two recorded runs; it does not run either
pipeline itself and makes no claim about results it was not given.

The audit exists because "we ported it and the numbers look fine" is not
evidence. Every stage carries a comparison class, every comparison produces one
label from a frozen seven-value vocabulary, and the three labels that mean "this
difference is expected" require a human justification -- with a linked release
note for an intentional contract change.

Submodule-only: nothing here is exported from the root ``pdelie`` namespace.
"""

from __future__ import annotations

from pdelie.audit.comparators import (
    COMPARATOR_ASSIGNABLE_LABELS,
    MIGRATION_LABELS,
    PRINCIPAL_ANGLE_RESOLUTION_FLOOR_RAD,
    QUALITATIVE_INVARIANTS,
    ComparisonResult,
    compare_exact,
    compare_numeric,
    compare_qualitative,
    compare_selected_rows_by_objective,
    compare_subspaces,
    principal_angles,
    summarize_labels,
)
from pdelie.audit.pipeline_migration import (
    PIPELINE_MIGRATION_SUMMARY_TYPE,
    PipelineMigrationComparisonPolicy,
    StagePolicy,
    compare_pipeline_stages,
)
from pdelie.audit.stage_bundle import (
    COMPARISON_CLASSES,
    STAGE_BUNDLE_SCHEMA_VERSION,
    StageBundle,
    read_stage_bundle,
    write_stage_bundle,
)

__all__ = [
    "COMPARATOR_ASSIGNABLE_LABELS",
    "COMPARISON_CLASSES",
    "MIGRATION_LABELS",
    "PIPELINE_MIGRATION_SUMMARY_TYPE",
    "PRINCIPAL_ANGLE_RESOLUTION_FLOOR_RAD",
    "QUALITATIVE_INVARIANTS",
    "STAGE_BUNDLE_SCHEMA_VERSION",
    "ComparisonResult",
    "PipelineMigrationComparisonPolicy",
    "StageBundle",
    "StagePolicy",
    "compare_exact",
    "compare_numeric",
    "compare_pipeline_stages",
    "compare_qualitative",
    "compare_selected_rows_by_objective",
    "compare_subspaces",
    "principal_angles",
    "read_stage_bundle",
    "summarize_labels",
    "write_stage_bundle",
]
