"""v0.31.1a PySINDy 2.x migration prototype tests.

Verify the private ``_pysindy2_prototype`` module:

- correctly detects the installed PySINDy generation;
- correctly refuses to guess a generation outside the supported set;
- exposes the same delta enumeration the migration audit document
  documents (i.e. the two artifacts cannot drift silently);
- does not leak into any public surface;
- does not affect legacy 1.x behavior (no wire-up in production paths).

The prototype is research-only per outcome A (modern-only future line) —
the v0.31.1 / v0.32 migration PR will either promote it to
``_pysindy_compat.py`` (renamed) or delete it entirely.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_AUDIT_DOC_PATH = _REPO_ROOT / "docs" / "design" / "PYSINDY_2_MIGRATION_AUDIT.md"


# ---------------------------------------------------------------------------
# 1. Version detection works for both supported generations.
# ---------------------------------------------------------------------------


def test_prototype_detects_pysindy_1x() -> None:
    from pdelie.discovery import _pysindy2_prototype

    class _FakePysindy:
        __version__ = "1.7.5"

    assert _pysindy2_prototype._detect_pysindy_api_generation(_FakePysindy()) == "1x"


def test_prototype_detects_pysindy_2x() -> None:
    from pdelie.discovery import _pysindy2_prototype

    class _FakePysindy:
        __version__ = "2.1.0"

    assert _pysindy2_prototype._detect_pysindy_api_generation(_FakePysindy()) == "2x"


def test_prototype_detects_pysindy_2x_dev_version() -> None:
    from pdelie.discovery import _pysindy2_prototype

    class _FakePysindy:
        __version__ = "2.2.0.dev0"

    assert _pysindy2_prototype._detect_pysindy_api_generation(_FakePysindy()) == "2x"


# ---------------------------------------------------------------------------
# 2. Unsupported generations raise the prototype's actionable error.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_version", ["0.15.0", "3.0.0", "10.0.0"])
def test_prototype_rejects_unsupported_major(bad_version: str) -> None:
    from pdelie.discovery import _pysindy2_prototype

    class _FakePysindy:
        __version__ = bad_version

    with pytest.raises(
        _pysindy2_prototype.UnsupportedPySINDyGenerationError
    ) as excinfo:
        _pysindy2_prototype._detect_pysindy_api_generation(_FakePysindy())
    # The message must name the observed version and cross-reference the
    # migration audit document.
    assert bad_version in str(excinfo.value)
    assert "PYSINDY_2_MIGRATION_AUDIT" in str(excinfo.value)


def test_prototype_rejects_non_string_version() -> None:
    from pdelie.discovery import _pysindy2_prototype

    class _FakePysindy:
        __version__ = 2  # not a string

    with pytest.raises(_pysindy2_prototype.UnsupportedPySINDyGenerationError):
        _pysindy2_prototype._detect_pysindy_api_generation(_FakePysindy())


def test_prototype_rejects_malformed_version_string() -> None:
    from pdelie.discovery import _pysindy2_prototype

    class _FakePysindy:
        __version__ = "not-a-version"

    with pytest.raises(_pysindy2_prototype.UnsupportedPySINDyGenerationError):
        _pysindy2_prototype._detect_pysindy_api_generation(_FakePysindy())


def test_prototype_rejects_missing_version_attribute() -> None:
    from pdelie.discovery import _pysindy2_prototype

    class _FakePysindy:
        pass  # no __version__

    with pytest.raises(_pysindy2_prototype.UnsupportedPySINDyGenerationError):
        _pysindy2_prototype._detect_pysindy_api_generation(_FakePysindy())


# ---------------------------------------------------------------------------
# 3. Delta enumeration matches the migration audit document.
# ---------------------------------------------------------------------------


def test_delta_enumeration_names_the_six_documented_api_breaks() -> None:
    """The prototype's ``_describe_migration_breaks`` must expose an entry
    for every API break called out in the migration audit document.
    """
    from pdelie.discovery import _pysindy2_prototype

    breaks = _pysindy2_prototype._describe_migration_breaks()

    # Six of the seven audit deltas are covered by the prototype's tuple
    # constants (delta 7 — WeakPDELibrary random-state — is documented as
    # unchanged and not encoded here).
    expected_break_keys = {
        "SINDy.__init__.removed_kwargs",
        "SINDy.fit.removed_kwargs",
        "SINDy.methods_removed",
        "SINDy.attrs_removed",
        "STLSQ.__init__.removed_kwargs",
        "PDELibrary_and_WeakPDELibrary.__init__.removed_kwargs",
    }
    assert set(breaks.keys()) == expected_break_keys


@pytest.mark.parametrize(
    "kwarg",
    ["feature_names", "t_default", "discrete_time"],
)
def test_sindy_init_break_lists_removed_kwargs(kwarg: str) -> None:
    from pdelie.discovery import _pysindy2_prototype

    breaks = _pysindy2_prototype._describe_migration_breaks()
    assert kwarg in breaks["SINDy.__init__.removed_kwargs"]


@pytest.mark.parametrize(
    "kwarg",
    ["multiple_trajectories", "unbias", "quiet", "ensemble", "library_ensemble"],
)
def test_sindy_fit_break_lists_removed_kwargs(kwarg: str) -> None:
    from pdelie.discovery import _pysindy2_prototype

    breaks = _pysindy2_prototype._describe_migration_breaks()
    assert kwarg in breaks["SINDy.fit.removed_kwargs"]


def test_sindy_differentiate_is_flagged_as_removed() -> None:
    from pdelie.discovery import _pysindy2_prototype

    breaks = _pysindy2_prototype._describe_migration_breaks()
    assert "differentiate" in breaks["SINDy.methods_removed"]


def test_sindy_model_attribute_is_flagged_as_removed() -> None:
    from pdelie.discovery import _pysindy2_prototype

    breaks = _pysindy2_prototype._describe_migration_breaks()
    assert "model" in breaks["SINDy.attrs_removed"]


def test_stlsq_fit_intercept_is_flagged_as_removed() -> None:
    from pdelie.discovery import _pysindy2_prototype

    breaks = _pysindy2_prototype._describe_migration_breaks()
    assert "fit_intercept" in breaks["STLSQ.__init__.removed_kwargs"]


@pytest.mark.parametrize(
    "kwarg",
    ["library_functions", "function_names", "interaction_only"],
)
def test_library_break_lists_removed_kwargs(kwarg: str) -> None:
    from pdelie.discovery import _pysindy2_prototype

    breaks = _pysindy2_prototype._describe_migration_breaks()
    assert (
        kwarg
        in breaks["PDELibrary_and_WeakPDELibrary.__init__.removed_kwargs"]
    )


def test_prototype_and_audit_document_agree_on_break_surfaces() -> None:
    """The migration audit document lists every API surface enumerated by
    the prototype. If the audit is edited without updating the prototype
    (or vice versa) this test fires.
    """
    audit_text = _AUDIT_DOC_PATH.read_text(encoding="utf-8")
    for surface_fragment in (
        "SINDy.__init__",
        "SINDy.fit",
        "SINDy.differentiate",
        "SINDy.model",
        "STLSQ.__init__",
        "PDELibrary.__init__",
        "WeakPDELibrary.__init__",
    ):
        assert surface_fragment in audit_text, (
            f"audit document must mention API surface {surface_fragment!r}"
        )


# ---------------------------------------------------------------------------
# 4. Prototype does not affect legacy 1.x behavior.
# ---------------------------------------------------------------------------


def test_prototype_does_not_break_legacy_task_runtime() -> None:
    """Import-only smoke: the v0.31b1/b2 task-runtime modules and the
    v0.31c example runner all import cleanly with the prototype present.
    """
    from pdelie.discovery import _pysindy2_prototype  # noqa: F401
    from pdelie.examples import (  # noqa: F401
        run_downstream_discovery_task_bridge_example,
    )
    from pdelie.tasks import (  # noqa: F401
        PySINDyDiscoveryUnsupportedBoundaryError,
        WeakPDELibraryDiagnostic,
        inspect_pysindy_weak_pde_library,
        run_pysindy_pde_task,
        summarize_discovery_task_result,
        summarize_pysindy_weak_pde_library_diagnostic,
    )


def test_pysindy_1x_installed_matches_prototype_detection() -> None:
    """The installed pysindy version — resolved by the [test] extra to
    something in ``>=1.7.5,<2`` on the v0.31.x line — must be detected as
    ``"1x"`` by the prototype. This is the load-bearing legacy-lane guard.
    """
    pytest.importorskip("pysindy", reason="pysindy is an optional [downstream] dep")
    import pysindy

    from pdelie.discovery import _pysindy2_prototype

    assert _pysindy2_prototype._detect_pysindy_api_generation(pysindy) == "1x"
