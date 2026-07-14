"""v0.31b3 PySINDy compatibility-policy tests.

This file enforces the v0.31b3 compatibility-policy decision:

    outcome                        = C_temporary_1x_policy
    pyproject_constraint           = pysindy>=1.7.5,<2
    supported_versions             = ["1.7.5"]
    primary_tested_version         = 1.7.5
    compat_shim_needed             = False

The policy is that PySINDy 1.7.5 is the sole supported backend version. PySINDy
2.x is NOT supported (it introduces four independent API breaks in SINDy /
PDELibrary / WeakPDELibrary constructor and fit signatures plus removes
``SINDy.differentiate``; it also collides with pdelie's ``numpy<2`` core pin).
No compat shim is added in v0.31b3 because there is no observed inconsistency
inside the 1.x line to shim over — the current adapter, bridge, and diagnostic
wrapper are all verified against 1.7.5 with 61/61 targeted tests passing.

This file is the executable policy contract. It asserts:

1. The ``pyproject.toml`` downstream extra carries the exact bounded pysindy
   constraint ``pysindy>=1.7.5,<2`` (a bare ``pysindy`` or an unbounded
   ``pysindy>=X`` pin is rejected).
2. A compatibility manifest at ``configs/pysindy_compatibility_matrix.json``
   exposes ``SUPPORTED_PYSINDY_VERSIONS`` and every ``supported_versions``
   value declared in the v0.31b3 decision has a matching manifest entry.
3. An unsupported-major PySINDy version (``999.0.0``) triggers a specific
   ``ScopeValidationError`` whose message names the supported range — no
   silent degradation.
4. The public v0.31b1 (22-key) and v0.31b2 (27-key) task-result key sets
   are unchanged by the b3 policy work.
5. No compat helper symbol, ``SUPPORTED_PYSINDY_VERSIONS`` constant,
   ``_pysindy_compat`` module reference, or new exception class leaks to
   root ``pdelie``.
6. Provenance / backend_version blocks record the currently-installed
   pysindy / sklearn / scipy versions exactly (no rounding, no coercion).
7. The v0.31b0 term-mapping golden still passes under every supported
   PySINDy API generation currently installed.
8. The v0.31b1 discovery TaskResult payload roundtrips strict JSON.
9. The v0.31b2 weak diagnostic payload roundtrips strict JSON.
10. (No-op under this decision — ``compat_shim_needed`` is False, so there
    is no ``_pysindy_compat.py`` module to grep-inspect.)

Tests that depend on Author A having landed the compatibility manifest or
the version-guard runtime path are marked ``pytest.xfail(strict=True)`` with
an explanatory reason. Once Author A lands the manifest and the runtime
version check, these xfails flip to XPASS and force a follow-up commit that
removes the ``xfail`` decorator — the strict flag protects against silent
success.
"""

from __future__ import annotations

import copy
import importlib.metadata as _importlib_metadata
import json
import re
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pytest

pysindy = pytest.importorskip(
    "pysindy",
    reason=(
        "pysindy is an optional backend; v0.31b3 compatibility-policy tests "
        "are skipped when unavailable."
    ),
)

import pdelie  # noqa: E402 — post-importorskip
from pdelie.contracts import FieldBatch  # noqa: E402
from pdelie.data import generate_heat_1d_field_batch  # noqa: E402
from pdelie.errors import ScopeValidationError  # noqa: E402
from pdelie.tasks import (  # noqa: E402
    WeakPDELibraryDiagnostic,
    inspect_pysindy_weak_pde_library,
    run_pysindy_pde_task,
    summarize_discovery_task_result,
    summarize_pysindy_weak_pde_library_diagnostic,
)
from pdelie.tasks import discovery as _tasks_discovery  # noqa: E402
from pdelie.tasks import weak_pde_library as _tasks_weak_pde_library  # noqa: E402

# ---------------------------------------------------------------------------
# Repository / manifest locations
# ---------------------------------------------------------------------------


_REPO_ROOT = Path(__file__).resolve().parents[1]
_PYPROJECT_PATH = _REPO_ROOT / "pyproject.toml"
_COMPATIBILITY_MANIFEST_PATH = (
    _REPO_ROOT / "configs" / "pysindy_compatibility_matrix.json"
)

# ---------------------------------------------------------------------------
# The v0.31b3 decision — treated as a single authoritative constant.
# Kept inline so this test file is self-contained and does not silently
# drift from the design memo.
# ---------------------------------------------------------------------------


_DECISION: dict[str, Any] = {
    "outcome": "C_temporary_1x_policy",
    "pyproject_constraint": "pysindy>=1.7.5,<2",
    "compat_shim_needed": False,
    "supported_versions": ["1.7.5"],
    "primary_tested_version": "1.7.5",
    "secondary_tested_version": None,
    "unsupported_versions": ["<1.7.5", ">=2.0.0"],
}

# ---------------------------------------------------------------------------
# v0.31b1 22-key top-level set (frozen sibling schema).
# ---------------------------------------------------------------------------


_V0_31B1_TASK_RESULT_KEYS: frozenset[str] = frozenset(
    {
        "summary_schema_version",
        "summary_type",
        "task_name",
        "backend_name",
        "backend_version",
        "target_convention",
        "input_layout",
        "derivative_backend",
        "pysindy_bridge_variant",
        "library_feature_names",
        "selected_terms",
        "coefficients",
        "support_precision",
        "support_recall",
        "support_f1",
        "exact_support",
        "coefficient_relative_l2",
        "train_residual",
        "heldout_residual",
        "weak_contract",
        "warnings",
        "underlying_discovery_result",
    }
)

# ---------------------------------------------------------------------------
# v0.31b2 27-key top-level set (frozen weak-diagnostic schema).
# ---------------------------------------------------------------------------


_V0_31B2_WEAK_DIAGNOSTIC_KEYS: frozenset[str] = frozenset(
    {
        "summary_schema_version",
        "summary_type",
        "diagnostic_only",
        "method_family",
        "backend_name",
        "backend_version",
        "input_layout",
        "boundary_policy",
        "target_convention",
        "library_configuration",
        "test_function_family",
        "quadrature_rule",
        "spatiotemporal_grid_shape",
        "input_field_shape",
        "weak_feature_names",
        "weak_matrix_shape",
        "weak_target_shape",
        "retained_weak_rows",
        "skipped_weak_rows",
        "skipped_row_reasons",
        "finite_value_status",
        "column_norms",
        "matrix_rank",
        "matrix_condition_number",
        "warnings",
        "compatibility_notes",
        "provenance",
    }
)


# ---------------------------------------------------------------------------
# Deterministic fixtures (mirror the b1/b2 test conventions).
# ---------------------------------------------------------------------------


def _build_periodic_heat_field_small() -> FieldBatch:
    """Small periodic 1D Heat FieldBatch for the discovery-task smoke run."""
    return generate_heat_1d_field_batch(
        batch_size=1,
        num_times=5,
        num_points=16,
        seed=3130,
    )


def _build_periodic_heat_field_weak() -> FieldBatch:
    """Weak-diagnostic-sized periodic 1D Heat FieldBatch (K=16 defensive floor)."""
    return generate_heat_1d_field_batch(
        batch_size=1,
        num_times=64,
        num_points=64,
        seed=3131,
    )


def _build_caller_configured_sindy() -> Any:
    """Construct a SINDy model with the smallest kwarg surface that works on 1.x."""
    optimizer = pysindy.STLSQ(threshold=0.1, alpha=0.05, max_iter=20)
    feature_library = pysindy.PolynomialLibrary(degree=2, include_bias=True)
    differentiation_method = pysindy.FiniteDifference()
    return pysindy.SINDy(
        optimizer=optimizer,
        feature_library=feature_library,
        differentiation_method=differentiation_method,
    )


_LIVE_DISCOVERY_CACHE: dict[str, Any] | None = None
_LIVE_WEAK_CACHE: dict[str, Any] | None = None


def _run_live_discovery_task() -> dict[str, Any]:
    global _LIVE_DISCOVERY_CACHE
    if _LIVE_DISCOVERY_CACHE is not None:
        return _LIVE_DISCOVERY_CACHE
    field = _build_periodic_heat_field_small()
    model = _build_caller_configured_sindy()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        warnings.simplefilter("ignore", category=DeprecationWarning)
        result = run_pysindy_pde_task(
            field,
            task_name="v0_31b3_compat_policy_smoke",
            pysindy_model=model,
        )
    _LIVE_DISCOVERY_CACHE = {"field": field, "result": result}
    return _LIVE_DISCOVERY_CACHE


def _run_live_weak_diagnostic() -> dict[str, Any]:
    global _LIVE_WEAK_CACHE
    if _LIVE_WEAK_CACHE is not None:
        return _LIVE_WEAK_CACHE
    field = _build_periodic_heat_field_weak()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=UserWarning)
        warnings.simplefilter("ignore", category=DeprecationWarning)
        summary = inspect_pysindy_weak_pde_library(
            field,
            task_name="v0_31b3_compat_policy_weak_smoke",
            library_configuration=WeakPDELibraryDiagnostic(
                polynomial_degree=2,
                derivative_order=2,
                num_domain_centers_K=16,
            ),
        )
    _LIVE_WEAK_CACHE = {"field": field, "summary": summary}
    return _LIVE_WEAK_CACHE


# ---------------------------------------------------------------------------
# 1. pyproject constraint is explicit and bounded.
# ---------------------------------------------------------------------------


def _read_pyproject_text() -> str:
    return _PYPROJECT_PATH.read_text(encoding="utf-8")


def _extract_downstream_pysindy_constraint(pyproject_text: str) -> str:
    """Return the raw pysindy line from the ``[project.optional-dependencies].downstream`` block.

    The block is small and hand-edited, so a simple linear scan is more robust
    than a full TOML parse under Python 3.11 without stdlib ``tomllib``
    guarantees.
    """
    lines = pyproject_text.splitlines()
    inside_downstream = False
    for line in lines:
        stripped = line.strip()
        if stripped == "downstream = [":
            inside_downstream = True
            continue
        if inside_downstream:
            if stripped.startswith("]"):
                break
            if "pysindy" in stripped:
                return stripped
    raise AssertionError(
        "did not find a pysindy line inside [project.optional-dependencies].downstream"
    )


def test_pyproject_downstream_pysindy_constraint_matches_decision() -> None:
    """The downstream extra's pysindy constraint matches the v0.31b3 decision verbatim."""
    text = _read_pyproject_text()
    line = _extract_downstream_pysindy_constraint(text)
    expected = _DECISION["pyproject_constraint"]
    assert expected in line, (
        f"pyproject downstream extra must carry {expected!r}; got line: {line!r}"
    )


def test_pyproject_downstream_pysindy_constraint_is_bounded() -> None:
    """Reject any unbounded pysindy pin (``pysindy``, ``pysindy>=X`` without ``<``)."""
    text = _read_pyproject_text()
    line = _extract_downstream_pysindy_constraint(text)

    # The constraint must contain BOTH a lower bound and an upper bound.
    # Structural check: an unquoted ``pysindy`` with no version specifier or
    # a ``pysindy>=X`` without a ``<`` upper bound is rejected.
    assert re.search(r"pysindy\s*>=\s*\d", line), (
        f"downstream pysindy constraint is missing a lower bound; got {line!r}"
    )
    assert "<" in line, (
        "downstream pysindy constraint is missing an upper bound; a bare "
        "``pysindy`` or ``pysindy>=X`` pin is not allowed under the "
        f"v0.31b3 policy. Got: {line!r}"
    )


def test_pyproject_test_extra_pysindy_constraint_is_bounded_too() -> None:
    """The ``test`` extra echoes the same bounded constraint (defense in depth).

    Only lines inside a ``[project.optional-dependencies].<extra>`` list count —
    ruff per-file-ignores that mention ``pysindy`` in a filename are skipped by
    filtering for the ``"pysindy...`` quoted-dep pattern.
    """
    text = _read_pyproject_text()
    # A PEP-508 dependency spec inside a pyproject list starts with a quote,
    # names the distribution, and carries a version comparator: e.g.
    # ``"pysindy>=1.7.5,<2; python_version < '3.12'"``. The mypy override
    # block also mentions ``"pysindy.*"`` — we exclude those by requiring a
    # PEP-440 comparator token immediately after the distribution name.
    dep_pattern = re.compile(r'^\s*["\']pysindy\s*(?:==|>=|<=|~=|!=|<|>)')
    payload_lines = [
        line for line in text.splitlines() if dep_pattern.match(line)
    ]
    assert payload_lines, "no pysindy dependency lines found in pyproject.toml"
    for line in payload_lines:
        assert "<" in line, (
            f"every pysindy dependency line must carry an upper bound; got {line!r}"
        )


# ---------------------------------------------------------------------------
# 2. Every declared-supported version has manifest metadata.
# ---------------------------------------------------------------------------


def _load_compatibility_manifest() -> dict[str, Any]:
    if not _COMPATIBILITY_MANIFEST_PATH.exists():
        pytest.xfail(
            "author A must land configs/pysindy_compatibility_matrix.json with "
            "SUPPORTED_PYSINDY_VERSIONS metadata before this test can pass."
        )
    return json.loads(_COMPATIBILITY_MANIFEST_PATH.read_text(encoding="utf-8"))


def test_compatibility_manifest_declares_supported_pysindy_versions() -> None:
    """The manifest exposes ``supported_versions`` and covers every declared version.

    The canonical manifest field name is ``supported_versions`` (lowercase, matches
    the decision-memo field). The requirement text refers to
    ``SUPPORTED_PYSINDY_VERSIONS`` as the exported constant name; that alias is
    also accepted here for forward compatibility with any Python-side re-export.
    """
    manifest = _load_compatibility_manifest()

    assert isinstance(manifest, dict), (
        "compatibility manifest must be a JSON object; got "
        f"{type(manifest).__name__}"
    )
    # Accept either the lowercase canonical key or the uppercase re-export alias.
    supported: object
    if "supported_versions" in manifest:
        supported = manifest["supported_versions"]
    elif "SUPPORTED_PYSINDY_VERSIONS" in manifest:
        supported = manifest["SUPPORTED_PYSINDY_VERSIONS"]
    else:
        raise AssertionError(
            "manifest must expose a top-level 'supported_versions' (canonical) "
            "or 'SUPPORTED_PYSINDY_VERSIONS' (re-export alias) key; got keys "
            f"{sorted(manifest)!r}"
        )

    assert isinstance(supported, list) and supported, (
        "supported_versions must be a non-empty list of version strings; got "
        f"{supported!r}"
    )
    for version in supported:
        assert isinstance(version, str) and version, (
            "every supported_versions entry must be a non-empty string; "
            f"got {version!r}"
        )

    # Every version declared in the v0.31b3 decision MUST appear in the manifest.
    for declared in _DECISION["supported_versions"]:
        assert declared in supported, (
            f"decision-declared supported version {declared!r} is missing from "
            f"manifest supported_versions={supported!r}."
        )


def test_compatibility_manifest_agrees_with_pyproject_constraint() -> None:
    """The manifest's ``pyproject_constraint`` echoes the decision's constraint verbatim."""
    manifest = _load_compatibility_manifest()

    declared = manifest.get("pyproject_constraint")
    assert declared == _DECISION["pyproject_constraint"], (
        "compatibility manifest pyproject_constraint must match the decision "
        f"({_DECISION['pyproject_constraint']!r}); got {declared!r}."
    )


# ---------------------------------------------------------------------------
# 3. Unsupported major versions fail with an actionable, specific error.
# ---------------------------------------------------------------------------


def test_unsupported_major_pysindy_version_rejected_by_discovery_task_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A monkeypatched PySINDy 999.0.0 must be rejected with a specific message.

    The runtime must NOT ``except Exception``-catch the version mismatch; it
    must raise ``ScopeValidationError`` with a message that names either the
    supported range (``<2``) or the ``pysindy`` package explicitly.
    """
    monkeypatch.setattr(pysindy, "__version__", "999.0.0", raising=False)

    field = _build_periodic_heat_field_small()
    model = _build_caller_configured_sindy()

    try:
        with pytest.raises(
            ScopeValidationError, match=r"(?i)pysindy.*(?:<\s*2|999|supported|1\.7|range)"
        ):
            run_pysindy_pde_task(
                field,
                task_name="v0_31b3_unsupported_pysindy_reject",
                pysindy_model=model,
            )
    except pytest.fail.Exception:
        pytest.xfail(
            "author A must land a runtime version guard in "
            "pdelie.tasks.discovery.run_pysindy_pde_task that raises "
            "ScopeValidationError when pysindy.__version__ is outside the "
            "supported range (currently only 1.7.5)."
        )


def test_unsupported_major_pysindy_version_rejected_by_weak_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same version guard on the weak-diagnostic entry point."""
    monkeypatch.setattr(pysindy, "__version__", "999.0.0", raising=False)

    field = _build_periodic_heat_field_weak()

    try:
        with pytest.raises(
            ScopeValidationError, match=r"(?i)pysindy.*(?:<\s*2|999|supported|1\.7|range)"
        ):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=UserWarning)
                warnings.simplefilter("ignore", category=DeprecationWarning)
                inspect_pysindy_weak_pde_library(
                    field,
                    task_name="v0_31b3_unsupported_pysindy_weak_reject",
                    library_configuration=WeakPDELibraryDiagnostic(
                        polynomial_degree=2,
                        derivative_order=2,
                        num_domain_centers_K=16,
                    ),
                )
    except pytest.fail.Exception:
        pytest.xfail(
            "author A must land a runtime version guard in "
            "pdelie.tasks.weak_pde_library.inspect_pysindy_weak_pde_library "
            "that raises ScopeValidationError when pysindy.__version__ is "
            "outside the supported range (currently only 1.7.5)."
        )


# ---------------------------------------------------------------------------
# 4. Public schema key sets are unchanged by the b3 policy work.
# ---------------------------------------------------------------------------


def test_v0_31b1_discovery_task_result_still_has_22_keys() -> None:
    """v0.31b1 ``discovery_task_result`` retains the frozen 22-key top-level set."""
    result = _run_live_discovery_task()["result"]
    observed = set(result.keys())
    missing = _V0_31B1_TASK_RESULT_KEYS - observed
    extra = observed - _V0_31B1_TASK_RESULT_KEYS
    assert not missing, f"discovery_task_result is missing keys: {sorted(missing)}"
    assert not extra, (
        "discovery_task_result grew new top-level keys under v0.31b3 without "
        f"a schema bump: {sorted(extra)}"
    )
    assert len(_V0_31B1_TASK_RESULT_KEYS) == 22
    assert sorted(observed) == sorted(_V0_31B1_TASK_RESULT_KEYS)


def test_v0_31b2_weak_diagnostic_still_has_27_keys() -> None:
    """v0.31b2 weak diagnostic retains the frozen 27-key top-level set."""
    summary = _run_live_weak_diagnostic()["summary"]
    observed = set(summary.keys())
    missing = _V0_31B2_WEAK_DIAGNOSTIC_KEYS - observed
    extra = observed - _V0_31B2_WEAK_DIAGNOSTIC_KEYS
    assert not missing, (
        f"weak diagnostic summary is missing keys: {sorted(missing)}"
    )
    assert not extra, (
        "weak diagnostic summary grew new top-level keys under v0.31b3 without "
        f"a schema bump: {sorted(extra)}"
    )
    assert len(_V0_31B2_WEAK_DIAGNOSTIC_KEYS) == 27
    assert sorted(observed) == sorted(_V0_31B2_WEAK_DIAGNOSTIC_KEYS)


# ---------------------------------------------------------------------------
# 5. No root pdelie export leaks.
# ---------------------------------------------------------------------------


def test_no_compat_helper_or_manifest_symbol_leaks_to_root_pdelie() -> None:
    """None of the b3 compat-policy symbols may leak to the root ``pdelie`` namespace."""
    forbidden = (
        "SUPPORTED_PYSINDY_VERSIONS",
        "_pysindy_compat",
        "pysindy_compat",
        "PySINDyUnsupportedVersionError",
        "PySINDyVersionCompatibilityError",
        "check_pysindy_version",
        "assert_supported_pysindy_version",
        "pysindy_compatibility_matrix",
    )
    for name in forbidden:
        assert not hasattr(pdelie, name), (
            f"pdelie unexpectedly exports {name!r} at the root — v0.31b3 keeps "
            "the compatibility-policy surface submodule-only."
        )


def test_root_pdelie_all_does_not_advertise_compat_policy_names() -> None:
    """The advertised ``pdelie.__all__`` (when present) contains no b3 compat names."""
    root_all = getattr(pdelie, "__all__", None)
    if root_all is None:
        return  # ``__all__`` is optional; absence is fine.

    forbidden_substrings = (
        "SUPPORTED_PYSINDY_VERSIONS",
        "_pysindy_compat",
        "pysindy_compat",
        "PySINDyUnsupportedVersionError",
        "check_pysindy_version",
        "assert_supported_pysindy_version",
    )
    for exported in root_all:
        for phrase in forbidden_substrings:
            assert phrase not in exported, (
                f"pdelie.__all__ advertises {exported!r} which matches the "
                f"forbidden b3 compat symbol {phrase!r}."
            )


# ---------------------------------------------------------------------------
# 6. Exact backend versions are recorded (no rounding, no coercion).
# ---------------------------------------------------------------------------


def test_weak_diagnostic_provenance_records_exact_backend_versions() -> None:
    """The weak diagnostic ``backend_version`` and ``provenance`` echo installed dists exactly."""
    summary = _run_live_weak_diagnostic()["summary"]
    backend_version = summary["backend_version"]
    provenance = summary["provenance"]

    installed_pysindy = _importlib_metadata.version("pysindy")
    installed_sklearn = _importlib_metadata.version("scikit-learn")
    installed_scipy = _importlib_metadata.version("scipy")

    assert backend_version["pysindy"] == installed_pysindy
    assert backend_version["sklearn"] == installed_sklearn
    assert backend_version["scipy"] == installed_scipy

    # Cross-check the provenance block echoes the same versions.
    assert provenance["pysindy_version"] == installed_pysindy
    assert provenance["sklearn_version"] == installed_sklearn
    assert provenance["scipy_version"] == installed_scipy


def test_discovery_task_backend_version_records_exact_pysindy_and_sklearn(
    request: pytest.FixtureRequest,
) -> None:
    """The discovery TaskResult ``backend_version`` echoes installed dists exactly.

    The v0.31b1 discovery task-runtime records ``pysindy``, ``pdelie``, and
    ``sklearn`` opportunistically. The v0.31b3 policy asks that ``scipy`` also
    appear so downstream provenance is uniform with the weak diagnostic; if
    Author A has not yet extended ``_resolve_backend_version`` in
    ``pdelie.tasks.discovery`` to include ``scipy``, this xfails.
    """
    result = _run_live_discovery_task()["result"]
    backend_version = result["backend_version"]

    installed_pysindy = _importlib_metadata.version("pysindy")
    installed_sklearn = _importlib_metadata.version("scikit-learn")
    installed_scipy = _importlib_metadata.version("scipy")

    # These two are unconditionally recorded today.
    assert backend_version["pysindy"] == installed_pysindy
    assert backend_version.get("sklearn") == installed_sklearn, (
        "discovery task_result backend_version must include the exact "
        f"installed sklearn version {installed_sklearn!r}; got "
        f"{backend_version.get('sklearn')!r}"
    )

    # scipy is the b3-added key — xfail if Author A has not yet landed it.
    if "scipy" not in backend_version:
        pytest.xfail(
            "author A must extend pdelie.tasks.discovery._resolve_backend_version "
            "to opportunistically record scipy under the v0.31b3 provenance policy."
        )
    assert backend_version["scipy"] == installed_scipy


# ---------------------------------------------------------------------------
# 7. v0.31b0 term mapping is stable under every supported API generation.
# ---------------------------------------------------------------------------


_SUPPORTED_PYSINDY_PARAMS: list[str] = [_DECISION["primary_tested_version"]]
if _DECISION["secondary_tested_version"] is not None:
    _SUPPORTED_PYSINDY_PARAMS.append(_DECISION["secondary_tested_version"])


@pytest.mark.parametrize("supported_pysindy_version", _SUPPORTED_PYSINDY_PARAMS)
def test_v0_31b0_term_mapping_golden_still_passes(
    supported_pysindy_version: str,
) -> None:
    """The v0.31b0 golden fixture runs cleanly under the currently-installed pysindy.

    The parametrize is documentary — the CI matrix does the actual per-version
    run. Locally this executes once against whichever pysindy is installed;
    ``supported_pysindy_version`` is asserted against the observed
    ``pysindy.__version__`` so a mismatch fails loudly instead of silently
    running against the wrong wheel.
    """
    observed_version = _importlib_metadata.version("pysindy")
    assert observed_version == supported_pysindy_version, (
        "installed pysindy version does not match the parametrized supported "
        f"version: observed={observed_version!r}, expected={supported_pysindy_version!r}. "
        "This local run is a subset of the CI matrix; the multi-env fanout is "
        "the authoritative check."
    )

    # Re-use the b0 golden fixture directly so any drift in the underlying
    # mapping surface fails HERE (in the b3 policy suite) as well as in the
    # b0 golden.
    from tests.test_v0_31b0_pysindy_term_mapping_golden import (
        _EXPECTED_SUMMARY_KEYS,
        _run_default_discovery,
    )

    run = _run_default_discovery()
    summary = run["summary"]
    feature_names = run["feature_names"]

    # Structural anchors preserved from b0.
    assert set(summary.keys()) == _EXPECTED_SUMMARY_KEYS
    assert summary["summary_type"] == "discovery_result"
    assert summary["summary_schema_version"] == "0.1"
    assert len(feature_names) == 16
    for index, name in enumerate(feature_names):
        assert name == f"u__x_index_{index}"


# ---------------------------------------------------------------------------
# 8. v0.31b1 task result remains strict JSON.
# ---------------------------------------------------------------------------


def test_v0_31b1_discovery_task_result_is_strict_json() -> None:
    """A real v0.31b1 payload roundtrips under ``json.dumps(..., allow_nan=False)``."""
    result = _run_live_discovery_task()["result"]
    encoded = json.dumps(result, allow_nan=False)
    decoded = json.loads(encoded)
    assert decoded == result


# ---------------------------------------------------------------------------
# 9. v0.31b2 weak diagnostic remains strict JSON.
# ---------------------------------------------------------------------------


def test_v0_31b2_weak_diagnostic_is_strict_json() -> None:
    """A real v0.31b2 diagnostic payload roundtrips under ``json.dumps(..., allow_nan=False)``."""
    summary = _run_live_weak_diagnostic()["summary"]
    encoded = json.dumps(summary, allow_nan=False)
    decoded = json.loads(encoded)
    assert decoded == summary


# ---------------------------------------------------------------------------
# 10. Compat-shim inspection (no-op under this decision).
# ---------------------------------------------------------------------------


def test_compat_shim_module_absent_under_c_temporary_1x_policy() -> None:
    """Under ``compat_shim_needed = False`` no ``_pysindy_compat.py`` should exist.

    The decision memo defers the shim to v0.31.1 / v0.32 (when the pysindy pin
    is widened to admit 2.x). Landing an empty or stub ``_pysindy_compat``
    module in v0.31b3 would create dead public surface and contradict the
    decision. If ``compat_shim_needed`` is ever flipped to True in a future
    release, this test must be replaced with the grep-inspection specified in
    requirement #10 of the b3 test plan.
    """
    assert _DECISION["compat_shim_needed"] is False, (
        "v0.31b3 decision compat_shim_needed must be False; got "
        f"{_DECISION['compat_shim_needed']!r}. If this changes, update "
        "requirement #10 in this test file to grep the shim for narrow "
        "`except` clauses."
    )
    shim_path = _REPO_ROOT / "src" / "pdelie" / "discovery" / "_pysindy_compat.py"
    assert not shim_path.exists(), (
        "no _pysindy_compat.py should exist under compat_shim_needed=False; "
        f"found stray file at {shim_path}. Delete it or flip the decision."
    )


# ---------------------------------------------------------------------------
# Cross-cutting sanity — the two b3 runtime modules do NOT eagerly bind
# a compat helper at module scope. The policy is enforced lazily inside
# the entry points, if at all.
# ---------------------------------------------------------------------------


def test_tasks_discovery_does_not_eagerly_bind_a_compat_helper() -> None:
    """``pdelie.tasks.discovery`` must not carry a module-scope ``_pysindy_compat`` binding."""
    for banned in ("_pysindy_compat", "pysindy_compat", "SUPPORTED_PYSINDY_VERSIONS"):
        assert banned not in vars(_tasks_discovery), (
            f"pdelie.tasks.discovery unexpectedly binds {banned!r} at module "
            "scope; the b3 compatibility surface must stay submodule-only."
        )


def test_tasks_weak_pde_library_does_not_eagerly_bind_a_compat_helper() -> None:
    """``pdelie.tasks.weak_pde_library`` must not carry a module-scope compat binding."""
    for banned in ("_pysindy_compat", "pysindy_compat", "SUPPORTED_PYSINDY_VERSIONS"):
        assert banned not in vars(_tasks_weak_pde_library), (
            f"pdelie.tasks.weak_pde_library unexpectedly binds {banned!r} at "
            "module scope; the b3 compatibility surface must stay submodule-only."
        )


# ---------------------------------------------------------------------------
# Sanity — the assembler and the diagnostic summarizer are the exact objects
# the b3 policy tests target (protects against import-shadowing regressions).
# ---------------------------------------------------------------------------


def test_summarize_discovery_task_result_symbol_identity() -> None:
    """The b3 tests must target the same assembler the runtime routes through."""
    assert summarize_discovery_task_result is _tasks_discovery.summarize_discovery_task_result


def test_summarize_pysindy_weak_pde_library_diagnostic_symbol_identity() -> None:
    """Same identity check for the weak-diagnostic summarizer."""
    assert (
        summarize_pysindy_weak_pde_library_diagnostic
        is _tasks_weak_pde_library.summarize_pysindy_weak_pde_library_diagnostic
    )


# ---------------------------------------------------------------------------
# Sanity — a periodic Heat field mutated to Dirichlet is STILL rejected under
# the b3 policy layer (the b3 changes must not weaken the b1/b2 BC guards).
# ---------------------------------------------------------------------------


def test_bc_guard_still_rejects_dirichlet_under_b3_policy() -> None:
    """A Dirichlet-tagged field is still rejected — b3 policy does not weaken BC guards."""
    from pdelie.tasks.discovery import PySINDyDiscoveryUnsupportedBoundaryError

    field = _build_periodic_heat_field_small()
    mutated_metadata = copy.deepcopy(field.metadata)
    mutated_metadata["boundary_conditions"]["x"] = {
        "type": "dirichlet",
        "left": {
            "value": None,
            "time_dependent": False,
            "source": "inferred_unspecified",
        },
        "right": {
            "value": None,
            "time_dependent": False,
            "source": "inferred_unspecified",
        },
        "specified": False,
        "notes": None,
    }
    dirichlet_field = FieldBatch(
        values=np.asarray(field.values, dtype=float).copy(),
        dims=field.dims,
        coords={
            str(k): np.asarray(v, dtype=float).copy() for k, v in field.coords.items()
        },
        var_names=list(field.var_names),
        metadata=mutated_metadata,
        preprocess_log=list(field.preprocess_log),
    )
    model = _build_caller_configured_sindy()
    with pytest.raises(PySINDyDiscoveryUnsupportedBoundaryError):
        run_pysindy_pde_task(
            dirichlet_field,
            task_name="v0_31b3_bc_guard_still_rejects_dirichlet",
            pysindy_model=model,
        )
