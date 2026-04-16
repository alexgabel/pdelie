class PDELieValidationError(ValueError):
    """Base class for V0.1 contract validation failures."""


class SchemaValidationError(PDELieValidationError):
    """Raised when object structure or required fields are invalid."""


class ShapeValidationError(PDELieValidationError):
    """Raised when tensor or coordinate shapes are incompatible."""


class ScopeValidationError(PDELieValidationError):
    """Raised when inputs are outside the stable V0.1 scope."""

