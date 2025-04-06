"""Unit tests for the MCPConnectionManager class.

This module contains comprehensive tests for the MCPConnectionManager class,
focusing on behavior verification, error handling, and resource management.
"""

import asyncio
import pytest
from contextlib import AsyncExitStack
from unittest.mock import AsyncMock, MagicMock, patch

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters

from agentical.mcp.connection import MCPConnectionManager
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

class AsyncContextManagerMock:
    """Mock class that implements the async context manager protocol."""
    def __init__(self, mock_transport):
        self.mock_transport = mock_transport
        
    async def __aenter__(self):
        return self.mock_transport
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None

@pytest.fixture
def mock_stdio_client():
    """Fixture providing a mocked stdio_client context manager."""
    mock_stdio = AsyncMock()
    mock_write = AsyncMock()
    mock_transport = (mock_stdio, mock_write)
    
    # Create a proper async context manager mock
    context_manager = AsyncContextManagerMock(mock_transport)
    
    with patch('agentical.mcp.connection.stdio_client', return_value=context_manager) as mock:
        yield mock, mock_transport

@pytest.fixture
def mock_client_session():
    """Fixture providing a mocked ClientSession."""
    mock_session = AsyncMock(spec=ClientSession)
    
    # Create a proper async context manager mock for ClientSession
    context_manager = AsyncContextManagerMock(mock_session)
    
    with patch('agentical.mcp.connection.ClientSession', return_value=context_manager) as mock:
        yield mock, mock_session

@pytest.mark.asyncio
async def test_successful_connection(exit_stack, server_config, mock_stdio_client, mock_client_session):
    """Test successful server connection and initialization."""
    _, mock_transport = mock_stdio_client
    _, mock_session = mock_client_session
    
    manager = MCPConnectionManager(exit_stack)
    session = await manager.connect("test_server", server_config)
    
    assert session == mock_session
    assert "test_server" in manager.sessions
    assert manager.sessions["test_server"] == mock_session
    mock_session.initialize.assert_called_once()

@pytest.mark.asyncio
async def test_duplicate_connection(exit_stack, server_config, mock_stdio_client, mock_client_session):
    """Test that connecting to the same server twice raises an error."""
    manager = MCPConnectionManager(exit_stack)
    await manager.connect("test_server", server_config)
    
    with pytest.raises(ValueError, match="Server test_server is already connected"):
        await manager.connect("test_server", server_config)

@pytest.mark.asyncio
async def test_connection_retry(exit_stack, server_config, mock_stdio_client, mock_client_session):
    """Test connection retry behavior on transient failures."""
    mock_client, mock_transport = mock_stdio_client
    
    # Create context managers for failed attempts
    failed_context1 = AsyncContextManagerMock(None)
    failed_context2 = AsyncContextManagerMock(None)
    success_context = AsyncContextManagerMock(mock_transport)
    
    # Configure the mock to fail twice then succeed
    mock_client.side_effect = [
        ConnectionError("First failure"),
        ConnectionError("Second failure"),
        success_context
    ]
    
    manager = MCPConnectionManager(exit_stack)
    session = await manager.connect("test_server", server_config)
    
    assert session is not None
    assert mock_client.call_count == 3

@pytest.mark.asyncio
async def test_cleanup_single_server(exit_stack, server_config, mock_stdio_client, mock_client_session):
    """Test cleanup of a single server's resources."""
    manager = MCPConnectionManager(exit_stack)
    await manager.connect("test_server", server_config)
    
    await manager.cleanup("test_server")
    
    assert "test_server" not in manager.sessions
    assert "test_server" not in manager.stdios
    assert "test_server" not in manager.writes

@pytest.mark.asyncio
async def test_cleanup_all_servers(exit_stack, server_config, mock_stdio_client, mock_client_session):
    """Test cleanup of all server resources."""
    manager = MCPConnectionManager(exit_stack)
    await manager.connect("server1", server_config)
    await manager.connect("server2", server_config)
    
    await manager.cleanup_all()
    
    assert len(manager.sessions) == 0
    assert len(manager.stdios) == 0
    assert len(manager.writes) == 0

@pytest.mark.asyncio
async def test_cleanup_nonexistent_server(exit_stack):
    """Test cleanup of a server that doesn't exist."""
    manager = MCPConnectionManager(exit_stack)
    # Should not raise any exceptions
    await manager.cleanup("nonexistent_server")

@pytest.mark.asyncio
async def test_connection_failure_cleanup(exit_stack, server_config, mock_stdio_client):
    """Test resource cleanup on connection failure."""
    mock_client, _ = mock_stdio_client
    mock_client.side_effect = ConnectionError("Permanent failure")
    
    manager = MCPConnectionManager(exit_stack)
    
    with pytest.raises(ConnectionError, match="Failed to connect to server"):
        await manager.connect("test_server", server_config)
    
    assert "test_server" not in manager.sessions
    assert "test_server" not in manager.stdios
    assert "test_server" not in manager.writes

@pytest.mark.asyncio
async def test_cleanup_during_cancellation(exit_stack, server_config, mock_stdio_client, mock_client_session):
    """Test cleanup behavior during task cancellation."""
    manager = MCPConnectionManager(exit_stack)
    await manager.connect("test_server", server_config)
    
    # Simulate task cancellation during cleanup
    with patch.object(exit_stack, 'aclose', side_effect=asyncio.CancelledError):
        try:
            await manager.cleanup_all()
        except asyncio.CancelledError:
            # Expected behavior - the cancellation should propagate
            pass
    
    # Even with cancellation, resources should be cleaned up
    assert len(manager.sessions) == 0
    assert len(manager.stdios) == 0
    assert len(manager.writes) == 0

@pytest.mark.asyncio
async def test_server_params_creation(exit_stack, server_config, mock_stdio_client, mock_client_session):
    """Test correct creation of StdioServerParameters."""
    mock_client, _ = mock_stdio_client
    
    manager = MCPConnectionManager(exit_stack)
    await manager.connect("test_server", server_config)
    
    # Verify the StdioServerParameters were created correctly
    mock_client.assert_called_once()
    # Get the actual parameters passed to stdio_client
    call_args = mock_client.call_args[0][0]
    assert isinstance(call_args, StdioServerParameters)
    assert call_args.command == server_config.command
    assert call_args.args == server_config.args
    assert call_args.env == server_config.env 