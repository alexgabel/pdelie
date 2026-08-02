"""v0.38 §5: corrections are additive, and the register cannot be rewritten.

"125 measurements are bitwise identical" says the *numbers* were preserved. It
does not say the old reports remain valid scientific artifacts: their operator
declaration and semantic hash described a different operator. The register keeps
both facts, and keeps them apart.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTER = REPO_ROOT / "docs/specs/artifact_corrections.json"

VALID_CORRECTION_CLASSES = {"specification_only", "measurement_affecting"}
VALID_MEASUREMENT_RELATIONS = {
    "bitwise_identical",
    "within_tolerance",
    "changed",
    "not_applicable",
}
VALID_SUPERSEDED_STATUSES = {
    "invalidated_declaration_mismatch",
    "invalidated_measurement_error",
    "superseded_scope_extension",
}


def _register() -> dict:
    return json.loads(REGISTER.read_text())


def _corrections() -> list[dict]:
    return _register()["corrections"]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_register_exists_and_is_strict_json() -> None:
    assert REGISTER.exists()
    json.dumps(_register(), allow_nan=False)


def test_the_register_declares_itself_append_only() -> None:
    assert _register()["register_policy"]["append_only"] is True


def test_every_correction_has_the_three_status_fields() -> None:
    """The payload shape you cannot infer from prose."""
    for correction in _corrections():
        assert correction["correction_class"] in VALID_CORRECTION_CLASSES
        assert correction["measurement_relation"] in VALID_MEASUREMENT_RELATIONS
        assert isinstance(correction["old_scientific_interpretation_valid"], bool)


def test_bitwise_identical_does_not_imply_the_old_reading_was_valid() -> None:
    """The distinction the whole register exists to preserve.

    A correction whose numbers are unchanged is still a correction if what the
    numbers *meant* changed. Recording only the first fact is how a superseded
    artifact keeps being cited.
    """
    specification_only = [
        c for c in _corrections() if c["correction_class"] == "specification_only"
    ]
    assert specification_only, "no specification-only correction to check"
    for correction in specification_only:
        assert correction["measurement_relation"] == "bitwise_identical"
        assert correction["old_scientific_interpretation_valid"] is False, (
            "a specification-only correction that leaves the old interpretation "
            "valid is not a correction -- it is a no-op, and should not be in "
            "the register"
        )


def test_the_superseded_artifact_is_retained_not_deleted() -> None:
    for correction in _corrections():
        superseded = correction["superseded_artifact"]
        assert superseded["retained"] is True
        assert (REPO_ROOT / superseded["path"]).exists(), (
            f"{superseded['path']} was deleted. A correction whose evidence is "
            f"gone cannot be reviewed."
        )


def test_the_pre_correction_identity_is_preserved() -> None:
    """The identity a reader may already have cited is never overwritten.

    Two hashes are recorded, not one: what the artifact was before the
    correction, and what it is now that the status banner is on it. Keeping only
    the second would break every citation made before the correction; keeping
    only the first would leave the frozen state uncheckable.
    """
    for correction in _corrections():
        superseded = correction["superseded_artifact"]
        before = superseded["sha256_before_correction"]
        after = superseded["sha256_at_invalidation"]
        assert len(before) == 64 and len(after) == 64
        assert before != after, (
            "the pre- and post-correction hashes match, so no banner was "
            "applied and a reader opening the file learns nothing"
        )
        assert superseded["body_edited"] is False


def test_the_superseded_hash_is_not_overwritten() -> None:
    """The post-banner hash is pinned and must keep matching.

    If the superseded document is edited, this fails -- which is the intent.
    Corrections are additive: the banner is prepended once, and after that the
    artifact is frozen. Silently editing it would let a reader believe the old
    record always said what it says now.
    """
    for correction in _corrections():
        superseded = correction["superseded_artifact"]
        path = REPO_ROOT / superseded["path"]
        assert _sha256(path) == superseded["sha256_at_invalidation"], (
            f"{superseded['path']} has changed since correction "
            f"{correction['correction_id']} pinned it. The superseded artifact "
            f"is frozen; add a new correction rather than editing it."
        )


def test_the_superseding_hash_is_pinned() -> None:
    for correction in _corrections():
        superseding = correction["superseding_artifact"]
        path = REPO_ROOT / superseding["path"]
        assert path.exists()
        assert _sha256(path) == superseding["sha256_at_signing"], (
            f"{superseding['path']} has changed since it was signed. A signed "
            f"artifact is amended additively, not edited."
        )


def test_the_superseded_artifact_carries_its_status_banner() -> None:
    """The register and the document must not disagree about the status."""
    for correction in _corrections():
        superseded = correction["superseded_artifact"]
        text = (REPO_ROOT / superseded["path"]).read_text()
        assert superseded["status"] in text, (
            f"{superseded['path']} does not state its status "
            f"{superseded['status']!r}; a reader opening the file directly would "
            f"not learn it was superseded"
        )
        assert superseded["status"] in VALID_SUPERSEDED_STATUSES


def test_the_banner_points_at_the_superseding_artifact() -> None:
    """A status with no forward pointer sends a reader nowhere."""
    for correction in _corrections():
        text = (REPO_ROOT / correction["superseded_artifact"]["path"]).read_text()
        target = Path(correction["superseding_artifact"]["path"]).name
        assert target in text, f"the banner does not name {target}"


def test_changed_and_unchanged_fields_are_disjoint_and_non_empty() -> None:
    """A field cannot be both, and a correction claiming neither says nothing."""
    for correction in _corrections():
        changed = set(correction["changed_fields"])
        unchanged = set(correction["unchanged_fields"])
        assert changed, f"{correction['correction_id']} lists no changed field"
        assert unchanged, f"{correction['correction_id']} lists no unchanged field"
        assert not changed & unchanged, (
            f"{correction['correction_id']} lists {sorted(changed & unchanged)} as "
            f"both changed and unchanged"
        )


def test_the_evidence_counts_are_internally_consistent() -> None:
    for correction in _corrections():
        evidence = correction.get("evidence")
        if not evidence:
            continue
        compared = evidence["measurements_compared"]
        identical = evidence["measurements_bitwise_identical"]
        assert 0 <= identical <= compared
        if correction["measurement_relation"] == "bitwise_identical":
            assert identical == compared, (
                f"{correction['correction_id']} claims bitwise_identical but only "
                f"{identical}/{compared} matched"
            )


def test_correction_ids_are_unique() -> None:
    ids = [c["correction_id"] for c in _corrections()]
    assert len(ids) == len(set(ids))


def test_every_correction_gives_citation_guidance() -> None:
    """A superseded artifact with no instruction keeps getting cited."""
    for correction in _corrections():
        guidance = correction.get("citation_guidance", "")
        assert "superseding" in guidance, (
            f"{correction['correction_id']} does not tell a reader which "
            f"identity to cite"
        )


@pytest.mark.parametrize(
    ("field", "allowed"),
    [
        ("correction_class", VALID_CORRECTION_CLASSES),
        ("measurement_relation", VALID_MEASUREMENT_RELATIONS),
    ],
)
def test_the_vocabularies_are_closed(field: str, allowed: set[str]) -> None:
    for correction in _corrections():
        assert correction[field] in allowed
