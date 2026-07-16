"""v0.32c candidate-to-discovery workflow example (JSON-only, submodule-only).

Demonstrates the core PDELie chain using ONLY public submodule APIs::

    FieldBatch
      -> run_symmetry_method("polynomial_translation_svd")
      -> SymmetryCandidate
      -> validate_symmetry_candidate
      -> verify_translation_generator
      -> caller-configured periodic translation orbit (train-only)
      -> run_pysindy_pde_task (baseline)
      -> run_pysindy_pde_task (candidate-guided)
      -> summarize_candidate_to_discovery_workflow

Two deterministic scenarios are offered:

- ``"successful"``: runs every stage end-to-end on a single periodic scalar
  1D heat FieldBatch. Reports the measured downstream comparison honestly;
  the evidence-conclusion label is chosen from the measured absolute delta
  against a fixed threshold. NO universal-improvement claim is made.
- ``"valid_but_not_useful_static"``: executes every real stage
  (field-readiness through split/leakage provenance) using the same real
  fixtures, but the ``baseline_discovery_task`` / ``candidate_guided_discovery_task``
  / ``downstream_comparison`` / ``evidence_conclusion`` blocks are replaced
  with a provenance-backed static illustration. ``extra_metrics.static_illustration``
  is set to ``True``. This exists so that a deterministic
  valid-but-not-useful outcome can be demonstrated without pretending
  static numbers were runtime-measured.

Scope-boundaries encoded in the emitted payload record that the workflow
example does NOT claim generic symmetry discovery, universal downstream
benefit, noise robustness, nonperiodic support, multi-D support, external
data support, or automatic best-candidate selection.

This module has no root ``pdelie`` re-export.
"""

from __future__ import annotations

import importlib.metadata as _importlib_metadata
import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any, Literal

import numpy as np

from pdelie._boundary import is_x_periodic
from pdelie.contracts import FieldBatch, GeneratorFamily
from pdelie.data import generate_heat_1d_field_batch
from pdelie.derivatives import compute_derivatives
from pdelie.errors import SchemaValidationError
from pdelie.invariants import (
    OrbitBatchResult,
    build_uniform_translation_orbit_batch,
)
from pdelie.reporting import (
    enrich_method_scores,
    summarize_candidate_to_discovery_workflow,
    summarize_field_batch_readiness,
    summarize_generator_confidence,
    summarize_residual_batch,
    summarize_split_leakage_provenance,
    summarize_verification_report,
)
from pdelie.residuals import HeatResidualEvaluator
from pdelie.symmetry import (
    run_symmetry_method,
    summarize_symmetry_candidate,
    summarize_symmetry_method_result,
    validate_symmetry_candidate,
)
from pdelie.symmetry.methods.polynomial_translation_svd import SCORE_METADATA
from pdelie.tasks import run_pysindy_pde_task
from pdelie.verification import verify_translation_generator

_SUMMARY_TYPE = "candidate_to_discovery_workflow_example"
_SUMMARY_SCHEMA_VERSION = "0.1"

# Frozen configuration — do not tune. The example is deterministic under
# these constants; changes here are a public-surface change and must be
# discussed on the ROADMAP.
_DEFAULT_SEED = 32_300
# The symmetry-method + validation + verification stages run on a training
# batch large enough for held-out finite-transform verification (batch >= 3).
# The discovery stages run on a single-trajectory slice so that every PySINDy
# 2.x fit takes the single-trajectory adapter path — the pdelie task-bridge's
# multi-trajectory PySINDy 2.x adapter path is still being hardened under
# the v0.32a modern-runtime migration (see PR #103) and this example does
# NOT depend on it.
_TRAIN_BATCH_SIZE = 4
_HELDOUT_BATCH_SIZE = 1
_NUM_TIMES = 48
_NUM_POINTS = 64
_POLYNOMIAL_DEGREE = 2
_TASK_NAME_BASELINE = "candidate_to_discovery_workflow_example_baseline"
_TASK_NAME_CANDIDATE_GUIDED = (
    "candidate_to_discovery_workflow_example_candidate_guided"
)
_ABS_DELTA_USEFULNESS_THRESHOLD = 1e-6

_SCENARIO_LITERAL = ("successful", "valid_but_not_useful_static")

# Fixed periodic translation shifts (train-only). The values are caller-
# supplied; they are NOT inferred from method scores. They are recorded
# verbatim on the action_policy stage.
#
# One non-zero shift keeps the candidate-guided discovery run on the single-
# trajectory adapter path (orbit output batch_size = source batch_size x
# shift_count = 1). Extending the shift set to demonstrate multi-trajectory
# orbit-guided discovery is deferred to v0.33 alongside the wider PySINDy 2.x
# multi-trajectory hardening.
_ACTION_POLICY_SHIFTS: tuple[float, ...] = (0.5,)

_SCOPE_BOUNDARIES: dict[str, bool] = {
    "periodic_scalar_1d_only": True,
    "generic_symmetry_discovery_claimed": False,
    "universal_downstream_benefit_claimed": False,
    "noise_robustness_claimed": False,
    "nonperiodic_claimed": False,
    "multi_d_claimed": False,
    "external_data_claimed": False,
    "automatic_best_selection_claimed": False,
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
    """Seed the legacy ``np.random`` state around a PySINDy call.

    PySINDy 2.1.x still reaches for ``np.random.*`` in some code paths;
    seeding the legacy global RNG and restoring it on exit keeps the
    example deterministic without permanently perturbing caller state.
    Not thread-safe; the example does not expose a concurrency API.
    """
    saved = np.random.get_state()  # noqa: NPY002 — PySINDy legacy RNG
    try:
        np.random.seed(seed)  # noqa: NPY002 — PySINDy legacy RNG
        yield
    finally:
        np.random.set_state(saved)  # noqa: NPY002 — PySINDy legacy RNG


def _build_caller_configured_sindy() -> Any:
    try:
        import pysindy
    except ImportError as exc:  # pragma: no cover — surfaced via test
        raise ImportError(
            "pdelie.examples.candidate_to_discovery_workflow requires the "
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


def _slice_first_trajectory(field: FieldBatch) -> FieldBatch:
    """Return a batch_size=1 view of ``field`` (first trajectory only).

    Preserves the periodic-x contract and all metadata; used to feed the
    single-trajectory PySINDy 2.x adapter path from the discovery-task
    stages of the v0.32c workflow example.
    """
    from copy import deepcopy

    if field.values.shape[field.dims.index("batch")] < 1:
        raise SchemaValidationError(
            "cannot slice first trajectory from an empty FieldBatch."
        )
    return FieldBatch(
        schema_version=field.schema_version,
        values=field.values[0:1].copy(),
        dims=field.dims,
        coords={k: v.copy() for k, v in field.coords.items()},
        var_names=list(field.var_names),
        metadata=deepcopy(field.metadata),
        preprocess_log=[dict(entry) for entry in field.preprocess_log],
        mask=None if field.mask is None else field.mask[0:1].copy(),
    )


def _generate_train_and_heldout(
    seed: int,
) -> tuple[FieldBatch, FieldBatch]:
    train = generate_heat_1d_field_batch(
        batch_size=_TRAIN_BATCH_SIZE,
        num_times=_NUM_TIMES,
        num_points=_NUM_POINTS,
        seed=seed,
    )
    heldout = generate_heat_1d_field_batch(
        batch_size=_HELDOUT_BATCH_SIZE,
        num_times=_NUM_TIMES,
        num_points=_NUM_POINTS,
        seed=seed + 1,
    )
    if not (is_x_periodic(train) and is_x_periodic(heldout)):
        raise SchemaValidationError(
            "candidate_to_discovery_workflow_example requires periodic-in-x "
            "training and heldout FieldBatches."
        )
    return train, heldout


def _stage_marker(
    *, stage: str, status: str, reason: str
) -> dict[str, Any]:
    return {
        "summary_type": "candidate_to_discovery_workflow_stage_marker",
        "status": status,
        "reason": reason,
        "stage": stage,
    }


def _measured_downstream_comparison(
    baseline_task: Mapping[str, Any],
    candidate_task: Mapping[str, Any],
) -> dict[str, Any]:
    warnings: list[str] = []
    baseline_value: float | None = _extract_heldout_residual_l2(
        baseline_task, warnings, side="baseline"
    )
    candidate_value: float | None = _extract_heldout_residual_l2(
        candidate_task, warnings, side="candidate_guided"
    )
    absolute_delta: float | None = None
    relative_delta: float | None = None
    if baseline_value is not None and candidate_value is not None:
        absolute_delta = float(candidate_value - baseline_value)
        if abs(baseline_value) > 0:
            relative_delta = float(absolute_delta / baseline_value)
    improved: bool | None = None
    if absolute_delta is not None:
        improved = absolute_delta < -_ABS_DELTA_USEFULNESS_THRESHOLD
    return {
        "metric_key": "heldout_residual_l2_norm",
        "baseline_value": baseline_value,
        "candidate_guided_value": candidate_value,
        "absolute_delta": absolute_delta,
        "relative_delta": relative_delta,
        "improvement_direction": "lower_is_better",
        "improved": improved,
        "warnings": warnings,
    }


def _extract_heldout_residual_l2(
    task: Mapping[str, Any], warnings: list[str], *, side: str
) -> float | None:
    """Read the ``heldout_residual.l2_norm`` field from a discovery_task_result.

    The v0.31b1 ``discovery_task_result`` schema exposes both
    ``train_residual`` and ``heldout_residual`` blocks with ``size``,
    ``l2_norm``, ``rms``, and ``max_abs`` keys. Held-out evaluation is the
    honest downstream metric — the training residual is not a valid
    generalization proxy.
    """
    heldout = task.get("heldout_residual")
    if not isinstance(heldout, Mapping):
        warnings.append(f"{side}_task_missing_heldout_residual_block")
        return None
    raw = heldout.get("l2_norm")
    if raw is None:
        warnings.append(f"{side}_task_missing_heldout_residual_l2_norm")
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        warnings.append(f"{side}_task_heldout_residual_l2_not_a_float")
        return None
    if not np.isfinite(value):
        warnings.append(f"{side}_task_heldout_residual_l2_non_finite")
        return None
    return value


def _label_from_measurement(
    comparison: Mapping[str, Any],
) -> dict[str, Any]:
    """Choose evidence_conclusion label from the measured comparison.

    - ``successful_composition`` when the candidate-guided task's fit
      residual is strictly better than the baseline (by more than the
      absolute threshold).
    - ``valid_but_not_useful`` otherwise — including ties and cases
      where the augmentation does not measurably help. NO
      universal-benefit claim in either case.
    """
    reasons: list[str] = []
    delta = comparison.get("absolute_delta")
    improved = comparison.get("improved")
    if delta is None or improved is None:
        reasons.append(
            "downstream_comparison_incomplete_defaulting_to_valid_but_not_useful"
        )
        label = "valid_but_not_useful"
    elif improved:
        reasons.append(
            "candidate_guided_fit_residual_strictly_below_baseline"
        )
        label = "successful_composition"
    else:
        reasons.append(
            "candidate_guided_fit_residual_did_not_strictly_beat_baseline"
        )
        label = "valid_but_not_useful"
    return {
        "label": label,
        "reasons": reasons,
        "downstream_gain_claimed": False,
    }


def _static_illustration_downstream_comparison() -> dict[str, Any]:
    return {
        "metric_key": "heldout_residual_l2_norm",
        "baseline_value": 1.0e-3,
        "candidate_guided_value": 1.0e-3,
        "absolute_delta": 0.0,
        "relative_delta": 0.0,
        "improvement_direction": "lower_is_better",
        "improved": False,
        "warnings": ["static_illustration_not_runtime_measurement"],
    }


def _static_illustration_evidence_conclusion() -> dict[str, Any]:
    return {
        "label": "valid_but_not_useful",
        "reasons": [
            "static_illustration_of_valid_but_not_useful_wedge",
            "no_downstream_gain_claimed",
        ],
        "downstream_gain_claimed": False,
    }


def run_candidate_to_discovery_workflow_example(
    *,
    scenario: Literal["successful", "valid_but_not_useful_static"] = "successful",
    seed: int | None = None,
) -> dict[str, Any]:
    """Run one of two deterministic candidate-to-discovery workflow scenarios.

    Returns a strict-JSON-compatible ``candidate_to_discovery_workflow``
    payload wrapped in a top-level ``candidate_to_discovery_workflow_example``
    envelope carrying backend versions and provenance.
    """
    if scenario not in _SCENARIO_LITERAL:
        raise SchemaValidationError(
            f"scenario must be one of {list(_SCENARIO_LITERAL)}; got "
            f"{scenario!r}."
        )
    effective_seed = _DEFAULT_SEED if seed is None else int(seed)
    train, heldout = _generate_train_and_heldout(effective_seed)
    residual_evaluator = HeatResidualEvaluator()

    # Stage 1 — field_readiness (train side; heldout provenance recorded via
    # the split_leakage stage and the action_policy.train_test_policy field).
    field_readiness = summarize_field_batch_readiness(train)

    # Stage 2 — derivative_residual_evidence: a residual_batch report is the
    # narrowest existing summary that fits derivative + residual context.
    derivatives = compute_derivatives(train, backend="spectral_fd")
    residual = residual_evaluator.evaluate(train)
    derivative_residual_evidence = summarize_residual_batch(residual)
    # Attach the derivative backend as an extra_metric on the vertical-slice
    # style provenance without changing the residual_batch schema.
    _ = derivatives  # kept for provenance; used by run_pysindy_pde_task

    # Stage 3 — symmetry_method_result.
    method_result = run_symmetry_method(
        "polynomial_translation_svd",
        train,
        residual_evaluator=residual_evaluator,
    )
    symmetry_method_result = summarize_symmetry_method_result(method_result)

    # No "best" selection; the built-in method emits exactly one candidate.
    if len(method_result.candidates) != 1:
        raise SchemaValidationError(
            "polynomial_translation_svd is contracted to emit exactly one "
            "SymmetryCandidate; got "
            f"{len(method_result.candidates)}."
        )
    candidate = method_result.candidates[0]
    candidate_summary = summarize_symmetry_candidate(candidate)

    # Stage 5 (optional) — generator_confidence with enriched method_scores.
    generator_family: GeneratorFamily = candidate.payload
    enriched_scores = enrich_method_scores(
        method_result.method_scores, SCORE_METADATA
    )
    generator_confidence = summarize_generator_confidence(
        residual=residual,
        generator=generator_family,
        fit_diagnostics=generator_family,
        method_scores=enriched_scores,
    )

    # Stage 6 — candidate_validation. validate_symmetry_candidate accepts the
    # candidate's payload (a GeneratorFamily here), not the SymmetryCandidate
    # wrapper.
    validation = validate_symmetry_candidate(
        train,
        candidate.payload,
        residual_evaluator=residual_evaluator,
        source_candidate_id=candidate.candidate_id,
    )

    # Stage 7 — finite_transform_verification. Only run if validation didn't
    # fail; otherwise emit a stage marker and gate every downstream stage.
    validation_failed = validation.get("conclusion") == "failed"
    if validation_failed:
        finite_transform_verification: dict[str, Any] = _stage_marker(
            stage="finite_transform_verification",
            status="blocked",
            reason="candidate_validation_failed",
        )
    else:
        verification_report = verify_translation_generator(
            train, generator_family, residual_evaluator
        )
        finite_transform_verification = summarize_verification_report(
            verification_report
        )

    verification_failed = (
        validation_failed
        or finite_transform_verification.get("classification") == "failed"
    )

    # Stage 8 — action_policy (caller-configured; never inferred from scores).
    action_policy: dict[str, Any] = {
        "explicitly_configured_by_caller": True,
        "shifts": list(_ACTION_POLICY_SHIFTS),
        "orbit_cardinality": len(_ACTION_POLICY_SHIFTS),
        "augmentation_budget": len(_ACTION_POLICY_SHIFTS)
        * _TRAIN_BATCH_SIZE,
        "train_test_policy": "orbit_train_only_heldout_untransformed",
        "action_family": "periodic_translation",
        "warnings": [],
    }

    # Stage 9 — orbit_or_coverage_diagnostics. Materialize the train-only
    # orbit; if verification failed, refuse to materialize and emit a marker.
    if verification_failed:
        orbit_stage: dict[str, Any] = _stage_marker(
            stage="orbit_or_coverage_diagnostics",
            status="blocked",
            reason=(
                "candidate_validation_failed"
                if validation_failed
                else "finite_transform_verification_failed"
            ),
        )
        orbit_batch_for_split: OrbitBatchResult | None = None
    else:
        orbit_batch_for_split = build_uniform_translation_orbit_batch(
            train, shifts=list(_ACTION_POLICY_SHIFTS)
        )
        orbit_stage = dict(orbit_batch_for_split.report)

    # Stage 10 — split_leakage_provenance. When orbit isn't materialized we
    # still emit a real report over the training partitions to preserve
    # stage identity; heldout provenance is documented via
    # action_policy.train_test_policy.
    if orbit_batch_for_split is None:
        split_leakage_provenance: dict[str, Any] = _stage_marker(
            stage="split_leakage_provenance",
            status="blocked",
            reason="orbit_not_materialized_upstream_verification_gate",
        )
    else:
        partitions = ["train"] * int(
            orbit_batch_for_split.report["output_batch_size"]
        )
        split_leakage_provenance = summarize_split_leakage_provenance(
            partitions=partitions,
            orbit_batch=orbit_batch_for_split,
            source_report_id=candidate.candidate_id,
        )

    # Stages 11 + 12 — baseline_discovery_task + candidate_guided_discovery_task.
    if verification_failed or orbit_batch_for_split is None:
        baseline_discovery_task: dict[str, Any] = _stage_marker(
            stage="baseline_discovery_task",
            status="blocked",
            reason="upstream_verification_gate",
        )
        candidate_guided_discovery_task: dict[str, Any] = _stage_marker(
            stage="candidate_guided_discovery_task",
            status="blocked",
            reason="upstream_verification_gate",
        )
    elif scenario == "valid_but_not_useful_static":
        # Static illustration: real fixtures ran up to here; the discovery-task
        # numbers below are NOT runtime measurements — they are documented
        # illustrative provenance for the valid-but-not-useful wedge.
        baseline_discovery_task = _stage_marker(
            stage="baseline_discovery_task",
            status="skipped_by_policy",
            reason="static_illustration_no_runtime_task_executed",
        )
        candidate_guided_discovery_task = _stage_marker(
            stage="candidate_guided_discovery_task",
            status="skipped_by_policy",
            reason="static_illustration_no_runtime_task_executed",
        )
    else:
        # For the discovery-task stages, use a single-trajectory slice of the
        # training FieldBatch (and the same for orbit output) so every fit
        # takes the single-trajectory PySINDy 2.x adapter path.
        train_slice = _slice_first_trajectory(train)
        orbit_slice = _slice_first_trajectory(orbit_batch_for_split.field)
        baseline_model = _build_caller_configured_sindy()
        candidate_guided_model = _build_caller_configured_sindy()
        with _legacy_numpy_rng_seed_scope(effective_seed):
            baseline_discovery_task = run_pysindy_pde_task(
                train_slice,
                task_name=_TASK_NAME_BASELINE,
                pysindy_model=baseline_model,
                heldout_field=heldout,
            )
            candidate_guided_discovery_task = run_pysindy_pde_task(
                orbit_slice,
                task_name=_TASK_NAME_CANDIDATE_GUIDED,
                pysindy_model=candidate_guided_model,
                heldout_field=heldout,
            )

    # Stages 13 + 14 — downstream_comparison + evidence_conclusion.
    if verification_failed:
        downstream_comparison: dict[str, Any] = {
            "metric_key": "heldout_residual_l2_norm",
            "baseline_value": None,
            "candidate_guided_value": None,
            "absolute_delta": None,
            "relative_delta": None,
            "improvement_direction": "lower_is_better",
            "improved": None,
            "warnings": [
                "downstream_comparison_not_computed_upstream_verification_gate"
            ],
        }
        if validation_failed:
            evidence_label = "blocked_by_candidate_validation"
            reasons = ["candidate_validation_conclusion_failed"]
        else:
            evidence_label = "blocked_by_finite_transform_verification"
            reasons = ["finite_transform_verification_classification_failed"]
        evidence_conclusion: dict[str, Any] = {
            "label": evidence_label,
            "reasons": reasons,
            "downstream_gain_claimed": False,
        }
    elif scenario == "valid_but_not_useful_static":
        downstream_comparison = _static_illustration_downstream_comparison()
        evidence_conclusion = _static_illustration_evidence_conclusion()
    else:
        downstream_comparison = _measured_downstream_comparison(
            baseline_discovery_task, candidate_guided_discovery_task
        )
        evidence_conclusion = _label_from_measurement(downstream_comparison)

    workflow_summary = summarize_candidate_to_discovery_workflow(
        field_readiness=field_readiness,
        derivative_residual_evidence=derivative_residual_evidence,
        symmetry_method_result=symmetry_method_result,
        candidate_summary=candidate_summary,
        generator_confidence=generator_confidence,
        candidate_validation=validation,
        finite_transform_verification=finite_transform_verification,
        action_policy=action_policy,
        orbit_or_coverage_diagnostics=orbit_stage,
        split_leakage_provenance=split_leakage_provenance,
        baseline_discovery_task=baseline_discovery_task,
        candidate_guided_discovery_task=candidate_guided_discovery_task,
        downstream_comparison=downstream_comparison,
        evidence_conclusion=evidence_conclusion,
        scope_boundaries=_SCOPE_BOUNDARIES,
        extra_metrics={
            "scenario": scenario,
            "static_illustration": scenario == "valid_but_not_useful_static",
            "derivative_backend": derivatives.backend,
            "seed": effective_seed,
            "train_batch_size": _TRAIN_BATCH_SIZE,
            "heldout_batch_size": _HELDOUT_BATCH_SIZE,
        },
    )

    payload: dict[str, Any] = {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": _SUMMARY_TYPE,
        "scenario": scenario,
        "workflow": workflow_summary,
        "backend_versions": _resolve_backend_versions(),
    }
    # Strict-JSON boundary — refuse NaN / Inf at the outer envelope.
    json.dumps(payload, allow_nan=False)
    return payload


def main() -> None:
    print(
        json.dumps(
            run_candidate_to_discovery_workflow_example(scenario="successful"),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
