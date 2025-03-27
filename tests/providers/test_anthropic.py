"""Tests for Anthropic provider implementation."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json

from agentical.core import ProviderConfig, ToolExecutor, Tool, ToolParameter, ProviderError
from agentical.providers.anthropic import AnthropicProvider


@pytest.fixture
def config():
    """Fixture for provider config."""
    return ProviderConfig(
        api_key="test-key",
        model="claude-3-sonnet-20240229"
    )


@pytest.fixture
def executor():
    """Fixture for tool executor."""
    return Mock(spec=ToolExecutor)


@pytest.fixture
def provider(config, executor):
    """Fixture for Anthropic provider."""
    return AnthropicProvider(config, executor)


@pytest.fixture
def sample_tools():
    """Fixture for sample tools."""
    return [
        Tool(
            name="test_tool",
            description="A test tool",
            parameters={
                "param1": ToolParameter(
                    type="string",
                    description="Test parameter",
                    required=True
                ),
                "param2": ToolParameter(
                    type="integer",
                    description="Optional parameter",
                    required=False,
                    enum=["1", "2", "3"]  # Enum values must be strings
                )
            }
        )
    ]


def test_initialization_success(config, executor):
    """Test successful provider initialization."""
    provider = AnthropicProvider(config, executor)
    assert provider.config == config
    assert provider.executor == executor


def test_initialization_no_model(executor):
    """Test initialization with no model specified."""
    config = ProviderConfig(api_key="test-key")
    provider = AnthropicProvider(config, executor)
    assert provider.config.model == "claude-3-sonnet-20240229"


@patch('agentical.providers.anthropic.AsyncAnthropic')
def test_initialization_failure(mock_client, config, executor):
    """Test initialization failure."""
    mock_client.side_effect = Exception("Connection error")
    
    with pytest.raises(ProviderError) as exc:
        AnthropicProvider(config, executor)
    assert "Failed to initialize Anthropic client" in str(exc.value)


def test_get_name(provider):
    """Test get_name method."""
    assert provider.get_name() == "anthropic"


def test_get_description(provider):
    """Test get_description method."""
    assert "Anthropic provider" in provider.get_description()
    assert "Claude models" in provider.get_description()


def test_format_tools(provider, sample_tools):
    """Test tool formatting."""
    formatted = provider._format_tools(sample_tools)
    
    assert len(formatted) == 1
    tool = formatted[0]
    
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "test_tool"
    assert tool["function"]["description"] == "A test tool"
    
    params = tool["function"]["parameters"]
    assert params["type"] == "object"
    assert "param1" in params["properties"]
    assert "param2" in params["properties"]
    assert params["properties"]["param1"]["type"] == "string"
    assert params["properties"]["param2"]["type"] == "integer"
    assert params["properties"]["param2"]["enum"] == ["1", "2", "3"]
    assert "param1" in params["required"]
    assert "param2" not in params["required"]


@pytest.mark.asyncio
async def test_run_conversation_simple(provider, sample_tools):
    """Test running a simple conversation without tool calls."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"}
    ]
    
    mock_response = Mock()
    mock_response.content = [Mock(text="Hello there!")]
    mock_response.tool_calls = None
    
    with patch.object(provider._client.messages, 'create', 
                     AsyncMock(return_value=mock_response)):
        response = await provider.run_conversation(messages, sample_tools)
        
        assert response == "Hello there!"
        provider._client.messages.create.assert_called_once_with(
            model=provider.config.model,
            system="You are a helpful assistant.",
            messages=[{"role": "user", "content": "Hello"}],
            tools=provider._format_tools(sample_tools)
        )


@pytest.mark.asyncio
async def test_run_conversation_with_tool_call(provider, sample_tools, executor):
    """Test running a conversation with tool calls."""
    messages = [{"role": "user", "content": "Use the tool"}]
    
    # Mock the tool call response
    tool_call = Mock()
    tool_call.id = "call_123"
    tool_call.name = "test_tool"
    tool_call.input = {"param1": "test"}
    
    mock_responses = [
        Mock(
            content=[Mock(text="")],
            tool_calls=[tool_call]
        ),
        Mock(
            content=[Mock(text="Tool used successfully")],
            tool_calls=None
        )
    ]
    
    # Mock the tool execution
    executor.execute_tool = AsyncMock(return_value="Tool result")
    
    with patch.object(provider._client.messages, 'create', 
                     AsyncMock(side_effect=mock_responses)):
        response = await provider.run_conversation(messages, sample_tools)
        
        assert response == "Tool used successfully"
        assert len(provider._client.messages.create.mock_calls) == 2
        
        # Verify tool execution
        executor.execute_tool.assert_called_once_with(
            "test_tool",
            {"param1": "test"}
        )


@pytest.mark.asyncio
async def test_run_conversation_error(provider, sample_tools):
    """Test error handling in conversation."""
    messages = [{"role": "user", "content": "Hello"}]
    
    with patch.object(provider._client.messages, 'create',
                     AsyncMock(side_effect=Exception("API error"))):
        with pytest.raises(ProviderError) as exc:
            await provider.run_conversation(messages, sample_tools)
        assert "Error in Anthropic conversation" in str(exc.value) 