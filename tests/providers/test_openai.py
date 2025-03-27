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
def executor(base_tool_executor, sample_tools, mock_async_handler):
    """Fixture for tool executor."""
    return base_tool_executor(
        tools=sample_tools,
        handlers={
            "test_tool": mock_async_handler("Tool result")
        }
    )


@pytest.fixture
def provider(config, executor):
    """Fixture for OpenAI provider."""
    return OpenAIProvider(config, executor)


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
    
    assert len(formatted) == 2
    
    # Test first tool
    tool1 = formatted[0]
    assert tool1["type"] == "function"
    assert tool1["function"]["name"] == "test_tool"
    assert tool1["function"]["description"] == "A test tool for demonstration"
    
    params1 = tool1["function"]["parameters"]
    assert params1["type"] == "object"
    assert "param1" in params1["properties"]
    assert "param2" in params1["properties"]
    assert params1["properties"]["param1"]["type"] == "string"
    assert params1["properties"]["param2"]["type"] == "integer"
    assert params1["properties"]["param2"]["enum"] == ["1", "2", "3"]
    assert "param1" in params1["required"]
    assert "param2" not in params1["required"]
    
    # Test second tool
    tool2 = formatted[1]
    assert tool2["type"] == "function"
    assert tool2["function"]["name"] == "another_tool"
    assert tool2["function"]["description"] == "Another test tool with different parameters"
    
    params2 = tool2["function"]["parameters"]
    assert params2["type"] == "object"
    assert "param3" in params2["properties"]
    assert "param4" in params2["properties"]
    assert params2["properties"]["param3"]["type"] == "boolean"
    assert params2["properties"]["param4"]["type"] == "array"
    assert "param3" in params2["required"]
    assert "param4" not in params2["required"]


@pytest.mark.asyncio
async def test_run_conversation_simple(provider, sample_tools, sample_messages):
    """Test running a simple conversation without tool calls."""
    mock_response = Mock()
    mock_response.choices = [
        Mock(message=Mock(content="Hello there!", tool_calls=None))
    ]
    
    with patch.object(provider._client.chat.completions, 'create', 
                     AsyncMock(return_value=mock_response)):
        response = await provider.run_conversation(sample_messages, sample_tools)
        
        assert response == "Hello there!"
        provider._client.chat.completions.create.assert_called_once_with(
            model=provider.config.model,
            messages=sample_messages,
            tools=provider._format_tools(sample_tools)
        )


@pytest.mark.asyncio
async def test_run_conversation_with_tool_call(provider, sample_tools, sample_tool_calls):
    """Test running a conversation with tool calls."""
    messages = [{"role": "user", "content": "Use the tool"}]
    
    # Mock the tool call response
    tool_call = Mock()
    tool_call.id = sample_tool_calls["test_tool"]["id"]
    tool_call.function.name = sample_tool_calls["test_tool"]["name"]
    tool_call.function.arguments = json.dumps(sample_tool_calls["test_tool"]["parameters"])
    
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
    
    with patch.object(provider._client.chat.completions, 'create', 
                     AsyncMock(side_effect=mock_responses)):
        response = await provider.run_conversation(messages, sample_tools)
        
        assert response == "Tool used successfully"
        assert len(provider._client.chat.completions.create.mock_calls) == 2


@pytest.mark.asyncio
async def test_run_conversation_tool_error(provider, sample_tools, sample_tool_calls, sample_tool_results):
    """Test handling of tool execution errors."""
    messages = [{"role": "user", "content": "Use the tool"}]
    
    # Mock the tool call response
    tool_call = Mock()
    tool_call.id = sample_tool_calls["test_tool"]["id"]
    tool_call.function.name = sample_tool_calls["test_tool"]["name"]
    tool_call.function.arguments = json.dumps(sample_tool_calls["test_tool"]["parameters"])
    
    mock_response = Mock(choices=[
        Mock(message=Mock(
            content=None,
            tool_calls=[tool_call]
        ))
    ])
    
    # Configure executor with error handler
    error_handler = Mock(side_effect=Exception(sample_tool_results["test_tool"]["error"]))
    provider.executor.register_handler("test_tool", error_handler)
    
    with patch.object(provider._client.chat.completions, 'create',
                     AsyncMock(return_value=mock_response)):
        with pytest.raises(ProviderError) as exc:
            await provider.run_conversation(messages, sample_tools)
        assert "Error in OpenAI conversation" in str(exc.value) 