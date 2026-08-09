"""Independent audit of a Gate F replay artifact.

**Imports neither the generator nor the comparator.** That is the whole point.

Run `31326189317` produced a population the generator built and the comparator
blessed, because both consulted the same broken understanding of what a row
means. A checker that shares a helper with the thing it checks cannot detect an
error in that helper -- the two agree, and agreement is mistaken for correctness.

So this module re-derives everything from the JSON on disk, using its own
parsing, and cross-checks three sources that should agree:

1. the **row key** as displayed (parsed here, independently)
2. the **typed field** ``derivative_order`` the runner emitted
3. the **frozen manifest** ``configs/gate_f_expected_rows.json``

Any disagreement is reported. This deliberately duplicates logic that exists
elsewhere; the duplication is the mechanism, not an oversight.

Usage:
    python scripts/audit_replay_population.py <artifact-dir-or-json> [...]
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]

#: Parsed here, not imported. See the module docstring.
_TRAILING_ORDER = re.compile(r"_d(\d+)$")

#: Restated here, not imported, for the same reason. If these drift from the
#: scope artifact the audit says so rather than silently adopting the new value.
AUDIT_SUPPORTED_ORDERS = frozenset({1, 2, 3})
AUDIT_EXPLORATORY_ORDERS = frozenset({4})
AUDIT_NON_ORDER_FAMILIES = frozenset({"weak", "grid", "reference_kind"})


def _displayed_order(row_key: str) -> int | None:
    match = _TRAILING_ORDER.search(row_key)
    return int(match.group(1)) if match else None


def _artifacts(paths: list[Path]) -> dict[str, list[dict[str, Any]]]:
    found: dict[str, list[dict[str, Any]]] = {}
    for path in paths:
        candidates = (
            sorted(path.rglob("gate_f_replay.json")) if path.is_dir() else [path]
        )
        for candidate in candidates:
            payload = json.loads(candidate.read_text())
            p = payload.get("platform", {})
            label = f"{p.get('system','?')}/{p.get('machine','?')}-py{p.get('python','?')}"
            found[f"{label} [{candidate.name}]"] = payload["rows"]
    return found


def audit(label: str, rows: list[dict[str, Any]], manifest: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    expected = {(r["workload"], r["row_key"]): r for r in manifest["rows"]}

    emitted = {(r["workload"], r["row_key"]) for r in rows}
    missing = sorted(set(expected) - emitted)
    unexpected = sorted(emitted - set(expected))
    if missing:
        problems.append(f"{len(missing)} row(s) missing, e.g. {missing[:3]}")
    if unexpected:
        problems.append(f"{len(unexpected)} unexpected row(s), e.g. {unexpected[:3]}")

    for row in rows:
        key = (row["workload"], row["row_key"])
        typed = row.get("derivative_order")
        shown = _displayed_order(row["row_key"])
        gate_use = row.get("gate_use")
        family = row.get("workload_family")

        # 1 vs 2: the display string and the typed field.
        if shown != typed:
            problems.append(
                f"{key[0]}/{key[1]}: row key displays d={shown} but the row "
                f"carries derivative_order={typed}"
            )

        # 1/2 vs 3: both against the frozen manifest.
        if key in expected:
            want = expected[key]
            if typed != want["derivative_order"]:
                problems.append(
                    f"{key[0]}/{key[1]}: derivative_order {typed} != frozen "
                    f"{want['derivative_order']}"
                )
            if gate_use != want["gate_use"]:
                problems.append(
                    f"{key[0]}/{key[1]}: gate_use {gate_use!r} != frozen "
                    f"{want['gate_use']!r}"
                )

        if gate_use != "gate_evidence":
            continue

        # The scope rule, restated independently.
        if typed is None:
            if family not in AUDIT_NON_ORDER_FAMILIES:
                problems.append(
                    f"{key[0]}/{key[1]}: gate evidence with no derivative order, "
                    f"family {family!r} is not declared order-free"
                )
        elif typed not in AUDIT_SUPPORTED_ORDERS:
            problems.append(
                f"{key[0]}/{key[1]}: gate evidence at d={typed}, outside "
                f"{sorted(AUDIT_SUPPORTED_ORDERS)}"
            )

    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()

    manifest = json.loads((REPO_ROOT / "configs/gate_f_expected_rows.json").read_text())

    # The manifest is itself audited against the audit's own restated rules,
    # before it is used to judge anything. A frozen artifact is not exempt.
    manifest_problems = audit("frozen manifest", manifest["rows"], manifest)
    if manifest_problems:
        print("### The frozen manifest fails its own audit\n")
        for problem in manifest_problems:
            print(f"- {problem}")
        raise SystemExit(2)

    artifacts = _artifacts(args.paths)
    if not artifacts:
        raise SystemExit("no gate_f_replay.json found")

    failed = False
    for label, rows in sorted(artifacts.items()):
        problems = audit(label, rows, manifest)
        gate = [r for r in rows if r.get("gate_use") == "gate_evidence"]
        expl = [r for r in rows if r.get("gate_use") == "exploratory_only"]
        orders = collections.Counter(
            r["derivative_order"] for r in gate
        )
        print(f"### {label}\n")
        print(f"- rows: {len(rows)} (gate {len(gate)}, exploratory {len(expl)})")
        print(f"- gate rows by derivative order: "
              f"{dict(sorted(orders.items(), key=lambda kv: (kv[0] is None, kv[0])))}")
        if problems:
            failed = True
            print(f"- **{len(problems)} problem(s)**")
            for problem in problems[:20]:
                print(f"  - {problem}")
        else:
            print("- no disagreement between row key, typed field and manifest")
        print()

    if failed:
        print("AUDIT FAILED")
    else:
        print("AUDIT PASSED — three independent sources agree on every row")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
