"""v0.36b: content-addressed artifact stores.

Two implementations of one protocol. Both are **per-run**; neither is a cache,
neither persists across runs, and neither uses a global directory.

Why per-run, emphatically
=========================

A global artifact directory is a correctness hazard disguised as a convenience.
Content addressing means two different runs that produce identical bytes share
an id -- which is the desired property *within* a run and a silent cross-run
coupling *between* them. A stale artifact from a prior run, retrieved because
its hash matched, would make a comparison report agreement that the current run
never actually produced.

So :class:`ContentAddressedFileStore` roots itself at
``{root}/.pdelie_artifacts/run_{run_id}/`` and :meth:`cleanup` removes exactly
that directory. Sharing across processes is deliberately out of scope until
v0.36a-β, which needs it and will state the sharing rule explicitly.
"""

from __future__ import annotations

import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pdelie.artifact.refs import ArtifactRef, content_artifact_id
from pdelie.errors import ScopeValidationError

__all__ = [
    "ARTIFACT_ROOT_DIRECTORY_NAME",
    "ArtifactStore",
    "ContentAddressedFileStore",
    "MemoryArtifactStore",
]

#: Directory created beneath the caller-supplied root. Named so a stray
#: directory in a working tree is obviously ours and obviously disposable.
ARTIFACT_ROOT_DIRECTORY_NAME = ".pdelie_artifacts"

#: How many leading hex characters become the shard directory. Two gives 256
#: shards, which keeps any single directory small without deep nesting.
_SHARD_PREFIX_LENGTH = 2


@runtime_checkable
class ArtifactStore(Protocol):
    """The storage contract. Bytes in, :class:`ArtifactRef` out."""

    def put_bytes(
        self,
        content: bytes,
        *,
        artifact_kind: str,
        schema_version: str,
        producer_stage_id: str,
    ) -> ArtifactRef: ...

    def get_bytes(self, artifact_id: str) -> bytes: ...

    def exists(self, artifact_id: str) -> bool: ...


def _validated_content(content: object) -> bytes:
    if not isinstance(content, (bytes, bytearray)):
        raise ScopeValidationError(
            "content must be bytes. Serialize before storing so the stored bytes "
            "are exactly what the artifact id describes."
        )
    return bytes(content)


def _build_ref(
    content: bytes,
    *,
    artifact_kind: str,
    schema_version: str,
    producer_stage_id: str,
    metadata: Mapping[str, Any] | None = None,
) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=content_artifact_id(content),
        artifact_kind=artifact_kind,
        schema_version=schema_version,
        producer_stage_id=producer_stage_id,
        byte_count=len(content),
        metadata=dict(metadata or {}),
    )


class MemoryArtifactStore:
    """In-process store. One instance per run; nothing survives it."""

    def __init__(self) -> None:
        self._blobs: dict[str, bytes] = {}
        self._refs: dict[str, ArtifactRef] = {}

    def put_bytes(
        self,
        content: bytes,
        *,
        artifact_kind: str,
        schema_version: str,
        producer_stage_id: str,
    ) -> ArtifactRef:
        payload = _validated_content(content)
        ref = _build_ref(
            payload,
            artifact_kind=artifact_kind,
            schema_version=schema_version,
            producer_stage_id=producer_stage_id,
        )
        # Content addressing makes re-putting identical bytes a no-op by
        # construction; the first ref wins so producer provenance is stable.
        self._blobs.setdefault(ref.artifact_id, payload)
        self._refs.setdefault(ref.artifact_id, ref)
        return self._refs[ref.artifact_id]

    def get_bytes(self, artifact_id: str) -> bytes:
        try:
            return self._blobs[artifact_id]
        except KeyError:
            raise ScopeValidationError(
                f"no artifact {artifact_id!r} in this store."
            ) from None

    def exists(self, artifact_id: str) -> bool:
        return artifact_id in self._blobs

    def ref(self, artifact_id: str) -> ArtifactRef:
        try:
            return self._refs[artifact_id]
        except KeyError:
            raise ScopeValidationError(
                f"no artifact {artifact_id!r} in this store."
            ) from None

    def artifact_count(self) -> int:
        return len(self._blobs)

    def cleanup(self) -> None:
        self._blobs.clear()
        self._refs.clear()


class ContentAddressedFileStore:
    """On-disk store rooted at a per-run directory.

    Writes ``{root}/.pdelie_artifacts/run_{run_id}/{ab}/{full_sha256}``. The
    same content written twice produces one file, because the path *is* the
    hash.
    """

    def __init__(self, root_dir: Path | str, *, run_id: str) -> None:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ScopeValidationError("run_id must be a non-empty string.")
        if "/" in run_id or "\\" in run_id or run_id in (".", ".."):
            raise ScopeValidationError(
                f"run_id {run_id!r} must be a plain name, not a path fragment."
            )
        self._run_id = run_id
        self._root = Path(root_dir) / ARTIFACT_ROOT_DIRECTORY_NAME / f"run_{run_id}"
        self._root.mkdir(parents=True, exist_ok=True)
        self._refs: dict[str, ArtifactRef] = {}

    @property
    def root(self) -> Path:
        return self._root

    @property
    def run_id(self) -> str:
        return self._run_id

    def _path_for(self, artifact_id: str) -> Path:
        return self._root / artifact_id[:_SHARD_PREFIX_LENGTH] / artifact_id

    def put_bytes(
        self,
        content: bytes,
        *,
        artifact_kind: str,
        schema_version: str,
        producer_stage_id: str,
    ) -> ArtifactRef:
        payload = _validated_content(content)
        ref = _build_ref(
            payload,
            artifact_kind=artifact_kind,
            schema_version=schema_version,
            producer_stage_id=producer_stage_id,
        )
        path = self._path_for(ref.artifact_id)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        self._refs.setdefault(ref.artifact_id, ref)
        return self._refs[ref.artifact_id]

    def get_bytes(self, artifact_id: str) -> bytes:
        path = self._path_for(artifact_id)
        if not path.is_file():
            raise ScopeValidationError(
                f"no artifact {artifact_id!r} under {self._root}."
            )
        content = path.read_bytes()
        observed = content_artifact_id(content)
        if observed != artifact_id:
            raise ScopeValidationError(
                f"artifact {artifact_id!r} hashes to {observed[:16]}... on read. "
                f"The stored bytes have changed since they were written."
            )
        return content

    def exists(self, artifact_id: str) -> bool:
        return self._path_for(artifact_id).is_file()

    def ref(self, artifact_id: str) -> ArtifactRef:
        try:
            return self._refs[artifact_id]
        except KeyError:
            raise ScopeValidationError(
                f"no ref for {artifact_id!r} in this store instance."
            ) from None

    def artifact_count(self) -> int:
        return sum(1 for path in self._root.rglob("*") if path.is_file())

    def cleanup(self) -> None:
        """Remove this run's directory. Never touches a sibling run."""
        if self._root.exists():
            shutil.rmtree(self._root)
        self._refs.clear()
