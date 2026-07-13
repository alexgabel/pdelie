"""v0.31b0 golden test — pin the PySINDy feature-name / term-mapping surface.

Purpose
-------
This test is authored BEFORE the v0.31b1 downstream ``TaskResult`` runtime is
written. Its job is to characterize the *current* PySINDy adapter + bridge +
``summarize_discovery_result`` mapping surface — the exact strings, shapes, and
top-level keys the v0.30 release ships — so that when the v0.31b1 task runner
composes on top of this surface, any accidental change to the underlying
mapping is caught here rather than silently absorbed into the new runner.

Concretely, this file pins:

* The feature-name string convention emitted by ``to_pysindy_trajectories``
  (``f"{var}__x_index_{i}"``) — because the v0.31b1 runner will be defined to
  route through this bridge and inherit these names.
* The PolynomialLibrary(degree=2) *shape* of ``library_feature_names`` — as a
  ``list[str]`` of unique non-empty tokens — without asserting specific term
  content (the raw content is a PySINDy internal we only rely on structurally).
* The ``summarize_discovery_result`` top-level keyset (exactly 17 keys) and the
  frozen inner shapes of ``coefficient_summary``, ``residuals``, and
  ``equation_terms``.
* The ``returns_coefficients=False`` invariant that guarantees the summary
  strips the raw coefficient matrix before serialization.

Deliberate non-goals
--------------------
* We do NOT pin STLSQ-selected term names — with ``threshold=0.1`` and a tiny
  random Heat batch, the selected support is fragile. Only structural keys
  (``equation_terms.keys() == feature_names``) are pinned.
* We do NOT pin numeric coefficient values. Those are backend-numerics.

Pattern
-------
Follows ``tests/test_discovery_task_result_schema.py`` — module-level
``pytest.importorskip`` for the optional backend, deterministic seed, and a
cached single-invocation helper so all tests share one bridge/adapter run.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip(
    "pysindy",
    reason="pysindy is an optional backend; term-mapping golden is skipped when unavailable.",
)

from pdelie.data import generate_heat_1d_field_batch
from pdelie.discovery import (
    fit_pysindy_discovery,
    summarize_discovery_result,
    to_pysindy_trajectories,
)

# Deterministic tiny fixture — mirrors the tiny-fixture pattern used in
# tests/test_pysindy_discovery_adapter.py and tests/test_v0_7_release_gate.py.
_BATCH_SIZE = 1
_NUM_TIMES = 5
_NUM_POINTS = 16
_SEED = 310

# The frozen v0.30 top-level keyset of ``summarize_discovery_result`` output.
# Any addition/removal of a top-level summary field must be a deliberate schema
# bump — this frozenset makes that bump loud.
_EXPECTED_SUMMARY_KEYS: frozenset[str] = frozenset(
    {
        "summary_schema_version",
        "summary_type",
        "source_result_id",
        "status",
        "backend",
        "feature_names",
        "library_feature_names",
        "equation_terms",
        "equation_strings",
        "coefficient_summary",
        "support_epsilon",
        "fit_diagnostics",
        "fit_config",
        "failure_reason",
        "residuals",
        "recovery",
        "returns_coefficients",
    }
)

_EXPECTED_COEFFICIENT_SUMMARY_KEYS: frozenset[str] = frozenset(
    {"present", "shape", "finite", "l2_norm", "linf_norm", "nonzero_count"}
)

_EXPECTED_RESIDUAL_INNER_KEYS: frozenset[str] = frozenset(
    {"size", "l2_norm", "rms", "max_abs"}
)

# One-shot cache of the (result, summary, feature_names, library_feature_names)
# tuple so all tests share a single PySINDy invocation.
_CACHED_RUN: dict[str, Any] | None = None


def _run_default_discovery() -> dict[str, Any]:
    """Run the full bridge → adapter → summarize chain once and cache the result.

    Returns a dict with keys:
        - ``field`` — the small deterministic Heat FieldBatch
        - ``feature_names`` — bridge-emitted feature names (list[str])
        - ``result`` — raw adapter dict (fit_pysindy_discovery output)
        - ``summary`` — the ``summarize_discovery_result`` payload

    Cached at module scope; a repeat call is O(1).
    """
    global _CACHED_RUN
    if _CACHED_RUN is not None:
        return _CACHED_RUN

    field = generate_heat_1d_field_batch(
        batch_size=_BATCH_SIZE,
        num_times=_NUM_TIMES,
        num_points=_NUM_POINTS,
        seed=_SEED,
    )
    trajectories, time_values, feature_names = to_pysindy_trajectories(field)
    result = fit_pysindy_discovery(trajectories, time_values, feature_names)
    summary = summarize_discovery_result(result)

    _CACHED_RUN = {
        "field": field,
        "feature_names": list(feature_names),
        "result": result,
        "summary": summary,
    }
    return _CACHED_RUN


# Sanity: the test file lives alongside the rest of the discovery suite.
assert Path(__file__).parent.name == "tests"


def test_to_pysindy_trajectories_feature_name_convention() -> None:
    """Pin the bridge's feature-name string format ``f"{var}__x_index_{i}"``.

    The v0.31b1 task runner will inherit these names; if the bridge ever
    renames its emitted columns, this test forces a deliberate schema decision.
    """
    run = _run_default_discovery()
    feature_names = run["feature_names"]

    assert isinstance(feature_names, list)
    assert len(feature_names) == _NUM_POINTS
    for index, name in enumerate(feature_names):
        assert name == f"u__x_index_{index}", (
            "bridge feature-name convention drifted: "
            f"expected 'u__x_index_{index}', got {name!r}"
        )
    # No duplicates — the summary's uniqueness invariant depends on this.
    assert len(set(feature_names)) == len(feature_names)


def test_fit_pysindy_discovery_default_config_summary_keyset() -> None:
    """The summary top-level keyset with ``config=None`` matches the frozen 17-key set.

    Uses set-equality against a hard-coded frozenset so any accidental key
    rename/addition/removal in the mapping surface fails loudly here.
    """
    run = _run_default_discovery()
    summary = run["summary"]

    assert set(summary.keys()) == _EXPECTED_SUMMARY_KEYS


def test_summarize_discovery_result_library_feature_names_shape() -> None:
    """``library_feature_names`` is a ``list[str]`` of unique non-empty tokens.

    We deliberately do NOT pin the exact PolynomialLibrary(degree=2) term
    content — PySINDy owns that string surface. We only pin the structural
    contract downstream consumers (and the v0.31b1 runner) will rely on.
    """
    run = _run_default_discovery()
    summary = run["summary"]

    library_feature_names = summary["library_feature_names"]
    assert isinstance(library_feature_names, list)
    assert len(library_feature_names) > 0
    for token in library_feature_names:
        assert isinstance(token, str)
        assert token, "library feature names must be non-empty strings"
    assert len(set(library_feature_names)) == len(library_feature_names), (
        "library_feature_names must be unique"
    )


def test_summarize_discovery_result_equation_terms_shape() -> None:
    """``equation_terms`` is ``dict[str, dict[str, float]]`` keyed by feature_names.

    Pins the KEY SET (equation_terms.keys() == feature_names) and the inner
    value-typing contract. Does NOT pin specific selected terms — STLSQ's
    threshold=0.1 on a tiny random batch makes term content fragile.
    """
    run = _run_default_discovery()
    summary = run["summary"]
    feature_names = run["feature_names"]

    equation_terms = summary["equation_terms"]
    assert isinstance(equation_terms, dict)
    assert set(equation_terms.keys()) == set(feature_names)
    for feature_name, term_map in equation_terms.items():
        assert isinstance(feature_name, str)
        assert isinstance(term_map, dict), (
            f"equation_terms[{feature_name!r}] must be a dict"
        )
        for term_name, coefficient in term_map.items():
            assert isinstance(term_name, str) and term_name
            assert isinstance(coefficient, float), (
                f"equation_terms[{feature_name!r}][{term_name!r}] must be a "
                f"float, got {type(coefficient).__name__}"
            )

    # And equation_strings mirrors the same key set with str values.
    equation_strings = summary["equation_strings"]
    assert isinstance(equation_strings, dict)
    assert set(equation_strings.keys()) == set(feature_names)
    for value in equation_strings.values():
        assert isinstance(value, str)


def test_coefficient_summary_frozen_keyset() -> None:
    """The nested ``coefficient_summary`` payload carries exactly six frozen keys.

    Pinning this keyset here means the v0.31b1 runner can compose its own
    ``coefficient_relative_l2`` fields on top without accidentally shadowing
    one of the six low-level fields.
    """
    run = _run_default_discovery()
    summary = run["summary"]

    coefficient_summary = summary["coefficient_summary"]
    assert isinstance(coefficient_summary, dict)
    assert set(coefficient_summary.keys()) == _EXPECTED_COEFFICIENT_SUMMARY_KEYS

    # ``present`` must be a bool; the other numeric fields are None-or-numeric.
    assert isinstance(coefficient_summary["present"], bool)
    if coefficient_summary["present"]:
        shape = coefficient_summary["shape"]
        assert isinstance(shape, list) and len(shape) == 2
        assert all(isinstance(dim, int) for dim in shape)
        assert isinstance(coefficient_summary["finite"], bool)
        assert isinstance(coefficient_summary["nonzero_count"], int)


def test_residuals_shape() -> None:
    """``residuals`` is ``{train, heldout}`` where each is None or the four-key block.

    Pins the two-slot residual container so v0.31b1 can safely lift
    ``train_residual`` / ``heldout_residual`` to the top-level TaskResult.
    """
    run = _run_default_discovery()
    summary = run["summary"]

    residuals = summary["residuals"]
    assert isinstance(residuals, dict)
    assert set(residuals.keys()) == {"train", "heldout"}
    for slot_name in ("train", "heldout"):
        slot = residuals[slot_name]
        assert slot is None or isinstance(slot, dict), (
            f"residuals[{slot_name!r}] must be None or a dict"
        )
        if isinstance(slot, dict):
            assert set(slot.keys()) == _EXPECTED_RESIDUAL_INNER_KEYS


def test_returns_coefficients_is_false() -> None:
    """The summary strips the raw coefficient matrix (``returns_coefficients`` is False).

    This is the load-bearing invariant that keeps the JSON payload compact and
    prevents the summary from becoming a de-facto model-serialization surface.
    """
    run = _run_default_discovery()
    summary = run["summary"]

    assert summary["returns_coefficients"] is False
    # And no raw ``coefficients`` array key leaks in at the top level.
    assert "coefficients" not in summary


def test_no_regression_in_summarize_discovery_result_key_set() -> None:
    """Golden — the FULL top-level keyset matches the frozen 17-key set exactly.

    This is the single most important test in this file. It anchors the entire
    ``summarize_discovery_result`` schema against silent drift.

    * ``summary_schema_version`` is pinned to ``"0.1"``.
    * ``summary_type`` is pinned to ``"discovery_result"``.
    * All 17 top-level keys are present; no extras.
    """
    run = _run_default_discovery()
    summary = run["summary"]

    assert summary["summary_schema_version"] == "0.1"
    assert summary["summary_type"] == "discovery_result"

    observed = set(summary.keys())
    missing = _EXPECTED_SUMMARY_KEYS - observed
    extra = observed - _EXPECTED_SUMMARY_KEYS
    assert not missing, f"summary is missing frozen keys: {sorted(missing)}"
    assert not extra, (
        "summary grew new top-level keys without a schema bump: "
        f"{sorted(extra)}"
    )
    assert len(_EXPECTED_SUMMARY_KEYS) == 17
