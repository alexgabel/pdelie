"""Pair two runners' Gate F measurements and report the gaps.

Applies the reporting discipline the closure plan section 5 requires, and that
this arc arrived at the hard way:

* **Metric identity is checked before a relative gap is quoted.** Two rows whose
  ``error_metric_spec_id`` differ are not comparable; quoting a ratio between
  them is the v0.37c pilot-1 defect, where a bound in one norm met a measurement
  in another and the factor of 11.96 went unnoticed.

* **Relative gaps are not computed at the floor.** A ratio between two numbers
  that are both `~1e-14` is meaningless. The v0.38d pilot blocked on this twice,
  and the initial 175-measurement replay report applied the same rule.

* **`exact_discrete` fields must agree exactly.** No tolerance, because there is
  no norm on a classification.

Usage:
    python scripts/compare_replay.py <artifact-dir> [--json out.json]
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

# Fields that are classifications, not measurements. Any disagreement is a
# failure regardless of magnitude.
_DISCRETE_FIELDS = (
    "reporting_regime",
    "reference_kind",
    "g5_verdict",
    "is_uniform",
    "accepted",
    "expected_accepted",
    "windows_are_independent",
    "formal_accuracy",
    "portability_class",
    "error_metric_spec_id",
)

# Fields that carry a number to be compared under a tolerance.
_NUMERIC_FIELDS = (
    "absolute_error",
    "relative_error",
    "linear_exactness_relative",
    "ratio_minus_one",
    "spacing_ratio",
    "overlap_fraction",
)

_SQRT_EPS = math.sqrt(2.220446049250313e-16)


def _load(directory: Path) -> dict[str, dict[str, Any]]:
    """Return {runner_label: payload} for every gate_f_replay.json found."""
    found: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.rglob("gate_f_replay.json")):
        payload = json.loads(path.read_text())
        p = payload["platform"]
        label = f"{p['system']}/{p['machine']}-py{p['python']}"
        found[label] = payload
    return found


def _index(payload: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {(r["workload"], r["row_key"]): r for r in payload["rows"]}


def compare(left_label: str, left: dict, right_label: str, right: dict) -> dict[str, Any]:
    a, b = _index(left), _index(right)
    keys = sorted(set(a) & set(b))
    only_left = sorted(set(a) - set(b))
    only_right = sorted(set(b) - set(a))

    discrete_mismatch: list[str] = []
    metric_mismatch: list[str] = []
    worst_rel = 0.0
    worst_key: str | None = None
    floor_rows = 0
    signal_rows = 0
    bitwise = 0
    numeric_rows = 0

    for key in keys:
        ra, rb = a[key], b[key]

        # Metric identity first. A relative gap between rows in different
        # metrics is not a number, whatever the arithmetic says.
        if ra.get("error_metric_spec_id") != rb.get("error_metric_spec_id"):
            metric_mismatch.append(f"{key[0]}/{key[1]}")
            continue

        for field in _DISCRETE_FIELDS:
            if (field in ra or field in rb) and ra.get(field) != rb.get(field):
                discrete_mismatch.append(
                    f"{key[0]}/{key[1]}:{field} {ra.get(field)!r} vs {rb.get(field)!r}"
                )

        # Floor rows: both sides report None for the relative error by design.
        if ra.get("reporting_regime") == "floor":
            floor_rows += 1
            continue

        for field in _NUMERIC_FIELDS:
            x, y = ra.get(field), rb.get(field)
            if x is None or y is None:
                continue
            numeric_rows += 1
            if x == y:
                bitwise += 1
            scale = ra.get("reference_scale") or max(abs(x), abs(y))
            if scale == 0.0:
                continue
            # Signal versus floor, against the v0.38d boundary.
            if max(abs(x), abs(y)) <= _SQRT_EPS * scale:
                floor_rows += 1
                continue
            signal_rows += 1
            denominator = max(abs(x), abs(y))
            rel = abs(x - y) / denominator if denominator else 0.0
            if rel > worst_rel:
                worst_rel, worst_key = rel, f"{key[0]}/{key[1]}:{field}"

    return {
        "left": left_label,
        "right": right_label,
        "paired_rows": len(keys),
        "unpaired_left": only_left,
        "unpaired_right": only_right,
        "discrete_mismatches": discrete_mismatch,
        "metric_mismatches": metric_mismatch,
        "numeric_comparisons": numeric_rows,
        "bitwise_identical": bitwise,
        "signal_rows": signal_rows,
        "floor_rows": floor_rows,
        "worst_relative_gap": worst_rel,
        "worst_relative_gap_at": worst_key,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    runners = _load(args.directory)
    if len(runners) < 2:
        raise SystemExit(f"need at least two runners, found {sorted(runners)}")

    labels = sorted(runners)
    results = []
    # Every pair, so the 2x2 corner's diagonals are compared explicitly rather
    # than inferred from two independent comparisons against one anchor.
    for i, left in enumerate(labels):
        for right in labels[i + 1 :]:
            results.append(compare(left, runners[left], right, runners[right]))

    print(f"### Runners ({len(labels)})\n")
    for label in labels:
        counts = runners[label]["counts"]
        print(f"- `{label}` — {counts['total']} rows "
              f"({counts['v0_38b']} b / {counts['v0_38c']} c / {counts['v0_38d']} d)")

    print(f"\n### Pairwise comparisons ({len(results)})\n")
    print("| pair | paired | discrete | metric | signal | floor | bitwise | worst rel gap |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in results:
        d = len(r["discrete_mismatches"]) or "—"
        m = len(r["metric_mismatches"]) or "—"
        print(f"| {r['left']} vs {r['right']} | {r['paired_rows']} | {d} | {m} | "
              f"{r['signal_rows']} | {r['floor_rows']} | {r['bitwise_identical']} | "
              f"`{r['worst_relative_gap']:.3e}` |")

    failures = [r for r in results if r["discrete_mismatches"] or r["metric_mismatches"]
                or r["unpaired_left"] or r["unpaired_right"]]
    if failures:
        print("\n### Failures\n")
        for r in failures:
            for x in r["discrete_mismatches"][:10]:
                print(f"- discrete: {x}")
            for x in r["metric_mismatches"][:10]:
                print(f"- metric: {x}")
            for x in r["unpaired_left"][:5]:
                print(f"- only in {r['left']}: {x}")
            for x in r["unpaired_right"][:5]:
                print(f"- only in {r['right']}: {x}")

    if args.json:
        args.json.write_text(json.dumps(results, indent=2))

    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
