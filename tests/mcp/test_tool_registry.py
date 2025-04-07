"""Unit tests for ToolRegistry.

This module contains tests for the ToolRegistry class, which manages
tool registration and lookup across different MCP servers.
"""

import pytest
from mcp.types import Tool as MCPTool

from agentical.mcp.tool_registry import ToolRegistry


@pytest.fixture
def mock_tools() -> list[MCPTool]:
    """Fixture providing mock MCP tools."""
    return [
        MCPTool(
            name="tool1",
            description="Tool 1",
            parameters={},
            inputSchema={"type": "object", "properties": {}},
        ),
        MCPTool(
            name="tool2",
            description="Tool 2",
            parameters={},
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@pytest.fixture
def registry() -> ToolRegistry:
    """Fixture providing a clean ToolRegistry instance."""
    return ToolRegistry()


def test_registry_initialization(registry):
    """Test ToolRegistry initialization."""
    assert registry.tools_by_server == {}
    assert registry.all_tools == []


def test_register_server_tools(registry, mock_tools):
    """Test registering tools for a server."""
    # Register tools for first server
    registry.register_server_tools("server1", mock_tools)
    assert "server1" in registry.tools_by_server
    assert len(registry.tools_by_server["server1"]) == 2
    assert len(registry.all_tools) == 2

    # Register tools for second server
    registry.register_server_tools("server2", mock_tools)
    assert "server2" in registry.tools_by_server
    assert len(registry.tools_by_server["server2"]) == 2
    assert len(registry.all_tools) == 4  # Combined tools from both servers

    # Re-register tools for first server (should replace)
    new_tools = [mock_tools[0]]  # Just one tool
    registry.register_server_tools("server1", new_tools)
    assert len(registry.tools_by_server["server1"]) == 1
    assert len(registry.all_tools) == 3  # One from server1, two from server2


def test_remove_server_tools(registry, mock_tools):
    """Test removing tools for a server."""
    # Setup initial state
    registry.register_server_tools("server1", mock_tools)
    registry.register_server_tools("server2", mock_tools)

    # Remove server1's tools
    num_removed = registry.remove_server_tools("server1")
    assert num_removed == 2
    assert "server1" not in registry.tools_by_server
    assert "server2" in registry.tools_by_server
    assert len(registry.all_tools) == 2  # Only server2's tools remain

    # Try removing nonexistent server
    num_removed = registry.remove_server_tools("nonexistent")
    assert num_removed == 0
    assert len(registry.all_tools) == 2  # No change


def test_find_tool_server(registry, mock_tools):
    """Test finding which server hosts a tool."""
    registry.register_server_tools("server1", [mock_tools[0]])
    registry.register_server_tools("server2", [mock_tools[1]])

    # Find existing tools
    assert registry.find_tool_server("tool1") == "server1"
    assert registry.find_tool_server("tool2") == "server2"

    # Try finding nonexistent tool
    assert registry.find_tool_server("nonexistent") is None


def test_clear_registry(registry, mock_tools):
    """Test clearing all tools from the registry."""
    # Setup initial state
    registry.register_server_tools("server1", mock_tools)
    registry.register_server_tools("server2", mock_tools)

    # Clear registry
    num_tools, num_servers = registry.clear()
    assert num_tools == 4  # Total tools before clearing
    assert num_servers == 2  # Total servers before clearing
    assert registry.tools_by_server == {}
    assert registry.all_tools == []


def test_get_server_tools(registry, mock_tools):
    """Test getting tools for a specific server."""
    registry.register_server_tools("server1", mock_tools)

    # Get tools for existing server
    tools = registry.get_server_tools("server1")
    assert len(tools) == 2
    assert tools == mock_tools

    # Get tools for nonexistent server
    tools = registry.get_server_tools("nonexistent")
    assert tools == []
