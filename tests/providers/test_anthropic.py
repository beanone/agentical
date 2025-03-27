"""Tests for Anthropic provider implementation."""

import pytest
from unittest.mock import Mock, patch, AsyncMock, call
import json

from agentical.core import ProviderConfig, ToolExecutor, Tool, ToolParameter, ProviderError, ProviderSettings
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
        ),
        base_tool(
            name="another_tool",
            description="Another test tool",
            parameters={
                "param3": base_tool_parameter(
                    param_type="boolean",
                    description="Boolean parameter",
                    required=True,
                    default=False
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
    config = ProviderConfig.from_settings("anthropic", ProviderSettings(anthropic_api_key="test-key"))
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
    
    assert len(formatted) == 2
    
    # Test first tool
    tool1 = formatted[0]
    assert tool1["type"] == "custom"
    assert tool1["name"] == "test_tool"
    assert tool1["description"] == "A test tool"
    
    params1 = tool1["input_schema"]
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
    assert tool2["type"] == "custom"
    assert tool2["name"] == "another_tool"
    assert tool2["description"] == "Another test tool"
    
    params2 = tool2["input_schema"]
    assert params2["type"] == "object"
    assert "param3" in params2["properties"]
    assert params2["properties"]["param3"]["type"] == "boolean"
    assert "param3" in params2["required"]


@pytest.mark.asyncio
async def test_run_conversation_simple(provider, sample_tools):
    """Test running a simple conversation without tool calls."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"}
    ]
    
    mock_response = Mock()
    mock_response.content = [
        Mock(type='text', text="I'm doing great! How can I help you today?")
    ]
    
    with patch.object(provider._client.messages, 'create', 
                     AsyncMock(return_value=mock_response)):
        response = await provider.run_conversation(messages, sample_tools)
        
        assert response == "I'm doing great! How can I help you today?"
        provider._client.messages.create.assert_called_once()
        call_args = provider._client.messages.create.call_args[1]
        
        assert call_args["model"] == provider.config.model
        assert call_args["system"] == "You are a helpful assistant."
        assert len(call_args["messages"]) == 3  # Excluding system message
        assert call_args["tools"] == provider._format_tools(sample_tools)


@pytest.mark.asyncio
async def test_run_conversation_with_tool_call(provider, sample_tools, executor):
    """Test running a conversation with tool calls."""
    messages = [{"role": "user", "content": "Use the test tool"}]

    # First response with tool use
    first_response = Mock()
    mock_tool_use = Mock(
        type='tool_use',
        id='call_123',
        input={"param1": "test_value"}
    )
    mock_tool_use.name = 'test_tool'  # Set name as string directly
    first_response.content = [
        Mock(type='text', text="I'll help you with that."),
        mock_tool_use
    ]

    # Second response after tool execution
    second_response = Mock()
    second_response.content = [
        Mock(type='text', text="The tool returned: Tool result")
    ]

    mock_responses = [first_response, second_response]

    # Mock the tool execution
    executor.execute_tool = AsyncMock(return_value="Tool result")

    with patch.object(provider._client.messages, 'create',
                     AsyncMock(side_effect=mock_responses)):
        response = await provider.run_conversation(messages, sample_tools)

        assert response == "The tool returned: Tool result"
        assert provider._client.messages.create.call_count == 2

        # Verify tool execution
        executor.execute_tool.assert_called_once_with(
            'test_tool',  # Use string directly
            {"param1": "test_value"}
        )


@pytest.mark.asyncio
async def test_run_conversation_with_multiple_tools(provider, sample_tools, executor):
    """Test running a conversation with multiple tool calls."""
    messages = [{"role": "user", "content": "Use both tools"}]

    # First response with first tool use
    first_response = Mock()
    mock_tool_use1 = Mock(
        type='tool_use',
        id='call_123',
        input={"param1": "test_value"}
    )
    mock_tool_use1.name = 'test_tool'  # Set name as string directly
    first_response.content = [
        Mock(type='text', text="Using first tool"),
        mock_tool_use1
    ]

    # Second response with second tool use
    second_response = Mock()
    mock_tool_use2 = Mock(
        type='tool_use',
        id='call_456',
        input={"param3": True}
    )
    mock_tool_use2.name = 'another_tool'  # Set name as string directly
    second_response.content = [
        Mock(type='text', text="Using second tool"),
        mock_tool_use2
    ]

    # Final response
    final_response = Mock()
    final_response.content = [
        Mock(type='text', text="All tools executed successfully")
    ]

    mock_responses = [first_response, second_response, final_response]

    # Mock the tool executions
    tool_results = ["First tool result", "Second tool result"]
    executor.execute_tool = AsyncMock(side_effect=tool_results)

    with patch.object(provider._client.messages, 'create',
                     AsyncMock(side_effect=mock_responses)):
        response = await provider.run_conversation(messages, sample_tools)

        assert response == "All tools executed successfully"
        assert provider._client.messages.create.call_count == 3

        # Verify tool executions
        assert executor.execute_tool.call_count == 2
        executor.execute_tool.assert_has_calls([
            call('test_tool', {"param1": "test_value"}),  # Use string directly
            call('another_tool', {"param3": True})
        ])


@pytest.mark.asyncio
async def test_run_conversation_error(provider, sample_tools):
    """Test error handling in conversation."""
    messages = [{"role": "user", "content": "Hello"}]
    
    with patch.object(provider._client.messages, 'create',
                     AsyncMock(side_effect=Exception("API error"))):
        with pytest.raises(ProviderError) as exc:
            await provider.run_conversation(messages, sample_tools)
        assert "Error in Anthropic conversation" in str(exc.value)


@pytest.mark.asyncio
async def test_run_conversation_tool_error(provider, sample_tools, executor):
    """Test handling of tool execution errors."""
    messages = [{"role": "user", "content": "Use the tool"}]
    
    # Response with tool use
    mock_response = Mock()
    mock_response.content = [
        Mock(type='text', text="Let me try that"),
        Mock(
            type='tool_use',
            id='call_123',
            name='test_tool',
            input={"param1": "test_value"}
        )
    ]
    
    # Mock tool execution to raise an error
    executor.execute_tool = AsyncMock(side_effect=Exception("Tool execution failed"))
    
    with patch.object(provider._client.messages, 'create',
                     AsyncMock(return_value=mock_response)):
        with pytest.raises(ProviderError) as exc:
            await provider.run_conversation(messages, sample_tools)
        assert "Error in Anthropic conversation" in str(exc.value) 