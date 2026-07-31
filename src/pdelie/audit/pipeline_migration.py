"""v0.36a-alpha: the public entry point for the paper-critical migration audit.

Compares a legacy stage-bundle tree against a modern one and emits
``summary_type = "pdelie_pipeline_migration_report"``.

Division of authority
=====================

:mod:`pdelie.audit.comparators` decides only what array evidence supports:
preserved, within tolerance, invariant-preserved, or unexplained. The three
labels that require a human judgement --
``intentional_contract_change``, ``platform_specific_difference``,
``blocked_missing_legacy_dependency`` -- are supplied by the
:class:`PipelineMigrationComparisonPolicy` and must carry a justification. An
``intentional_contract_change`` additionally requires a linked release note,
because "we meant to do that" without a citation is indistinguishable from
"we noticed it afterwards".
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pdelie.artifact import semantic_hash
from pdelie.audit.comparators import (
    MIGRATION_LABELS,
    compare_exact,
    compare_numeric,
    compare_qualitative,
)
from pdelie.audit.stage_bundle import read_stage_bundle
from pdelie.errors import ScopeValidationError

__all__ = [
    "PIPELINE_MIGRATION_SUMMARY_TYPE",
    "PipelineMigrationComparisonPolicy",
    "StagePolicy",
    "compare_pipeline_stages",
]

PIPELINE_MIGRATION_SUMMARY_TYPE = "pdelie_pipeline_migration_report"

#: Labels a policy may assign, each requiring a justification.
_POLICY_ASSIGNABLE_LABELS = (
    "intentional_contract_change",
    "platform_specific_difference",
    "blocked_missing_legacy_dependency",
)


@dataclass(frozen=True)
class StagePolicy:
    """Per-stage comparison settings.

    ``rtol``/``atol`` are required for a ``tolerance_numeric`` stage and must not
    be defaulted -- a tolerance chosen without measurement is precisely the thing
    the freeze process forbids.
    """

    stage_id: str
    rtol: float | None = None
    atol: float | None = None
    invariant: str | None = None
    override_label: str | None = None
    justification: str | None = None
    release_note: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.stage_id, str) or not self.stage_id.strip():
            raise ScopeValidationError("StagePolicy.stage_id must be a non-empty string.")
        if self.override_label is not None:
            if self.override_label not in _POLICY_ASSIGNABLE_LABELS:
                raise ScopeValidationError(
                    f"override_label must be one of {list(_POLICY_ASSIGNABLE_LABELS)}; "
                    f"got {self.override_label!r}. A comparator outcome cannot be "
                    f"overridden into a preserved label."
                )
            if not (self.justification or "").strip():
                raise ScopeValidationError(
                    f"override_label {self.override_label!r} on stage "
                    f"{self.stage_id!r} requires a justification."
                )
            if self.override_label == "intentional_contract_change" and not (
                self.release_note or ""
            ).strip():
                raise ScopeValidationError(
                    f"intentional_contract_change on stage {self.stage_id!r} requires "
                    f"a linked release note; an undocumented intentional change is "
                    f"indistinguishable from an unnoticed one."
                )


@dataclass(frozen=True)
class PipelineMigrationComparisonPolicy:
    """The whole comparison policy: per-stage settings plus a run label."""

    policy_id: str
    stage_policies: Mapping[str, StagePolicy] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.policy_id, str) or not self.policy_id.strip():
            raise ScopeValidationError("policy_id must be a non-empty string.")
        for stage_id, policy in self.stage_policies.items():
            if policy.stage_id != stage_id:
                raise ScopeValidationError(
                    f"stage_policies key {stage_id!r} does not match "
                    f"StagePolicy.stage_id {policy.stage_id!r}."
                )

    def for_stage(self, stage_id: str) -> StagePolicy:
        return self.stage_policies.get(stage_id, StagePolicy(stage_id=stage_id))


def _compare_one_stage(
    legacy_bundle: Any, modern_bundle: Any, policy: StagePolicy
) -> tuple[str, dict[str, Any]]:
    """Compare one stage's arrays; returns (label, detail)."""
    if legacy_bundle.comparison_class != modern_bundle.comparison_class:
        raise ScopeValidationError(
            f"stage {legacy_bundle.stage_id!r} declares comparison_class "
            f"{legacy_bundle.comparison_class!r} on the legacy side and "
            f"{modern_bundle.comparison_class!r} on the modern side. The class is a "
            f"property of the stage; the two sides must agree before comparing."
        )
    comparison_class = legacy_bundle.comparison_class

    legacy_names = set(legacy_bundle.arrays)
    modern_names = set(modern_bundle.arrays)
    if legacy_names != modern_names:
        return "unexplained_regression", {
            "reason": "array_name_set_differs",
            "only_in_legacy": sorted(legacy_names - modern_names),
            "only_in_modern": sorted(modern_names - legacy_names),
        }

    per_array: dict[str, Any] = {}
    labels: list[str] = []
    for name in sorted(legacy_names):
        left = legacy_bundle.arrays[name]
        right = modern_bundle.arrays[name]
        if comparison_class == "exact_discrete":
            result = compare_exact(left, right)
        elif comparison_class == "tolerance_numeric":
            if policy.rtol is None or policy.atol is None:
                raise ScopeValidationError(
                    f"stage {policy.stage_id!r} is tolerance_numeric but its policy "
                    f"supplies rtol={policy.rtol!r}, atol={policy.atol!r}. Both are "
                    f"required and are set by the pilot, never defaulted."
                )
            result = compare_numeric(left, right, rtol=policy.rtol, atol=policy.atol)
        elif comparison_class == "qualitative_invariant":
            if not policy.invariant:
                raise ScopeValidationError(
                    f"stage {policy.stage_id!r} is qualitative_invariant but its "
                    f"policy names no invariant."
                )
            result = compare_qualitative(left, right, invariant=policy.invariant)
        else:  # platform_specific_diagnostic
            per_array[name] = {
                "label": "platform_specific_difference",
                "comparison_class": comparison_class,
                "note": "platform_specific_diagnostic stages are reported, never asserted",
            }
            labels.append("platform_specific_difference")
            continue
        per_array[name] = result.as_dict()
        labels.append(result.label)

    # The stage takes the worst label among its arrays.
    severity = {label: index for index, label in enumerate(MIGRATION_LABELS)}
    stage_label = max(labels, key=lambda label: severity[label]) if labels else "unexplained_regression"
    return stage_label, {"arrays": per_array}


def compare_pipeline_stages(
    *,
    legacy_bundle_dir: Path,
    modern_bundle_dir: Path,
    experiment_config: Mapping[str, Any],
    comparison_policy: PipelineMigrationComparisonPolicy,
) -> dict[str, Any]:
    """Compare every stage named in ``experiment_config`` and emit the report."""
    legacy_root = Path(legacy_bundle_dir)
    modern_root = Path(modern_bundle_dir)
    for label, root in (("legacy_bundle_dir", legacy_root), ("modern_bundle_dir", modern_root)):
        if not root.is_dir():
            raise ScopeValidationError(f"{label} {root} is not a directory.")

    stages = experiment_config.get("stages")
    if not isinstance(stages, Sequence) or not stages:
        raise ScopeValidationError(
            "experiment_config must carry a non-empty 'stages' sequence."
        )

    stage_reports: list[dict[str, Any]] = []
    label_counts = dict.fromkeys(MIGRATION_LABELS, 0)

    for entry in stages:
        stage_id = entry["stage_id"]
        policy = comparison_policy.for_stage(stage_id)
        legacy_present = (legacy_root / stage_id / "stage.json").is_file()
        modern_present = (modern_root / stage_id / "stage.json").is_file()

        if not legacy_present:
            label = "blocked_missing_legacy_dependency"
            detail: dict[str, Any] = {
                "reason": "legacy bundle absent",
                "justification": policy.justification,
            }
        elif not modern_present:
            label = "unexplained_regression"
            detail = {"reason": "modern bundle absent"}
        else:
            legacy_bundle = read_stage_bundle(legacy_root, stage_id)
            modern_bundle = read_stage_bundle(modern_root, stage_id)
            label, detail = _compare_one_stage(legacy_bundle, modern_bundle, policy)
            detail["legacy_provenance"] = dict(legacy_bundle.provenance)
            detail["modern_provenance"] = dict(modern_bundle.provenance)

            # A policy override may only be applied to a comparator FAILURE, and
            # only with a justification. It can explain a difference; it cannot
            # manufacture agreement.
            if policy.override_label and label == "unexplained_regression":
                detail["overridden_from"] = label
                detail["justification"] = policy.justification
                detail["release_note"] = policy.release_note
                label = policy.override_label

        label_counts[label] += 1
        stage_reports.append(
            {
                "stage_id": stage_id,
                "declared_comparison_class": entry.get("comparison_class"),
                "label": label,
                "detail": detail,
            }
        )

    unexplained = [
        report["stage_id"] for report in stage_reports if report["label"] == "unexplained_regression"
    ]
    report = {
        "summary_type": PIPELINE_MIGRATION_SUMMARY_TYPE,
        "schema_version": "0.1",
        "experiment_id": experiment_config.get("experiment_id", "unspecified"),
        "policy_id": comparison_policy.policy_id,
        "stage_count": len(stage_reports),
        "label_counts": label_counts,
        "unexplained_regression_stage_ids": unexplained,
        "all_stages_explained": not unexplained,
        "stages": stage_reports,
        "migration_label_vocabulary": list(MIGRATION_LABELS),
        "diagnostic_only": True,
    }
    report["report_semantic_hash"] = semantic_hash(
        {
            "experiment_id": report["experiment_id"],
            "policy_id": report["policy_id"],
            "stages": [
                {"stage_id": item["stage_id"], "label": item["label"]}
                for item in stage_reports
            ],
        }
    )
    # Fail loudly here rather than at the caller's json.dumps.
    json.dumps(report, allow_nan=False)
    return report
