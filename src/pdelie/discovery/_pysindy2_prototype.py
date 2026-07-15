"""v0.31.1a EXPERIMENTAL private compatibility prototype for PySINDy 2.x.

.. warning::
    This module is a RESEARCH SPIKE artifact from the v0.31.1a runtime
    modernization audit. It is:

    * private (leading underscore; not re-exported from any package);
    * NOT wired into any production code path in v0.31.1a;
    * intentionally narrow — it names the six PySINDy 1.7.5 -> 2.1.0 API
      breaks the migration PR will need to absorb, and provides a
      generation-detection helper and an actionable unsupported-generation
      guard;
    * scheduled to be deleted OR promoted (to ``_pysindy_compat``) in the
      v0.31.1 / v0.32 migration PR.

    Do NOT depend on any symbol from this module from outside
    ``src/pdelie/discovery/``. Consumer code that grew a runtime dependency
    on this file will break silently at v0.32.

Companion documents:

- ``docs/design/PYSINDY_2_MIGRATION_AUDIT.md`` — exhaustive per-delta API
  diff and per-lane failure signatures.
- ``docs/design/RUNTIME_COMPATIBILITY_POLICY.md`` — SPEC 0 policy framing
  and outcome (A_modern_only_future_line).
- ``configs/runtime_compatibility_matrix.json`` — machine-readable form.

Migration decision: **outcome A (modern-only future line)**. The audit found
six independent API breaks in PySINDy 2.1.0 plus a transitive numpy>=2
floor conflict; a dual 1.x/2.x runtime is not the goal. This prototype
records the SHAPE of the eventual shim so the v0.31.1 / v0.32 migration PR
has a concrete anchor — nothing more.
"""

from __future__ import annotations

from typing import Any, Literal

# ---------------------------------------------------------------------------
# Frozen enumeration of the six PySINDy 1.7.5 -> 2.1.0 API breaks the
# migration PR must absorb. Each entry is a keyword the migration code path
# must stop passing (or move) when the detected generation is "2x".
# ---------------------------------------------------------------------------

#: SINDy.__init__ removed kwargs.
_SINDY_INIT_REMOVED_KWARGS: tuple[str, ...] = (
    "feature_names",
    "t_default",
    "discrete_time",
)

#: SINDy.fit removed kwargs; ``feature_names`` moved here from ``__init__``.
_SINDY_FIT_REMOVED_KWARGS: tuple[str, ...] = (
    "multiple_trajectories",
    "unbias",
    "quiet",
    "ensemble",
    "library_ensemble",
    "replace",
    "n_candidates_to_drop",
    "n_subset",
    "n_models",
    "ensemble_aggregator",
)

#: ``SINDy.differentiate`` method removed in 2.1.0. Migration path: use
#: ``model.differentiation_method_(trajectory, t=time_values)`` instead.
_SINDY_METHODS_REMOVED: tuple[str, ...] = ("differentiate",)

#: ``SINDy.model`` attribute removed on class and fitted instance. No
#: pdelie call site depends on it today; documented for downstream
#: consumers.
_SINDY_ATTRS_REMOVED: tuple[str, ...] = ("model",)

#: STLSQ.__init__ removed kwargs.
_STLSQ_INIT_REMOVED_KWARGS: tuple[str, ...] = ("fit_intercept",)

#: PDELibrary and WeakPDELibrary removed kwargs. Migration pattern:
#: pass ``function_library=<BaseFeatureLibrary>`` (e.g.
#: ``pysindy.PolynomialLibrary(degree=2, interaction_only=True)``).
_LIBRARY_INIT_REMOVED_KWARGS: tuple[str, ...] = (
    "library_functions",
    "function_names",
    "interaction_only",
)

#: The supported PySINDy generation for the v0.32 modern lane.
_SUPPORTED_MODERN_MAJOR: int = 2

#: The supported PySINDy generation for the v0.31.x legacy line.
_SUPPORTED_LEGACY_MAJOR: int = 1


class UnsupportedPySINDyGenerationError(RuntimeError):
    """Raised when the detected PySINDy generation is outside the supported set.

    v0.31.1a research prototype exception. In the v0.31.1 / v0.32 migration
    PR this class is either renamed / re-exported from a stable location or
    replaced with :class:`pdelie.errors.ScopeValidationError` — decide at
    implementation time.
    """


def _detect_pysindy_api_generation(pysindy_module: Any) -> Literal["1x", "2x"]:
    """Detect the installed PySINDy API generation from ``pysindy.__version__``.

    Returns
    -------
    ``"1x"`` if the installed major is 1; ``"2x"`` if the installed major
    is 2.

    Raises
    ------
    :class:`UnsupportedPySINDyGenerationError`
        If the module has no ``__version__`` attribute, the version string
        does not parse as ``<major>.<...>``, or the major is not in
        ``{1, 2}``. Never catches a broader exception silently.
    """
    version = getattr(pysindy_module, "__version__", None)
    if not isinstance(version, str):
        raise UnsupportedPySINDyGenerationError(
            f"pysindy.__version__ is not a string; got {type(version).__name__}."
        )
    head, _, _ = version.partition(".")
    try:
        major = int(head)
    except ValueError as exc:
        raise UnsupportedPySINDyGenerationError(
            f"pysindy.__version__ = {version!r} does not begin with an "
            "integer major."
        ) from exc
    if major == _SUPPORTED_LEGACY_MAJOR:
        return "1x"
    if major == _SUPPORTED_MODERN_MAJOR:
        return "2x"
    raise UnsupportedPySINDyGenerationError(
        f"pysindy major version {major} is outside the v0.31.1a supported "
        f"set {{{_SUPPORTED_LEGACY_MAJOR}, {_SUPPORTED_MODERN_MAJOR}}}; "
        f"observed pysindy.__version__ = {version!r}. See "
        "docs/design/PYSINDY_2_MIGRATION_AUDIT.md."
    )


def _describe_migration_breaks() -> dict[str, tuple[str, ...]]:
    """Return the frozen enumeration of API breaks for introspection.

    Used by ``tests/test_pysindy_2_migration_prototype.py`` to assert the
    prototype accurately mirrors the delta table in the migration audit
    document — so that if the audit document is edited without a
    corresponding code change (or vice versa), the test fires.
    """
    return {
        "SINDy.__init__.removed_kwargs": _SINDY_INIT_REMOVED_KWARGS,
        "SINDy.fit.removed_kwargs": _SINDY_FIT_REMOVED_KWARGS,
        "SINDy.methods_removed": _SINDY_METHODS_REMOVED,
        "SINDy.attrs_removed": _SINDY_ATTRS_REMOVED,
        "STLSQ.__init__.removed_kwargs": _STLSQ_INIT_REMOVED_KWARGS,
        "PDELibrary_and_WeakPDELibrary.__init__.removed_kwargs": (
            _LIBRARY_INIT_REMOVED_KWARGS
        ),
    }
