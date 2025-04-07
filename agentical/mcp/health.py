"""Server health monitoring implementation."""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass
class ServerHealth:
    """Track server connection health."""

    last_heartbeat: float = 0.0
    consecutive_failures: int = 0
    is_connected: bool = False
    reconnection_attempt: int = 0
    last_error: str | None = None


class ServerReconnector(Protocol):
    """Protocol for server reconnection handlers."""

    async def reconnect(self, server_name: str) -> bool:
        """Attempt to reconnect to a server.

        Args:
            server_name: Name of the server to reconnect to

        Returns:
            bool: True if reconnection was successful, False otherwise
        """
        ...


class ServerCleanupHandler(Protocol):
    """Protocol for server cleanup handlers."""

    async def cleanup(self, server_name: str) -> None:
        """Clean up server resources.

        Args:
            server_name: Name of the server to clean up
        """
        ...


class HealthMonitor:
    """Monitors and manages server connection health."""

    def __init__(
        self,
        heartbeat_interval: float,
        max_heartbeat_miss: int,
        reconnector: ServerReconnector,
        cleanup_handler: ServerCleanupHandler,
    ):
        """Initialize the health monitor.

        Args:
            heartbeat_interval: Time in seconds between heartbeat checks
            max_heartbeat_miss: Maximum number of consecutive heartbeat misses 
                before reconnection
            reconnector: Handler for server reconnection attempts
            cleanup_handler: Handler for cleaning up server resources
        """
        self.heartbeat_interval = heartbeat_interval
        self.max_heartbeat_miss = max_heartbeat_miss
        self.reconnector = reconnector
        self.cleanup_handler = cleanup_handler
        self.server_health: dict[str, ServerHealth] = {}
        self._monitor_task: asyncio.Task | None = None

    def register_server(self, server_name: str) -> None:
        """Register a new server for health monitoring.

        Args:
            server_name: Name of the server to monitor
        """
        if server_name not in self.server_health:
            self.server_health[server_name] = ServerHealth()

    def update_heartbeat(self, server_name: str) -> None:
        """Update the heartbeat timestamp for a server.

        Args:
            server_name: Name of the server to update
        """
        if server_name in self.server_health:
            self.server_health[server_name].last_heartbeat = time.time()
            self.server_health[server_name].consecutive_failures = 0
            self.server_health[server_name].is_connected = True

    def mark_connection_failed(self, server_name: str, error: str) -> None:
        """Mark a server connection as failed.

        Args:
            server_name: Name of the server that failed
            error: Error message describing the failure
        """
        if server_name in self.server_health:
            health = self.server_health[server_name]
            health.is_connected = False
            health.last_error = error
            health.consecutive_failures += 1

    async def _monitor_servers(self) -> None:
        """Monitor server connections and attempt reconnection if needed."""
        while True:
            try:
                current_time = time.time()
                for server_name, health in self.server_health.items():
                    if not health.is_connected:
                        continue

                    time_since_heartbeat = current_time - health.last_heartbeat
                    if time_since_heartbeat > self.heartbeat_interval:
                        health.consecutive_failures += 1
                        logger.warning(
                            "Server %s missed heartbeat. Consecutive failures: %d",
                            server_name,
                            health.consecutive_failures,
                        )

                        if health.consecutive_failures >= self.max_heartbeat_miss:
                            logger.error(
                                "Server %s connection appears dead. "
                                "Initiating reconnection.",
                                server_name,
                            )
                            health.is_connected = False
                            await self.cleanup_handler.cleanup(server_name)

                            try:
                                success = await self.reconnector.reconnect(server_name)
                                if success:
                                    health.consecutive_failures = 0
                                    health.is_connected = True
                                    health.last_heartbeat = time.time()
                                    logger.info(
                                        "Successfully reconnected to %s", server_name
                                    )
                                else:
                                    health.last_error = "Reconnection failed"
                                    logger.error(
                                        "Failed to reconnect to %s", server_name
                                    )
                            except Exception as e:
                                health.last_error = str(e)
                                logger.error(
                                    "Error during reconnection to %s: %s",
                                    server_name,
                                    str(e),
                                )

                await asyncio.sleep(self.heartbeat_interval / 2)
            except Exception as e:
                logger.error("Error in health monitor: %s", str(e))
                await asyncio.sleep(self.heartbeat_interval)

    def start_monitoring(self) -> None:
        """Start the server health monitoring task."""
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor_servers())
            logger.info("Started server health monitoring")

    def stop_monitoring(self) -> None:
        """Stop the server health monitoring task."""
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            logger.info("Stopped server health monitoring")
