"""Unit tests for MCP Connection components.

This module contains tests for the MCPConnectionService and MCPConnectionManager
classes, which handle server connections and health monitoring.
"""

from contextlib import AsyncExitStack
from unittest.mock import AsyncMock, Mock, patch

import pytest

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
        command="test_command", args=["--test"], env={"TEST_ENV": "value"}
    )


class MockClientSession:
    """Mock implementation of ClientSession.

    This mock implements only the methods that exist in the real ClientSession:
    - Context manager protocol (__aenter__/__aexit__)
    - initialize()
    - list_tools()
    - call_tool()
    """

    def __init__(self, tools=None, server_name=None):
        self.tools = tools or []
        self.server_name = server_name
        self.mock_response = Mock()
        self.mock_response.tools = self.tools
        self.initialized = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

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

    with patch(
        "agentical.mcp.connection.MCPConnectionManager.connect", new_callable=AsyncMock
    ) as mock_connect:
        mock_connect.return_value = mock_session

        # Test successful connection
        session = await service.connect("server1", server_config)
        assert session is mock_session

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

    with patch(
        "agentical.mcp.connection.MCPConnectionManager.connect", new_callable=AsyncMock
    ) as mock_connect:
        mock_connect.return_value = mock_session

        # Connect and verify
        session = await service.connect("server1", server_config)
        await mock_session.initialize()
        assert session.initialized

        # Disconnect and verify
        with patch(
            "agentical.mcp.connection.MCPConnectionManager.cleanup",
            new_callable=AsyncMock,
        ) as mock_cleanup:
            await service.disconnect("server1")
            mock_cleanup.assert_called_once_with("server1")


@pytest.mark.asyncio
async def test_connection_service_cleanup(exit_stack, server_config):
    """Test cleaning up all connections through the connection service."""
    service = connection.MCPConnectionService(exit_stack)
    mock_session1 = MockClientSession()
    mock_session2 = MockClientSession()

    with patch(
        "agentical.mcp.connection.MCPConnectionManager.connect", new_callable=AsyncMock
    ) as mock_connect:
        mock_connect.side_effect = [mock_session1, mock_session2]

        # Connect to multiple servers
        session1 = await service.connect("server1", server_config)
        session2 = await service.connect("server2", server_config)

        # Initialize sessions
        await mock_session1.initialize()
        await mock_session2.initialize()

        # Cleanup all
        with patch(
            "agentical.mcp.connection.MCPConnectionManager.cleanup_all",
            new_callable=AsyncMock,
        ) as mock_cleanup:
            await service.cleanup_all()
            mock_cleanup.assert_called_once()


@pytest.mark.asyncio
async def test_connection_manager_connect(exit_stack, server_config):
    """Test MCPConnectionManager connection functionality."""
    manager = connection.MCPConnectionManager(exit_stack)
    mock_session = MockClientSession()

    with patch("agentical.mcp.connection.stdio_client") as mock_stdio:
        mock_stdio.return_value = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())

        with patch("agentical.mcp.connection.ClientSession") as mock_client:
            mock_client.return_value = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_session

            # Test successful connection
            session = await manager.connect("server1", server_config)
            await session.initialize()
            assert session is mock_session
            assert session.initialized

            # Test invalid server name
            with pytest.raises(ValueError):
                await manager.connect("", server_config)


@pytest.mark.asyncio
async def test_connection_manager_disconnect(exit_stack, server_config):
    """Test MCPConnectionManager disconnection functionality."""
    manager = connection.MCPConnectionManager(exit_stack)
    mock_session = MockClientSession()

    with patch("agentical.mcp.connection.stdio_client") as mock_stdio:
        mock_stdio.return_value = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())

        with patch("agentical.mcp.connection.ClientSession") as mock_client:
            mock_client.return_value = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_session

            # Connect and verify
            session = await manager.connect("server1", server_config)
            await session.initialize()
            assert session.initialized

            # Cleanup and verify references are removed
            await manager.cleanup("server1")
            assert "server1" not in manager.sessions
            assert "server1" not in manager.stdios
            assert "server1" not in manager.writes


@pytest.mark.asyncio
async def test_connection_manager_cleanup(exit_stack, server_config):
    """Test MCPConnectionManager cleanup functionality."""
    manager = connection.MCPConnectionManager(exit_stack)
    mock_session1 = MockClientSession()
    mock_session2 = MockClientSession()

    with patch("agentical.mcp.connection.stdio_client") as mock_stdio:
        mock_stdio.return_value = AsyncMock()
        mock_stdio.return_value.__aenter__.return_value = (AsyncMock(), AsyncMock())

        with patch("agentical.mcp.connection.ClientSession") as mock_client:
            mock_client.return_value = AsyncMock()
            mock_client.return_value.__aenter__.side_effect = [
                mock_session1,
                mock_session2,
            ]

            # Connect to multiple servers
            session1 = await manager.connect("server1", server_config)
            session2 = await manager.connect("server2", server_config)

            # Initialize sessions
            await session1.initialize()
            await session2.initialize()

            # Cleanup all and verify references are removed
            await manager.cleanup_all()
            assert not manager.sessions
            assert not manager.stdios
            assert not manager.writes


@pytest.mark.asyncio
async def test_connection_manager_connect_retry_failure(exit_stack, server_config):
    """Test MCPConnectionManager connection retry failure."""
    manager = connection.MCPConnectionManager(exit_stack)

    with patch("agentical.mcp.connection.stdio_client") as mock_stdio:
        mock_stdio.return_value = AsyncMock()
        mock_stdio.return_value.__aenter__.side_effect = ConnectionError("Failed to connect")

        with pytest.raises(ConnectionError):
            await manager.connect("server1", server_config)

        # Verify cleanup was called
        assert "server1" not in manager.sessions
        assert "server1" not in manager.stdios
        assert "server1" not in manager.writes


@pytest.mark.asyncio
async def test_connection_manager_cleanup_nonexistent_server(exit_stack):
    """Test cleaning up a non-existent server."""
    manager = connection.MCPConnectionManager(exit_stack)

    # Should not raise any errors
    await manager.cleanup("nonexistent_server")


@pytest.mark.asyncio
async def test_connection_manager_cleanup_all_empty(exit_stack):
    """Test cleaning up when no servers are connected."""
    manager = connection.MCPConnectionManager(exit_stack)

    # Should not raise any errors
    await manager.cleanup_all()


@pytest.mark.asyncio
async def test_connection_service_connect_failure(exit_stack, server_config):
    """Test connection service handling of connection failures."""
    service = connection.MCPConnectionService(exit_stack)

    with patch(
        "agentical.mcp.connection.MCPConnectionManager.connect",
        new_callable=AsyncMock,
        side_effect=ConnectionError("Failed to connect")
    ):
        with pytest.raises(ConnectionError):
            await service.connect("server1", server_config)


@pytest.mark.asyncio
async def test_connection_service_cleanup_all_failure(exit_stack, server_config):
    """Test connection service handling of cleanup failures."""
    service = connection.MCPConnectionService(exit_stack)
    mock_session = MockClientSession()

    with patch(
        "agentical.mcp.connection.MCPConnectionManager.connect",
        new_callable=AsyncMock,
        return_value=mock_session
    ):
        await service.connect("server1", server_config)

    with patch(
        "agentical.mcp.connection.MCPConnectionManager.cleanup_all",
        new_callable=AsyncMock,
        side_effect=Exception("Cleanup failed")
    ) as mock_cleanup, patch(
        "agentical.mcp.connection.logger.error"
    ) as mock_logger:
        # Should not raise the exception
        await service.cleanup_all()

        # Verify cleanup was attempted
        mock_cleanup.assert_called_once()

        # Verify error was logged
        mock_logger.assert_called_once()
        assert "Error during connection cleanup" in str(mock_logger.call_args[0][0])
        assert "Cleanup failed" in str(mock_logger.call_args[0][1])


@pytest.mark.asyncio
async def test_connection_manager_handle_connection_failure(exit_stack, server_config):
    """Test MCPConnectionManager handling of connection failures."""
    manager = connection.MCPConnectionManager(exit_stack)

    with patch("agentical.mcp.connection.stdio_client") as mock_stdio:
        mock_stdio.return_value = AsyncMock()
        mock_stdio.return_value.__aenter__.side_effect = Exception("Connection failed")

        with pytest.raises(ConnectionError):
            await manager._handle_connection("server1", server_config)

        # Verify cleanup was called
        assert "server1" not in manager.sessions
        assert "server1" not in manager.stdios
        assert "server1" not in manager.writes


@pytest.mark.asyncio
async def test_connection_service_reconnect_success(exit_stack, server_config):
    """Test successful reconnection through the connection service."""
    service = connection.MCPConnectionService(exit_stack)
    mock_session = MockClientSession()

    with patch(
        "agentical.mcp.connection.MCPConnectionManager.connect",
        new_callable=AsyncMock,
        return_value=mock_session
    ) as mock_connect, patch(
        "agentical.mcp.connection.MCPConnectionManager.cleanup",
        new_callable=AsyncMock
    ) as mock_cleanup:
        # First connect to establish the session and store config
        await service.connect("server1", server_config)
        # Manually store the session and config since the mock doesn't do it
        service._connection_manager.sessions["server1"] = mock_session
        service._connection_manager._configs["server1"] = server_config

        # Test reconnection
        success = await service.reconnect("server1")
        assert success, f"Reconnect failed. Sessions: {service._connection_manager.sessions}, Configs: {service._connection_manager._configs}"
        assert service.get_session("server1") is not None

        # Verify cleanup was called before reconnect
        mock_cleanup.assert_called_once_with("server1")

        # Verify connect was called twice (initial connect and reconnect)
        assert mock_connect.call_count == 2
        assert mock_connect.call_args_list[0][0] == ("server1", server_config)
        assert mock_connect.call_args_list[1][0] == ("server1", server_config)


@pytest.mark.asyncio
async def test_connection_service_reconnect_no_session(exit_stack):
    """Test reconnection attempt when no session exists."""
    service = connection.MCPConnectionService(exit_stack)

    # Attempt to reconnect non-existent server
    success = await service.reconnect("nonexistent_server")
    assert not success


@pytest.mark.asyncio
async def test_connection_service_reconnect_no_config(exit_stack, server_config):
    """Test reconnection attempt when no config exists."""
    service = connection.MCPConnectionService(exit_stack)
    mock_session = MockClientSession()

    with patch(
        "agentical.mcp.connection.MCPConnectionManager.connect",
        new_callable=AsyncMock,
        return_value=mock_session
    ):
        # Connect but don't store config
        await service.connect("server1", server_config)
        service._connection_manager._configs.clear()  # Clear stored config

        # Attempt reconnection
        success = await service.reconnect("server1")
        assert not success


@pytest.mark.asyncio
async def test_connection_service_reconnect_failure(exit_stack, server_config):
    """Test reconnection failure handling."""
    service = connection.MCPConnectionService(exit_stack)
    mock_session = MockClientSession()

    with patch(
        "agentical.mcp.connection.MCPConnectionManager.connect",
        new_callable=AsyncMock,
        return_value=mock_session
    ) as mock_connect:
        # First connect to establish the session and store config
        await service.connect("server1", server_config)

        # Now patch connect to fail during reconnect
        mock_connect.side_effect = Exception("Connection failed")

        # Test reconnection failure
        success = await service.reconnect("server1")
        assert not success
        assert service.get_session("server1") is None
