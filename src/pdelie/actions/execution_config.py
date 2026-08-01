"""v0.37a: where a seed lives, and why not on the action.

Constraint C-1 in ``docs/planning/V0_37_BINDING_DESIGN_CONSTRAINTS.md`` requires
three layers, not one:

===========================  =================================================
Layer                        Holds
===========================  =================================================
action specification         the pure mathematical/declarative action
**execution config**         backend, tolerances, optional stochastic settings
run manifest                 the realised seed and RNG provenance
===========================  =================================================

This module is the middle layer.

Why the seed is not on the bundle
=================================

``u(t,x) -> u(t, x - tau)`` has no random seed. Every action family v0.37 declares --
``shift``, ``scalar_rescale``, ``identity`` -- is deterministic, and no RNG is
consulted anywhere in their execution. Putting a required seed on
:class:`~pdelie.actions.action_bundle.ProblemActionBundle` would:

* make deterministic actions read as stochastic;
* give two bundles that are identical in every mathematical respect different
  ``semantic_hash`` values, purely because a number nobody used differed;
* and therefore break caching and equality on a distinction with no meaning.

An early v0.37 draft did exactly that. It was caught by
``tests/test_v0_37_binding_constraints.py``, which asserts ``pdelie.actions``
carries no seed outside this module.

The hard cut is preserved, not weakened
=======================================

``seed`` is a **required** field here -- there is no ``_UNSET`` sentinel and no
default, so omitting it is a ``TypeError`` from the dataclass. What changed is
*where* the requirement lives, not whether it exists. ``seed=None`` remains
expressible and means "no RNG is involved", which is the honest declaration for
every v0.37 action family and must be stated rather than assumed.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from pdelie.artifact.semantic_hash import semantic_hash
from pdelie.errors import ScopeValidationError

__all__ = ["INTERPOLATION_BACKENDS", "ActionExecutionConfig"]

#: How a coefficient field is resampled when an action moves it off-grid.
INTERPOLATION_BACKENDS: tuple[str, ...] = ("exact_grid_shift", "fourier", "linear")


@dataclass(frozen=True)
class ActionExecutionConfig:
    """How to execute an action bundle. Never what the action *is*."""

    interpolation_backend: str
    numerical_tolerances: Mapping[str, float]
    seed: int | None
    deterministic_expected: bool
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.interpolation_backend not in INTERPOLATION_BACKENDS:
            raise ScopeValidationError(
                f"interpolation_backend {self.interpolation_backend!r} is not one of "
                f"{list(INTERPOLATION_BACKENDS)}."
            )
        if not isinstance(self.numerical_tolerances, Mapping):
            raise ScopeValidationError("numerical_tolerances must be a mapping.")
        tolerances: dict[str, float] = {}
        for key, value in self.numerical_tolerances.items():
            if not isinstance(key, str):
                raise ScopeValidationError("numerical_tolerances keys must be strings.")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ScopeValidationError(f"numerical_tolerances[{key!r}] must be a number.")
            if not math.isfinite(float(value)) or float(value) < 0.0:
                raise ScopeValidationError(
                    f"numerical_tolerances[{key!r}] must be finite and non-negative."
                )
            tolerances[key] = float(value)
        object.__setattr__(self, "numerical_tolerances", tolerances)

        if self.seed is not None and (
            isinstance(self.seed, bool) or not isinstance(self.seed, int)
        ):
            raise ScopeValidationError(
                "seed must be an int or None. None is a declaration -- it says no "
                "RNG is involved -- and is not the same as omitting the field, "
                "which is a TypeError."
            )
        if not isinstance(self.deterministic_expected, bool):
            raise ScopeValidationError("deterministic_expected must be a bool.")
        if self.deterministic_expected and self.seed is not None:
            raise ScopeValidationError(
                "deterministic_expected=True with a non-None seed is contradictory: "
                "a run that consults no RNG has no seed to record. Use seed=None."
            )
        if not self.deterministic_expected and self.seed is None:
            raise ScopeValidationError(
                "a nondeterministic run needs a seed, or it cannot be reproduced."
            )
        if not isinstance(self.metadata, Mapping):
            raise ScopeValidationError("metadata must be a mapping.")
        object.__setattr__(self, "metadata", dict(self.metadata))
        semantic_hash(self.as_dict())

    def identity(self) -> str:
        return semantic_hash(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "interpolation_backend": self.interpolation_backend,
            "numerical_tolerances": dict(self.numerical_tolerances),
            "seed": self.seed,
            "deterministic_expected": self.deterministic_expected,
            "metadata": dict(self.metadata),
        }
