"""Shared data contracts.

Converted from a single module to a package at v0.38 day-zero so new
specification types can live in their own files. **Every existing import path is
preserved** -- ``from pdelie.contracts import FieldBatch`` resolves exactly as
before, and all 97 call sites in the tree were unchanged by the conversion. The
batch contracts live in :mod:`pdelie.contracts._core`.

Re-exports use the explicit ``X as X`` form. A package boundary turns a plain
``from ._core import X`` into an *implicit* re-export, which mypy rejects under
``--no-implicit-reexport`` -- and rightly, since it makes every incidental
import of a submodule part of the public surface by accident.
"""

from __future__ import annotations

from pdelie._boundary import (
    LEGACY_BOUNDARY_NORMALIZATION_OPERATION as LEGACY_BOUNDARY_NORMALIZATION_OPERATION,
)
from pdelie._boundary import (
    normalize_x_boundary_condition as normalize_x_boundary_condition,
)
from pdelie.contracts._core import ALLOWED_CLASSIFICATIONS as ALLOWED_CLASSIFICATIONS
from pdelie.contracts._core import (
    ALLOWED_DERIVATIVE_BACKENDS as ALLOWED_DERIVATIVE_BACKENDS,
)
from pdelie.contracts._core import ALLOWED_DOMAIN_VALIDITIES as ALLOWED_DOMAIN_VALIDITIES
from pdelie.contracts._core import ALLOWED_RESIDUAL_TYPES as ALLOWED_RESIDUAL_TYPES
from pdelie.contracts._core import GENERATOR_FAMILY_LAYOUT as GENERATOR_FAMILY_LAYOUT
from pdelie.contracts._core import (
    GENERATOR_FAMILY_REQUIRED_BASIS_SPEC_FIELDS as GENERATOR_FAMILY_REQUIRED_BASIS_SPEC_FIELDS,
)
from pdelie.contracts._core import REQUIRED_METADATA_KEYS as REQUIRED_METADATA_KEYS
from pdelie.contracts._core import SPATIAL_DIMS as SPATIAL_DIMS
from pdelie.contracts._core import DerivativeBatch as DerivativeBatch
from pdelie.contracts._core import FieldBatch as FieldBatch
from pdelie.contracts._core import GeneratorFamily as GeneratorFamily
from pdelie.contracts._core import InvariantMapSpec as InvariantMapSpec
from pdelie.contracts._core import ResidualBatch as ResidualBatch
from pdelie.contracts._core import VerificationReport as VerificationReport

# Private helpers that predate the conversion and are imported across module
# boundaries by five call sites. Aliased so the package boundary does not turn
# them into implicit re-exports; kept out of __all__ because they were never
# public API, only cross-module internals.
from pdelie.contracts._core import _is_uniform as _is_uniform
from pdelie.contracts._core import (
    _translation_generator_basis_spec as _translation_generator_basis_spec,
)
from pdelie.contracts.error_metric_spec import ERROR_METRIC_NORMS as ERROR_METRIC_NORMS
from pdelie.contracts.error_metric_spec import (
    ERROR_METRIC_QUANTITIES as ERROR_METRIC_QUANTITIES,
)
from pdelie.contracts.error_metric_spec import ErrorMetricSpec as ErrorMetricSpec
from pdelie.contracts.error_metric_spec import (
    require_matching_metric as require_matching_metric,
)
from pdelie.contracts.profile_geometry_spec import SMOOTHNESS_CLASSES as SMOOTHNESS_CLASSES
from pdelie.contracts.profile_geometry_spec import (
    ProfileGeometrySpec as ProfileGeometrySpec,
)
from pdelie.contracts.profile_geometry_spec import (
    require_compatible_domain as require_compatible_domain,
)

# These pass through pdelie.contracts for historical reasons: callers have
# imported them from here since before the conversion. Imported from their true
# sources rather than through _core.
from pdelie.errors import SchemaValidationError as SchemaValidationError
from pdelie.errors import ScopeValidationError as ScopeValidationError
from pdelie.errors import ShapeValidationError as ShapeValidationError

__all__ = [
    "ALLOWED_CLASSIFICATIONS",
    "ALLOWED_DERIVATIVE_BACKENDS",
    "ALLOWED_DOMAIN_VALIDITIES",
    "ALLOWED_RESIDUAL_TYPES",
    "ERROR_METRIC_NORMS",
    "ERROR_METRIC_QUANTITIES",
    "GENERATOR_FAMILY_LAYOUT",
    "GENERATOR_FAMILY_REQUIRED_BASIS_SPEC_FIELDS",
    "LEGACY_BOUNDARY_NORMALIZATION_OPERATION",
    "REQUIRED_METADATA_KEYS",
    "SMOOTHNESS_CLASSES",
    "SPATIAL_DIMS",
    "DerivativeBatch",
    "ErrorMetricSpec",
    "FieldBatch",
    "GeneratorFamily",
    "InvariantMapSpec",
    "ProfileGeometrySpec",
    "ResidualBatch",
    "SchemaValidationError",
    "ScopeValidationError",
    "ShapeValidationError",
    "VerificationReport",
    "normalize_x_boundary_condition",
    "require_compatible_domain",
    "require_matching_metric",
]
