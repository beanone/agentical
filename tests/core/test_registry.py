"""Tests for the ToolRegistry class."""

import pytest
from typing import Dict, Any

from agentical.core import ToolRegistry
from agentical.core.types import Tool, ToolParameter


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