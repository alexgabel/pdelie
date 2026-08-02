"""v0.38 §10: the benchmark case registry is the authority; docs are generated.

The defect this replaces
========================

Counts about the benchmark were asserted by matching numbers against prose. The
C-5 guard did ``str(count) in text`` over a document containing "v0.37" sixteen
times, so it passed on the title whatever the count was -- and the documented
figure sat at 34 against a measured 37 for three payloads with nothing able to
notice.

Parsing prose to test a scientific count is a false assurance. The durable fix
is the other direction: derive the counts from a structured registry, generate
the documentation table *from* that registry, and have CI compare the generated
table against the committed one.

Text parsing remains useful as a stale-document check. It is not the authority
for what cases exist.

What is derived from what
=========================

``BENCHMARK_CASES`` is the single source. This module renders it -- and nothing
else renders it, so a table in a document and a count in a test cannot disagree
without CI saying so.
"""

from __future__ import annotations

from typing import Any

from pdelie.benchmarks.parameter_equivariant import (
    BENCHMARK_CASES,
    V0_37C_CASE_IDS,
    V0_38E_CASE_IDS,
)

__all__ = [
    "GENERATED_TABLE_PATH",
    "case_registry_summary",
    "render_case_table",
]

#: Where the generated table is committed. CI regenerates and compares.
GENERATED_TABLE_PATH = "docs/design/generated/benchmark_case_table.md"

_FREEZE_BY_CASE: dict[str, str] = {
    **{case_id: "v0.37c" for case_id in V0_37C_CASE_IDS},
    **{case_id: "v0.38e" for case_id in V0_38E_CASE_IDS},
}


def case_registry_summary() -> dict[str, Any]:
    """Counts, derived. Nothing here is written down twice."""
    cases = BENCHMARK_CASES
    return {
        "total_cases": len(cases),
        "cases_by_freeze": {
            freeze: sorted(
                case_id for case_id, owner in _FREEZE_BY_CASE.items() if owner == freeze
            )
            for freeze in sorted(set(_FREEZE_BY_CASE.values()))
        },
        "deliberate_obstructions": sorted(
            case_id for case_id, case in cases.items() if case.is_deliberate_obstruction
        ),
        "multi_parameter_cases": sorted(
            case_id for case_id, case in cases.items() if case.extra_numeric_parameters
        ),
        "equation_families": sorted({case.equation_family for case in cases.values()}),
        "profiles_used": sorted({case.profile_id for case in cases.values()}),
    }


def render_case_table() -> str:
    """Render the committed documentation table from the registry.

    Deterministic: same registry, same bytes. A test regenerates it and compares
    against the committed file, so a case added without regenerating fails CI
    rather than leaving a table quietly out of date.
    """
    summary = case_registry_summary()
    lines: list[str] = [
        "<!-- GENERATED FILE -- do not edit.",
        "     Source: pdelie.benchmarks.case_registry.render_case_table()",
        "     Regenerate: python -m pdelie.benchmarks.case_registry",
        "     CI compares this file against a fresh render. -->",
        "",
        "# Benchmark Cases (generated)",
        "",
        "| case | freeze | equation family | profile | obstruction | numeric params |",
        "|---|---|---|---|---|---:|",
    ]
    for case_id in sorted(BENCHMARK_CASES):
        case = BENCHMARK_CASES[case_id]
        lines.append(
            f"| {case_id} "
            f"| {_FREEZE_BY_CASE.get(case_id, 'unassigned')} "
            f"| `{case.equation_family}` "
            f"| `{case.profile_id}` "
            f"| {'yes' if case.is_deliberate_obstruction else 'no'} "
            f"| {1 + len(case.extra_numeric_parameters)} |"
        )
    lines += [
        "",
        "## Derived counts",
        "",
        f"- **Total cases:** {summary['total_cases']}",
        (
            f"- **Deliberate obstructions:** "
            f"{len(summary['deliberate_obstructions'])} "
            f"({', '.join(summary['deliberate_obstructions'])})"
        ),
        (
            f"- **Multi-parameter cases:** "
            f"{len(summary['multi_parameter_cases'])} "
            f"({', '.join(summary['multi_parameter_cases']) or 'none'})"
        ),
        f"- **Equation families:** {', '.join(f'`{f}`' for f in summary['equation_families'])}",
        "",
        "### Cases by governing freeze",
        "",
    ]
    for freeze, case_ids in summary["cases_by_freeze"].items():
        lines.append(f"- **{freeze}:** {', '.join(case_ids)}")
    lines.append("")
    lines.append(
        "A signed freeze governs the population it measured. A case added later "
        "belongs to a later freeze, never retroactively to an earlier one."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:  # pragma: no cover - invoked as a script
    from pathlib import Path

    target = Path(__file__).resolve().parents[3] / GENERATED_TABLE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_case_table())
    print(f"wrote {target}")


if __name__ == "__main__":  # pragma: no cover
    main()
