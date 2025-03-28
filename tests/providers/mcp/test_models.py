"""Tests for MCP models."""

import pytest
from pydantic import ValidationError
from agentical.providers.mcp.models import (
    MCPErrorCode,
    MCPError,
    MCPConfig,
    MCPServerConfig,
    MCPProgress,
    MCPCapabilities,
    MCPRequest,
    MCPResponse,
    MCPNotification
)


def test_mcp_error():
    """Test MCP error creation and properties."""
    error = MCPError(MCPErrorCode.INVALID_REQUEST, "Test error", {"detail": "test"})
    assert error.code == MCPErrorCode.INVALID_REQUEST
    assert error.message == "Test error"
    assert error.data == {"detail": "test"}
    assert str(error) == "[-32600] Test error"


def test_mcp_config_validation():
    """Test MCP config validation."""
    # Valid config
    config = MCPConfig(
        command="test",
        args=["--arg1", "--arg2"],
        config={"key": "value"},
        workingDir="/tmp",
        env={"ENV_VAR": "value"}
    )
    assert config.command == "test"
    assert config.args == ["--arg1", "--arg2"]
    assert config.config == {"key": "value"}
    assert config.workingDir == "/tmp"
    assert config.env == {"ENV_VAR": "value"}

    # Required fields only
    config = MCPConfig(command="test", args=[])
    assert config.command == "test"
    assert config.args == []
    assert config.config is None
    assert config.workingDir is None
    assert config.env is None

    # Invalid config (missing required field)
    with pytest.raises(ValidationError):
        MCPConfig(args=[])


def test_mcp_server_config_validation():
    """Test MCP server config validation."""
    config = MCPServerConfig(mcpServers={
        "server1": MCPConfig(command="test1", args=[]),
        "server2": MCPConfig(command="test2", args=["--arg"])
    })
    assert len(config.mcpServers) == 2
    assert "server1" in config.mcpServers
    assert "server2" in config.mcpServers

    # Empty servers dict should fail
    with pytest.raises(ValidationError):
        MCPServerConfig(mcpServers={})


def test_mcp_progress_validation():
    """Test MCP progress validation."""
    # Valid progress
    progress = MCPProgress(
        operation_id="test_op",
        progress=0.5,
        message="Half done",
        data={"step": 2},
        is_final=False
    )
    assert progress.operation_id == "test_op"
    assert progress.progress == 0.5
    assert progress.message == "Half done"
    assert progress.data == {"step": 2}
    assert not progress.is_final

    # Progress bounds validation
    with pytest.raises(ValidationError):
        MCPProgress(operation_id="test", progress=-0.1)
    with pytest.raises(ValidationError):
        MCPProgress(operation_id="test", progress=1.1)


def test_mcp_capabilities():
    """Test MCP capabilities validation."""
    # Default capabilities
    caps = MCPCapabilities()
    assert caps.tools is True
    assert caps.progress is True
    assert caps.completion is False
    assert caps.sampling is False
    assert caps.cancellation is True

    # Custom capabilities
    caps = MCPCapabilities(
        tools=False,
        progress=False,
        completion=True,
        sampling=True,
        cancellation=False
    )
    assert not caps.tools
    assert not caps.progress
    assert caps.completion
    assert caps.sampling
    assert not caps.cancellation


def test_mcp_request():
    """Test MCP request message validation."""
    # Normal request
    request = MCPRequest(
        id=1,
        method="test",
        params={"arg": "value"}
    )
    assert request.jsonrpc == "2.0"
    assert request.id == 1
    assert request.method == "test"
    assert request.params == {"arg": "value"}

    # Request with default empty params
    request = MCPRequest(method="test")
    assert request.params == {}

    # Request without ID (notification-style)
    request = MCPRequest(method="test", id=None)
    assert request.id is None


def test_mcp_response():
    """Test MCP response message validation."""
    # Success response
    response = MCPResponse(
        id=1,
        result={"status": "ok"}
    )
    assert response.jsonrpc == "2.0"
    assert response.id == 1
    assert response.result == {"status": "ok"}
    assert response.error is None

    # Error response
    response = MCPResponse(
        id=1,
        error={
            "code": MCPErrorCode.INVALID_REQUEST,
            "message": "Test error"
        }
    )
    assert response.id == 1
    assert response.result is None
    assert response.error.code == MCPErrorCode.INVALID_REQUEST
    assert response.error.message == "Test error"


def test_mcp_notification():
    """Test MCP notification message validation."""
    # Normal notification
    notif = MCPNotification(
        method="test",
        params={"event": "update"}
    )
    assert notif.jsonrpc == "2.0"
    assert notif.method == "test"
    assert notif.params == {"event": "update"}

    # Notification with default empty params
    notif = MCPNotification(method="test")
    assert notif.params == {} 