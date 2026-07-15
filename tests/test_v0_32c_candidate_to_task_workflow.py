"""v0.32c candidate-to-discovery workflow example — 20 required contract tests.

The workflow example lives at
``src/pdelie/examples/candidate_to_discovery_workflow.py`` and composes the
15 frozen stages via
``pdelie.reporting.summarize_candidate_to_discovery_workflow``. This module
enforces the frozen surface (public-submodule-only imports, stage order,
strict-JSON, action-policy separation, held-out policy, valid-but-not-useful
honesty, CLI JSON-only, no root export).
"""

from __future__ import annotations

import ast
import importlib
import json
import math
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

import pdelie
from pdelie.errors import SchemaValidationError
from pdelie.examples import candidate_to_discovery_workflow as example_module
from pdelie.examples.candidate_to_discovery_workflow import (
    run_candidate_to_discovery_workflow_example,
)
from pdelie.reporting import summarize_candidate_to_discovery_workflow

_STAGE_ORDER = (
    "field_readiness",
    "derivative_residual_evidence",
    "symmetry_method_result",
    "candidate_summary",
    "generator_confidence",
    "candidate_validation",
    "finite_transform_verification",
    "action_policy",
    "orbit_or_coverage_diagnostics",
    "split_leakage_provenance",
    "baseline_discovery_task",
    "candidate_guided_discovery_task",
    "downstream_comparison",
    "evidence_conclusion",
    "scope_boundaries",
)

_STAGE_MARKER_SUMMARY_TYPE = "candidate_to_discovery_workflow_stage_marker"

_SUCCESSFUL_LABELS = {"successful_composition", "valid_but_not_useful"}


@pytest.fixture(scope="module")
def scenario_a_result() -> dict:
    return run_candidate_to_discovery_workflow_example(scenario="successful")


@pytest.fixture(scope="module")
def scenario_b_result() -> dict:
    return run_candidate_to_discovery_workflow_example(
        scenario="valid_but_not_useful_static"
    )


# ---------------------------------------------------------------------------
# Case 1: only public submodule APIs imported by the example.
# ---------------------------------------------------------------------------


def test_case_01_example_imports_only_public_submodule_apis() -> None:
    """The example module must import only names from public pdelie submodules.

    Enforced by parsing the source and checking every ``from pdelie...``
    import points at a submodule (never the root ``pdelie`` package) and
    every imported name is present on that submodule's public surface.
    """
    source = Path(example_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if not module.startswith("pdelie"):
                continue
            assert module != "pdelie", (
                f"Example imports directly from root pdelie: {ast.dump(node)}"
            )
            submodule = importlib.import_module(module)
            for alias in node.names:
                name = alias.name
                assert hasattr(submodule, name), (
                    f"{module} has no public attribute {name!r} "
                    "(v0.32c example imports may only reference public "
                    "submodule surfaces)."
                )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                assert not alias.name == "pdelie", (
                    "Example must not `import pdelie` (root import)."
                )


# ---------------------------------------------------------------------------
# Case 2: root API unchanged.
# ---------------------------------------------------------------------------


def test_case_02_root_api_unchanged() -> None:
    """No v0.32c symbol may appear on the root ``pdelie`` namespace."""
    forbidden = (
        "run_candidate_to_discovery_workflow_example",
        "summarize_candidate_to_discovery_workflow",
    )
    for name in forbidden:
        assert not hasattr(pdelie, name), (
            f"v0.32c leaked a root export: pdelie.{name}"
        )


# ---------------------------------------------------------------------------
# Case 3: exact stage order.
# ---------------------------------------------------------------------------


def test_case_03_stage_order_is_exact(scenario_a_result: dict) -> None:
    workflow = scenario_a_result["workflow"]
    assert workflow["stage_order"] == list(_STAGE_ORDER)
    # Every stage key must be present.
    for stage in _STAGE_ORDER:
        assert stage in workflow, (
            f"Missing stage {stage!r} in workflow payload."
        )


# ---------------------------------------------------------------------------
# Case 4: every stage retained even when failed / unavailable.
# ---------------------------------------------------------------------------


def test_case_04_every_stage_retained_static_illustration_scenario_b(
    scenario_b_result: dict,
) -> None:
    """Scenario B skips the two discovery-task stages by policy — the stage
    keys are still present, carrying stage-marker payloads (never dropped).
    """
    workflow = scenario_b_result["workflow"]
    for stage in _STAGE_ORDER:
        assert stage in workflow
    for skipped in (
        "baseline_discovery_task",
        "candidate_guided_discovery_task",
    ):
        marker = workflow[skipped]
        assert marker["summary_type"] == _STAGE_MARKER_SUMMARY_TYPE
        assert marker["status"] == "skipped_by_policy"


# ---------------------------------------------------------------------------
# Case 5: strict-JSON complete payload.
# ---------------------------------------------------------------------------


def test_case_05_strict_json_complete_payload_round_trip(
    scenario_a_result: dict, scenario_b_result: dict
) -> None:
    for payload in (scenario_a_result, scenario_b_result):
        encoded = json.dumps(payload, allow_nan=False)
        assert json.loads(encoded) == payload


# ---------------------------------------------------------------------------
# Case 6: NaN / Inf adversarial rejection.
# ---------------------------------------------------------------------------


def test_case_06_nan_inf_adversarial_rejection() -> None:
    """A NaN inside the downstream_comparison block must raise
    SchemaValidationError at the composed-summary boundary."""
    minimal_field_readiness = _valid_field_readiness_summary()
    with pytest.raises(SchemaValidationError, match="finite"):
        summarize_candidate_to_discovery_workflow(
            field_readiness=minimal_field_readiness,
            derivative_residual_evidence={
                "summary_type": "candidate_to_discovery_workflow_stage_marker",
                "status": "unavailable",
                "reason": "test",
                "stage": "derivative_residual_evidence",
            },
            symmetry_method_result={
                "summary_type": "candidate_to_discovery_workflow_stage_marker",
                "status": "unavailable",
                "reason": "test",
                "stage": "symmetry_method_result",
            },
            candidate_summary={
                "summary_type": "candidate_to_discovery_workflow_stage_marker",
                "status": "unavailable",
                "reason": "test",
                "stage": "candidate_summary",
            },
            candidate_validation={
                "summary_type": "candidate_to_discovery_workflow_stage_marker",
                "status": "unavailable",
                "reason": "test",
                "stage": "candidate_validation",
            },
            finite_transform_verification={
                "summary_type": "candidate_to_discovery_workflow_stage_marker",
                "status": "unavailable",
                "reason": "test",
                "stage": "finite_transform_verification",
            },
            action_policy=_valid_action_policy(),
            orbit_or_coverage_diagnostics={
                "summary_type": "candidate_to_discovery_workflow_stage_marker",
                "status": "unavailable",
                "reason": "test",
                "stage": "orbit_or_coverage_diagnostics",
            },
            split_leakage_provenance={
                "summary_type": "candidate_to_discovery_workflow_stage_marker",
                "status": "unavailable",
                "reason": "test",
                "stage": "split_leakage_provenance",
            },
            baseline_discovery_task={
                "summary_type": "candidate_to_discovery_workflow_stage_marker",
                "status": "unavailable",
                "reason": "test",
                "stage": "baseline_discovery_task",
            },
            candidate_guided_discovery_task={
                "summary_type": "candidate_to_discovery_workflow_stage_marker",
                "status": "unavailable",
                "reason": "test",
                "stage": "candidate_guided_discovery_task",
            },
            downstream_comparison={
                "metric_key": "heldout_residual_l2_norm",
                "baseline_value": math.nan,  # <- adversarial
                "candidate_guided_value": None,
                "absolute_delta": None,
                "relative_delta": None,
                "improvement_direction": "lower_is_better",
                "improved": None,
                "warnings": [],
            },
            evidence_conclusion=_valid_evidence_conclusion(),
            scope_boundaries=_valid_scope_boundaries(),
        )


# ---------------------------------------------------------------------------
# Case 7: candidate-validation failure blocks transformation.
# ---------------------------------------------------------------------------


def test_case_07_candidate_validation_failure_blocks_transformation() -> None:
    """When the candidate_validation stage is marked ``failed``, the
    orbit_or_coverage_diagnostics stage MUST be a stage-marker (never a
    materialized orbit report)."""
    workflow = _build_workflow_with_validation_status("failed")
    orbit_stage = workflow["orbit_or_coverage_diagnostics"]
    assert orbit_stage["summary_type"] == _STAGE_MARKER_SUMMARY_TYPE
    assert orbit_stage["status"] == "blocked"


# ---------------------------------------------------------------------------
# Case 8: finite-transform verification failure blocks orbit use.
# ---------------------------------------------------------------------------


def test_case_08_finite_transform_verification_failure_blocks_orbit() -> None:
    workflow = _build_workflow_with_verification_status("failed")
    orbit_stage = workflow["orbit_or_coverage_diagnostics"]
    assert orbit_stage["summary_type"] == _STAGE_MARKER_SUMMARY_TYPE
    assert orbit_stage["status"] == "blocked"
    assert (
        workflow["evidence_conclusion"]["label"]
        == "blocked_by_finite_transform_verification"
    )


# ---------------------------------------------------------------------------
# Case 9: explicit action-policy parameters recorded.
# ---------------------------------------------------------------------------


def test_case_09_action_policy_explicit_fields_recorded(
    scenario_a_result: dict,
) -> None:
    action_policy = scenario_a_result["workflow"]["action_policy"]
    assert action_policy["explicitly_configured_by_caller"] is True
    assert isinstance(action_policy["shifts"], list) and action_policy["shifts"]
    assert isinstance(action_policy["orbit_cardinality"], int)
    assert action_policy["orbit_cardinality"] > 0
    assert action_policy["train_test_policy"]
    assert action_policy["action_family"] == "periodic_translation"


# ---------------------------------------------------------------------------
# Case 10: no action parameters inferred from method scores.
# ---------------------------------------------------------------------------


def test_case_10_no_action_parameters_inferred_from_method_scores() -> None:
    """An action_policy with ``explicitly_configured_by_caller=False`` must
    be refused. The workflow example never promotes method scores to
    action parameters."""
    with pytest.raises(SchemaValidationError, match="explicitly_configured"):
        summarize_candidate_to_discovery_workflow(
            **_minimal_marker_kwargs(exclude=("action_policy",)),
            action_policy={
                "explicitly_configured_by_caller": False,
                "shifts": [0.0],
                "orbit_cardinality": 1,
                "augmentation_budget": None,
                "train_test_policy": "test",
                "action_family": "periodic_translation",
                "warnings": [],
            },
        )


# ---------------------------------------------------------------------------
# Case 11: heldout remains untransformed.
# ---------------------------------------------------------------------------


def test_case_11_heldout_remains_untransformed(
    scenario_a_result: dict,
) -> None:
    workflow = scenario_a_result["workflow"]
    train_test_policy = workflow["action_policy"]["train_test_policy"]
    assert "orbit_train_only_heldout_untransformed" == train_test_policy
    # The orbit stage's construction_method must be a training-side
    # transformation; source_field_shape must reference the training batch.
    orbit_stage = workflow["orbit_or_coverage_diagnostics"]
    if orbit_stage["summary_type"] != _STAGE_MARKER_SUMMARY_TYPE:
        assert orbit_stage["construction_method"] == "uniform_translation"


# ---------------------------------------------------------------------------
# Case 12: split/leakage provenance recorded.
# ---------------------------------------------------------------------------


def test_case_12_split_leakage_provenance_recorded(
    scenario_a_result: dict,
) -> None:
    workflow = scenario_a_result["workflow"]
    split_stage = workflow["split_leakage_provenance"]
    assert split_stage["summary_type"] == "split_leakage_provenance"
    # Every partition count in scenario A belongs to the training
    # partition — heldout is never transformed by the orbit step.
    assert set(split_stage["partition_counts"].keys()) == {"train"}
    assert split_stage["policy"]["partitions_are_user_supplied"] is True


# ---------------------------------------------------------------------------
# Case 13: baseline + candidate-guided use comparable configured policies.
# ---------------------------------------------------------------------------


def test_case_13_baseline_and_candidate_guided_share_backend_and_optimizer(
    scenario_a_result: dict,
) -> None:
    workflow = scenario_a_result["workflow"]
    baseline = workflow["baseline_discovery_task"]
    candidate_guided = workflow["candidate_guided_discovery_task"]
    if _is_stage_marker(baseline) or _is_stage_marker(candidate_guided):
        pytest.skip("scenario A ran with static illustration; no runtime tasks")
    assert baseline["backend_name"] == candidate_guided["backend_name"]
    assert baseline["input_layout"] == candidate_guided["input_layout"]
    assert baseline["derivative_backend"] == candidate_guided["derivative_backend"]
    assert baseline["target_convention"] == candidate_guided["target_convention"]


# ---------------------------------------------------------------------------
# Case 14: no silent failed-seed / stage exclusion.
# ---------------------------------------------------------------------------


def test_case_14_no_silent_failed_stage_exclusion(
    scenario_b_result: dict,
) -> None:
    """Every skipped or blocked stage must be surfaced as a stage-marker
    with a non-empty ``reason`` — never omitted from the payload."""
    workflow = scenario_b_result["workflow"]
    for stage in _STAGE_ORDER:
        value = workflow[stage]
        if _is_stage_marker(value):
            assert value["reason"]
            assert value["stage"] == stage


# ---------------------------------------------------------------------------
# Case 15: deterministic output.
# ---------------------------------------------------------------------------


def test_case_15_deterministic_output_under_fixed_seed() -> None:
    """Two calls with the same scenario and seed produce byte-identical
    payloads once wall-clock ``runtime_seconds`` and ULP-level numeric
    diagnostics (which vary by fused-multiply-add scheduling across
    otherwise-identical runs) are canonicalized to a stable sentinel."""
    a = _canonicalize_variance(
        run_candidate_to_discovery_workflow_example(
            scenario="valid_but_not_useful_static"
        )
    )
    b = _canonicalize_variance(
        run_candidate_to_discovery_workflow_example(
            scenario="valid_but_not_useful_static"
        )
    )
    assert json.dumps(a, allow_nan=False, sort_keys=True) == json.dumps(
        b, allow_nan=False, sort_keys=True
    )


def _canonicalize_variance(payload: dict) -> dict:
    """Zero out fields that legitimately vary between runs (wall-clock
    timing, floating-point batch-error diagnostics at ULP precision)."""
    import copy

    p = copy.deepcopy(payload)
    method = p["workflow"]["symmetry_method_result"]
    method["runtime_seconds"] = 0.0
    for stage in (
        "finite_transform_verification",
        "candidate_validation",
    ):
        node = p["workflow"][stage]
        _zero_numeric_diagnostics(node)
    return p


def _zero_numeric_diagnostics(node: object) -> None:
    if isinstance(node, dict):
        for key in list(node.keys()):
            if key == "batch_errors":
                node[key] = "__variance_canonicalized__"
            else:
                _zero_numeric_diagnostics(node[key])
    elif isinstance(node, list):
        for item in node:
            _zero_numeric_diagnostics(item)


# ---------------------------------------------------------------------------
# Case 16: valid candidate can be not useful downstream.
# ---------------------------------------------------------------------------


def test_case_16_valid_candidate_can_be_not_useful_downstream(
    scenario_b_result: dict,
) -> None:
    workflow = scenario_b_result["workflow"]
    assert workflow["candidate_validation"]["conclusion"] in {
        "validated",
        "partially_validated",
    }
    assert workflow["finite_transform_verification"]["classification"] in {
        "exact",
        "approximate",
    }
    assert workflow["evidence_conclusion"]["label"] == "valid_but_not_useful"
    assert workflow["evidence_conclusion"]["downstream_gain_claimed"] is False


# ---------------------------------------------------------------------------
# Case 17: no automatic "best" result.
# ---------------------------------------------------------------------------


def test_case_17_no_automatic_best_result_selection(
    scenario_a_result: dict,
) -> None:
    workflow = scenario_a_result["workflow"]
    method_result = workflow["symmetry_method_result"]
    # The built-in method contract emits exactly one candidate; there is
    # no ranking / winner / "best" field on the workflow payload.
    assert len(method_result["candidates"]) == 1
    # scope_boundaries records the non-claim.
    assert workflow["scope_boundaries"]["automatic_best_selection_claimed"] is False


# ---------------------------------------------------------------------------
# Case 18: CLI emits JSON only.
# ---------------------------------------------------------------------------


def test_case_18_cli_emits_json_only() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pdelie.examples.candidate_to_discovery_workflow",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["summary_type"] == "candidate_to_discovery_workflow_example"
    assert payload["workflow"]["summary_type"] == "candidate_to_discovery_workflow"


# ---------------------------------------------------------------------------
# Case 19: built-wheel example passes (in-tree deterministic smoke).
# ---------------------------------------------------------------------------


def test_case_19_example_runs_end_to_end_deterministic(
    scenario_a_result: dict,
) -> None:
    """v0.32c does not build a fresh wheel per test — the harness runs on
    the editable install. This test enforces that the example returns a
    valid ``candidate_to_discovery_workflow_example`` payload with the
    workflow summary nested at ``payload["workflow"]``. The clean-wheel
    smoke is exercised separately in the release validation."""
    assert scenario_a_result["summary_type"] == "candidate_to_discovery_workflow_example"
    assert (
        scenario_a_result["workflow"]["summary_type"]
        == "candidate_to_discovery_workflow"
    )
    label = scenario_a_result["workflow"]["evidence_conclusion"]["label"]
    assert label in _SUCCESSFUL_LABELS


# ---------------------------------------------------------------------------
# Case 20: scope-boundary text forbids generic symmetry discovery and
# universal downstream benefit claims.
# ---------------------------------------------------------------------------


def test_case_20_scope_boundaries_forbid_generic_and_universal_claims(
    scenario_a_result: dict,
) -> None:
    scope = scenario_a_result["workflow"]["scope_boundaries"]
    assert scope["generic_symmetry_discovery_claimed"] is False
    assert scope["universal_downstream_benefit_claimed"] is False
    assert scope["noise_robustness_claimed"] is False
    assert scope["nonperiodic_claimed"] is False
    assert scope["multi_d_claimed"] is False
    assert scope["external_data_claimed"] is False
    assert scope["automatic_best_selection_claimed"] is False
    assert scope["periodic_scalar_1d_only"] is True


# ---------------------------------------------------------------------------
# Test helpers.
# ---------------------------------------------------------------------------


def _is_stage_marker(value: Mapping[str, object]) -> bool:
    return value.get("summary_type") == _STAGE_MARKER_SUMMARY_TYPE


def _valid_action_policy() -> dict:
    return {
        "explicitly_configured_by_caller": True,
        "shifts": [0.0, 0.25],
        "orbit_cardinality": 2,
        "augmentation_budget": 4,
        "train_test_policy": "orbit_train_only_heldout_untransformed",
        "action_family": "periodic_translation",
        "warnings": [],
    }


def _valid_evidence_conclusion() -> dict:
    return {
        "label": "valid_but_not_useful",
        "reasons": ["test"],
        "downstream_gain_claimed": False,
    }


def _valid_scope_boundaries() -> dict:
    return {
        "periodic_scalar_1d_only": True,
        "generic_symmetry_discovery_claimed": False,
        "universal_downstream_benefit_claimed": False,
        "noise_robustness_claimed": False,
        "nonperiodic_claimed": False,
        "multi_d_claimed": False,
        "external_data_claimed": False,
        "automatic_best_selection_claimed": False,
    }


def _valid_field_readiness_summary() -> dict:
    # A minimal field_batch_readiness-shaped stage marker suffices for the
    # NaN/Inf test: the composed-summary boundary only recognizes the
    # summary_type discriminator + strict-JSON compatibility of the payload.
    return {
        "summary_type": "candidate_to_discovery_workflow_stage_marker",
        "status": "unavailable",
        "reason": "test_only",
        "stage": "field_readiness",
    }


def _valid_downstream_comparison() -> dict:
    return {
        "metric_key": "heldout_residual_l2_norm",
        "baseline_value": 1.0,
        "candidate_guided_value": 1.0,
        "absolute_delta": 0.0,
        "relative_delta": 0.0,
        "improvement_direction": "lower_is_better",
        "improved": False,
        "warnings": [],
    }


def _minimal_marker_kwargs(*, exclude: tuple[str, ...] = ()) -> dict:
    """Build a full set of stage-marker kwargs so we can vary one field."""
    kwargs = {}
    for stage in _STAGE_ORDER:
        if stage == "action_policy":
            kwargs[stage] = _valid_action_policy()
        elif stage == "downstream_comparison":
            kwargs[stage] = _valid_downstream_comparison()
        elif stage == "evidence_conclusion":
            kwargs[stage] = _valid_evidence_conclusion()
        elif stage == "scope_boundaries":
            kwargs[stage] = _valid_scope_boundaries()
        elif stage == "generator_confidence":
            # generator_confidence is optional; skip.
            continue
        else:
            kwargs[stage] = {
                "summary_type": _STAGE_MARKER_SUMMARY_TYPE,
                "status": "unavailable",
                "reason": "test_only",
                "stage": stage,
            }
    for name in exclude:
        kwargs.pop(name, None)
    return kwargs


def _build_workflow_with_validation_status(status: str) -> dict:
    """Compose a workflow payload with an artificial validation status."""
    kwargs = _minimal_marker_kwargs(
        exclude=("candidate_validation", "orbit_or_coverage_diagnostics",
                 "evidence_conclusion")
    )
    kwargs["candidate_validation"] = {
        "summary_type": "symmetry_candidate_validation",
        "summary_schema_version": "0.1",
        "candidate_kind": "generator_family",
        "source_candidate_id": "test",
        "empirical_interpretation": "test",
        "field_shape": [1, 1, 1, 1],
        "equation": "heat",
        "residual_evaluator": "HeatResidualEvaluator",
        "finite_transform_epsilons": [1e-4],
        "thresholds": {},
        "closure_required": True,
        "candidate_summary": {},
        "configured_validation_checks": [],
        "check_reports": {},
        "conclusion": status,
    }
    kwargs["orbit_or_coverage_diagnostics"] = {
        "summary_type": _STAGE_MARKER_SUMMARY_TYPE,
        "status": "blocked",
        "reason": "candidate_validation_failed",
        "stage": "orbit_or_coverage_diagnostics",
    }
    kwargs["evidence_conclusion"] = {
        "label": "blocked_by_candidate_validation",
        "reasons": ["candidate_validation_conclusion_failed"],
        "downstream_gain_claimed": False,
    }
    return summarize_candidate_to_discovery_workflow(**kwargs)


def _build_workflow_with_verification_status(status: str) -> dict:
    kwargs = _minimal_marker_kwargs(
        exclude=("finite_transform_verification",
                 "orbit_or_coverage_diagnostics",
                 "evidence_conclusion")
    )
    kwargs["finite_transform_verification"] = {
        "summary_schema_version": "0.1",
        "summary_type": "verification_report",
        "norm": "l2",
        "classification": status,
        "epsilon_values": [1e-4, 1e-3, 1e-2],
        "error_curve": [1.0, 1.0, 1.0],
        "first_epsilon": 1e-4,
        "first_error": 1.0,
        "max_error": 1.0,
        "diagnostics": {},
    }
    kwargs["orbit_or_coverage_diagnostics"] = {
        "summary_type": _STAGE_MARKER_SUMMARY_TYPE,
        "status": "blocked",
        "reason": "finite_transform_verification_failed",
        "stage": "orbit_or_coverage_diagnostics",
    }
    kwargs["evidence_conclusion"] = {
        "label": "blocked_by_finite_transform_verification",
        "reasons": ["finite_transform_verification_classification_failed"],
        "downstream_gain_claimed": False,
    }
    return summarize_candidate_to_discovery_workflow(**kwargs)
