"""v0.36c: compare design candidates on equal terms, or say why you cannot.

``attainability_report`` puts a set of candidates side by side against a
reference and reports paired per-seed deltas. Two things it will not do:

**It will not compare two designs built under different budgets and call the
difference a result.** Thirty rows drawn with duplicates retained and thirty
drawn after deduplication are not the same allowance, and a delta between them
measures the budget as much as the method. Such pairs go to
``budget_incomparable_pairs`` with the mismatch named. The delta is still
reported -- suppressing it would hide information -- but flagged
``budget_fair=False`` so nobody quotes it as a like-for-like win.

**It will not call anything an "oracle" without qualification.** Four
situations get four names, per
:data:`~pdelie.design.candidate_record.METHOD_CLASSES`. A method that
exhaustively searches a small space is exact, not privileged; a method that
reads the true support is privileged in a way no practitioner can reproduce.
Collapsing those into one word turns a measurement into a verdict.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from pdelie.artifact.refs import ArtifactRef
from pdelie.design.budget import DesignBudget
from pdelie.design.candidate_record import DesignCandidateRecord
from pdelie.design.statistics import paired_bootstrap_interval
from pdelie.errors import ScopeValidationError

__all__ = [
    "ATTAINABILITY_SUMMARY_TYPE",
    "attainability_report",
    "budgets_are_equal",
]

ATTAINABILITY_SUMMARY_TYPE = "pdelie_attainable_design_comparison"

#: Every field of a budget that must match for two designs to be comparable.
#: All of them: a budget differing in any one of these is a different allowance.
_BUDGET_FIELDS: tuple[str, ...] = (
    "budget_value",
    "budget_unit",
    "num_views",
    "allocation_policy",
    "grouping_policy",
    "duplicate_policy",
    "row_weight_policy",
    "train_only",
)


def budgets_are_equal(first: DesignBudget, second: DesignBudget) -> tuple[bool, list[str]]:
    """Whether two budgets are the same allowance, and which fields differ."""
    if not isinstance(first, DesignBudget) or not isinstance(second, DesignBudget):
        raise ScopeValidationError("both arguments must be DesignBudget instances.")
    differing = [
        name
        for name in _BUDGET_FIELDS
        if getattr(first, name) != getattr(second, name)
    ]
    return (not differing), differing


def _validated_candidates(candidates: object) -> list[DesignCandidateRecord]:
    if isinstance(candidates, (str, bytes)) or not isinstance(candidates, Sequence):
        raise ScopeValidationError("candidates must be a sequence.")
    if not candidates:
        raise ScopeValidationError("candidates must be non-empty.")
    records: list[DesignCandidateRecord] = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, DesignCandidateRecord):
            raise ScopeValidationError(
                f"candidates[{index}] is {type(candidate).__name__}, not a "
                f"DesignCandidateRecord."
            )
        records.append(candidate)
    identifiers = [record.design_id for record in records]
    duplicates = {value for value in identifiers if identifiers.count(value) > 1}
    if duplicates:
        raise ScopeValidationError(
            f"candidates repeat design_id values: {sorted(duplicates)}."
        )
    return records


def attainability_report(
    candidates: Sequence[DesignCandidateRecord],
    *,
    reference_design_id: str,
    downstream_metrics: Mapping[str, Sequence[float | None] | None],
    seed_ids: Sequence[str],
    n_resamples: int = 2000,
    interval_level: float = 0.95,
    bootstrap_seed: int = 20360,
    sparse_recovery_report_artifact: ArtifactRef | None = None,
) -> dict[str, Any]:
    """Compare every candidate against the reference, paired by seed.

    ``downstream_metrics`` maps ``design_id`` to per-seed values positional
    against ``seed_ids``. A failed run is ``None`` in that sequence, and a design
    that never ran is ``None`` instead of a sequence -- the two are different and
    are counted separately.
    """
    records = _validated_candidates(candidates)
    by_id = {record.design_id: record for record in records}

    if reference_design_id not in by_id:
        raise ScopeValidationError(
            f"reference_design_id {reference_design_id!r} is not among the "
            f"candidates: {sorted(by_id)}."
        )
    if isinstance(seed_ids, (str, bytes)) or not isinstance(seed_ids, Sequence):
        raise ScopeValidationError("seed_ids must be a sequence.")
    identifiers = [str(value) for value in seed_ids]
    if not identifiers:
        raise ScopeValidationError("seed_ids must be non-empty.")
    if not isinstance(downstream_metrics, Mapping):
        raise ScopeValidationError("downstream_metrics must be a mapping.")
    missing = sorted(set(by_id) - set(downstream_metrics))
    if missing:
        raise ScopeValidationError(
            f"downstream_metrics has no entry for {missing}. A design with no "
            f"metric entry is ambiguous: pass None to say it never ran."
        )
    if sparse_recovery_report_artifact is not None and not isinstance(
        sparse_recovery_report_artifact, ArtifactRef
    ):
        raise ScopeValidationError(
            "sparse_recovery_report_artifact must be an ArtifactRef or None."
        )

    reference = by_id[reference_design_id]
    reference_metrics = downstream_metrics[reference_design_id]

    never_ran = sorted(
        design_id for design_id, values in downstream_metrics.items() if values is None
    )
    failed_run_count = sum(
        1
        for values in downstream_metrics.values()
        if values is not None
        for value in values
        if value is None
    )

    paired_deltas: list[dict[str, Any]] = []
    incomparable: list[dict[str, Any]] = []

    for record in records:
        if record.design_id == reference_design_id:
            continue
        equal, differing = budgets_are_equal(record.budget, reference.budget)
        candidate_metrics = downstream_metrics[record.design_id]

        if candidate_metrics is None or reference_metrics is None:
            interval: dict[str, Any] = {
                "interval_available": False,
                "reason": "one or both designs never ran",
                "seed_ids_a": identifiers,
                "seed_ids_b": identifiers,
            }
        else:
            interval = paired_bootstrap_interval(
                candidate_metrics,
                reference_metrics,
                seed_ids=identifiers,
                n_resamples=n_resamples,
                interval_level=interval_level,
                resampling_unit="seed",
                seed=bootstrap_seed,
            )

        entry = {
            "design_id": record.design_id,
            "reference_design_id": reference_design_id,
            "method_class": record.method_class,
            "uses_privileged_information": record.uses_privileged_information,
            "budget_fair": equal,
            "seed_ids_a": interval["seed_ids_a"],
            "seed_ids_b": interval["seed_ids_b"],
            "interval": interval,
        }
        paired_deltas.append(entry)

        if not equal:
            incomparable.append(
                {
                    "designs": [record.design_id, reference_design_id],
                    "reason": "budget_unit_or_value_or_policy_mismatch",
                    "differing_budget_fields": differing,
                    "delta_still_reported_but_not_budget_fair": True,
                    "mean_difference": interval.get("mean_difference"),
                }
            )

    return {
        "summary_type": ATTAINABILITY_SUMMARY_TYPE,
        "schema_version": "0.1",
        "reference_design_id": reference_design_id,
        "candidate_count": len(records),
        "seed_ids": identifiers,
        "seed_count": len(identifiers),
        "candidates": [record.as_dict() for record in records],
        "paired_deltas": paired_deltas,
        "budget_incomparable_pairs": incomparable,
        "designs_that_never_ran": never_ran,
        "failed_run_count": failed_run_count,
        "privileged_design_ids": sorted(
            record.design_id for record in records if record.uses_privileged_information
        ),
        "sparse_recovery_report_artifact_id": (
            None
            if sparse_recovery_report_artifact is None
            else sparse_recovery_report_artifact.artifact_id
        ),
        "resampling_unit": "seed",
        "diagnostic_only": True,
    }
