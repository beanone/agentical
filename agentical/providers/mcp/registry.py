"""MCP registry implementation."""

import json
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
        with open(self.config_path) as f:
            data = json.load(f)
            self.config = MCPServerConfig(**data)
            
        # Initialize clients
        for server_id, server_config in self.config.mcpServers.items():
            self.clients[server_id] = MCPClient(
                server_id,
                server_config,
                self.progress_callback
            )
            
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
            raise ValueError(f"Unknown MCP server: {server}")
            
        client = self.clients[server]
        
        # Ensure client is connected and initialized
        if not client._initialized:
            await client.connect()
        
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
            raise ValueError(f"Unknown MCP server: {server}")
            
        await self.clients[server].cancel(request_id)
            
    async def close(self):
        """Close all MCP client connections."""
        for client in self.clients.values():
            await client.close()