"""MCPToolProvider implementation using the new LLM Layer abstraction."""

import asyncio
import json
from pathlib import Path
from typing import Dict, Optional, List, Any

from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool as MCPTool
from mcp.types import CallToolResult

from agentical.core import LLMBackend


class MCPToolProvider:
    """Main facade for integrating LLMs with MCP tools.
    
    This class follows the architecture diagram's Integration Layer, coordinating
    between the LLM Layer and MCP Layer.
    """
    
    def __init__(self, llm_backend: LLMBackend):
        """Initialize the MCP Tool Provider.
        
        Args:
            llm_backend: LLMBackend instance to use for processing queries.
            
        Raises:
            TypeError: If llm_backend is None or not an instance of LLMBackend.
        """
        if not isinstance(llm_backend, LLMBackend):
            raise TypeError("llm_backend must be an instance of LLMBackend")
            
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()
        self.available_servers: Dict[str, dict] = {}
        self.llm_backend = llm_backend
        self.tools: List[MCPTool] = []
        
    @staticmethod
    def load_mcp_config(config_path: str | Path) -> Dict[str, dict]:
        """Load MCP configurations from a JSON file.
        
        Args:
            config_path: Path to the MCP configuration file
            
        Returns:
            Dict of server names to their configurations
        """
        with open(config_path) as f:
            config = json.load(f)
            
        # Validate each server configuration
        for server_name, server_config in config.items():
            if not isinstance(server_config, dict):
                raise ValueError(f"Configuration for {server_name} must be a dictionary")
            if "command" not in server_config:
                raise ValueError(f"Configuration for {server_name} must contain 'command' field")
            if "args" not in server_config or not isinstance(server_config["args"], list):
                raise ValueError(f"Configuration for {server_name} must contain 'args' as a list")
                
        return config

    def list_available_servers(self) -> List[str]:
        """List all available MCP servers from the loaded configuration."""
        return list(self.available_servers.keys())

    async def mcp_connect(self, server_name: str):
        """Connect to a specific MCP server by name.
        
        Args:
            server_name: Name of the server as defined in the configuration
            
        Raises:
            ValueError: If server_name is invalid or configuration is incomplete
            TypeError: If configuration values are of incorrect type
        """
        if not isinstance(server_name, str):
            raise TypeError(f"server_name must be a string, got {type(server_name)}")
            
        if not server_name:
            raise ValueError("server_name cannot be empty")
            
        if server_name not in self.available_servers:
            raise ValueError(f"Unknown server: {server_name}. Available servers: {self.list_available_servers()}")
            
        config = self.available_servers[server_name]
        
        # Validate required configuration fields
        if not isinstance(config, dict):
            raise TypeError(f"Configuration for {server_name} must be a dictionary")
            
        if "command" not in config:
            raise ValueError(f"Configuration for {server_name} missing required 'command' field")
            
        if not isinstance(config["command"], str):
            raise TypeError(f"'command' for {server_name} must be a string")
            
        if "args" not in config:
            raise ValueError(f"Configuration for {server_name} missing required 'args' field")
            
        if not isinstance(config["args"], list):
            raise TypeError(f"'args' for {server_name} must be a list")
        
        # Create server parameters with validated fields
        params = {
            "command": config["command"],
            "args": config["args"]
        }
        
        # Only include env if it exists and is a dictionary
        if "env" in config:
            if not isinstance(config["env"], dict):
                raise TypeError(f"'env' for {server_name} must be a dictionary")
            params["env"] = config["env"]
            
        try:
            server_params = StdioServerParameters(**params)
        except Exception as e:
            raise ValueError(f"Failed to create server parameters: {str(e)}")

        try:
            # Connect to the server
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            
            self.stdio, self.write = stdio_transport
            
            # Initialize session
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(self.stdio, self.write)
            )
            
            # Initialize and get tools
            await self.session.initialize()
            response = await self.session.list_tools()
            
            print(f"\nConnected to server '{server_name}' with tools:", 
                  [tool.name for tool in response.tools])
            
            # Store MCP tools directly
            self.tools = response.tools
            
        except Exception as e:
            await self.cleanup()  # Ensure resources are cleaned up on error
            raise ConnectionError(f"Failed to connect to server '{server_name}': {str(e)}")

    async def interactive_server_selection(self) -> str:
        """Interactively prompt the user to select an MCP server.
        
        Returns:
            Selected server name
        """
        servers = self.list_available_servers()
        
        if not servers:
            raise ValueError("No MCP servers available in configuration")
            
        print("\nAvailable MCP servers:")
        for idx, server in enumerate(servers, 1):
            print(f"{idx}. {server}")
            
        while True:
            try:
                choice = input("\nSelect a server (enter number): ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(servers):
                    return servers[idx]
                print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

    async def process_query(self, query: str) -> str:
        """Process a user query using the configured LLM backend.
        
        Args:
            query: The user's input query
            
        Returns:
            The response generated by the LLM
        """
        if not self.session:
            raise ValueError("Not connected to any MCP server. Please select and connect to a server first.")

        # Execute tool directly with MCP types
        async def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> CallToolResult:
            return await self.session.call_tool(tool_name, tool_args)

        # Process the query using the LLM backend with MCP tools directly
        return await self.llm_backend.process_query(
            query=query,
            tools=self.tools,
            execute_tool=execute_tool
        )

    async def cleanup(self):
        """Clean up resources."""
        if self.exit_stack:
            await self.exit_stack.aclose() 