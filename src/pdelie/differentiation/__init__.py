"""v0.36b: differentiation-policy contracts. Submodule-only.

This package carries the *declaration* of how derivatives were taken. The
computation itself lives in :mod:`pdelie.derivatives` and is unchanged.
"""

from __future__ import annotations

from pdelie.differentiation.policy_spec import (
    DIFFERENTIATION_BACKENDS,
    DIFFERENTIATION_BOUNDARY_HANDLING,
    DifferentiationPolicySpec,
)

__all__ = [
    "DIFFERENTIATION_BACKENDS",
    "DIFFERENTIATION_BOUNDARY_HANDLING",
    "DifferentiationPolicySpec",
]
