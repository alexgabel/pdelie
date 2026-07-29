"""v0.35b: catalogue of known Lie point symmetries per supported PDE.

**Private on purpose.** The module is underscore-prefixed because the taxonomy
this catalogue encodes has no public write-up to cite. Publishing an API that
asserts "these are the point symmetries of this PDE" without a citable source
would make PDELie the reference for a claim it cannot support. Un-privatising is
a one-line change once a write-up exists; retracting a public API is not.

What this is, and what it is not
================================

This is **catalogue data**: analytically known generators, recorded so a fitted
generator can be compared against ground truth. It is deliberately *not*
registered through :mod:`pdelie.symmetry.registry`. That registry's
:class:`~pdelie.symmetry.registry.SymmetryMethod` contract requires
``fit(field, ...)`` -- an algorithm that *discovers* a generator from data. A
catalogued symmetry discovers nothing; wiring it in would mean writing a ``fit``
that ignores its input and returns a constant, and would make
``list_symmetry_methods()`` report methods that never read the data they are
handed.

The classification, and the wedge it exists to express
=====================================================

Each entry carries a classification in :data:`POINT_SYMMETRY_CLASSIFICATIONS`:

``exact_and_useful``
    The symmetry holds on the data *and* the design it implies supports
    coefficient recovery.
``valid_but_not_useful``
    The symmetry holds and the design does not support recovery. This is the
    wedge documented in ``docs/strategy/data/valid_but_not_useful_example.json``:
    passing validation is not the same as being worth acting on.
``invalid``
    The symmetry does not hold on this data.

The two axes come from different places, and that separation is the point.
**Validity is a property of the symmetry** and is supplied by the caller from the
existing verification machinery. **Usefulness is a property of the design** and
comes from :func:`pdelie.diagnostics.irrepresentability_constant`.

This was measured before it was frozen. An earlier composition keyed the whole
classification on the irrepresentability constant, which put all three supported
PDEs in the same bucket -- because that constant is a property of the design
matrix and support and never consults the symmetry at all. Sweeping every
two-element support of the canonical heat design, only one of ten reached
``exact_and_useful`` (rho_IR 0.963 against a threshold of 1.0). A classification
whose verdict does not depend on the thing being classified is not a
classification, so validity is a required input rather than something inferred.

Expect the wedge to be wide. At the canonical weak-form configuration every
supported PDE reports ``rho_IR`` above 1.0 -- heat 2.743, Burgers 2.194,
advection-diffusion 1.178 -- so a symmetry that validates there is
``valid_but_not_useful``. That is a finding about the design, not a defect in the
catalogue.

Sources
=======

The generators are the classical Lie point symmetries of the scalar 1-D
equations, in the ``(tau, xi, phi)`` component convention of
:class:`~pdelie.symmetry.formula.FormulaGeneratorFamily`, where the generator is
``X = tau d/dt + xi d/dx + phi d/du``. They are recorded at the canonical
parameter values the PDELie generators produce (heat and Burgers at unit
diffusivity); a catalogue entry is a statement about the canonical equation, not
about an arbitrary parameterization, and :data:`CANONICAL_PARAMETERS` records
which.
"""

from __future__ import annotations

from typing import Any

from pdelie.errors import ScopeValidationError
from pdelie.symmetry.formula import FormulaGeneratorFamily

__all__ = [
    "CANONICAL_PARAMETERS",
    "CATALOGUED_PDE_NAMES",
    "POINT_SYMMETRY_CLASSIFICATIONS",
    "classify_point_symmetry",
    "list_point_symmetries",
    "point_symmetry_family",
    "summarize_point_symmetry_catalogue",
]

#: Frozen classification vocabulary.
POINT_SYMMETRY_CLASSIFICATIONS: frozenset[str] = frozenset(
    {"exact_and_useful", "valid_but_not_useful", "invalid"}
)

#: Threshold on the irrepresentability constant separating a design that
#: supports recovery from one that does not. Not tunable here: it is the
#: threshold the constant is defined against (Zhao & Yu 2006), carried through
#: from :mod:`pdelie.diagnostics`.
_RECOVERY_THRESHOLD = 1.0


def _const(value: float) -> dict[str, Any]:
    return {"node": "const", "value": float(value)}


def _var(name: str) -> dict[str, Any]:
    return {"node": "var", "name": name}


def _mul(*factors: dict[str, Any]) -> dict[str, Any]:
    return {"node": "mul", "factors": list(factors)}


def _add(*terms: dict[str, Any]) -> dict[str, Any]:
    return {"node": "add", "terms": list(terms)}


def _pow(base: dict[str, Any], exponent: int) -> dict[str, Any]:
    return {"node": "pow", "base": base, "exponent": int(exponent)}


_ZERO = _const(0.0)
_ONE = _const(1.0)

#: The parameter values each catalogue is stated at. A catalogue entry describes
#: the canonical equation; at other parameter values the generators differ.
CANONICAL_PARAMETERS: dict[str, dict[str, float]] = {
    "heat_1d": {"nu": 1.0},
    "burgers_1d": {"nu": 1.0},
    "advection_diffusion_1d": {"nu": 1.0, "c": 1.0},
}

# u_t = u_xx -- the six-dimensional classical algebra.
_HEAT_1D: tuple[tuple[str, dict[str, Any], dict[str, Any], dict[str, Any], str], ...] = (
    ("time_translation", _ONE, _ZERO, _ZERO, "t -> t + eps"),
    ("space_translation", _ZERO, _ONE, _ZERO, "x -> x + eps"),
    ("amplitude_scaling", _ZERO, _ZERO, _var("u"), "u -> u * exp(eps)"),
    (
        "dilation",
        _mul(_const(2.0), _var("t")),
        _var("x"),
        _ZERO,
        "(t, x) -> (t * exp(2 eps), x * exp(eps))",
    ),
    (
        "galilean_boost",
        _ZERO,
        _mul(_const(2.0), _var("t")),
        _mul(_const(-1.0), _var("x"), _var("u")),
        "x -> x + 2 eps t, with the compensating amplitude factor",
    ),
    (
        "projective",
        _mul(_const(4.0), _pow(_var("t"), 2)),
        _mul(_const(4.0), _var("t"), _var("x")),
        _mul(
            _const(-1.0),
            _add(_pow(_var("x"), 2), _mul(_const(2.0), _var("t"))),
            _var("u"),
        ),
        "the projective (conformal) symmetry of the heat equation",
    ),
)

# u_t + u u_x = u_xx.
_BURGERS_1D: tuple[
    tuple[str, dict[str, Any], dict[str, Any], dict[str, Any], str], ...
] = (
    ("time_translation", _ONE, _ZERO, _ZERO, "t -> t + eps"),
    ("space_translation", _ZERO, _ONE, _ZERO, "x -> x + eps"),
    (
        "galilean_boost",
        _ZERO,
        _var("t"),
        _ONE,
        "x -> x + eps t, u -> u + eps",
    ),
    (
        "dilation",
        _mul(_const(2.0), _var("t")),
        _var("x"),
        _mul(_const(-1.0), _var("u")),
        "(t, x, u) -> (t e^{2 eps}, x e^{eps}, u e^{-eps})",
    ),
)

# u_t + c u_x = nu u_xx.
_ADVECTION_DIFFUSION_1D: tuple[
    tuple[str, dict[str, Any], dict[str, Any], dict[str, Any], str], ...
] = (
    ("time_translation", _ONE, _ZERO, _ZERO, "t -> t + eps"),
    ("space_translation", _ZERO, _ONE, _ZERO, "x -> x + eps"),
    ("amplitude_scaling", _ZERO, _ZERO, _var("u"), "u -> u * exp(eps)"),
)

_CATALOGUE: dict[
    str, tuple[tuple[str, dict[str, Any], dict[str, Any], dict[str, Any], str], ...]
] = {
    "heat_1d": _HEAT_1D,
    "burgers_1d": _BURGERS_1D,
    "advection_diffusion_1d": _ADVECTION_DIFFUSION_1D,
}

#: PDEs with a catalogue. Ordered for stable reporting.
CATALOGUED_PDE_NAMES: tuple[str, ...] = tuple(_CATALOGUE)


def _validated_pde_name(pde_name: object) -> str:
    if not isinstance(pde_name, str) or not pde_name.strip():
        raise ScopeValidationError("pde_name must be a non-empty string.")
    if pde_name not in _CATALOGUE:
        raise ScopeValidationError(
            f"no point-symmetry catalogue for {pde_name!r}; catalogued PDEs are "
            f"{list(CATALOGUED_PDE_NAMES)}."
        )
    return pde_name


def list_point_symmetries(pde_name: object) -> list[dict[str, Any]]:
    """Catalogue entries for ``pde_name`` as strict-JSON records."""
    name = _validated_pde_name(pde_name)
    return [
        {
            "pde_name": name,
            "symmetry_name": symmetry_name,
            "components": {"tau": tau, "xi": xi, "phi": phi},
            "action": action,
            "canonical_parameters": dict(CANONICAL_PARAMETERS[name]),
            "source": "classical_lie_point_symmetry",
        }
        for symmetry_name, tau, xi, phi, action in _CATALOGUE[name]
    ]


def point_symmetry_family(pde_name: object) -> FormulaGeneratorFamily:
    """The catalogue for ``pde_name`` as a :class:`FormulaGeneratorFamily`."""
    name = _validated_pde_name(pde_name)
    return FormulaGeneratorFamily(
        formula_generators=[
            {
                "name": entry["symmetry_name"],
                "components": entry["components"],
                "metadata": {
                    "pde_name": entry["pde_name"],
                    "action": entry["action"],
                    "source": entry["source"],
                },
            }
            for entry in list_point_symmetries(name)
        ]
    )


def classify_point_symmetry(
    *,
    pde_name: object,
    symmetry_name: object,
    symmetry_is_valid: object,
    irrepresentability_constant: object,
) -> dict[str, Any]:
    """Classify a catalogued symmetry on a particular design.

    ``symmetry_is_valid`` is **required** and comes from the caller's
    verification of the symmetry against the data -- it is not inferred here.
    Measurement showed why: the irrepresentability constant is a property of the
    design matrix and support and never consults the symmetry, so a
    classification derived from it alone returns the same verdict for every
    symmetry of every PDE.

    ``irrepresentability_constant`` is
    :func:`pdelie.diagnostics.irrepresentability_constant`'s ``metric_value``.
    ``None`` is accepted -- that function returns it for an undefined case --
    and yields an inconclusive usefulness axis rather than a guess.
    """
    name = _validated_pde_name(pde_name)
    if not isinstance(symmetry_name, str) or not symmetry_name.strip():
        raise ScopeValidationError("symmetry_name must be a non-empty string.")
    known = {entry["symmetry_name"] for entry in list_point_symmetries(name)}
    if symmetry_name not in known:
        raise ScopeValidationError(
            f"{symmetry_name!r} is not catalogued for {name!r}; known symmetries "
            f"are {sorted(known)}."
        )
    if not isinstance(symmetry_is_valid, bool):
        raise ScopeValidationError(
            "symmetry_is_valid must be a bool supplied by the caller's "
            "verification; it is deliberately not inferred from the design."
        )

    constant: float | None
    if irrepresentability_constant is None:
        constant = None
    elif isinstance(irrepresentability_constant, bool) or not isinstance(
        irrepresentability_constant, (int, float)
    ):
        raise ScopeValidationError(
            "irrepresentability_constant must be a real number or None."
        )
    else:
        constant = float(irrepresentability_constant)

    warnings_out: list[str] = []
    if not symmetry_is_valid:
        classification = "invalid"
        recovery_supported: bool | None = None
    elif constant is None:
        classification = "valid_but_not_useful"
        recovery_supported = None
        warnings_out.append("usefulness_axis_inconclusive_irrepresentability_undefined")
    else:
        recovery_supported = bool(constant < _RECOVERY_THRESHOLD)
        classification = (
            "exact_and_useful" if recovery_supported else "valid_but_not_useful"
        )

    if classification == "valid_but_not_useful" and recovery_supported is False:
        warnings_out.append("design_does_not_support_recovery")

    return {
        "summary_type": "pdelie_point_symmetry_classification",
        "pde_name": name,
        "symmetry_name": symmetry_name,
        "classification": classification,
        "symmetry_is_valid": bool(symmetry_is_valid),
        "irrepresentability_constant": constant,
        "recovery_threshold": _RECOVERY_THRESHOLD,
        "design_supports_recovery": recovery_supported,
        "classification_vocabulary": sorted(POINT_SYMMETRY_CLASSIFICATIONS),
        "warnings": warnings_out,
        "diagnostic_only": True,
    }


def summarize_point_symmetry_catalogue() -> dict[str, Any]:
    """The whole catalogue as one strict-JSON report."""
    entries = {name: list_point_symmetries(name) for name in CATALOGUED_PDE_NAMES}
    return {
        "summary_type": "pdelie_point_symmetry_catalogue",
        "catalogued_pde_names": list(CATALOGUED_PDE_NAMES),
        "entry_counts": {name: len(values) for name, values in entries.items()},
        "total_entry_count": sum(len(values) for values in entries.values()),
        "entries": entries,
        "canonical_parameters": {
            name: dict(values) for name, values in CANONICAL_PARAMETERS.items()
        },
        "classification_vocabulary": sorted(POINT_SYMMETRY_CLASSIFICATIONS),
        "is_registered_as_symmetry_method": False,
        "registration_rationale": (
            "SymmetryMethod requires fit(field, ...), which discovers a generator "
            "from data. Catalogued symmetries are analytically known and discover "
            "nothing, so they are carried as data rather than as registered "
            "methods."
        ),
        "diagnostic_only": True,
    }
