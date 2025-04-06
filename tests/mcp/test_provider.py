"""Unit tests for MCPToolProvider.

This module contains tests for the MCPToolProvider class, which serves as the main
integration layer between LLM backends and MCP tools.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, call
from typing import Dict, List
import asyncio
from contextlib import AsyncExitStack

from agentical.api import LLMBackend
from agentical.mcp.provider import MCPToolProvider
from agentical.mcp.config import DictBasedMCPConfigProvider
from agentical.mcp.schemas import ServerConfig
from agentical.mcp.connection import MCPConnectionManager
from mcp.types import Tool as MCPTool, CallToolResult

class MockClientSession:
    """Mock implementation of ClientSession."""
    def __init__(self, tools=None, server_name=None):
        self.tools = tools or []
        self.server_name = server_name
        self.closed = False
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.closed = True
    
    async def list_tools(self):
        return Mock(tools=self.tools)
    
    async def call_tool(self, tool_name, tool_args):
        return CallToolResult(result="success")

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
        "server1": ServerConfig(
            command="cmd1",
            args=["--arg1"],
            env={"ENV1": "val1"}
        ),
        "server2": ServerConfig(
            command="cmd2",
            args=["--arg2"],
            env={"ENV2": "val2"}
        )
    }

@pytest.fixture
def mock_mcp_tools():
    """Fixture providing mock MCP tools."""
    return [
        MCPTool(
            name="tool1",
            description="Tool 1",
            parameters={},
            inputSchema={"type": "object", "properties": {}}
        ),
        MCPTool(
            name="tool2",
            description="Tool 2",
            parameters={},
            inputSchema={"type": "object", "properties": {}}
        )
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
    with pytest.raises(ValueError, match="Either config_provider or server_configs must be provided"):
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
async def test_provider_connect(mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack):
    """Test connecting to a specific server."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()
    
    with patch.object(provider.connection_manager, 'connect', side_effect=lambda name, _: mock_session(name)):
        await provider.mcp_connect("server1")
        
        # Check tools are registered correctly
        server_tools = provider.tool_registry.get_server_tools("server1")
        assert len(server_tools) == 2
        assert len(provider.tool_registry.all_tools) == 2
        
        # Test invalid server name
        with pytest.raises(ValueError, match="must be a non-empty string"):
            await provider.mcp_connect("")
        
        with pytest.raises(ValueError, match="Unknown server"):
            await provider.mcp_connect("nonexistent")

@pytest.mark.asyncio
async def test_provider_connect_all(mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack):
    """Test connecting to all servers."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()
    
    with patch.object(provider.connection_manager, 'connect', side_effect=lambda name, _: mock_session(name)):
        results = await provider.mcp_connect_all()
        
        assert len(results) == 2
        assert all(error is None for _, error in results)
        assert len(provider.tool_registry.tools_by_server) == 2
        assert len(provider.tool_registry.all_tools) == 4  # 2 tools per server

@pytest.mark.asyncio
async def test_provider_reconnect(mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack):
    """Test server reconnection functionality."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()
    
    with patch.object(provider.connection_manager, 'connect', side_effect=lambda name, _: mock_session(name)):
        # Test successful reconnection
        success = await provider.reconnect("server1")
        assert success
        assert len(provider.tool_registry.get_server_tools("server1")) == 2
        
        # Test reconnection to unknown server
        success = await provider.reconnect("nonexistent")
        assert not success

@pytest.mark.asyncio
async def test_provider_cleanup(mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack):
    """Test cleanup functionality."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()
    
    try:
        with patch.object(provider.connection_manager, 'connect', side_effect=lambda name, _: mock_session(name)):
            # Connect to servers
            await provider.mcp_connect_all()
            
            # Verify initial state
            assert len(provider.tool_registry.tools_by_server) == 2
            assert len(provider.tool_registry.all_tools) == 4  # 2 tools per server
            
            # Test single server cleanup
            await provider.cleanup("server1")
            assert not provider.tool_registry.get_server_tools("server1")
            assert len(provider.tool_registry.get_server_tools("server2")) == 2
            assert len(provider.tool_registry.all_tools) == 2  # Only server2's tools remain
            
            # Test cleanup all
            await provider.cleanup_all()
            assert not provider.tool_registry.tools_by_server
            assert not provider.tool_registry.all_tools
    finally:
        # Ensure health monitor is stopped
        if provider.health_monitor._monitor_task and not provider.health_monitor._monitor_task.done():
            provider.health_monitor.stop_monitoring()
            try:
                await provider.health_monitor._monitor_task
            except asyncio.CancelledError:
                pass

@pytest.mark.asyncio
async def test_process_query(mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack):
    """Test query processing functionality."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()
    
    with patch.object(provider.connection_manager, 'connect', side_effect=lambda name, _: mock_session(name)):
        # Connect to a server
        await provider.mcp_connect("server1")
        
        # Configure mock LLM response
        mock_llm_backend.process_query.return_value = "Test response"
        
        # Process query
        response = await provider.process_query("Test query")
        assert response == "Test response"
        
        # Verify LLM backend was called with correct tools
        mock_llm_backend.process_query.assert_called_once()
        call_args = mock_llm_backend.process_query.call_args
        assert call_args[1]["query"] == "Test query"
        assert len(call_args[1]["tools"]) == 2
        
        # Test query with no connected servers
        await provider.cleanup_all()
        with pytest.raises(ValueError, match="Not connected to any MCP server"):
            await provider.process_query("Test query")

@pytest.mark.asyncio
async def test_health_monitoring(mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack):
    """Test health monitoring functionality."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()
    
    with patch.object(provider.connection_manager, 'connect', side_effect=lambda name, _: mock_session(name)):
        # Connect to a server
        await provider.mcp_connect("server1")
        
        # Verify health monitor is started
        assert provider.health_monitor._monitor_task is not None
        assert not provider.health_monitor._monitor_task.done()
        
        # Test heartbeat update
        provider.health_monitor.update_heartbeat("server1")
        
        # Test cleanup stops monitoring
        await provider.cleanup_all()
        assert provider.health_monitor._monitor_task is None or provider.health_monitor._monitor_task.done()

@pytest.mark.asyncio
async def test_error_handling(mock_llm_backend, valid_server_configs, mock_exit_stack):
    """Test error handling during operations."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()
    
    # Test connection error
    with patch.object(provider.connection_manager, 'connect', side_effect=ConnectionError("Failed to connect")):
        with pytest.raises(ConnectionError):
            await provider.mcp_connect("server1")
        assert not provider.tool_registry.get_server_tools("server1")
    
    # Test tool registration error
    mock_session = AsyncMock()
    mock_session.list_tools = AsyncMock(side_effect=Exception("Failed to list tools"))
    
    with patch.object(provider.connection_manager, 'connect', return_value=mock_session):
        with pytest.raises(ConnectionError):
            await provider.mcp_connect("server1")
        assert not provider.tool_registry.get_server_tools("server1")

@pytest.mark.asyncio
async def test_concurrent_operations(mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack):
    """Test concurrent operations on the provider."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()
    
    with patch.object(provider.connection_manager, 'connect', side_effect=lambda name, _: mock_session(name)):
        # Connect to both servers concurrently
        await asyncio.gather(
            provider.mcp_connect("server1"),
            provider.mcp_connect("server2")
        )
        
        assert len(provider.tool_registry.tools_by_server) == 2
        assert len(provider.tool_registry.all_tools) == 4  # 2 tools per server
        
        # Cleanup both servers concurrently
        await asyncio.gather(
            provider.cleanup("server1"),
            provider.cleanup("server2")
        )
        
        assert not provider.tool_registry.tools_by_server
        assert not provider.tool_registry.all_tools 