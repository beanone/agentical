"""Tests for MCP client implementation."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agentical.providers.mcp.models import (
    MCPConfig,
    MCPError,
    MCPErrorCode,
    MCPProgress
)
from agentical.providers.mcp.client import MCPClient, MCPConnection


class MockProcess:
    """Mock subprocess for testing."""
    def __init__(self, responses=None):
        self.responses = responses or []
        self.stdin = AsyncMock()
        self.stdout = AsyncMock()
        self.stderr = AsyncMock()
        self.processed_messages = []
        
        # Set up stdout.readline to return responses
        async def readline():
            await asyncio.sleep(0.1)  # Small delay to simulate real process
            if not self.responses:
                print("No more responses in mock process")
                return b""
            response = self.responses.pop(0)
            print(f"Mock process returning response: {response}")
            self.processed_messages.append(response)
            return json.dumps(response).encode() + b"\n"
            
        self.stdout.readline = readline
        self.stdout.at_eof = MagicMock(return_value=False)
        
        # Configure stdin.write to return length of data
        self.stdin.write.return_value = 0
        
    async def wait(self):
        return 0
        
    def terminate(self):
        pass
        
    def kill(self):
        pass


@pytest.fixture
def mock_process():
    """Create a mock process with predefined responses."""
    return MockProcess([
        {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "capabilities": {
                    "tools": True,
                    "progress": True,
                    "completion": False,
                    "sampling": False,
                    "cancellation": True
                }
            }
        }
    ])


@pytest.fixture
def config():
    """Create a test MCP config."""
    return MCPConfig(
        command="test_server",
        args=["--port", "1234"]
    )


@pytest.mark.asyncio
async def test_connection_lifecycle(config, mock_process):
    """Test MCPConnection lifecycle management."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        conn = MCPConnection(config)
        
        # Test connection
        await conn.connect()
        assert conn.process is not None
        
        # Test message sending
        message = {"jsonrpc": "2.0", "method": "initialize", "id": 1}
        mock_process.responses.append({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "capabilities": {
                    "tools": True,
                    "progress": True,
                    "completion": False,
                    "sampling": False,
                    "cancellation": True
                }
            }
        })
        response = await conn.send_message(message)
        assert response["result"]["capabilities"]["tools"] is True
        
        # Test notification handling
        notification_received = asyncio.Event()
        notification_params = None
        
        async def handle_notification(params):
            nonlocal notification_params
            print("Notification handler called with params:", params)
            notification_params = params
            notification_received.set()
            
        conn.register_notification_handler("test_notify", handle_notification)
        
        # Simulate notification
        notification = {
            "jsonrpc": "2.0",
            "method": "test_notify",
            "params": {"test": "data"}
        }
        print("Adding notification to mock process responses")
        mock_process.responses.append(notification)
        
        # Wait for notification with increased timeout
        try:
            print("Waiting for notification...")
            await asyncio.wait_for(notification_received.wait(), timeout=2.0)
            print("Notification received!")
            assert notification_received.is_set()
            assert notification_params == {"test": "data"}
            # Verify the notification was processed
            assert any(
                msg.get("method") == "test_notify" and "id" not in msg
                for msg in mock_process.processed_messages
            ), "Notification not found in processed messages"
        except asyncio.TimeoutError:
            print("Processed messages:", mock_process.processed_messages)
            pytest.fail("Notification not received")
            
        # Test close
        await conn.close()
        assert conn.process is None


@pytest.mark.asyncio
async def test_client_initialization(config, mock_process):
    """Test MCPClient initialization and capability negotiation."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPClient("test_server", config)
        
        # Test initialization
        await client.connect()
        assert client._initialized
        assert client.capabilities is not None
        assert client.capabilities.tools
        assert client.capabilities.progress
        assert not client.capabilities.completion
        assert not client.capabilities.sampling
        assert client.capabilities.cancellation


@pytest.mark.asyncio
async def test_client_method_execution(config, mock_process):
    """Test MCPClient method execution."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPClient("test_server", config)
        await client.connect()
        
        # Test method execution
        mock_process.responses.append({
            "jsonrpc": "2.0",
            "id": 2,
            "result": {"status": "success"}
        })
        
        async for result in client.execute("test_method", {"arg": "value"}):
            assert result == {"status": "success"}


@pytest.mark.asyncio
async def test_client_progress_tracking(config, mock_process):
    """Test MCPClient progress tracking."""
    progress_updates = []
    
    async def progress_callback(progress: MCPProgress):
        progress_updates.append(progress)
        
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPClient("test_server", config, progress_callback)
        await client.connect()
        
        # Simulate progress notification
        mock_process.responses.append({
            "jsonrpc": "2.0",
            "method": "$/progress",
            "params": {
                "operation_id": "test_op",
                "progress": 0.5,
                "message": "Half done"
            }
        })
        
        # Wait for progress update
        await asyncio.sleep(0.1)
        
        assert len(progress_updates) == 1
        assert progress_updates[0].operation_id == "test_op"
        assert progress_updates[0].progress == 0.5
        assert progress_updates[0].message == "Half done"


@pytest.mark.asyncio
async def test_client_error_handling(config, mock_process):
    """Test MCPClient error handling."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPClient("test_server", config)
        await client.connect()
        
        # Test error response
        mock_process.responses.append({
            "jsonrpc": "2.0",
            "id": 2,
            "error": {
                "code": MCPErrorCode.INVALID_REQUEST,
                "message": "Invalid method"
            }
        })
        
        with pytest.raises(MCPError) as exc_info:
            async for _ in client.execute("invalid_method", {}):
                pass
                
        assert exc_info.value.code == MCPErrorCode.INVALID_REQUEST
        assert exc_info.value.message == "Invalid method"


@pytest.mark.asyncio
async def test_client_cancellation(config, mock_process):
    """Test MCPClient operation cancellation."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPClient("test_server", config)
        await client.connect()
        
        # Test cancellation
        await client.cancel(123)
        
        # Verify cancellation message was sent
        assert mock_process.stdin.write.called
        call_args = mock_process.stdin.write.call_args[0][0]
        message = json.loads(call_args.decode().strip())
        assert message["method"] == "$/cancel"
        assert message["params"]["id"] == 123 