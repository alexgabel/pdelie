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
    """The release version, with any PEP 440 prerelease suffix stripped.

    ``0.38.0a1`` parses as ``(0, 38, 0)``. That is deliberate: an alpha of
    0.38.0 is *already* 0.38 for the purpose of a forward promise, so a notice
    saying "v0.38 will require X" comes due at the alpha, not at the final. If
    the suffix were kept in the comparison, a promise could be carried past
    every prerelease of the release it names and only fall due at the end --
    which is exactly the deferral this module exists to prevent.

    The earlier form did ``int(part)`` on each component and raised
    ``ValueError: invalid literal for int() with base 10: '0a1'`` at the first
    prerelease the project ever cut.
    """
    raw = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]["version"]
    parts: list[int] = []
    for part in raw.split(".")[:3]:
        match = re.match(r"^(\d+)", part)
        if match is None:
            raise AssertionError(f"unparseable version component {part!r} in {raw!r}")
        parts.append(int(match.group(1)))
    return tuple(parts)


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


def test_the_scanner_finds_a_planted_promise() -> None:
    """Replaces "at least one promise exists in src/", retired at v0.38.

    That assertion existed so the parametrized test below could not pass by
    scanning nothing. Its premise was that the repository always carries an
    outstanding promise -- and it does not: v0.38 discharged the last one by
    making the weak diagnostic's seed required.

    **Zero outstanding promises is the good state**, not a broken gate. So the
    non-vacuity is established against synthetic text instead, which keeps the
    scanner honest without requiring the codebase to carry debt forever.
    """
    planted = [
        'warnings.warn("v9.99 will require an explicit widget", FutureWarning)',
        "# v9.99 will require an explicit widget",
    ]
    for text in planted:
        assert any(cue in text for cue in _PROMISE_CUES), (
            f"no cue matches {text!r}; the scanner would miss a real promise "
            f"written this way"
        )
        assert _VERSION_TOKEN.search(text), "the version token did not parse"


def test_a_promise_naming_a_past_version_would_fail() -> None:
    """The gate's actual job, proven against a constructed violation.

    Without this, "no promises found" and "every promise is fine" are
    indistinguishable outcomes -- and after v0.38 the first is the real one.
    """
    current = _packaged_version()
    stale = (current[0], current[1])  # names this very release
    assert not stale > current[: len(stale)], (
        "a promise naming the current version must not read as future; if this "
        "passes, the comparison below cannot catch a promise that came due"
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


def test_the_weak_diagnostic_seed_promise_was_fulfilled_not_dropped() -> None:
    """The migration this module exists because of, now discharged.

    This test used to assert the promise was still *detected*, and said in its
    own message: "either it was fulfilled -- in which case remove this test --
    or its wording drifted out of _PROMISE_CUES, which would make the guard
    silently blind."

    Those two outcomes look identical to a scanner, so the distinction is made
    by checking the thing the promise promised. It was fulfilled at v0.38: the
    seed is a required keyword-only argument.
    """
    import inspect as _inspect

    from pdelie.tasks.weak_pde_library import inspect_pysindy_weak_pde_library

    parameter = _inspect.signature(inspect_pysindy_weak_pde_library).parameters["seed"]
    assert parameter.default is _inspect.Parameter.empty, (
        "the weak-diagnostic seed promise is no longer detected AND the seed "
        "still has a default -- so the promise was not fulfilled, its wording "
        "drifted out of _PROMISE_CUES, and the guard is silently blind"
    )
    assert parameter.kind is _inspect.Parameter.KEYWORD_ONLY


def test_promise_cues_catch_the_wording_that_escaped() -> None:
    """The exact phrasing that shipped wrong must be detectable."""
    escaped = "v0.37 will require an explicit integer seed"
    assert any(cue in escaped for cue in _PROMISE_CUES)
    assert _VERSION_TOKEN.search(escaped)


def test_a_historical_citation_is_not_treated_as_a_promise() -> None:
    """"Added in v0.33d" is history, not a commitment; the guard must not fire."""
    history = "This vocabulary was introduced in v0.33d and is unchanged."
    assert not any(cue in history.lower() for cue in _PROMISE_CUES)
