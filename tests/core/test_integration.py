"""Tests for the LLMToolIntegration class."""

import pytest
from typing import Dict, Any, List

from agentical.core import LLMToolIntegration, ToolRegistry, ToolExecutor


@pytest.fixture
def integration() -> LLMToolIntegration:
    """Create a test integration instance."""
    return LLMToolIntegration(
        registry=ToolRegistry(),
        executor=ToolExecutor(ToolRegistry()),
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
    assert len(response) > 0


@pytest.mark.asyncio
async def test_run_conversation_with_tools(integration: LLMToolIntegration) -> None:
    """Test running a conversation with tools."""
    # Create a test tool
    registry = ToolRegistry()
    registry.register_tool({
        "name": "test_tool",
        "description": "A test tool",
        "parameters": {
            "type": "object",
            "properties": {
                "param": {
                    "type": "string",
                    "description": "A test parameter"
                }
            },
            "required": ["param"]
        }
    })
    
    # Create executor with handler
    executor = ToolExecutor(registry)
    executor.register_handler("test_tool", lambda params: f"Test result: {params['param']}")
    
    # Create integration with tool
    integration = LLMToolIntegration(registry, executor)
    
    # Run conversation
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Use the test tool with param 'hello'"}
    ]
    
    response = await integration.run_conversation(messages)
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_run_conversation_api_error(integration: LLMToolIntegration) -> None:
    """Test handling of API errors."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
    
    # Simulate API error
    integration.client = None
    
    with pytest.raises(ValueError):
        await integration.run_conversation(messages) 