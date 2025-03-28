"""MCP registry implementation."""

import json
from typing import Dict, Any, Optional, Callable, Awaitable
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
            
    async def execute(self, server: str, method: str, params: Dict[str, Any]) -> Any:
        """Execute a method on a specific MCP server."""
        if server not in self.clients:
            raise ValueError(f"Unknown MCP server: {server}")
            
        client = self.clients[server]
        
        # Ensure client is connected and initialized
        if not client._initialized:
            await client.connect()
        
        # Execute method
        async for result in client.execute(method, params):
            return result
            
    async def cancel(self, server: str, message_id: int):
        """Cancel an ongoing operation on a specific server."""
        if server not in self.clients:
            raise ValueError(f"Unknown MCP server: {server}")
            
        await self.clients[server].cancel(message_id)
            
    async def close(self):
        """Close all MCP client connections."""
        for client in self.clients.values():
            await client.close()