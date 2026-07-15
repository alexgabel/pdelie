"""v0.30.1 lazy symmetry-method registry.

External symmetry methods (Ko-style, LieGAN, LaLiGAN, LieGG, and future
adapters) generate ``SymmetryCandidate``s from a canonical
``FieldBatch``. This module provides the registry that pdelie uses to
name those methods, load their adapters lazily, and expose a stable
``SymmetryMethodResult`` shape.

Architectural rule
------------------

External methods GENERATE candidates. PDELie verification determines
EVIDENCE. Candidate generation, candidate validation, and downstream
utility remain distinct stages. The registry deliberately does NOT rank,
select a winner, or call arbitrary method-native scores "confidence".
The v0.30.1 name for method-native scalar quantities is ``method_scores``.

Public submodule surface (submodule-only; no root ``pdelie`` export):

- :class:`SymmetryMethod` (Protocol)
- :class:`SymmetryMethodMetadata`
- :class:`SymmetryMethodResult`
- :class:`SymmetryMethodSpec`
- :func:`register_symmetry_method`
- :func:`get_symmetry_method`
- :func:`list_symmetry_methods`
- :func:`run_symmetry_method`
- :func:`summarize_symmetry_method_result`

Design references
-----------------

- ``docs/design/SYMMETRY_METHOD_REGISTRY.md`` — the full registry design.
- ``docs/specs/API_STABILITY.md`` — v0.30.1 stable public-surface note.
"""

from __future__ import annotations

import importlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, ClassVar, Protocol, cast, runtime_checkable

from pdelie.contracts import FieldBatch
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.residuals.base import ResidualEvaluator
from pdelie.symmetry.candidates import (
    SymmetryCandidate,
    summarize_symmetry_candidate,
)


def _validate_strict_json_compatible(value: Any, *, name: str) -> Any:
    """Lazy shim — same rationale as :mod:`pdelie.symmetry.candidates`."""
    from pdelie.reporting.summaries import _validate_strict_json_compatible as _impl

    return _impl(value, name=name)

# ---------------------------------------------------------------------------
# Metadata constants
# ---------------------------------------------------------------------------

_ALLOWED_IMPLEMENTATION_STATUSES: frozenset[str] = frozenset(
    {"builtin", "wrapped", "reimplemented", "external_optional"}
)

_ALLOWED_METHOD_CLASSES: frozenset[str] = frozenset(
    {"closed_form", "sparse_regression", "generative", "extraction", "symbolic"}
)

_ALLOWED_INPUT_LAYOUTS: frozenset[str] = frozenset(
    {"scalar_1d_uniform"}
)


def _require_nonempty_string(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaValidationError(f"{name} must be a non-empty string.")
    return value


def _require_string_or_none(value: Any, *, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SchemaValidationError(f"{name} must be a string or None.")
    return value


# ---------------------------------------------------------------------------
# SymmetryMethodMetadata
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class SymmetryMethodMetadata:
    """Static, JSON-safe description of a registered symmetry method.

    Constructed by the method module itself (e.g.
    ``pdelie.symmetry.methods.polynomial_translation_svd.METADATA``) and
    exposed via :func:`list_symmetry_methods` without importing the
    method's runtime dependencies.
    """

    method_name: str
    method_version: str
    citation_key: str | None
    paper_url: str | None
    code_url: str | None
    license: str | None
    implementation_status: str
    method_class: str
    deterministic: bool
    requires_training: bool
    requires_extras: tuple[str, ...]
    supported_input_layouts: tuple[str, ...]
    supported_boundary_conditions: tuple[str, ...]
    output_representation_types: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_nonempty_string(self.method_name, name="method_name")
        _require_nonempty_string(self.method_version, name="method_version")
        _require_string_or_none(self.citation_key, name="citation_key")
        _require_string_or_none(self.paper_url, name="paper_url")
        _require_string_or_none(self.code_url, name="code_url")
        _require_string_or_none(self.license, name="license")
        if self.implementation_status not in _ALLOWED_IMPLEMENTATION_STATUSES:
            raise SchemaValidationError(
                f"implementation_status must be one of "
                f"{sorted(_ALLOWED_IMPLEMENTATION_STATUSES)!r}; got "
                f"{self.implementation_status!r}."
            )
        if self.method_class not in _ALLOWED_METHOD_CLASSES:
            raise SchemaValidationError(
                f"method_class must be one of "
                f"{sorted(_ALLOWED_METHOD_CLASSES)!r}; got "
                f"{self.method_class!r}."
            )
        if not isinstance(self.deterministic, bool):
            raise SchemaValidationError("deterministic must be a bool.")
        if not isinstance(self.requires_training, bool):
            raise SchemaValidationError("requires_training must be a bool.")
        for extra in self.requires_extras:
            _require_nonempty_string(extra, name=f"requires_extras entry {extra!r}")
        for layout in self.supported_input_layouts:
            if layout not in _ALLOWED_INPUT_LAYOUTS:
                raise SchemaValidationError(
                    f"supported_input_layouts entry {layout!r} is not in "
                    f"{sorted(_ALLOWED_INPUT_LAYOUTS)!r}."
                )
        for bc in self.supported_boundary_conditions:
            _require_nonempty_string(bc, name="supported_boundary_conditions entry")
        for representation in self.output_representation_types:
            _require_nonempty_string(
                representation, name="output_representation_types entry"
            )

    def as_dict(self) -> dict[str, Any]:
        return cast(dict[str, Any], _validate_strict_json_compatible(
            {
                "method_name": self.method_name,
                "method_version": self.method_version,
                "citation_key": self.citation_key,
                "paper_url": self.paper_url,
                "code_url": self.code_url,
                "license": self.license,
                "implementation_status": self.implementation_status,
                "method_class": self.method_class,
                "deterministic": self.deterministic,
                "requires_training": self.requires_training,
                "requires_extras": list(self.requires_extras),
                "supported_input_layouts": list(self.supported_input_layouts),
                "supported_boundary_conditions": list(
                    self.supported_boundary_conditions
                ),
                "output_representation_types": list(
                    self.output_representation_types
                ),
            },
            name="SymmetryMethodMetadata.as_dict",
        ))


# ---------------------------------------------------------------------------
# SymmetryMethod Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class SymmetryMethod(Protocol):
    """Duck-typed contract for a registered symmetry method.

    Adapters must expose:

    - ``METADATA``: a :class:`SymmetryMethodMetadata` (class attribute).
    - ``fit(field, *, residual_evaluator=None, config=None)``: the
      single required operation. Returns a :class:`SymmetryMethodResult`.

    We use ``typing.Protocol`` (not ABC) so third-party adapters can be
    plain callables or dataclasses without inheriting from a pdelie base
    class. :func:`register_symmetry_method` still checks that the
    metadata block is present and well-formed.
    """

    METADATA: ClassVar[SymmetryMethodMetadata]

    def fit(
        self,
        field: FieldBatch,
        *,
        residual_evaluator: ResidualEvaluator | None = None,
        config: Mapping[str, Any] | None = None,
    ) -> SymmetryMethodResult:
        ...


# ---------------------------------------------------------------------------
# SymmetryMethodResult
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SymmetryMethodResult:
    """Uniform result shape for every registered symmetry method.

    Fields
    ------
    method_name:
        Non-empty string; must match the registered method's metadata.
    candidates:
        List of :class:`SymmetryCandidate`. May be empty. Order is
        method-defined and NOT normalized here — the registry does not
        rank candidates and does NOT expose a ``best`` accessor.
    method_scores:
        Mapping of method-native scalar quantities. Values must be
        finite floats OR ``None``. **The name is deliberately not
        "confidence" — no method-native quantity is a probability, a
        Bayes factor, or a validated score without explicit downstream
        verification.**
    fit_diagnostics:
        Mapping of any additional diagnostic outputs the method wishes
        to surface (e.g. condition numbers, span distances, iteration
        counts). Strict-JSON-safe. May be empty.
    runtime_seconds:
        Wall-clock time for the ``fit`` call. Finite float or ``None``.
    peak_memory_mb:
        Peak RSS in MiB during ``fit``, if measured. Finite float or
        ``None``.
    seed:
        Integer seed used by the method's RNG, if any. May be ``None``
        for deterministic methods that do not use randomness.
    deterministic:
        Boolean asserting the method's OUTPUT is deterministic given
        the input ``FieldBatch`` and ``config``. Should match the
        method's registered metadata unless the specific config disables
        determinism.
    warnings:
        List of strings surfacing runtime warnings.
    backend_versions:
        Mapping of ``package_name -> version_string`` for every
        dependency the method touched.
    provenance:
        Strict-JSON mapping. Recommended keys include the residual
        evaluator identifier, the config key, the FieldBatch schema
        version, and the input ``dims`` tuple.
    """

    method_name: str
    candidates: list[SymmetryCandidate]
    method_scores: dict[str, float | None] = field(default_factory=dict)
    fit_diagnostics: dict[str, Any] = field(default_factory=dict)
    runtime_seconds: float | None = None
    peak_memory_mb: float | None = None
    seed: int | None = None
    deterministic: bool = True
    warnings: list[str] = field(default_factory=list)
    backend_versions: dict[str, str] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    SCHEMA_VERSION: ClassVar[str] = "0.1"

    def __post_init__(self) -> None:
        _require_nonempty_string(self.method_name, name="method_name")
        if not isinstance(self.candidates, list):
            raise SchemaValidationError("candidates must be a list.")
        for index, candidate in enumerate(self.candidates):
            if not isinstance(candidate, SymmetryCandidate):
                raise SchemaValidationError(
                    f"candidates[{index}] must be a SymmetryCandidate; got "
                    f"{type(candidate).__name__!r}."
                )
        # method_scores: values must be finite float or None.
        if not isinstance(self.method_scores, Mapping):
            raise SchemaValidationError("method_scores must be a mapping.")
        normalized_scores: dict[str, float | None] = {}
        for key, value in dict(self.method_scores).items():
            if not isinstance(key, str) or not key:
                raise SchemaValidationError(
                    "method_scores keys must be non-empty strings."
                )
            if value is None:
                normalized_scores[key] = None
                continue
            try:
                cast_value = float(value)
            except (TypeError, ValueError) as exc:
                raise SchemaValidationError(
                    f"method_scores[{key!r}] must be a finite float or None."
                ) from exc
            # Reject NaN / Inf — the registry deliberately refuses these.
            import math
            if not math.isfinite(cast_value):
                raise SchemaValidationError(
                    f"method_scores[{key!r}] must be a finite float; got "
                    f"{cast_value!r}. Use None for unavailable values."
                )
            normalized_scores[key] = cast_value
        self.method_scores = normalized_scores
        # runtime + memory: finite float or None.
        for field_name in ("runtime_seconds", "peak_memory_mb"):
            value = getattr(self, field_name)
            if value is None:
                continue
            try:
                cast_value = float(value)
            except (TypeError, ValueError) as exc:
                raise SchemaValidationError(
                    f"{field_name} must be a finite float or None."
                ) from exc
            import math
            if not math.isfinite(cast_value):
                raise SchemaValidationError(
                    f"{field_name} must be a finite float; got {cast_value!r}. "
                    "Use None for unavailable values."
                )
            setattr(self, field_name, cast_value)
        if self.seed is not None and not isinstance(self.seed, int):
            raise SchemaValidationError("seed must be an int or None.")
        if not isinstance(self.deterministic, bool):
            raise SchemaValidationError("deterministic must be a bool.")
        # warnings: sequence of strings.
        if not isinstance(self.warnings, list):
            raise SchemaValidationError("warnings must be a list of strings.")
        for index, warning in enumerate(self.warnings):
            if not isinstance(warning, str):
                raise SchemaValidationError(
                    f"warnings[{index}] must be a string."
                )
        # backend_versions: dict[str, str].
        if not isinstance(self.backend_versions, Mapping):
            raise SchemaValidationError("backend_versions must be a mapping.")
        normalized_backend: dict[str, str] = {}
        for backend_key, backend_value in dict(self.backend_versions).items():
            if not isinstance(backend_key, str) or not backend_key:
                raise SchemaValidationError(
                    "backend_versions keys must be non-empty strings."
                )
            if not isinstance(backend_value, str) or not backend_value:
                raise SchemaValidationError(
                    f"backend_versions[{backend_key!r}] must be a non-empty string."
                )
            normalized_backend[backend_key] = backend_value
        self.backend_versions = normalized_backend
        # fit_diagnostics + provenance: strict-JSON.
        self.fit_diagnostics = dict(
            _validate_strict_json_compatible(
                dict(self.fit_diagnostics), name="fit_diagnostics"
            )
        )
        self.provenance = dict(
            _validate_strict_json_compatible(
                dict(self.provenance), name="provenance"
            )
        )


def summarize_symmetry_method_result(
    result: SymmetryMethodResult,
) -> dict[str, Any]:
    """Return a strict-JSON summary of a :class:`SymmetryMethodResult`."""
    if not isinstance(result, SymmetryMethodResult):
        raise SchemaValidationError(
            "summarize_symmetry_method_result requires a SymmetryMethodResult."
        )
    summary: dict[str, Any] = {
        "summary_schema_version": result.SCHEMA_VERSION,
        "summary_type": "pdelie_symmetry_method_result",
        "method_name": result.method_name,
        "candidates": [
            summarize_symmetry_candidate(candidate)
            for candidate in result.candidates
        ],
        "method_scores": dict(result.method_scores),
        "fit_diagnostics": dict(result.fit_diagnostics),
        "runtime_seconds": result.runtime_seconds,
        "peak_memory_mb": result.peak_memory_mb,
        "seed": result.seed,
        "deterministic": result.deterministic,
        "warnings": list(result.warnings),
        "backend_versions": dict(result.backend_versions),
        "provenance": dict(result.provenance),
    }
    return cast(dict[str, Any], _validate_strict_json_compatible(
        summary, name="pdelie_symmetry_method_result summary"
    ))


# ---------------------------------------------------------------------------
# SymmetryMethodSpec — the lazy registry entry
# ---------------------------------------------------------------------------


@dataclass(slots=True, frozen=True)
class SymmetryMethodSpec:
    """Lazy registration entry.

    Stores the metadata (constructed eagerly at registration time so
    :func:`list_symmetry_methods` works without importing the adapter
    module) plus an import path that the registry resolves the first
    time :func:`get_symmetry_method` or :func:`run_symmetry_method` is
    called for this name.

    ``import_path`` is a dotted string of the form
    ``"pdelie.symmetry.methods.polynomial_translation_svd:build_method"``
    (module and callable, colon-separated). The callable is invoked with
    no arguments and must return a fresh method instance implementing
    :class:`SymmetryMethod`.
    """

    method_name: str
    metadata: SymmetryMethodMetadata
    import_path: str

    def __post_init__(self) -> None:
        _require_nonempty_string(self.method_name, name="method_name")
        if self.method_name != self.metadata.method_name:
            raise SchemaValidationError(
                f"method_name mismatch: spec {self.method_name!r} vs "
                f"metadata {self.metadata.method_name!r}."
            )
        _require_nonempty_string(self.import_path, name="import_path")
        if ":" not in self.import_path:
            raise SchemaValidationError(
                f"import_path {self.import_path!r} must be "
                f"'module:callable'."
            )


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------

# Module-private dict — the registry itself. Ordered by insertion for
# deterministic listing.
_REGISTRY: dict[str, SymmetryMethodSpec] = {}


def register_symmetry_method(
    method_name: str,
    metadata: SymmetryMethodMetadata,
    import_path: str,
) -> None:
    """Register a symmetry method by name.

    Does NOT import the method's runtime dependencies. The adapter
    module is loaded lazily on the first :func:`get_symmetry_method` or
    :func:`run_symmetry_method` call.

    Raises
    ------
    :class:`SchemaValidationError`
        If ``method_name`` is empty, ``metadata.method_name`` disagrees,
        or ``import_path`` is malformed.
    :class:`ScopeValidationError`
        If ``method_name`` is already registered.
    """
    spec = SymmetryMethodSpec(
        method_name=method_name, metadata=metadata, import_path=import_path
    )
    if method_name in _REGISTRY:
        existing = _REGISTRY[method_name]
        raise ScopeValidationError(
            f"symmetry method {method_name!r} is already registered "
            f"(existing spec import_path={existing.import_path!r}); "
            "duplicate registration is refused."
        )
    _REGISTRY[method_name] = spec


def _resolve_spec(method_name: str) -> SymmetryMethodSpec:
    _require_nonempty_string(method_name, name="method_name")
    if method_name not in _REGISTRY:
        available = sorted(_REGISTRY.keys())
        raise ScopeValidationError(
            f"unknown symmetry method {method_name!r}; registered methods: "
            f"{available!r}."
        )
    return _REGISTRY[method_name]


def _load_method(spec: SymmetryMethodSpec) -> SymmetryMethod:
    module_name, _, callable_name = spec.import_path.partition(":")
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        # Emit an actionable message that names the required extras.
        extras = list(spec.metadata.requires_extras)
        if extras:
            hint = (
                f"install pdelie with the required extras "
                f"({', '.join(sorted(extras))}) e.g. "
                f"`pip install pdelie[{','.join(sorted(extras))}]`"
            )
        else:
            hint = (
                "the method's module could not be imported; check the "
                "installation of its dependencies"
            )
        raise ScopeValidationError(
            f"symmetry method {spec.method_name!r} adapter module "
            f"{module_name!r} could not be imported: {exc!s}. {hint}."
        ) from exc
    factory = getattr(module, callable_name, None)
    if factory is None:
        raise ScopeValidationError(
            f"symmetry method {spec.method_name!r} adapter module "
            f"{module_name!r} does not expose callable {callable_name!r}."
        )
    method = factory()
    if not isinstance(method, SymmetryMethod):
        raise SchemaValidationError(
            f"symmetry method factory {callable_name!r} in "
            f"{module_name!r} returned {type(method).__name__!r}; must "
            "implement the SymmetryMethod protocol (fit + METADATA)."
        )
    return method


def get_symmetry_method(method_name: str) -> SymmetryMethod:
    """Return a fresh instance of the named symmetry method.

    Lazy: the adapter module is imported only on the first call.
    """
    spec = _resolve_spec(method_name)
    return _load_method(spec)


def list_symmetry_methods() -> list[dict[str, Any]]:
    """List every registered method's metadata as a JSON-safe list.

    Does NOT import any adapter module. Safe to call in a core-only
    install without optional extras.
    """
    return [
        _REGISTRY[name].metadata.as_dict()
        for name in _REGISTRY
    ]


def run_symmetry_method(
    method_name: str,
    field: FieldBatch,
    *,
    residual_evaluator: ResidualEvaluator | None = None,
    config: Mapping[str, Any] | None = None,
) -> SymmetryMethodResult:
    """Run a registered method on ``field`` and return its result.

    Lazy: the adapter module is imported only on the first call for
    this ``method_name``.
    """
    if not isinstance(field, FieldBatch):
        raise SchemaValidationError(
            "run_symmetry_method requires a FieldBatch; file-path input, "
            "ndarray coercion, and xarray coercion are out of scope for "
            "v0.30.1."
        )
    method = get_symmetry_method(method_name)
    result = method.fit(field, residual_evaluator=residual_evaluator, config=config)
    if not isinstance(result, SymmetryMethodResult):
        raise SchemaValidationError(
            f"method {method_name!r} fit(...) returned "
            f"{type(result).__name__!r}; must return a SymmetryMethodResult."
        )
    if result.method_name != method_name:
        raise SchemaValidationError(
            f"method {method_name!r} returned a result with method_name="
            f"{result.method_name!r}; must match the registered name."
        )
    return result


# ---------------------------------------------------------------------------
# Test / debugging helpers — private, for the registry test suite only.
# ---------------------------------------------------------------------------


def _snapshot_registry() -> dict[str, SymmetryMethodSpec]:
    """Return a copy of the current registry state — private test helper."""
    return dict(_REGISTRY)


def _restore_registry(snapshot: Mapping[str, SymmetryMethodSpec]) -> None:
    """Replace the registry with ``snapshot`` — private test helper."""
    global _REGISTRY
    _REGISTRY.clear()
    for name, spec in snapshot.items():
        _REGISTRY[name] = spec


def _clear_registry_for_tests() -> None:
    """Clear the registry entirely — private test helper.

    Do NOT call from production code. The v0.30.1 test suite uses this
    to guard against cross-test state leakage.
    """
    _REGISTRY.clear()


# ---------------------------------------------------------------------------
# Bootstrap: register the built-in methods.
#
# We register the built-in polynomial_translation_svd method HERE (not
# in pdelie.symmetry.methods.__init__) so that importing
# pdelie.symmetry.methods does NOT eagerly load any optional dependency.
# The polynomial_translation_svd adapter has no optional dependencies
# beyond numpy, so it is safe to eagerly register but still lazily
# import its module — the import_path resolution defers module import
# until the first get/run call.
# ---------------------------------------------------------------------------

_BUILTIN_POLYNOMIAL_TRANSLATION_SVD_METADATA = SymmetryMethodMetadata(
    method_name="polynomial_translation_svd",
    method_version="0.1",
    citation_key=None,
    paper_url=None,
    code_url="src/pdelie/symmetry/methods/polynomial_translation_svd.py",
    license="MIT",
    implementation_status="builtin",
    method_class="closed_form",
    deterministic=True,
    requires_training=False,
    requires_extras=(),
    supported_input_layouts=("scalar_1d_uniform",),
    supported_boundary_conditions=("periodic",),
    output_representation_types=("generator_family",),
)


def _register_builtin_methods() -> None:
    """Idempotent registration of the built-in adapters."""
    if "polynomial_translation_svd" in _REGISTRY:
        return
    register_symmetry_method(
        "polynomial_translation_svd",
        _BUILTIN_POLYNOMIAL_TRANSLATION_SVD_METADATA,
        "pdelie.symmetry.methods.polynomial_translation_svd:build_method",
    )


_register_builtin_methods()


__all__: Sequence[str] = (
    "SymmetryMethod",
    "SymmetryMethodMetadata",
    "SymmetryMethodResult",
    "SymmetryMethodSpec",
    "get_symmetry_method",
    "list_symmetry_methods",
    "register_symmetry_method",
    "run_symmetry_method",
    "summarize_symmetry_method_result",
)


# ---------------------------------------------------------------------------
# Suppress unused-import warnings from static analysers — Iterable is
# exported for downstream annotation use if needed but not otherwise used
# in this module.
# ---------------------------------------------------------------------------

_ = Iterable
