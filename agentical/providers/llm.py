"""LLM Integration for Agentical Framework.

This module provides integration with LLM providers for tool execution.
"""

from typing import Dict, List, Any, Optional, Literal

from agentical.core import (
    ToolRegistry,
    ToolExecutor,
    ProviderRegistry,
    ProviderConfig
)
from .default_provider_registry import DefaultProviderRegistry


class LLMToolIntegration:
    """Integration between LLM and tools.
    
    This class provides the integration layer between LLMs 
    and the tool execution framework.
    """
    
    def __init__(
        self, 
        registry: ToolRegistry, 
        executor: ToolExecutor,
        provider_registry: Optional[ProviderRegistry] = None,
        provider_config: ProviderConfig = None,
        model_provider: Literal["openai", "anthropic"] = "openai",
    ) -> None:
        """Initialize LLM tool integration.
        
        Args:
            registry: The tool registry containing available tools
            executor: The tool executor for handling tool calls
            provider_registry: The provider registry for managing LLM providers
            provider_config: Configuration for the provider when using default registry
            model_provider: The LLM provider to use
        """
        self.registry = registry
        self.executor = executor
        self.provider_registry = provider_registry
        
        if provider_registry is None:
            self.provider_registry = DefaultProviderRegistry(provider_config, executor)
            
        self.provider = self.provider_registry.get_provider(model_provider)
    
    async def run_conversation(
        self, 
        messages: List[Dict[str, Any]], 
        model: Optional[str] = None
    ) -> str:
        """Run a conversation with tools.
        
        Args:
            messages: The conversation history
            model: The specific model to use (overrides the one set in init)
            
        Returns:
            The LLM's response
        """
        tools = self.registry.list_tools()
        return await self.provider.run_conversation(messages, tools) 