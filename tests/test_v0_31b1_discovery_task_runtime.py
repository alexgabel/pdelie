"""v0.31b1 tests for the ``pdelie.tasks.discovery`` runtime.

This suite exercises the composed ``discovery_task_result`` payload returned
by :func:`pdelie.tasks.discovery.run_pysindy_pde_task`, plus the direct
strict-JSON payload assembler
:func:`pdelie.tasks.discovery.summarize_discovery_task_result` for the
invariants that do not depend on a live PySINDy fit.

The strict-JSON adversarial tests (NaN/Inf) build a payload directly via the
assembler so they run even when ``pysindy`` is not installed. The
composition-boundary spy test patches ``_validate_strict_json_compatible`` at
module scope so we can prove the runtime routes the composed payload through
the strict validator exactly once — this is the load-bearing check the peer
memo review flagged as absent in v0.31a.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from unittest.mock import MagicMock

import numpy as np
import pytest

import pdelie
import pdelie.tasks.discovery as _tasks_discovery
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.tasks.discovery import (
    _PYSINDY_BRIDGE_VARIANT,
    _SUMMARY_SCHEMA_VERSION,
    _SUMMARY_TYPE,
    _TASK_RESULT_TOP_LEVEL_KEYS,
    _UNDERLYING_KEY,
    PDELIE_MASK_DIAGNOSTICS_KEY,
    PySINDyDiscoveryUnsupportedBoundaryError,
    run_pysindy_pde_task,
    summarize_discovery_task_result,
)

pysindy = pytest.importorskip(
    "pysindy",
    reason="pysindy is an optional backend; v0.31b1 task-runtime tests are skipped when unavailable.",
)

from pdelie.data import generate_heat_1d_field_batch  # noqa: E402 — post-importorskip
from pdelie.discovery import summarize_discovery_result, to_pysindy_trajectories  # noqa: E402
from pdelie.discovery.pysindy_adapter import fit_pysindy_discovery  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_BATCH_SIZE = 1
_NUM_TIMES = 5
_NUM_POINTS = 16
_SEED = 3110


def _build_heat_field() -> Any:
    return generate_heat_1d_field_batch(
        batch_size=_BATCH_SIZE,
        num_times=_NUM_TIMES,
        num_points=_NUM_POINTS,
        seed=_SEED,
    )


def _build_caller_configured_sindy() -> Any:
    """A caller-configured PySINDy model that composes with the periodic bridge."""
    optimizer = pysindy.STLSQ(threshold=0.1, alpha=0.05, max_iter=20)
    feature_library = pysindy.PolynomialLibrary(degree=2, include_bias=True)
    differentiation_method = pysindy.FiniteDifference()
    return pysindy.SINDy(
        optimizer=optimizer,
        feature_library=feature_library,
        differentiation_method=differentiation_method,
    )


def _build_minimal_valid_task_result_payload(
    *, target_convention: str = "pde_library"
) -> dict[str, Any]:
    """Mirror of the design-only fixture in ``test_discovery_task_result_schema.py``.

    Kept independent of a live PySINDy fit so the strict-JSON adversarial
    tests can run under any environment.
    """
    weak_contract: dict[str, Any] | None
    if target_convention == "weak_pde_library":
        weak_contract = {
            "method_family": "pysindy_weak_pde_library_polynomial_gauss_v1",
            "test_function_family": "pysindy_weak_pde_library_polynomial_bump_v1",
            "quadrature_rule": "pysindy_weak_pde_library_composite_gauss_v1",
            "diagnostic_only": True,
        }
    else:
        weak_contract = None

    return {
        "task_name": "heat_pysindy_pde_task_smoke",
        "backend_name": "pysindy",
        "backend_version": {
            "pysindy": "1.7.5",
            "sklearn": "1.4.0",
            "pdelie": "0.30.0",
        },
        "target_convention": target_convention,
        "input_layout": "scalar_1d_uniform",
        "derivative_backend": "FiniteDifference",
        "pysindy_bridge_variant": "periodic_only_v1",
        "library_feature_names": ["u", "u_x", "u_xx", "u*u_x"],
        "selected_terms": {"x0": {"u_xx": 0.1}},
        "coefficients": None,
        "support_precision": 1.0,
        "support_recall": 1.0,
        "support_f1": 1.0,
        "exact_support": True,
        "coefficient_relative_l2": 0.0,
        "train_residual": {
            "size": 128,
            "l2_norm": 0.01,
            "rms": 0.001,
            "max_abs": 0.002,
        },
        "heldout_residual": None,
        "weak_contract": weak_contract,
        "warnings": [],
        "underlying_discovery_result": {
            "summary_schema_version": "0.1",
            "summary_type": "discovery_result",
            "status": "success",
            "backend": "pysindy",
            "feature_names": ["x0"],
            "library_feature_names": ["u", "u_x", "u_xx", "u*u_x"],
            "equation_terms": {"x0": {"u_xx": 0.1}},
            "equation_strings": {"x0": "0.100 u_xx"},
            "coefficient_summary": {
                "present": True,
                "shape": [1, 4],
                "finite": True,
                "l2_norm": 0.1,
                "linf_norm": 0.1,
                "nonzero_count": 1,
            },
            "support_epsilon": 1e-8,
            "fit_diagnostics": {},
            "fit_config": {},
            "failure_reason": None,
            "residuals": {"train": None, "heldout": None},
            "recovery": None,
            "returns_coefficients": False,
        },
    }


# Cache one live task-runtime invocation so all live-path tests share it.
_LIVE_CACHE: dict[str, Any] | None = None


def _run_live_task() -> dict[str, Any]:
    global _LIVE_CACHE
    if _LIVE_CACHE is not None:
        return _LIVE_CACHE
    field = _build_heat_field()
    model = _build_caller_configured_sindy()
    result = run_pysindy_pde_task(
        field,
        task_name="heat_1d_v0_31b1_smoke",
        pysindy_model=model,
    )
    _LIVE_CACHE = {"field": field, "result": result}
    return _LIVE_CACHE


# ---------------------------------------------------------------------------
# 1. Happy-path invariants (live task-runtime)
# ---------------------------------------------------------------------------


def test_valid_periodic_pdelibrary_task_produces_discovery_task_result_summary() -> None:
    """Happy path — the composed payload carries the frozen schema literals."""
    run = _run_live_task()
    summary = run["result"]
    assert summary["summary_type"] == _SUMMARY_TYPE == "discovery_task_result"
    assert summary["summary_schema_version"] == _SUMMARY_SCHEMA_VERSION == "0.1"


def test_embedded_key_is_underlying_discovery_result_not_discovery_result() -> None:
    """The embedded sibling MUST live under ``underlying_discovery_result``.

    ``discovery_result`` as a top-level key would collide with the sibling
    summarizer's own ``summary_type`` value and defeat the parent/child
    distinction.
    """
    run = _run_live_task()
    summary = run["result"]
    assert _UNDERLYING_KEY in summary
    assert _UNDERLYING_KEY == "underlying_discovery_result"
    assert "discovery_result" not in summary


def test_all_required_sibling_fields_are_present() -> None:
    """Every design-doc-mandated top-level field must appear on the summary."""
    run = _run_live_task()
    summary = run["result"]
    observed = set(summary.keys())
    required = set(_TASK_RESULT_TOP_LEVEL_KEYS)
    missing = required - observed
    assert not missing, f"discovery_task_result is missing required keys: {sorted(missing)}"
    # 22 canonical keys (21 siblings + underlying_discovery_result).
    assert len(_TASK_RESULT_TOP_LEVEL_KEYS) == 22


def test_underlying_discovery_result_is_embedded_verbatim() -> None:
    """The embedded payload equals ``summarize_discovery_result`` byte-for-byte,
    except for the single namespaced v0.33c key.

    The task runtime composes with the existing v0.22 summarizer as a sibling
    wrapper. Any divergence between the embedded payload and a freshly-computed
    ``summarize_discovery_result`` on the same inputs indicates the composition
    is silently rewriting the sibling.

    v0.33c narrowing: the task attaches its mask diagnostics under exactly one
    namespaced key, ``fit_diagnostics["pdelie_mask_diagnostics"]``. That key is
    stripped before comparison so the guard still covers every backend-native
    field; nothing else in the sibling may be rewritten.
    """
    run = _run_live_task()
    field = run["field"]

    trajectories, time_values, feature_names = to_pysindy_trajectories(field)
    # Same fit path the runtime uses — caller-supplied pysindy_model.
    fresh_model = _build_caller_configured_sindy()
    raw_result = fit_pysindy_discovery(
        trajectories, time_values, feature_names, pysindy_model=fresh_model
    )
    expected_underlying = summarize_discovery_result(
        raw_result,
        source_result_id="heat_1d_v0_31b1_smoke",
        support_epsilon=1e-8,
        target_terms=None,
    )
    # Fit determinism: PySINDy's FiniteDifference + STLSQ is deterministic for
    # a fixed seed / dataset, so the embedded payload should equal a fresh
    # summarization of a fresh fit on the same trajectories.
    embedded = deepcopy(run["result"][_UNDERLYING_KEY])
    namespaced = embedded.get("fit_diagnostics", {}).pop(
        PDELIE_MASK_DIAGNOSTICS_KEY, None
    )
    # The namespaced block must be present and must be the ONLY difference.
    assert namespaced is not None
    assert embedded == expected_underlying


def test_pysindy_bridge_variant_is_periodic_only_v1() -> None:
    """The provenance identifier for the v0.31 bridge is ``periodic_only_v1``."""
    run = _run_live_task()
    summary = run["result"]
    assert summary["pysindy_bridge_variant"] == _PYSINDY_BRIDGE_VARIANT
    assert summary["pysindy_bridge_variant"] == "periodic_only_v1"


# ---------------------------------------------------------------------------
# 2. Runtime BC guard
# ---------------------------------------------------------------------------


def test_runtime_bc_guard_rejects_dirichlet_field() -> None:
    """A Dirichlet-tagged field must be rejected before any PySINDy is touched.

    This is the layer-1 gate that closes the hole a caller who assembles
    trajectories directly could otherwise use to bypass the bridge-level guard.
    """
    field = _build_heat_field()
    field.metadata["boundary_conditions"] = {"x": "dirichlet"}
    model = _build_caller_configured_sindy()
    with pytest.raises(PySINDyDiscoveryUnsupportedBoundaryError):
        run_pysindy_pde_task(
            field,
            task_name="heat_dirichlet_reject",
            pysindy_model=model,
        )


def test_pysindy_discovery_unsupported_boundary_error_is_scope_validation_subclass() -> None:
    """The runtime exception is a ``ScopeValidationError`` for uniform catching."""
    assert issubclass(PySINDyDiscoveryUnsupportedBoundaryError, ScopeValidationError)


# ---------------------------------------------------------------------------
# 3. Composition-boundary strict-JSON spy
# ---------------------------------------------------------------------------


def test_validate_strict_json_compatible_called_once_with_composed_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The runtime MUST call ``_validate_strict_json_compatible`` exactly once,
    at the composition boundary, with the fully-assembled payload.

    This is the load-bearing invariant: only 2 of 14 current ``summarize_*``
    funnels enforce ``allow_nan=False``; if the composed payload skipped the
    strict validator, a NaN embedded in ``underlying_discovery_result`` would
    silently pass through the permissive ``_summary_payload`` funnel.
    """
    real_validator = _tasks_discovery._validate_strict_json_compatible
    spy = MagicMock(side_effect=real_validator)
    monkeypatch.setattr(
        _tasks_discovery, "_validate_strict_json_compatible", spy, raising=True
    )

    field = _build_heat_field()
    model = _build_caller_configured_sindy()
    result = run_pysindy_pde_task(
        field,
        task_name="heat_1d_composition_spy",
        pysindy_model=model,
    )

    assert spy.call_count == 1, (
        "run_pysindy_pde_task must route the composed payload through "
        f"_validate_strict_json_compatible exactly once (got {spy.call_count})."
    )
    # The first positional argument passed to the strict validator must be the
    # fully-assembled payload — proven by equality with the returned summary.
    passed_payload = spy.call_args.args[0]
    assert passed_payload == result
    # And the name argument identifies the composition boundary.
    assert spy.call_args.kwargs.get("name") == "discovery_task_result summary"


# ---------------------------------------------------------------------------
# 4. Strict-JSON adversarial: NaN / Inf inside sub-payloads
# ---------------------------------------------------------------------------


def test_nan_inside_underlying_discovery_result_raises_schema_validation_error() -> None:
    """NaN embedded in the sibling ``underlying_discovery_result`` is rejected."""
    payload_inputs = _build_minimal_valid_task_result_payload()
    payload_inputs["underlying_discovery_result"]["coefficient_summary"]["l2_norm"] = float(
        "nan"
    )
    with pytest.raises(SchemaValidationError):
        summarize_discovery_task_result(**payload_inputs)


def test_nan_in_train_residual_raises() -> None:
    """NaN in the top-level ``train_residual.l2_norm`` is rejected."""
    payload_inputs = _build_minimal_valid_task_result_payload()
    payload_inputs["train_residual"]["l2_norm"] = float("nan")
    with pytest.raises(SchemaValidationError):
        summarize_discovery_task_result(**payload_inputs)


def test_positive_infinity_in_heldout_residual_max_abs_raises() -> None:
    """Positive infinity in ``heldout_residual.max_abs`` is rejected."""
    payload_inputs = _build_minimal_valid_task_result_payload()
    payload_inputs["heldout_residual"] = {
        "size": 64,
        "l2_norm": 0.01,
        "rms": 0.001,
        "max_abs": float("inf"),
    }
    with pytest.raises(SchemaValidationError):
        summarize_discovery_task_result(**payload_inputs)


# ---------------------------------------------------------------------------
# 5. Literal-set / literal-string invariants on the assembler
# ---------------------------------------------------------------------------


def test_target_convention_not_in_accepted_set_raises() -> None:
    payload_inputs = _build_minimal_valid_task_result_payload()
    payload_inputs["target_convention"] = "something_else"
    with pytest.raises(SchemaValidationError):
        summarize_discovery_task_result(**payload_inputs)


def test_input_layout_not_scalar_1d_uniform_raises() -> None:
    payload_inputs = _build_minimal_valid_task_result_payload()
    payload_inputs["input_layout"] = "multichannel_1d_uniform"
    with pytest.raises(SchemaValidationError):
        summarize_discovery_task_result(**payload_inputs)


def test_weak_contract_non_null_with_pde_library_raises() -> None:
    """``weak_contract`` must be None when ``target_convention == 'pde_library'``."""
    payload_inputs = _build_minimal_valid_task_result_payload()
    payload_inputs["weak_contract"] = {
        "method_family": "pysindy_weak_pde_library_polynomial_gauss_v1",
        "test_function_family": "pysindy_weak_pde_library_polynomial_bump_v1",
        "quadrature_rule": "pysindy_weak_pde_library_composite_gauss_v1",
        "diagnostic_only": True,
    }
    with pytest.raises(SchemaValidationError):
        summarize_discovery_task_result(**payload_inputs)


def test_weak_contract_null_with_weak_pde_library_raises() -> None:
    """``weak_contract`` must be non-null when ``target_convention == 'weak_pde_library'``."""
    payload_inputs = _build_minimal_valid_task_result_payload(
        target_convention="weak_pde_library"
    )
    payload_inputs["weak_contract"] = None
    with pytest.raises(SchemaValidationError):
        summarize_discovery_task_result(**payload_inputs)


def test_backend_name_outside_pysindy_raises() -> None:
    payload_inputs = _build_minimal_valid_task_result_payload()
    payload_inputs["backend_name"] = "pysr"
    with pytest.raises(SchemaValidationError):
        summarize_discovery_task_result(**payload_inputs)


def test_backend_version_missing_pysindy_key_raises() -> None:
    """The ``pysindy`` version key is required in ``backend_version``."""
    payload_inputs = _build_minimal_valid_task_result_payload()
    payload_inputs["backend_version"] = {"pdelie": "0.30.0"}
    with pytest.raises(SchemaValidationError):
        summarize_discovery_task_result(**payload_inputs)


def test_underlying_summary_type_not_discovery_result_raises() -> None:
    """The embedded sibling must carry ``summary_type == 'discovery_result'``."""
    payload_inputs = _build_minimal_valid_task_result_payload()
    payload_inputs["underlying_discovery_result"]["summary_type"] = "something_else"
    with pytest.raises(SchemaValidationError):
        summarize_discovery_task_result(**payload_inputs)


# ---------------------------------------------------------------------------
# 6. Public-surface / no-root-export invariants
# ---------------------------------------------------------------------------


def test_no_root_pdelie_export() -> None:
    """v0.31 keeps the task-bridge submodule-only — no root ``pdelie`` re-exports."""
    assert not hasattr(pdelie, "run_pysindy_pde_task")
    assert not hasattr(pdelie, "summarize_discovery_task_result")
    assert not hasattr(pdelie, "TaskResult")
    assert not hasattr(pdelie, "PySINDyDiscoveryUnsupportedBoundaryError")


def test_pdelie_tasks_discovery_public_surface() -> None:
    """The submodule exposes the three v0.31b1 public names."""
    import pdelie.tasks.discovery as module

    assert hasattr(module, "run_pysindy_pde_task")
    assert hasattr(module, "summarize_discovery_task_result")
    assert hasattr(module, "PySINDyDiscoveryUnsupportedBoundaryError")


# ---------------------------------------------------------------------------
# 7. Meta — v0.31b0 golden must still pass after v0.31b1
# ---------------------------------------------------------------------------


def test_v0_31b0_term_mapping_golden_still_passes_after_v0_31b1() -> None:
    """The v0.31b0 golden (default-config discovery) must not regress under v0.31b1.

    We exercise the pre-existing helper directly so any breakage in the
    default-config path (which the v0.31b1 adapter loosening MUST preserve as a
    backward-compatible shape) is caught here rather than only in the golden.
    """
    from tests.test_v0_31b0_pysindy_term_mapping_golden import _run_default_discovery

    run = _run_default_discovery()
    assert run["summary"]["summary_type"] == "discovery_result"
    assert run["summary"]["summary_schema_version"] == "0.1"
    # And the frozen 17-key set is still the observed key set.
    from tests.test_v0_31b0_pysindy_term_mapping_golden import (
        _EXPECTED_SUMMARY_KEYS,
    )

    assert set(run["summary"].keys()) == _EXPECTED_SUMMARY_KEYS


# ---------------------------------------------------------------------------
# 8. Sanity — deterministic numpy handling under the assembler
# ---------------------------------------------------------------------------


def test_summarize_discovery_task_result_accepts_numpy_scalar_metrics() -> None:
    """The assembler tolerates numpy floats (json_safe coerces before strict JSON)."""
    payload_inputs = _build_minimal_valid_task_result_payload()
    payload_inputs["support_precision"] = np.float64(1.0)
    payload_inputs["support_recall"] = np.float64(1.0)
    payload_inputs["support_f1"] = np.float64(1.0)
    payload_inputs["coefficient_relative_l2"] = np.float64(0.0)
    validated = summarize_discovery_task_result(**payload_inputs)
    assert validated["support_precision"] == 1.0
