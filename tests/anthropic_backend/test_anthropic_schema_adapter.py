"""Unit tests for Anthropic schema adapter."""

from anthropic.types import Message
from mcp.types import Tool as MCPTool

from agentical.anthropic_backend.schema_adapter import SchemaAdapter


def test_extract_answer():
    """Test extracting answers from text."""
    adapter = SchemaAdapter()

    # Test with answer tags
    text = "Some prefix <answer>The actual answer</answer> some suffix"
    assert adapter.extract_answer(text) == "The actual answer"

    # Test with multiline answer
    text = """Some prefix
<answer>
Line 1
Line 2
</answer>
some suffix"""
    assert adapter.extract_answer(text) == "Line 1\nLine 2"

    # Test without answer tags
    text = "Just plain text"
    assert adapter.extract_answer(text) == "Just plain text"

    # Test with empty answer tags
    text = "Some text <answer></answer> more text"
    assert adapter.extract_answer(text) == ""


def test_clean_schema():
    """Test cleaning JSON schemas for Anthropic compatibility."""
    adapter = SchemaAdapter()

    # Test basic schema cleaning
    schema = {
        "type": "object",
        "title": "Test Schema",  # Should be removed
        "properties": {
            "name": {
                "type": "string",
                "description": "A name",
                "default": "test",  # Should be removed
            }
        },
        "required": ["name"],
        "$schema": "http://json-schema.org/draft-07/schema#",  # Should be removed
        "additionalProperties": False,  # Should be removed
    }

    cleaned = adapter.clean_schema(schema)
    assert "title" not in cleaned
    assert "$schema" not in cleaned
    assert "additionalProperties" not in cleaned
    assert cleaned["type"] == "object"
    assert "name" in cleaned["properties"]
    assert "default" not in cleaned["properties"]["name"]
    assert cleaned["properties"]["name"]["description"] == "A name"

    # Test nested object cleaning
    nested_schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "title": "User",  # Should be removed
                "properties": {
                    "id": {"type": "integer"},
                    "settings": {
                        "type": "object",
                        "default": {},  # Should be removed
                        "properties": {"theme": {"type": "string"}},
                    },
                },
            }
        },
    }

    cleaned = adapter.clean_schema(nested_schema)
    assert "title" not in cleaned["properties"]["user"]
    assert "default" not in cleaned["properties"]["user"]["properties"]["settings"]

    # Test array schema cleaning
    array_schema = {
        "type": "array",
        "title": "Array Schema",  # Should be removed
        "items": {
            "type": "object",
            "properties": {
                "value": {"type": "string", "default": ""}  # default should be removed
            },
        },
    }

    cleaned = adapter.clean_schema(array_schema)
    assert "title" not in cleaned
    assert "default" not in cleaned["items"]["properties"]["value"]


def test_convert_mcp_tools_to_anthropic():
    """Test converting MCP tools to Anthropic format."""
    adapter = SchemaAdapter()

    tools = [
        MCPTool(
            name="test_tool",
            description="A test tool",
            parameters={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "First parameter"},
                    "param2": {"type": "integer"},
                },
                "required": ["param1"],
            },
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "First parameter"},
                    "param2": {"type": "integer"},
                },
                "required": ["param1"],
            },
        )
    ]

    anthropic_tools = adapter.convert_mcp_tools_to_anthropic(tools)
    assert len(anthropic_tools) == 1

    tool = anthropic_tools[0]
    assert tool["type"] == "custom"
    assert tool["name"] == "test_tool"
    assert tool["description"] == "A test tool"
    assert "input_schema" in tool
    assert tool["input_schema"]["type"] == "object"
    assert "param1" in tool["input_schema"]["properties"]
    assert "param2" in tool["input_schema"]["properties"]
    assert tool["input_schema"]["required"] == ["param1"]


def test_create_user_message():
    """Test creating user messages."""
    adapter = SchemaAdapter()

    message = adapter.create_user_message("Test query")
    assert message["role"] == "user"
    assert len(message["content"]) == 1
    assert message["content"][0]["type"] == "text"
    assert message["content"][0]["text"] == "Test query"


def test_create_system_message():
    """Test creating system messages."""
    adapter = SchemaAdapter()

    message = adapter.create_system_message("System instruction")
    assert len(message) == 1
    assert message[0]["type"] == "text"
    assert message[0]["text"] == "System instruction"


def test_create_assistant_message():
    """Test creating assistant messages."""
    adapter = SchemaAdapter()

    message = adapter.create_assistant_message("Assistant response")
    assert message["role"] == "assistant"
    assert len(message["content"]) == 1
    assert message["content"][0]["type"] == "text"
    assert message["content"][0]["text"] == "Assistant response"


def test_create_tool_response_message():
    """Test creating tool response messages."""
    adapter = SchemaAdapter()

    # Test successful tool response
    success_msg = adapter.create_tool_response_message("test_tool", result="Success")
    assert success_msg["role"] == "user"
    assert "Tool test_tool returned: Success" in success_msg["content"][0]["text"]

    # Test error tool response
    error_msg = adapter.create_tool_response_message("test_tool", error="Failed")
    assert error_msg["role"] == "user"
    assert "Tool test_tool error: Failed" in error_msg["content"][0]["text"]


def test_extract_tool_calls():
    """Test extracting tool calls from Anthropic messages."""
    adapter = SchemaAdapter()

    # Create a mock Message with tool calls
    message = Message(
        id="test_id",
        model="claude-3",
        role="assistant",
        type="message",
        content=[
            {"type": "text", "text": "I will use a tool"},
            {
                "type": "tool_use",
                "id": "call_1",
                "name": "test_tool",
                "input": {"param": "value"},
            },
        ],
        usage={"input_tokens": 10, "output_tokens": 20},
    )

    tool_calls = adapter.extract_tool_calls(message)
    assert len(tool_calls) == 1
    assert tool_calls[0] == ("test_tool", {"param": "value"})

    # Test message without tool calls
    message = Message(
        id="test_id",
        model="claude-3",
        role="assistant",
        type="message",
        content=[{"type": "text", "text": "No tool calls"}],
        usage={"input_tokens": 10, "output_tokens": 20},
    )

    tool_calls = adapter.extract_tool_calls(message)
    assert len(tool_calls) == 0


def test_clean_schema_edge_cases():
    """Test schema cleaning with edge cases."""
    adapter = SchemaAdapter()

    # Test empty schema
    assert adapter.clean_schema({}) == {}

    # Test schema with only unsupported fields
    schema = {
        "title": "Test",
        "$schema": "http://json-schema.org/draft-07/schema#",
        "additionalProperties": False,
    }
    assert adapter.clean_schema(schema) == {}

    # Test schema with nested arrays
    schema = {
        "type": "array",
        "items": {
            "type": "array",
            "items": {
                "type": "string",
                "default": "",  # Should be removed
            },
        },
    }
    cleaned = adapter.clean_schema(schema)
    assert cleaned["type"] == "array"
    assert cleaned["items"]["type"] == "array"
    assert "default" not in cleaned["items"]["items"]


def test_convert_mcp_tools_to_anthropic_edge_cases():
    """Test tool conversion with edge cases."""
    adapter = SchemaAdapter()

    # Test empty tool list
    assert adapter.convert_mcp_tools_to_anthropic([]) == []

    # Test tool without parameters
    tool = MCPTool(
        name="no_params",
        description="Tool without parameters",
        parameters={},
        inputSchema={},
    )
    result = adapter.convert_mcp_tools_to_anthropic([tool])
    assert len(result) == 1
    assert result[0]["input_schema"]["properties"] == {}
