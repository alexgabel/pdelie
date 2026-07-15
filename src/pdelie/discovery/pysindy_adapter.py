from __future__ import annotations

import importlib
from collections.abc import Sequence

import numpy as np

from pdelie.discovery._pysindy_defaults import get_default_pysindy_discovery_config
from pdelie.errors import SchemaValidationError, ScopeValidationError


def _require_discovery_dependencies():
    """Import PySINDy + scikit-learn or raise with an actionable hint.

    v0.32a: the Python 3.12+ deferral branch that lived here through the
    v0.31.x line is removed. Python 3.12+ is now the supported target,
    not the deferred surface.
    """
    try:
        pysindy = importlib.import_module("pysindy")
        importlib.import_module("sklearn")
    except (ModuleNotFoundError, ImportError, ValueError) as exc:
        raise ImportError(
            "PySINDy discovery adapter requires pdelie[downstream] or "
            "pdelie[test]. Install with `pip install pdelie[downstream]`."
        ) from exc
    return pysindy


def _validate_trajectories(trajectories: object) -> list[np.ndarray]:
    if not isinstance(trajectories, (list, tuple)) or not trajectories:
        raise SchemaValidationError("trajectories must be a non-empty list or tuple of 2D finite numeric arrays.")

    normalized: list[np.ndarray] = []
    expected_shape: tuple[int, int] | None = None
    for _index, trajectory in enumerate(trajectories):
        try:
            array = np.asarray(trajectory, dtype=float)
        except (TypeError, ValueError) as exc:
            raise SchemaValidationError(
                "trajectories must contain only 2D finite numeric arrays."
            ) from exc
        if array.ndim != 2:
            raise SchemaValidationError("each trajectory must be a 2D finite numeric array.")
        if not np.all(np.isfinite(array)):
            raise SchemaValidationError("trajectories must contain only finite values.")
        if expected_shape is None:
            expected_shape = tuple(int(dim) for dim in array.shape)
        elif tuple(array.shape) != expected_shape:
            raise SchemaValidationError("all trajectories must share identical shape in V0.6 Milestone 2.")
        normalized.append(array.copy())
    return normalized


def _validate_time_values(time_values: object, *, num_times: int) -> np.ndarray:
    try:
        array = np.asarray(time_values, dtype=float)
    except (TypeError, ValueError) as exc:
        raise SchemaValidationError("time_values must be a one-dimensional finite numeric array.") from exc
    if array.ndim != 1:
        raise SchemaValidationError("time_values must be a one-dimensional finite numeric array.")
    if array.size < 3:
        raise SchemaValidationError("time_values must have at least 3 entries.")
    if array.size != num_times:
        raise SchemaValidationError("time_values length must match the trajectory time dimension.")
    if not np.all(np.isfinite(array)):
        raise SchemaValidationError("time_values must contain only finite values.")
    if not np.all(np.diff(array) > 0.0):
        raise SchemaValidationError("time_values must be strictly increasing.")
    return array.copy()


def _validate_feature_names(feature_names: object, *, num_state_features: int) -> list[str]:
    if isinstance(feature_names, (str, bytes)) or not isinstance(feature_names, Sequence):
        raise SchemaValidationError("feature_names must be a sequence of unique non-empty strings.")

    normalized = list(feature_names)
    if len(normalized) != num_state_features:
        raise SchemaValidationError("feature_names length must match the trajectory feature dimension.")
    if any(not isinstance(name, str) or not name for name in normalized):
        raise SchemaValidationError("feature_names must contain only non-empty strings.")
    if len(set(normalized)) != len(normalized):
        raise SchemaValidationError("feature_names must be unique in V0.6 Milestone 2.")
    return normalized


def _build_pysindy_model(pysindy, *, feature_names: list[str], fit_config: dict[str, object]):
    """Assemble a default PySINDy 2.1.x SINDy instance.

    v0.32a migration notes:

    - ``SINDy.__init__`` no longer accepts ``feature_names``,
      ``t_default``, or ``discrete_time`` (all three removed in 2.0).
      ``feature_names`` moves to ``SINDy.fit(...)``; the other two are
      dropped entirely.
    - Kwargs from the default-config dict are validated implicitly by
      passing them straight through to the 2.1.x constructors.
    """
    model_config = dict(fit_config["pysindy_model"])
    return pysindy.SINDy(
        optimizer=pysindy.STLSQ(**dict(model_config["optimizer"])),
        feature_library=pysindy.PolynomialLibrary(**dict(model_config["feature_library"])),
        differentiation_method=pysindy.FiniteDifference(**dict(model_config["differentiation_method"])),
    )


def _format_backend_equation(terms: dict[str, float]) -> str:
    if not terms:
        return "0"

    parts: list[str] = []
    for index, (term, coefficient) in enumerate(terms.items()):
        if index == 0:
            parts.append(f"{coefficient:.12g}*{term}")
            continue
        if coefficient < 0.0:
            parts.append(f"- {abs(coefficient):.12g}*{term}")
        else:
            parts.append(f"+ {coefficient:.12g}*{term}")
    return " ".join(parts)


def _extract_backend_terms(
    coefficients: np.ndarray,
    *,
    feature_names: list[str],
    library_feature_names: list[str],
    coefficient_threshold: float,
) -> tuple[dict[str, dict[str, float]], dict[str, str], dict[str, int]]:
    expected_shape = (len(feature_names), len(library_feature_names))
    if coefficients.ndim != 2 or tuple(coefficients.shape) != expected_shape:
        raise SchemaValidationError(
            f"PySINDy coefficients must have shape {expected_shape}, got {tuple(coefficients.shape)}."
        )

    equation_terms: dict[str, dict[str, float]] = {}
    equation_strings: dict[str, str] = {}
    nonzero_term_counts: dict[str, int] = {}

    for row_index, feature_name in enumerate(feature_names):
        sparse_terms: dict[str, float] = {}
        for column_index, library_feature_name in enumerate(library_feature_names):
            coefficient = float(coefficients[row_index, column_index])
            if abs(coefficient) > coefficient_threshold:
                sparse_terms[library_feature_name] = coefficient
        equation_terms[feature_name] = sparse_terms
        equation_strings[feature_name] = _format_backend_equation(sparse_terms)
        nonzero_term_counts[feature_name] = len(sparse_terms)

    return equation_terms, equation_strings, nonzero_term_counts


def _success_result(
    *,
    feature_names: list[str],
    library_feature_names: list[str],
    coefficients: np.ndarray,
    equation_terms: dict[str, dict[str, float]],
    equation_strings: dict[str, str],
    fit_config: dict[str, object],
    num_trajectories: int,
    num_times: int,
    nonzero_term_counts: dict[str, int],
) -> dict[str, object]:
    return {
        "status": "success",
        "backend": "pysindy",
        "feature_names": list(feature_names),
        "library_feature_names": list(library_feature_names),
        "coefficients": coefficients.copy(),
        "equation_terms": equation_terms,
        "equation_strings": equation_strings,
        "fit_config": fit_config,
        "fit_diagnostics": {
            "num_trajectories": num_trajectories,
            "num_times": num_times,
            "num_state_features": len(feature_names),
            "num_library_features": len(library_feature_names),
            "coefficient_threshold": float(fit_config["coefficient_threshold"]),
            "nonzero_term_counts": nonzero_term_counts,
            "terms_are_backend_native": True,
            "canonicalized": False,
        },
    }


def _failed_result(
    *,
    feature_names: list[str],
    fit_config: dict[str, object],
    exc: Exception,
) -> dict[str, object]:
    return {
        "status": "failed",
        "backend": "pysindy",
        "feature_names": list(feature_names),
        "library_feature_names": [],
        "coefficients": None,
        "equation_terms": {},
        "equation_strings": {},
        "fit_config": fit_config,
        "fit_diagnostics": {
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "terms_are_backend_native": True,
            "canonicalized": False,
        },
        "failure_reason": "backend_fit_failed",
    }


def _fit_caller_supplied_model(
    pysindy_model: object,
    *,
    trajectories: list[np.ndarray],
    time_values: np.ndarray,
) -> tuple[np.ndarray, list[str], dict[str, object]]:
    """Fit a caller-configured ``pysindy.SINDy`` instance and extract the
    same coefficients / library_feature_names / fit_config surface the
    default-config path returns.

    v0.31b1 loosening path — used when ``fit_pysindy_discovery`` is called
    with an explicit ``pysindy_model=<configured_SINDy>``. The caller retains
    full control over the feature library (e.g. ``PDELibrary``,
    ``PolynomialLibrary``), the optimizer, and the differentiation method.

    v0.32a migration: ``SINDy.fit`` in 2.1.x is ``fit(x, t, x_dot=None,
    u=None, feature_names=None)`` — ``t`` is positional-required and
    every legacy ensemble/multi-trajectory kwarg is gone. For pdelie's
    task-bridge use case (a single-trajectory PDELibrary fit), we pass
    the trajectory array directly as ``x`` and the scalar/array time
    grid as ``t``. Callers wanting ensembling must fit their model
    themselves and pass a fitted instance.
    """
    # In 2.1.x ``x`` accepts either a single (T, F) ndarray OR a list of
    # trajectories that get concatenated internally. pdelie's task bridge
    # emits one trajectory at a time in the current scope; pass the first
    # element directly and preserve the list form for the future
    # multi-trajectory extension.
    fit_input = trajectories[0] if len(trajectories) == 1 else trajectories
    pysindy_model.fit(fit_input, t=time_values)
    coefficients = np.asarray(pysindy_model.coefficients(), dtype=float)
    library_feature_names = [str(name) for name in pysindy_model.get_feature_names()]
    fit_config_record: dict[str, object] = {
        "pysindy_model_source": "caller_supplied",
        "coefficient_threshold": 1e-8,
        "pysindy_model": {
            "type": type(pysindy_model).__name__,
        },
    }
    return coefficients, library_feature_names, fit_config_record


def fit_pysindy_discovery(
    trajectories: object,
    time_values: object,
    feature_names: object,
    *,
    config: object | None = None,
    pysindy_model: object | None = None,
) -> dict[str, object]:
    """Fit PySINDy against a bridge-emitted (trajectories, time_values, feature_names)
    triple.

    v0.31b1 loosening:

    - ``config=None, pysindy_model=None`` (default): unchanged from v0.30 — the
      adapter assembles a default ``pysindy.SINDy`` with a ``PolynomialLibrary``
      / ``STLSQ`` / ``FiniteDifference`` and fits it.
    - ``config is not None``: still rejected with :class:`ScopeValidationError`
      — the ``config`` shape is not stabilized in v0.31.
    - ``pysindy_model is not None``: NEW opt-in path — the caller passes a
      pre-configured ``pysindy.SINDy`` instance (typically with a
      ``PDELibrary``). The adapter runs the caller's model against the
      bridge-emitted arrays and returns the same result-dict shape.
    """
    if config is not None:
        raise ScopeValidationError("fit_pysindy_discovery only supports config=None in V0.6 Milestone 2.")

    normalized_trajectories = _validate_trajectories(trajectories)
    num_times, num_state_features = normalized_trajectories[0].shape
    normalized_time_values = _validate_time_values(time_values, num_times=num_times)
    normalized_feature_names = _validate_feature_names(feature_names, num_state_features=num_state_features)

    if pysindy_model is not None:
        # Caller-supplied model path — skip default-config assembly.
        try:
            coefficients, library_feature_names, fit_config = _fit_caller_supplied_model(
                pysindy_model,
                trajectories=normalized_trajectories,
                time_values=normalized_time_values,
            )
        except Exception as exc:  # mirror default-path degrade behavior
            return _failed_result(
                feature_names=normalized_feature_names,
                fit_config={
                    "pysindy_model_source": "caller_supplied",
                    "coefficient_threshold": 1e-8,
                },
                exc=exc,
            )
    else:
        pysindy = _require_discovery_dependencies()
        fit_config = get_default_pysindy_discovery_config()

        try:
            model = _build_pysindy_model(
                pysindy,
                feature_names=normalized_feature_names,
                fit_config=fit_config,
            )
            # v0.32a: SINDy.fit(x, t, ...) in 2.1.x — no ensemble kwargs,
            # feature_names moved off the ctor onto fit. See
            # _pysindy_defaults: pysindy_fit is now an empty dict.
            fit_input = (
                normalized_trajectories[0]
                if len(normalized_trajectories) == 1
                else normalized_trajectories
            )
            model.fit(
                fit_input,
                t=normalized_time_values,
                feature_names=list(normalized_feature_names),
                **dict(fit_config["pysindy_fit"]),
            )
            coefficients = np.asarray(model.coefficients(), dtype=float)
            library_feature_names = list(model.get_feature_names())
        except Exception as exc:
            return _failed_result(
                feature_names=normalized_feature_names,
                fit_config=fit_config,
                exc=exc,
            )

    if not np.all(np.isfinite(coefficients)):
        raise SchemaValidationError("PySINDy coefficients must be finite.")

    equation_terms, equation_strings, nonzero_term_counts = _extract_backend_terms(
        coefficients,
        feature_names=normalized_feature_names,
        library_feature_names=library_feature_names,
        coefficient_threshold=float(fit_config["coefficient_threshold"]),
    )

    return _success_result(
        feature_names=normalized_feature_names,
        library_feature_names=library_feature_names,
        coefficients=coefficients,
        equation_terms=equation_terms,
        equation_strings=equation_strings,
        fit_config=fit_config,
        num_trajectories=len(normalized_trajectories),
        num_times=num_times,
        nonzero_term_counts=nonzero_term_counts,
    )
