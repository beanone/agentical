"""Unit tests for Anthropic backend implementation."""

import os
from unittest.mock import AsyncMock, Mock, patch

import anthropic
import httpx
import pytest
from anthropic.types import Message, Usage
from mcp.types import CallToolResult, TextContent
from mcp.types import Tool as MCPTool

from agentical.llm.anthropic.anthropic_chat import AnthropicBackend


@pytest.fixture
def mock_anthropic_client():
    """Fixture providing a mock Anthropic client."""
    with patch("anthropic.AsyncAnthropic") as mock:
        mock_instance = AsyncMock()
        mock_instance.messages = AsyncMock()
        mock_instance.messages.create = AsyncMock()
        mock.return_value = mock_instance
        yield mock


def test_init_without_api_key():
    """Test initialization fails without API key."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY not found"):
            AnthropicBackend()


def test_init_with_invalid_api_key():
    """Test initialization with invalid API key."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.headers = {"content-type": "application/json"}
    mock_response.request = Mock(spec=httpx.Request)
    with patch(
        "anthropic.AsyncAnthropic",
        side_effect=anthropic.AuthenticationError(
            message="401 Client Error: Unauthorized",
            response=mock_response,
            body={"error": {"type": "authentication_error"}},
        ),
    ):
        with pytest.raises(
            ValueError,
            match=(
                "Failed to initialize Anthropic client: 401 Client Error: Unauthorized"
            ),
        ):
            AnthropicBackend(api_key="invalid_key")


def test_init_with_api_key(mock_anthropic_client):
    """Test initialization with explicit API key."""
    backend = AnthropicBackend(api_key="test_key")
    assert backend.model == AnthropicBackend.DEFAULT_MODEL


def test_init_with_env_vars(mock_env_vars, mock_anthropic_client):
    """Test initialization with environment variables."""
    backend = AnthropicBackend()
    assert backend.model == "test_model"


@pytest.fixture
def mock_env_vars():
    """Fixture to set and cleanup environment variables."""
    with patch.dict(
        os.environ,
        {"ANTHROPIC_API_KEY": "test_key", "ANTHROPIC_MODEL": "test_model"},
        clear=True,
    ):
        yield


@pytest.fixture
def mock_mcp_tools():
    """Fixture providing mock MCP tools."""
    return [
        MCPTool(
            name="tool1",
            description="Test tool 1",
            parameters={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "First parameter"}
                },
                "required": ["param1"],
            },
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "First parameter"}
                },
                "required": ["param1"],
            },
        )
    ]


@pytest.mark.asyncio
async def test_process_query_without_tool_calls(
    mock_env_vars, mock_anthropic_client, mock_mcp_tools
):
    """Test processing a query that doesn't require tool calls."""
    # Setup mock response
    mock_message = Message(
        id="msg_123",
        model="claude-3",
        role="assistant",
        type="message",
        content=[{"type": "text", "text": "<answer>Test response</answer>"}],
        stop_reason="end_turn",
        stop_sequence=None,
        usage=Usage(input_tokens=10, output_tokens=20),
    )

    # Configure mock client
    mock_client = AsyncMock()
    mock_client.messages = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)
    mock_anthropic_client.return_value = mock_client

    # Execute test
    backend = AnthropicBackend()
    response = await backend.process_query(
        query="test query",
        tools=mock_mcp_tools,
        resources=[],
        prompts=[],
        execute_tool=AsyncMock(),
    )

    assert response == "Test response"
    mock_client.messages.create.assert_called_once()


@pytest.mark.asyncio
async def test_process_query_with_tool_calls(
    mock_env_vars, mock_anthropic_client, mock_mcp_tools
):
    """Test processing a query that requires tool calls."""
    # Setup mock responses
    # First response with tool call
    mock_message1 = Message(
        id="test1",
        model="claude-3",
        role="assistant",
        type="message",
        content=[
            {
                "type": "tool_use",
                "id": "call1",
                "name": "tool1",
                "input": {"param1": "test"},
            }
        ],
        stop_reason="tool_use",
        stop_sequence=None,
        usage=Usage(input_tokens=10, output_tokens=20),
    )

    # Second response with final answer
    mock_message2 = Message(
        id="test2",
        model="claude-3",
        role="assistant",
        type="message",
        content=[{"type": "text", "text": "Final response"}],
        stop_reason="end_turn",
        stop_sequence=None,
        usage=Usage(input_tokens=10, output_tokens=20),
    )

    # Configure mock client
    mock_client = AsyncMock()
    mock_client.messages = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=[mock_message1, mock_message2])
    mock_anthropic_client.return_value = mock_client

    # Mock tool execution
    mock_execute_tool = AsyncMock(
        return_value=CallToolResult(
            content=[TextContent(type="text", text="Tool result")]
        )
    )

    # Execute test
    backend = AnthropicBackend()
    response = await backend.process_query(
        query="test query",
        tools=mock_mcp_tools,
        resources=[],
        prompts=[],
        execute_tool=mock_execute_tool,
    )

    assert response == "Final response"
    assert mock_client.messages.create.call_count == 2
    mock_execute_tool.assert_called_once_with("tool1", {"param1": "test"})


@pytest.mark.asyncio
async def test_process_query_with_tool_error(
    mock_env_vars, mock_anthropic_client, mock_mcp_tools
):
    """Test handling of tool execution errors."""
    # Setup mock responses
    # First response with tool call
    mock_message1 = Message(
        id="test1",
        model="claude-3",
        role="assistant",
        type="message",
        content=[
            {
                "type": "tool_use",
                "id": "call1",
                "name": "tool1",
                "input": {"param1": "test"},
            }
        ],
        stop_reason="tool_use",
        stop_sequence=None,
        usage=Usage(input_tokens=10, output_tokens=20),
    )

    # Second response with error handling
    mock_message2 = Message(
        id="test2",
        model="claude-3",
        role="assistant",
        type="message",
        content=[{"type": "text", "text": "Error handled response"}],
        stop_reason="end_turn",
        stop_sequence=None,
        usage=Usage(input_tokens=10, output_tokens=20),
    )

    # Configure mock client
    mock_client = AsyncMock()
    mock_client.messages = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=[mock_message1, mock_message2])
    mock_anthropic_client.return_value = mock_client

    # Mock tool execution to raise error
    mock_execute_tool = AsyncMock(side_effect=ValueError("Tool execution failed"))

    # Execute test
    backend = AnthropicBackend()
    response = await backend.process_query(
        query="test query",
        tools=mock_mcp_tools,
        resources=[],
        prompts=[],
        execute_tool=mock_execute_tool,
    )

    assert response == "Error handled response"
    mock_execute_tool.assert_called_once_with("tool1", {"param1": "test"})


@pytest.mark.asyncio
async def test_process_query_with_context(
    mock_env_vars, mock_anthropic_client, mock_mcp_tools
):
    """Test processing a query with conversation context."""
    # Setup mock response
    mock_message = Message(
        id="test",
        content=[{"type": "text", "text": "Test response"}],
        role="assistant",
        model="claude-3",
        type="message",
        stop_reason="end_turn",
        stop_sequence=None,
        usage=Usage(input_tokens=10, output_tokens=20),
        tool_calls=None,
    )

    # Configure mock client
    mock_client = Mock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)
    mock_anthropic_client.return_value = mock_client

    # Execute test with context
    backend = AnthropicBackend()
    context = [{"role": "user", "content": "previous message"}]
    response = await backend.process_query(
        query="test query",
        tools=mock_mcp_tools,
        resources=[],
        prompts=[],
        execute_tool=AsyncMock(),
        context=context,
    )

    assert response == "Test response"
    mock_client.messages.create.assert_called_once()


@pytest.mark.asyncio
async def test_process_query_with_api_error(
    mock_env_vars, mock_anthropic_client, mock_mcp_tools
):
    """Test handling of API errors."""
    # Configure mock client to raise an error
    mock_client = Mock()
    mock_client.messages.create = AsyncMock(side_effect=Exception("API error"))
    mock_anthropic_client.return_value = mock_client

    # Execute test
    backend = AnthropicBackend()
    with pytest.raises(Exception) as exc_info:
        await backend.process_query(
            query="test query",
            tools=mock_mcp_tools,
            resources=[],
            prompts=[],
            execute_tool=AsyncMock(),
        )

    assert "API error" in str(exc_info.value)
    mock_client.messages.create.assert_called_once()


@pytest.mark.asyncio
async def test_process_query_with_multiple_tool_calls(
    mock_env_vars, mock_anthropic_client, mock_mcp_tools
):
    """Test processing a query that requires multiple tool calls."""
    # Setup mock responses
    # First response with tool call
    mock_message1 = Message(
        id="test1",
        model="claude-3",
        role="assistant",
        type="message",
        content=[
            {
                "type": "tool_use",
                "id": "call1",
                "name": "tool1",
                "input": {"param1": "test1"},
            }
        ],
        stop_reason="tool_use",
        stop_sequence=None,
        usage=Usage(input_tokens=10, output_tokens=20),
    )

    # Second response with another tool call
    mock_message2 = Message(
        id="test2",
        model="claude-3",
        role="assistant",
        type="message",
        content=[
            {
                "type": "tool_use",
                "id": "call2",
                "name": "tool1",
                "input": {"param1": "test2"},
            }
        ],
        stop_reason="tool_use",
        stop_sequence=None,
        usage=Usage(input_tokens=10, output_tokens=20),
    )

    # Third response with final answer
    mock_message3 = Message(
        id="test3",
        model="claude-3",
        role="assistant",
        type="message",
        content=[{"type": "text", "text": "Final response"}],
        stop_reason="end_turn",
        stop_sequence=None,
        usage=Usage(input_tokens=10, output_tokens=20),
    )

    # Configure mock client
    mock_client = AsyncMock()
    mock_client.messages = AsyncMock()
    mock_client.messages.create = AsyncMock(
        side_effect=[mock_message1, mock_message2, mock_message3]
    )
    mock_anthropic_client.return_value = mock_client

    # Mock tool execution
    mock_execute_tool = AsyncMock(
        return_value=CallToolResult(
            content=[TextContent(type="text", text="Tool result")]
        )
    )

    # Execute test
    backend = AnthropicBackend()
    response = await backend.process_query(
        query="test query",
        tools=mock_mcp_tools,
        resources=[],
        prompts=[],
        execute_tool=mock_execute_tool,
    )

    assert response == "Final response"
    assert mock_client.messages.create.call_count == 3
    assert mock_execute_tool.call_count == 2
    mock_execute_tool.assert_any_call("tool1", {"param1": "test1"})
    mock_execute_tool.assert_any_call("tool1", {"param1": "test2"})


@pytest.mark.asyncio
async def test_process_query_with_system_content(
    mock_env_vars, mock_anthropic_client, mock_mcp_tools
):
    """Test processing a query with and without system content."""
    # Setup mock response
    mock_message = Message(
        id="msg_123",
        model="claude-3",
        role="assistant",
        type="message",
        content=[{"type": "text", "text": "<answer>Test response</answer>"}],
        stop_reason="end_turn",
        stop_sequence=None,
        usage=Usage(input_tokens=10, output_tokens=20),
    )

    # Configure mock client
    mock_client = AsyncMock()
    mock_client.messages = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)
    mock_anthropic_client.return_value = mock_client

    # Test with custom system content
    backend = AnthropicBackend()
    custom_system_content = "Custom system instructions"
    await backend.process_query(
        query="test query",
        tools=mock_mcp_tools,
        resources=[],
        prompts=[],
        execute_tool=AsyncMock(),
        context=[{"role": "system", "content": custom_system_content}],
    )

    # Verify custom system content was used
    call_kwargs = mock_client.messages.create.call_args[1]
    assert "system" in call_kwargs
    assert isinstance(call_kwargs["system"], list)
    assert len(call_kwargs["system"]) == 1
    assert call_kwargs["system"][0]["type"] == "text"
    assert call_kwargs["system"][0]["text"] == custom_system_content

    # Reset mock
    mock_client.messages.create.reset_mock()

    # Test without system content (should use default)
    await backend.process_query(
        query="test query",
        tools=mock_mcp_tools,
        resources=[],
        prompts=[],
        execute_tool=AsyncMock(),
    )

    # Verify default system content was used
    call_kwargs = mock_client.messages.create.call_args[1]
    assert "system" in call_kwargs
    assert isinstance(call_kwargs["system"], list)
    assert len(call_kwargs["system"]) == 1
    assert call_kwargs["system"][0]["type"] == "text"
    assert "You are an AI assistant" in call_kwargs["system"][0]["text"]
    assert "<thinking>" in call_kwargs["system"][0]["text"]
    assert "<answer>" in call_kwargs["system"][0]["text"]

    # Reset mock
    mock_client.messages.create.reset_mock()

    # Test with None system content (should use default system content)
    await backend.process_query(
        query="test query",
        tools=mock_mcp_tools,
        resources=[],
        prompts=[],
        execute_tool=AsyncMock(),
        context=[{"role": "system", "content": None}],
    )

    # Verify default system content was used
    call_kwargs = mock_client.messages.create.call_args[1]
    assert "system" in call_kwargs
    assert isinstance(call_kwargs["system"], list)
    assert len(call_kwargs["system"]) == 1
    assert call_kwargs["system"][0]["type"] == "text"
    assert "You are an AI assistant" in call_kwargs["system"][0]["text"]
    assert "<thinking>" in call_kwargs["system"][0]["text"]
    assert "<answer>" in call_kwargs["system"][0]["text"]
