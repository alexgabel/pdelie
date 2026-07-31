"""v0.36 day-zero: the mypy baseline fingerprint file and its rename policy.

``typecheck`` is advisory, and the standing error count has been held at
delta-zero by reviewer habit across five release closes. Habit is not a control.
The baseline turns the count into an artifact that can be ratcheted, and this
file asserts the artifact is well-formed and that the rename rule is exactly
what it claims.

The rename rule matters because a module path is part of a fingerprint: moving
``summaries.py`` would otherwise orphan forty entries and read as forty new
errors.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO_ROOT / "configs/mypy_baseline.v0_36.json"

REQUIRED_KEYS = {
    "checker",
    "pin",
    "pin_rationale",
    "baseline_error_count",
    "fingerprints",
    "renames",
    "rename_policy",
}


def load_baseline() -> dict[str, Any]:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def fingerprint_key(entry: dict[str, Any]) -> tuple[str, str, str]:
    return (entry["module"], entry["code"], entry["line_agnostic_message"])


def inherits(old: dict[str, Any], new: dict[str, Any]) -> bool:
    """The frozen rename rule.

    A renamed module inherits a fingerprint **if and only if** the error code
    and the line-agnostic message both match. The module path deliberately does
    not participate: that is the thing being renamed.
    """
    return (
        old["code"] == new["code"]
        and old["line_agnostic_message"] == new["line_agnostic_message"]
    )


def test_baseline_file_exists_and_has_the_required_shape() -> None:
    baseline = load_baseline()
    assert REQUIRED_KEYS <= set(baseline), (
        f"missing keys: {sorted(REQUIRED_KEYS - set(baseline))}"
    )
    assert baseline["checker"] == "mypy"
    assert isinstance(baseline["fingerprints"], list)
    assert isinstance(baseline["renames"], list)


def test_baseline_count_matches_the_fingerprint_list() -> None:
    baseline = load_baseline()
    assert baseline["baseline_error_count"] == len(baseline["fingerprints"])


def test_baseline_is_pinned_to_the_version_the_project_pins() -> None:
    """The count is only meaningful under the checker that produced it.

    Measured: mypy 2.3.0 reports 147 errors on this tree; ``mypy~=1.11``
    resolves to 1.20.2 and reports 148 plus an unused-section config warning.
    A baseline pinned to a different line than pyproject would disagree with
    its own ratchet on day one.
    """
    import tomllib

    baseline = load_baseline()
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    test_extra = config["project"]["optional-dependencies"]["test"]
    mypy_pin = next(dep for dep in test_extra if dep.lower().startswith("mypy"))

    assert baseline["pin"] == "2.3.x", baseline["pin"]
    assert mypy_pin == "mypy~=2.3.0", mypy_pin
    assert baseline["pin_rationale"].strip()


def test_every_fingerprint_is_complete_and_line_agnostic() -> None:
    baseline = load_baseline()
    for entry in baseline["fingerprints"]:
        assert set(entry) == {"module", "code", "line_agnostic_message"}, entry
        assert entry["module"].startswith("src/pdelie/"), entry
        assert entry["code"], entry
        assert entry["line_agnostic_message"].strip(), entry
        assert "line" not in entry, "fingerprints must not carry line numbers"


def test_fingerprints_are_stable_under_json_round_trip() -> None:
    baseline = load_baseline()
    encoded = json.dumps(baseline, allow_nan=False)
    assert json.loads(encoded) == baseline
    assert "NaN" not in encoded and "Infinity" not in encoded


def test_rename_policy_inherits_only_on_code_and_message_match() -> None:
    original = {
        "module": "src/pdelie/reporting/summaries.py",
        "code": "no-any-return",
        "line_agnostic_message": "Returning Any from function declared to return \"dict[str, Any]\"",
    }
    renamed_same = {**original, "module": "src/pdelie/reporting/_summaries.py"}
    different_code = {**renamed_same, "code": "arg-type"}
    different_message = {**renamed_same, "line_agnostic_message": "Something else entirely"}

    assert inherits(original, renamed_same) is True
    assert inherits(original, different_code) is False
    assert inherits(original, different_message) is False


def test_rename_policy_does_not_let_a_new_error_inherit() -> None:
    """The rule must not absorb a genuinely new error under an old entry.

    The novel entry reuses an error *code* that the baseline already contains --
    ``unreachable`` is present 1+ times -- so this exercises the case that
    actually matters: a code collision alone must not be enough to inherit.
    """
    baseline = load_baseline()
    existing = baseline["fingerprints"][0]
    novel = {
        "module": existing["module"],
        "code": existing["code"],
        "line_agnostic_message": "SENTINEL: a message that does not occur in the baseline",
    }
    assert any(entry["code"] == novel["code"] for entry in baseline["fingerprints"]), (
        "the novel entry must reuse an existing code for this test to be meaningful"
    )
    assert not any(
        entry["line_agnostic_message"] == novel["line_agnostic_message"]
        for entry in baseline["fingerprints"]
    )
    assert not any(inherits(entry, novel) for entry in baseline["fingerprints"])


def test_declared_renames_satisfy_the_policy() -> None:
    """``renames`` is empty today; the rule is enforced for whenever it is not."""
    baseline = load_baseline()
    by_key = {fingerprint_key(entry): entry for entry in baseline["fingerprints"]}
    for rename in baseline["renames"]:
        assert {"from", "to"} <= set(rename), rename
        source, target = rename["from"], rename["to"]
        assert inherits(source, target), (
            f"declared rename does not satisfy the inheritance rule: {rename}"
        )
        assert fingerprint_key(target) in by_key or fingerprint_key(source) in by_key


def test_baseline_concentration_matches_the_known_debt_map() -> None:
    """Sanity check that the baseline describes this repo and not a stale tree."""
    baseline = load_baseline()
    counts: dict[str, int] = {}
    for entry in baseline["fingerprints"]:
        counts[entry["module"]] = counts.get(entry["module"], 0) + 1
    assert counts["src/pdelie/reporting/summaries.py"] == 40
    assert counts["src/pdelie/data/xarray_adapter.py"] == 19
    assert sum(counts.values()) == 147
