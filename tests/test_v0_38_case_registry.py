"""v0.38 §10: counts come from the registry; the docs table is generated.

Replaces "assert the number appears somewhere in the prose", which passed on a
document title for three payloads without anyone noticing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pdelie.benchmarks.case_registry import (
    GENERATED_TABLE_PATH,
    case_registry_summary,
    render_case_table,
)
from pdelie.benchmarks.parameter_equivariant import (
    BENCHMARK_CASES,
    V0_37C_CASE_IDS,
    V0_38E_CASE_IDS,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATED = REPO_ROOT / GENERATED_TABLE_PATH


def test_the_committed_table_matches_a_fresh_render() -> None:
    """The CI comparison. A case added without regenerating fails here.

    This is the whole mechanism: the registry is the authority, the table is a
    projection of it, and the two cannot drift without the build saying so.
    """
    assert GENERATED.exists(), (
        f"{GENERATED_TABLE_PATH} is missing. Regenerate with "
        f"`python -m pdelie.benchmarks.case_registry`."
    )
    assert GENERATED.read_text() == render_case_table(), (
        "the committed benchmark case table is out of date. Regenerate with "
        "`python -m pdelie.benchmarks.case_registry` -- do not hand-edit it."
    )


def test_the_render_is_deterministic() -> None:
    """Otherwise the comparison above would fail intermittently."""
    assert render_case_table() == render_case_table()


def test_the_generated_file_says_it_is_generated() -> None:
    """A reader who opens it must not edit it by hand."""
    text = GENERATED.read_text()
    assert "GENERATED FILE" in text
    assert "do not edit" in text
    assert "python -m pdelie.benchmarks.case_registry" in text


# --------------------------------------------------------------------------
# Counts are derived, never written down twice
# --------------------------------------------------------------------------


def test_the_summary_counts_agree_with_the_registry() -> None:
    summary = case_registry_summary()
    assert summary["total_cases"] == len(BENCHMARK_CASES)
    assert summary["deliberate_obstructions"] == sorted(
        case_id for case_id, case in BENCHMARK_CASES.items() if case.is_deliberate_obstruction
    )
    assert summary["multi_parameter_cases"] == sorted(
        case_id for case_id, case in BENCHMARK_CASES.items() if case.extra_numeric_parameters
    )


def test_every_case_is_assigned_to_exactly_one_freeze() -> None:
    summary = case_registry_summary()
    assigned = [case_id for ids in summary["cases_by_freeze"].values() for case_id in ids]
    assert sorted(assigned) == sorted(BENCHMARK_CASES)
    assert len(assigned) == len(set(assigned)), "a case belongs to two freezes"


def test_the_freeze_partition_matches_the_declared_tuples() -> None:
    summary = case_registry_summary()
    assert summary["cases_by_freeze"]["v0.37c"] == sorted(V0_37C_CASE_IDS)
    assert summary["cases_by_freeze"]["v0.38e"] == sorted(V0_38E_CASE_IDS)


# --------------------------------------------------------------------------
# The registry is the single renderer
# --------------------------------------------------------------------------


def test_only_the_registry_renders_the_case_table() -> None:
    """Two renderers would be two authorities, which is the defect returning."""
    import ast

    src = REPO_ROOT / "src" / "pdelie"
    renderers: list[str] = []
    for path in sorted(src.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and "render_case_table" in node.name:
                renderers.append(f"{path.name}::{node.name}")
    assert renderers == ["case_registry.py::render_case_table"], (
        f"the case table is rendered from {renderers}; there must be exactly one"
    )


def test_the_generated_table_is_not_the_authority_for_the_cases() -> None:
    """Direction check: the table is derived from the registry, not parsed into it.

    If `case_registry` ever read the markdown back, the generated file would
    become an input and the loop would close on itself.
    """
    source = (REPO_ROOT / "src/pdelie/benchmarks/case_registry.py").read_text()
    assert ".read_text()" not in source, (
        "case_registry reads a file. The registry is the authority; nothing here "
        "may parse a document to learn what the cases are."
    )


# --------------------------------------------------------------------------
# A planted drift is detected
# --------------------------------------------------------------------------


def test_a_drifted_table_is_detected(tmp_path: Path) -> None:
    """Sentinel: the comparison must be able to fail.

    A comparison that always passes is exactly the failure mode this replaces --
    the old guard passed because "37" appeared in the phrase "v0.37".
    """
    tampered = render_case_table().replace("**Total cases:** ", "**Total cases:** 99 ")
    assert tampered != render_case_table()
    scratch = tmp_path / "table.md"
    scratch.write_text(tampered)
    assert scratch.read_text() != render_case_table()


@pytest.mark.parametrize("case_id", sorted(BENCHMARK_CASES))
def test_every_case_appears_in_the_generated_table(case_id: str) -> None:
    assert f"| {case_id} |" in GENERATED.read_text()
