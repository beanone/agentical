"""Tests for the LLMToolIntegration class."""

import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch

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
def mock_anthropic_client() -> AsyncMock:
    """Create a mock Anthropic client."""
    mock_client = AsyncMock()
    
    # Mock the messages create method
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Test response")]
    mock_response.tool_calls = []
    mock_client.messages.create = AsyncMock(return_value=mock_response)
    
    return mock_client


@pytest.fixture
def integration(mock_openai_client: AsyncMock) -> LLMToolIntegration:
    """Create a test integration instance with OpenAI."""
    return LLMToolIntegration(
        registry=ToolRegistry(),
        executor=ToolExecutor(ToolRegistry()),
        model_provider="openai",
        client=mock_openai_client
    )


@pytest.fixture
def anthropic_integration(mock_anthropic_client: AsyncMock) -> LLMToolIntegration:
    """Create a test integration instance with Anthropic."""
    return LLMToolIntegration(
        registry=ToolRegistry(),
        executor=ToolExecutor(ToolRegistry()),
        model_provider="anthropic",
        client=mock_anthropic_client
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


@pytest.mark.asyncio
async def test_anthropic_conversation_no_tools(anthropic_integration: LLMToolIntegration) -> None:
    """Test running an Anthropic conversation without tools."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there!"}
    ]
    
    response = await anthropic_integration.run_conversation(messages)
    assert isinstance(response, str)
    assert response == "Test response"
    
    # Verify the mock was called correctly with proper message format
    anthropic_integration.client.messages.create.assert_called_once()
    call_args = anthropic_integration.client.messages.create.call_args[1]
    assert call_args["system"] == "You are a helpful assistant."
    assert len(call_args["messages"]) == 2
    assert call_args["messages"][0]["role"] == "user"
    assert call_args["messages"][1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_anthropic_conversation_with_tools(anthropic_integration: LLMToolIntegration, mock_anthropic_client: AsyncMock) -> None:
    """Test running an Anthropic conversation with tools."""
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
    integration = LLMToolIntegration(registry, executor, model_provider="anthropic", client=mock_anthropic_client)
    
    # Mock tool call responses
    mock_tool_call = MagicMock()
    mock_tool_call.id = "test_call_id"
    mock_tool_call.name = "test_tool"
    mock_tool_call.input = {"param": "hello"}
    
    mock_response1 = MagicMock()
    mock_response1.content = [MagicMock(text="")]
    mock_response1.tool_calls = [mock_tool_call]
    
    mock_response2 = MagicMock()
    mock_response2.content = [MagicMock(text="Final response after tool call")]
    mock_response2.tool_calls = []
    
    # Set up the mock to return different responses
    mock_anthropic_client.messages.create = AsyncMock(side_effect=[
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
    assert mock_anthropic_client.messages.create.call_count == 2


@pytest.mark.asyncio
async def test_unsupported_model_provider() -> None:
    """Test handling of unsupported model provider."""
    with pytest.raises(ValueError, match="Unsupported model provider: unknown"):
        LLMToolIntegration(
            registry=ToolRegistry(),
            executor=ToolExecutor(ToolRegistry()),
            model_provider="unknown"
        )


@pytest.mark.asyncio
async def test_openai_client_initialization() -> None:
    """Test OpenAI client initialization."""
    with patch("openai.AsyncOpenAI") as mock_openai:
        integration = LLMToolIntegration(
            registry=ToolRegistry(),
            executor=ToolExecutor(ToolRegistry()),
            model_provider="openai"
        )
        assert integration.client is not None
        mock_openai.assert_called_once()


@pytest.mark.asyncio
async def test_anthropic_client_initialization() -> None:
    """Test Anthropic client initialization."""
    with patch("anthropic.AsyncAnthropic") as mock_anthropic:
        integration = LLMToolIntegration(
            registry=ToolRegistry(),
            executor=ToolExecutor(ToolRegistry()),
            model_provider="anthropic"
        )
        assert integration.client is not None
        mock_anthropic.assert_called_once()


@pytest.mark.asyncio
async def test_openai_import_error() -> None:
    """Test handling of OpenAI import error."""
    with patch("openai.AsyncOpenAI", side_effect=ImportError):
        integration = LLMToolIntegration(
            registry=ToolRegistry(),
            executor=ToolExecutor(ToolRegistry()),
            model_provider="openai"
        )
        assert integration.client is None
        with pytest.raises(ValueError, match="Client for openai is not initialized"):
            await integration.run_conversation([{"role": "user", "content": "Hello"}])


@pytest.mark.asyncio
async def test_anthropic_import_error() -> None:
    """Test handling of Anthropic import error."""
    with patch("anthropic.AsyncAnthropic", side_effect=ImportError):
        integration = LLMToolIntegration(
            registry=ToolRegistry(),
            executor=ToolExecutor(ToolRegistry()),
            model_provider="anthropic"
        )
        assert integration.client is None
        with pytest.raises(ValueError, match="Client for anthropic is not initialized"):
            await integration.run_conversation([{"role": "user", "content": "Hello"}]) 