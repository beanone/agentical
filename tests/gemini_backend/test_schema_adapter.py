"""Unit tests for Gemini schema adapter."""

import pytest
from google.genai.types import (
    Content,
    Part,
    Schema,
)
from google.genai.types import (
    Tool as GeminiTool,
)
from mcp.types import CallToolResult, TextContent
from mcp.types import Tool as MCPTool

from agentical.gemini_backend.schema_adapter import SchemaAdapter


@pytest.fixture
def schema_adapter():
    """Fixture providing a SchemaAdapter instance."""
    return SchemaAdapter()


def test_clean_schema_removes_unsupported_fields():
    """Test that clean_schema removes unsupported fields."""
    input_schema = {
        "title": "Test Schema",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "default": 0},
        },
        "$schema": "http://json-schema.org/draft-07/schema#",
        "additionalProperties": False,
    }

    cleaned = SchemaAdapter.clean_schema(input_schema)

    assert "title" not in cleaned
    assert "$schema" not in cleaned
    assert "additionalProperties" not in cleaned
    assert cleaned["type"] == "object"
    assert "properties" in cleaned
    assert cleaned["properties"]["name"]["type"] == "string"
    assert "default" not in cleaned["properties"]["age"]


def test_clean_schema_handles_nested_objects():
    """Test that clean_schema handles nested object structures."""
    input_schema = {
        "type": "object",
        "properties": {
            "user": {
                "type": "object",
                "title": "User",
                "properties": {
                    "name": {"type": "string"},
                    "settings": {
                        "type": "object",
                        "title": "Settings",
                        "properties": {"theme": {"type": "string"}},
                    },
                },
            }
        },
    }

    cleaned = SchemaAdapter.clean_schema(input_schema)

    assert "title" not in cleaned["properties"]["user"]
    assert "title" not in cleaned["properties"]["user"]["properties"]["settings"]
    assert (
        cleaned["properties"]["user"]["properties"]["settings"]["properties"]["theme"][
            "type"
        ]
        == "string"
    )


def test_clean_schema_handles_arrays():
    """Test that clean_schema handles array types properly."""
    input_schema = {
        "type": "object",
        "properties": {
            "tags": {"type": "array", "items": {"type": "string", "title": "Tag"}},
            "records": {
                "type": "array",
                "items": {
                    "type": "object",
                    "title": "Record",
                    "properties": {"id": {"type": "string"}},
                },
            },
        },
    }

    cleaned = SchemaAdapter.clean_schema(input_schema)

    assert "title" not in cleaned["properties"]["tags"]["items"]
    assert "title" not in cleaned["properties"]["records"]["items"]
    assert (
        cleaned["properties"]["records"]["items"]["properties"]["id"]["type"]
        == "string"
    )


def test_clean_schema_preserves_required_fields():
    """Test that clean_schema preserves and validates required fields."""
    input_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string"},
            "age": {"type": "integer"},
        },
        "required": ["name", "email"],
    }

    cleaned = SchemaAdapter.clean_schema(input_schema)

    assert "required" in cleaned
    assert set(cleaned["required"]) == {"name", "email"}


def test_convert_mcp_tool_to_gemini():
    """Test conversion of MCP tool to Gemini format."""
    mcp_tool = MCPTool(
        name="test_tool",
        description="A test tool",
        parameters={},
        inputSchema={
            "type": "object",
            "properties": {"param1": {"type": "string"}, "param2": {"type": "integer"}},
            "required": ["param1"],
        },
    )

    gemini_tool = SchemaAdapter.convert_mcp_tool_to_gemini(mcp_tool)

    assert isinstance(gemini_tool, GeminiTool)
    assert len(gemini_tool.function_declarations) == 1
    func_decl = gemini_tool.function_declarations[0]
    assert func_decl.name == "test_tool"
    assert func_decl.description == "A test tool"
    assert isinstance(func_decl.parameters, Schema)
    # Verify schema structure through the schema's properties
    schema = func_decl.parameters
    assert "param1" in schema.properties
    assert "param2" in schema.properties
    assert "param1" in schema.required


def test_convert_mcp_tool_to_gemini_empty_params():
    """Test conversion of MCP tool with empty parameters."""
    mcp_tool = MCPTool(
        name="test_tool",
        description="A test tool",
        parameters={},
        inputSchema={"type": "object", "properties": {}},
    )

    gemini_tool = SchemaAdapter.convert_mcp_tool_to_gemini(mcp_tool)

    assert isinstance(gemini_tool, GeminiTool)
    assert len(gemini_tool.function_declarations) == 1
    func_decl = gemini_tool.function_declarations[0]
    schema = func_decl.parameters
    assert "random_string" in schema.properties


def test_create_user_content():
    """Test creation of user content."""
    query = "Test query"
    content = SchemaAdapter.create_user_content(query)

    assert isinstance(content, Content)
    assert content.role == "user"
    assert len(content.parts) == 1
    assert isinstance(content.parts[0], Part)
    assert content.parts[0].text == query


def test_create_tool_response_content_success():
    """Test creation of tool response content for successful execution."""
    function_call_part = Part(
        function_call={"name": "test_tool", "args": {"param": "value"}}
    )
    result = CallToolResult(content=[TextContent(type="text", text="Success result")])

    contents = SchemaAdapter.create_tool_response_content(
        function_call_part=function_call_part, tool_name="test_tool", result=result
    )

    assert len(contents) == 2
    assert contents[0].role == "assistant"
    assert contents[1].role == "tool"
    # Access the response content directly
    response = contents[1].parts[0].function_response
    assert response.name == "test_tool"
    assert isinstance(response.response, dict)
    assert len(response.response["items"]) == 1
    assert response.response["items"][0].text == "Success result"


def test_create_tool_response_content_error():
    """Test creation of tool response content for failed execution."""
    function_call_part = Part(
        function_call={"name": "test_tool", "args": {"param": "value"}}
    )

    contents = SchemaAdapter.create_tool_response_content(
        function_call_part=function_call_part, tool_name="test_tool", error="Test error"
    )

    assert len(contents) == 2
    assert contents[0].role == "assistant"
    assert contents[1].role == "tool"
    # Access the response content directly
    response = contents[1].parts[0].function_response
    assert response.name == "test_tool"
    assert isinstance(response.response, dict)
    assert response.response["error"] == "Test error"


def test_create_tool_response_content_list_result():
    """Test creation of tool response content for list results."""
    function_call_part = Part(
        function_call={"name": "test_tool", "args": {"param": "value"}}
    )
    result = CallToolResult(
        content=[
            TextContent(type="text", text="item1"),
            TextContent(type="text", text="item2"),
        ]
    )

    contents = SchemaAdapter.create_tool_response_content(
        function_call_part=function_call_part, tool_name="test_tool", result=result
    )

    assert len(contents) == 2
    # Access the response content directly
    response = contents[1].parts[0].function_response
    assert response.name == "test_tool"
    assert isinstance(response.response, dict)
    assert len(response.response["items"]) == 2
    assert response.response["items"][0].text == "item1"
    assert response.response["items"][1].text == "item2"


def test_extract_tool_call():
    """Test extraction of tool call details."""
    part = Part(function_call={"name": "test_tool", "args": {"param": "value"}})

    result = SchemaAdapter.extract_tool_call(part)

    assert result is not None
    tool_name, tool_args = result
    assert tool_name == "test_tool"
    assert tool_args == {"param": "value"}


def test_extract_tool_call_no_function_call():
    """Test extraction of tool call details when no function call exists."""
    part = Part(text="Not a function call")

    result = SchemaAdapter.extract_tool_call(part)

    assert result is None
