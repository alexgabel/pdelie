"""The Gate F assurance audit must stay honest about its own status.

The audit exists because a required independent review was not performed: the
author of the fix implemented it and reviewed it, and the missing behavioural
tests were found later by that same author.

An audit document is worthless if it can drift into implying assurance that
nobody granted. These tests hold two properties:

* while unsigned, it must SAY it is unsigned -- prominently, not in a footnote;
* once signed, the verdict must be one of the three declared outcomes, and the
  reviewer and independence statement must both be filled in.

There is deliberately no test asserting the verdict is favourable. That would
make the audit's conclusion a precondition of the suite passing, which is the
same defect one level up.
"""

from __future__ import annotations

import re
from pathlib import Path

AUDIT = Path(__file__).resolve().parents[1] / "docs/audits/V0_38_GATE_F_INDEPENDENT_REVIEW.md"

VERDICTS = (
    "assurance_confirmed",
    "assurance_confirmed_with_non_load_bearing_findings",
    "assurance_not_confirmed",
)

PLACEHOLDER = "*(unsigned)*"


def _text() -> str:
    return AUDIT.read_text(encoding="utf-8")


def _prose() -> str:
    """Markdown emphasis and line wrapping stripped, whitespace collapsed.

    Matching raw markdown is brittle for the same reason parsing a row key is:
    it couples a check to a presentation detail. ``was **not**\nperformed``
    and ``was not performed`` are the same claim.
    """
    # NOT `_`: these documents use `*` for emphasis, and stripping
    # underscores would destroy every snake_case identifier the
    # assertions look for -- `spectral_periodic_uniform` became
    # `spectralperiodicuniform` and eight tests failed for a reason
    # unrelated to the document's content.
    text = re.sub(r"[*`]", "", _text())
    return re.sub(r"\s+", " ", text).lower()


def _verdict_line() -> str:
    match = re.search(r"^\*\*Verdict:\*\*\s*(.+)$", _text(), flags=re.MULTILINE)
    assert match, "the audit has no **Verdict:** line"
    return match.group(1).strip()


def test_the_audit_exists() -> None:
    assert AUDIT.exists(), (
        "the Gate F assurance audit is missing. It was required because the "
        "independent review was not performed; deleting it does not perform it."
    )


def test_an_unsigned_audit_says_so_at_the_top() -> None:
    """Not in a footnote. A reader must not have to hunt for the status."""
    text = _text()
    if _verdict_line() != PLACEHOLDER:
        return  # signed; see the signature tests below
    head = "\n".join(text.splitlines()[:6])
    assert "UNSIGNED" in head, (
        "the audit is unsigned but does not say so in its first six lines"
    )


def test_a_signed_audit_uses_the_declared_vocabulary() -> None:
    verdict = _verdict_line()
    if verdict == PLACEHOLDER:
        return
    assert any(v in verdict for v in VERDICTS), (
        f"verdict {verdict!r} is not one of {list(VERDICTS)}. An invented "
        f"verdict is not a verdict."
    )


def test_a_signed_audit_names_a_reviewer_and_asserts_independence() -> None:
    """A verdict with no attributable reviewer is an unsigned verdict."""
    text = _text()
    if _verdict_line() == PLACEHOLDER:
        return
    reviewer = re.search(r"^\*\*Reviewer:\*\*\s*(.+)$", text, flags=re.MULTILINE)
    assert reviewer and reviewer.group(1).strip() != PLACEHOLDER, (
        "the audit carries a verdict but names no reviewer"
    )
    assert "independence statement" in text.lower()
    assert "*(to be filled by reviewer)*" not in text, (
        "the audit is signed but still carries unfilled reviewer fields"
    )


def test_the_audit_records_that_the_evidence_was_author_produced() -> None:
    """The limitation that makes the document honest must not be edited out."""
    text = _prose()
    assert "was not performed" in text
    assert "author" in text
    assert "not a substitute for the review" in text, (
        "the audit must state that author-produced evidence does not establish "
        "independence; without that line it reads as a completed review"
    )


def test_the_audit_does_not_claim_to_modify_the_release() -> None:
    """It is additive. An audit that rewrites what it reviews is not an audit."""
    text = _text()
    assert "does **not** modify" in text or "does not modify" in text
    for forbidden in ("retag", "re-tag", "amend the tag", "rewrite Appendix"):
        assert forbidden not in text, f"the audit proposes to {forbidden}"


def test_the_control_case_is_present() -> None:
    """Without it, every rejection is consistent with a validator that rejects
    everything -- which is the vacuity failure the audit is about."""
    text = _text()
    assert "control" in text.lower()
    assert "rejects everything" in text
