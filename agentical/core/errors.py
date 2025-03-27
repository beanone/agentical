"""Error classes for the Agentical framework."""

class ProviderError(Exception):
    """Base exception for all provider-related errors."""
    
    def __init__(self, message: str, *, provider_name: str = None):
        self.provider_name = provider_name
        super().__init__(message)

    def __str__(self) -> str:
        if self.provider_name:
            return f"[{self.provider_name}] {super().__str__()}"
        return super().__str__()


class ConfigError(ProviderError):
    """Raised when there is an error in provider configuration."""
    pass


class APIError(ProviderError):
    """Raised when there is an error communicating with the provider's API."""
    pass


class ToolError(ProviderError):
    """Raised when there is an error executing a tool."""
    pass