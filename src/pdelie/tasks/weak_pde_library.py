"""v0.31b2 diagnostic wrapper around PySINDy's ``WeakPDELibrary``.

This module is submodule-only. No root ``pdelie`` re-export is added.

The wrapper is *diagnostic-only*: it introspects the PySINDy WeakPDELibrary
matrix / target shapes, feature names, column norms, rank, and condition
number for a scalar-1D uniform periodic FieldBatch. It is not a
sparse-identification benchmark, is not a validated weak sparse-recovery
result, does not certify anything about behavior under measurement noise,
and does not promote any PDE into the ``supported_existing_slice``. The
single load-bearing marker is the top-level ``diagnostic_only = True``
field on the emitted summary.

Design references
-----------------
The identifier strings ``method_family``, ``test_function_family``, and
``quadrature_rule`` are pinned by ``docs/design/DISCOVERY_TASK_RESULT_SCHEMA.md``
(lines 121-122, 130-137) and are deliberately distinct from the PDELie-native
``weak_1d`` identifier strings so downstream provenance is unambiguous.
The pinned strings use ``_gauss`` naming for historical reasons; the underlying
PySINDy WeakPDELibrary actually integrates a piecewise-linear interpolant of
the input against a polynomial spatial test function of degree ``p`` (default
4) analytically. The label is retained as opaque provenance; see the design
doc for the naming disambiguation rationale.

Two-layer periodic-only guard
-----------------------------
The wrapper enforces the same two-layer periodic-only guard as the v0.31b1
``run_pysindy_pde_task`` runtime:

1. Layer 1 — this module raises
   :class:`pdelie.tasks.discovery.PySINDyDiscoveryUnsupportedBoundaryError`
   on a non-periodic-in-x ``FieldBatch``, before any PySINDy call.
2. Layer 2 — general scope checks (uniform x/t grids, scalar 1D var,
   dims layout, minimum grid dimensions) raise
   :class:`pdelie.errors.ScopeValidationError` /
   :class:`pdelie.errors.SchemaValidationError`.
"""

from __future__ import annotations

import contextlib as _contextlib
import importlib.metadata as _importlib_metadata
import warnings as _warnings
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np
import numpy.random as _np_random

from pdelie._boundary import is_x_periodic
from pdelie.contracts import FieldBatch
from pdelie.discovery.column_normalize import summarize_column_normalization
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.reporting.summaries import _validate_strict_json_compatible
from pdelie.tasks.discovery import PySINDyDiscoveryUnsupportedBoundaryError

# ---------------------------------------------------------------------------
# Frozen module-level constants (design-authoritative literal strings)
# ---------------------------------------------------------------------------

_SUMMARY_TYPE = "pdelie_weak_pde_library_diagnostic"
_SUMMARY_SCHEMA_VERSION = "0.1"
_METHOD_FAMILY = "pysindy_weak_pde_library_polynomial_gauss_v1"
_INPUT_LAYOUT = "scalar_1d_uniform"
_TEST_FUNCTION_FAMILY = "pysindy_weak_pde_library_polynomial_bump_v1"
_QUADRATURE_RULE = "pysindy_weak_pde_library_composite_gauss_v1"
_BACKEND_NAME = "pysindy"
_TARGET_CONVENTION = "weak_pde_library"
_BOUNDARY_POLICY = "periodic_only_v1"

# Design-frozen top-level key set for the emitted summary. The composition
# boundary check asserts the emitted payload's keys are exactly this set.
_SUMMARY_TOP_LEVEL_KEYS: tuple[str, ...] = (
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
)

#: v0.34c: keys permitted on the payload but NOT required.
#:
#: The 27-key ``_SUMMARY_TOP_LEVEL_KEYS`` set above is a frozen invariant and
#: remains exactly what the default path emits. ``column_normalization`` is
#: emitted only when a caller explicitly opts in via
#: ``inspect_pysindy_weak_pde_library(..., column_normalize=True)``, so every
#: payload that could be produced before v0.34c still has exactly 27 keys and no
#: existing consumer sees a shape change.
_SUMMARY_OPTIONAL_TOP_LEVEL_KEYS: tuple[str, ...] = ("column_normalization",)


# ---------------------------------------------------------------------------
# Small dataclass — a caller-supplied library-configuration record
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WeakPDELibraryDiagnostic:
    """Caller-declared, JSON-safe library-configuration record.

    The wrapper accepts an instance of this dataclass (or a mapping with the
    same fields) and echoes its ``as_dict()`` output verbatim in the emitted
    summary's ``library_configuration`` slot. Only JSON-safe scalars are
    permitted; NaN/Inf are rejected at construction time via
    :func:`pdelie.reporting.summaries._validate_strict_json_compatible`.
    """

    polynomial_degree: int = 2
    derivative_order: int = 2
    include_bias: bool = False
    include_interaction: bool = True
    interaction_only: bool = True
    num_domain_centers_K: int = 16
    test_function_polynomial_degree_p: int = 4
    library_function_names: tuple[str, ...] = ("x0", "x0^2")
    notes: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "polynomial_degree": int(self.polynomial_degree),
            "derivative_order": int(self.derivative_order),
            "include_bias": bool(self.include_bias),
            "include_interaction": bool(self.include_interaction),
            "interaction_only": bool(self.interaction_only),
            "num_domain_centers_K": int(self.num_domain_centers_K),
            "test_function_polynomial_degree_p": int(
                self.test_function_polynomial_degree_p
            ),
            "library_function_names": [str(name) for name in self.library_function_names],
            "notes": None if self.notes is None else str(self.notes),
            "extra": dict(self.extra),
        }
        return cast(
            dict[str, Any],
            _validate_strict_json_compatible(
                payload, name="WeakPDELibraryDiagnostic.as_dict"
            ),
        )


# ---------------------------------------------------------------------------
# Backend-version resolution (opportunistic — sklearn/scipy are optional)
# ---------------------------------------------------------------------------


#: Distinguishes "the caller said nothing about seeding" from "the caller
#: explicitly asked for nondeterminism". ``None`` cannot carry both meanings, and
#: conflating them is why the diagnostic has been silently unreproducible since
#: v0.31b2: every unseeded caller looked identical to one who had opted in.
_UNSET: Any = object()


@_contextlib.contextmanager
def _seeded_global_numpy_random(seed: int | None) -> Iterator[None]:
    """Temporarily seed the legacy global NumPy RNG, then restore it.

    PySINDy's ``WeakPDELibrary`` places its ``K`` domain centers using
    ``np.random`` and exposes **no seed parameter**, which makes the emitted
    diagnostic nondeterministic run-to-run: ``column_norms`` and
    ``matrix_condition_number`` both move. Seeding around the library build is
    the only way to make the report reproducible without forking PySINDy.

    The prior RNG state is saved and restored so a caller's global random
    stream is not perturbed as a side effect of asking for a reproducible
    diagnostic.
    """
    if seed is None:
        yield
        return
    # NPY002 suppressed deliberately: PySINDy's WeakPDELibrary draws from the
    # LEGACY global RNG, so a np.random.Generator cannot control it. Seeding the
    # legacy global stream is the only lever that reaches PySINDy.
    state = _np_random.get_state()  # noqa: NPY002
    try:
        _np_random.seed(int(seed))  # noqa: NPY002
        yield
    finally:
        _np_random.set_state(state)  # noqa: NPY002


def _resolve_backend_version() -> dict[str, str]:
    resolved: dict[str, str] = {}
    for package_name, distribution_name in (
        ("pysindy", "pysindy"),
        ("pdelie", "pdelie"),
        ("sklearn", "scikit-learn"),
        ("scipy", "scipy"),
    ):
        try:
            resolved[package_name] = _importlib_metadata.version(distribution_name)
        except _importlib_metadata.PackageNotFoundError:
            # sklearn / scipy are optional; skip. pysindy / pdelie are
            # required and their absence surfaces below as a warning entry.
            continue
    return resolved


# ---------------------------------------------------------------------------
# Field validation (scope-rejection layer)
# ---------------------------------------------------------------------------


def _validate_field_scope(field_batch: FieldBatch) -> None:
    """Reject any FieldBatch outside the b2 diagnostic scope.

    The five rejection paths (a-e in the task spec) are enforced here BEFORE
    any PySINDy call:

    (a) non-periodic in x — raises PySINDyDiscoveryUnsupportedBoundaryError
    (b) non-uniform x grid — raises ScopeValidationError
    (c) non-uniform t grid — raises ScopeValidationError
    (d) not scalar 1D layout — raises ScopeValidationError
    (e) grid too small for the requested weak window — enforced at K-check time
    """
    if not isinstance(field_batch, FieldBatch):
        raise SchemaValidationError("field must be a FieldBatch instance.")

    if field_batch.dims != ("batch", "time", "x", "var"):
        raise ScopeValidationError(
            "inspect_pysindy_weak_pde_library only supports scalar 1D+time "
            "FieldBatch with dims ('batch', 'time', 'x', 'var'); got "
            f"{field_batch.dims!r}."
        )
    if field_batch.values.shape[0] != 1:
        raise ScopeValidationError(
            "inspect_pysindy_weak_pde_library only supports single-trajectory "
            "FieldBatch (batch dim == 1); got "
            f"batch_size={field_batch.values.shape[0]}; multi-batch is "
            "explicitly out of scope for v0.31b2."
        )
    if len(field_batch.var_names) != 1:
        raise ScopeValidationError(
            "inspect_pysindy_weak_pde_library only supports a single scalar "
            f"variable; got var_names={field_batch.var_names!r}."
        )

    if not is_x_periodic(field_batch):
        raise PySINDyDiscoveryUnsupportedBoundaryError(
            "inspect_pysindy_weak_pde_library requires a periodic-in-x "
            f"FieldBatch (boundary_policy={_BOUNDARY_POLICY!r}); "
            "FD-nonperiodic extension is explicitly deferred."
        )

    # Uniform-grid checks (FieldBatch.validate() already rejects non-uniform
    # spatial grids at construction time, but we re-check to be defensive
    # and to give a clearer error message tied to the wrapper's scope.)
    x_coord = np.asarray(field_batch.coords["x"], dtype=float)
    t_coord = np.asarray(field_batch.coords["time"], dtype=float)
    if x_coord.size < 4:
        raise ScopeValidationError(
            "inspect_pysindy_weak_pde_library requires at least 4 x-samples; "
            f"got {x_coord.size}."
        )
    if t_coord.size < 4:
        raise ScopeValidationError(
            "inspect_pysindy_weak_pde_library requires at least 4 t-samples; "
            f"got {t_coord.size}."
        )
    if not _is_uniform_1d(x_coord):
        raise ScopeValidationError(
            "inspect_pysindy_weak_pde_library requires a uniform x-grid."
        )
    if not _is_uniform_1d(t_coord):
        raise ScopeValidationError(
            "inspect_pysindy_weak_pde_library requires a uniform t-grid."
        )


def _is_uniform_1d(coord: np.ndarray[Any, Any], tol: float = 1e-10) -> bool:
    if coord.ndim != 1 or coord.size < 2:
        return False
    diffs = np.diff(coord)
    return bool(np.allclose(diffs, diffs[0], atol=tol, rtol=0.0))


# ---------------------------------------------------------------------------
# NaN/Inf normalization helpers
# ---------------------------------------------------------------------------


def _finite_scalar_or_none(
    value: Any, *, name: str, warnings_out: list[str]
) -> float | None:
    """Return float(value) if finite; else None + emit a warning."""
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        warnings_out.append(f"{name}_not_representable_as_float")
        return None
    if not np.isfinite(normalized):
        warnings_out.append(f"{name}_non_finite_coerced_to_none")
        return None
    return normalized


def _finite_int_or_none(
    value: Any, *, name: str, warnings_out: list[str]
) -> int | None:
    try:
        normalized_float = float(value)
    except (TypeError, ValueError):
        warnings_out.append(f"{name}_not_representable_as_int")
        return None
    if not np.isfinite(normalized_float):
        warnings_out.append(f"{name}_non_finite_coerced_to_none")
        return None
    return int(normalized_float)


# ---------------------------------------------------------------------------
# Public — the summary assembler (strict-JSON at the composition boundary)
# ---------------------------------------------------------------------------


def summarize_pysindy_weak_pde_library_diagnostic(
    *,
    backend_version: Mapping[str, str],
    library_configuration: Mapping[str, Any],
    spatiotemporal_grid_shape: tuple[int, ...] | list[int],
    input_field_shape: tuple[int, ...] | list[int],
    weak_feature_names: list[str],
    weak_matrix_shape: tuple[int, ...] | list[int],
    weak_target_shape: tuple[int, ...] | list[int],
    retained_weak_rows: int | None,
    skipped_weak_rows: int | None,
    skipped_row_reasons: list[str],
    finite_value_status: str,
    column_norms: dict[str, float | None],
    matrix_rank: int | None,
    matrix_condition_number: float | None,
    warnings: list[str],
    compatibility_notes: list[str],
    provenance: Mapping[str, Any],
    column_normalization: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble and strict-JSON-validate the diagnostic summary payload.

    The final composed payload is routed through
    :func:`pdelie.reporting.summaries._validate_strict_json_compatible`
    exactly once at the composition boundary. NaN/Inf are NEVER used as
    missing-value sentinels; the caller must convert non-finite scalars to
    ``None`` and append an entry to ``warnings`` beforehand.
    """
    payload: dict[str, Any] = {
        "summary_schema_version": _SUMMARY_SCHEMA_VERSION,
        "summary_type": _SUMMARY_TYPE,
        "diagnostic_only": True,
        "method_family": _METHOD_FAMILY,
        "backend_name": _BACKEND_NAME,
        "backend_version": {str(k): str(v) for k, v in backend_version.items()},
        "input_layout": _INPUT_LAYOUT,
        "boundary_policy": _BOUNDARY_POLICY,
        "target_convention": _TARGET_CONVENTION,
        "library_configuration": dict(library_configuration),
        "test_function_family": _TEST_FUNCTION_FAMILY,
        "quadrature_rule": _QUADRATURE_RULE,
        "spatiotemporal_grid_shape": [int(v) for v in spatiotemporal_grid_shape],
        "input_field_shape": [int(v) for v in input_field_shape],
        "weak_feature_names": [str(name) for name in weak_feature_names],
        "weak_matrix_shape": [int(v) for v in weak_matrix_shape],
        "weak_target_shape": [int(v) for v in weak_target_shape],
        "retained_weak_rows": (
            None if retained_weak_rows is None else int(retained_weak_rows)
        ),
        "skipped_weak_rows": (
            None if skipped_weak_rows is None else int(skipped_weak_rows)
        ),
        "skipped_row_reasons": [str(r) for r in skipped_row_reasons],
        "finite_value_status": str(finite_value_status),
        "column_norms": {
            str(k): (None if v is None else float(v))
            for k, v in column_norms.items()
        },
        "matrix_rank": None if matrix_rank is None else int(matrix_rank),
        "matrix_condition_number": (
            None
            if matrix_condition_number is None
            else float(matrix_condition_number)
        ),
        "warnings": [str(w) for w in warnings],
        "compatibility_notes": [str(n) for n in compatibility_notes],
        "provenance": dict(provenance),
    }

    # v0.34c: emitted only on the opt-in normalization path, so the default
    # payload keeps exactly the frozen 27 keys.
    if column_normalization is not None:
        payload["column_normalization"] = dict(column_normalization)

    # Design-frozen top-level keyset invariant: the 27 required keys must all be
    # present, and nothing beyond the documented optional set may appear.
    required = set(_SUMMARY_TOP_LEVEL_KEYS)
    permitted = required | set(_SUMMARY_OPTIONAL_TOP_LEVEL_KEYS)
    if not required.issubset(payload) or not set(payload).issubset(permitted):
        missing = sorted(required - set(payload))
        extra = sorted(set(payload) - permitted)
        raise SchemaValidationError(
            "pysindy weak pde library diagnostic summary has unexpected keys; "
            f"missing={missing} extra={extra}."
        )

    validated = _validate_strict_json_compatible(
        payload, name="pysindy weak pde library diagnostic summary"
    )
    return cast(dict[str, Any], validated)


# ---------------------------------------------------------------------------
# Public — the diagnostic runner
# ---------------------------------------------------------------------------


def _build_weak_library(
    library_configuration: WeakPDELibraryDiagnostic,
    *,
    x_coord: np.ndarray[Any, Any],
    t_coord: np.ndarray[Any, Any],
) -> tuple[Any, np.ndarray[Any, Any]]:
    """Construct a PySINDy WeakPDELibrary matched to the caller's config.

    Returns ``(library, spatiotemporal_grid)``. The grid shape is
    ``(X, T, 2)`` per ``preflight.array_shape_convention``.
    """
    try:
        import pysindy
    except ImportError as exc:  # pragma: no cover — importorskip guards tests
        raise ScopeValidationError(
            "pysindy is required for inspect_pysindy_weak_pde_library. "
            "Install with `pip install pdelie[downstream]`."
        ) from exc

    X = int(x_coord.size)
    T = int(t_coord.size)

    # (e) grid must be large enough for K subdomains — the WeakPDELibrary
    # samples K subdomain centers over the interior; require at least K*4
    # spatial samples so that the default p=4 test function has enough
    # support on each side. This is a defensive lower bound; if the caller
    # supplies a tiny grid we reject with an actionable message.
    K = int(library_configuration.num_domain_centers_K)
    if K < 1:
        raise ScopeValidationError(
            f"library_configuration.num_domain_centers_K must be >= 1; got {K}."
        )
    min_x = max(8, 4 * K)
    min_t = max(8, 4 * K)
    if X < min_x or T < min_t:
        raise ScopeValidationError(
            "inspect_pysindy_weak_pde_library requires at least "
            f"{min_x} x-samples and {min_t} t-samples for K={K} weak-library "
            f"subdomains (defensive lower bound = max(8, 4*K)); "
            f"got X={X}, T={T}."
        )

    grid = np.zeros((X, T, 2), dtype=float)
    grid[..., 0] = x_coord[:, None]
    grid[..., 1] = t_coord[None, :]

    # v0.32a migration: PySINDy 2.1.x's WeakPDELibrary REMOVED the legacy
    # ``library_functions=``, ``function_names=``, and ``interaction_only=``
    # kwargs. The library-composition entry point is now
    # ``function_library=<BaseFeatureLibrary>``; the polynomial
    # library is passed as a ``PolynomialLibrary`` instance whose degree
    # matches the caller's requested polynomial_degree.
    include_bias = bool(library_configuration.include_bias)
    include_interaction = bool(library_configuration.include_interaction)
    interaction_only = bool(library_configuration.interaction_only)
    polynomial_library = pysindy.PolynomialLibrary(
        degree=int(library_configuration.polynomial_degree),
        include_bias=include_bias,
        include_interaction=include_interaction,
        interaction_only=interaction_only,
    )

    # Silence numpy 2.x DeprecationWarnings from pysindy internals during
    # library construction. The v0.32a runtime does NOT pass the
    # deprecated is_uniform/periodic kwargs — periodic-boundary handling
    # is routed through diff_kwargs on the differentiation method.
    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore", category=DeprecationWarning)
        try:
            library = pysindy.WeakPDELibrary(
                function_library=polynomial_library,
                derivative_order=int(library_configuration.derivative_order),
                spatiotemporal_grid=grid,
                include_bias=include_bias,
                include_interaction=include_interaction,
                K=K,
                differentiation_method=pysindy.FiniteDifference,
                diff_kwargs={"periodic": True},
            )
        except TypeError as exc:
            raise ScopeValidationError(
                "installed PySINDy WeakPDELibrary API is incompatible with "
                f"the v0.32a diagnostic wrapper: {exc!s}"
            ) from exc

    return library, grid


def _column_norms_from_matrix(
    weak_matrix: np.ndarray[Any, Any],
    feature_names: list[str],
    warnings_out: list[str],
) -> dict[str, float | None]:
    norms: dict[str, float | None] = {}
    for idx, name in enumerate(feature_names):
        try:
            column = np.asarray(weak_matrix[:, idx], dtype=float)
        except (IndexError, TypeError):
            norms[name] = None
            warnings_out.append(f"column_norm_missing_for_{name}")
            continue
        if not np.all(np.isfinite(column)):
            norms[name] = None
            warnings_out.append(f"column_norm_non_finite_for_{name}")
            continue
        value = float(np.linalg.norm(column))
        if not np.isfinite(value):
            norms[name] = None
            warnings_out.append(f"column_norm_non_finite_for_{name}")
        else:
            norms[name] = value
    return norms


def _safe_matrix_rank(
    weak_matrix: np.ndarray[Any, Any], warnings_out: list[str]
) -> int | None:
    try:
        rank_value = int(np.linalg.matrix_rank(weak_matrix))
    except (np.linalg.LinAlgError, ValueError, TypeError):
        warnings_out.append("matrix_rank_not_computable")
        return None
    return rank_value


def _safe_condition_number(
    weak_matrix: np.ndarray[Any, Any], warnings_out: list[str]
) -> float | None:
    try:
        cond_value = float(np.linalg.cond(weak_matrix))
    except (np.linalg.LinAlgError, ValueError, TypeError):
        warnings_out.append("matrix_condition_number_not_computable")
        return None
    if not np.isfinite(cond_value):
        warnings_out.append("matrix_condition_number_non_finite_coerced_to_none")
        return None
    return cond_value


def inspect_pysindy_weak_pde_library(
    field_batch: FieldBatch,
    *,
    task_name: str,
    library_configuration: WeakPDELibraryDiagnostic | Mapping[str, Any] | None = None,
    column_normalize: bool = False,
    seed: int | Any | None = _UNSET,
) -> dict[str, Any]:
    """Run the diagnostic wrapper and return the strict-JSON summary.

    Parameters
    ----------
    field_batch:
        Scalar-1D-uniform, periodic-in-x ``FieldBatch``.
    task_name:
        Provenance identifier surfaced under ``provenance.task_name``.
    library_configuration:
        A :class:`WeakPDELibraryDiagnostic` instance or a mapping with the
        same fields. Defaults to :class:`WeakPDELibraryDiagnostic()`.
    column_normalize:
        v0.34c. When ``False`` (the default) the emitted report is byte-for-byte
        what pre-v0.34c produced, with exactly the frozen 27 top-level keys.
        When ``True`` the weak design matrix is column-normalized to unit L2
        norm and a ``column_normalization`` block is added, reporting the
        conditioning before and after.

        This is a **conditioning** fix. It is not WSINDy and makes no
        noise-robustness claim. The measured improvement is fixture-dependent:
        across the six fixtures pinned in
        ``tests/fixtures/v0_34c_conditioning_ratios.json`` the condition-number
        ratio ranges 1.77x-66.75x with a median of 4.52x.
    """
    if not isinstance(task_name, str) or not task_name:
        raise SchemaValidationError("task_name must be a non-empty string.")

    # v0.36e: three-state seed. Omitted, explicitly None, and an integer are
    # three different intentions and are reported as three different states.
    if seed is _UNSET:
        _warnings.warn(
            "inspect_pysindy_weak_pde_library was called without an explicit "
            "seed. Legacy nondeterministic behavior is retained temporarily; "
            "v0.38 will require an explicit integer seed. Pass seed=<int> for "
            "deterministic behavior, or seed=None to explicitly opt into "
            "nondeterminism.",
            # FutureWarning, NOT DeprecationWarning: the latter is hidden by
            # default outside __main__, which would make this transition
            # invisible to exactly the callers who need to see it.
            FutureWarning,
            stacklevel=2,
        )
        effective_seed: int | None = None
        seed_was_omitted = True
        nondeterministic_requested = False
    elif seed is None:
        effective_seed = None
        seed_was_omitted = False
        nondeterministic_requested = True
    else:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ScopeValidationError(
                f"seed must be an int, None, or omitted; got {type(seed).__name__}."
            )
        effective_seed = int(seed)
        seed_was_omitted = False
        nondeterministic_requested = False

    # Layer 1 + Layer 2 scope checks — before any PySINDy call.
    _validate_field_scope(field_batch)

    # Normalize the library configuration.
    if library_configuration is None:
        config = WeakPDELibraryDiagnostic()
    elif isinstance(library_configuration, WeakPDELibraryDiagnostic):
        config = library_configuration
    elif isinstance(library_configuration, Mapping):
        try:
            config = WeakPDELibraryDiagnostic(**dict(library_configuration))
        except TypeError as exc:
            raise SchemaValidationError(
                f"library_configuration mapping is incompatible with "
                f"WeakPDELibraryDiagnostic: {exc!s}"
            ) from exc
    else:
        raise SchemaValidationError(
            "library_configuration must be a WeakPDELibraryDiagnostic, a "
            "mapping, or None."
        )

    warnings_out: list[str] = []
    compatibility_notes: list[str] = [
        "pysindy_2_1_x_weak_pde_library_function_library_pattern_v0_32a",
        "pysindy_2_1_x_weak_pde_library_periodic_boundary_via_diff_kwargs_v0_32a",
    ]

    x_coord = np.asarray(field_batch.coords["x"], dtype=float)
    t_coord = np.asarray(field_batch.coords["time"], dtype=float)

    # Collapse the (batch, time, x, var=1) tensor into the (X, T, 1) input
    # PySINDy expects for spatiotemporal_grid of shape (X, T, 2).
    values = np.asarray(field_batch.values, dtype=float)
    # Batch dim is guarded to size 1 upstream by _validate_field_scope, so
    # indexing element 0 is safe and lossless for the single-trajectory
    # diagnostic contract.
    single = values[0, ..., 0]  # shape (T, X)
    u_input = np.asarray(single.T[..., None], dtype=float)  # (X, T, 1)
    input_field_shape = list(u_input.shape)

    # v0.34c: the library construction AND the fit both draw domain centers from
    # the global NumPy RNG, so both must sit inside the seeded scope for the
    # emitted diagnostic to be reproducible.
    with _seeded_global_numpy_random(effective_seed):
        library, spatiotemporal_grid = _build_weak_library(
            config, x_coord=x_coord, t_coord=t_coord
        )

        # Fit the library on the input, then transform to get the weak matrix
        # and target. All PySINDy warnings are silenced within this scope.
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore", category=UserWarning)
            _warnings.simplefilter("ignore", category=DeprecationWarning)
            try:
                library.fit(u_input)
                weak_matrix = np.asarray(library.transform(u_input), dtype=float)
                weak_target = np.asarray(
                    library.convert_u_dot_integral(u_input), dtype=float
                )
                feature_names = list(library.get_feature_names())
            except Exception as exc:
                raise ScopeValidationError(
                    "PySINDy WeakPDELibrary fit/transform failed inside "
                    f"inspect_pysindy_weak_pde_library: {exc!s}"
                ) from exc

    weak_matrix_shape = list(weak_matrix.shape)
    weak_target_shape = list(weak_target.shape)

    # Finite-value status of the weak matrix. The wrapper does not raise on
    # non-finite; it downgrades to None + a warning at the summary boundary.
    if np.all(np.isfinite(weak_matrix)) and np.all(np.isfinite(weak_target)):
        finite_value_status = "all_finite"
    else:
        finite_value_status = "contains_non_finite_values"
        warnings_out.append("weak_matrix_or_target_contains_non_finite_values")

    # retained/skipped row counts — the WeakPDELibrary API in 1.7.5 does not
    # expose a skipped-row inventory. We treat all K rows as retained if
    # finite, else infer skipped from the finite mask.
    K = int(weak_matrix.shape[0])
    if finite_value_status == "all_finite":
        retained_weak_rows: int | None = K
        skipped_weak_rows: int | None = 0
        skipped_row_reasons: list[str] = []
    else:
        finite_mask = np.all(np.isfinite(weak_matrix), axis=1) & np.all(
            np.isfinite(weak_target), axis=1
        )
        retained_weak_rows = int(np.sum(finite_mask))
        skipped_weak_rows = int(K - retained_weak_rows)
        skipped_row_reasons = ["non_finite_row_values"] if skipped_weak_rows > 0 else []

    column_norms = _column_norms_from_matrix(weak_matrix, feature_names, warnings_out)
    matrix_rank = _safe_matrix_rank(weak_matrix, warnings_out)
    matrix_condition_number = _safe_condition_number(weak_matrix, warnings_out)
    # matrix_condition_number normalization to None already handled inside
    # _safe_condition_number; run through the finite-scalar-or-none helper
    # just to keep the invariant local to the composition boundary.
    if matrix_condition_number is not None:
        matrix_condition_number = _finite_scalar_or_none(
            matrix_condition_number,
            name="matrix_condition_number",
            warnings_out=warnings_out,
        )

    backend_version = _resolve_backend_version()

    provenance: dict[str, Any] = {
        "backend_name": _BACKEND_NAME,
        "task_name": task_name,
        "method_family": _METHOD_FAMILY,
        "test_function_family": _TEST_FUNCTION_FAMILY,
        "quadrature_rule": _QUADRATURE_RULE,
        "diagnostic_only": True,
        "timestamp": None,
        "pdelie_version": backend_version.get("pdelie"),
        "pysindy_version": backend_version.get("pysindy"),
        "sklearn_version": backend_version.get("sklearn"),
        "scipy_version": backend_version.get("scipy"),
        # Nested deliberately: a new TOP-LEVEL key would break the frozen 27/28
        # conditional schema. This lives inside the provenance block that
        # already exists, so the default path still has exactly 27 keys and the
        # column_normalize path exactly 28.
        "seed_provenance": {
            "seed": effective_seed,
            "seed_was_omitted": seed_was_omitted,
            "rng_backend": "numpy_legacy_global_state",
            "rng_scope": "process_wide_context_manager",
            "nondeterministic_requested": nondeterministic_requested,
            "thread_safe": False,
            "legacy_global_rng_workaround": True,
        },
    }

    library_configuration_payload = config.as_dict()

    column_normalization_block: dict[str, Any] | None = None
    if column_normalize:
        column_normalization_block = summarize_column_normalization(weak_matrix)

    return summarize_pysindy_weak_pde_library_diagnostic(
        backend_version=backend_version,
        library_configuration=library_configuration_payload,
        spatiotemporal_grid_shape=list(spatiotemporal_grid.shape),
        input_field_shape=input_field_shape,
        weak_feature_names=feature_names,
        weak_matrix_shape=weak_matrix_shape,
        weak_target_shape=weak_target_shape,
        retained_weak_rows=retained_weak_rows,
        skipped_weak_rows=skipped_weak_rows,
        skipped_row_reasons=skipped_row_reasons,
        finite_value_status=finite_value_status,
        column_norms=column_norms,
        matrix_rank=matrix_rank,
        matrix_condition_number=matrix_condition_number,
        warnings=warnings_out,
        compatibility_notes=compatibility_notes,
        provenance=provenance,
        column_normalization=column_normalization_block,
    )


__all__ = [
    "WeakPDELibraryDiagnostic",
    "inspect_pysindy_weak_pde_library",
    "summarize_pysindy_weak_pde_library_diagnostic",
]
