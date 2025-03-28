"""MCP registry implementation."""

import json
import logging
from typing import Dict, Any, Optional, Callable, Awaitable, AsyncIterator
from .models import MCPServerConfig, MCPConfig, MCPProgress
from .client import MCPClient, ProgressCallback


class MCPRegistry:
    """Registry for managing MCP clients."""
    
    def __init__(
        self,
        config_path: str,
        progress_callback: Optional[ProgressCallback] = None
    ):
        self._logger = logging.getLogger(f"{__name__}.MCPRegistry")
        self._logger.info("[lifecycle.registry] Starting: Registry initialization")
        
        self.config_path = config_path
        self.config: Optional[MCPServerConfig] = None
        self.clients: Dict[str, MCPClient] = {}
        self.progress_callback = progress_callback
        
    @classmethod
    def from_json(cls, path: str, progress_callback: Optional[ProgressCallback] = None) -> "MCPRegistry":
        """Create a new registry from a JSON configuration file."""
        registry = cls(path, progress_callback)
        registry.load_config()
        return registry
        
    def load_config(self):
        """Load the MCP server configuration from JSON."""
        self._logger.info("[lifecycle.registry] Starting: Configuration loading")
        try:
            with open(self.config_path) as f:
                data = json.load(f)
                self.config = MCPServerConfig(**data)
                
            # Initialize clients
            for server_id, server_config in self.config.mcpServers.items():
                self._logger.debug("Creating client for server %s", server_id)
                self.clients[server_id] = MCPClient(
                    server_id,
                    server_config,
                    self.progress_callback
                )
            self._logger.info("[lifecycle.registry] Ready: Configuration loaded")
        except (IOError, json.JSONDecodeError) as e:
            self._logger.error("Failed to load configuration - %s", str(e))
            raise
        except Exception as e:
            self._logger.error("Unexpected error loading configuration - %s", str(e))
            raise
            
    async def execute(self, server: str, method: str, params: Dict[str, Any]) -> AsyncIterator[Any]:
        """Execute a method on a specific MCP server.
        
        Args:
            server: The ID of the MCP server to execute on.
            method: The method name to execute.
            params: The parameters to pass to the method.
            
        Returns:
            An async iterator yielding results from the method execution.
            
        Raises:
            ValueError: If the server ID is not found.
            MCPError: If the method execution fails.
        """
        if server not in self.clients:
            self._logger.error("Unknown server %s", server)
            raise ValueError(f"Unknown MCP server: {server}")
            
        client = self.clients[server]
        
        # Ensure client is connected and initialized
        if not client._initialized:
            self._logger.debug("Initializing client for server %s", server)
            await client.connect()
        
        self._logger.debug("Executing method %s on server %s", method, server)
        # Execute method and yield all results
        async for result in client.execute(method, params):
            yield result
            
    async def cancel(self, server: str, request_id: int):
        """Cancel an ongoing request on a specific server.
        
        Args:
            server: The ID of the MCP server to cancel on.
            request_id: The ID of the request to cancel.
            
        Raises:
            ValueError: If the server ID is not found.
            MCPError: If the cancellation fails.
        """
        if server not in self.clients:
            self._logger.error("Unknown server %s", server)
            raise ValueError(f"Unknown MCP server: {server}")
            
        self._logger.debug("Cancelling request %d on server %s", request_id, server)
        await self.clients[server].cancel(request_id)
            
    async def close(self):
        """Close all MCP client connections."""
        self._logger.info("[lifecycle.registry] Shutdown: Starting")
        for client in self.clients.values():
            await client.close()
        self._logger.info("[lifecycle.registry] Shutdown: Completed")