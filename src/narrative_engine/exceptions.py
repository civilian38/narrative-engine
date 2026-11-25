class NarrativeEngineError(Exception):
    """Base exception for narrative engine errors."""


class ResourceNotFoundError(NarrativeEngineError):
    """Raised when a requested resource does not exist."""

    def __init__(
        self,
        resource: str,
        resource_id: int,
    ) -> None:
        self.resource = resource
        self.resource_id = resource_id

        super().__init__(
            f"{resource} resource with ID {resource_id} was not found."
        )


class InvalidOperationError(NarrativeEngineError):
    """Raised when an operation violates a domain rule."""


class PersistenceError(NarrativeEngineError):
    """Raised when a database operation fails."""


class ExternalServiceError(NarrativeEngineError):
    """Raised when a configured external service cannot complete a request."""


class InvalidModelResponseError(ExternalServiceError):
    """Raised when an external model returns an invalid or unusable response."""


class ConfigurationError(NarrativeEngineError):
    """Raised when required application configuration is missing or invalid."""


OuterAPIError = ExternalServiceError
"""Backward-compatible alias for ExternalServiceError."""
