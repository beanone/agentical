"""Default provider registry implementation."""

from typing import Dict

from agentical.core import Provider, ProviderConfig
from agentical.core import ToolExecutor
from agentical.core import ProviderRegistry
from .openai import OpenAIProvider
from .anthropic import AnthropicProvider


class DefaultProviderRegistry(ProviderRegistry):
    """Default implementation of the provider registry."""
    
    _instance = None
    
    def __new__(cls, config: ProviderConfig, executor: ToolExecutor):
        """Create or return the singleton instance.
        
        Args:
            config: Configuration for the providers
            executor: Tool executor for handling tool calls
            
        Returns:
            The singleton instance
        """
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.providers: Dict[str, Provider] = {}
            
            # Initialize default providers
            openai = OpenAIProvider(config, executor)
            anthropic = AnthropicProvider(config, executor)
            
            cls._instance.providers[openai.get_name()] = openai
            cls._instance.providers[anthropic.get_name()] = anthropic
            
        return cls._instance

    def get_provider(self, name: str) -> Provider:
        """Get a provider by name.
        
        Args:
            name: The name of the provider
            
        Returns:
            The requested provider
            
        Raises:
            KeyError: If the provider is not found
        """
        if name not in self.providers:
            raise KeyError(f"Provider '{name}' not found")
        return self.providers[name]
