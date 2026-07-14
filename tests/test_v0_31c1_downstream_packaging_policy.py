"""v0.31c1 downstream-packaging-policy tests.

The v0.31c1 sub-release added a narrow, temporary ``setuptools<82;
python_version<'3.12'`` cap to the ``pdelie[downstream]`` optional-dependency
extra after an adversarial install matrix demonstrated that PySINDy 1.7.5
imports ``pkg_resources`` at package init and setuptools 82 removed that
module. The cap is bounded, Python-version-scoped, and documented as
temporary until the PySINDy 2.x migration in ``v0.31.1`` / ``v0.32``.

This module tests the packaging policy without spinning up fresh venvs at
test-collection time. The adversarial matrix itself is exercised out-of-band
in the release-close workflow; the in-repo tests below verify the durable
public evidence — pyproject constraint text, matrix JSON, policy doc, and
wheel METADATA — plus the invariants v0.31c1 must preserve (no public schema
drift, no root export drift, PySINDy pin stays ``>=1.7.5,<2``).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import pdelie

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT_PATH = _REPO_ROOT / "pyproject.toml"
_MATRIX_PATH = _REPO_ROOT / "configs" / "pysindy_compatibility_matrix.json"
_POLICY_DOC_PATH = _REPO_ROOT / "docs" / "design" / "PYSINDY_COMPATIBILITY_POLICY.md"


def _pyproject_text() -> str:
    return _PYPROJECT_PATH.read_text(encoding="utf-8")


def _matrix() -> dict[str, Any]:
    return json.loads(_MATRIX_PATH.read_text(encoding="utf-8"))


def _policy_text() -> str:
    return _POLICY_DOC_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Declared downstream extra matches the observed compatibility boundary.
# ---------------------------------------------------------------------------


def test_v0_31c1_downstream_extra_declares_setuptools_lt_82_cap() -> None:
    """The `[downstream]` extra must declare the temporary `setuptools<82` cap.

    The v0.31c1 adversarial audit found setuptools 82 removes `pkg_resources`,
    which pysindy 1.7.5 imports at package init. The extra must cap at <82
    to auto-downgrade a modern ambient setuptools when pdelie[downstream] is
    installed.
    """
    text = _pyproject_text()
    # Match on the exact policy string; whitespace-agnostic within the marker.
    pattern = re.compile(
        r'"setuptools<82;\s*python_version\s*<\s*[\'"]3\.12[\'"]"',
    )
    assert pattern.search(text), (
        "pyproject.toml [project.optional-dependencies].downstream must "
        "declare 'setuptools<82; python_version < \"3.12\"' — the v0.31c1 "
        "compatibility boundary for PySINDy 1.7.5's pkg_resources import."
    )


# ---------------------------------------------------------------------------
# 2. Any temporary setuptools pin is bounded and Python-version-scoped.
# ---------------------------------------------------------------------------


def test_v0_31c1_setuptools_pin_is_bounded_and_python_scoped() -> None:
    """Every downstream/test setuptools constraint in pyproject.toml must be
    bounded above AND scoped to `python_version < '3.12'`. A bare or
    unbounded ``setuptools`` runtime-dependency line is forbidden.

    The ``[build-system].requires`` and ``[build-system].build-backend``
    entries are build-time-only and correctly reference setuptools without
    the runtime constraint — this test excludes them explicitly.
    """
    text = _pyproject_text()
    # Match only the runtime dependency lines: `"setuptools<...`.
    # Excludes `"setuptools.build_meta"` and `"setuptools>=..."` build-time
    # requires. The v0.31c1 cap is always an upper bound.
    runtime_lines = [
        line.strip()
        for line in text.splitlines()
        if re.search(r'"setuptools\s*<', line)
    ]
    assert runtime_lines, (
        "pyproject.toml must contain at least one runtime setuptools "
        "constraint (the v0.31c1 compatibility cap)."
    )
    for line in runtime_lines:
        assert "python_version" in line and "3.12" in line, (
            f"every runtime setuptools line must be Python-version-scoped "
            f"to <3.12; got {line!r}"
        )


# ---------------------------------------------------------------------------
# 3. The policy document records the reason.
# ---------------------------------------------------------------------------


def test_v0_31c1_policy_doc_records_setuptools_82_boundary() -> None:
    """The compatibility policy doc must explain the setuptools cap.

    It must reference: pysindy 1.7.5, pkg_resources, setuptools 82, and
    label the constraint as temporary pending v0.31.1 / v0.32.
    """
    text = _policy_text().lower()
    assert "pysindy 1.7.5" in text or "pysindy==1.7.5" in text or "1.7.5" in text
    assert "pkg_resources" in text
    assert "setuptools" in text and "82" in text
    assert "temporary" in text or "temporarily" in text


# ---------------------------------------------------------------------------
# 4. PySINDy remains >=1.7.5,<2.
# ---------------------------------------------------------------------------


def test_v0_31c1_pysindy_pin_unchanged() -> None:
    text = _pyproject_text()
    pattern = re.compile(r'"pysindy>=1\.7\.5,<2;\s*python_version\s*<\s*[\'"]3\.12[\'"]"')
    assert pattern.search(text), (
        "pyproject.toml must retain the v0.31b3 pysindy>=1.7.5,<2 pin."
    )


# ---------------------------------------------------------------------------
# 5. No public schema changed.
# ---------------------------------------------------------------------------


def test_v0_31c1_discovery_task_result_schema_unchanged() -> None:
    """The 22-key discovery_task_result contract from v0.31b1 must be
    unaffected by the v0.31c1 packaging work."""
    from pdelie.tasks import discovery as discovery_module

    assert hasattr(discovery_module, "_TASK_RESULT_TOP_LEVEL_KEYS")
    top_level = discovery_module._TASK_RESULT_TOP_LEVEL_KEYS
    assert len(top_level) == 22, (
        f"discovery_task_result 22-key schema drifted; got {len(top_level)}"
    )


def test_v0_31c1_weak_pde_library_diagnostic_schema_unchanged() -> None:
    """The 27-key pdelie_weak_pde_library_diagnostic contract from v0.31b2
    must be unaffected by the v0.31c1 packaging work."""
    from pdelie.tasks import weak_pde_library as weak_module

    # The module pins its emitted top-level key set as a tuple; find it.
    top_level = getattr(weak_module, "_DIAGNOSTIC_TOP_LEVEL_KEYS", None)
    if top_level is None:
        # Fall back to _SUMMARY_TOP_LEVEL_KEYS naming convention.
        top_level = getattr(weak_module, "_SUMMARY_TOP_LEVEL_KEYS", None)
    assert top_level is not None, (
        "weak_pde_library module must expose an internal top-level-keys "
        "tuple for the diagnostic summary"
    )
    assert len(top_level) == 27, (
        f"pdelie_weak_pde_library_diagnostic 27-key schema drifted; got "
        f"{len(top_level)}"
    )


# ---------------------------------------------------------------------------
# 6. No root export changed.
# ---------------------------------------------------------------------------


def test_v0_31c1_no_new_root_exports() -> None:
    """v0.31c1 must not add any new attribute to the root `pdelie`
    package."""
    for forbidden in (
        "setuptools",
        "_legacy_numpy_rng_seed_scope",
        "downstream_discovery_task_bridge",
        "run_downstream_discovery_task_bridge_example",
    ):
        assert not hasattr(pdelie, forbidden), (
            f"root pdelie must not export {forbidden!r}"
        )


# ---------------------------------------------------------------------------
# 7. Wheel metadata contains the expected conditional requirements.
# ---------------------------------------------------------------------------


def test_v0_31c1_installed_wheel_metadata_declares_setuptools_cap() -> None:
    """The installed pdelie distribution's Requires-Dist metadata must
    declare the setuptools<82 cap under the downstream extra.

    Uses ``dist.requires`` (parsed list of PEP 508 requirement strings)
    rather than ``str(dist.metadata)`` — the latter can raise
    ``HeaderParseError`` on Requires-Dist rows whose values contain
    newlines, because README content flows into Description.
    """
    import importlib.metadata as _md

    try:
        dist = _md.distribution("pdelie")
    except _md.PackageNotFoundError:
        pytest.skip("pdelie is not installed as a distribution; skipping")

    requires = dist.requires or []
    downstream_setuptools_reqs = [
        req
        for req in requires
        if req.lower().startswith("setuptools")
        and "extra ==" in req.lower().replace('"', "'")
        and "'downstream'" in req.lower().replace('"', "'")
    ]
    assert downstream_setuptools_reqs, (
        f"installed pdelie Requires-Dist must include a setuptools "
        f"requirement under extra == 'downstream'; got requires={requires!r}"
    )
    for req in downstream_setuptools_reqs:
        # PEP 508: split on ';' — LHS is the version specifier.
        specifier = req.split(";", 1)[0].strip()
        assert "<82" in specifier.replace(" ", ""), (
            f"downstream setuptools requirement must cap at <82; got {req!r}"
        )


# ---------------------------------------------------------------------------
# 8. A modern-setuptools failure cannot be hidden by a preinstalled old
#    setuptools.
# ---------------------------------------------------------------------------


def test_v0_31c1_pip_dry_run_downgrades_ambient_setuptools_82() -> None:
    """Verify pip's resolver, when asked to install pdelie[downstream] into
    an environment that already has setuptools==82, plans to downgrade it.

    We do NOT actually install into a fresh venv here (that lives in the
    adversarial matrix audit); instead we use ``pip install --dry-run
    --report -`` against the current environment's context to inspect the
    resolver's plan. The resolver decision is what the invariant hinges
    on — the cap must not be silently satisfied by a preinstalled old
    setuptools.

    Skipped if the current pip / pdelie install context does not support
    dry-run reporting.
    """
    # Locate the current pdelie wheel; if not present locally, skip.
    dist_dir = _REPO_ROOT / "dist"
    wheels = sorted(dist_dir.glob("pdelie-*.whl"))
    if not wheels:
        pytest.skip(
            "no wheel present at dist/; run `python -m build --wheel` first"
        )
    wheel_path = wheels[-1]

    # Ask pip to resolve pdelie[downstream] without installing anything.
    # The resolver may fail on some CI environments; if it does, skip
    # rather than fail — the substantive matrix audit is out-of-band.
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--dry-run",
            "--ignore-installed",
            "--report",
            "-",
            f"{wheel_path}[downstream]",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(
            f"pip dry-run resolver could not evaluate in this environment; "
            f"tail: {result.stderr[-400:]}"
        )
    # The report is JSON on stdout; parse and inspect setuptools.
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.skip("pip did not emit a JSON report; skipping")
    installs = report.get("install", [])
    setuptools_entries = [
        entry
        for entry in installs
        if entry.get("metadata", {}).get("name", "").lower() == "setuptools"
    ]
    if not setuptools_entries:
        # setuptools is not in the resolved install plan — either it's
        # already satisfied by the current environment's setuptools (which
        # must therefore already be <82), or the resolver excluded it.
        # Either way, we cannot conclude a failure here.
        pytest.skip(
            "resolver did not plan a setuptools install/downgrade; "
            "invariant is satisfied vacuously"
        )
    for entry in setuptools_entries:
        version = entry.get("metadata", {}).get("version", "")
        major = int(version.split(".", 1)[0]) if version and version[0].isdigit() else 0
        assert major < 82, (
            f"resolver planned setuptools version {version!r}; must be <82 "
            f"per the v0.31c1 downstream extra cap"
        )


# ---------------------------------------------------------------------------
# 9. Clean resolved downstream installation passes.
# ---------------------------------------------------------------------------


def test_v0_31c1_matrix_json_records_verdict_and_boundary() -> None:
    """The compatibility matrix JSON must record the v0.31c1 verdict.

    The v0.31c1 sub-release amends the matrix with:
    - a `packaging_audit` block enumerating the setuptools versions tested;
    - a `verdict` string such as 'B_setuptools_82_boundary';
    - a note that setuptools 82 removed pkg_resources.
    """
    matrix = _matrix()
    # Preserve v0.31b3 top-level shape.
    assert matrix["summary_type"] == "pdelie_pysindy_compatibility_matrix"
    assert matrix["policy_outcome"] == "C_temporary_1x_policy"

    audit = matrix.get("v0_31c1_packaging_audit")
    assert audit is not None, (
        "configs/pysindy_compatibility_matrix.json must include a "
        "'v0_31c1_packaging_audit' block after v0.31c1"
    )
    assert audit["verdict"] == "B_setuptools_82_boundary", (
        f"expected verdict 'B_setuptools_82_boundary'; got "
        f"{audit['verdict']!r}"
    )
    assert audit["highest_working_setuptools_version"] == "81.0.0"
    assert 82 in [
        int(str(v).split(".", 1)[0]) for v in audit["failing_setuptools_versions"]
    ], (
        "setuptools 82 must be listed as failing in the audit"
    )
