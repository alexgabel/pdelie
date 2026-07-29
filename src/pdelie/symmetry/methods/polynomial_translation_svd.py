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
- Scalar 1D input only. Since v0.33a **nonperiodic** input is accepted and
  dispatches through the interior-only branch of ``fit_translation_generator``
  (finite-difference derivatives, boundary rows shaved by the residual
  evaluator's ``boundary_trim_width``). Acceptance is **not** a claim of
  boundary-value-problem preservation: the nonperiodic branch establishes
  interior differential-operator covariance only, and the narrower claim is
  carried by the ``symmetry_claim`` entry in ``fit_diagnostics``.

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

import numpy as np

from pdelie.contracts import FieldBatch, GeneratorFamily
from pdelie.errors import ScopeValidationError
from pdelie.residuals.base import ResidualEvaluator
from pdelie.symmetry.admissibility import score_against_reference
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


#: v0.32b frozen score-name → metadata mapping for
#: :class:`PolynomialTranslationSvdMethod`. Consumers who need the enriched
#: form (value + direction + description + units) look up the direction/
#: description/units here and pair them with the ``method_scores`` values
#: emitted on :class:`SymmetryMethodResult`. See
#: ``docs/design/GENERATOR_CONFIDENCE_ADDITIVE_FIELDS.md``.
SCORE_METADATA: dict[str, dict[str, Any]] = {
    "span_distance": {
        "direction": "lower_is_better",
        "description": (
            "Post-selection SVD span-distance of the chosen translation "
            "coefficient direction (0 == exactly translation-invariant)."
        ),
        "units": None,
    },
    "residual_l2": {
        "direction": "lower_is_better",
        "description": (
            "L2 norm of the baseline residual field emitted by the "
            "residual evaluator on the input FieldBatch."
        ),
        "units": None,
    },
    "error_curve_max": {
        "direction": "diagnostic_only",
        "description": (
            "Maximum L2 norm of the finite-difference deltas across the "
            "polynomial basis; larger implies stronger perturbation signal."
        ),
        "units": None,
    },
    "svd_condition_number": {
        "direction": "diagnostic_only",
        "description": (
            "Ratio of the largest to smallest SVD singular value of the "
            "design matrix; None when the smallest singular value is zero."
        ),
        "units": None,
    },
}


@dataclass(slots=True)
class PolynomialTranslationSvdMethod:
    """v0.30.1 built-in adapter implementing :class:`SymmetryMethod`.

    Constructed by :func:`build_method`. Not intended for direct
    instantiation by users — go through the registry.
    """

    METADATA: ClassVar[SymmetryMethodMetadata] = (
        _BUILTIN_POLYNOMIAL_TRANSLATION_SVD_METADATA
    )

    #: Frozen score-metadata surface (v0.32b). Exposed as a class attribute
    #: for the confidence-report enrichment helper.
    SCORE_METADATA: ClassVar[dict[str, dict[str, Any]]] = SCORE_METADATA

    def fit(
        self,
        field: FieldBatch,
        *,
        residual_evaluator: ResidualEvaluator | None = None,
        config: Mapping[str, Any] | None = None,
        reference_generator_family: GeneratorFamily | None = None,
        reference_generator_family_id: str | None = None,
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
        # v0.33a: nonperiodic inputs dispatch through the interior-only branch of
        # fit_translation_generator. The claim they support is narrower than the
        # periodic one -- interior differential-operator covariance, not
        # boundary-value-problem preservation -- and is carried by the
        # `symmetry_claim` diagnostic rather than by acceptance alone.
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
        # v0.32b: the emitted ``method_scores`` uses the FROZEN score names
        # from configs/planning/v0_32_method_scores_scope.json. The
        # semantic mapping from the underlying diagnostics:
        #
        #   span_distance         <- selected_span_distance (post-selection)
        #   residual_l2           <- L2 norm of the residual field
        #   error_curve_max       <- max of basis_delta_norms.values()
        #   svd_condition_number  <- condition_number
        #
        # Direction/description/units metadata lives on the class-level
        # SCORE_METADATA attribute for the confidence-report enrichment
        # helper; see ``docs/design/GENERATOR_CONFIDENCE_ADDITIVE_FIELDS.md``.
        diag = dict(generator_family.diagnostics)
        residual_l2 = self._compute_residual_l2(field, residual_evaluator)
        error_curve_max = self._compute_error_curve_max(diag)
        method_scores: dict[str, float | None] = {
            "span_distance": _finite_float_or_none(
                diag.get("selected_span_distance")
            ),
            "residual_l2": residual_l2,
            "error_curve_max": error_curve_max,
            "svd_condition_number": _finite_float_or_none(
                diag.get("condition_number")
            ),
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
            # v0.33a boundary-dispatch diagnostics, forwarded verbatim.
            "boundary_condition_x": diag.get("boundary_condition_x"),
            "boundary_condition_dispatch_reason": diag.get(
                "boundary_condition_dispatch_reason"
            ),
            "interior_only_reduction_applied": bool(
                diag.get("interior_only_reduction_applied", False)
            ),
            "interior_only_row_count": diag.get("interior_only_row_count"),
            "interior_only_trim_width": diag.get("interior_only_trim_width"),
            "symmetry_claim": diag.get("symmetry_claim"),
            # Pre-fallback span, so callers can see the honest fit quality even
            # on the periodic branch where the reference fallback may fire.
            "svd_span_distance": _finite_float_or_none(diag.get("svd_span_distance")),
            # v0.34b: reference-relative admissibility. A nested block, NOT a
            # fifth score name -- the frozen four are an invariant, and
            # admissibility is a diagnostic about a caller-supplied reference
            # rather than a property of this fit alone. None when no reference
            # is supplied.
            "variable_coefficient_admissibility": None,
        }

        if reference_generator_family is not None:
            if reference_generator_family_id is None:
                raise ScopeValidationError(
                    f"{_METHOD_NAME}.fit requires reference_generator_family_id "
                    "whenever reference_generator_family is supplied; a score "
                    "against an unidentified reference is not traceable."
                )
            fit_diagnostics["variable_coefficient_admissibility"] = (
                score_against_reference(
                    generator_family,
                    reference_generator_family,
                    reference_generator_family_id=reference_generator_family_id,
                )
            )
        elif reference_generator_family_id is not None:
            raise ScopeValidationError(
                f"{_METHOD_NAME}.fit received reference_generator_family_id "
                "without reference_generator_family; supply both or neither."
            )
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


    # --- v0.32b score-computation helpers ---------------------------------

    @staticmethod
    def _compute_residual_l2(
        field: FieldBatch, residual_evaluator: ResidualEvaluator
    ) -> float | None:
        """Return the L2 norm of the residual field, or ``None`` on failure.

        The residual evaluator was already invoked inside
        ``fit_translation_generator`` for the baseline_residual computation;
        we re-invoke here for the top-level ``residual_l2`` score without
        assuming the underlying fit exposes the intermediate residual.
        """
        try:
            residual = residual_evaluator.evaluate(field).residual
        except Exception:  # noqa: BLE001 — degrade gracefully to None
            return None
        residual_array = np.asarray(residual, dtype=float).reshape(-1)
        if residual_array.size == 0:
            return None
        if not np.all(np.isfinite(residual_array)):
            return None
        return float(np.linalg.norm(residual_array))

    @staticmethod
    def _compute_error_curve_max(diag: dict[str, Any]) -> float | None:
        """Return max of basis_delta_norms.values(), or ``None`` on failure."""
        basis_delta_norms = diag.get("basis_delta_norms")
        if not isinstance(basis_delta_norms, dict) or not basis_delta_norms:
            return None
        values = [
            _finite_float_or_none(v) for v in basis_delta_norms.values()
        ]
        finite_values = [v for v in values if v is not None]
        if not finite_values:
            return None
        return max(finite_values)


def build_method() -> PolynomialTranslationSvdMethod:
    """Factory used by the registry to build a fresh adapter instance."""
    return PolynomialTranslationSvdMethod()


# --- v0.32b: opt-in batch-bootstrap uncertainty -----------------------------


_BOOTSTRAP_MIN_UNITS_DEFAULT = 8
_BOOTSTRAP_INTERVAL_LEVEL_DEFAULT = 0.95
_BOOTSTRAP_NUM_RESAMPLES_DEFAULT = 64
_BOOTSTRAP_SCORE_NAMES: tuple[str, ...] = (
    "span_distance",
    "residual_l2",
    "error_curve_max",
    "svd_condition_number",
)


def _slice_field_batch_by_batch_indices(
    field: FieldBatch, indices: np.ndarray[Any, Any]
) -> FieldBatch:
    """Return a FieldBatch containing the selected batch rows.

    Keeps the same dims / var_names / metadata / preprocess_log /
    boundary conditions; only the values (and mask, if present) are
    resampled along the batch axis.
    """
    if "batch" not in field.dims:
        raise ScopeValidationError(
            "bootstrap_uncertainty requires a FieldBatch with a 'batch' dim."
        )
    batch_axis = field.dims.index("batch")
    resampled_values = np.take(field.values, indices, axis=batch_axis)
    resampled_mask = None
    if field.mask is not None:
        resampled_mask = np.take(field.mask, indices, axis=batch_axis)
    # Coords stay identical (batch has no coord array under the scalar 1D
    # contract because "batch" is not required in required_coord_dims).
    return FieldBatch(
        schema_version=field.schema_version,
        values=resampled_values,
        dims=field.dims,
        coords={k: v.copy() for k, v in field.coords.items()},
        var_names=list(field.var_names),
        metadata={k: v for k, v in field.metadata.items()},
        preprocess_log=[dict(entry) for entry in field.preprocess_log],
        mask=resampled_mask,
    )


def _percentile_interval(
    samples: list[float], interval_level: float
) -> tuple[float | None, float | None]:
    if not samples:
        return None, None
    array = np.asarray(samples, dtype=float)
    if array.size == 0 or not np.all(np.isfinite(array)):
        finite = array[np.isfinite(array)]
        if finite.size == 0:
            return None, None
        array = finite
    alpha = (1.0 - interval_level) / 2.0
    low = float(np.quantile(array, alpha))
    high = float(np.quantile(array, 1.0 - alpha))
    if not (math.isfinite(low) and math.isfinite(high)):
        return None, None
    return low, high


def bootstrap_uncertainty(
    field: FieldBatch,
    residual_evaluator: ResidualEvaluator,
    *,
    seed: int,
    num_resamples: int = _BOOTSTRAP_NUM_RESAMPLES_DEFAULT,
    interval_level: float = _BOOTSTRAP_INTERVAL_LEVEL_DEFAULT,
    min_units: int = _BOOTSTRAP_MIN_UNITS_DEFAULT,
    resampling_unit: str = "batch",
) -> dict[str, Any]:
    """Batch-bootstrap uncertainty helper for :func:`fit`.

    Opt-in. Refuses row-level bootstrap outright — resampling MUST occur
    at the batch (trajectory) unit, never over spatial or temporal rows
    (correlated for PDE dynamics; row bootstrap invalidates the interval).
    Returns an uncertainty report ready to hand to
    :func:`pdelie.reporting.summarize_generator_confidence`
    ``uncertainty_report=...``.

    Contract (frozen v0.32b):

    - ``resampling_unit`` must be ``"batch"``. Anything else (in
      particular ``"row"``) raises :class:`ScopeValidationError`. There
      is no silent fallback.
    - ``seed`` is required; ``np.random.default_rng(seed)`` selects batch
      indices; same seed + same field → byte-identical intervals.
    - When the number of independent batch units is below ``min_units``,
      the report is emitted with ``sample_count = actual``, empty
      intervals, and a warning entry — never a spurious interval.
    - Each resample re-runs the full underlying fit; the bootstrap does
      NOT resample precomputed scalar scores.
    - Any resample whose fit raises is caught, counted in
      ``failed_resamples``, and excluded from the interval computation.
    """
    if resampling_unit == "row":
        raise ScopeValidationError(
            "bootstrap_uncertainty refuses row-level bootstrap: spatial "
            "and temporal rows are correlated under PDE dynamics; use "
            "resampling_unit='batch' (or 'trajectory'), or hand-craft an "
            "explicit uncertainty_report."
        )
    if resampling_unit not in ("batch", "trajectory"):
        raise ScopeValidationError(
            "bootstrap_uncertainty resampling_unit must be 'batch' or "
            f"'trajectory'; got {resampling_unit!r}."
        )
    if not isinstance(field, FieldBatch):
        raise ScopeValidationError(
            "bootstrap_uncertainty requires a FieldBatch."
        )
    if residual_evaluator is None:
        raise ScopeValidationError(
            "bootstrap_uncertainty requires a residual_evaluator."
        )
    if not isinstance(num_resamples, int) or num_resamples <= 0:
        raise ScopeValidationError(
            "num_resamples must be a positive integer."
        )
    if not isinstance(min_units, int) or min_units <= 0:
        raise ScopeValidationError("min_units must be a positive integer.")
    if (
        not isinstance(interval_level, (int, float))
        or isinstance(interval_level, bool)
        or not (0.0 < float(interval_level) < 1.0)
    ):
        raise ScopeValidationError(
            "interval_level must be a finite float strictly in (0.0, 1.0)."
        )
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ScopeValidationError("seed must be an integer.")

    batch_size = field.values.shape[field.dims.index("batch")]
    warnings_out: list[str] = []

    method = PolynomialTranslationSvdMethod()
    # Point estimates on the original field.
    point_result = method.fit(field, residual_evaluator=residual_evaluator)
    point_estimates: dict[str, float | None] = {
        name: point_result.method_scores.get(name)
        for name in _BOOTSTRAP_SCORE_NAMES
    }

    intervals: dict[str, dict[str, float | None]] = {
        name: {"low": None, "high": None} for name in _BOOTSTRAP_SCORE_NAMES
    }

    if batch_size < min_units:
        warnings_out.append(
            f"insufficient_independent_units:{batch_size}<{min_units}"
        )
        return {
            "method": "bootstrap",
            "resampling_unit": resampling_unit,
            "sample_count": int(batch_size),
            "seed": int(seed),
            "interval_level": float(interval_level),
            "intervals": intervals,
            "point_estimates": point_estimates,
            "failed_resamples": 0,
            "warnings": warnings_out,
            "diagnostic_only": True,
        }

    rng = np.random.default_rng(seed)
    samples: dict[str, list[float]] = {
        name: [] for name in _BOOTSTRAP_SCORE_NAMES
    }
    failed_resamples = 0
    for _ in range(num_resamples):
        indices = rng.integers(low=0, high=batch_size, size=batch_size)
        try:
            resampled = _slice_field_batch_by_batch_indices(field, indices)
            resample_result = method.fit(
                resampled, residual_evaluator=residual_evaluator
            )
        except Exception:  # noqa: BLE001 — count failed resamples explicitly
            failed_resamples += 1
            continue
        for name in _BOOTSTRAP_SCORE_NAMES:
            score = resample_result.method_scores.get(name)
            if score is None:
                continue
            score_float = float(score)
            if math.isfinite(score_float):
                samples[name].append(score_float)

    for name in _BOOTSTRAP_SCORE_NAMES:
        low, high = _percentile_interval(samples[name], float(interval_level))
        intervals[name] = {"low": low, "high": high}
        if low is None or high is None:
            warnings_out.append(f"empty_interval_for_score:{name}")

    if failed_resamples > 0:
        warnings_out.append(f"failed_resamples:{failed_resamples}")

    return {
        "method": "bootstrap",
        "resampling_unit": resampling_unit,
        "sample_count": int(batch_size),
        "seed": int(seed),
        "interval_level": float(interval_level),
        "intervals": intervals,
        "point_estimates": point_estimates,
        "failed_resamples": int(failed_resamples),
        "warnings": warnings_out,
        "diagnostic_only": True,
    }
