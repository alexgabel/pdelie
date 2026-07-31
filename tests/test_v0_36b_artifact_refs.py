"""v0.36b: ArtifactRef, StageRecord, RunManifest."""

from __future__ import annotations

import dataclasses
import json

import pytest

from pdelie.artifact import ArtifactRef, RunManifest, StageRecord, content_artifact_id
from pdelie.errors import ScopeValidationError

VALID_ID = content_artifact_id(b"payload")


def ref(**overrides: object) -> ArtifactRef:
    base = {
        "artifact_id": VALID_ID,
        "artifact_kind": "design_matrix",
        "schema_version": "0.1",
        "producer_stage_id": "design_matrix_x",
        "byte_count": 7,
    }
    base.update(overrides)
    return ArtifactRef(**base)  # type: ignore[arg-type]


def test_artifact_ref_round_trips_through_strict_json() -> None:
    payload = ref().as_dict()
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload


def test_dataclasses_asdict_round_trips() -> None:
    assert dataclasses.asdict(ref())["artifact_id"] == VALID_ID


def test_artifact_id_must_be_a_sha256_digest() -> None:
    for bad in ("not-a-hash", "abc", VALID_ID.upper(), VALID_ID[:-1] + "z"):
        with pytest.raises(ScopeValidationError, match="SHA-256"):
            ref(artifact_id=bad)


def test_artifact_ref_identity_is_the_content_hash() -> None:
    """Identity is content, not a name -- see the module docstring."""
    assert ref().identity() == VALID_ID
    assert content_artifact_id(b"payload") == VALID_ID
    assert content_artifact_id(b"payload") != content_artifact_id(b"payloa")


def test_negative_or_non_integer_byte_count_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="non-negative"):
        ref(byte_count=-1)
    with pytest.raises(ScopeValidationError, match="must be an integer"):
        ref(byte_count=True)


def test_non_strict_json_metadata_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="strict-JSON"):
        ref(metadata={"drift": float("nan")})


def test_stage_record_rejects_self_parenthood_and_duplicates() -> None:
    with pytest.raises(ScopeValidationError, match="its own parent"):
        StageRecord(stage_id="s", stage_kind="mask", parent_stage_ids=("s",))
    with pytest.raises(ScopeValidationError, match="must not repeat"):
        StageRecord(stage_id="s", stage_kind="mask", parent_stage_ids=("p", "p"))


def test_run_manifest_refuses_dangling_parents() -> None:
    """A manifest whose parents dangle cannot satisfy the traceability gate."""
    with pytest.raises(ScopeValidationError, match="not in this manifest"):
        RunManifest(
            run_id="r1",
            stage_records=(
                StageRecord(stage_id="child", stage_kind="matrix", parent_stage_ids=("ghost",)),
            ),
        )


def test_run_manifest_refuses_duplicate_stage_ids() -> None:
    with pytest.raises(ScopeValidationError, match="repeat stage ids"):
        RunManifest(
            run_id="r1",
            stage_records=(
                StageRecord(stage_id="s", stage_kind="mask"),
                StageRecord(stage_id="s", stage_kind="matrix"),
            ),
        )


def test_ancestors_walks_the_full_chain() -> None:
    """Traceability in executable form."""
    manifest = RunManifest(
        run_id="r1",
        stage_records=(
            StageRecord(stage_id="a", stage_kind="field"),
            StageRecord(stage_id="b", stage_kind="mask", parent_stage_ids=("a",)),
            StageRecord(stage_id="c", stage_kind="matrix", parent_stage_ids=("b",)),
        ),
    )
    assert set(manifest.ancestors("c")) == {"a", "b"}
    assert manifest.ancestors("a") == ()
    assert manifest.stage("b").stage_kind == "mask"


def test_unknown_stage_lookup_is_refused() -> None:
    manifest = RunManifest(run_id="r1", stage_records=(StageRecord(stage_id="a", stage_kind="f"),))
    with pytest.raises(ScopeValidationError, match="no stage"):
        manifest.stage("nope")


def test_identities_are_stable_and_distinguish_records() -> None:
    first = StageRecord(stage_id="a", stage_kind="field")
    same = StageRecord(stage_id="a", stage_kind="field")
    other = StageRecord(stage_id="a", stage_kind="mask")
    assert first.identity() == same.identity()
    assert first.identity() != other.identity()


def test_artifact_refs_are_not_exported_from_the_root_namespace() -> None:
    import pdelie

    for name in ("ArtifactRef", "RunManifest", "StageRecord"):
        assert name not in pdelie.__all__
        assert not hasattr(pdelie, name)


def test_blank_required_strings_are_refused() -> None:
    for field in ("artifact_kind", "schema_version", "producer_stage_id"):
        with pytest.raises(ScopeValidationError, match=field):
            ref(**{field: "  "})


def test_non_mapping_or_non_string_keyed_metadata_is_refused() -> None:
    with pytest.raises(ScopeValidationError, match="must be a mapping"):
        ref(metadata=["a"])
    with pytest.raises(ScopeValidationError, match="keys must be strings"):
        ref(metadata={1: "a"})


def test_stage_record_rejects_non_sequence_id_fields() -> None:
    with pytest.raises(ScopeValidationError, match="must be a sequence"):
        StageRecord(stage_id="s", stage_kind="k", parent_stage_ids="not-a-sequence")


def test_run_manifest_rejects_non_stage_record_entries() -> None:
    with pytest.raises(ScopeValidationError, match="StageRecord instances"):
        RunManifest(run_id="r", stage_records=({"stage_id": "s"},))  # type: ignore[arg-type]


def test_content_artifact_id_refuses_non_bytes() -> None:
    with pytest.raises(ScopeValidationError, match="content must be bytes"):
        content_artifact_id("a string")  # type: ignore[arg-type]
