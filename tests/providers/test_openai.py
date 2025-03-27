"""Tests for OpenAI provider implementation."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import json

from agentical.core import ProviderConfig, ToolExecutor, Tool, ToolParameter, ProviderError, ProviderSettings
from agentical.providers.openai import OpenAIProvider


@pytest.fixture
def config(base_provider_config):
    """Fixture for provider config."""
    return base_provider_config(
        provider_type="openai",
        api_key="test-key",
        model="gpt-4-turbo"
    )


@pytest.fixture
def executor():
    """Fixture for tool executor."""
    return Mock(spec=ToolExecutor)


@pytest.fixture
def provider(config, executor):
    """Fixture for OpenAI provider."""
    return OpenAIProvider(config, executor)


@pytest.fixture
def sample_tools(base_tool, base_tool_parameter):
    """Fixture for sample tools."""
    return [
        base_tool(
            name="test_tool",
            description="A test tool",
            parameters={
                "param1": base_tool_parameter(
                    param_type="string",
                    description="Test parameter",
                    required=True
                ),
                "param2": base_tool_parameter(
                    param_type="integer",
                    description="Optional parameter",
                    required=False,
                    enum=["1", "2", "3"]  # Enum values must be strings
                )
            }
        )
    ]


def test_initialization_success(config, executor):
    """Test successful provider initialization."""
    provider = OpenAIProvider(config, executor)
    assert provider.config == config
    assert provider.executor == executor


def test_initialization_no_model(executor, base_provider_config):
    """Test initialization with no model specified."""
    config = base_provider_config(
        provider_type="openai",
        api_key="test-key"
    )
    provider = OpenAIProvider(config, executor)
    assert provider.config.model == "gpt-4-turbo-preview"


@patch('agentical.providers.openai.AsyncOpenAI')
def test_initialization_failure(mock_client, config, executor):
    """Test initialization failure."""
    mock_client.side_effect = Exception("Connection error")
    
    with pytest.raises(ProviderError) as exc:
        OpenAIProvider(config, executor)
    assert "Failed to initialize OpenAI client" in str(exc.value)


def test_get_name(provider):
    """Test get_name method."""
    assert provider.get_name() == "openai"


def test_get_description(provider):
    """Test get_description method."""
    assert "OpenAI provider" in provider.get_description()
    assert "GPT models" in provider.get_description()


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
    assert params["properties"]["param2"]["enum"] == ["1", "2", "3"]  # Enum values are strings
    assert "param1" in params["required"]
    assert "param2" not in params["required"]


@pytest.mark.asyncio
async def test_run_conversation_simple(provider, sample_tools):
    """Test running a simple conversation without tool calls."""
    messages = [{"role": "user", "content": "Hello"}]
    
    mock_response = Mock()
    mock_response.choices = [
        Mock(message=Mock(content="Hello there!", tool_calls=None))
    ]
    
    with patch.object(provider._client.chat.completions, 'create', 
                     AsyncMock(return_value=mock_response)):
        response = await provider.run_conversation(messages, sample_tools)
        
        assert response == "Hello there!"
        provider._client.chat.completions.create.assert_called_once_with(
            model=provider.config.model,
            messages=messages,
            tools=provider._format_tools(sample_tools)
        )


@pytest.mark.asyncio
async def test_run_conversation_with_tool_call(provider, sample_tools, executor):
    """Test running a conversation with tool calls."""
    messages = [{"role": "user", "content": "Use the tool"}]
    
    # Mock the tool call response
    tool_call = Mock()
    tool_call.id = "call_123"
    tool_call.function.name = "test_tool"
    tool_call.function.arguments = json.dumps({"param1": "test"})
    
    mock_responses = [
        Mock(choices=[
            Mock(message=Mock(
                content=None,
                tool_calls=[tool_call]
            ))
        ]),
        Mock(choices=[
            Mock(message=Mock(
                content="Tool used successfully",
                tool_calls=None
            ))
        ])
    ]
    
    # Mock the tool execution
    executor.execute_tool = AsyncMock(return_value="Tool result")
    
    with patch.object(provider._client.chat.completions, 'create', 
                     AsyncMock(side_effect=mock_responses)):
        response = await provider.run_conversation(messages, sample_tools)
        
        assert response == "Tool used successfully"
        assert len(provider._client.chat.completions.create.mock_calls) == 2
        
        # Verify tool execution
        executor.execute_tool.assert_called_once_with(
            "test_tool",
            {"param1": "test"}
        )


@pytest.mark.asyncio
async def test_run_conversation_error(provider, sample_tools):
    """Test error handling in conversation."""
    messages = [{"role": "user", "content": "Hello"}]
    
    with patch.object(provider._client.chat.completions, 'create',
                     AsyncMock(side_effect=Exception("API error"))):
        with pytest.raises(ProviderError) as exc:
            await provider.run_conversation(messages, sample_tools)
        assert "Error in OpenAI conversation" in str(exc.value) 