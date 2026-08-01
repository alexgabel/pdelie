"""v0.37c: the registries must match the freeze document that governs them.

A benchmark whose code and whose freeze can drift apart is a benchmark with two
answers to every question. These tests parse
``docs/design/v0_37c_hypothesis_freeze.md`` and assert the registries agree with
it, so the document is the specification rather than a description of one.

They also assert what the freeze forbids: **no tolerance value lives in the
scaffolding**. A threshold here would let the benchmark define its own pass
mark before the pilot that is supposed to measure it has run.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pytest

from pdelie.benchmarks import (
    CONFIRMATORY_ALPHA_GRID,
    EXPECTED_CLASSIFICATIONS,
    PILOT_ALPHA_GRID,
    PROFILE_REGISTRY,
    SIX_BENCHMARK_CASES,
    alpha_grid,
    build_coefficient_field,
    resolve_case,
)
from pdelie.errors import ScopeValidationError

REPO_ROOT = Path(__file__).resolve().parents[1]
FREEZE = REPO_ROOT / "docs/design/v0_37c_hypothesis_freeze.md"
PILOT_REPORT = REPO_ROOT / "docs/design/v0_37c_pilot_report.md"
CONFIRMATORY = REPO_ROOT / "docs/design/v0_37c_confirmatory_freeze.md"


def _freeze() -> str:
    return FREEZE.read_text()


def _case_rows() -> dict[str, list[str]]:
    """Parse the six-case table out of the freeze document."""
    rows: dict[str, list[str]] = {}
    for line in _freeze().splitlines():
        match = re.match(r"^\|\s*(C-\d)\s*\|", line)
        if match:
            cells = [cell.strip().strip("`") for cell in line.strip().strip("|").split("|")]
            rows[match.group(1)] = cells
    return rows


# --- the document governs the registry --------------------------------------


def test_the_freeze_document_exists_and_is_marked_frozen() -> None:
    assert "**Status:** frozen" in _freeze()


def test_the_six_cases_match_the_freeze_table() -> None:
    rows = _case_rows()
    assert set(rows) == set(SIX_BENCHMARK_CASES) == {"C-1", "C-2", "C-3", "C-4", "C-5", "C-6"}


@pytest.mark.parametrize("case_id", sorted(SIX_BENCHMARK_CASES))
def test_each_case_declares_the_operator_family_the_freeze_gives_it(case_id: str) -> None:
    cells = _case_rows()[case_id]
    case = SIX_BENCHMARK_CASES[case_id]
    assert case.expected_operator_family in cells, (
        f"{case_id}: registry says {case.expected_operator_family!r}, freeze row "
        f"says {cells}"
    )


@pytest.mark.parametrize("case_id", sorted(SIX_BENCHMARK_CASES))
def test_each_case_declares_the_equation_and_profile_the_freeze_gives_it(case_id: str) -> None:
    cells = _case_rows()[case_id]
    case = SIX_BENCHMARK_CASES[case_id]
    assert case.equation_family in cells
    assert case.profile_id in cells


@pytest.mark.parametrize("classification", EXPECTED_CLASSIFICATIONS)
def test_every_expected_classification_appears_in_the_freeze(classification: str) -> None:
    assert classification in _freeze()


def test_the_operator_family_set_is_exactly_identity_and_scalar_multiplier() -> None:
    """The measured consequence: the v0.37b synthesis gap is inert here.

    No case selects ``linear_combination_of_derivatives`` or
    ``diagnostic_fitted``, so v0.37b's decision not to synthesise the former
    cannot affect this benchmark. If a future case selects it, this fails and
    the gap becomes a blocker that has to be closed first.
    """
    families = {case.expected_operator_family for case in SIX_BENCHMARK_CASES.values()}
    assert families == {"identity", "scalar_multiplier"}
    assert "linear_combination_of_derivatives" not in families
    assert "diagnostic_fitted" not in families


def test_four_of_six_cases_are_deliberate_obstructions() -> None:
    """The benchmark distinguishes six outcomes; it does not pass six tests."""
    obstructions = [c.case_id for c in SIX_BENCHMARK_CASES.values() if c.is_deliberate_obstruction]
    assert sorted(obstructions) == ["C-3", "C-4", "C-5", "C-6"]


# --- alpha grids ----------------------------------------------------------------


def test_the_alpha_grids_are_disjoint() -> None:
    assert set(PILOT_ALPHA_GRID).isdisjoint(set(CONFIRMATORY_ALPHA_GRID))


def test_the_grids_match_the_freeze_document() -> None:
    text = _freeze()
    for value in PILOT_ALPHA_GRID:
        assert f"{value}" in text, value
    for value in CONFIRMATORY_ALPHA_GRID:
        assert f"{value}" in text, value


def test_zero_is_a_pilot_control_and_not_a_confirmatory_point() -> None:
    """At zero dose every profile degenerates to constant; that is the control."""
    assert 0.0 in PILOT_ALPHA_GRID
    assert 0.0 not in CONFIRMATORY_ALPHA_GRID


def test_every_alpha_is_inside_the_positivity_bound() -> None:
    for value in PILOT_ALPHA_GRID + CONFIRMATORY_ALPHA_GRID:
        assert 0.0 <= value < 1.0


def test_alpha_grid_dispatch_refuses_an_unknown_phase() -> None:
    assert alpha_grid("pilot") == PILOT_ALPHA_GRID
    assert alpha_grid("confirmatory") == CONFIRMATORY_ALPHA_GRID
    with pytest.raises(ScopeValidationError, match="no third phase"):
        alpha_grid("final")


# --- profiles and positivity ------------------------------------------------


@pytest.mark.parametrize("profile_id", sorted(PROFILE_REGISTRY))
@pytest.mark.parametrize("alpha", PILOT_ALPHA_GRID + CONFIRMATORY_ALPHA_GRID)
def test_every_profile_is_strictly_positive_at_every_alpha(profile_id: str, alpha: float) -> None:
    """Positivity is the reason for the a0*(1 + alpha*f) form; assert it."""
    x = np.linspace(0.0, 2.0 * np.pi, 64)
    values = build_coefficient_field(profile_id, alpha, x)
    assert values.min() > 0.0


@pytest.mark.parametrize("profile_id", sorted(PROFILE_REGISTRY))
def test_every_profile_shape_is_bounded_by_one(profile_id: str) -> None:
    """|f|inf <= 1 is what makes the positivity guarantee hold."""
    x = np.linspace(0.0, 2.0 * np.pi, 512)
    shape = PROFILE_REGISTRY[profile_id].shape(x)
    assert float(np.abs(shape).max()) <= 1.0 + 1e-12


def test_the_constant_profile_ignores_alpha() -> None:
    """It is the control: the knob must have no effect."""
    x = np.linspace(0.0, 2.0 * np.pi, 32)
    baseline = build_coefficient_field("constant", 0.0, x)
    for alpha in PILOT_ALPHA_GRID:
        assert np.array_equal(build_coefficient_field("constant", alpha, x), baseline)


def test_alpha_zero_collapses_every_profile_to_the_constant() -> None:
    """The PS-1 control rests on this being true by construction."""
    x = np.linspace(0.0, 2.0 * np.pi, 32)
    constant = build_coefficient_field("constant", 0.0, x)
    for profile_id in PROFILE_REGISTRY:
        assert np.allclose(build_coefficient_field(profile_id, 0.0, x), constant)


@pytest.mark.parametrize("alpha", [-0.1, 1.0, 1.5])
def test_alpha_outside_the_positivity_bound_is_refused(alpha: float) -> None:
    x = np.linspace(0.0, 2.0 * np.pi, 32)
    with pytest.raises(ScopeValidationError, match="outside"):
        build_coefficient_field("sinusoidal", alpha, x)


def test_the_five_profiles_match_the_freeze() -> None:
    text = _freeze()
    assert len(PROFILE_REGISTRY) == 5
    for profile_id in PROFILE_REGISTRY:
        assert f"`{profile_id}`" in text, profile_id


def test_unknown_case_and_profile_are_refused() -> None:
    with pytest.raises(ScopeValidationError, match="unknown benchmark case"):
        resolve_case("C-7")
    with pytest.raises(ScopeValidationError, match="unknown profile"):
        build_coefficient_field("chirp", 0.1, np.linspace(0, 1, 8))


# --- what the freeze forbids ------------------------------------------------


def test_no_tolerance_lives_in_the_scaffolding() -> None:
    """Thresholds belong to the confirmatory freeze, after the pilot measures them.

    Checked against **declared names**, parsed. A text scan flags this module's
    own docstring saying no tolerance appears in it -- the disclaim-vs-claim
    trap that ``tests/test_forbidden_language.py`` documents at length. The
    constraint is about what the module declares, not what its prose mentions.
    """
    import ast

    source = (REPO_ROOT / "src/pdelie/benchmarks/parameter_equivariant.py").read_text()
    tree = ast.parse(source)
    declared: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            declared.append(node.target.id)
        elif isinstance(node, ast.Assign):
            declared.extend(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.arg):
            declared.append(node.arg)

    banned = ("rtol", "atol", "tolerance", "threshold", "floor", "pass_mark")
    offenders = [
        name for name in declared if any(token in name.lower() for token in banned)
    ]
    assert not offenders, (
        f"the benchmark scaffolding declares {offenders}; a threshold here would "
        f"let the benchmark define its own pass mark before the pilot measured it"
    )


def test_the_freeze_declares_the_block_status_and_the_artifact_paths() -> None:
    """Blocking must be a declared outcome, not an absent document."""
    text = _freeze()
    assert "blocked_pilot_criteria_not_met" in text
    assert "v0_37c_pilot_report.md" in text
    assert "v0_37c_confirmatory_freeze.md" in text
    assert "names the specific PS criterion violated" in text


def test_the_freeze_states_all_three_pilot_criteria() -> None:
    text = _freeze()
    for criterion in ("PS-1", "PS-2", "PS-3"):
        assert criterion in text, criterion


def test_the_freeze_contains_no_frozen_tolerance_value() -> None:
    """PS-2: an experimentally-tuned threshold is a failure however well it works."""
    assert "No tolerance value appears in this document" in _freeze()


def test_the_pilot_and_confirmatory_documents_do_not_exist_yet() -> None:
    """Scaffolding only. The pilot has not run and nothing may claim it has."""
    assert not PILOT_REPORT.exists()
    assert not CONFIRMATORY.exists()


def test_the_reconnaissance_is_disclosed() -> None:
    """A pilot presented as blind when it was not is worse than one described."""
    text = _freeze()
    assert "Pre-registration reconnaissance" in text
    assert "disjoint from the grid the reconnaissance used" in text


def test_v0_37c_adds_no_root_export() -> None:
    import pdelie

    for name in ("SIX_BENCHMARK_CASES", "PROFILE_REGISTRY", "BenchmarkCase"):
        assert name not in pdelie.__all__
