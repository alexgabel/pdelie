"""v0.31b1 downstream discovery task-bridge runtime.

This module composes the existing narrow discovery surface —
``pdelie.discovery.to_pysindy_trajectories``,
``pdelie.discovery.fit_pysindy_discovery``,
``pdelie.discovery.summarize_discovery_result``, and
``pdelie.discovery.evaluate_discovery_recovery`` — into a single stable,
strict-JSON-safe ``TaskResult`` artifact returned by
``run_pysindy_pde_task(...)``.

The schema is frozen in ``docs/design/DISCOVERY_TASK_RESULT_SCHEMA.md`` under
``summary_type = "discovery_task_result"`` and
``summary_schema_version = "0.1"``. This is a submodule-only surface; no root
``pdelie`` export is added in v0.31.

The runtime performs a two-layer periodic-only enforcement:

1. ``run_pysindy_pde_task`` calls :func:`pdelie._boundary.is_x_periodic` on
   the incoming ``FieldBatch`` and raises
   :class:`PySINDyDiscoveryUnsupportedBoundaryError` (a
   :class:`ScopeValidationError` subclass) with a message referencing
   ``pysindy_bridge_variant = "periodic_only_v1"`` when the field is not
   periodic. This closes the hole that a caller who assembles trajectories
   directly could otherwise bypass the bridge-level gate.
2. The existing :func:`pdelie.discovery.to_pysindy_trajectories` gate
   continues to reject nonperiodic fields inside the bridge path.

At the composition boundary the fully assembled payload is routed through
:func:`pdelie.reporting.summaries._validate_strict_json_compatible` exactly
once so ``json.loads(json.dumps(payload, allow_nan=False)) == payload`` before
return.
"""

from __future__ import annotations

import importlib.metadata as _importlib_metadata
from collections.abc import Mapping, Sequence
from typing import Any, cast

import numpy as np

from pdelie._boundary import is_x_periodic
from pdelie.contracts import FieldBatch
from pdelie.discovery.contracts import summarize_discovery_result
from pdelie.discovery.evaluation import evaluate_discovery_recovery
from pdelie.discovery.pysindy_adapter import fit_pysindy_discovery
from pdelie.discovery.pysindy_bridge import to_pysindy_trajectories
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.reporting.summaries import _validate_strict_json_compatible

# ---------------------------------------------------------------------------
# Module-level constants (design-frozen literal-set / literal-string invariants)
# ---------------------------------------------------------------------------

_SUMMARY_SCHEMA_VERSION = "0.1"
_SUMMARY_TYPE = "discovery_task_result"
_UNDERLYING_KEY = "underlying_discovery_result"
_UNDERLYING_SUMMARY_TYPE = "discovery_result"
_INPUT_LAYOUT = "scalar_1d_uniform"
_ACCEPTED_TARGET_CONVENTIONS = frozenset({"pde_library", "weak_pde_library"})
_ACCEPTED_BACKEND_NAMES = frozenset({"pysindy"})
_PYSINDY_BRIDGE_VARIANT = "periodic_only_v1"
# sklearn is optional in v0.31b1 per the preflight; only pysindy + pdelie are required.
_REQUIRED_BACKEND_VERSION_KEYS = frozenset({"pysindy", "pdelie"})

# The design-doc-ordered top-level keys the composed payload must carry.
_TASK_RESULT_TOP_LEVEL_KEYS: tuple[str, ...] = (
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
    _UNDERLYING_KEY,
)


# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------


class PySINDyDiscoveryUnsupportedBoundaryError(ScopeValidationError):
    """Runtime BC guard raised by :func:`run_pysindy_pde_task`.

    Raised before assembling PySINDy trajectories when the input
    ``FieldBatch`` is not periodic in ``x``. The v0.31 PySINDy PDELibrary
    bridge is periodic-only (``pysindy_bridge_variant = "periodic_only_v1"``);
    FD-nonperiodic extension is explicitly deferred.
    """


# ---------------------------------------------------------------------------
# Field validators (all raise SchemaValidationError with actionable messages)
# ---------------------------------------------------------------------------


def _validate_task_name(task_name: object) -> str:
    if not isinstance(task_name, str) or not task_name:
        raise SchemaValidationError("task_name must be a non-empty string.")
    return task_name


def _validate_derivative_backend(derivative_backend: object) -> str:
    if not isinstance(derivative_backend, str) or not derivative_backend:
        raise SchemaValidationError("derivative_backend must be a non-empty string.")
    return derivative_backend


def _validate_pysindy_bridge_variant(pysindy_bridge_variant: object) -> str:
    if pysindy_bridge_variant != _PYSINDY_BRIDGE_VARIANT:
        raise SchemaValidationError(
            "pysindy_bridge_variant must equal "
            f"{_PYSINDY_BRIDGE_VARIANT!r} in v0.31; got {pysindy_bridge_variant!r}."
        )
    return _PYSINDY_BRIDGE_VARIANT


def _validate_target_convention_and_weak_contract(
    target_convention: object,
    weak_contract: object,
) -> tuple[str, dict[str, Any] | None]:
    if target_convention not in _ACCEPTED_TARGET_CONVENTIONS:
        raise SchemaValidationError(
            "target_convention must be one of "
            f"{sorted(_ACCEPTED_TARGET_CONVENTIONS)}; got {target_convention!r}."
        )
    if target_convention == "pde_library" and weak_contract is not None:
        raise SchemaValidationError(
            "weak_contract must be None when target_convention == 'pde_library'."
        )
    if target_convention == "weak_pde_library" and not isinstance(weak_contract, Mapping):
        raise SchemaValidationError(
            "weak_contract must be a non-null mapping when "
            "target_convention == 'weak_pde_library'."
        )
    normalized_weak = (
        None
        if weak_contract is None
        else dict(cast(Mapping[str, Any], weak_contract))
    )
    return str(target_convention), normalized_weak


def _validate_input_layout(input_layout: object) -> str:
    if input_layout != _INPUT_LAYOUT:
        raise SchemaValidationError(
            f"input_layout must equal {_INPUT_LAYOUT!r} in v0.31; got {input_layout!r}."
        )
    return _INPUT_LAYOUT


def _validate_backend_name(backend_name: object) -> str:
    if backend_name not in _ACCEPTED_BACKEND_NAMES:
        raise SchemaValidationError(
            "backend_name must be one of "
            f"{sorted(_ACCEPTED_BACKEND_NAMES)}; got {backend_name!r}."
        )
    return str(backend_name)


def _validate_backend_version(backend_version: object) -> dict[str, str]:
    if not isinstance(backend_version, Mapping):
        raise SchemaValidationError("backend_version must be a mapping of str -> str.")
    normalized: dict[str, str] = {}
    for key, value in backend_version.items():
        if not isinstance(key, str) or not key:
            raise SchemaValidationError("backend_version keys must be non-empty strings.")
        if not isinstance(value, str) or not value:
            raise SchemaValidationError(
                f"backend_version[{key!r}] must be a non-empty version string."
            )
        normalized[key] = value
    missing = sorted(_REQUIRED_BACKEND_VERSION_KEYS - set(normalized))
    if missing:
        raise SchemaValidationError(
            f"backend_version is missing required keys: {missing}."
        )
    return normalized


def _validate_underlying_discovery_result(underlying: object) -> dict[str, Any]:
    if not isinstance(underlying, Mapping):
        raise SchemaValidationError(
            "underlying_discovery_result must be a mapping produced by "
            "summarize_discovery_result."
        )
    summary_type = underlying.get("summary_type")
    if summary_type != _UNDERLYING_SUMMARY_TYPE:
        raise SchemaValidationError(
            "underlying_discovery_result.summary_type must equal "
            f"{_UNDERLYING_SUMMARY_TYPE!r}; got {summary_type!r}."
        )
    return dict(underlying)


def _validate_library_feature_names(library_feature_names: object) -> list[str]:
    if isinstance(library_feature_names, (str, bytes)) or not isinstance(
        library_feature_names, Sequence
    ):
        raise SchemaValidationError(
            "library_feature_names must be a sequence of unique non-empty strings."
        )
    normalized = [str(name) for name in library_feature_names]
    if any(not name for name in normalized):
        raise SchemaValidationError(
            "library_feature_names must contain only non-empty strings."
        )
    if len(set(normalized)) != len(normalized):
        raise SchemaValidationError("library_feature_names must be unique.")
    return normalized


def _validate_selected_terms(selected_terms: object) -> dict[str, dict[str, float]]:
    if not isinstance(selected_terms, Mapping):
        raise SchemaValidationError(
            "selected_terms must be a mapping of str -> mapping of str -> float."
        )
    normalized: dict[str, dict[str, float]] = {}
    for feature_name, term_map in selected_terms.items():
        if not isinstance(feature_name, str) or not feature_name:
            raise SchemaValidationError(
                "selected_terms keys must be non-empty strings."
            )
        if not isinstance(term_map, Mapping):
            raise SchemaValidationError(
                f"selected_terms[{feature_name!r}] must be a mapping."
            )
        inner: dict[str, float] = {}
        for term_name, coefficient in term_map.items():
            if not isinstance(term_name, str) or not term_name:
                raise SchemaValidationError(
                    f"selected_terms[{feature_name!r}] keys must be non-empty strings."
                )
            try:
                coefficient_value = float(coefficient)
            except (TypeError, ValueError) as exc:
                raise SchemaValidationError(
                    f"selected_terms[{feature_name!r}][{term_name!r}] must be a "
                    "finite float."
                ) from exc
            if not np.isfinite(coefficient_value):
                raise SchemaValidationError(
                    f"selected_terms[{feature_name!r}][{term_name!r}] must be finite."
                )
            inner[term_name] = coefficient_value
        normalized[feature_name] = inner
    return normalized


def _validate_finite_float(value: object, *, name: str) -> float:
    try:
        normalized = float(cast(Any, value))
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError(f"{name} must be a finite float.") from exc
    if not np.isfinite(normalized):
        raise SchemaValidationError(f"{name} must be a finite float.")
    return normalized


def _validate_residual_dict_or_none(
    value: object, *, name: str
) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise SchemaValidationError(
            f"{name} must be None or a mapping with keys size/l2_norm/rms/max_abs."
        )
    required = {"size", "l2_norm", "rms", "max_abs"}
    if set(value) != required:
        raise SchemaValidationError(
            f"{name} keys must be exactly {sorted(required)}; got {sorted(value)}."
        )
    size = value["size"]
    if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
        raise SchemaValidationError(f"{name}.size must be a positive integer.")
    return {
        "size": int(size),
        "l2_norm": _validate_finite_float(value["l2_norm"], name=f"{name}.l2_norm"),
        "rms": _validate_finite_float(value["rms"], name=f"{name}.rms"),
        "max_abs": _validate_finite_float(value["max_abs"], name=f"{name}.max_abs"),
    }


def _validate_coefficients_or_none(
    value: object,
) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise SchemaValidationError(
            "coefficients must be None or a mapping (opt-in shape)."
        )
    # Opt-in shape: {"shape": [num_features, num_terms], "values": list[list[float]],
    # "epsilon": support_epsilon}. We keep the validator lenient — it only re-serializes
    # numpy-like content so the strict JSON boundary can catch any residual NaN/Inf.
    return {str(k): _json_safe(v) for k, v in value.items()}


def _validate_warnings(warnings: object) -> list[str]:
    if isinstance(warnings, (str, bytes)) or not isinstance(warnings, Sequence):
        raise SchemaValidationError("warnings must be a sequence of non-empty strings.")
    normalized: list[str] = []
    for warning in warnings:
        if not isinstance(warning, str) or not warning:
            raise SchemaValidationError(
                "warnings entries must be non-empty strings."
            )
        normalized.append(warning)
    return normalized


# ---------------------------------------------------------------------------
# JSON coercion helper (kept minimal; the strict JSON boundary is authoritative)
# ---------------------------------------------------------------------------


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


# ---------------------------------------------------------------------------
# Public: strict-JSON-validated payload assembler
# ---------------------------------------------------------------------------


def summarize_discovery_task_result(
    *,
    task_name: str,
    backend_name: str,
    backend_version: Mapping[str, str],
    target_convention: str,
    input_layout: str,
    derivative_backend: str,
    pysindy_bridge_variant: str,
    library_feature_names: Sequence[str],
    selected_terms: Mapping[str, Mapping[str, float]],
    coefficients: Mapping[str, Any] | None,
    support_precision: float,
    support_recall: float,
    support_f1: float,
    exact_support: bool,
    coefficient_relative_l2: float,
    train_residual: Mapping[str, Any] | None,
    heldout_residual: Mapping[str, Any] | None,
    weak_contract: Mapping[str, Any] | None,
    warnings: Sequence[str],
    underlying_discovery_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Assemble and strict-JSON-validate a ``discovery_task_result`` payload.

    All field-level invariants are enforced up front. The final composed payload
    is routed through
    :func:`pdelie.reporting.summaries._validate_strict_json_compatible` exactly
    once, at the composition boundary, so any NaN/Inf that leaked through a
    permissive sub-summarizer is caught before return.
    """
    normalized_task_name = _validate_task_name(task_name)
    normalized_backend_name = _validate_backend_name(backend_name)
    normalized_backend_version = _validate_backend_version(backend_version)
    normalized_target_convention, normalized_weak_contract = (
        _validate_target_convention_and_weak_contract(target_convention, weak_contract)
    )
    normalized_input_layout = _validate_input_layout(input_layout)
    normalized_derivative_backend = _validate_derivative_backend(derivative_backend)
    normalized_pysindy_bridge_variant = _validate_pysindy_bridge_variant(
        pysindy_bridge_variant
    )
    normalized_library_feature_names = _validate_library_feature_names(
        library_feature_names
    )
    normalized_selected_terms = _validate_selected_terms(selected_terms)
    normalized_coefficients = _validate_coefficients_or_none(coefficients)
    normalized_support_precision = _validate_finite_float(
        support_precision, name="support_precision"
    )
    normalized_support_recall = _validate_finite_float(
        support_recall, name="support_recall"
    )
    normalized_support_f1 = _validate_finite_float(support_f1, name="support_f1")
    if not isinstance(exact_support, bool):
        raise SchemaValidationError("exact_support must be a bool.")
    normalized_coefficient_relative_l2 = _validate_finite_float(
        coefficient_relative_l2, name="coefficient_relative_l2"
    )
    normalized_train_residual = _validate_residual_dict_or_none(
        train_residual, name="train_residual"
    )
    normalized_heldout_residual = _validate_residual_dict_or_none(
        heldout_residual, name="heldout_residual"
    )
    normalized_warnings = _validate_warnings(warnings)
    normalized_underlying = _validate_underlying_discovery_result(
        underlying_discovery_result
    )

    payload: dict[str, Any] = {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": _SUMMARY_TYPE,
        "task_name": normalized_task_name,
        "backend_name": normalized_backend_name,
        "backend_version": normalized_backend_version,
        "target_convention": normalized_target_convention,
        "input_layout": normalized_input_layout,
        "derivative_backend": normalized_derivative_backend,
        "pysindy_bridge_variant": normalized_pysindy_bridge_variant,
        "library_feature_names": normalized_library_feature_names,
        "selected_terms": normalized_selected_terms,
        "coefficients": normalized_coefficients,
        "support_precision": normalized_support_precision,
        "support_recall": normalized_support_recall,
        "support_f1": normalized_support_f1,
        "exact_support": bool(exact_support),
        "coefficient_relative_l2": normalized_coefficient_relative_l2,
        "train_residual": normalized_train_residual,
        "heldout_residual": normalized_heldout_residual,
        "weak_contract": normalized_weak_contract,
        "warnings": normalized_warnings,
        _UNDERLYING_KEY: normalized_underlying,
    }

    # Composition-boundary check — the single load-bearing strict-JSON validation.
    validated = _validate_strict_json_compatible(
        payload, name="discovery_task_result summary"
    )
    return cast(dict[str, Any], validated)


# ---------------------------------------------------------------------------
# Backend-version resolution
# ---------------------------------------------------------------------------


def _resolve_backend_version(
    supplied_backend_version: Mapping[str, str] | None,
) -> dict[str, str]:
    """Return a validated backend_version dict.

    If ``supplied_backend_version`` is provided, it is validated as-is. Otherwise
    the runtime queries ``importlib.metadata.version(...)`` for ``pysindy`` and
    ``pdelie`` (required) plus ``sklearn`` opportunistically.
    """
    if supplied_backend_version is not None:
        return _validate_backend_version(supplied_backend_version)

    resolved: dict[str, str] = {}
    for package_name in ("pysindy", "pdelie"):
        try:
            resolved[package_name] = _importlib_metadata.version(package_name)
        except _importlib_metadata.PackageNotFoundError as exc:
            raise SchemaValidationError(
                f"backend_version could not be resolved for required package "
                f"{package_name!r}. Supply backend_version explicitly."
            ) from exc

    # sklearn is optional in v0.31b1 per the preflight; include it opportunistically
    # so consumers who require the full three-key backend_version design still see it.
    try:
        resolved["sklearn"] = _importlib_metadata.version("scikit-learn")
    except _importlib_metadata.PackageNotFoundError:
        pass

    return _validate_backend_version(resolved)


# ---------------------------------------------------------------------------
# Sibling extraction from the adapter's raw result dict
# ---------------------------------------------------------------------------


def _flatten_target_terms_over_features(
    target_terms: Mapping[str, Any] | None,
    feature_names: Sequence[str],
) -> dict[str, dict[str, float]] | None:
    """Expand a scalar target-term mapping to a per-feature mapping.

    Callers who supply a single ``dict[str, float]`` (i.e. the target PDE
    written once, not once per pysindy x_index feature) get the same target
    applied to every feature. Callers who already supply a nested
    ``dict[str, dict[str, float]]`` keyed by feature name are returned as-is
    after coverage validation.

    Returns ``None`` when the caller did not supply target_terms.
    """
    if target_terms is None:
        return None
    if not isinstance(target_terms, Mapping):
        raise SchemaValidationError(
            "target_terms must be a mapping (either str->float or "
            "str->mapping[str, float])."
        )
    if not target_terms:
        # Empty mapping: broadcast an empty target to every feature.
        return {name: {} for name in feature_names}

    first_value = next(iter(target_terms.values()))
    if isinstance(first_value, Mapping):
        # Already per-feature — ensure every feature is covered.
        return {
            name: {
                str(term): float(coefficient)
                for term, coefficient in dict(target_terms.get(name, {})).items()
            }
            for name in feature_names
        }

    # Flat form: broadcast to every feature.
    normalized_flat: dict[str, float] = {}
    for term, coefficient in target_terms.items():
        if not isinstance(term, str) or not term:
            raise SchemaValidationError(
                "target_terms flat-form keys must be non-empty strings."
            )
        normalized_flat[term] = float(coefficient)
    return {name: dict(normalized_flat) for name in feature_names}


def _aggregate_recovery_metrics(
    equation_terms: Mapping[str, Mapping[str, float]],
    target_terms_per_feature: Mapping[str, Mapping[str, float]] | None,
    *,
    support_epsilon: float,
) -> tuple[float, float, float, bool, float]:
    """Compute aggregate support metrics across features.

    Returns a tuple ``(precision, recall, f1, exact_support, coefficient_relative_l2)``
    where the scalar aggregates are the arithmetic mean of the per-feature
    metrics produced by :func:`evaluate_discovery_recovery`, and
    ``exact_support`` is True iff every feature is exactly recovered.
    """
    if target_terms_per_feature is None:
        # No target supplied — support metrics are trivially zero and
        # coefficient error cannot be computed against absent targets. The
        # caller receives the "support_epsilon_defaulted" warning via the
        # run_pysindy_pde_task path.
        return 0.0, 0.0, 0.0, False, 0.0

    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []
    coefficient_relative_l2s: list[float] = []
    all_exact = True
    saw_any_feature = False

    for feature_name, discovered_terms in equation_terms.items():
        saw_any_feature = True
        target_for_feature = target_terms_per_feature.get(feature_name, {})
        recovery = evaluate_discovery_recovery(
            target_for_feature,
            discovered_terms,
            support_epsilon=support_epsilon,
        )
        precisions.append(float(cast(Any, recovery["support_precision"])))
        recalls.append(float(cast(Any, recovery["support_recall"])))
        f1s.append(float(cast(Any, recovery["support_f1"])))
        coefficient_relative_l2s.append(
            float(cast(Any, recovery["coefficient_relative_l2_error"]))
        )
        if not bool(recovery["support_exact_match"]):
            all_exact = False

    if not saw_any_feature:
        return 0.0, 0.0, 0.0, False, 0.0

    return (
        float(np.mean(precisions)),
        float(np.mean(recalls)),
        float(np.mean(f1s)),
        bool(all_exact),
        float(np.mean(coefficient_relative_l2s)),
    )


def _residual_summary_from_array(
    array: np.ndarray[Any, Any] | None,
) -> dict[str, Any] | None:
    if array is None:
        return None
    flat = np.asarray(array, dtype=float).reshape(-1)
    if flat.size == 0:
        return None
    if not np.all(np.isfinite(flat)):
        # Do not surface NaN/Inf residuals; the strict-JSON boundary would
        # reject them anyway. Emit a warning instead by returning None.
        return None
    return {
        "size": int(flat.size),
        "l2_norm": float(np.linalg.norm(flat)),
        "rms": float(np.sqrt(np.mean(flat**2))),
        "max_abs": float(np.max(np.abs(flat))),
    }


def _compute_residual_over_trajectories(
    pysindy_model: Any,
    trajectories: Sequence[np.ndarray[Any, Any]],
    time_values: np.ndarray[Any, Any],
) -> np.ndarray[Any, Any] | None:
    """Compute a concatenated ``predict - differentiate`` residual, or None on failure.

    The PySINDy model's ``.predict`` returns predicted time-derivatives.
    v0.32a migration: ``SINDy.differentiate(...)`` was REMOVED in PySINDy
    2.x. The replacement path is the configured differentiation method
    itself, exposed on the fitted model as ``model.differentiation_method``
    (attribute — no trailing underscore). We call it directly as a
    callable to obtain the observed time-derivatives.

    Any exception from the backend degrades to ``None`` so the task-runner
    can still emit a valid TaskResult.
    """
    if pysindy_model is None:
        return None
    diff_method = getattr(pysindy_model, "differentiation_method", None)
    if diff_method is None:
        return None
    try:
        pieces: list[np.ndarray[Any, Any]] = []
        for trajectory in trajectories:
            predicted = np.asarray(pysindy_model.predict(trajectory), dtype=float)
            differentiated = np.asarray(
                diff_method(trajectory, t=time_values), dtype=float
            )
            pieces.append((predicted - differentiated).reshape(-1))
        if not pieces:
            return None
        return cast("np.ndarray[Any, Any]", np.concatenate(pieces))
    except Exception:  # noqa: BLE001 — degrade gracefully, warning surfaced upstream
        return None


# ---------------------------------------------------------------------------
# Public: task runner
# ---------------------------------------------------------------------------


def run_pysindy_pde_task(
    field: FieldBatch,
    *,
    task_name: str,
    pysindy_model: Any,
    derivative_backend: str = "FiniteDifference",
    target_terms: Mapping[str, Any] | None = None,
    heldout_field: FieldBatch | None = None,
    backend_version: Mapping[str, str] | None = None,
    warnings: Sequence[str] = (),
    support_epsilon: float = 1e-8,
) -> dict[str, Any]:
    """Run a PySINDy-backed PDE discovery task and return a ``discovery_task_result``.

    Parameters
    ----------
    field:
        Canonical scalar-1D-uniform ``FieldBatch``. Must be periodic in ``x``
        or :class:`PySINDyDiscoveryUnsupportedBoundaryError` is raised.
    task_name:
        Non-empty provenance identifier surfaced as ``source_result_id`` on the
        embedded ``underlying_discovery_result``.
    pysindy_model:
        Caller-configured ``pysindy.SINDy`` instance (with a ``PDELibrary``,
        ``PolynomialLibrary``, or other feature library, an optimizer, and a
        differentiation method).
    derivative_backend:
        Free-form string recorded as ``derivative_backend`` on the TaskResult.
        Defaults to ``"FiniteDifference"``.
    target_terms:
        Optional target-term mapping. Accepts either a flat
        ``dict[str, float]`` (broadcast to every pysindy x_index feature) or
        a nested ``dict[str, dict[str, float]]`` (per-feature). When absent,
        aggregate support metrics are zero-defaulted and the
        ``"support_epsilon_defaulted"`` warning is emitted.
    heldout_field:
        Optional held-out field batch used to compute ``heldout_residual``.
        Must be periodic in ``x`` if supplied. When absent, the
        ``"heldout_residual_missing"`` warning is emitted.
    backend_version:
        Optional pre-resolved ``dict[str, str]``. When absent, versions are
        queried via ``importlib.metadata``.
    warnings:
        Extra warnings to merge into the emitted list.
    support_epsilon:
        Support threshold forwarded to :func:`evaluate_discovery_recovery`.
    """
    if not isinstance(field, FieldBatch):
        raise SchemaValidationError("field must be a FieldBatch instance.")

    # Layer 1 periodic-only enforcement — closes the hole left by trajectory-
    # only callers who could otherwise bypass the bridge-level gate.
    if not is_x_periodic(field):
        raise PySINDyDiscoveryUnsupportedBoundaryError(
            "run_pysindy_pde_task requires a periodic-in-x FieldBatch "
            f"(pysindy_bridge_variant={_PYSINDY_BRIDGE_VARIANT!r}); "
            "FD-nonperiodic extension is explicitly deferred to v0.32.5+."
        )

    # Layer 2 (existing) periodic-only enforcement lives inside to_pysindy_trajectories.
    trajectories, time_values, feature_names = to_pysindy_trajectories(field)

    # Fit through the (loosened in v0.31b1) adapter with the caller-configured model.
    result_dict = fit_pysindy_discovery(
        trajectories,
        time_values,
        feature_names,
        pysindy_model=pysindy_model,
    )

    if result_dict.get("status") != "success":
        raise SchemaValidationError(
            "PySINDy discovery fit failed inside run_pysindy_pde_task: "
            f"{result_dict.get('failure_reason', 'backend_fit_failed')}."
        )

    # Compose the embedded backend-native summary. This is the sibling wrapper —
    # it MUST be included verbatim under the ``underlying_discovery_result`` key.
    target_terms_per_feature = _flatten_target_terms_over_features(
        target_terms, feature_names
    )
    underlying = summarize_discovery_result(
        result_dict,
        source_result_id=task_name,
        support_epsilon=support_epsilon,
        target_terms=target_terms_per_feature,
    )

    # Extract sibling fields from the raw result dict.
    library_feature_names = list(
        cast(Sequence[str], result_dict.get("library_feature_names", []))
    )
    equation_terms = dict(
        cast(Mapping[str, Mapping[str, float]], result_dict.get("equation_terms", {}))
    )

    # Aggregate recovery metrics across features.
    (
        support_precision,
        support_recall,
        support_f1,
        exact_support,
        coefficient_relative_l2,
    ) = _aggregate_recovery_metrics(
        equation_terms,
        target_terms_per_feature,
        support_epsilon=float(support_epsilon),
    )

    # Compute residuals via the caller-supplied model when possible.
    train_residual_array = _compute_residual_over_trajectories(
        pysindy_model, trajectories, time_values
    )
    train_residual = _residual_summary_from_array(train_residual_array)

    heldout_residual: dict[str, Any] | None = None
    if heldout_field is not None:
        if not isinstance(heldout_field, FieldBatch):
            raise SchemaValidationError("heldout_field must be a FieldBatch instance.")
        if not is_x_periodic(heldout_field):
            raise PySINDyDiscoveryUnsupportedBoundaryError(
                "heldout_field must be periodic in x "
                f"(pysindy_bridge_variant={_PYSINDY_BRIDGE_VARIANT!r})."
            )
        heldout_trajectories, heldout_time_values, _ = to_pysindy_trajectories(
            heldout_field
        )
        heldout_array = _compute_residual_over_trajectories(
            pysindy_model, heldout_trajectories, heldout_time_values
        )
        heldout_residual = _residual_summary_from_array(heldout_array)

    # Compose warnings — caller-supplied plus opportunistic diagnostic warnings.
    merged_warnings: list[str] = list(warnings)
    if target_terms is None:
        merged_warnings.append("support_epsilon_defaulted")
    if heldout_field is None:
        merged_warnings.append("heldout_residual_missing")

    resolved_backend_version = _resolve_backend_version(backend_version)

    return summarize_discovery_task_result(
        task_name=task_name,
        backend_name="pysindy",
        backend_version=resolved_backend_version,
        target_convention="pde_library",
        input_layout=_INPUT_LAYOUT,
        derivative_backend=derivative_backend,
        pysindy_bridge_variant=_PYSINDY_BRIDGE_VARIANT,
        library_feature_names=library_feature_names,
        selected_terms=equation_terms,
        coefficients=None,
        support_precision=support_precision,
        support_recall=support_recall,
        support_f1=support_f1,
        exact_support=exact_support,
        coefficient_relative_l2=coefficient_relative_l2,
        train_residual=train_residual,
        heldout_residual=heldout_residual,
        weak_contract=None,
        warnings=merged_warnings,
        underlying_discovery_result=underlying,
    )


__all__ = [
    "PySINDyDiscoveryUnsupportedBoundaryError",
    "run_pysindy_pde_task",
    "summarize_discovery_task_result",
]
