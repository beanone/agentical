"""Tests for MCP registry implementation."""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from agentical.providers.mcp.models import (
    MCPConfig,
    MCPServerConfig,
    MCPError,
    MCPErrorCode,
    MCPProgress
)
from agentical.providers.mcp.registry import MCPRegistry


@pytest.fixture
def config_file(tmp_path):
    """Create a temporary config file for testing."""
    config = {
        "mcpServers": {
            "server1": {
                "command": "test_server1",
                "args": ["--port", "1234"]
            },
            "server2": {
                "command": "test_server2",
                "args": ["--port", "5678"],
                "workingDir": "/tmp",
                "env": {"TEST_VAR": "value"}
            }
        }
    }
    
    config_path = tmp_path / "mcp_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f)
        
    return str(config_path)


@pytest.fixture
def mock_client():
    """Create a mock MCP client."""
    client = AsyncMock()
    client._initialized = False
    client.capabilities = None
    return client


@pytest.mark.asyncio
async def test_registry_initialization(config_file):
    """Test registry initialization from config file."""
    registry = MCPRegistry.from_json(config_file)
    
    assert len(registry.clients) == 2
    assert "server1" in registry.clients
    assert "server2" in registry.clients
    
    # Check server1 config
    server1_config = registry.config.mcpServers["server1"]
    assert server1_config.command == "test_server1"
    assert server1_config.args == ["--port", "1234"]
    
    # Check server2 config
    server2_config = registry.config.mcpServers["server2"]
    assert server2_config.command == "test_server2"
    assert server2_config.args == ["--port", "5678"]
    assert server2_config.workingDir == "/tmp"
    assert server2_config.env == {"TEST_VAR": "value"}


@pytest.mark.asyncio
async def test_registry_execute(config_file, mock_client):
    """Test registry method execution."""
    with patch("agentical.providers.mcp.registry.MCPClient", return_value=mock_client):
        registry = MCPRegistry.from_json(config_file)
        
        # Set up mock response
        mock_client.execute = AsyncMock()
        mock_client.execute.return_value = [{"status": "success"}]
        
        # Execute method
        result = await registry.execute(
            "server1",
            "test_method",
            {"arg": "value"}
        )
        
        assert result == {"status": "success"}
        mock_client.execute.assert_called_once_with(
            "test_method",
            {"arg": "value"}
        )


@pytest.mark.asyncio
async def test_registry_execute_unknown_server(config_file):
    """Test registry execution with unknown server."""
    registry = MCPRegistry.from_json(config_file)
    
    with pytest.raises(ValueError) as exc_info:
        await registry.execute(
            "unknown_server",
            "test_method",
            {}
        )
    assert "Unknown MCP server: unknown_server" in str(exc_info.value)


@pytest.mark.asyncio
async def test_registry_progress_tracking(config_file, mock_client):
    """Test registry progress tracking."""
    progress_updates = []
    
    async def progress_callback(progress: MCPProgress):
        progress_updates.append(progress)
        
    with patch("agentical.providers.mcp.registry.MCPClient", return_value=mock_client):
        registry = MCPRegistry.from_json(config_file, progress_callback)
        
        # Simulate progress callback
        progress = MCPProgress(
            operation_id="test_op",
            progress=0.5,
            message="Half done"
        )
        await registry.clients["server1"].progress_callback(progress)
        
        assert len(progress_updates) == 1
        assert progress_updates[0].operation_id == "test_op"
        assert progress_updates[0].progress == 0.5
        assert progress_updates[0].message == "Half done"


@pytest.mark.asyncio
async def test_registry_cancellation(config_file, mock_client):
    """Test registry operation cancellation."""
    with patch("agentical.providers.mcp.registry.MCPClient", return_value=mock_client):
        registry = MCPRegistry.from_json(config_file)
        
        # Test cancellation
        await registry.cancel("server1", 123)
        mock_client.cancel.assert_called_once_with(123)
        
        # Test cancellation with unknown server
        with pytest.raises(ValueError) as exc_info:
            await registry.cancel("unknown_server", 123)
        assert "Unknown MCP server: unknown_server" in str(exc_info.value)


@pytest.mark.asyncio
async def test_registry_close(config_file, mock_client):
    """Test registry cleanup."""
    with patch("agentical.providers.mcp.registry.MCPClient", return_value=mock_client):
        registry = MCPRegistry.from_json(config_file)
        
        # Close registry
        await registry.close()
        
        # Verify all clients were closed
        assert mock_client.close.call_count == 2  # Two servers in config 