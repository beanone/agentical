"""Tests for the LLMToolIntegration class."""

import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

from agentical.core import LLMToolIntegration, ToolRegistry, ToolExecutor
from agentical.types import Tool, ToolParameter


@pytest.fixture
def mock_openai_client() -> AsyncMock:
    """Create a mock OpenAI client."""
    mock_client = AsyncMock()
    
    # Mock the chat completions create method
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="Test response",
                tool_calls=[]
            )
        )
    ]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    
    return mock_client


@pytest.fixture
def integration(mock_openai_client: AsyncMock) -> LLMToolIntegration:
    """Create a test integration instance."""
    return LLMToolIntegration(
        registry=ToolRegistry(),
        executor=ToolExecutor(ToolRegistry()),
        model_provider="openai",
        client=mock_openai_client
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
    
    # Verify the mock was called correctly
    integration.client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_run_conversation_with_tools(integration: LLMToolIntegration, mock_openai_client: AsyncMock) -> None:
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
    
    # Create executor with handler
    executor = ToolExecutor(registry)
    async def test_handler(params: Dict[str, Any]) -> str:
        return f"Test result: {params['param']}"
    executor.register_handler("test_tool", test_handler)
    
    # Create integration with tool
    integration = LLMToolIntegration(registry, executor, model_provider="openai", client=mock_openai_client)
    
    # Mock a tool call response
    mock_tool_call = MagicMock()
    mock_tool_call.id = "test_call_id"
    mock_tool_call.function.name = "test_tool"
    mock_tool_call.function.arguments = '{"param": "hello"}'
    
    mock_response1 = MagicMock()
    mock_response1.choices = [
        MagicMock(
            message=MagicMock(
                content=None,
                tool_calls=[mock_tool_call]
            )
        )
    ]
    
    mock_response2 = MagicMock()
    mock_response2.choices = [
        MagicMock(
            message=MagicMock(
                content="Final response after tool call",
                tool_calls=[]
            )
        )
    ]
    
    # Set up the mock to return different responses
    mock_openai_client.chat.completions.create = AsyncMock(side_effect=[
        mock_response1,
        mock_response2
    ])
    
    # Run conversation
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Use the test tool with param 'hello'"}
    ]
    
    response = await integration.run_conversation(messages)
    assert isinstance(response, str)
    assert response == "Final response after tool call"
    
    # Verify the mock was called twice (initial + after tool call)
    assert mock_openai_client.chat.completions.create.call_count == 2


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