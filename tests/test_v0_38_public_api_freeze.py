"""The v0.38 public API freeze, checked against the tree rather than asserted.

Why this is not just "``pdelie.__all__`` is unchanged"
=====================================================

It *is* unchanged — 11 names, same as v0.37.1. And a freeze asserting only that
would be true and nearly vacuous, because the root namespace never moved while
**11 new modules and 61 names** became importable across five packages.

That gap is the shape of every defect this arc produced: a declaration that is
technically accurate and describes almost nothing of what happened. So the
freeze enumerates what actually grew, per module, measured by importing both
trees rather than recalled from a plan.

What "frozen" means here
========================

Growth is allowed; **silent** growth is not. Any name added to a frozen surface
fails these tests until the manifest is updated in the same commit, which makes
the addition a deliberate act with a reviewable diff.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = REPO_ROOT / "docs/specs/public_api_freeze.v0_38.json"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text())


def test_the_manifest_exists_and_is_strict_json() -> None:
    assert MANIFEST.exists()
    json.dumps(_manifest(), allow_nan=False)


def test_the_root_surface_is_unchanged_from_v0_37_1() -> None:
    """The constraint that has held all release long."""
    import pdelie

    manifest = _manifest()
    assert sorted(pdelie.__all__) == manifest["root_exports"]
    assert len(pdelie.__all__) == manifest["root_export_count"] == 11


def test_every_declared_new_module_imports() -> None:
    """A manifest naming a module that does not exist describes nothing."""
    for name in _manifest()["new_modules"]:
        importlib.import_module(name)


def test_the_new_module_surfaces_match_the_manifest() -> None:
    """The enumeration the root check cannot make.

    61 names across 11 modules. Adding one without recording it fails here.
    """
    manifest = _manifest()
    drift: list[str] = []
    for name, expected in manifest["new_module_surface"].items():
        actual = sorted(getattr(importlib.import_module(name), "__all__", []))
        if actual != expected:
            added = sorted(set(actual) - set(expected))
            removed = sorted(set(expected) - set(actual))
            drift.append(f"{name}: +{added} -{removed}")
    assert not drift, (
        "the v0.38 module surfaces have drifted from the freeze:\n  "
        + "\n  ".join(drift)
        + "\nUpdate docs/specs/public_api_freeze.v0_38.json in the same commit."
    )


def test_the_package_exports_match_the_manifest() -> None:
    manifest = _manifest()
    for package, expected in manifest["package_exports"].items():
        actual = sorted(getattr(importlib.import_module(package), "__all__", []))
        assert actual == expected, (
            f"{package}.__all__ drifted: +{sorted(set(actual) - set(expected))} "
            f"-{sorted(set(expected) - set(actual))}"
        )


def test_the_name_count_matches_what_the_manifest_claims() -> None:
    """Guard the summary figure, so it cannot be quoted while being wrong."""
    manifest = _manifest()
    counted = sum(len(v) for v in manifest["new_module_surface"].values())
    assert counted == manifest["new_module_name_count"]


# --------------------------------------------------------------------------
# Exported-but-undeclared: the inconsistency this inventory found
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("package", "module"),
    [
        ("pdelie.actions", "pdelie.actions.parameter_action_spec"),
        ("pdelie.design", "pdelie.design.row_mask"),
    ],
)
def test_a_package_export_is_declared_by_its_own_module(package: str, module: str) -> None:
    """``build_row_mask`` was re-exported by ``pdelie.design`` and absent from
    ``row_mask.__all__``.

    A name can be part of a package's surface while its own module declines to
    declare it, and then ``from module import *`` and the package export
    disagree about what exists. Found by building this inventory; fixed at the
    same time.

    Only names *defined* in the module are checked -- a package re-exporting
    something imported from elsewhere is ordinary and not a defect.
    """
    package_module = importlib.import_module(package)
    target = importlib.import_module(module)
    target_all = set(getattr(target, "__all__", []))

    undeclared = [
        name
        for name in getattr(package_module, "__all__", [])
        if getattr(getattr(target, name, None), "__module__", None) == module
        and name not in target_all
    ]
    assert not undeclared, (
        f"{package} exports {undeclared} which {module} defines but does not "
        f"declare in its own __all__"
    )


# --------------------------------------------------------------------------
# What was deliberately NOT exported
# --------------------------------------------------------------------------


def test_the_unexported_modules_stay_unexported() -> None:
    """Deliberate omissions, recorded so they are not "fixed" by accident.

    ``pdelie.residuals.irregular_weak`` in particular: the M3 guard freezes
    ``pdelie.residuals.__all__`` at eight names, and v0.38c withdrew its
    re-exports rather than widen it.
    """
    manifest = _manifest()
    for module_name, reason in manifest["deliberately_unexported"].items():
        assert reason, f"{module_name} has no recorded reason"
        module = importlib.import_module(module_name)
        package_name = module_name.rsplit(".", 1)[0]
        package = importlib.import_module(package_name)
        leaked = [
            name
            for name in getattr(module, "__all__", [])
            if name in getattr(package, "__all__", [])
        ]
        assert not leaked, (
            f"{module_name} names {leaked} are now exported from {package_name}, "
            f"but the freeze records them as deliberately unexported because: "
            f"{reason}"
        )


def test_the_residuals_surface_is_still_eight() -> None:
    """The M3 guard's number, restated here so the two cannot drift apart."""
    import pdelie.residuals as package

    assert len(package.__all__) == 8


def test_the_freeze_records_why_the_root_check_is_insufficient() -> None:
    """Without this the manifest reads as a formality."""
    note = _manifest()["note"]
    assert "vacuous" in note and "submodule" in note
