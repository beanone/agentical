"""Tests for MCP client implementation."""

import asyncio
import json
import os
import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from agentical.providers.mcp.models import (
    MCPConfig,
    MCPError,
    MCPErrorCode,
    MCPProgress
)
from agentical.providers.mcp.client import MCPClient, MCPConnection

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure pytest-asyncio
pytest.mark.asyncio_mode = "strict"

@pytest.fixture(autouse=True)
async def cleanup_event_loop():
    """Cleanup any pending tasks after each test."""
    yield
    # Clean up any pending tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    if tasks:
        logger.warning(f"Found {len(tasks)} pending tasks to clean up")
        for task in tasks:
            if not task.done():
                logger.warning(f"Cancelling task: {task.get_name()}")
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=0.5)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass

@pytest.fixture(autouse=True)
async def mock_process_cleanup(mock_process):
    """Ensure mock process is cleaned up after each test."""
    yield mock_process
    if not mock_process._closed:
        logger.warning("MockProcess not properly closed, cleaning up")
        mock_process._closed = True
        mock_process.responses.clear()
        mock_process.processed_messages.clear()

class MockProcess:
    """Mock subprocess for testing."""
    def __init__(self, responses=None):
        self.responses = responses or []
        self.stdin = AsyncMock()
        self.stderr = AsyncMock()
        self.processed_messages = []  # Messages processed in both directions
        self._closed = False
        self._logger = logging.getLogger(__name__ + ".MockProcess")
        self._read_lock = asyncio.Lock()
        self.pid = 12345  # Mock process ID
        self.stdout = self
        
        # Configure stdin.write to track outgoing messages
        async def mock_write(data):
            if self._closed:
                raise ConnectionError("Process is closed")
            try:
                # Track the outgoing message if it's valid JSON
                message = json.loads(data.decode())
                self._logger.debug(f"Outgoing message: {message}")
                self.processed_messages.append(message)
            except json.JSONDecodeError:
                # If it's not valid JSON, that's a client issue, not a mock issue
                pass
            return len(data)
        self.stdin.write = AsyncMock(side_effect=mock_write)
        
        self._logger.debug("MockProcess initialized")
        
    async def readline(self):
        """Thread-safe readline implementation."""
        async with self._read_lock:
            if self._closed:
                self._logger.debug("Process is closed, returning empty response")
                return b""
                
            await asyncio.sleep(0.01)  # Smaller delay to speed up tests
            
            if not self.responses:
                self._logger.debug("No more responses in queue")
                return b""
                
            response = self.responses.pop(0)
            self._logger.debug(f"Returning response: {response}")
            
            # Track incoming messages that are valid JSON
            if isinstance(response, dict):
                self._logger.debug(f"Incoming message: {response}")
                self.processed_messages.append(response)
            
            # Always return bytes, just like a real process would
            if isinstance(response, bytes):
                return response
            if isinstance(response, str):
                return response.encode()
            # If it's a dict/list, it's meant to be JSON
            return json.dumps(response).encode() + b"\n"
            
    async def at_eof(self):
        """Check if the process is closed."""
        return self._closed
        
    async def wait(self):
        self._logger.debug("Process wait called")
        return 0 if not self._closed else 1
        
    def terminate(self):
        self._logger.debug("Process terminate called")
        self._closed = True
        
    def kill(self):
        self._logger.debug("Process kill called")
        self._closed = True


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


@pytest.fixture
async def client(config, mock_process):
    """Fixture to create and cleanup client."""
    logger.info("Setting up client fixture")
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPClient("test_server", config)
        logger.debug("Client created, connecting...")
        await client.connect()
        logger.debug("Client connected")
        yield client
        logger.debug("Cleaning up client fixture")
        await client.close()
        logger.info("Client fixture cleanup complete")


@pytest.mark.asyncio
async def test_connection_basic(config, mock_process):
    """Test basic connection establishment and cleanup."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        conn = MCPConnection(config)
        await conn.connect()
        assert conn.process is not None
        await conn.close()
        assert conn.process is None


@pytest.mark.asyncio
async def test_message_sending(config, mock_process):
    """Test sending and receiving a message."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        conn = MCPConnection(config)
        await conn.connect()
        
        try:
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
            response = await asyncio.wait_for(conn.send_message(message), timeout=1.0)
            assert response["result"]["capabilities"]["tools"] is True
        finally:
            await conn.close()


@pytest.mark.asyncio
async def test_notification_handling(config, mock_process):
    """Test handling of server notifications."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        conn = MCPConnection(config)
        await conn.connect()
        
        try:
            # Set up notification handling
            notification_received = asyncio.Event()
            notification_params = None
            
            async def handle_notification(params):
                nonlocal notification_params
                notification_params = params
                notification_received.set()
                
            conn.register_notification_handler("test_notify", handle_notification)
            
            # Send notification
            notification = {
                "jsonrpc": "2.0",
                "method": "test_notify",
                "params": {"test": "data"}
            }
            mock_process.responses.append(notification)
            
            # Wait for notification
            await asyncio.wait_for(notification_received.wait(), timeout=1.0)
            assert notification_params == {"test": "data"}
            
            # Verify the notification was processed
            assert any(
                msg.get("method") == "test_notify" and "id" not in msg
                for msg in mock_process.processed_messages
            ), "Notification not found in processed messages"
        finally:
            await conn.close()


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
        
        try:
            # Test method execution
            mock_process.responses.append({
                "jsonrpc": "2.0",
                "id": 2,
                "result": {"status": "success"}
            })
            
            results = []
            async for result in client.execute("test_method", {"arg": "value"}):
                results.append(result)
                
            assert len(results) == 1
            assert results[0] == {"status": "success"}
        finally:
            await client.close()


@pytest.mark.asyncio
async def test_client_progress_tracking(config, mock_process):
    """Test MCPClient progress tracking."""
    progress_received = asyncio.Event()
    progress_updates = []
    
    async def progress_callback(progress: MCPProgress):
        progress_updates.append(progress)
        progress_received.set()
        
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPClient("test_server", config, progress_callback)
        await client.connect()
        
        try:
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
            await asyncio.wait_for(progress_received.wait(), timeout=1.0)
            
            assert len(progress_updates) == 1
            assert progress_updates[0].operation_id == "test_op"
            assert progress_updates[0].progress == 0.5
            assert progress_updates[0].message == "Half done"
        finally:
            await client.close()


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


@pytest.mark.asyncio
async def test_connection_timeout(config):
    """Test connection timeout handling."""
    # Mock the create_subprocess_exec to simulate a connection that never completes
    with patch("asyncio.create_subprocess_exec", side_effect=OSError("Connection timed out")):
        client = MCPClient("test_server", config)
        
        with pytest.raises(MCPError) as exc_info:
            await client.connect()
            
        assert exc_info.value.code == MCPErrorCode.SERVER_NOT_INITIALIZED
        assert "Failed to initialize server" in str(exc_info.value)


@pytest.mark.asyncio
async def test_invalid_json_response(config):
    """Test handling of invalid JSON responses."""
    # Create mock process with an invalid JSON response
    mock_process = MockProcess([
        b"invalid json\n"  # Raw bytes, simulating invalid JSON from server
    ])
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        conn = MCPConnection(config)
        await conn.connect()
        
        # Send a message and verify it handles the invalid JSON gracefully
        message = {"id": 1, "method": "test"}
        with pytest.raises(MCPError) as exc_info:
            await conn.send_message(message)
            
        assert exc_info.value.code == MCPErrorCode.INTERNAL_ERROR
        assert "Invalid JSON from server" in str(exc_info.value)
        await conn.close()


@pytest.mark.asyncio
async def test_process_termination(config):
    """Test handling of unexpected process termination."""
    mock_process = MockProcess([])
    mock_process.wait = AsyncMock(return_value=1)  # Non-zero exit code
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        conn = MCPConnection(config)
        await conn.connect()
        
        # Force process termination
        await conn.close()
        
        # Give time for tasks to be cleaned up
        await asyncio.sleep(0.1)
        
        # Verify connection is properly cleaned up
        assert conn.process is None
        assert conn._read_task is None or conn._read_task.done()


@pytest.mark.asyncio
async def test_environment_variables(config):
    """Test environment variable handling."""
    env_vars = {"TEST_VAR": "test_value"}
    config.env = env_vars
    
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        conn = MCPConnection(config)
        await conn.connect()
        
        # Verify environment variables were passed correctly
        call_kwargs = mock_exec.call_args[1]
        assert "env" in call_kwargs
        assert call_kwargs["env"]["TEST_VAR"] == "test_value"


@pytest.mark.asyncio
async def test_working_directory(config):
    """Test working directory configuration."""
    config.workingDir = "/test/dir"
    
    with patch("asyncio.create_subprocess_exec") as mock_exec:
        conn = MCPConnection(config)
        await conn.connect()
        
        # Verify working directory was set correctly
        call_kwargs = mock_exec.call_args[1]
        assert call_kwargs["cwd"] == "/test/dir"


@pytest.mark.asyncio
async def test_concurrent_requests(client, mock_process):
    """Test handling of multiple concurrent requests."""
    logger.info("Starting concurrent requests test")
    
    # Prepare multiple responses
    logger.debug("Adding response messages to mock process")
    mock_process.responses.extend([
        {"jsonrpc": "2.0", "id": 2, "result": {"value": 1}},
        {"jsonrpc": "2.0", "id": 3, "result": {"value": 2}},
        {"jsonrpc": "2.0", "id": 4, "result": {"value": 3}}
    ])
    
    # Send multiple requests concurrently with timeout
    async def execute_request(value):
        logger.debug(f"Executing request with value: {value}")
        async for result in client.execute("test", {"value": value}):
            logger.debug(f"Received result for value {value}: {result}")
            return result
    
    logger.debug("Gathering concurrent requests")
    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                execute_request(1),
                execute_request(2),
                execute_request(3)
            ),
            timeout=2.0
        )
        
        logger.debug(f"Received all results: {results}")
        assert len(results) == 3
        assert all(r["value"] in [1, 2, 3] for r in results)
        logger.info("Concurrent requests test completed successfully")
    except Exception as e:
        logger.error(f"Concurrent requests test failed: {e}")
        raise


@pytest.mark.asyncio
async def test_multiple_progress_updates(config, mock_process):
    """Test handling of multiple progress updates."""
    logger.info("Starting multiple progress updates test")
    progress_updates = []
    progress_event = asyncio.Event()
    
    async def progress_callback(progress: MCPProgress):
        logger.debug(f"Progress callback received: {progress}")
        progress_updates.append(progress)
        if len(progress_updates) == 2:
            logger.debug("Both progress updates received, setting event")
            progress_event.set()
        
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPClient("test_server", config, progress_callback)
        logger.debug("Connecting client")
        await client.connect()
        
        try:
            # Simulate multiple progress notifications
            logger.debug("Adding progress notifications to mock process")
            mock_process.responses.extend([
                {
                    "jsonrpc": "2.0",
                    "method": "$/progress",
                    "params": {
                        "operation_id": "test_op",
                        "progress": 0.25,
                        "message": "Quarter done"
                    }
                },
                {
                    "jsonrpc": "2.0",
                    "method": "$/progress",
                    "params": {
                        "operation_id": "test_op",
                        "progress": 0.75,
                        "message": "Almost done"
                    }
                }
            ])
            
            # Wait for both progress updates with timeout
            logger.debug("Waiting for progress updates...")
            await asyncio.wait_for(progress_event.wait(), timeout=1.0)
            logger.debug("Progress event received")
            
            assert len(progress_updates) == 2
            assert progress_updates[0].progress == 0.25
            assert progress_updates[1].progress == 0.75
            logger.debug("Progress assertions passed")
        except Exception as e:
            logger.error(f"Test failed with error: {e}")
            raise
        finally:
            logger.debug("Cleaning up client")
            await client.close()
            logger.info("Multiple progress updates test completed")


@pytest.mark.asyncio
async def test_connection_failure(config):
    """Test handling of connection failures."""
    with patch("asyncio.create_subprocess_exec", side_effect=OSError("Failed to start process")):
        client = MCPClient("test_server", config)
        
        with pytest.raises(MCPError) as exc_info:
            await client.connect()
            
        assert exc_info.value.code == MCPErrorCode.SERVER_NOT_INITIALIZED
        assert "Failed to initialize server" in exc_info.value.message


@pytest.mark.asyncio
async def test_missing_response(config, mock_process):
    """Test handling of missing responses."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPClient("test_server", config)
        await client.connect()
        
        # Don't append any response, which will trigger a timeout
        with pytest.raises(MCPError) as exc_info:
            async for _ in client.execute("test_method", {}):
                pass
                
        assert exc_info.value.code == MCPErrorCode.INTERNAL_ERROR
        assert "Timeout" in exc_info.value.message


@pytest.mark.asyncio
async def test_malformed_progress(config, mock_process):
    """Test handling of malformed progress notifications."""
    progress_updates = []
    
    async def progress_callback(progress: MCPProgress):
        progress_updates.append(progress)
        
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPClient("test_server", config, progress_callback)
        await client.connect()
        
        try:
            # Simulate malformed progress notification
            mock_process.responses.append({
                "jsonrpc": "2.0",
                "method": "$/progress",
                "params": {
                    "operation_id": "test_op",
                    # Missing progress field
                    "message": "Malformed"
                }
            })
            
            # Wait a short time for any potential updates
            await asyncio.sleep(0.1)
            
            # Verify no progress update was processed due to validation error
            assert len(progress_updates) == 0
        finally:
            await client.close()


@pytest.mark.asyncio
async def test_read_responses_fatal_error(config, mock_process):
    """Test that read errors are treated as fatal and kill the connection."""
    # Configure mock process to raise a read error
    mock_process.stdout.readline = AsyncMock(side_effect=IOError("Read error"))
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        conn = MCPConnection(config)
        await conn.connect()
        
        # Send a message - should fail due to fatal error
        with pytest.raises(MCPError) as exc_info:
            await conn.send_message({"id": 1, "method": "test"})
        
        # Verify error handling and connection state
        assert exc_info.value.code == MCPErrorCode.INTERNAL_ERROR
        assert "Fatal connection error" in str(exc_info.value)
        assert conn.process is not None  # Process cleanup happens in close()
        assert not conn._pending_requests  # All pending requests should be cleared
        
        # Verify connection is unusable after fatal error
        with pytest.raises(MCPError) as exc_info:
            await conn.send_message({"id": 2, "method": "test"})
        assert exc_info.value.code == MCPErrorCode.INTERNAL_ERROR


@pytest.mark.asyncio
async def test_read_responses_logs_error(config, mock_process, caplog):
    """Test that read_responses logs errors properly."""
    # Configure mock process to raise an error
    mock_process.stdout.readline = AsyncMock(side_effect=RuntimeError("Read error"))

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        conn = MCPConnection(config)
        await conn.connect()
        await asyncio.sleep(0.1)  # Give time for error to be logged

        # Verify error was logged
        assert any(
            record.levelname == "ERROR" and
            "[lifecycle.application] Fatal connection error: Read error" in record.message
            for record in caplog.records
        )


@pytest.mark.asyncio
async def test_read_responses_invalid_json(config, mock_process, caplog):
    """Test that JSON decode errors only fail the current message."""
    # Track what's been read
    read_count = 0

    async def mock_readline():
        nonlocal read_count
        read_count += 1
        if read_count == 1:
            return b"invalid json\n"
        return b""  # EOF after invalid JSON

    mock_process.stdout.readline = mock_readline

    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        conn = MCPConnection(config)
        await conn.connect()

        # Message should fail with JSON error
        with pytest.raises(MCPError) as exc_info:
            await conn.send_message({"id": 1, "method": "test"})
        assert exc_info.value.code == MCPErrorCode.INTERNAL_ERROR
        assert "Invalid JSON from server" in str(exc_info.value)

        # Verify error was logged
        assert any(
            record.levelname == "ERROR" and
            "[lifecycle.application] Protocol error" in record.message and
            "Invalid JSON from server" in record.message
            for record in caplog.records
        )

        # Connection should be closed after error
        assert not conn._pending_requests  # Request should be cleared


@pytest.mark.asyncio
async def test_read_responses_eof(config, mock_process):
    """Test that EOF is handled gracefully."""
    # Configure mock process to return EOF
    mock_process.stdout.readline = AsyncMock(return_value=b"")
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        conn = MCPConnection(config)
        await conn.connect()
        
        # Send a message - should timeout since no response will come
        with pytest.raises(MCPError) as exc_info:
            await conn.send_message({"id": 1, "method": "test"})
        
        assert exc_info.value.code == MCPErrorCode.INTERNAL_ERROR
        assert "Timeout" in str(exc_info.value)
        assert not conn._pending_requests  # Request should be cleared
        
        # Connection should be closed after EOF
        assert conn.process is not None  # Process cleanup happens in close()
        await conn.close()
        assert conn.process is None


@pytest.mark.asyncio
async def test_read_responses_continues_after_error(config, mock_process):
    """Test that non-fatal errors don't kill the connection."""
    # Set up mock responses - first invalid JSON, then valid response
    mock_process.responses = [
        b"invalid json\n",
        {"id": 2, "result": "success"}
    ]
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        conn = MCPConnection(config)
        await conn.connect()
        
        try:
            # First message should fail with JSON error
            with pytest.raises(MCPError) as exc_info:
                await conn.send_message({"id": 1, "method": "test"})
            assert exc_info.value.code == MCPErrorCode.INTERNAL_ERROR
            assert "Invalid JSON from server" in str(exc_info.value)
            
            # Connection state should be preserved
            assert conn.process is not None
            assert not conn._pending_requests
            
            # Second message should succeed
            response = await conn.send_message({"id": 2, "method": "test"})
            assert response == {"id": 2, "result": "success"}
        finally:
            await conn.close()
            assert conn.process is None
            assert not conn._pending_requests


@pytest.mark.asyncio
async def test_unknown_notification(config, mock_process):
    """Test handling of notifications for unknown methods."""
    # Add a notification for an unregistered method
    mock_process.responses.append({
        "jsonrpc": "2.0",
        "method": "unknown_method",
        "params": {"test": "data"}
    })
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        conn = MCPConnection(config)
        await conn.connect()
        
        # Wait a bit to let the notification be processed
        await asyncio.sleep(0.1)
        
        # Verify the notification was received but ignored
        assert any(
            msg.get("method") == "unknown_method"
            for msg in mock_process.processed_messages
        )


@pytest.mark.asyncio
async def test_double_connect(config, mock_process):
    """Test that connecting twice is safe."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        conn = MCPConnection(config)
        await conn.connect()  # First connect
        await conn.connect()  # Second connect should be no-op
        assert conn.process is mock_process


@pytest.mark.asyncio
async def test_connect_failure_handling(config):
    """Test handling of connection failures."""
    with patch("asyncio.create_subprocess_exec", side_effect=OSError("Failed to start")):
        conn = MCPConnection(config)
        with pytest.raises(OSError, match="Failed to start"):
            await conn.connect()
        assert conn.process is None


@pytest.mark.asyncio
async def test_notification_handler_lifecycle(config, mock_process):
    """Test registration and handling of notification handlers."""
    notifications = []
    
    async def handler(params):
        notifications.append(params)
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        conn = MCPConnection(config)
        await conn.connect()
        
        # Register handler and verify registration
        conn.register_notification_handler("test", handler)
        assert "test" in conn._notification_handlers
        
        # Queue a notification in the mock process's response queue
        mock_process.responses.append({
            "method": "test",
            "params": {"value": 123}
        })
        
        # Wait for notification processing
        await asyncio.sleep(0.1)
        assert len(notifications) == 1
        assert notifications[0] == {"value": 123}


@pytest.mark.asyncio
async def test_close_error_handling(config, mock_process):
    """Test error handling during close."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        conn = MCPConnection(config)
        await conn.connect()
        
        # Replace kill method with one that raises an error
        original_kill = mock_process.kill
        def failing_kill():
            raise ProcessLookupError("Process already dead")
        mock_process.kill = failing_kill
        
        try:
            # Close should handle the error gracefully
            await conn.close()
            assert conn.process is None
        finally:
            # Restore original kill method for cleanup
            mock_process.kill = original_kill


@pytest.mark.asyncio
async def test_progress_callback(config, mock_process):
    """Test progress callback handling."""
    progress_updates = []
    
    def progress_callback(progress):
        progress_updates.append(progress)
    
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPClient("test", config, progress_callback=progress_callback)
        await client.connect()
        
        # Queue a progress notification in the mock process's response queue
        mock_process.responses.append({
            "method": "$/progress",
            "params": {
                "operation_id": "test_op_1",
                "progress": 0.5,
                "message": "Processing...",
                "data": {"step": 1},
                "is_final": False
            }
        })
        
        # Wait for progress processing
        await asyncio.sleep(0.1)
        assert len(progress_updates) == 1
        assert progress_updates[0].operation_id == "test_op_1"
        assert progress_updates[0].progress == 0.5
        assert progress_updates[0].message == "Processing..."
        assert progress_updates[0].data == {"step": 1}
        assert not progress_updates[0].is_final


@pytest.mark.asyncio
async def test_cancel_request(config, mock_process):
    """Test cancellation of requests."""
    with patch("asyncio.create_subprocess_exec", return_value=mock_process):
        client = MCPClient("test", config)
        await client.connect()
        
        # Queue the initial response that indicates the request is in progress
        mock_process.responses.append({
            "jsonrpc": "2.0",
            "method": "$/progress",
            "params": {
                "operation_id": "test_op",
                "progress": 0.5,
                "message": "Processing..."
            }
        })
        
        # Start the request
        request_gen = client.execute("test", {"param": "value"})
        request_task = asyncio.create_task(anext(request_gen))
        
        # Wait for the request to be processed (slightly longer than mock's 0.01s delay)
        await asyncio.sleep(0.02)
        
        # Queue the error response that will be returned after cancellation
        mock_process.responses.append({
            "jsonrpc": "2.0",
            "id": 2,  # This will be the ID of our execute request
            "error": {
                "code": MCPErrorCode.INTERNAL_ERROR,
                "message": "Operation cancelled"
            }
        })
        
        # Send the cancellation request
        await client.cancel(2)  # Cancel request ID 2
        
        # Verify the cancellation request was sent
        cancel_requests = [
            msg for msg in mock_process.processed_messages
            if msg.get("method") == "$/cancel"
        ]
        assert len(cancel_requests) == 1
        assert cancel_requests[0]["params"]["id"] == 2
        
        # Verify the original request receives the cancellation error
        with pytest.raises(MCPError) as exc_info:
            await request_task
        assert exc_info.value.code == MCPErrorCode.INTERNAL_ERROR
        assert "Operation cancelled" in str(exc_info.value)


        assert "Operation cancelled" in str(exc_info.value) 