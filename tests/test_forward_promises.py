"""Every "this will change at version X" promise, in one place.

A deprecation notice naming a version that has already shipped is worse than no
notice: it tells a reader the change happened when it did not. v0.37 shipped
with a `FutureWarning` saying "v0.37 will require an explicit integer seed",
because the transition was scoped out of v0.37a after the notice was written.

Nobody noticed until the release close, and only then because the warning
happened to print during a test run.

This module is the single point of failure for that class. The packaged version
is read from ``pyproject.toml`` -- never hardcoded -- so the check tightens
automatically at every release rather than needing to be remembered.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src/pdelie"

#: Any token that looks like a promised release.
_VERSION_TOKEN = re.compile(r"\bv(\d+)\.(\d+)(?:\.(\d+))?\b")

#: Phrases that make a version token a *promise* rather than a citation. A
#: docstring saying "added in v0.33d" is history; "v0.38 will require" is a
#: commitment, and only commitments are checked.
_PROMISE_CUES = (
    "will require",
    "will be required",
    "will raise",
    "will become",
    "will change",
    "will be removed",
    "will retire",
)


def _packaged_version() -> tuple[int, ...]:
    raw = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]["version"]
    return tuple(int(part) for part in raw.split(".")[:3])


def _as_tuple(match: re.Match[str]) -> tuple[int, ...]:
    return tuple(int(g) for g in match.groups() if g is not None)


def _promises() -> list[tuple[Path, int, str, tuple[int, ...]]]:
    """Every (file, line, text, promised_version) in shipped source."""
    found: list[tuple[Path, int, str, tuple[int, ...]]] = []
    for path in sorted(SRC.rglob("*.py")):
        for number, line in enumerate(path.read_text().splitlines(), start=1):
            lowered = line.lower()
            if not any(cue in lowered for cue in _PROMISE_CUES):
                continue
            for match in _VERSION_TOKEN.finditer(line):
                found.append((path, number, line.strip(), _as_tuple(match)))
    return found


def test_at_least_one_promise_is_found() -> None:
    """Otherwise every assertion below passes by scanning nothing.

    If the last forward promise is ever removed, delete this test deliberately
    rather than letting the module become a no-op that still looks like a gate.
    """
    assert _promises(), (
        "no forward promises found in src/. If that is genuinely true, this "
        "module is now vacuous and should be retired on purpose."
    )


@pytest.mark.parametrize(
    ("path", "line", "text", "promised"),
    _promises(),
    ids=lambda v: str(v) if not isinstance(v, Path) else v.name,
)
def test_every_promise_names_a_future_version(
    path: Path, line: int, text: str, promised: tuple[int, ...]
) -> None:
    """A promise must name a version strictly later than the packaged one."""
    current = _packaged_version()
    assert promised > current[: len(promised)], (
        f"{path.relative_to(REPO_ROOT)}:{line} promises {promised}, but the "
        f"package is already {current}. Either make the change or move the "
        f"promise to a later version.\n  {text}"
    )


def test_the_weak_diagnostic_seed_promise_is_registered_here() -> None:
    """The migration this module exists because of.

    Previously asserted inside ``test_v0_36e_deterministic_seed.py``, where it
    only covered one API and one wording. Consolidated so a second promise
    added anywhere in ``src/`` is checked without anyone remembering to.
    """
    promises = {path.name for path, _, _, _ in _promises()}
    assert "weak_pde_library.py" in promises, (
        "the weak-diagnostic seed promise is no longer detected; either it was "
        "fulfilled -- in which case remove this test -- or its wording drifted "
        "out of _PROMISE_CUES, which would make the guard silently blind"
    )


def test_promise_cues_catch_the_wording_that_escaped() -> None:
    """The exact phrasing that shipped wrong must be detectable."""
    escaped = "v0.37 will require an explicit integer seed"
    assert any(cue in escaped for cue in _PROMISE_CUES)
    assert _VERSION_TOKEN.search(escaped)


def test_a_historical_citation_is_not_treated_as_a_promise() -> None:
    """"Added in v0.33d" is history, not a commitment; the guard must not fire."""
    history = "This vocabulary was introduced in v0.33d and is unchanged."
    assert not any(cue in history.lower() for cue in _PROMISE_CUES)
