"""v0.37a: what a problem *is*, and what a coefficient field is *allowed* to do.

Contracts only. Nothing here executes an action; :mod:`pdelie.actions.execute`
arrives at v0.37b.

The layer this module occupies
==============================

Three shipped vocabularies describe the background-coefficient question at three
different layers, introduced three releases apart. This module owns the first:

============================  =============================================  ========
Layer                         Asks                                           Since
============================  =============================================  ========
**Declared capability**       What may this background do?                   v0.33d
Claimed action                What does this transformation say it did?      v0.36b
Measured outcome              What happened when the residual was computed?  v0.34b
============================  =============================================  ========

:class:`CoefficientFieldRef` is the declared-capability layer, generalised from
the ``nu_treatment_policy`` tag the v0.33d generators already emit. It is
deliberately not a new vocabulary: ``fixed_background`` is carried over
unchanged, and ``co_transformable_background`` extends it. The generators say
``nu_treatment_policy: "fixed_background"`` today, and a per-field reference must
mean the same thing by the same name.

Why ``co_transformable_``, not ``co_transforming_``
====================================================

The reference declares what a field *may* do. Whether it actually co-transformed
on a given run is the v0.34b classification
``co_transforming_background_equivalence``, which is frozen into two released
support matrices and stays as it is. The ``-ing`` form describes something
observed to happen; the ``-able`` form describes a capability. Merging them
would put a measured outcome on a declarative spec, which is the collapse
``docs/planning/V0_37_BINDING_DESIGN_CONSTRAINTS.md`` C-4 forbids.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pdelie.artifact.refs import ArtifactRef
from pdelie.artifact.semantic_hash import semantic_hash
from pdelie.errors import ScopeValidationError

__all__ = [
    "COEFFICIENT_TREATMENTS",
    "COORDINATE_FIELD_ACTION_FAMILIES",
    "DOMAIN_TYPES",
    "EQUATION_FAMILIES",
    "EQUATION_FORMS",
    "CoefficientFieldRef",
    "CoordinateFieldAction",
    "ProblemInstanceSpec",
]

#: PDEs v0.37 declares actions for. Narrower than the residual layer on purpose:
#: ``kdv_1d`` and ``reaction_diffusion_1d`` have residual evaluators but no
#: v0.37 action semantics, and listing them here would imply otherwise.
EQUATION_FAMILIES: tuple[str, ...] = ("heat_1d", "burgers_1d", "advection_diffusion_1d")

#: Which form the equation is written in. v0.34a dispatches on this.
EQUATION_FORMS: tuple[str, ...] = ("conservative", "nonconservative")

#: Declared capability of a background coefficient field.
#:
#: ``fixed_background`` is carried over verbatim from the v0.33d
#: ``nu_treatment_policy`` generator tag rather than renamed.
COEFFICIENT_TREATMENTS: tuple[str, ...] = (
    "fixed_background",
    "co_transformable_background",
    "unknown",
)

#: How a coefficient field may be acted on. Growth happens by adding a family,
#: not by widening an existing family's parameter mapping.
COORDINATE_FIELD_ACTION_FAMILIES: tuple[str, ...] = ("shift", "scalar_rescale", "identity")

#: Domain shapes v0.37 declares actions for.
DOMAIN_TYPES: tuple[str, ...] = ("periodic_uniform", "nonperiodic_uniform")

#: Parameters each coordinate-field action family declares. Empty tuple means the
#: family takes none, which is a shape rather than an omission.
_ACTION_FAMILY_PARAMETERS: dict[str, tuple[str, ...]] = {
    "identity": (),
    "shift": ("offset",),
    "scalar_rescale": ("factor",),
}


def _require_json_scalar(value: object, *, where: str) -> None:
    """Reject anything that would not survive a strict-JSON round trip."""
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ScopeValidationError(
                f"{where} is {value!r}; a missing value is None, never NaN or Inf."
            )
        return
    if isinstance(value, str):
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ScopeValidationError(f"{where} has a non-string key {key!r}.")
            _require_json_scalar(item, where=f"{where}[{key!r}]")
        return
    if isinstance(value, Sequence):
        for index, item in enumerate(value):
            _require_json_scalar(item, where=f"{where}[{index}]")
        return
    raise ScopeValidationError(
        f"{where} is {type(value).__name__}, which is not strict-JSON representable."
    )


@dataclass(frozen=True)
class CoordinateFieldAction:
    """One action on a coordinate-dependent field.

    Growth is by *family*, not by widening ``parameters``. A new kind of action
    is a new family with its own declared parameter names; it is never an extra
    key smuggled into an existing family's mapping, because then the mapping
    stops being checkable.
    """

    family: str
    parameters: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.family not in COORDINATE_FIELD_ACTION_FAMILIES:
            raise ScopeValidationError(
                f"family {self.family!r} is not one of "
                f"{list(COORDINATE_FIELD_ACTION_FAMILIES)}."
            )
        if not isinstance(self.parameters, Mapping):
            raise ScopeValidationError("parameters must be a mapping.")
        parameters = dict(self.parameters)

        expected = set(_ACTION_FAMILY_PARAMETERS[self.family])
        # `closed_form` is permitted on any family: it declares an analytical
        # field that has no stored values artifact. See rule R-A11.
        supplied = set(parameters) - {"closed_form"}
        if supplied != expected:
            raise ScopeValidationError(
                f"family {self.family!r} declares parameters {sorted(expected)}; "
                f"got {sorted(supplied)}. A family's parameter set is closed -- "
                f"a new kind of action is a new family, not an extra key."
            )
        _require_json_scalar(parameters, where="CoordinateFieldAction.parameters")
        object.__setattr__(self, "parameters", parameters)

    @property
    def is_identity(self) -> bool:
        return self.family == "identity"

    def as_dict(self) -> dict[str, Any]:
        return {"family": self.family, "parameters": dict(self.parameters)}


@dataclass(frozen=True)
class CoefficientFieldRef:
    """A reference to a coefficient field, and what it is *allowed* to do.

    It deliberately holds no action. The action applied to a field on a given
    run lives on :class:`~pdelie.actions.action_bundle.ProblemActionBundle`,
    which is the sole authority for it. Holding an action here as well would
    permit the two to disagree with no rule to decide which wins.
    """

    field_name: str
    coordinate_dependency: tuple[str, ...] | Sequence[str]
    treatment: str
    values_artifact: ArtifactRef | None = None
    analytical_spec: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.field_name, str) or not self.field_name.strip():
            raise ScopeValidationError("field_name must be a non-empty string.")
        dependency: object = self.coordinate_dependency
        if isinstance(dependency, (str, bytes)) or not isinstance(dependency, Sequence):
            raise ScopeValidationError(
                "coordinate_dependency must be a sequence of axis names, not a bare string."
            )
        axes = tuple(str(axis) for axis in dependency)
        if len(set(axes)) != len(axes):
            raise ScopeValidationError("coordinate_dependency must not repeat an axis.")
        object.__setattr__(self, "coordinate_dependency", axes)

        if self.treatment not in COEFFICIENT_TREATMENTS:
            raise ScopeValidationError(
                f"treatment {self.treatment!r} is not one of {list(COEFFICIENT_TREATMENTS)}. "
                f"'co_transforming_background' is deliberately not a value here: the "
                f"-ing form is the v0.34b *measured outcome* label, and this field "
                f"declares a capability."
            )
        if self.values_artifact is not None and not isinstance(self.values_artifact, ArtifactRef):
            raise ScopeValidationError("values_artifact must be an ArtifactRef or None.")
        if self.analytical_spec is not None:
            if not isinstance(self.analytical_spec, Mapping):
                raise ScopeValidationError("analytical_spec must be a mapping or None.")
            _require_json_scalar(self.analytical_spec, where="analytical_spec")
            object.__setattr__(self, "analytical_spec", dict(self.analytical_spec))
        semantic_hash(self.as_dict())

    def identity(self) -> str:
        return semantic_hash(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "coordinate_dependency": list(self.coordinate_dependency),
            "treatment": self.treatment,
            "values_artifact_id": (
                None if self.values_artifact is None else self.values_artifact.artifact_id
            ),
            "analytical_spec": (
                None if self.analytical_spec is None else dict(self.analytical_spec)
            ),
        }


@dataclass(frozen=True)
class ProblemInstanceSpec:
    """One concrete problem: equation, parameters, coefficient fields, domain."""

    equation_family: str
    equation_form: str
    parameters: Mapping[str, Any]
    coefficient_fields: Mapping[str, CoefficientFieldRef]
    spatial_axis_name: str
    time_axis_name: str
    domain_type: str
    boundary_conditions: Mapping[str, Any] = field(default_factory=dict)
    metadata_version: str = "0.1"

    def __post_init__(self) -> None:
        for name, allowed in (
            ("equation_family", EQUATION_FAMILIES),
            ("equation_form", EQUATION_FORMS),
            ("domain_type", DOMAIN_TYPES),
        ):
            value = getattr(self, name)
            if value not in allowed:
                raise ScopeValidationError(f"{name} {value!r} is not one of {list(allowed)}.")
        if self.metadata_version != "0.1":
            raise ScopeValidationError("metadata_version must be '0.1'.")
        for name in ("spatial_axis_name", "time_axis_name"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ScopeValidationError(f"{name} must be a non-empty string.")
        if self.spatial_axis_name == self.time_axis_name:
            raise ScopeValidationError(
                "spatial_axis_name and time_axis_name must differ; a single axis "
                "cannot be both."
            )
        for name in ("parameters", "boundary_conditions"):
            value = getattr(self, name)
            if not isinstance(value, Mapping):
                raise ScopeValidationError(f"{name} must be a mapping.")
            _require_json_scalar(value, where=name)
            object.__setattr__(self, name, dict(value))

        if not isinstance(self.coefficient_fields, Mapping):
            raise ScopeValidationError("coefficient_fields must be a mapping.")

        # One name, one owner. A name appearing in both is two declarations of
        # the same quantity with no rule about which an executor should read --
        # and the v0.37c C-5 defect is what that ambiguity produced: the bundle
        # declared an action on the parameter `nu` while the runner transformed
        # something else entirely, and nothing could tell them apart.
        overlap = sorted(set(self.parameters) & set(self.coefficient_fields))
        if overlap:
            raise ScopeValidationError(
                f"{overlap} appear in both parameters and coefficient_fields. A "
                f"quantity has one owner: a scalar parameter or a coordinate-"
                f"dependent field, never both. Rename one -- e.g. 'nu_baseline' "
                f"for the scalar and 'nu' for the field."
            )
        fields: dict[str, CoefficientFieldRef] = {}
        for key, ref in self.coefficient_fields.items():
            if not isinstance(ref, CoefficientFieldRef):
                raise ScopeValidationError(
                    f"coefficient_fields[{key!r}] is {type(ref).__name__}, not a "
                    f"CoefficientFieldRef."
                )
            if ref.field_name != key:
                raise ScopeValidationError(
                    f"coefficient_fields[{key!r}] carries field_name "
                    f"{ref.field_name!r}; the key and the name must agree or the "
                    f"mapping has two answers for one field."
                )
            unknown_axes = set(ref.coordinate_dependency) - {
                self.spatial_axis_name,
                self.time_axis_name,
            }
            if unknown_axes:
                raise ScopeValidationError(
                    f"coefficient_fields[{key!r}] depends on {sorted(unknown_axes)}, "
                    f"which are not this problem's axes "
                    f"({self.spatial_axis_name!r}, {self.time_axis_name!r})."
                )
            fields[key] = ref
        object.__setattr__(self, "coefficient_fields", fields)
        semantic_hash(self.as_dict())

    def identity(self) -> str:
        return semantic_hash(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "equation_family": self.equation_family,
            "equation_form": self.equation_form,
            "parameters": dict(self.parameters),
            "coefficient_fields": {
                name: ref.as_dict() for name, ref in self.coefficient_fields.items()
            },
            "spatial_axis_name": self.spatial_axis_name,
            "time_axis_name": self.time_axis_name,
            "domain_type": self.domain_type,
            "boundary_conditions": dict(self.boundary_conditions),
            "metadata_version": self.metadata_version,
        }
