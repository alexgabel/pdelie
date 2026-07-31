"""v0.36d: assumptions sparse-recovery theorems require, reported as diagnostics.

Two reports. The first evaluates *theoretical* conditions on a design matrix and
a candidate support; the second measures *empirical* support stability under
resampling. They are separate functions because they are separate claims, and a
reader must be able to tell which one produced a given number.

What this module refuses to say
===============================

No status here says "recoverable". The vocabulary is theorem-specific --
``lasso_sign_consistency_condition_satisfied`` names a condition from a specific
result under specific assumptions, and satisfying it is not the same as
recovering anything. A diagnostic that reported "recoverable" would be making a
claim about an algorithm it never ran, on noise it never saw, under a
regularization path it was not given. The forbidden vocabulary is asserted
absent from both this source file and every emitted payload.

Signed versus uniform: measured to be a real distinction
========================================================

``rho_signed`` depends on the sign pattern of the true coefficients;
``rho_uniform`` is the worst case over all sign patterns. Measured on a 4x3
correlated matrix with support ``[0, 1]``, the difference is decisive:

======================  ====================
sign pattern            ``rho_signed``
======================  ====================
``s = [+, +]``          **1.56197280263**
``s = [+, -]``          **1.11022302463e-16**
``rho_uniform``         **1.56197280263**
======================  ====================

The sign pattern moves the constant across the threshold. So ``sign_patterns``
is not decorative, and when it is unavailable the honest report is
``sign_pattern_unavailable`` with uniform as the only actionable statistic --
not a signed value computed against an assumed pattern.

No pseudoinverse fallback, and why the rank check is still needed
================================================================

``np.linalg.solve`` on a singular Gram matrix raises ``LinAlgError``, which is
the behaviour this module wants: v0.35a measured ``lstsq`` silently returning
``0.4956551696`` from exactly such a system -- finite, plausible, below
threshold, and meaningless.

But the protection is partial. ``solve`` raises on *exact* singularity; a Gram
matrix at ``cond ~ 1e13`` does not raise and returns numerical noise. Hence
:data:`ACTIVE_SUPPORT_CONDITION_LIMIT`, which covers the near-singular gap the
raise leaves open. Measured: real 2-element supports of the canonical weak
matrix reach ``cond(G_SS) = 20.85``; the exactly-singular case sits at
``1.39e17``. The cutoff sits in an empty gap between them.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import Any, Literal

import numpy as np

from pdelie.discovery.column_normalize import column_normalize_design_matrix
from pdelie.errors import ScopeValidationError, ShapeValidationError

__all__ = [
    "ACTIVE_SUPPORT_CONDITION_LIMIT",
    "IRREPRESENTABILITY_THRESHOLD",
    "RESAMPLING_UNITS",
    "SPARSE_RECOVERY_STATUSES",
    "empirical_support_stability_report",
    "sparse_recovery_assumption_report",
]

#: The threshold the theorems are stated against. Not tunable, not a pilot
#: output -- carried from :mod:`pdelie.diagnostics.design_matrix`.
IRREPRESENTABILITY_THRESHOLD = 1.0

#: Above this Gram condition number the constant is refused rather than
#: computed. Set by the v0.36d pilot: real supports reach 20.85, exact
#: singularity sits at 1.39e17, and this sits in the empty gap between.
ACTIVE_SUPPORT_CONDITION_LIMIT = 1e12

#: Frozen status vocabulary. Every entry is reachable on a real input; the
#: confirmatory freeze records which input reaches each.
SPARSE_RECOVERY_STATUSES: tuple[str, ...] = (
    "lasso_sign_consistency_condition_satisfied",
    "lasso_sign_consistency_condition_violated",
    "uniform_irrepresentability_bound_satisfied",
    "uniform_irrepresentability_bound_violated",
    "undefined_singular_support",
    "sign_pattern_unavailable",
    "insufficient_assumptions_for_recovery_claim",
)

#: Resampling units that respect the correlation structure of PDE-derived data.
#: ``row`` is deliberately absent; see :func:`empirical_support_stability_report`.
RESAMPLING_UNITS: tuple[str, ...] = ("trajectory", "complementary_pair")

_NORMALIZATION_POLICIES = ("column_l2", "none")
_RESTRICTED_EIGENVALUE_DEFINITIONS = (
    "active_support_min_singular_value",
    "sampled_re_lower_bound",
)


def _validated_matrix(design_matrix: object) -> np.ndarray:
    values = np.asarray(design_matrix, dtype=float)
    if values.ndim != 2:
        raise ShapeValidationError(
            f"design_matrix must be two-dimensional; got shape {values.shape}."
        )
    if values.size == 0:
        raise ScopeValidationError("design_matrix must contain at least one entry.")
    if not np.all(np.isfinite(values)):
        raise ScopeValidationError("design_matrix must be finite everywhere.")
    return values


def _validated_support(support: object, n_features: int, *, index: int) -> list[int]:
    if isinstance(support, (str, bytes)) or not isinstance(support, Sequence):
        raise ScopeValidationError(
            f"candidate_supports[{index}] must be a sequence of column indices."
        )
    try:
        indices = [int(value) for value in support]
    except (TypeError, ValueError) as exc:
        raise ScopeValidationError(
            f"candidate_supports[{index}] must contain integers."
        ) from exc
    if not indices:
        raise ScopeValidationError(
            f"candidate_supports[{index}] is empty; an empty support has no "
            f"irrepresentability condition to evaluate."
        )
    if len(set(indices)) != len(indices):
        raise ScopeValidationError(
            f"candidate_supports[{index}] repeats a column index."
        )
    out_of_range = [value for value in indices if not 0 <= value < n_features]
    if out_of_range:
        raise ScopeValidationError(
            f"candidate_supports[{index}] indices {out_of_range} are outside "
            f"[0, {n_features})."
        )
    return sorted(indices)


def _validated_sign_pattern(
    pattern: object, support_size: int, *, index: int
) -> np.ndarray | None:
    if pattern is None:
        return None
    if isinstance(pattern, (str, bytes)) or not isinstance(pattern, Sequence):
        raise ScopeValidationError(
            f"sign_patterns[{index}] must be a sequence of +1/-1 values or None."
        )
    values = np.asarray(pattern, dtype=float)
    if values.shape != (support_size,):
        raise ShapeValidationError(
            f"sign_patterns[{index}] has shape {values.shape}; expected "
            f"({support_size},) to match its support."
        )
    if not np.all(np.isin(values, (-1.0, 1.0))):
        raise ScopeValidationError(
            f"sign_patterns[{index}] must contain only +1 and -1; a sign pattern "
            f"records the sign of each active coefficient."
        )
    return values


def _gram_blocks(
    normalized: np.ndarray, support: list[int]
) -> tuple[np.ndarray, np.ndarray | None, list[int]]:
    n_rows = normalized.shape[0]
    outside = [j for j in range(normalized.shape[1]) if j not in set(support)]
    gram_ss = normalized[:, support].T @ normalized[:, support] / n_rows
    if not outside:
        return gram_ss, None, outside
    gram_scs = normalized[:, outside].T @ normalized[:, support] / n_rows
    return gram_ss, gram_scs, outside


def _support_is_usable(
    normalized: np.ndarray, support: list[int], gram_ss: np.ndarray
) -> tuple[bool, float | None, int, list[str]]:
    """Rank and conditioning gate, before any solve is attempted."""
    warnings_out: list[str] = []
    block = normalized[:, support]
    singular_values = np.linalg.svd(block, compute_uv=False)
    tolerance = (
        max(block.shape) * float(np.finfo(float).eps) * float(singular_values[0])
        if singular_values.size
        else 0.0
    )
    rank = int((singular_values > tolerance).sum())
    if rank < len(support):
        return False, None, rank, ["active_support_is_rank_deficient"]

    condition = float(np.linalg.cond(gram_ss))
    if not math.isfinite(condition) or condition > ACTIVE_SUPPORT_CONDITION_LIMIT:
        warnings_out.append("poorly_conditioned_active_support")
        return False, condition if math.isfinite(condition) else None, rank, warnings_out
    return True, condition, rank, warnings_out


def _rho_signed(
    gram_ss: np.ndarray, gram_scs: np.ndarray, sign_pattern: np.ndarray
) -> float | None:
    try:
        coefficients = np.linalg.solve(gram_ss, sign_pattern)
    except np.linalg.LinAlgError:
        # Deliberately no pseudoinverse fallback: a minimum-norm substitute
        # returns a finite, plausible number from a system that determines none.
        return None
    return float(np.max(np.abs(gram_scs @ coefficients)))


def _rho_uniform(gram_ss: np.ndarray, gram_scs: np.ndarray) -> float | None:
    try:
        product = gram_scs @ np.linalg.inv(gram_ss)
    except np.linalg.LinAlgError:
        return None
    return float(np.abs(product).sum(axis=1).max())


def _support_entry(
    normalized: np.ndarray,
    support: list[int],
    sign_pattern: np.ndarray | None,
) -> dict[str, Any]:
    gram_ss, gram_scs, outside = _gram_blocks(normalized, support)
    warnings_out: list[str] = []
    statuses: list[str] = []

    if gram_scs is None:
        return {
            "support": list(support),
            "support_size": len(support),
            "off_support_size": 0,
            "rho_signed": None,
            "rho_signed_available": False,
            "rho_uniform": None,
            "rho_uniform_available": False,
            "active_support_min_singular_value": None,
            "active_support_rank": len(support),
            "active_support_gram_condition_number": None,
            "statuses": ["insufficient_assumptions_for_recovery_claim"],
            "warnings": ["support_covers_every_column"],
        }

    usable, condition, rank, gate_warnings = _support_is_usable(
        normalized, support, gram_ss
    )
    warnings_out.extend(gate_warnings)

    singular_values = np.linalg.svd(normalized[:, support], compute_uv=False)
    min_singular = (
        float(singular_values.min() ** 2 / normalized.shape[0])
        if singular_values.size
        else None
    )

    if not usable:
        statuses.append("undefined_singular_support")
        rho_signed: float | None = None
        rho_uniform: float | None = None
    else:
        rho_uniform = _rho_uniform(gram_ss, gram_scs)
        if rho_uniform is None:
            statuses.append("undefined_singular_support")
        else:
            statuses.append(
                "uniform_irrepresentability_bound_satisfied"
                if rho_uniform < IRREPRESENTABILITY_THRESHOLD
                else "uniform_irrepresentability_bound_violated"
            )

        if sign_pattern is None:
            rho_signed = None
            statuses.append("sign_pattern_unavailable")
            warnings_out.append("uniform_bound_is_the_only_actionable_statistic")
        else:
            rho_signed = _rho_signed(gram_ss, gram_scs, sign_pattern)
            if rho_signed is None:
                statuses.append("undefined_singular_support")
            else:
                statuses.append(
                    "lasso_sign_consistency_condition_satisfied"
                    if rho_signed < IRREPRESENTABILITY_THRESHOLD
                    else "lasso_sign_consistency_condition_violated"
                )

    return {
        "support": list(support),
        "support_size": len(support),
        "off_support_size": len(outside),
        "rho_signed": rho_signed,
        "rho_signed_available": rho_signed is not None,
        "rho_uniform": rho_uniform,
        "rho_uniform_available": rho_uniform is not None,
        "active_support_min_singular_value": min_singular,
        "active_support_rank": rank,
        "active_support_gram_condition_number": condition,
        "statuses": statuses,
        "warnings": warnings_out,
    }


def sparse_recovery_assumption_report(
    design_matrix: object,
    *,
    candidate_supports: object,
    sign_patterns: object = None,
    normalization_policy: Literal["column_l2", "none"] = "column_l2",
    restricted_eigenvalue_definition: Literal[
        "active_support_min_singular_value", "sampled_re_lower_bound"
    ] = "active_support_min_singular_value",
) -> dict[str, Any]:
    """Evaluate theoretical sparse-recovery assumptions per candidate support.

    Every field is always populated. Where a quantity is undefined the value is
    ``None`` and a sibling ``*_available`` flag says so, rather than the field
    being omitted -- a consumer should never have to distinguish "absent because
    undefined" from "absent because this version did not compute it".
    """
    values = _validated_matrix(design_matrix)
    if normalization_policy not in _NORMALIZATION_POLICIES:
        raise ScopeValidationError(
            f"normalization_policy must be one of {list(_NORMALIZATION_POLICIES)}."
        )
    if restricted_eigenvalue_definition not in _RESTRICTED_EIGENVALUE_DEFINITIONS:
        raise ScopeValidationError(
            f"restricted_eigenvalue_definition must be one of "
            f"{list(_RESTRICTED_EIGENVALUE_DEFINITIONS)}."
        )
    if restricted_eigenvalue_definition == "sampled_re_lower_bound":
        raise ScopeValidationError(
            "restricted_eigenvalue_definition='sampled_re_lower_bound' is "
            "reserved and not implemented; it requires a sampling procedure "
            "that has not been specified or measured."
        )
    if isinstance(candidate_supports, (str, bytes)) or not isinstance(
        candidate_supports, Sequence
    ):
        raise ScopeValidationError("candidate_supports must be a sequence of supports.")
    if not candidate_supports:
        raise ScopeValidationError("candidate_supports must be non-empty.")

    if normalization_policy == "column_l2":
        normalized, _scaling, zero_columns = column_normalize_design_matrix(values)
        normalized = np.asarray(normalized, dtype=float)
    else:
        normalized = values
        zero_columns = int((np.linalg.norm(values, axis=0) == 0).sum())

    supports = [
        _validated_support(support, normalized.shape[1], index=index)
        for index, support in enumerate(candidate_supports)
    ]

    if sign_patterns is None:
        patterns: list[np.ndarray | None] = [None] * len(supports)
    else:
        if isinstance(sign_patterns, (str, bytes)) or not isinstance(
            sign_patterns, Sequence
        ):
            raise ScopeValidationError("sign_patterns must be a sequence or None.")
        if len(sign_patterns) != len(supports):
            raise ScopeValidationError(
                f"sign_patterns has {len(sign_patterns)} entries but there are "
                f"{len(supports)} candidate supports; they are positional."
            )
        patterns = [
            _validated_sign_pattern(pattern, len(support), index=index)
            for index, (pattern, support) in enumerate(
                zip(sign_patterns, supports, strict=True)
            )
        ]

    entries = [
        _support_entry(normalized, support, pattern)
        for support, pattern in zip(supports, patterns, strict=True)
    ]

    aggregated: list[str] = []
    for entry in entries:
        for warning in entry["warnings"]:
            if warning not in aggregated:
                aggregated.append(warning)
    if zero_columns:
        aggregated.append("design_matrix_contains_zero_columns")

    return {
        "summary_type": "pdelie_sparse_recovery_assumption_report",
        "schema_version": "0.1",
        "num_rows": int(values.shape[0]),
        "num_features": int(values.shape[1]),
        "normalization_policy": normalization_policy,
        "restricted_eigenvalue_definition": restricted_eigenvalue_definition,
        "irrepresentability_threshold": IRREPRESENTABILITY_THRESHOLD,
        "active_support_condition_limit": ACTIVE_SUPPORT_CONDITION_LIMIT,
        "candidate_support_count": len(entries),
        "sign_patterns_supplied": sign_patterns is not None,
        "zero_column_count": zero_columns,
        "supports": entries,
        "status_vocabulary": list(SPARSE_RECOVERY_STATUSES),
        "warnings": aggregated,
        "diagnostic_only": True,
    }


def empirical_support_stability_report(
    design_matrix: object,
    target: object,
    *,
    seed: int,
    n_resamples: int,
    resampling_unit: Literal["trajectory", "complementary_pair"],
    selection_method: Callable[[np.ndarray, np.ndarray], Sequence[int]],
    trajectory_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    """How often a selection method picks the same support under resampling.

    **Row-level resampling is refused.** Rows of a PDE-derived design matrix are
    adjacent samples of a continuous field; resampling them independently
    destroys exactly the correlation structure that makes the design what it is,
    and produces confidence intervals that describe a dataset nobody has. Only
    trajectory-level and complementary-pair splitting are permitted.

    This is an *empirical* report and is deliberately separate from
    :func:`sparse_recovery_assumption_report`. Selection frequency is not
    evidence that a theoretical condition holds, and the two must not be read as
    one number.
    """
    values = _validated_matrix(design_matrix)
    target_values = np.asarray(target, dtype=float).reshape(-1)
    if target_values.shape[0] != values.shape[0]:
        raise ShapeValidationError(
            f"target has {target_values.shape[0]} entries but design_matrix has "
            f"{values.shape[0]} rows."
        )
    if not np.all(np.isfinite(target_values)):
        raise ScopeValidationError("target must be finite everywhere.")
    if resampling_unit not in RESAMPLING_UNITS:
        raise ScopeValidationError(
            f"resampling_unit must be one of {list(RESAMPLING_UNITS)}; row-level "
            f"resampling would break the correlation structure of PDE-derived "
            f"design matrices and is not offered."
        )
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ScopeValidationError("seed must be an integer; stability must reproduce.")
    if isinstance(n_resamples, bool) or not isinstance(n_resamples, int):
        raise ScopeValidationError("n_resamples must be an integer.")
    if n_resamples < 1:
        raise ScopeValidationError("n_resamples must be at least 1.")
    if not callable(selection_method):
        raise ScopeValidationError("selection_method must be callable.")

    if trajectory_ids is None:
        identifiers = [str(index) for index in range(values.shape[0])]
    else:
        identifiers = [str(value) for value in trajectory_ids]
        if len(identifiers) != values.shape[0]:
            raise ShapeValidationError(
                f"trajectory_ids has {len(identifiers)} entries but design_matrix "
                f"has {values.shape[0]} rows."
            )
    groups = sorted(set(identifiers))
    if resampling_unit == "trajectory" and len(groups) < 2:
        raise ScopeValidationError(
            "trajectory resampling needs at least two distinct trajectory_ids; "
            "with one group every resample is the whole dataset."
        )

    generator = np.random.default_rng(seed)
    membership = {group: np.flatnonzero(np.asarray(identifiers) == group) for group in groups}

    feature_counts = np.zeros(values.shape[1], dtype=float)
    support_counts: dict[tuple[int, ...], int] = {}
    completed = 0
    for _ in range(n_resamples):
        if resampling_unit == "trajectory":
            drawn = generator.choice(len(groups), size=len(groups), replace=True)
            rows = np.concatenate([membership[groups[index]] for index in drawn])
        else:
            shuffled = generator.permutation(len(groups))
            half = max(1, len(groups) // 2)
            rows = np.concatenate(
                [membership[groups[index]] for index in shuffled[:half]]
            )
        if rows.size == 0:
            continue
        selected = selection_method(values[rows], target_values[rows])
        canonical: tuple[int, ...] = tuple(sorted({int(index) for index in selected}))
        for index in canonical:
            if not 0 <= index < values.shape[1]:
                raise ScopeValidationError(
                    f"selection_method returned column index {index}, outside "
                    f"[0, {values.shape[1]})."
                )
            feature_counts[index] += 1.0
        support_counts[canonical] = support_counts.get(canonical, 0) + 1
        completed += 1

    divisor = float(completed) if completed else 1.0
    return {
        "summary_type": "pdelie_empirical_support_stability_report",
        "schema_version": "0.1",
        "num_rows": int(values.shape[0]),
        "num_features": int(values.shape[1]),
        "seed": int(seed),
        "n_resamples": int(n_resamples),
        "completed_resamples": completed,
        "resampling_unit": resampling_unit,
        "group_count": len(groups),
        "selection_frequency_by_feature": {
            str(index): float(count / divisor)
            for index, count in enumerate(feature_counts)
        },
        "support_frequency": {
            ",".join(str(index) for index in support): float(count / divisor)
            for support, count in sorted(support_counts.items())
        },
        "most_frequent_support": (
            list(max(support_counts.items(), key=lambda item: item[1])[0])
            if support_counts
            else None
        ),
        "is_theoretical_assumption_report": False,
        "warnings": [] if completed == n_resamples else ["some_resamples_were_empty"],
        "diagnostic_only": True,
    }
