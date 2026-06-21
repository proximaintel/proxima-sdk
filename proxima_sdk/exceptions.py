"""
Proxima SDK — Exceptions

Clear, typed exceptions for toolbox developers.
Every error tells you what went wrong and how to fix it.
"""


class ProximaError(Exception):
    """Base exception for all Proxima SDK errors."""
    pass


class SourceNotFoundError(ProximaError):
    """Knowledge source not found in the connected knowledge base."""
    def __init__(self, source_id: str):
        super().__init__(f"Knowledge source '{source_id}' not found. Check that the source is registered and connected to the agent's knowledge base.")
        self.source_id = source_id


class ConnectionFailedError(ProximaError):
    """Failed to connect to a platform service (Knowledge Service, Gateway)."""
    def __init__(self, service: str, url: str, detail: str = ""):
        super().__init__(f"Failed to connect to {service} at {url}. {detail}")
        self.service = service
        self.url = url


class QueryFailedError(ProximaError):
    """Knowledge query failed — source unreachable or credentials invalid."""
    def __init__(self, source_id: str, detail: str = ""):
        super().__init__(f"Query failed for source '{source_id}'. {detail}")
        self.source_id = source_id


class SecretNotFoundError(ProximaError):
    """Secret not found in the platform secret store."""
    def __init__(self, secret_name: str):
        super().__init__(f"Secret '{secret_name}' not found in platform secret store.")
        self.secret_name = secret_name


class PermissionDeniedError(ProximaError):
    """Insufficient permissions for the requested operation."""
    def __init__(self, operation: str, detail: str = ""):
        super().__init__(f"Permission denied for '{operation}'. {detail}")
        self.operation = operation


class TimeoutError(ProximaError):
    """Request timed out."""
    def __init__(self, service: str, timeout_seconds: float):
        super().__init__(f"Request to {service} timed out after {timeout_seconds}s.")
        self.service = service
        self.timeout_seconds = timeout_seconds
