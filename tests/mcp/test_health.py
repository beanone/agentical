"""Unit tests for the server health monitoring system.

This module contains tests for the HealthMonitor class and related components,
focusing on server health tracking, reconnection logic, and monitoring behavior.
"""

import asyncio
import logging
import time

import pytest

from agentical.mcp.health import (
    HealthMonitor,
    ServerHealth,
)

logger = logging.getLogger(__name__)


class MockReconnector:
    """Mock implementation of ServerReconnector protocol."""

    def __init__(self, success: bool = True):
        self.reconnect_calls = []
        self.should_succeed = success

    async def reconnect(self, server_name: str) -> bool:
        """Record reconnection attempt and return configured success state."""
        self.reconnect_calls.append(server_name)
        return self.should_succeed


class MockCleanupHandler:
    """Mock implementation of ServerCleanupHandler protocol."""

    def __init__(self):
        self.cleanup_calls = []

    async def cleanup(self, server_name: str) -> None:
        """Record cleanup call."""
        self.cleanup_calls.append(server_name)


@pytest.fixture
def mock_reconnector():
    """Fixture providing a mock reconnector."""
    return MockReconnector()


@pytest.fixture
def mock_cleanup_handler():
    """Fixture providing a mock cleanup handler."""
    return MockCleanupHandler()


@pytest.fixture
async def health_monitor(mock_reconnector, mock_cleanup_handler):
    """Fixture providing a configured HealthMonitor instance."""
    monitor = HealthMonitor(
        heartbeat_interval=1.0,
        max_heartbeat_miss=2,
        reconnector=mock_reconnector,
        cleanup_handler=mock_cleanup_handler,
    )
    yield monitor
    # Ensure monitoring is stopped after each test
    await monitor.stop_monitoring()
    # Double check task is properly cleaned up
    if monitor._monitor_task and not monitor._monitor_task.done():
        logger.warning(
            "Monitor task still running after stop_monitoring, forcing cleanup"
        )
        monitor._monitor_task.cancel()
        try:
            await monitor._monitor_task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_server_registration(health_monitor):
    """Test server registration and initial health state."""
    health_monitor.register_server("test_server")

    assert "test_server" in health_monitor.server_health
    health = health_monitor.server_health["test_server"]
    assert isinstance(health, ServerHealth)
    assert health.last_heartbeat == 0.0
    assert health.consecutive_failures == 0
    assert not health.is_connected
    assert health.last_error is None


@pytest.mark.asyncio
async def test_heartbeat_update(health_monitor):
    """Test heartbeat update functionality."""
    health_monitor.register_server("test_server")
    initial_time = time.time()

    health_monitor.update_heartbeat("test_server")
    health = health_monitor.server_health["test_server"]

    assert health.last_heartbeat >= initial_time
    assert health.consecutive_failures == 0
    assert health.is_connected
    assert health.last_error is None


@pytest.mark.asyncio
async def test_connection_failure_marking(health_monitor):
    """Test marking a server connection as failed."""
    health_monitor.register_server("test_server")
    health_monitor.update_heartbeat("test_server")  # Set initial connected state

    health_monitor.mark_connection_failed("test_server", "Test error")
    health = health_monitor.server_health["test_server"]

    assert not health.is_connected
    assert health.last_error == "Test error"
    assert health.consecutive_failures == 1


@pytest.mark.asyncio
async def test_monitoring_missed_heartbeats(health_monitor):
    """Test monitoring behavior for missed heartbeats."""
    health_monitor.register_server("test_server")
    health_monitor.update_heartbeat("test_server")

    # Start monitoring
    health_monitor.start_monitoring()

    # Wait for more than heartbeat interval * max_misses
    await asyncio.sleep(2.5)  # Slightly longer than 2 heartbeat intervals

    # Verify reconnection was attempted
    assert "test_server" in health_monitor.cleanup_handler.cleanup_calls
    assert "test_server" in health_monitor.reconnector.reconnect_calls

    # Explicitly stop monitoring
    await health_monitor.stop_monitoring()


@pytest.mark.asyncio
async def test_successful_reconnection(health_monitor):
    """Test successful server reconnection."""
    health_monitor.register_server("test_server")
    health_monitor.mark_connection_failed("test_server", "Initial failure")

    # Simulate successful reconnection
    success = await health_monitor.reconnector.reconnect("test_server")
    assert success

    # Update heartbeat to reflect reconnection
    health_monitor.update_heartbeat("test_server")
    health = health_monitor.server_health["test_server"]

    assert health.is_connected
    assert health.consecutive_failures == 0


@pytest.mark.asyncio
async def test_failed_reconnection(
    health_monitor, mock_reconnector, mock_cleanup_handler
):
    """Test failed reconnection attempt."""
    # Configure reconnector to fail
    failing_monitor = HealthMonitor(
        heartbeat_interval=1.0,
        max_heartbeat_miss=2,
        reconnector=MockReconnector(success=False),
        cleanup_handler=mock_cleanup_handler,
    )

    failing_monitor.register_server("test_server")
    failing_monitor.mark_connection_failed("test_server", "Initial failure")

    # Attempt reconnection
    success = await failing_monitor.reconnector.reconnect("test_server")
    assert not success

    health = failing_monitor.server_health["test_server"]
    assert not health.is_connected
    assert health.last_error == "Initial failure"


@pytest.mark.asyncio
async def test_monitoring_task_cancellation(health_monitor):
    """Test proper cancellation of monitoring task."""
    health_monitor.start_monitoring()
    assert health_monitor._monitor_task is not None
    assert not health_monitor._monitor_task.done()

    await health_monitor.stop_monitoring()
    await asyncio.sleep(0.1)  # Give time for cancellation to process

    assert health_monitor._monitor_task.done()


@pytest.mark.asyncio
async def test_multiple_server_monitoring(health_monitor):
    """Test monitoring multiple servers simultaneously."""
    # Register multiple servers
    servers = ["server1", "server2", "server3"]
    for server in servers:
        health_monitor.register_server(server)
        health_monitor.update_heartbeat(server)

    # Start monitoring
    health_monitor.start_monitoring()

    # Wait for heartbeats to be missed
    await asyncio.sleep(2.5)

    # Verify all servers were handled
    for server in servers:
        assert server in health_monitor.cleanup_handler.cleanup_calls
        assert server in health_monitor.reconnector.reconnect_calls

    # Explicitly stop monitoring
    await health_monitor.stop_monitoring()


@pytest.mark.asyncio
async def test_monitor_error_handling():
    """Test error handling in the monitoring loop."""
    mock_reconnector = MockReconnector()
    mock_cleanup = MockCleanupHandler()

    # Create a monitor with a very short interval for testing
    monitor = HealthMonitor(
        heartbeat_interval=0.1,
        max_heartbeat_miss=1,
        reconnector=mock_reconnector,
        cleanup_handler=mock_cleanup,
    )

    # Register a server
    monitor.register_server("test_server")
    monitor.update_heartbeat("test_server")

    # Patch the cleanup handler to raise an exception
    async def raise_error(*args):
        raise Exception("Test error")

    mock_cleanup.cleanup = raise_error

    # Start monitoring
    monitor.start_monitoring()

    # Wait for error to occur and be handled
    await asyncio.sleep(0.3)

    # Verify monitor is still running
    assert not monitor._monitor_task.done()

    # Explicitly stop monitoring
    await monitor.stop_monitoring()


@pytest.mark.asyncio
async def test_concurrent_health_updates(health_monitor):
    """Test concurrent health updates from multiple tasks."""
    server_name = "test_server"
    health_monitor.register_server(server_name)

    async def update_health():
        for _ in range(5):
            health_monitor.update_heartbeat(server_name)
            await asyncio.sleep(0.1)

    # Create multiple concurrent update tasks
    tasks = [update_health() for _ in range(3)]
    await asyncio.gather(*tasks)

    health = health_monitor.server_health[server_name]
    assert health.is_connected
    assert health.consecutive_failures == 0
