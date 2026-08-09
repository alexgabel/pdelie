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
import re
from pathlib import Path
from typing import Any


def _scope() -> dict:
    """The single source of scope, shared with replay_workloads.py.

    Neither script keeps its own list. Run 31278210299 failed to close Gate F
    partly because the harness swept derivative order 4 on its own authority,
    against a bound the v0.38b freeze explicitly declines to make.
    """
    path = Path(__file__).resolve().parents[1] / "configs/gate_f_replay_scope.json"
    return json.loads(path.read_text())


SCOPE = _scope()


def _expected() -> dict:
    """The reviewed row population. F-3 asserts equality against this set."""
    path = Path(__file__).resolve().parents[1] / "configs/gate_f_expected_rows.json"
    return json.loads(path.read_text())


EXPECTED = _expected()
EXPECTED_KEYS = {(r["workload"], r["row_key"]) for r in EXPECTED["rows"]}
EXPECTED_GATE_KEYS = {
    (r["workload"], r["row_key"])
    for r in EXPECTED["rows"]
    if r["gate_use"] == "gate_evidence"
}

#: Declared per workload family in the scope artifact. A gate row may carry
#: ``derivative_order: null`` only if its family is listed here.
NON_ORDER_FAMILIES = set(SCOPE["non_order_parameterized_families"])

_ROW_ID_ORDER = re.compile(r"_d(\d+)$")


def parse_row_id_for_audit(row_id: str) -> int | None:
    """Recover the order a row key *displays*, to audit it against the typed value.

    Never a source. The comparator reads ``derivative_order`` from the row; this
    only checks the two agree, catching a formatting bug rather than supplying
    semantics. Duplicated from ``replay_contracts`` deliberately: the comparator
    must not import the generator, so that an error common to both cannot cancel
    itself out.
    """
    match = _ROW_ID_ORDER.search(row_id)
    return int(match.group(1)) if match else None


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


def structural_checks(runners: dict[str, dict]) -> list[str]:
    """Fail before comparing numbers if the populations are not what was frozen.

    A comparison over the wrong rows produces a number, and a number is what a
    reader trusts. These run first.
    """
    problems: list[str] = []
    frozen_workloads = set(SCOPE["workload_ids"])
    classes = SCOPE["portability_classes"]
    key_sets: dict[str, set] = {}

    for label, payload in runners.items():
        rows = payload["rows"]

        # Artifacts produced before the scope contract carry no gate_use or
        # derivative_order. Treating their rows as gate evidence by default is
        # exactly the defect this contract exists to prevent, so it is refused
        # rather than defaulted -- an unlabelled row cannot be shown to be in
        # scope, and "cannot be shown" is not "is".
        unlabelled = [r for r in rows if "gate_use" not in r or "scope" not in r]
        if unlabelled:
            problems.append(
                f"{label}: {len(unlabelled)} row(s) carry no scope label, so this "
                f"artifact predates configs/gate_f_replay_scope.json. It cannot be "
                f"used for a gate decision; re-run the lane with the current "
                f"harness. (e.g. {unlabelled[0]['workload']}/{unlabelled[0]['row_key']})"
            )
            continue

        keys = [(r["workload"], r["row_key"]) for r in rows]
        duplicates = sorted({k for k in keys if keys.count(k) > 1})
        if duplicates:
            problems.append(f"{label}: duplicate row keys {duplicates[:5]}")
        key_sets[label] = set(keys)

        seen = {r["workload"] for r in rows}
        missing = sorted(frozen_workloads - seen)
        if missing:
            problems.append(f"{label}: frozen workloads absent {missing}")
        extra = sorted(seen - frozen_workloads)
        if extra:
            problems.append(f"{label}: workloads not in the frozen scope {extra}")

        for r in rows:
            cls = r.get("portability_class")
            if cls not in ("exact_discrete", "tolerance_numeric",
                           "platform_specific_diagnostic"):
                problems.append(f"{label}: unknown portability class {cls!r} "
                                f"on {r['workload']}/{r['row_key']}")
                break
            if classes.get(r["workload"]) not in (None, cls):
                problems.append(f"{label}: {r['workload']} declares {cls!r}, "
                                f"scope says {classes[r['workload']]!r}")
                break

        # F-3: exact set equality against the reviewed manifest. Not a count.
        # A count check passes on the wrong 229 rows, and the population that
        # broke run 31326189317 had the right total (286) throughout.
        emitted = {(r["workload"], r["row_key"]) for r in rows}
        if emitted != EXPECTED_KEYS:
            missing = sorted(EXPECTED_KEYS - emitted)
            unexpected = sorted(emitted - EXPECTED_KEYS)
            problems.append(
                f"{label}: row population differs from the frozen manifest "
                f"({len(missing)} missing, {len(unexpected)} unexpected). "
                f"missing e.g. {missing[:3]}; unexpected e.g. {unexpected[:3]}"
            )

        # F-3a: the gate/exploratory partition must equal the frozen partition.
        # Same total, different split, is exactly the failure being corrected.
        emitted_gate = {
            (r["workload"], r["row_key"]) for r in rows
            if r.get("gate_use") == "gate_evidence"
        }
        if emitted_gate != EXPECTED_GATE_KEYS:
            wrongly_gate = sorted(emitted_gate - EXPECTED_GATE_KEYS)
            wrongly_expl = sorted(EXPECTED_GATE_KEYS - emitted_gate)
            problems.append(
                f"{label}: gate/exploratory partition differs from the frozen "
                f"partition. {len(wrongly_gate)} row(s) claim gate evidence but "
                f"are frozen exploratory (e.g. {wrongly_gate[:3]}); "
                f"{len(wrongly_expl)} the reverse (e.g. {wrongly_expl[:3]})"
            )

        for r in rows:
            if r.get("gate_use") != "gate_evidence":
                continue
            order = r.get("derivative_order")

            # F-4a first. A row whose order is None is in scope only because a
            # DECLARED non-order-parameterised family permits it -- never because
            # the value is absent and the check cannot tell. Treating None as
            # in-scope by default is how F-4 passed vacuously over ten d=4 rows.
            if order is None:
                family = r.get("workload_family")
                if family is None:
                    problems.append(
                        f"{label}: {r['workload']}/{r['row_key']} is gate evidence "
                        f"with no derivative_order and no workload_family, so its "
                        f"scope cannot be established. Refused, not defaulted."
                    )
                    break
                if family not in NON_ORDER_FAMILIES:
                    problems.append(
                        f"{label}: {r['workload']}/{r['row_key']} is gate evidence "
                        f"with derivative_order null, but family {family!r} IS "
                        f"order-parameterised. This is the exact defect that put "
                        f"ten d=4 rows into run 31326189317's gate population."
                    )
                    break
                continue

            # F-4: an order that is present must be in the frozen scope.
            if order not in SCOPE["supported_derivative_orders"]:
                problems.append(
                    f"{label}: {r['workload']}/{r['row_key']} is gate evidence "
                    f"at derivative order {order}, outside the frozen scope "
                    f"{SCOPE['supported_derivative_orders']}"
                )
                break

            # The displayed key must agree with the typed value. This catches a
            # formatting bug; it never supplies the order.
            displayed = parse_row_id_for_audit(r["row_key"])
            if displayed is not None and displayed != order:
                problems.append(
                    f"{label}: {r['workload']}/{r['row_key']} displays derivative "
                    f"order {displayed} but carries {order}"
                )
                break

    labels = sorted(key_sets)
    for i, left in enumerate(labels):
        for right in labels[i + 1:]:
            if key_sets[left] != key_sets[right]:
                only_l = sorted(key_sets[left] - key_sets[right])[:3]
                only_r = sorted(key_sets[right] - key_sets[left])[:3]
                problems.append(
                    f"row-key populations differ: {left} vs {right}; "
                    f"only-left {only_l}, only-right {only_r}"
                )
    return problems


def compare(left_label: str, left: dict, right_label: str, right: dict) -> dict[str, Any]:
    a, b = _index(left), _index(right)
    # GATE ROWS ONLY. Exploratory rows are emitted and labelled by the harness;
    # including them here is what produced the 2.478e-01 headline from d=4.
    keys = sorted(
        k for k in set(a) & set(b)
        if a[k].get("gate_use", "gate_evidence") == "gate_evidence"
    )
    only_left = sorted(set(a) - set(b))
    only_right = sorted(set(b) - set(a))

    discrete_mismatch: list[str] = []
    metric_mismatch: list[str] = []
    worst_rel = 0.0
    worst_key: str | None = None
    worst_scaled = 0.0
    worst_scaled_key: str | None = None
    # Six independent counters. The previous three conflated "was compared"
    # with "was comparable under a relative statistic", so a row could be
    # excluded from the bitwise denominator by a classification unrelated to
    # whether its bits were equal.
    numeric_comparisons_total = 0
    numeric_comparisons_bitwise_equal = 0
    numeric_comparisons_bitwise_different = 0
    signal_comparisons = 0
    floor_comparisons = 0
    not_comparable = 0
    bitwise_differences: list[str] = []

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

        for field in _NUMERIC_FIELDS:
            x, y = ra.get(field), rb.get(field)
            if x is None or y is None:
                not_comparable += 1
                continue

            # BITWISE ACCOUNTING RUNS FIRST, AND UNCONDITIONALLY.
            #
            # F-6 asks whether two CPython patch releases produced identical
            # bits. That question is well posed at the numerical floor -- more
            # so, in fact, since floor values are the ones a libm change would
            # perturb. The previous ordering classified a comparison as "floor"
            # and skipped it before counting, so F-6's denominator silently
            # excluded exactly the rows most likely to differ, and a bitwise
            # difference there would have been reported as agreement.
            #
            # Floor classification governs which *statistic is meaningful*
            # (absolute, not relative). It has no bearing on whether the bits
            # were compared.
            numeric_comparisons_total += 1
            if x == y:
                numeric_comparisons_bitwise_equal += 1
            else:
                numeric_comparisons_bitwise_different += 1
                bitwise_differences.append(
                    f"{key[0]}/{key[1]}:{field} {x!r} vs {y!r}"
                )

            scale = ra.get("reference_scale") or max(abs(x), abs(y))
            if scale == 0.0:
                not_comparable += 1
                continue
            # Signal versus floor, against the v0.38d boundary. This selects the
            # statistic; the bits above were already accounted for.
            if (
                ra.get("reporting_regime") == "floor"
                or max(abs(x), abs(y)) <= _SQRT_EPS * scale
            ):
                floor_comparisons += 1
                continue
            signal_comparisons += 1
            # PRIMARY: scale-stable. abs difference against the quantity's own
            # reference scale, the definition v0.38d froze.
            scaled = abs(x - y) / scale
            if scaled > worst_scaled:
                worst_scaled, worst_scaled_key = scaled, f"{key[0]}/{key[1]}:{field}"
            # SECONDARY, diagnostic only: unstable near the floor.
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
        "numeric_comparisons_total": numeric_comparisons_total,
        "numeric_comparisons_bitwise_equal": numeric_comparisons_bitwise_equal,
        "numeric_comparisons_bitwise_different": numeric_comparisons_bitwise_different,
        "bitwise_differences": bitwise_differences[:20],
        "signal_comparisons": signal_comparisons,
        "floor_comparisons": floor_comparisons,
        "not_comparable": not_comparable,
        "accounting_identity": (
            "total == bitwise_equal + bitwise_different; "
            "total == signal + floor + not_comparable(post-scale)"
        ),
        # Primary statistic for the gate decision.
        "worst_scaled_difference": worst_scaled,
        "worst_scaled_difference_at": worst_scaled_key,
        "scaled_difference_formula": "abs(left - right) / reference_scale",
        # Secondary. Named with its limitation so it cannot be quoted bare.
        "worst_relative_between_errors": worst_rel,
        "worst_relative_between_errors_at": worst_key,
        "relative_between_errors_labels": [
            "unstable_near_numerical_floor",
            "not_used_for_gate_decision",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    runners = _load(args.directory)
    if len(runners) < 2:
        raise SystemExit(f"need at least two runners, found {sorted(runners)}")

    # Structure before numbers. A comparison over the wrong population still
    # produces a number, and a number is what a reader trusts.
    structural = structural_checks(runners)
    if structural:
        print("### Structural failures\n")
        for problem in structural:
            print(f"- {problem}")
        print("\nNo comparison performed: the populations are not what the "
              "frozen scope declares.")
        raise SystemExit(1)

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
    print("| pair | gate rows | discrete | metric | signal | floor | bitwise | "
          "**worst scaled diff** | rel-between-errors |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in results:
        d = len(r["discrete_mismatches"]) or "—"
        m = len(r["metric_mismatches"]) or "—"
        print(f"| {r['left']} vs {r['right']} | {r['paired_rows']} | {d} | {m} | "
              f"{r['signal_comparisons']} | {r['floor_comparisons']} | "
              f"{r['numeric_comparisons_bitwise_equal']}/{r['numeric_comparisons_total']} | "
              f"**`{r['worst_scaled_difference']:.3e}`** | "
              f"`{r['worst_relative_between_errors']:.3e}` |")
    print("\n*Primary statistic is the scaled difference. "
          "`rel-between-errors` is unstable near the numerical floor and is not "
          "used for the gate decision.*")

    failures = [r for r in results if r["discrete_mismatches"] or r["metric_mismatches"]
                or r["unpaired_left"] or r["unpaired_right"]]

    # The accounting identity, asserted rather than assumed. If these ever
    # disagree the counters have drifted apart again and no number above is
    # trustworthy.
    for r in results:
        total = r["numeric_comparisons_total"]
        assert total == (r["numeric_comparisons_bitwise_equal"]
                         + r["numeric_comparisons_bitwise_different"]), (
            f"bitwise counters do not sum to the total for "
            f"{r['left']} vs {r['right']}"
        )
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
