from __future__ import annotations

from pdelie.contracts import GeneratorFamily
from pdelie.errors import ScopeValidationError


def _validate_supported_external_family(generator: GeneratorFamily) -> None:
    if not generator.parameterization.startswith("polynomial_"):
        raise ScopeValidationError(
            "V0.5 Milestone 2 only supports polynomial GeneratorFamily parameterizations."
        )
