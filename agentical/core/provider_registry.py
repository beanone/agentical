"""Provider factory interface for Agentical Framework.

This module provides a factory interface for creating LLM providers.
"""

from abc import ABC, abstractmethod
from typing import Any

from agentical.core.provider import Provider, ProviderConfig
from agentical.core.executor import ToolExecutor


class ProviderRegistry(ABC):
    """Abstract factory interface for creating LLM providers."""
    
    @abstractmethod
    def get_provider(self, name: str) -> Provider:
        """Get a provider by name.
        
        Args:
            name: The name of the provider
        """
        pass