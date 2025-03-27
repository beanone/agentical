"""Tests for the LLMToolIntegration class."""

import json
from typing import Dict, Any, List
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agentical.core import ToolRegistry, ToolExecutor, ProviderConfig, ProviderRegistry
from agentical.core.types import Tool, ToolParameter
from agentical.providers.llm import LLMToolIntegration
from agentical.providers.default_provider_registry import DefaultProviderRegistry


@pytest.fixture
def config() -> ProviderConfig:
    """Create a test provider config."""
    return ProviderConfig(
        api_key="test-key",
        model="gpt-4-turbo-preview"
    )


@pytest.fixture
def mock_provider_registry(config: ProviderConfig, executor: ToolExecutor) -> ProviderRegistry:
    """Create a mock provider registry."""
    registry = MagicMock(spec=DefaultProviderRegistry)
    
    # Mock provider for testing
    mock_provider = AsyncMock()
    mock_provider.run_conversation = AsyncMock(return_value="Test response")
    registry.get_provider.return_value = mock_provider
    
    return registry


@pytest.fixture
def executor() -> ToolExecutor:
    """Create a test executor."""
    return ToolExecutor(ToolRegistry())


@pytest.fixture
def integration(config: ProviderConfig, executor: ToolExecutor, mock_provider_registry: ProviderRegistry) -> LLMToolIntegration:
    """Create a test integration instance."""
    return LLMToolIntegration(
        registry=ToolRegistry(),
        executor=executor,
        provider_registry=mock_provider_registry,
        provider_config=config,
        model_provider="openai"
    )


@pytest.mark.asyncio
async def test_run_conversation_no_tools(integration: LLMToolIntegration) -> None:
    """Test running a conversation without tools."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
    
    response = await integration.run_conversation(messages)
    assert isinstance(response, str)
    assert response == "Test response"
    
    # Verify the provider was called correctly
    integration.provider.run_conversation.assert_called_once()
    call_args = integration.provider.run_conversation.call_args[0]
    assert call_args[0] == messages
    assert call_args[1] == []


@pytest.mark.asyncio
async def test_run_conversation_with_tools(
    config: ProviderConfig,
    executor: ToolExecutor,
    mock_provider_registry: ProviderRegistry
) -> None:
    """Test running a conversation with tools."""
    # Create a test tool
    registry = ToolRegistry()
    test_tool = Tool(
        name="test_tool",
        description="A test tool",
        parameters={
            "param": ToolParameter(
                type="string",
                description="A test parameter",
                required=True
            )
        }
    )
    registry.register_tool(test_tool)
    
    # Create integration with tool
    integration = LLMToolIntegration(
        registry=registry,
        executor=executor,
        provider_registry=mock_provider_registry,
        provider_config=config,
        model_provider="openai"
    )
    
    # Run conversation
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Use the test tool with param 'hello'"}
    ]
    
    response = await integration.run_conversation(messages)
    assert isinstance(response, str)
    assert response == "Test response"
    
    # Verify the provider was called with the correct tools
    integration.provider.run_conversation.assert_called_once()
    call_args = integration.provider.run_conversation.call_args[0]
    assert call_args[0] == messages
    assert len(call_args[1]) == 1
    assert call_args[1][0].name == "test_tool"


@pytest.mark.asyncio
async def test_run_conversation_api_error(integration: LLMToolIntegration) -> None:
    """Test handling of API errors."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
    
    # Simulate API error
    integration.provider.run_conversation.side_effect = Exception("API error")
    
    with pytest.raises(Exception, match="API error"):
        await integration.run_conversation(messages)


@pytest.mark.asyncio
async def test_default_provider_registry() -> None:
    """Test using the default provider registry."""
    with patch("agentical.providers.llm.DefaultProviderRegistry") as mock_registry_class:
        mock_provider = AsyncMock()
        mock_provider.run_conversation = AsyncMock(return_value="Test response")
        mock_registry = MagicMock()
        mock_registry.get_provider.return_value = mock_provider
        mock_registry_class.return_value = mock_registry
        
        integration = LLMToolIntegration(
            registry=ToolRegistry(),
            executor=ToolExecutor(ToolRegistry()),
            provider_config=ProviderConfig(api_key="test-key"),
            model_provider="openai"
        )
        
        assert integration.provider_registry is not None
        mock_registry_class.assert_called_once()


@pytest.mark.asyncio
async def test_unsupported_model_provider(
    config: ProviderConfig,
    executor: ToolExecutor,
    mock_provider_registry: ProviderRegistry
) -> None:
    """Test handling of unsupported model provider."""
    mock_provider_registry.get_provider.side_effect = KeyError("Provider 'unknown' not found")
    
    with pytest.raises(KeyError, match="Provider 'unknown' not found"):
        LLMToolIntegration(
            registry=ToolRegistry(),
            executor=executor,
            provider_registry=mock_provider_registry,
            provider_config=config,
            model_provider="unknown"
        ) 