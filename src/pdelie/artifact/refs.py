"""v0.36b: artifact identity and run lineage records.

Three frozen dataclasses that answer three different questions:

``ArtifactRef``
    *What is this bytes-blob and where did it come from?* The ``artifact_id`` is
    the SHA-256 of the content, so identity is content, not location. Two runs
    that produce the same bytes produce the same ref.

``StageRecord``
    *What did this pipeline stage consume and produce?* Carries
    ``parent_stage_ids``, which is what makes an artifact traceable backwards --
    the v0.36a-β exit gate that every stage be reachable through its parents.

``RunManifest``
    *What happened in this run?* An ordered set of stage records plus the run's
    own identity.

Identity, not ``__hash__``
==========================

These are frozen dataclasses carrying ``Mapping`` fields, which makes them
unhashable -- ``dataclass(frozen=True)`` generates a ``__hash__`` that hashes
the field tuple, and a dict inside that tuple raises ``TypeError``. Rather than
fight it with ``field(hash=False)`` gymnastics, each type exposes
:meth:`identity`, a canonical string suitable as dict-key material.
``ArtifactRef.artifact_id`` *is* its identity; the others derive one.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pdelie.artifact.semantic_hash import semantic_hash
from pdelie.errors import ScopeValidationError

__all__ = [
    "ArtifactRef",
    "JSONValue",
    "RunManifest",
    "StageRecord",
]

#: Values permitted inside an artifact's metadata. Deliberately narrow: these
#: records are serialized with ``allow_nan=False`` and compared across
#: processes, so anything that is not strict JSON does not belong here.
JSONValue = None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]

_SHA256_LENGTH = 64


def _require_nonempty_string(value: object, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScopeValidationError(f"{name} must be a non-empty string.")
    return value


def _require_strict_json_mapping(value: object, *, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ScopeValidationError(f"{name} must be a mapping.")
    mapping = dict(value)
    for key in mapping:
        if not isinstance(key, str):
            raise ScopeValidationError(f"{name} keys must be strings; got {key!r}.")
    try:
        semantic_hash(mapping)
    except (TypeError, ValueError) as exc:
        raise ScopeValidationError(
            f"{name} must be strict-JSON with no NaN or Infinity: {exc}"
        ) from exc
    return mapping


@dataclass(frozen=True)
class ArtifactRef:
    """A content-addressed reference to a stored artifact.

    ``artifact_id`` is the SHA-256 hex digest of the content itself. It is not
    assigned, it is *computed* -- which is what makes two runs that produce
    identical bytes produce an identical ref, across machines and processes.
    """

    artifact_id: str
    artifact_kind: str
    schema_version: str
    producer_stage_id: str
    byte_count: int
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        artifact_id = _require_nonempty_string(self.artifact_id, name="artifact_id")
        if len(artifact_id) != _SHA256_LENGTH or not all(
            char in "0123456789abcdef" for char in artifact_id
        ):
            raise ScopeValidationError(
                f"artifact_id must be a 64-character lowercase SHA-256 hex digest; "
                f"got {artifact_id!r}. Identity is the content hash, not a name."
            )
        _require_nonempty_string(self.artifact_kind, name="artifact_kind")
        _require_nonempty_string(self.schema_version, name="schema_version")
        _require_nonempty_string(self.producer_stage_id, name="producer_stage_id")
        if isinstance(self.byte_count, bool) or not isinstance(self.byte_count, int):
            raise ScopeValidationError("byte_count must be an integer.")
        if self.byte_count < 0:
            raise ScopeValidationError("byte_count must be non-negative.")
        object.__setattr__(
            self, "metadata", _require_strict_json_mapping(self.metadata, name="metadata")
        )

    def identity(self) -> str:
        """Canonical key material. For an artifact, that is its content hash."""
        return self.artifact_id

    def as_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_kind": self.artifact_kind,
            "schema_version": self.schema_version,
            "producer_stage_id": self.producer_stage_id,
            "byte_count": self.byte_count,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class StageRecord:
    """One pipeline stage: what it consumed, what it produced, what preceded it."""

    stage_id: str
    stage_kind: str
    parent_stage_ids: tuple[str, ...] = ()
    input_artifact_ids: tuple[str, ...] = ()
    output_artifact_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty_string(self.stage_id, name="stage_id")
        _require_nonempty_string(self.stage_kind, name="stage_kind")
        for name in ("parent_stage_ids", "input_artifact_ids", "output_artifact_ids"):
            values = getattr(self, name)
            if isinstance(values, str) or not isinstance(values, Sequence):
                raise ScopeValidationError(f"{name} must be a sequence of strings.")
            normalized = tuple(str(value) for value in values)
            if len(set(normalized)) != len(normalized):
                raise ScopeValidationError(f"{name} must not repeat an entry.")
            object.__setattr__(self, name, normalized)
        if self.stage_id in self.parent_stage_ids:
            raise ScopeValidationError(
                f"stage {self.stage_id!r} cannot be its own parent."
            )
        object.__setattr__(
            self, "metadata", _require_strict_json_mapping(self.metadata, name="metadata")
        )

    def identity(self) -> str:
        return semantic_hash(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "stage_kind": self.stage_kind,
            "parent_stage_ids": list(self.parent_stage_ids),
            "input_artifact_ids": list(self.input_artifact_ids),
            "output_artifact_ids": list(self.output_artifact_ids),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class RunManifest:
    """Every stage of one run, in order.

    Validates that the stage graph is internally consistent: no duplicate stage
    ids, and every declared parent exists in the same manifest. A manifest whose
    parents dangle cannot satisfy the traceability gate, so it is refused at
    construction rather than at report time.
    """

    run_id: str
    stage_records: tuple[StageRecord, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_nonempty_string(self.run_id, name="run_id")
        records = tuple(self.stage_records)
        for record in records:
            if not isinstance(record, StageRecord):
                raise ScopeValidationError(
                    "stage_records must contain StageRecord instances."
                )
        stage_ids = [record.stage_id for record in records]
        duplicates = {value for value in stage_ids if stage_ids.count(value) > 1}
        if duplicates:
            raise ScopeValidationError(
                f"stage_records repeat stage ids: {sorted(duplicates)}."
            )
        known = set(stage_ids)
        dangling = sorted(
            {
                parent
                for record in records
                for parent in record.parent_stage_ids
                if parent not in known
            }
        )
        if dangling:
            raise ScopeValidationError(
                f"stage_records declare parents that are not in this manifest: "
                f"{dangling}. A dangling parent cannot be traced."
            )
        object.__setattr__(self, "stage_records", records)
        object.__setattr__(
            self, "metadata", _require_strict_json_mapping(self.metadata, name="metadata")
        )

    def identity(self) -> str:
        return semantic_hash(self.as_dict())

    def stage(self, stage_id: str) -> StageRecord:
        for record in self.stage_records:
            if record.stage_id == stage_id:
                return record
        raise ScopeValidationError(f"no stage {stage_id!r} in run {self.run_id!r}.")

    def ancestors(self, stage_id: str) -> tuple[str, ...]:
        """Every stage reachable backwards from ``stage_id``, deepest last.

        This is the traceability gate in executable form: a stage whose ancestry
        cannot be walked is not traceable, whatever the report says.
        """
        seen: list[str] = []
        frontier = [stage_id]
        while frontier:
            current = frontier.pop()
            for parent in self.stage(current).parent_stage_ids:
                if parent not in seen:
                    seen.append(parent)
                    frontier.append(parent)
        return tuple(seen)

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "stage_records": [record.as_dict() for record in self.stage_records],
            "metadata": dict(self.metadata),
        }


def content_artifact_id(content: bytes) -> str:
    """The artifact id for a bytes blob: its SHA-256 hex digest."""
    if not isinstance(content, (bytes, bytearray)):
        raise ScopeValidationError("content must be bytes.")
    return hashlib.sha256(bytes(content)).hexdigest()
