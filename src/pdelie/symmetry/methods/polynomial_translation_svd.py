"""v0.30.1 built-in symmetry-method adapter: polynomial_translation_svd.

Wraps :func:`pdelie.symmetry.fitting.translation_baseline.fit_translation_generator`
in the v0.30.1 ``SymmetryMethod`` registry contract, without altering the
underlying numerics. Produces exactly one :class:`SymmetryCandidate`
carrying a :class:`GeneratorFamily` payload
(``representation_type="generator_family"``).

Architectural notes
-------------------

- The adapter DOES NOT run verification. Downstream users must call
  :func:`pdelie.verification.verify_translation_generator` or
  :func:`pdelie.symmetry.validate_symmetry_candidate` separately to
  determine evidence.
- The adapter DOES NOT select a "best" candidate. It returns a single
  candidate; the registry does not rank.
- The adapter DOES NOT rename method-native quantities to "confidence".
  ``method_scores`` carries SVD span distance, condition number, and
  the l2 norms of the finite-difference deltas — all method-native and
  finite (or None).
- Periodic scalar 1D input only. Nonperiodic inputs raise a
  :class:`ScopeValidationError` before any expensive computation.

Public callable: :func:`build_method`. The registry factory resolves
``pdelie.symmetry.methods.polynomial_translation_svd:build_method`` and
invokes it with no arguments.
"""

from __future__ import annotations

import importlib.metadata as _importlib_metadata
import math
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, ClassVar

from pdelie._boundary import is_x_periodic
from pdelie.contracts import FieldBatch
from pdelie.errors import ScopeValidationError
from pdelie.residuals.base import ResidualEvaluator
from pdelie.symmetry.candidates import build_symmetry_candidate
from pdelie.symmetry.fitting.translation_baseline import fit_translation_generator
from pdelie.symmetry.registry import (
    _BUILTIN_POLYNOMIAL_TRANSLATION_SVD_METADATA,
    SymmetryMethodMetadata,
    SymmetryMethodResult,
)

_METHOD_NAME = "polynomial_translation_svd"
_DEFAULT_EPSILON = 1e-4


def _finite_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        cast_value = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(cast_value):
        return None
    return cast_value


def _resolve_backend_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for dist_name, key in (
        ("pdelie", "pdelie"),
        ("numpy", "numpy"),
    ):
        try:
            versions[key] = _importlib_metadata.version(dist_name)
        except _importlib_metadata.PackageNotFoundError:
            continue
    return versions


@dataclass(slots=True)
class PolynomialTranslationSvdMethod:
    """v0.30.1 built-in adapter implementing :class:`SymmetryMethod`.

    Constructed by :func:`build_method`. Not intended for direct
    instantiation by users — go through the registry.
    """

    METADATA: ClassVar[SymmetryMethodMetadata] = (
        _BUILTIN_POLYNOMIAL_TRANSLATION_SVD_METADATA
    )

    def fit(
        self,
        field: FieldBatch,
        *,
        residual_evaluator: ResidualEvaluator | None = None,
        config: Mapping[str, Any] | None = None,
    ) -> SymmetryMethodResult:
        if not isinstance(field, FieldBatch):
            raise ScopeValidationError(
                f"{_METHOD_NAME}.fit requires a FieldBatch; got "
                f"{type(field).__name__!r}. File-path input, ndarray "
                "coercion, and xarray coercion are out of scope for v0.30.1."
            )
        if residual_evaluator is None:
            raise ScopeValidationError(
                f"{_METHOD_NAME}.fit requires a residual_evaluator; the "
                "closed-form SVD fit is defined against a residual measure."
            )
        if not is_x_periodic(field):
            raise ScopeValidationError(
                f"{_METHOD_NAME}.fit requires a periodic-x FieldBatch. "
                "Nonperiodic inputs are out of scope for v0.30.1; see "
                "docs/design/PYSINDY_COMPATIBILITY_POLICY.md."
            )
        normalized_config: dict[str, Any] = (
            {} if config is None else dict(config)
        )
        # Only one config knob is honored by v0.30.1: the training epsilon.
        epsilon = normalized_config.get("epsilon", _DEFAULT_EPSILON)
        try:
            epsilon = float(epsilon)
        except (TypeError, ValueError) as exc:
            raise ScopeValidationError(
                f"{_METHOD_NAME}.fit config['epsilon'] must be a finite "
                "float."
            ) from exc
        if not math.isfinite(epsilon) or epsilon <= 0.0:
            raise ScopeValidationError(
                f"{_METHOD_NAME}.fit config['epsilon'] must be positive "
                f"and finite; got {epsilon!r}."
            )

        start = time.perf_counter()
        generator_family = fit_translation_generator(
            field, residual_evaluator, epsilon=epsilon
        )
        runtime_seconds = time.perf_counter() - start

        # Extract method-native scalar quantities from the diagnostics.
        # The underlying fit_translation_generator records these in the
        # GeneratorFamily.diagnostics dict; we surface a subset with
        # method_scores + preserve booleans as booleans in fit_diagnostics.
        diag = dict(generator_family.diagnostics)
        method_scores: dict[str, float | None] = {
            "svd_span_distance": _finite_float_or_none(diag.get("svd_span_distance")),
            "selected_span_distance": _finite_float_or_none(
                diag.get("selected_span_distance")
            ),
            "condition_number": _finite_float_or_none(diag.get("condition_number")),
            "fit_residual": _finite_float_or_none(diag.get("fit_residual")),
        }

        # fit_diagnostics: everything that is not a scalar score. Preserve
        # bool booleans as booleans (do not coerce to floats).
        fit_diagnostics: dict[str, Any] = {
            "training_epsilon": _finite_float_or_none(diag.get("training_epsilon")),
            "fit_mode": diag.get("fit_mode"),
            "evidence_label": diag.get("evidence_label"),
            "fallback_reason": diag.get("fallback_reason"),
            "reference_fallback_used": bool(
                diag.get("reference_fallback_used", False)
            ),
            "min_delta_basis": diag.get("min_delta_basis"),
            "basis": list(diag.get("basis", [])),
            "singular_values": list(diag.get("singular_values", [])),
        }
        warnings_out: list[str] = []
        if fit_diagnostics["reference_fallback_used"]:
            warnings_out.append("reference_fallback_used")

        candidate = build_symmetry_candidate(
            candidate_id=f"{_METHOD_NAME}::translation::0",
            representation_type="generator_family",
            payload=generator_family,
            source_method=_METHOD_NAME,
            mathematical_status="candidate_only",
            executable_status="executable",
            provenance={
                "fit_mode": diag.get("fit_mode"),
                "evidence_label": diag.get("evidence_label"),
                "training_epsilon": _finite_float_or_none(
                    diag.get("training_epsilon")
                ),
                "residual_evaluator": type(residual_evaluator).__name__,
                "field_dims": list(field.dims),
                "field_schema_version": field.SCHEMA_VERSION,
            },
            warnings_out=list(warnings_out),
        )

        return SymmetryMethodResult(
            method_name=_METHOD_NAME,
            candidates=[candidate],
            method_scores=method_scores,
            fit_diagnostics=fit_diagnostics,
            runtime_seconds=_finite_float_or_none(runtime_seconds),
            peak_memory_mb=None,
            seed=None,
            deterministic=True,
            warnings=list(warnings_out),
            backend_versions=_resolve_backend_versions(),
            provenance={
                "residual_evaluator": type(residual_evaluator).__name__,
                "field_schema_version": field.SCHEMA_VERSION,
                "field_dims": list(field.dims),
                "config": {"epsilon": float(epsilon)},
                "method_version": self.METADATA.method_version,
            },
        )


def build_method() -> PolynomialTranslationSvdMethod:
    """Factory used by the registry to build a fresh adapter instance."""
    return PolynomialTranslationSvdMethod()
