"""v0.36b: MemoryArtifactStore and ContentAddressedFileStore."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from pdelie.artifact import (
    ARTIFACT_ROOT_DIRECTORY_NAME,
    ArtifactStore,
    ContentAddressedFileStore,
    MemoryArtifactStore,
)
from pdelie.errors import ScopeValidationError

PUT_KWARGS = {
    "artifact_kind": "design_matrix",
    "schema_version": "0.1",
    "producer_stage_id": "design_matrix_x",
}


def stores(tmp_path: Path) -> list[object]:
    return [
        MemoryArtifactStore(),
        ContentAddressedFileStore(tmp_path, run_id="run1"),
    ]


def test_both_stores_satisfy_the_protocol(tmp_path: Path) -> None:
    for store in stores(tmp_path):
        assert isinstance(store, ArtifactStore)


def test_artifact_id_is_the_sha256_of_the_content(tmp_path: Path) -> None:
    """The b-gate: put_bytes(content).artifact_id == sha256(content).hexdigest()."""
    content = b"the exact bytes"
    expected = hashlib.sha256(content).hexdigest()
    for store in stores(tmp_path):
        assert store.put_bytes(content, **PUT_KWARGS).artifact_id == expected


def test_round_trip_returns_the_same_bytes(tmp_path: Path) -> None:
    content = b"round trip"
    for store in stores(tmp_path):
        ref = store.put_bytes(content, **PUT_KWARGS)
        assert store.get_bytes(ref.artifact_id) == content
        assert store.exists(ref.artifact_id)


def test_putting_identical_content_twice_is_idempotent(tmp_path: Path) -> None:
    content = b"same bytes"
    for store in stores(tmp_path):
        first = store.put_bytes(content, **PUT_KWARGS)
        second = store.put_bytes(content, **PUT_KWARGS)
        assert first.artifact_id == second.artifact_id
        assert store.artifact_count() == 1


def test_file_store_writes_one_file_per_distinct_content(tmp_path: Path) -> None:
    store = ContentAddressedFileStore(tmp_path, run_id="run1")
    store.put_bytes(b"a", **PUT_KWARGS)
    store.put_bytes(b"a", **PUT_KWARGS)
    store.put_bytes(b"b", **PUT_KWARGS)
    assert store.artifact_count() == 2


def test_missing_artifact_is_refused(tmp_path: Path) -> None:
    for store in stores(tmp_path):
        with pytest.raises(ScopeValidationError, match="no artifact"):
            store.get_bytes("0" * 64)
        assert store.exists("0" * 64) is False


def test_non_bytes_content_is_refused(tmp_path: Path) -> None:
    for store in stores(tmp_path):
        with pytest.raises(ScopeValidationError, match="content must be bytes"):
            store.put_bytes("a string", **PUT_KWARGS)  # type: ignore[arg-type]


def test_file_store_is_rooted_per_run_and_never_global(tmp_path: Path) -> None:
    """A global directory would silently couple two runs through content addressing."""
    first = ContentAddressedFileStore(tmp_path, run_id="run1")
    second = ContentAddressedFileStore(tmp_path, run_id="run2")
    assert first.root != second.root
    assert first.root.parent.name == ARTIFACT_ROOT_DIRECTORY_NAME
    assert first.root.name == "run_run1"

    ref = first.put_bytes(b"only in run1", **PUT_KWARGS)
    assert second.exists(ref.artifact_id) is False


def test_cleanup_removes_only_its_own_run(tmp_path: Path) -> None:
    first = ContentAddressedFileStore(tmp_path, run_id="run1")
    second = ContentAddressedFileStore(tmp_path, run_id="run2")
    first.put_bytes(b"x", **PUT_KWARGS)
    kept = second.put_bytes(b"y", **PUT_KWARGS)

    first.cleanup()
    assert not first.root.exists()
    assert second.root.exists()
    assert second.get_bytes(kept.artifact_id) == b"y"


def test_file_store_detects_tampering_on_read(tmp_path: Path) -> None:
    store = ContentAddressedFileStore(tmp_path, run_id="run1")
    ref = store.put_bytes(b"original", **PUT_KWARGS)
    path = store.root / ref.artifact_id[:2] / ref.artifact_id
    path.write_bytes(b"tampered")
    with pytest.raises(ScopeValidationError, match="have changed since"):
        store.get_bytes(ref.artifact_id)


def test_run_id_must_not_be_a_path_fragment(tmp_path: Path) -> None:
    for bad in ("..", "a/b", "  ", ""):
        with pytest.raises(ScopeValidationError):
            ContentAddressedFileStore(tmp_path, run_id=bad)


def test_memory_store_cleanup_empties_it(tmp_path: Path) -> None:
    store = MemoryArtifactStore()
    ref = store.put_bytes(b"x", **PUT_KWARGS)
    assert store.ref(ref.artifact_id).artifact_kind == "design_matrix"
    store.cleanup()
    assert store.artifact_count() == 0
    with pytest.raises(ScopeValidationError):
        store.ref(ref.artifact_id)
