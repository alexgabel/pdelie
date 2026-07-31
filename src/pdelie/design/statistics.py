"""v0.36c: paired statistics over per-seed design metrics.

One function, with one refusal built into it.

Why row resampling is not offered
=================================

A bootstrap assumes the resampling unit is exchangeable. Rows of a PDE-derived
design matrix are not: they are adjacent samples of a continuous field, and
neighbouring rows carry nearly the same information. Resampling them
independently manufactures effective sample size that the data does not have,
and produces intervals that are too narrow by a factor nobody can state.

So the unit is ``seed`` or ``trajectory``, and ``row`` raises. The same refusal
appears in :mod:`pdelie.diagnostics.sparse_recovery` for the same reason; they
are separate functions because they resample different things, but the argument
is identical.

Pairing
=======

The interval is over the *paired* difference, not over two independent samples.
Two designs evaluated on the same seeds share whatever that seed did to the
problem, and pairing removes it. That only works if the seeds line up, so the
caller supplies one ``seed_ids`` sequence and both metric sequences are indexed
against it.

Failed runs are ``None``, never dropped silently. A pair is usable only when
both sides produced a value, and the count of unusable pairs is reported.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, Literal

import numpy as np

from pdelie.errors import ScopeValidationError, ShapeValidationError

__all__ = ["RESAMPLING_UNITS", "paired_bootstrap_interval"]

#: Units over which resampling is statistically defensible here.
RESAMPLING_UNITS: tuple[str, ...] = ("seed", "trajectory")


def _validated_metrics(values: object, *, name: str, length: int) -> list[float | None]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ScopeValidationError(f"{name} must be a sequence.")
    if len(values) != length:
        raise ShapeValidationError(
            f"{name} has {len(values)} entries but seed_ids has {length}; metrics "
            f"are positional against seed_ids so the pairing is unambiguous."
        )
    cleaned: list[float | None] = []
    for index, value in enumerate(values):
        if value is None:
            cleaned.append(None)
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ScopeValidationError(
                f"{name}[{index}] must be a real number or None; got "
                f"{type(value).__name__}."
            )
        if not math.isfinite(float(value)):
            raise ScopeValidationError(
                f"{name}[{index}] is not finite. A failed run is None, not NaN -- "
                f"NaN would propagate silently through the interval."
            )
        cleaned.append(float(value))
    return cleaned


def paired_bootstrap_interval(
    per_seed_a: object,
    per_seed_b: object,
    *,
    seed_ids: Sequence[str],
    n_resamples: int,
    interval_level: float,
    resampling_unit: Literal["seed", "trajectory"],
    seed: int,
) -> dict[str, Any]:
    """Bootstrap interval for the paired difference ``a - b``.

    Deterministic under a fixed ``seed``: the same inputs reproduce the interval
    exactly, which a test asserts.
    """
    if resampling_unit not in RESAMPLING_UNITS:
        raise ScopeValidationError(
            f"resampling_unit must be one of {list(RESAMPLING_UNITS)}. Row-level "
            f"resampling is not offered: rows of a PDE-derived design matrix are "
            f"adjacent samples of a continuous field, and resampling them "
            f"independently manufactures effective sample size the data lacks."
        )
    if isinstance(seed_ids, (str, bytes)) or not isinstance(seed_ids, Sequence):
        raise ScopeValidationError("seed_ids must be a sequence of identifiers.")
    identifiers = [str(value) for value in seed_ids]
    if not identifiers:
        raise ScopeValidationError("seed_ids must be non-empty.")
    if len(set(identifiers)) != len(identifiers):
        raise ScopeValidationError("seed_ids must not repeat.")
    if isinstance(n_resamples, bool) or not isinstance(n_resamples, int):
        raise ScopeValidationError("n_resamples must be an integer.")
    if n_resamples < 1:
        raise ScopeValidationError("n_resamples must be at least 1.")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ScopeValidationError("seed must be an integer; the interval must reproduce.")
    if (
        isinstance(interval_level, bool)
        or not isinstance(interval_level, (int, float))
        or not 0.0 < float(interval_level) < 1.0
    ):
        raise ScopeValidationError("interval_level must lie strictly between 0 and 1.")

    values_a = _validated_metrics(per_seed_a, name="per_seed_a", length=len(identifiers))
    values_b = _validated_metrics(per_seed_b, name="per_seed_b", length=len(identifiers))

    usable: list[int] = []
    paired_differences: list[float] = []
    for index in range(len(identifiers)):
        left, right = values_a[index], values_b[index]
        if left is None or right is None:
            continue
        usable.append(index)
        paired_differences.append(left - right)
    failed = len(identifiers) - len(usable)

    if not usable:
        return {
            "interval_available": False,
            "reason": "no seed produced a value on both designs",
            "paired_count": 0,
            "failed_pair_count": failed,
            "seed_ids_a": identifiers,
            "seed_ids_b": identifiers,
            "resampling_unit": resampling_unit,
            "n_resamples": int(n_resamples),
            "interval_level": float(interval_level),
            "seed": int(seed),
            "mean_difference": None,
            "lower": None,
            "upper": None,
        }

    differences = np.array(paired_differences, dtype=float)
    generator = np.random.default_rng(seed)
    draws = generator.integers(0, differences.size, size=(int(n_resamples), differences.size))
    means = differences[draws].mean(axis=1)

    tail = (1.0 - float(interval_level)) / 2.0
    lower = float(np.quantile(means, tail))
    upper = float(np.quantile(means, 1.0 - tail))

    return {
        "interval_available": True,
        "reason": None,
        "paired_count": len(usable),
        "failed_pair_count": failed,
        # Reported identically on both sides: the pairing is what makes this a
        # paired interval, and an exit gate asserts they match.
        "seed_ids_a": identifiers,
        "seed_ids_b": identifiers,
        "paired_seed_ids": [identifiers[index] for index in usable],
        "resampling_unit": resampling_unit,
        "n_resamples": int(n_resamples),
        "interval_level": float(interval_level),
        "seed": int(seed),
        "mean_difference": float(differences.mean()),
        "lower": lower,
        "upper": upper,
        "excludes_zero": bool(lower > 0.0 or upper < 0.0),
        "diagnostic_only": True,
    }
