"""v0.36 day-zero: planned release identifiers must sort above every shipped one.

This guard exists because the roadmap planned the 2-D contract widening as
``v0.4`` while ``v0.4.0`` was already a shipped tag -- and ``0.4.0`` sorts
*below* the then-current ``0.35.0``. The same string denoted a completed
milestone in one table and a future arc in another. Caught by inspection during
v0.36 planning; this test is what catches the next one.

Shipped versions are read from ``CHANGELOG.md`` rather than from ``git tag``:
CI checkouts are shallow and do not reliably carry the full tag list, and the
changelog is the authoritative in-repo record.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

packaging_version = pytest.importorskip("packaging.version")

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Rows in the forward-planning table. The historical table below it records
#: completed milestones and is deliberately not parsed.
_PLANNED_ROW = re.compile(r"^\|\s*`(v\d+\.\d+(?:\.\d+)?[a-z]?\d*)`\s*\|[^|]*\|\s*Planned")

#: ``## 0.35.0`` style changelog headings.
_RELEASED_HEADING = re.compile(r"^##\s+(\d+\.\d+(?:\.\d+)?)\s*$")


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def released_versions() -> list[str]:
    return [
        match.group(1)
        for line in _read("CHANGELOG.md").splitlines()
        if (match := _RELEASED_HEADING.match(line.strip()))
    ]


def planned_identifiers() -> list[str]:
    return [
        match.group(1)
        for line in _read("docs/planning/ROADMAP.md").splitlines()
        if (match := _PLANNED_ROW.match(line.strip()))
    ]


def test_changelog_records_shipped_versions() -> None:
    released = released_versions()
    assert released, "CHANGELOG.md must record at least one released version"
    assert "0.35.0" in released


def test_roadmap_declares_planned_milestones() -> None:
    planned = planned_identifiers()
    assert planned, "ROADMAP.md forward table must declare at least one planned milestone"


def test_every_planned_identifier_sorts_above_every_shipped_version() -> None:
    """The guard proper.

    A planned identifier that sorts at or below a shipped version cannot be
    tagged: the tag either already exists or would move the version backwards.
    """
    parse = packaging_version.Version
    released = [parse(value) for value in released_versions()]
    highest = max(released)

    failures: list[str] = []
    for identifier in planned_identifiers():
        planned = parse(identifier.lstrip("v"))
        if planned <= highest:
            failures.append(
                f"planned {identifier!r} parses as {planned} which is not above "
                f"the highest shipped version {highest}"
            )
    assert not failures, "\n".join(failures)


def test_no_planned_identifier_collides_with_a_shipped_version() -> None:
    parse = packaging_version.Version
    released = {parse(value) for value in released_versions()}
    collisions = [
        identifier
        for identifier in planned_identifiers()
        if parse(identifier.lstrip("v")) in released
    ]
    assert not collisions, (
        f"planned identifiers reuse a shipped version: {collisions}"
    )


def test_planned_identifiers_are_unique() -> None:
    planned = planned_identifiers()
    duplicates = {value for value in planned if planned.count(value) > 1}
    assert not duplicates, f"duplicate planned identifiers in ROADMAP: {sorted(duplicates)}"


def test_the_v0_4_collision_specifically_cannot_return() -> None:
    """Regression guard for the case that motivated this file.

    ``v0.4.0`` shipped long before ``v0.35.0``. Planning a future arc as ``v0.4``
    is the exact defect this test exists to prevent, so it is asserted by name
    rather than relying only on the general rule above.
    """
    assert "v0.4" not in planned_identifiers(), (
        "v0.4 is a shipped release (v0.4.0) and sorts below the current line; "
        "the multi-channel / 2-D widening arc is v0.40"
    )
