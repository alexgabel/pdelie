"""v0.33d: shared validation and provenance for variable-coefficient generator profiles.

The v0.33d generators accept a coefficient profile in three forms -- ``None``
(constant), a sampled ``np.ndarray``, or a ``Callable`` invoked on the spatial
grid. This module resolves all three to a single representation and records
deterministic provenance in ``FieldBatch.metadata["parameter_tags"]``.

Two properties matter to callers:

* **The constant path is byte-preserved.** ``resolve_coefficient_profile``
  returns ``None`` for the array when the caller passed ``None``, so generators
  keep their existing constant-coefficient numerical code path literally
  unchanged rather than routing a constant array through a variable-coefficient
  scheme. Those are not bit-identical -- ``diffusivity * u_xx`` and
  ``d/dx(nu(x) du/dx)`` differ in operation order even when ``nu`` is constant.
* **The read path is uniform.** ``<prefix>_min``, ``<prefix>_max``, and
  ``<prefix>_l2_norm`` are populated for all three kinds, so downstream
  diagnostics never need to branch on the profile kind to read a magnitude.

All validation fires before any numerical work: shape mismatch raises
``ShapeValidationError``; non-finite, out-of-range, and malformed-callable
inputs raise ``ScopeValidationError``.
"""

from __future__ import annotations

import hashlib
import inspect
from collections.abc import Callable
from typing import Any

import numpy as np

from pdelie.errors import ScopeValidationError, ShapeValidationError

#: Accepted profile forms. ``None`` selects the constant-coefficient path.
CoefficientProfile = "np.ndarray | Callable[[np.ndarray], np.ndarray] | None"

PROFILE_KIND_CONSTANT = "constant"
PROFILE_KIND_ARRAY = "array"
PROFILE_KIND_CALLABLE = "callable"

ALLOWED_PROFILE_KINDS = frozenset(
    {PROFILE_KIND_CONSTANT, PROFILE_KIND_ARRAY, PROFILE_KIND_CALLABLE}
)

#: Equation form for the diffusive term. Recorded as ``parameter_tags["nu_form"]``
#: so the v0.34a variable-coefficient residual evaluators can dispatch on it
#: rather than guess which operator produced the data. The two forms coincide
#: analytically for constant ``nu`` and differ for any ``nu(x)``.
DIFFUSIVITY_FORM_CONSERVATIVE = "conservative_divergence"
DIFFUSIVITY_FORM_NONCONSERVATIVE = "nonconservative_nu_uxx"
ALLOWED_DIFFUSIVITY_FORMS = frozenset(
    {DIFFUSIVITY_FORM_CONSERVATIVE, DIFFUSIVITY_FORM_NONCONSERVATIVE}
)

#: Equation form for the advective term. Recorded as ``parameter_tags["c_form"]``.
ADVECTION_FORM_CONSERVATIVE = "conservative_divergence"
ADVECTION_FORM_NONCONSERVATIVE = "nonconservative_c_ux"
ALLOWED_ADVECTION_FORMS = frozenset(
    {ADVECTION_FORM_CONSERVATIVE, ADVECTION_FORM_NONCONSERVATIVE}
)

#: How the coefficient field is treated under a symmetry transformation.
#: v0.33d ships a single value: the coefficient is a fixed background that does
#: NOT co-transform. v0.34b extends the vocabulary with
#: ``"co_transforming_equivalence_target"`` for the symmetry-breaking-versus-
#: equivalence benchmark, which is why the tag is emitted now rather than
#: retrofitted later.
NU_TREATMENT_POLICY_FIXED_BACKGROUND = "fixed_background"
ALLOWED_NU_TREATMENT_POLICIES = frozenset({NU_TREATMENT_POLICY_FIXED_BACKGROUND})


def validate_equation_form(value: object, *, allowed: frozenset[str], name: str) -> str:
    """Validate an equation-form selector against its frozen vocabulary."""
    if not isinstance(value, str) or value not in allowed:
        raise ScopeValidationError(
            f"{name} must be one of {sorted(allowed)}; got {value!r}."
        )
    return value


def _hash_profile_values(values: np.ndarray) -> str:
    """SHA-256 of the profile values, pinned to little-endian float64.

    The explicit dtype makes the hash reproducible across platforms; the raw
    ``tobytes()`` of a native-endian array would not be.
    """
    return hashlib.sha256(np.asarray(values, dtype="<f8").tobytes()).hexdigest()


def _describe_callable(profile: Callable[..., Any]) -> str:
    """Best-effort stable description of a callable profile.

    ``repr`` of a function embeds its memory address, which changes between
    runs and is therefore useless as provenance. Source text is preferred where
    retrievable (the common case for module-level ``def`` and for lambdas), and
    ``repr`` is the documented fallback for builtins, C functions, and callables
    defined in a REPL where no source is available.
    """
    try:
        return inspect.getsource(profile).strip()
    except (OSError, TypeError):
        return repr(profile)


def _validate_sampled_values(
    values: np.ndarray,
    *,
    name: str,
    expected_size: int,
    require_positive: bool,
    source: str,
) -> np.ndarray:
    values = np.asarray(values, dtype=float)

    if values.ndim != 1 or values.size != expected_size:
        raise ShapeValidationError(
            f"{name} must be one-dimensional with one value per spatial grid point "
            f"({expected_size},); {source} produced shape {values.shape}."
        )
    if not np.all(np.isfinite(values)):
        raise ScopeValidationError(
            f"{name} must be finite everywhere; {source} produced non-finite values."
        )
    if require_positive and not np.all(values > 0.0):
        raise ScopeValidationError(
            f"{name} must be strictly positive everywhere; {source} produced a "
            f"minimum of {float(np.min(values))!r}."
        )
    return values


def _magnitude_tags(values: np.ndarray, *, prefix: str) -> dict[str, Any]:
    return {
        f"{prefix}_min": float(np.min(values)),
        f"{prefix}_max": float(np.max(values)),
        f"{prefix}_l2_norm": float(np.linalg.norm(values)),
    }


def resolve_coefficient_profile(
    profile: np.ndarray | Callable[[np.ndarray], np.ndarray] | None,
    *,
    x: np.ndarray,
    constant_value: float,
    prefix: str,
    name: str,
    require_positive: bool = True,
) -> tuple[np.ndarray | None, dict[str, Any]]:
    """Resolve a coefficient profile and build its provenance tags.

    Returns ``(sampled_values, tags)``. ``sampled_values`` is ``None`` for the
    constant path, signalling the caller to keep its existing byte-preserved
    numerical branch; it is a validated ``(num_points,)`` array otherwise.

    ``prefix`` names the coefficient in the emitted tags (``"nu"`` for
    diffusivity, ``"c"`` for advection speed); ``name`` is the caller-facing
    parameter name used in error messages.

    ``require_positive`` is ``True`` for diffusivities, which must be strictly
    positive for the scheme to be well-posed, and ``False`` for signed
    coefficients such as advection speed.
    """
    x = np.asarray(x, dtype=float)
    expected_size = int(x.size)

    if profile is None:
        constant_array = np.full(expected_size, float(constant_value), dtype=float)
        tags: dict[str, Any] = {f"{prefix}_profile_kind": PROFILE_KIND_CONSTANT}
        tags.update(_magnitude_tags(constant_array, prefix=prefix))
        return None, tags

    if callable(profile):
        try:
            sampled = profile(x)
        except TypeError as exc:
            raise ScopeValidationError(
                f"{name} callable must accept the spatial grid as a single positional "
                f"argument, i.e. {name}(x) -> array of shape ({expected_size},). "
                f"Calling it raised: {exc}"
            ) from exc
        values = _validate_sampled_values(
            sampled,
            name=name,
            expected_size=expected_size,
            require_positive=require_positive,
            source="the callable",
        )
        tags = {
            f"{prefix}_profile_kind": PROFILE_KIND_CALLABLE,
            f"{prefix}_profile_callable_repr": _describe_callable(profile),
        }
        tags.update(_magnitude_tags(values, prefix=prefix))
        return values, tags

    values = _validate_sampled_values(
        profile,
        name=name,
        expected_size=expected_size,
        require_positive=require_positive,
        source="the array",
    )
    tags = {
        f"{prefix}_profile_kind": PROFILE_KIND_ARRAY,
        f"{prefix}_profile_shape": [int(values.size)],
        f"{prefix}_profile_hash": _hash_profile_values(values),
    }
    tags.update(_magnitude_tags(values, prefix=prefix))
    return values, tags


__all__ = [
    "ADVECTION_FORM_CONSERVATIVE",
    "ADVECTION_FORM_NONCONSERVATIVE",
    "ALLOWED_ADVECTION_FORMS",
    "ALLOWED_DIFFUSIVITY_FORMS",
    "ALLOWED_NU_TREATMENT_POLICIES",
    "ALLOWED_PROFILE_KINDS",
    "DIFFUSIVITY_FORM_CONSERVATIVE",
    "DIFFUSIVITY_FORM_NONCONSERVATIVE",
    "NU_TREATMENT_POLICY_FIXED_BACKGROUND",
    "PROFILE_KIND_ARRAY",
    "PROFILE_KIND_CALLABLE",
    "PROFILE_KIND_CONSTANT",
    "resolve_coefficient_profile",
    "validate_equation_form",
]
