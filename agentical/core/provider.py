"""Core provider interface for the Agentical framework."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass

from agentical.core.types import Tool


class ProviderError(Exception):
    """Base exception for provider-related errors."""
    pass


@dataclass
class ProviderConfig:
    """Configuration for a provider."""
    api_key: str
    model: str = ""  # Default model will be set by provider


class Provider(ABC):
    """Base interface for providers."""
    
    @abstractmethod
    def get_name(self) -> str:
        """Get the name of the provider.
        
        Returns:
            The provider's name (e.g., 'openai', 'anthropic')
        """
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get a description of the provider.
        
        Returns:
            A brief description of the provider and its capabilities
        """
        pass
    
    @abstractmethod
    async def run_conversation(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Tool]
    ) -> str:
        """Run a conversation with the provider using available tools.
        
        Args:
            messages: List of conversation messages
            tools: List of available tools
            
        Returns:
            The provider's response
            
        Raises:
            ProviderError: If there's an error communicating with the provider
        """
        pass 