"""v0.36a-alpha: the stage-bundle interchange format.

A *stage bundle* is one pipeline stage's output, written to disk in a form that
two mutually-incompatible Python environments can exchange. The legacy exporter
runs under Python 3.11 / NumPy 1.26 / PySINDy 1.7.5; the modern one under Python
3.12 / NumPy 2.x / PySINDy 2.1.x. They never import each other, and they never
import a shared serializer -- the legacy side uses the standard library only.

Constraints, each load-bearing
==============================

**No pickle.** Pickle embeds the defining module and class of every object, so a
legacy bundle would carry references to a ``pdelie`` that no longer exists. It is
also arbitrary code execution on load. Arrays are written as ``.npy``; metadata
is written as JSON.

**No object references.** Everything a comparator needs is in ``stage.json`` or
in a ``.npy`` beside it. A bundle is readable by anything that can read JSON and
NumPy's array format, which is the point.

**Content hash per array.** Each entry records the SHA-256 of the bytes on disk,
so a truncated or edited bundle is detected at read time rather than surfacing as
an inexplicable numerical difference three stages later.

**Comparison class travels with the data.** How a stage may be compared is a
property of the stage, not of the code doing the comparing -- see
``docs/design/CROSS_PLATFORM_PORTABILITY_CLASSES.md``. Storing it in the bundle
means the legacy and modern sides cannot disagree about it.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

from pdelie.errors import ScopeValidationError, ShapeValidationError

__all__ = [
    "COMPARISON_CLASSES",
    "STAGE_BUNDLE_SCHEMA_VERSION",
    "StageBundle",
    "read_stage_bundle",
    "write_stage_bundle",
]

STAGE_BUNDLE_SCHEMA_VERSION = "0.1"

ComparisonClass = Literal[
    "exact_discrete",
    "tolerance_numeric",
    "qualitative_invariant",
    "platform_specific_diagnostic",
]

#: The four classes from the portability taxonomy. A bundle declaring anything
#: else is refused at write time.
COMPARISON_CLASSES: tuple[str, ...] = (
    "exact_discrete",
    "tolerance_numeric",
    "qualitative_invariant",
    "platform_specific_diagnostic",
)

#: Provenance keys every bundle must carry. ``source_dirty`` is required by exit
#: gate A-alpha-0: a wheel built from a dirty tree is not the tag it claims to be.
REQUIRED_PROVENANCE_KEYS: tuple[str, ...] = (
    "wheel_sha256",
    "package_version",
    "git_commit",
    "source_dirty",
    "python_version",
    "numpy_version",
)


@dataclass(frozen=True)
class StageBundle:
    """One stage's arrays plus the metadata needed to compare them."""

    stage_id: str
    stage_type: str
    schema_version: str
    comparison_class: str
    parent_stage_ids: tuple[str, ...]
    arrays: Mapping[str, np.ndarray]
    provenance: Mapping[str, Any]

    def array_names(self) -> tuple[str, ...]:
        return tuple(sorted(self.arrays))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validated_stage_id(stage_id: object) -> str:
    if not isinstance(stage_id, str) or not stage_id.strip():
        raise ScopeValidationError("stage_id must be a non-empty string.")
    if "/" in stage_id or "\\" in stage_id or stage_id in (".", ".."):
        raise ScopeValidationError(
            f"stage_id {stage_id!r} must be a plain directory name, not a path."
        )
    return stage_id


def _validated_arrays(arrays: object) -> dict[str, np.ndarray]:
    if not isinstance(arrays, Mapping) or not arrays:
        raise ScopeValidationError("arrays must be a non-empty mapping of name to ndarray.")
    validated: dict[str, np.ndarray] = {}
    for name, value in arrays.items():
        if not isinstance(name, str) or not name.strip():
            raise ScopeValidationError("every array name must be a non-empty string.")
        array = np.asarray(value)
        if array.dtype == object:
            raise ScopeValidationError(
                f"array {name!r} has dtype=object; object arrays pickle on save and "
                f"are refused. Store a concrete numeric, boolean, or string dtype."
            )
        if array.size == 0:
            raise ShapeValidationError(f"array {name!r} is empty.")
        validated[name] = array
    return validated


def _validated_provenance(provenance: object) -> dict[str, Any]:
    if not isinstance(provenance, Mapping):
        raise ScopeValidationError("provenance must be a mapping.")
    missing = [key for key in REQUIRED_PROVENANCE_KEYS if key not in provenance]
    if missing:
        raise ScopeValidationError(
            f"provenance is missing required keys {missing}. Exit gate A-alpha-0 "
            f"requires wheel_sha256, git_commit, and source_dirty for both exporters."
        )
    if not isinstance(provenance["source_dirty"], bool):
        raise ScopeValidationError(
            "provenance['source_dirty'] must be a bool; a wheel built from a dirty "
            "tree is not the tag it claims to be, and 'unknown' is not an answer."
        )
    try:
        json.dumps(dict(provenance), allow_nan=False, sort_keys=True)
    except (TypeError, ValueError) as exc:
        raise ScopeValidationError(f"provenance must be strict-JSON: {exc}") from exc
    return dict(provenance)


def write_stage_bundle(
    directory: Path,
    stage_id: str,
    schema_version: str,
    arrays: Mapping[str, np.ndarray],
    provenance: Mapping[str, Any],
    parent_stage_ids: Sequence[str],
    comparison_class: str,
) -> None:
    """Write one stage bundle to ``directory / stage_id``.

    Arrays are saved with ``allow_pickle=False``. Each is hashed after writing --
    hashing the bytes on disk rather than the in-memory array means the recorded
    digest describes what a reader will actually load.
    """
    stage = _validated_stage_id(stage_id)
    validated_arrays = _validated_arrays(arrays)
    validated_provenance = _validated_provenance(provenance)

    if comparison_class not in COMPARISON_CLASSES:
        raise ScopeValidationError(
            f"comparison_class {comparison_class!r} is not one of {list(COMPARISON_CLASSES)}."
        )
    if not isinstance(schema_version, str) or not schema_version.strip():
        raise ScopeValidationError("schema_version must be a non-empty string.")
    parents = tuple(str(value) for value in parent_stage_ids)
    if len(set(parents)) != len(parents):
        raise ScopeValidationError("parent_stage_ids must not repeat.")
    if stage in parents:
        raise ScopeValidationError(f"stage {stage!r} cannot be its own parent.")

    target = Path(directory) / stage
    target.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    for index, name in enumerate(sorted(validated_arrays)):
        array = validated_arrays[name]
        relative = f"array_{index:03d}.npy"
        path = target / relative
        np.save(path, array, allow_pickle=False)
        entries.append(
            {
                "name": name,
                "path": relative,
                "shape": [int(dim) for dim in array.shape],
                "dtype": str(array.dtype),
                "sha256": _sha256_file(path),
            }
        )

    manifest = {
        "schema_version": schema_version,
        "stage_id": stage,
        # stage_type is descriptive metadata ("mask", "matrix", "metrics"). It
        # travels in provenance because the writer signature is fixed by the
        # v0.36a-alpha specification and does not take it separately.
        "stage_type": str(validated_provenance.get("stage_type", "unspecified")),
        "parent_stage_ids": list(parents),
        "comparison_class": comparison_class,
        "arrays": entries,
        "provenance": validated_provenance,
    }

    (target / "stage.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def read_stage_bundle(directory: Path, stage_id: str) -> StageBundle:
    """Read a stage bundle, verifying every recorded content hash.

    A hash mismatch raises rather than warning. A bundle whose bytes changed
    since it was written is not evidence about anything, and letting it through
    would surface three stages later as an inexplicable numerical difference.
    """
    stage = _validated_stage_id(stage_id)
    source = Path(directory) / stage
    manifest_path = source / "stage.json"
    if not manifest_path.is_file():
        raise ScopeValidationError(f"no stage.json found at {manifest_path}.")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared_class = manifest.get("comparison_class")
    if declared_class not in COMPARISON_CLASSES:
        raise ScopeValidationError(
            f"bundle {stage!r} declares comparison_class {declared_class!r}, "
            f"which is not one of {list(COMPARISON_CLASSES)}."
        )

    arrays: dict[str, np.ndarray] = {}
    for entry in manifest["arrays"]:
        path = source / entry["path"]
        if not path.is_file():
            raise ScopeValidationError(f"array file {path} listed in stage.json is missing.")
        observed = _sha256_file(path)
        if observed != entry["sha256"]:
            raise ScopeValidationError(
                f"content hash mismatch for {entry['name']!r} in stage {stage!r}: "
                f"stage.json records {entry['sha256'][:16]}..., file hashes to "
                f"{observed[:16]}.... The bundle has been modified since it was written."
            )
        array = np.load(path, allow_pickle=False)
        if list(array.shape) != list(entry["shape"]):
            raise ShapeValidationError(
                f"array {entry['name']!r} has shape {array.shape}, stage.json "
                f"records {tuple(entry['shape'])}."
            )
        arrays[entry["name"]] = array

    return StageBundle(
        stage_id=manifest["stage_id"],
        stage_type=manifest.get("stage_type", "unspecified"),
        schema_version=manifest["schema_version"],
        comparison_class=declared_class,
        parent_stage_ids=tuple(manifest.get("parent_stage_ids", ())),
        arrays=arrays,
        provenance=manifest["provenance"],
    )
