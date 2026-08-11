"""Prove the Gate F guards can FAIL. Run this when reviewing, not the suite.

A green suite shows the guards pass. It does not show they can fail, and that
distinction is the entire subject of the v0.38 Gate F correction: F-4 passed on
every run it was ever given, and could not have failed, because the rows it
existed to exclude were invisible to it.

So this script disables each guard in turn and asserts the suite goes RED. A
guard whose removal leaves the suite green is vacuous, and this exits nonzero.

    python scripts/verify_guard_nonvacuity.py

Every mutation is applied to a file on disk and reverted in a ``finally``, with
the restored content verified by SHA-256 before the next mutation runs. If a
restore ever fails the script stops immediately rather than continuing against a
mutated tree.

Reviewing with this
===================

The review question is not "does a test exist for requirement N". It is "would
that test fail if the behaviour regressed". This answers the second directly:
each row names the guard removed and the tests that consequently failed.

If a guard's row shows ``0 tests failed``, that guard is not being checked by
anything, whatever the test names suggest.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SUITE = "tests/test_replay_population_integrity.py"


@dataclass(frozen=True)
class Mutation:
    """One guard, disabled the way a careless refactor would disable it."""

    name: str
    path: str
    old: str
    new: str
    why: str


MUTATIONS = (
    Mutation(
        name="F-4a  null order accepted regardless of family",
        path="scripts/compare_replay.py",
        old="                if family not in NON_ORDER_FAMILIES:",
        new="                if False:",
        why="the original defect: `None` treated as proof of non-order-parameterisation",
    ),
    Mutation(
        name="F-3   exact row-set equality",
        path="scripts/compare_replay.py",
        old="        if emitted != EXPECTED_KEYS:",
        new="        if False:",
        why="a count check passes on the wrong 229 rows",
    ),
    Mutation(
        name="F-3a  gate/exploratory partition",
        path="scripts/compare_replay.py",
        old="        if emitted_gate != EXPECTED_GATE_KEYS:",
        new="        if False:",
        why="the broken population had the correct total (286) throughout",
    ),
    Mutation(
        name="F-4   gate order within {1,2,3}",
        path="scripts/compare_replay.py",
        old='            if order not in SCOPE["supported_derivative_orders"]:',
        new="            if False:",
        why="admits d=4 as gate evidence",
    ),
    Mutation(
        name="F-6   bitwise counted before the floor branch",
        path="scripts/compare_replay.py",
        old="            numeric_comparisons_total += 1",
        new="            pass  # counter moved after the floor branch",
        why=(
            "restores the ordering where floor rows bypassed the counter, so the "
            "bitwise denominator excluded exactly the values a libm change "
            "perturbs first"
        ),
    ),
    Mutation(
        name="contract  order-parameterised row may omit its order",
        path="scripts/replay_contracts.py",
        old="        if self.order_parameterized and self.derivative_order is None:",
        new="        if False:",
        why="the malformed row becomes constructible again",
    ),
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_suite() -> tuple[int, str]:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", SUITE, "-q", "--no-header", "-p", "no:cacheprovider"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout


def _failed_count(output: str) -> int:
    for line in reversed(output.splitlines()):
        if " failed" in line:
            for token in line.replace(",", " ").split():
                if token.isdigit():
                    return int(token)
    return 0


def main() -> None:
    print("=== Gate F guard non-vacuity ===\n")

    code, output = _run_suite()
    if code != 0:
        print("BASELINE IS NOT GREEN. Fix that before interpreting anything below.")
        print(output[-1500:])
        raise SystemExit(2)
    print(f"  baseline: {output.strip().splitlines()[-1]}\n")

    rows: list[tuple[str, int, bool]] = []
    for mutation in MUTATIONS:
        path = REPO_ROOT / mutation.path
        original = path.read_text()
        before = _sha(path)

        if mutation.old not in original:
            print(f"  SKIP  {mutation.name}\n        anchor not found in {mutation.path}")
            rows.append((mutation.name, -1, False))
            continue

        try:
            path.write_text(original.replace(mutation.old, mutation.new, 1))
            code, output = _run_suite()
            failed = _failed_count(output) if code != 0 else 0
        finally:
            path.write_text(original)
            if _sha(path) != before:
                raise SystemExit(
                    f"FATAL: could not restore {mutation.path}. Stopping with the "
                    f"tree possibly mutated. Run `git checkout -- {mutation.path}`."
                )

        caught = failed > 0
        rows.append((mutation.name, failed, caught))
        mark = "OK  " if caught else "VACUOUS"
        print(f"  {mark}  {mutation.name}")
        print(f"          {failed} test(s) failed when disabled")
        if not caught:
            print(f"          NOTHING CHECKS THIS. {mutation.why}")

    print("\n=== summary ===")
    vacuous = [name for name, _, caught in rows if not caught]
    for name, failed, caught in rows:
        state = f"{failed} red" if caught else ("skipped" if failed < 0 else "VACUOUS")
        print(f"  {state:>10}  {name}")

    if vacuous:
        print(f"\n{len(vacuous)} guard(s) can be removed without any test noticing:")
        for name in vacuous:
            print(f"  - {name}")
        raise SystemExit(1)
    print("\nEvery guard above turns the suite red when removed.")


if __name__ == "__main__":
    main()
