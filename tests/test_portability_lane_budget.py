"""v0.36 day-zero: the cross-platform portability lane is budgeted.

The lane (``.github/workflows/portability.yml``) runs on Linux **and** macOS so
that cross-platform equality claims are validated rather than assumed -- the
failure mode behind v0.33e, v0.35a, and v0.35c.

It is capped at 30 tests on purpose. A lane that runs the whole suite on two
platforms protects nothing in particular and takes twice as long to say so; the
budget forces the marker onto the assertions that genuinely cross platforms.
Raising the cap is a deliberate decision, made here, not a side effect of
marking one more test.

See ``docs/design/CROSS_PLATFORM_PORTABILITY_CLASSES.md``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Maximum number of tests permitted to carry ``@pytest.mark.portability``.
PORTABILITY_LANE_BUDGET = 30


def collected_portability_test_count() -> int:
    """Count tests the *collector* resolves for the marker.

    Collection is used rather than a source grep so that parametrized cases are
    counted as the lane will actually run them -- one marked parametrized test
    with eight cases costs eight slots, not one.
    """
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-m",
            "portability",
            "--collect-only",
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # pytest exits 5 when nothing is collected, which is a valid state here.
    if result.returncode not in (0, 5):
        raise AssertionError(
            f"portability collection failed (rc={result.returncode}):\n{result.stdout}\n{result.stderr}"
        )
    for line in reversed(result.stdout.splitlines()):
        stripped = line.strip()
        if stripped.endswith(("test collected", "tests collected")):
            return int(stripped.split()[0])
        # "3 tests collected, 1810 deselected" is handled above; a bare deselect
        # line with no collection at all means zero marked tests.
        if stripped.endswith("deselected") and "collected" not in stripped:
            return 0
        if "no tests collected" in stripped:
            return 0
    return 0


def test_portability_marker_is_registered() -> None:
    """An unregistered marker silently matches nothing under ``-m``."""
    import tomllib

    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    markers = config["tool"]["pytest"]["ini_options"]["markers"]
    assert any(entry.startswith("portability:") for entry in markers), (
        "the 'portability' marker must be registered in pyproject so that "
        "`pytest -m portability` selects rather than silently matching nothing"
    )


def test_portability_lane_stays_within_budget() -> None:
    count = collected_portability_test_count()
    assert count <= PORTABILITY_LANE_BUDGET, (
        f"{count} tests carry @pytest.mark.portability, over the budget of "
        f"{PORTABILITY_LANE_BUDGET}. Raising the cap is a deliberate decision: "
        f"edit PORTABILITY_LANE_BUDGET and say why in the PR."
    )


def test_portability_workflow_exists_and_covers_both_platforms() -> None:
    """The budget is meaningless if the lane does not actually run on both."""
    workflow = (REPO_ROOT / ".github/workflows/portability.yml").read_text(encoding="utf-8")
    assert "ubuntu-22.04" in workflow
    assert "macos-14" in workflow
    assert "-m portability" in workflow
