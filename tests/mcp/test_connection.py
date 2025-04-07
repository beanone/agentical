"""Unit tests for MCP Connection components.

This module contains tests for the MCPConnectionService and MCPConnectionManager classes,
which handle server connections and health monitoring.
"""

import asyncio
import pytest
from contextlib import AsyncExitStack
from unittest.mock import AsyncMock, MagicMock, patch, call, Mock

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters
from mcp.types import Tool as MCPTool

from agentical.mcp import connection
from agentical.mcp.schemas import ServerConfig

@pytest.fixture
async def exit_stack():
    """Fixture providing an AsyncExitStack for tests."""
    async with AsyncExitStack() as stack:
        yield stack

@pytest.fixture
def server_config():
    """Fixture providing a basic server configuration."""
    return ServerConfig(
        command="test_command",
        args=["--test"],
        env={"TEST_ENV": "value"}
    )

class MockClientSession:
    """Mock implementation of ClientSession.
    
    This mock focuses on the context manager protocol (__aenter__/__aexit__)
    which is how real ClientSession handles cleanup through AsyncExitStack.
    """
    def __init__(self, tools=None, server_name=None):
        self.tools = tools or []
        self.server_name = server_name
        self.is_closed = False  # Track if __aexit__ was called
        self.mock_response = Mock()
        self.mock_response.tools = self.tools
        self.initialized = False
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup through context manager protocol."""
        self.is_closed = True
    
    async def initialize(self):
        """Initialize the session."""
        self.initialized = True
        return self
    
    async def list_tools(self):
        return self.mock_response
    
    async def call_tool(self, tool_name, tool_args):
        return Mock(result="success")

@pytest.mark.asyncio
async def test_connection_service_init(exit_stack):
    """Test MCPConnectionService initialization."""
    service = connection.MCPConnectionService(exit_stack)
    assert service._connection_manager is not None
    assert service._health_monitor is not None

@pytest.mark.asyncio
async def test_connection_service_connect(exit_stack, server_config):
    """Test connecting to a server through the connection service."""
    service = connection.MCPConnectionService(exit_stack)
    mock_session = MockClientSession()
    
    with patch('agentical.mcp.connection.MCPConnectionManager.connect', 
               new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_session
        
        # Test successful connection
        session = await service.connect("server1", server_config)
        assert session is mock_session
        assert not session.is_closed
        
        # Initialize should be called during connect
        await mock_session.initialize()
        assert session.initialized
        
        # Test connection to same server returns existing session
        session2 = await service.connect("server1", server_config)
        assert session2 is session
        
        # Test invalid server name
        with pytest.raises(ValueError):
            await service.connect("", server_config)

@pytest.mark.asyncio
async def test_connection_service_disconnect(exit_stack, server_config):
    """Test disconnecting from a server through the connection service."""
    service = connection.MCPConnectionService(exit_stack)
    mock_session = MockClientSession()
    
    with patch('agentical.mcp.connection.MCPConnectionManager.connect', 
               new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = mock_session
        
        # Connect and verify
        session = await service.connect("server1", server_config)
        await mock_session.initialize()
        assert session.initialized
        
        # Disconnect and verify
        with patch('agentical.mcp.connection.MCPConnectionManager.cleanup', 
                  new_callable=AsyncMock) as mock_cleanup:
            await service.disconnect("server1")
            mock_cleanup.assert_called_once_with("server1")

@pytest.mark.asyncio
async def test_connection_service_cleanup(exit_stack, server_config):
    """Test cleaning up all connections through the connection service."""
    service = connection.MCPConnectionService(exit_stack)
    mock_session1 = MockClientSession()
    mock_session2 = MockClientSession()
    
    with patch('agentical.mcp.connection.MCPConnectionManager.connect', 
               new_callable=AsyncMock) as mock_connect:
        mock_connect.side_effect = [mock_session1, mock_session2]
        
        # Connect to multiple servers
        session1 = await service.connect("server1", server_config)
        session2 = await service.connect("server2", server_config)
        
        # Initialize sessions
        await mock_session1.initialize()
        await mock_session2.initialize()
        
        # Cleanup all
        with patch('agentical.mcp.connection.MCPConnectionManager.cleanup_all', 
                  new_callable=AsyncMock) as mock_cleanup:
            await service.cleanup_all()
            mock_cleanup.assert_called_once()

@pytest.mark.asyncio
async def test_connection_manager_connect(exit_stack, server_config):
    """Test MCPConnectionManager connection functionality."""
    manager = connection.MCPConnectionManager(exit_stack)
    mock_session = MockClientSession()
    
    with patch('agentical.mcp.connection.stdio_client') as mock_stdio:
        mock_stdio.return_value = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
        
        with patch('agentical.mcp.connection.ClientSession') as mock_client:
            mock_client.return_value = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_session
            
            # Test successful connection
            session = await manager.connect("server1", server_config)
            await session.initialize()
            assert session is mock_session
            assert not session.is_closed
            assert session.initialized
            
            # Test invalid server name
            with pytest.raises(ValueError):
                await manager.connect("", server_config)

@pytest.mark.asyncio
async def test_connection_manager_disconnect(exit_stack, server_config):
    """Test MCPConnectionManager disconnection functionality."""
    manager = connection.MCPConnectionManager(exit_stack)
    mock_session = MockClientSession()
    
    with patch('agentical.mcp.connection.stdio_client') as mock_stdio:
        mock_stdio.return_value = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
        
        with patch('agentical.mcp.connection.ClientSession') as mock_client:
            mock_client.return_value = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_session
            
            # Connect and verify
            session = await manager.connect("server1", server_config)
            await session.initialize()
            assert session.initialized
            
            # Cleanup and verify
            await manager.cleanup("server1")
            # Verify session is removed from manager
            assert "server1" not in manager.sessions
            assert "server1" not in manager.stdios
            assert "server1" not in manager.writes

@pytest.mark.asyncio
async def test_connection_manager_cleanup(exit_stack, server_config):
    """Test MCPConnectionManager cleanup functionality."""
    manager = connection.MCPConnectionManager(exit_stack)
    mock_session1 = MockClientSession()
    mock_session2 = MockClientSession()
    
    with patch('agentical.mcp.connection.stdio_client') as mock_stdio:
        mock_stdio.return_value = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())
        
        with patch('agentical.mcp.connection.ClientSession') as mock_client:
            mock_client.return_value = AsyncMock()
            mock_client.return_value.__aenter__.side_effect = [mock_session1, mock_session2]
            
            # Connect to multiple servers
            session1 = await manager.connect("server1", server_config)
            session2 = await manager.connect("server2", server_config)
            
            # Initialize sessions
            await session1.initialize()
            await session2.initialize()
            
            # Cleanup all
            await manager.cleanup_all()
            
            # Verify all references are removed
            assert not manager.sessions
            assert not manager.stdios
            assert not manager.writes 