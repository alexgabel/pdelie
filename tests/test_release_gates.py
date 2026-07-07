"""v0.30f — parameterized declarative release-gate.

Replays every declarative assertion in `configs/release_gate_manifest.json`
against the repo. Functional smoke tests intentionally remain as explicit
per-version files under ``tests/test_v0_NN_release_gate.py``.

Failure messages always begin with ``[v<release>][<class>]`` so a failure
identifies both the release the assertion belongs to and the assertion class
that failed.
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any

import pytest

import pdelie

_REPO_ROOT = Path(__file__).resolve().parents[1]
_MANIFEST_PATH = "configs/release_gate_manifest.json"

_SUPPORTED_CLASSES: tuple[str, ...] = (
    "required_phrases_in_scope_doc",
    "required_phrases_in_api_stability",
    "required_phrases_in_roadmap",
    "required_phrases_in_plan",
    "required_phrases_in_readiness_doc",
    "forbidden_root_attributes",
    "forbidden_submodule_attributes",
    "required_root_attributes",
    "required_submodule_attributes",
    "strict_json_manifests",
    "notebook_structural_checks",
)
_ROW_METADATA_KEYS: frozenset[str] = frozenset({"release", "source_file"})


def _repo_path(path: str) -> Path:
    return _REPO_ROOT / path


def _repo_text(path: str) -> str:
    return _repo_path(path).read_text(encoding="utf-8")


def _load_manifest() -> dict[str, Any]:
    payload = json.loads(_repo_text(_MANIFEST_PATH))
    # strict-JSON safety net: no NaN / infinity permitted through this boundary.
    assert json.loads(json.dumps(payload, allow_nan=False)) == payload
    return payload


_MANIFEST = _load_manifest()


# --- meta-level tests ------------------------------------------------------


def test_manifest_is_strict_json() -> None:
    """The manifest roundtrips through allow_nan=False JSON."""
    reserialized = json.dumps(_MANIFEST, allow_nan=False)
    assert json.loads(reserialized) == _MANIFEST


def test_manifest_release_count_matches_declared() -> None:
    declared = _MANIFEST["release_count"]
    actual = len(_MANIFEST["releases"])
    assert declared == actual, (
        f"manifest.release_count = {declared}, but len(releases) = {actual}"
    )


def test_manifest_only_uses_supported_assertion_classes() -> None:
    """Every non-metadata key in every release row must be a supported class."""
    for row in _MANIFEST["releases"]:
        row_release = row.get("release", "<missing>")
        for key in row:
            if key in _ROW_METADATA_KEYS:
                continue
            assert key in _SUPPORTED_CLASSES, (
                f"[v{row_release}] unsupported assertion class in manifest: {key!r}"
            )


def test_manifest_current_job_name_matches_ci_workflow() -> None:
    """The CI workflow must define exactly the release-gate job named in the manifest."""
    workflow = _repo_text(".github/workflows/ci.yml")
    declared_job = _MANIFEST["current_release_gate_job_name"]
    assert f"{declared_job}:" in workflow, (
        f"CI workflow missing release-gate job named in manifest: {declared_job!r}"
    )


# --- per-class dispatch ----------------------------------------------------


def _prefix(release: str, cls: str) -> str:
    return f"[v{release}][{cls}]"


def _check_phrases_in_doc(release: str, cls: str, entry: dict[str, Any]) -> None:
    doc_path = entry["doc_path"]
    doc = _repo_text(doc_path)
    prefix = _prefix(release, cls)
    for phrase in entry.get("phrases", []):
        assert phrase in doc, f"{prefix} missing phrase in {doc_path}: {phrase!r}"


def _check_forbidden_root_attributes(release: str, cls: str, entry: dict[str, Any]) -> None:
    prefix = _prefix(release, cls)
    for name in entry.get("names", []):
        assert not hasattr(pdelie, name), f"{prefix} pdelie.{name} must not exist"


def _check_forbidden_submodule_attributes(release: str, cls: str, entry: dict[str, Any]) -> None:
    prefix = _prefix(release, cls)
    submodules = entry.get("submodules", [])
    names = entry.get("names", [])
    for submodule in submodules:
        module = importlib.import_module(submodule)
        for name in names:
            assert not hasattr(module, name), f"{prefix} {submodule}.{name} must not exist"


def _check_required_root_attributes(release: str, cls: str, entry: dict[str, Any]) -> None:
    prefix = _prefix(release, cls)
    for name in entry.get("names", []):
        assert hasattr(pdelie, name), f"{prefix} pdelie.{name} must exist"


def _check_required_submodule_attributes(release: str, cls: str, entry: list[dict[str, Any]]) -> None:
    prefix = _prefix(release, cls)
    for pair in entry:
        submodule = pair["submodule"]
        name = pair["name"]
        module = importlib.import_module(submodule)
        assert hasattr(module, name), f"{prefix} {submodule}.{name} must exist"


def _check_strict_json_manifests(release: str, cls: str, entry: list[dict[str, Any]]) -> None:
    prefix = _prefix(release, cls)
    for spec in entry:
        path = spec["path"]
        payload = json.loads(_repo_text(path))
        # allow_nan=False roundtrip: no NaN/inf allowed to slip through.
        reserialized = json.dumps(payload, allow_nan=False)
        assert json.loads(reserialized) == payload, (
            f"{prefix} {path} failed strict-JSON roundtrip"
        )


def _concat_markdown(notebook: dict[str, Any]) -> str:
    parts = []
    for cell in notebook.get("cells", []):
        if cell.get("cell_type") == "markdown":
            src = cell.get("source", "")
            parts.append("".join(src) if isinstance(src, list) else src)
    return "\n\n".join(parts)


def _check_notebook_structural(release: str, cls: str, entry: list[dict[str, Any]]) -> None:
    prefix = _prefix(release, cls)
    for spec in entry:
        path = spec["path"]
        notebook = json.loads(_repo_text(path))
        markdown = _concat_markdown(notebook)
        for phrase in spec.get("required_markdown_phrases", []):
            assert phrase in markdown, (
                f"{prefix} {path} missing required markdown phrase: {phrase!r}"
            )
        any_of = spec.get("any_of_markdown_phrases")
        if any_of:
            assert any(p in markdown for p in any_of), (
                f"{prefix} {path} missing at least one of markdown phrases: {any_of!r}"
            )
        code_cells = [c for c in notebook.get("cells", []) if c.get("cell_type") == "code"]
        min_code = int(spec.get("min_code_cells", 0))
        assert len(code_cells) >= min_code, (
            f"{prefix} {path} has {len(code_cells)} code cells, need >= {min_code}"
        )
        if spec.get("require_execution_counts", False):
            for idx, cell in enumerate(code_cells):
                assert cell.get("execution_count") is not None, (
                    f"{prefix} {path} code cell #{idx} has no execution_count"
                )
        if spec.get("require_outputs", False):
            total_outputs = sum(len(cell.get("outputs", [])) for cell in code_cells)
            assert total_outputs > 0, (
                f"{prefix} {path} has no cell outputs (require_outputs=true)"
            )


_DISPATCH = {
    "required_phrases_in_scope_doc":     _check_phrases_in_doc,
    "required_phrases_in_api_stability": _check_phrases_in_doc,
    "required_phrases_in_roadmap":       _check_phrases_in_doc,
    "required_phrases_in_plan":          _check_phrases_in_doc,
    "required_phrases_in_readiness_doc": _check_phrases_in_doc,
    "forbidden_root_attributes":         _check_forbidden_root_attributes,
    "forbidden_submodule_attributes":    _check_forbidden_submodule_attributes,
    "required_root_attributes":          _check_required_root_attributes,
    "required_submodule_attributes":     _check_required_submodule_attributes,
    "strict_json_manifests":             _check_strict_json_manifests,
    "notebook_structural_checks":        _check_notebook_structural,
}


# --- parametrized replay ---------------------------------------------------


def _iter_release_class_pairs() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for row in _MANIFEST["releases"]:
        release = row["release"]
        for cls in _SUPPORTED_CLASSES:
            if cls in row:
                pairs.append((release, cls))
    return pairs


@pytest.mark.parametrize(("release", "assertion_class"), _iter_release_class_pairs(),
                         ids=lambda pair: f"v{pair[0]}::{pair[1]}" if isinstance(pair, tuple) else str(pair))
def test_release_gate_assertion(release: str, assertion_class: str) -> None:
    row = next(r for r in _MANIFEST["releases"] if r["release"] == release)
    entry = row[assertion_class]
    handler = _DISPATCH[assertion_class]
    handler(release, assertion_class, entry)
