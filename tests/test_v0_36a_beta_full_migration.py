"""v0.36a-beta contract tests: the full migration audit's scope and policy.

These gate every PR. The audit itself does not -- it builds two wheels across a
major Python boundary and runs ten pipelines, which belongs in
``.github/workflows/beta_migration.yml`` behind ``workflow_dispatch``.

What is asserted here is everything about beta that can be checked without
running the audit: that the scope is enumerated rather than assumed, that a
blocked combination says why it is blocked, that the frozen scope manifest still
matches what the code computes, and -- the one that caught a real defect -- that
the residuals tolerance carries the measurement that justifies it.

Why the residuals tolerance has its own tests
=============================================

Alpha froze ``atol=1e-12`` for every ``tolerance_numeric`` stage, measured on
``heat_1d`` alone. Beta widened the axis to five PDEs and that value failed on
``kdv_1d``: not because the migration drifted, but because kdv's fitted
coefficient vector has magnitude ``4.404e+01`` against heat's ``1.000e-01``, so
the same relative precision produces an absolute coefficient error 35,000x
larger, which propagates through ``|X| @ dc`` into a residual whose own elements
are ~``4e-09``. Error scale is set by the largest intermediate; tolerance scale
by the smallest output.

That is the release's recurring failure mode -- a threshold measured on one
input and recorded as universal -- so the override is tested for the presence of
its measurement, not merely for its value.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pdelie.audit.full_migration_scope import (
    AUDITABILITY,
    BETA_PDE_NAMES,
    BOUNDARY_CONDITIONS,
    PIPELINE_PATHS,
    ScopeEntry,
    enumerate_scope,
    summarize_scope,
)
from pdelie.errors import ScopeValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO_ROOT / "configs/full_migration"
SCOPE_MANIFEST = CONFIG_DIR / "full_migration_scope.json"
POLICY_PATH = CONFIG_DIR / "comparison_policy.json"

#: Every stage the beta configs declare. Twenty per PDE: alpha's sixteen plus
#: the four PySINDy-routed stages alpha deliberately routed around.
EXPECTED_STAGE_COUNT = 20
PYSINDY_STAGE_IDS = (
    "pysindy_trajectories",
    "pysindy_coefficients",
    "pysindy_selected_support",
    "pysindy_library_size",
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


# --- scope enumeration ------------------------------------------------------


def test_scope_enumerates_every_combination() -> None:
    entries = enumerate_scope()
    assert len(entries) == len(BETA_PDE_NAMES) * len(BOUNDARY_CONDITIONS) * len(PIPELINE_PATHS)
    assert len({(e.pde_name, e.boundary_condition, e.pipeline_path) for e in entries}) == len(
        entries
    )


def test_every_blocked_combination_states_why() -> None:
    """An unaudited combination must justify its absence, or it is just absent."""
    for entry in enumerate_scope():
        if not entry.is_auditable:
            assert (entry.reason or "").strip(), entry
            assert (entry.release_note or "").strip(), entry


def test_blocked_entry_without_a_reason_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="carries no reason"):
        ScopeEntry(
            pde_name="heat_1d",
            boundary_condition="dirichlet",
            pipeline_path="derivative_batch",
            auditability="blocked_missing_legacy_dependency",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pde_name", "schrodinger_1d"),
        ("boundary_condition", "absorbing"),
        ("pipeline_path", "strong_form"),
        ("auditability", "probably_fine"),
    ],
)
def test_unknown_vocabulary_is_refused(field: str, value: str) -> None:
    kwargs = {
        "pde_name": "heat_1d",
        "boundary_condition": "periodic",
        "pipeline_path": "derivative_batch",
        "auditability": "auditable",
    }
    kwargs[field] = value
    with pytest.raises(ScopeValidationError):
        ScopeEntry(**kwargs)  # type: ignore[arg-type]


def test_only_periodic_derivative_and_pysindy_paths_are_auditable() -> None:
    """The measured fact beta's scope rests on, asserted rather than assumed."""
    auditable = {
        (e.pde_name, e.boundary_condition, e.pipeline_path)
        for e in enumerate_scope()
        if e.is_auditable
    }
    expected = {
        (pde, "periodic", path)
        for pde in BETA_PDE_NAMES
        for path in ("derivative_batch", "pysindy_discovery")
    }
    assert auditable == expected


def test_summary_is_strict_json() -> None:
    json.dumps(summarize_scope(), allow_nan=False)


def test_summary_records_the_pysindy_obligation() -> None:
    """Alpha's scope decision created a beta obligation; the report carries it."""
    summary = summarize_scope()
    assert summary["pysindy_path_is_a_beta_obligation"] is True
    assert "1.7.5" in summary["pysindy_path_rationale"]


def test_auditability_vocabulary_is_closed() -> None:
    assert set(AUDITABILITY) == {"auditable", "blocked_missing_legacy_dependency"}


# --- the frozen manifest ----------------------------------------------------


def test_frozen_scope_manifest_matches_the_code() -> None:
    """The manifest is generated from ``summarize_scope``; drift means one moved."""
    frozen = _load(SCOPE_MANIFEST)["auditability"]
    assert frozen == summarize_scope()


def test_manifest_names_every_beta_experiment() -> None:
    manifest = _load(SCOPE_MANIFEST)
    assert tuple(manifest["experiments"]) == BETA_PDE_NAMES
    assert manifest["total_stages"] == len(BETA_PDE_NAMES) * EXPECTED_STAGE_COUNT


def test_manifest_carries_an_alpha_regression_target() -> None:
    """Beta exit gate 6 is run, not asserted -- the manifest says what to run."""
    alpha = _load(SCOPE_MANIFEST)["alpha_regression_manifest"]
    assert alpha["experiments"] == ["hard_heat_experiment"]
    assert Path(REPO_ROOT / alpha["comparison_policy"]).is_file()


@pytest.mark.parametrize("pde", BETA_PDE_NAMES)
def test_every_experiment_config_exists_and_declares_twenty_stages(pde: str) -> None:
    config = _load(CONFIG_DIR / f"{pde}.json")
    assert len(config["stages"]) == EXPECTED_STAGE_COUNT
    assert config["boundary_condition"] == "periodic"
    stage_ids = [stage["stage_id"] for stage in config["stages"]]
    assert len(set(stage_ids)) == len(stage_ids)
    for stage_id in PYSINDY_STAGE_IDS:
        assert stage_id in stage_ids


@pytest.mark.parametrize("pde", BETA_PDE_NAMES)
def test_every_stage_is_traceable_through_its_parents(pde: str) -> None:
    """Beta exit gate 1. Every parent resolves, and the graph is acyclic.

    Checked by actually topologically sorting it, not by looking for the
    self-parent special case -- a two-stage cycle is just as untraceable and
    would pass a self-parent check.
    """
    config = _load(CONFIG_DIR / f"{pde}.json")
    parents = {stage["stage_id"]: list(stage["parent_stage_ids"]) for stage in config["stages"]}

    for stage_id, stage_parents in parents.items():
        assert stage_id not in stage_parents, f"{stage_id} is its own parent"
        assert set(stage_parents) <= set(parents), (stage_id, stage_parents)

    # Kahn's algorithm: everything must be reachable in dependency order.
    resolved: set[str] = set()
    progressed = True
    while progressed:
        progressed = False
        for stage_id, stage_parents in parents.items():
            if stage_id not in resolved and set(stage_parents) <= resolved:
                resolved.add(stage_id)
                progressed = True
    unresolved = set(parents) - resolved
    assert not unresolved, f"{pde}: stages in a dependency cycle: {sorted(unresolved)}"


@pytest.mark.parametrize("pde", BETA_PDE_NAMES)
def test_pysindy_stages_descend_from_the_generated_field(pde: str) -> None:
    """The beta obligation is wired into the graph, not bolted on beside it."""
    config = _load(CONFIG_DIR / f"{pde}.json")
    parents = {stage["stage_id"]: list(stage["parent_stage_ids"]) for stage in config["stages"]}

    def ancestors(stage_id: str) -> set[str]:
        seen: set[str] = set()
        frontier = list(parents[stage_id])
        while frontier:
            current = frontier.pop()
            if current in seen:
                continue
            seen.add(current)
            frontier.extend(parents[current])
        return seen

    for stage_id in PYSINDY_STAGE_IDS:
        assert "generated_field_statistics" in ancestors(stage_id), stage_id


@pytest.mark.parametrize("pde", BETA_PDE_NAMES)
def test_stage_one_is_tolerance_numeric_not_qualitative(pde: str) -> None:
    """The alpha defect, asserted across all five so it cannot silently return.

    ``generated_field_statistics`` reports mean/std/l2. A ``sign`` invariant over
    them is not a real check: std and l2 are non-negative by construction, and
    the mean is ``-4.18e-17`` -- numerical zero, whose sign is rounding noise.
    """
    config = _load(CONFIG_DIR / f"{pde}.json")
    stage = next(s for s in config["stages"] if s["stage_id"] == "generated_field_statistics")
    assert stage["comparison_class"] == "tolerance_numeric"


# --- the comparison policy --------------------------------------------------


def test_policy_is_strict_json_and_inherits_alpha() -> None:
    policy = _load(POLICY_PATH)
    json.dumps(policy, allow_nan=False)
    assert Path(REPO_ROOT / policy["inherits_alpha_policy"]).is_file()


def test_every_intentional_contract_change_links_a_release_note() -> None:
    """Beta exit gate 3. An undocumented intentional change reads as an unnoticed one.

    The linked note must **exist on disk**. A dangling path satisfies
    ``StagePolicy``'s non-empty check while documenting nothing, which is the
    failure this gate is actually about.
    """
    changes = 0
    for stage_id, override in _load(POLICY_PATH)["stage_overrides"].items():
        if override.get("override_label") != "intentional_contract_change":
            continue
        changes += 1
        assert (override.get("justification") or "").strip(), stage_id
        note = (override.get("release_note") or "").strip()
        assert note, stage_id
        assert (REPO_ROOT / note).is_file(), f"{stage_id} links a missing note: {note}"
    assert changes, "beta records intentional PySINDy changes; none found"


def test_pysindy_divergence_is_recorded_per_pde() -> None:
    """The finding beta exists to produce, kept specific rather than summarised."""
    divergence = _load(POLICY_PATH)["pysindy_divergence_by_pde"]
    assert set(divergence) == set(BETA_PDE_NAMES)
    assert sum(1 for value in divergence.values() if value == "identical") == 3
    assert sum(1 for value in divergence.values() if "diverges" in value) == 2


def test_residuals_tolerance_override_carries_its_measurement() -> None:
    """A threshold with no measurement behind it is the thing the freeze forbids."""
    policy = _load(POLICY_PATH)
    override = policy["stage_overrides"]["residuals"]
    measurement = policy["residuals_tolerance_measurement"]

    assert set(measurement["measured_on"]) == set(BETA_PDE_NAMES)
    assert set(measurement["max_abs_delta_by_pde"]) == set(BETA_PDE_NAMES)
    assert measurement["chosen_atol"] == override["atol"]
    assert measurement["worst_observed"] == max(measurement["max_abs_delta_by_pde"].values())
    assert measurement["worst_pde"] == max(
        measurement["max_abs_delta_by_pde"], key=measurement["max_abs_delta_by_pde"].__getitem__
    )


def test_residuals_tolerance_actually_covers_every_measured_pde() -> None:
    """The value is not merely justified in prose; it bounds what was measured."""
    policy = _load(POLICY_PATH)
    atol = policy["stage_overrides"]["residuals"]["atol"]
    measured = policy["residuals_tolerance_measurement"]["max_abs_delta_by_pde"]
    for pde, delta in measured.items():
        assert delta < atol, f"{pde}: measured {delta:g} >= chosen atol {atol:g}"
    assert atol / max(measured.values()) >= 10.0, "house style is a 10x margin or better"


def test_alpha_tolerance_would_have_failed_on_kdv() -> None:
    """Why the override exists: alpha's value does not transfer, measurably."""
    policy = _load(POLICY_PATH)
    alpha_atol = _load(REPO_ROOT / policy["inherits_alpha_policy"])["default_tolerance_numeric"][
        "atol"
    ]
    measured = policy["residuals_tolerance_measurement"]["max_abs_delta_by_pde"]
    assert measured["kdv_1d"] > alpha_atol
    assert measured["heat_1d"] < alpha_atol, "and it did hold on the PDE alpha measured"


def test_beta_margin_is_recorded_against_alphas_claimed_margin() -> None:
    """Widening the PDE axis cost headroom; the policy says how much."""
    policy = _load(POLICY_PATH)
    assert (
        policy["measured_worst_derivative_batch_drift_all_pdes"]
        > policy["alpha_measured_worst_heat_only"]
    )
