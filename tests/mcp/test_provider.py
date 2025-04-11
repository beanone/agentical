"""Unit tests for MCPToolProvider.

This module contains tests for the MCPToolProvider class, which serves as the main
integration layer between LLM backends and MCP tools.
"""

from contextlib import AsyncExitStack
from unittest.mock import AsyncMock, Mock, patch

import pytest
from mcp.types import CallToolResult
from mcp.types import Tool as MCPTool
from mcp.types import Resource as MCPResource
from mcp.types import Prompt as MCPPrompt

from agentical.api import LLMBackend
from agentical.mcp.config import DictBasedMCPConfigProvider
from agentical.mcp.provider import MCPToolProvider
from agentical.mcp.schemas import ServerConfig


class MockClientSession:
    """Mock implementation of ClientSession."""

    def __init__(self, tools=None, server_name=None):
        self.tools = tools or []
        self.server_name = server_name
        self.closed = False
        self.list_tools = AsyncMock(return_value=Mock(tools=self.tools))
        self.list_resources = AsyncMock(return_value=Mock(resources=[]))
        self.list_prompts = AsyncMock(return_value=Mock(prompts=[]))
        self.call_tool = AsyncMock(
            return_value=CallToolResult(
                result="success",
                content=[{"type": "text", "text": "Tool execution successful"}],
            )
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.closed = True


@pytest.fixture
def mock_llm_backend():
    """Fixture providing a mock LLM backend."""
    backend = Mock(spec=LLMBackend)
    backend.process_query = AsyncMock()
    return backend


@pytest.fixture
def valid_server_configs():
    """Fixture providing valid server configurations."""
    return {
        "server1": ServerConfig(command="cmd1", args=["--arg1"], env={"ENV1": "val1"}),
        "server2": ServerConfig(command="cmd2", args=["--arg2"], env={"ENV2": "val2"}),
    }


@pytest.fixture
def mock_mcp_tools():
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
def mock_session(mock_mcp_tools):
    """Fixture providing a mock MCP session factory."""

    def create_session(server_name=None):
        return MockClientSession(tools=mock_mcp_tools.copy(), server_name=server_name)

    return create_session


@pytest.fixture
async def mock_exit_stack():
    """Fixture providing a mock AsyncExitStack."""
    async with AsyncExitStack() as stack:
        yield stack


@pytest.mark.asyncio
async def test_provider_initialization(mock_llm_backend, valid_server_configs):
    """Test MCPToolProvider initialization."""
    # Test with server configs
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    assert isinstance(provider.config_provider, DictBasedMCPConfigProvider)
    assert provider.llm_backend == mock_llm_backend

    # Test with invalid backend
    with pytest.raises(TypeError, match="must be an instance of LLMBackend"):
        MCPToolProvider("invalid_backend", server_configs=valid_server_configs)

    # Test with no configuration source
    with pytest.raises(
        ValueError, match="Either config_provider or server_configs must be provided"
    ):
        MCPToolProvider(mock_llm_backend)


@pytest.mark.asyncio
async def test_provider_initialize(mock_llm_backend, valid_server_configs):
    """Test provider initialization with configurations."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    await provider.initialize()

    assert provider.available_servers == valid_server_configs
    assert len(provider.list_available_servers()) == 2
    assert set(provider.list_available_servers()) == {"server1", "server2"}


@pytest.mark.asyncio
async def test_provider_tool_registration(
    mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack
):
    """Test tool registration when connecting to servers."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()

    with patch.object(
        provider.connection_service._connection_manager,
        "connect",
        side_effect=lambda name, config: mock_session(name),
    ):
        # Connect to a server
        await provider.mcp_connect("server1")

        # Verify tools were registered
        assert len(provider.tool_registry.all_tools) == 2
        assert provider.tool_registry.find_tool_server("tool1") == "server1"
        assert provider.tool_registry.find_tool_server("tool2") == "server1"


@pytest.mark.asyncio
async def test_provider_tool_cleanup(
    mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack
):
    """Test tool cleanup when disconnecting from servers."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()

    with patch.object(
        provider.connection_service._connection_manager,
        "connect",
        side_effect=lambda name, config: mock_session(name),
    ):
        # Connect to both servers
        await provider.mcp_connect("server1")
        await provider.mcp_connect("server2")
        assert len(provider.tool_registry.all_tools) == 4

        # Clean up one server
        await provider.cleanup_server("server1")
        assert len(provider.tool_registry.all_tools) == 2
        assert provider.tool_registry.find_tool_server("tool1") == "server2"
        assert provider.tool_registry.find_tool_server("tool2") == "server2"

        # Clean up all
        await provider.cleanup_all()
        assert len(provider.tool_registry.all_tools) == 0


@pytest.mark.asyncio
async def test_provider_query_processing(
    mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack
):
    """Test query processing with tool execution."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()

    with patch.object(
        provider.connection_service._connection_manager,
        "connect",
        side_effect=lambda name, config: mock_session(name),
    ):
        # Connect to a server
        await provider.mcp_connect("server1")

        # Process a query
        response = await provider.process_query("Test query")
        assert response is not None


@pytest.mark.asyncio
async def test_execute_tool_success(
    mock_llm_backend, valid_server_configs, mock_mcp_tools, mock_exit_stack
):
    """Test successful tool execution."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()

    # Create a session with tools
    session = MockClientSession(tools=mock_mcp_tools)

    with patch.object(
        provider.connection_service._connection_manager,
        "connect",
        side_effect=lambda name, config: session,
    ), patch.object(
        provider.connection_service,
        "get_session",
        return_value=session,
    ):
        # Connect to a server
        await provider.mcp_connect("server1")

        # Execute a tool
        result = await provider.execute_tool("tool1", {})
        assert result.result == "success"


@pytest.mark.asyncio
async def test_execute_tool_no_session(
    mock_llm_backend, valid_server_configs, mock_mcp_tools, mock_exit_stack
):
    """Test tool execution when no session exists."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()

    # Register tools directly in the registry to bypass session check
    provider.tool_registry.register_server_tools("server1", mock_mcp_tools)

    # Try to execute a tool without connecting
    with pytest.raises(ValueError, match="No session found for server"):
        await provider.execute_tool("tool1", {})


@pytest.mark.asyncio
async def test_execute_tool_not_found(
    mock_llm_backend, valid_server_configs, mock_mcp_tools, mock_exit_stack
):
    """Test tool execution when tool is not found."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()

    # Create a session with tools
    session = MockClientSession(tools=mock_mcp_tools)

    with patch.object(
        provider.connection_service._connection_manager,
        "connect",
        side_effect=lambda name, config: session,
    ):
        # Connect to a server
        await provider.mcp_connect("server1")

        # Try to execute a non-existent tool
        with pytest.raises(ValueError, match="Tool not found"):
            await provider.execute_tool("nonexistent_tool", {})


@pytest.mark.asyncio
async def test_execute_tool_session_error(
    mock_llm_backend, valid_server_configs, mock_mcp_tools, mock_exit_stack
):
    """Test tool execution when session encounters an error."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()

    # Create a session with tools that raises an error
    error_session = MockClientSession(tools=mock_mcp_tools)
    error_session.call_tool = AsyncMock(side_effect=Exception("Session error"))

    with patch.object(
        provider.connection_service._connection_manager,
        "connect",
        side_effect=lambda name, config: error_session,
    ), patch.object(
        provider.connection_service,
        "get_session",
        return_value=error_session,
    ):
        # Connect to a server
        await provider.mcp_connect("server1")

        # Try to execute a tool
        with pytest.raises(Exception, match="Session error"):
            await provider.execute_tool("tool1", {})
