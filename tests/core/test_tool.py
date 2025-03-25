"""Tests for the tool module."""

from typing import Dict, Any

import pytest

from agentical.types import Tool, ToolParameter
from agentical.core.tool import to_openai_format, to_anthropic_format


def create_test_tool(
    name: str = "test_tool",
    description: str = "A test tool",
    parameters: Dict[str, ToolParameter] = None
) -> Tool:
    """Helper function to create a test tool with given parameters."""
    if parameters is None:
        parameters = {
            "param1": ToolParameter(
                type="string",
                description="A test parameter",
                required=True
            )
        }
    return Tool(name=name, description=description, parameters=parameters)


def test_to_openai_format_basic() -> None:
    """Test basic OpenAI format conversion."""
    tool = create_test_tool()
    result = to_openai_format(tool)
    
    assert result["type"] == "function"
    assert result["function"]["name"] == "test_tool"
    assert result["function"]["description"] == "A test tool"
    assert result["function"]["parameters"]["type"] == "object"
    assert "param1" in result["function"]["parameters"]["properties"]
    assert result["function"]["parameters"]["required"] == ["param1"]


def test_to_openai_format_multiple_params() -> None:
    """Test OpenAI format with multiple parameters."""
    tool = create_test_tool(parameters={
        "param1": ToolParameter(type="string", description="First param", required=True),
        "param2": ToolParameter(type="integer", description="Second param", required=False),
        "param3": ToolParameter(type="boolean", description="Third param", required=True)
    })
    
    result = to_openai_format(tool)
    properties = result["function"]["parameters"]["properties"]
    
    assert len(properties) == 3
    assert properties["param1"]["type"] == "string"
    assert properties["param2"]["type"] == "integer"
    assert properties["param3"]["type"] == "boolean"
    assert set(result["function"]["parameters"]["required"]) == {"param1", "param3"}


def test_to_openai_format_with_enum() -> None:
    """Test OpenAI format with enum parameters."""
    tool = create_test_tool(parameters={
        "choice": ToolParameter(
            type="string",
            description="A choice parameter",
            required=True,
            enum=["option1", "option2", "option3"]
        )
    })
    
    result = to_openai_format(tool)
    choice_param = result["function"]["parameters"]["properties"]["choice"]
    
    assert "enum" in choice_param
    assert choice_param["enum"] == ["option1", "option2", "option3"]


def test_to_anthropic_format_basic() -> None:
    """Test basic Anthropic format conversion."""
    tool = create_test_tool()
    result = to_anthropic_format(tool)
    
    assert result["name"] == "test_tool"
    assert result["description"] == "A test tool"
    assert result["input_schema"]["type"] == "object"
    assert "param1" in result["input_schema"]["properties"]
    assert result["input_schema"]["required"] == ["param1"]


def test_to_anthropic_format_multiple_params() -> None:
    """Test Anthropic format with multiple parameters."""
    tool = create_test_tool(parameters={
        "param1": ToolParameter(type="string", description="First param", required=True),
        "param2": ToolParameter(type="integer", description="Second param", required=False),
        "param3": ToolParameter(type="boolean", description="Third param", required=True)
    })
    
    result = to_anthropic_format(tool)
    properties = result["input_schema"]["properties"]
    
    assert len(properties) == 3
    assert properties["param1"]["type"] == "string"
    assert properties["param2"]["type"] == "integer"
    assert properties["param3"]["type"] == "boolean"
    assert set(result["input_schema"]["required"]) == {"param1", "param3"}


def test_to_anthropic_format_with_enum() -> None:
    """Test Anthropic format with enum parameters."""
    tool = create_test_tool(parameters={
        "choice": ToolParameter(
            type="string",
            description="A choice parameter",
            required=True,
            enum=["option1", "option2", "option3"]
        )
    })
    
    result = to_anthropic_format(tool)
    choice_param = result["input_schema"]["properties"]["choice"]
    
    assert "enum" in choice_param
    assert choice_param["enum"] == ["option1", "option2", "option3"]


def test_complex_tool_conversion() -> None:
    """Test converting a complex tool with various parameter types and requirements."""
    tool = Tool(
        name="complex_tool",
        description="A complex tool with various parameters",
        parameters={
            "string_param": ToolParameter(
                type="string",
                description="A string parameter",
                required=True
            ),
            "int_param": ToolParameter(
                type="integer",
                description="An integer parameter",
                required=False
            ),
            "enum_param": ToolParameter(
                type="string",
                description="An enum parameter",
                required=True,
                enum=["a", "b", "c"]
            ),
            "bool_param": ToolParameter(
                type="boolean",
                description="A boolean parameter",
                required=False
            )
        }
    )
    
    # Test OpenAI format
    openai_result = to_openai_format(tool)
    assert openai_result["function"]["name"] == "complex_tool"
    assert len(openai_result["function"]["parameters"]["properties"]) == 4
    assert set(openai_result["function"]["parameters"]["required"]) == {"string_param", "enum_param"}
    
    # Test Anthropic format
    anthropic_result = to_anthropic_format(tool)
    assert anthropic_result["name"] == "complex_tool"
    assert len(anthropic_result["input_schema"]["properties"]) == 4
    assert set(anthropic_result["input_schema"]["required"]) == {"string_param", "enum_param"} 