"""v0.30.1 representation-neutral SymmetryCandidate contract.

A ``SymmetryCandidate`` is a discriminated wrapper around one of PDELie's
existing generator/invariant representations OR a documented placeholder
for a representation that PDELie has not yet stabilized. Candidates are
what external symmetry-generation methods *produce*; they do NOT imply
that the wrapped representation has been validated against a residual
evaluator or verified on held-out data. Validation and verification
remain the responsibility of the existing
:mod:`pdelie.symmetry.candidate_validation` and
:mod:`pdelie.verification` surfaces.

Public submodule surface (submodule-only; no root ``pdelie`` export):

- :class:`SymmetryCandidate`
- :func:`build_symmetry_candidate`
- :func:`summarize_symmetry_candidate`
- The reserved :data:`REPRESENTATION_TYPES` set.

Design references
-----------------

- ``docs/design/SYMMETRY_METHOD_REGISTRY.md`` — the v0.30.1 registry design.
- ``docs/specs/API_STABILITY.md`` — v0.30.1 stable public-surface note.

Reserved representation types
-----------------------------

Seven discriminator values are reserved:

- ``generator_family`` — v0.30.1 stably wraps :class:`GeneratorFamily`.
- ``formula_generator_family`` — v0.30.1 stably wraps
  :class:`FormulaGeneratorFamily`.
- ``invariant_map_spec`` — v0.30.1 stably wraps :class:`InvariantMapSpec`.
- ``matrix_lie_algebra`` — reserved. Not constructible in v0.30.1;
  awaits its own scope-freeze design.
- ``coordinate_vector_field`` — reserved. Same status.
- ``finite_transform_spec`` — reserved. Same status.
- ``latent_generator_reference`` — reserved. Same status.

Constructing a candidate with a reserved-but-unimplemented
``representation_type`` raises :class:`ScopeValidationError` unless the
caller passes ``allow_reserved_unimplemented=True`` (only intended for
internal spec-freeze tests).
"""

from __future__ import annotations

import copy
import warnings
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar, cast

import numpy as np

from pdelie.contracts import GeneratorFamily, InvariantMapSpec
from pdelie.errors import SchemaValidationError, ScopeValidationError
from pdelie.symmetry.formula import FormulaGeneratorFamily


def _validate_strict_json_compatible(value: Any, *, name: str) -> Any:
    """Lazy shim to :func:`pdelie.reporting.summaries._validate_strict_json_compatible`.

    Imported at call time to break the ``pdelie.reporting.summaries -> ...
    -> pdelie.symmetry.formula -> pdelie.symmetry.__init__ ->
    pdelie.symmetry.candidates -> pdelie.reporting.summaries`` circular
    import chain.
    """
    from pdelie.reporting.summaries import _validate_strict_json_compatible as _impl

    return _impl(value, name=name)

# ---------------------------------------------------------------------------
# Reserved representation types
# ---------------------------------------------------------------------------

#: v0.30.1 stably wrapping surfaces.
_IMPLEMENTED_REPRESENTATION_TYPES: frozenset[str] = frozenset(
    {
        "generator_family",
        "formula_generator_family",
        "invariant_map_spec",
    }
)

#: v0.30.1 reserved-but-unimplemented surfaces.
_RESERVED_REPRESENTATION_TYPES: frozenset[str] = frozenset(
    {
        "matrix_lie_algebra",
        "coordinate_vector_field",
        "finite_transform_spec",
        "latent_generator_reference",
    }
)

#: Full set of reserved discriminator values.
REPRESENTATION_TYPES: frozenset[str] = (
    _IMPLEMENTED_REPRESENTATION_TYPES | _RESERVED_REPRESENTATION_TYPES
)

_MATHEMATICAL_STATUSES: frozenset[str] = frozenset(
    {
        "candidate_only",
        "empirically_supported_configured",
        "no_evidence",
    }
)

_EXECUTABLE_STATUSES: frozenset[str] = frozenset(
    {
        "executable",
        "not_executable",
        "unknown",
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_nonempty_string(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaValidationError(f"{name} must be a non-empty string.")
    return value


def _normalize_provenance(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise SchemaValidationError("provenance must be a mapping or None.")
    return dict(_validate_strict_json_compatible(dict(value), name="provenance"))


def _normalize_warnings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str) or not hasattr(value, "__iter__"):
        raise SchemaValidationError(
            "warnings must be a sequence of warning strings (e.g. list/tuple); "
            "a single string or a non-iterable value is not accepted."
        )
    normalized: list[str] = []
    for index, warning in enumerate(value):
        if not isinstance(warning, str):
            raise SchemaValidationError(
                f"warnings[{index}] must be a string; got {type(warning).__name__!r}."
            )
        normalized.append(warning)
    return normalized


def _summarize_generator_family_payload(payload: GeneratorFamily) -> dict[str, Any]:
    payload.validate()
    return {
        "schema_version": payload.schema_version,
        "parameterization": payload.parameterization,
        "coefficients_shape": list(payload.coefficients.shape),
        "coefficients_finite": bool(np.all(np.isfinite(payload.coefficients))),
        "basis_spec": _validate_strict_json_compatible(
            payload.basis_spec, name="payload.basis_spec"
        ),
        "normalization": payload.normalization,
        "generator_names": (
            None if payload.generator_names is None else list(payload.generator_names)
        ),
        "diagnostics_keys": sorted(payload.diagnostics.keys()),
    }


def _summarize_formula_generator_family_payload(
    payload: FormulaGeneratorFamily,
) -> dict[str, Any]:
    return {
        "schema_version": payload.schema_version,
        "parameterization": payload.parameterization,
        "num_formula_generators": len(payload.formula_generators),
        "variables": list(payload.variables),
        "component_names": list(payload.component_names),
        "has_finite_transform_spec": payload.finite_transform_spec is not None,
        "diagnostics_keys": sorted(payload.diagnostics.keys()),
    }


def _summarize_invariant_map_spec_payload(
    payload: InvariantMapSpec,
) -> dict[str, Any]:
    return {
        "schema_version": payload.schema_version,
        "construction_method": payload.construction_method,
        "domain_validity": payload.domain_validity,
        "inverse_available": bool(payload.inverse_available),
        "parameter_keys": sorted(payload.parameters.keys()),
        "generator_metadata_keys": sorted(payload.generator_metadata.keys()),
        "diagnostics_keys": sorted(payload.diagnostics.keys()),
    }


_PAYLOAD_SUMMARIZERS: dict[str, Any] = {
    "generator_family": (GeneratorFamily, _summarize_generator_family_payload),
    "formula_generator_family": (
        FormulaGeneratorFamily,
        _summarize_formula_generator_family_payload,
    ),
    "invariant_map_spec": (InvariantMapSpec, _summarize_invariant_map_spec_payload),
}


# ---------------------------------------------------------------------------
# SymmetryCandidate
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SymmetryCandidate:
    """Representation-neutral wrapper for a candidate Lie symmetry.

    A ``SymmetryCandidate`` records **what a method emitted**, not whether
    the emission has been validated on a residual evaluator. The wrapper
    is deliberately narrow: it fixes the discriminator, provenance, and
    a JSON-safe summary of the payload, and it holds the original
    representation object as an opaque handle for downstream code that
    understands the specific ``representation_type``.

    Attributes
    ----------
    candidate_id:
        Non-empty string identifying this candidate instance. Used for
        provenance-tracing across the pipeline.
    representation_type:
        One of :data:`REPRESENTATION_TYPES`. v0.30.1 stably supports
        ``generator_family``, ``formula_generator_family``, and
        ``invariant_map_spec``. The other four are reserved and are not
        constructible without a validated payload schema.
    mathematical_status:
        One of ``candidate_only`` (default), ``empirically_supported_configured``,
        or ``no_evidence``. **v0.30.1 does not compute this — the caller
        sets it explicitly.** Wrapping does NOT imply
        ``empirically_supported_configured``.
    executable_status:
        One of ``executable``, ``not_executable``, or ``unknown``.
    source_method:
        Non-empty string naming the method that produced the candidate
        (e.g. ``"polynomial_translation_svd"``). Not automatically
        registered.
    payload:
        The representation object itself (``GeneratorFamily``,
        ``FormulaGeneratorFamily``, or ``InvariantMapSpec``). Opaque
        to callers who do not understand ``representation_type``.
    provenance:
        Strict-JSON mapping. Free-form; suggested keys include
        ``method_version``, ``seed``, ``config_key``, ``timestamp``, and
        the residual-evaluator identifier.
    warnings:
        List of strings surfacing method-specific warnings (e.g.
        ``"reference_fallback_used"``). Empty list by default.
    """

    candidate_id: str
    representation_type: str
    mathematical_status: str = "candidate_only"
    executable_status: str = "unknown"
    source_method: str = ""
    payload: Any = None
    provenance: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    SCHEMA_VERSION: ClassVar[str] = "0.1"

    def __post_init__(self) -> None:
        self.candidate_id = _require_nonempty_string(
            self.candidate_id, name="candidate_id"
        )
        self.representation_type = _require_nonempty_string(
            self.representation_type, name="representation_type"
        )
        if self.representation_type not in REPRESENTATION_TYPES:
            raise SchemaValidationError(
                f"representation_type {self.representation_type!r} is not in "
                f"the reserved set; allowed: {sorted(REPRESENTATION_TYPES)!r}."
            )
        if self.mathematical_status not in _MATHEMATICAL_STATUSES:
            raise SchemaValidationError(
                f"mathematical_status must be one of "
                f"{sorted(_MATHEMATICAL_STATUSES)!r}; got "
                f"{self.mathematical_status!r}."
            )
        if self.executable_status not in _EXECUTABLE_STATUSES:
            raise SchemaValidationError(
                f"executable_status must be one of "
                f"{sorted(_EXECUTABLE_STATUSES)!r}; got "
                f"{self.executable_status!r}."
            )
        self.source_method = _require_nonempty_string(
            self.source_method, name="source_method"
        )
        # Reject reserved-but-unimplemented representation types unless
        # the payload is explicitly None (only for the reserved-shape
        # spec-freeze tests).
        if self.representation_type in _RESERVED_REPRESENTATION_TYPES:
            if self.payload is not None:
                raise ScopeValidationError(
                    f"representation_type {self.representation_type!r} is "
                    "reserved but has no validated payload schema in "
                    "v0.30.1; construct a placeholder candidate with "
                    "payload=None only."
                )
        else:
            # Implemented representation: enforce payload type.
            expected_cls, _ = _PAYLOAD_SUMMARIZERS[self.representation_type]
            if not isinstance(self.payload, expected_cls):
                raise SchemaValidationError(
                    f"payload for representation_type "
                    f"{self.representation_type!r} must be a "
                    f"{expected_cls.__name__} instance; got "
                    f"{type(self.payload).__name__!r}."
                )
        self.provenance = _normalize_provenance(self.provenance)
        self.warnings = _normalize_warnings(self.warnings)

    def summarize(self) -> dict[str, Any]:
        """Return a strict-JSON summary of this candidate.

        The summary carries a payload sketch appropriate for the
        ``representation_type`` (shape / schema_version / diagnostic
        keys). It does NOT carry the full payload — callers who need the
        payload access it directly via :attr:`payload`.
        """
        payload_summary: dict[str, Any] | None
        if self.payload is None:
            payload_summary = None
        else:
            _, summarizer = _PAYLOAD_SUMMARIZERS[self.representation_type]
            payload_summary = summarizer(self.payload)
        summary: dict[str, Any] = {
            "summary_schema_version": self.SCHEMA_VERSION,
            "summary_type": "pdelie_symmetry_candidate",
            "candidate_id": self.candidate_id,
            "representation_type": self.representation_type,
            "mathematical_status": self.mathematical_status,
            "executable_status": self.executable_status,
            "source_method": self.source_method,
            "payload_summary": payload_summary,
            "provenance": dict(self.provenance),
            "warnings": list(self.warnings),
        }
        return cast(
            dict[str, Any],
            _validate_strict_json_compatible(
                summary, name="pdelie_symmetry_candidate summary"
            ),
        )


# ---------------------------------------------------------------------------
# Constructors + summarizers
# ---------------------------------------------------------------------------


def build_symmetry_candidate(
    *,
    candidate_id: str,
    representation_type: str,
    payload: Any,
    source_method: str,
    mathematical_status: str = "candidate_only",
    executable_status: str = "unknown",
    provenance: Mapping[str, Any] | None = None,
    warnings_out: Any = None,
    allow_reserved_unimplemented: bool = False,
) -> SymmetryCandidate:
    """Construct a :class:`SymmetryCandidate` with validation.

    Delegates to :class:`SymmetryCandidate` after normalizing the
    provenance and warnings. The ``allow_reserved_unimplemented`` flag
    is a narrow escape hatch for the reserved-representation-type
    spec-freeze tests — production callers must not use it.
    """
    if (
        representation_type in _RESERVED_REPRESENTATION_TYPES
        and not allow_reserved_unimplemented
        and payload is None
    ):
        # Emit a UserWarning; explicit is better than silent.
        warnings.warn(
            f"constructing a placeholder SymmetryCandidate for reserved "
            f"representation_type {representation_type!r}; production "
            "callers must not use this path.",
            UserWarning,
            stacklevel=2,
        )
    return SymmetryCandidate(
        candidate_id=candidate_id,
        representation_type=representation_type,
        mathematical_status=mathematical_status,
        executable_status=executable_status,
        source_method=source_method,
        payload=payload,
        provenance=copy.deepcopy(dict(provenance)) if provenance else {},
        warnings=list(warnings_out) if warnings_out else [],
    )


def summarize_symmetry_candidate(candidate: SymmetryCandidate) -> dict[str, Any]:
    """Return the strict-JSON summary for a :class:`SymmetryCandidate`."""
    if not isinstance(candidate, SymmetryCandidate):
        raise SchemaValidationError(
            f"summarize_symmetry_candidate requires a SymmetryCandidate; "
            f"got {type(candidate).__name__!r}."
        )
    return candidate.summarize()
