"""Tests for the ToolRegistry class."""

import pytest
from typing import Dict, Any

from agentical.core import ToolRegistry
from agentical.types import Tool, ToolParameter


def test_register_tool() -> None:
    """Test registering a tool."""
    registry = ToolRegistry()
    
    # Create a test tool
    tool = Tool(
        name="test_tool",
        description="A test tool",
        parameters={
            "param1": ToolParameter(
                type="string",
                description="Test parameter",
                required=True
            )
        }
    )
    
    # Register the tool
    registry.register_tool(tool)
    
    # Verify tool is registered
    assert tool.name in registry._tools
    assert registry._tools[tool.name] == tool


def test_register_duplicate_tool() -> None:
    """Test that registering a duplicate tool raises an error."""
    registry = ToolRegistry()
    
    # Create a test tool
    tool = Tool(
        name="test_tool",
        description="A test tool",
        parameters={
            "param1": ToolParameter(
                type="string",
                description="Test parameter",
                required=True
            )
        }
    )
    
    # Register the tool once
    registry.register_tool(tool)
    
    # Try to register again
    with pytest.raises(ValueError):
        registry.register_tool(tool)


def test_get_tool() -> None:
    """Test getting a registered tool."""
    registry = ToolRegistry()
    
    # Create and register a test tool
    tool = Tool(
        name="test_tool",
        description="A test tool",
        parameters={
            "param1": ToolParameter(
                type="string",
                description="Test parameter",
                required=True
            )
        }
    )
    
    registry.register_tool(tool)
    
    # Get the tool
    retrieved_tool = registry.get_tool("test_tool")
    assert retrieved_tool == tool


def test_get_nonexistent_tool() -> None:
    """Test that getting a nonexistent tool raises an error."""
    registry = ToolRegistry()
    
    with pytest.raises(KeyError):
        registry.get_tool("nonexistent_tool")


def test_get_openai_tools() -> None:
    """Test getting tools in OpenAI format."""
    registry = ToolRegistry()
    
    # Create and register test tools
    tool1 = Tool(
        name="tool1",
        description="First test tool",
        parameters={
            "param1": ToolParameter(
                type="string",
                description="Test parameter 1",
                required=True
            )
        }
    )
    
    tool2 = Tool(
        name="tool2",
        description="Second test tool",
        parameters={
            "param2": ToolParameter(
                type="number",
                description="Test parameter 2",
                required=False
            )
        }
    )
    
    registry.register_tool(tool1)
    registry.register_tool(tool2)
    
    # Get OpenAI tools
    openai_tools = registry.to_openai_format()
    
    # Verify format
    assert len(openai_tools) == 2
    
    for tool in openai_tools:
        assert "type" in tool
        assert tool["type"] == "function"
        assert "function" in tool
        assert "name" in tool["function"]
        assert "description" in tool["function"]
        assert "parameters" in tool["function"]
        
        if tool["function"]["name"] == "tool1":
            assert tool["function"]["description"] == "First test tool"
            assert "param1" in tool["function"]["parameters"]["properties"]
            assert tool["function"]["parameters"]["required"] == ["param1"]
            
        elif tool["function"]["name"] == "tool2":
            assert tool["function"]["description"] == "Second test tool"
            assert "param2" in tool["function"]["parameters"]["properties"]
            assert tool["function"]["parameters"]["required"] == [] 