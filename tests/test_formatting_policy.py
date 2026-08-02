"""v0.38: the formatting policy is a rule, not a preference.

``docs/design/FORMATTING_POLICY.md`` says the repository is not formatter-
governed through v0.38, and that `ruff format --check` is added afterwards in a
dedicated mechanical PR. This module keeps the two halves from drifting: the
policy cannot silently stop being true, and CI cannot silently start enforcing
what the policy says it does not.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY = REPO_ROOT / "docs/design/FORMATTING_POLICY.md"


def _workflow_text() -> str:
    workflows = REPO_ROOT / ".github/workflows"
    if not workflows.is_dir():
        return ""
    return "\n".join(path.read_text() for path in sorted(workflows.rglob("*.yml")))


def test_the_policy_document_exists() -> None:
    assert POLICY.exists(), "the formatting policy is the authority for this module"


def test_ci_does_not_yet_gate_on_ruff_format() -> None:
    """The interim rule, asserted against CI rather than trusted.

    If someone adds the gate without doing the mechanical formatting PR first,
    every subsequent branch fails on 206 files of unrelated layout -- which is
    the incident this policy exists because of, inverted.
    """
    assert "ruff format --check" not in _workflow_text(), (
        "CI now gates on `ruff format --check`. That is the intended end state, "
        "but only after the one mechanical formatting-only PR has landed. If it "
        "has, update FORMATTING_POLICY.md and this test together -- the policy "
        "and the gate must not disagree."
    )


def test_ci_still_gates_on_ruff_check() -> None:
    """Lint is a gate now and stays one; only *layout* is ungoverned."""
    assert "ruff check" in _workflow_text(), (
        "`ruff check` is no longer a CI gate. The formatting policy governs "
        "layout only and never licensed dropping lint."
    )


def test_the_policy_names_the_adoption_sequence() -> None:
    """A deferral with no plan is indistinguishable from an omission."""
    text = POLICY.read_text()
    for required in (
        "mechanical formatting-only PR",
        "ruff format --check",
        "not formatter-governed",
    ):
        assert required in text, f"the policy no longer states: {required!r}"


def test_the_policy_records_what_it_cost() -> None:
    """The 206-file number is the argument; without it this reads as taste."""
    assert "206 files" in POLICY.read_text(), (
        "the policy no longer records the incident that motivated it, which is "
        "the only thing distinguishing it from a style preference"
    )
