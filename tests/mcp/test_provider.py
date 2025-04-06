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
from agentical.mcp.connection import MCPConnectionService
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
        return CallToolResult(
            result="success",
            content=[{"type": "text", "text": "Tool execution successful"}]
        )

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
async def test_provider_tool_registration(mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack):
    """Test tool registration when connecting to servers."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()
    
    with patch.object(provider.connection_service._connection_manager, 'connect', 
                     side_effect=lambda name, _: mock_session(name)):
        # Connect to a server
        await provider.mcp_connect("server1")
        
        # Verify tools are registered
        server_tools = provider.tool_registry.get_server_tools("server1")
        assert len(server_tools) == 2
        assert all(tool.name in ["tool1", "tool2"] for tool in server_tools)
        
        # Connect to another server
        await provider.mcp_connect("server2")
        
        # Verify tools from both servers
        assert len(provider.tool_registry.all_tools) == 4
        assert len(provider.tool_registry.get_server_tools("server1")) == 2
        assert len(provider.tool_registry.get_server_tools("server2")) == 2

@pytest.mark.asyncio
async def test_provider_tool_cleanup(mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack):
    """Test tool cleanup when disconnecting from servers."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()
    
    with patch.object(provider.connection_service._connection_manager, 'connect', 
                     side_effect=lambda name, _: mock_session(name)):
        # Connect to both servers
        await provider.mcp_connect_all()
        assert len(provider.tool_registry.all_tools) == 4
        
        # Clean up one server
        await provider.cleanup_server("server1")
        assert len(provider.tool_registry.all_tools) == 2
        assert not provider.tool_registry.get_server_tools("server1")
        assert len(provider.tool_registry.get_server_tools("server2")) == 2
        
        # Clean up all
        await provider.cleanup_all()
        assert len(provider.tool_registry.all_tools) == 0
        assert not provider.tool_registry.tools_by_server

@pytest.mark.asyncio
async def test_provider_query_processing(mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack):
    """Test query processing with registered tools."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()
    
    with patch.object(provider.connection_service._connection_manager, 'connect', 
                     side_effect=lambda name, _: mock_session(name)):
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
        
        # Test query with no tools
        await provider.cleanup_all()
        with pytest.raises(ValueError, match="Not connected to any MCP server"):
            await provider.process_query("Test query")

@pytest.mark.asyncio
async def test_provider_reconnect(mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack):
    """Test server reconnection and tool re-registration."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()
    
    with patch.object(provider.connection_service._connection_manager, 'connect', 
                     side_effect=lambda name, _: mock_session(name)):
        # Test successful reconnection
        success = await provider.reconnect("server1")
        assert success
        assert len(provider.tool_registry.get_server_tools("server1")) == 2
        
        # Test reconnection to unknown server
        success = await provider.reconnect("nonexistent")
        assert not success
        
        # Test reconnection after cleanup
        await provider.cleanup_server("server1")
        success = await provider.reconnect("server1")
        assert success
        assert len(provider.tool_registry.get_server_tools("server1")) == 2

@pytest.mark.asyncio
async def test_execute_tool_success(mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack):
    """Test successful tool execution."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()
    
    # Create and store mock session
    session = mock_session("server1")
    provider.connection_service.get_session = Mock(return_value=session)
    
    with patch.object(provider.connection_service._connection_manager, 'connect', 
                     return_value=session):
        # Connect to a server
        await provider.mcp_connect("server1")
        
        # Configure mock LLM response
        async def mock_process_query(query, tools, execute_tool, **kwargs):
            # Execute the tool and verify response
            result = await execute_tool("tool1", {"arg": "value"})
            assert isinstance(result, CallToolResult)
            assert result.result == "success"
            return "Test response"
            
        mock_llm_backend.process_query.side_effect = mock_process_query
        
        # Process query
        response = await provider.process_query("Test query")
        assert response == "Test response"
        
        # Verify LLM backend was called
        mock_llm_backend.process_query.assert_called_once()

@pytest.mark.asyncio
async def test_execute_tool_no_session(mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack):
    """Test tool execution with no active session."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()
    
    with patch.object(provider.connection_service._connection_manager, 'connect', 
                     side_effect=lambda name, _: mock_session(name)):
        # Connect to a server
        await provider.mcp_connect("server1")
        
        # Mock connection service to return no session
        provider.connection_service.get_session = Mock(return_value=None)
        
        # Configure mock LLM response
        async def mock_process_query(query, tools, execute_tool, **kwargs):
            # Execute tool and expect ValueError
            with pytest.raises(ValueError, match="No active session for server server1"):
                await execute_tool("tool1", {"arg": "value"})
            return "Test response"
            
        mock_llm_backend.process_query.side_effect = mock_process_query
        
        # Process query
        response = await provider.process_query("Test query")
        assert response == "Test response"
        
        # Verify LLM backend was called
        mock_llm_backend.process_query.assert_called_once()

@pytest.mark.asyncio
async def test_execute_tool_not_found(mock_llm_backend, valid_server_configs, mock_session, mock_exit_stack):
    """Test execution of non-existent tool."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()
    
    with patch.object(provider.connection_service._connection_manager, 'connect', 
                     side_effect=lambda name, _: mock_session(name)):
        # Connect to a server
        await provider.mcp_connect("server1")
        
        # Configure mock LLM response
        async def mock_process_query(query, tools, execute_tool, **kwargs):
            # Execute unknown tool and expect ValueError
            with pytest.raises(ValueError, match="Tool unknown_tool not found in any connected server"):
                await execute_tool("unknown_tool", {"arg": "value"})
            return "Test response"
            
        mock_llm_backend.process_query.side_effect = mock_process_query
        
        # Process query
        response = await provider.process_query("Test query")
        assert response == "Test response"
        
        # Verify LLM backend was called
        mock_llm_backend.process_query.assert_called_once()

@pytest.mark.asyncio
async def test_execute_tool_session_error(mock_llm_backend, valid_server_configs, mock_exit_stack):
    """Test tool execution when session raises error."""
    provider = MCPToolProvider(mock_llm_backend, server_configs=valid_server_configs)
    provider.exit_stack = mock_exit_stack
    await provider.initialize()
    
    # Create mock session that raises error
    error_session = AsyncMock()
    error_session.list_tools = AsyncMock(return_value=Mock(tools=[
        MCPTool(
            name="tool1",
            description="Tool 1",
            parameters={},
            inputSchema={"type": "object", "properties": {}}  # Add required inputSchema
        )
    ]))
    error_session.call_tool = AsyncMock(side_effect=Exception("Tool execution failed"))
    
    # Store session in connection service
    provider.connection_service.get_session = Mock(return_value=error_session)
    
    with patch.object(provider.connection_service._connection_manager, 'connect', 
                     return_value=error_session):
        # Connect to a server
        await provider.mcp_connect("server1")
        
        # Configure mock LLM response
        async def mock_process_query(query, tools, execute_tool, **kwargs):
            # Execute tool and expect error
            with pytest.raises(Exception, match="Tool execution failed"):
                await execute_tool("tool1", {"arg": "value"})
            return "Test response"
            
        mock_llm_backend.process_query.side_effect = mock_process_query
        
        # Process query
        response = await provider.process_query("Test query")
        assert response == "Test response"
        
        # Verify LLM backend was called
        mock_llm_backend.process_query.assert_called_once()
        # Verify tool call was attempted
        error_session.call_tool.assert_called_once_with("tool1", {"arg": "value"}) 