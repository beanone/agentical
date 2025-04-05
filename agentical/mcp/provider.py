"""MCPToolProvider implementation using the new LLM Layer abstraction."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple
import backoff
import time

from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool as MCPTool
from mcp.types import CallToolResult

from agentical.api import LLMBackend
from agentical.mcp.health import HealthMonitor, ServerReconnector, ServerCleanupHandler

logger = logging.getLogger(__name__)

class MCPToolProvider(ServerReconnector, ServerCleanupHandler):
    """Main facade for integrating LLMs with MCP tools.
    
    This class follows the architecture diagram's Integration Layer, coordinating
    between the LLM Layer and MCP Layer.
    """
    
    # Connection settings
    MAX_RETRIES = 3
    BASE_DELAY = 1.0
    HEARTBEAT_INTERVAL = 30  # seconds
    MAX_HEARTBEAT_MISS = 2
    
    def __init__(self, llm_backend: LLMBackend):
        """Initialize the MCP Tool Provider.
        
        Args:
            llm_backend: LLMBackend instance to use for processing queries.
            
        Raises:
            TypeError: If llm_backend is None or not an instance of LLMBackend.
        """
        logger.debug("Initializing MCPToolProvider")
        if not isinstance(llm_backend, LLMBackend):
            logger.error("Invalid llm_backend type: %s", type(llm_backend))
            raise TypeError("llm_backend must be an instance of LLMBackend")
            
        self.sessions: Dict[str, ClientSession] = {}
        self.stdios: Dict[str, Any] = {}
        self.writes: Dict[str, Any] = {}
        self.exit_stack = AsyncExitStack()
        self.available_servers: Dict[str, dict] = {}
        self.llm_backend = llm_backend
        self.tools_by_server: Dict[str, List[MCPTool]] = {}
        self.all_tools: List[MCPTool] = []
        
        # Initialize health monitor
        self.health_monitor = HealthMonitor(
            heartbeat_interval=self.HEARTBEAT_INTERVAL,
            max_heartbeat_miss=self.MAX_HEARTBEAT_MISS,
            reconnector=self,
            cleanup_handler=self
        )
        logger.debug("MCPToolProvider initialized successfully")
        
    @staticmethod
    def load_mcp_config(config_path: str | Path) -> Dict[str, dict]:
        """Load MCP configurations from a JSON file.
        
        Args:
            config_path: Path to the MCP configuration file
            
        Returns:
            Dict of server names to their configurations
        """
        logger.info("Loading MCP configuration from: %s", config_path)
        try:
            with open(config_path) as f:
                config = json.load(f)
            
            # Validate each server configuration
            for server_name, server_config in config.items():
                logger.debug("Validating configuration for server: %s", server_name)
                if not isinstance(server_config, dict):
                    logger.error("Invalid configuration type for %s: %s", server_name, type(server_config))
                    raise ValueError(f"Configuration for {server_name} must be a dictionary")
                if "command" not in server_config:
                    logger.error("Missing 'command' in configuration for %s", server_name)
                    raise ValueError(f"Configuration for {server_name} must contain 'command' field")
                if "args" not in server_config or not isinstance(server_config["args"], list):
                    logger.error("Invalid or missing 'args' in configuration for %s", server_name)
                    raise ValueError(f"Configuration for {server_name} must contain 'args' as a list")
                    
            logger.info("Successfully loaded configuration with %d servers", len(config))
            return config
        except json.JSONDecodeError as e:
            logger.error("Failed to parse configuration file: %s", str(e))
            raise
        except Exception as e:
            logger.error("Error loading configuration: %s", str(e))
            raise

    def list_available_servers(self) -> List[str]:
        """List all available MCP servers from the loaded configuration."""
        servers = list(self.available_servers.keys())
        logger.debug("Available servers: %s", servers)
        return servers

    async def reconnect(self, server_name: str) -> bool:
        """Implement ServerReconnector protocol."""
        try:
            if server_name in self.available_servers:
                config = self.available_servers[server_name]
                if any("ws" in arg for arg in config["args"]) or server_name == "server-sequential-thinking":
                    await self._handle_websocket_server(server_name, config)
                else:
                    params = {
                        "command": config["command"],
                        "args": config["args"]
                    }
                    if "env" in config:
                        params["env"] = config["env"]
                    server_params = StdioServerParameters(**params)
                    await self._connect_with_retry(server_name, server_params)
                return True
        except Exception as e:
            logger.error("Reconnection failed for %s: %s", server_name, str(e))
            return False
        return False

    @backoff.on_exception(
        backoff.expo,
        (ConnectionError, TimeoutError),
        max_tries=MAX_RETRIES,
        base=BASE_DELAY
    )
    async def _connect_with_retry(self, server_name: str, server_params: StdioServerParameters):
        """Attempt to connect to a server with exponential backoff retry.
        
        Args:
            server_name: Name of the server to connect to
            server_params: Server connection parameters
            
        Raises:
            ConnectionError: If all connection attempts fail
        """
        try:
            logger.debug("Establishing connection to %s", server_name)
            
            # Register with health monitor
            self.health_monitor.register_server(server_name)
            
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            
            self.stdios[server_name], self.writes[server_name] = stdio_transport
            
            # Initialize session
            logger.debug("Initializing session for %s", server_name)
            self.sessions[server_name] = await self.exit_stack.enter_async_context(
                ClientSession(self.stdios[server_name], self.writes[server_name])
            )
            
            # Initialize and get tools
            await self.sessions[server_name].initialize()
            response = await self.sessions[server_name].list_tools()
            
            # Update health monitor
            self.health_monitor.update_heartbeat(server_name)
            
            tool_names = [tool.name for tool in response.tools]
            logger.info("Connected to server '%s' with tools: %s", server_name, tool_names)
            
            # Store MCP tools for this server
            self.tools_by_server[server_name] = response.tools
            self.all_tools.extend(response.tools)
            logger.debug("Total tools available: %d", len(self.all_tools))
            
            # Start health monitoring
            self.health_monitor.start_monitoring()
            
        except Exception as e:
            logger.error("Connection attempt failed for %s: %s", server_name, str(e))
            self.health_monitor.mark_connection_failed(server_name, str(e))
            await self._cleanup_server(server_name)
            raise ConnectionError(f"Failed to connect to server '{server_name}': {str(e)}")

    async def _cleanup_server(self, server_name: str):
        """Clean up resources for a specific server.
        
        Args:
            server_name: Name of the server to clean up
        """
        logger.info("Cleaning up resources for server: %s", server_name)
        try:
            # Remove server-specific tools from all_tools
            if server_name in self.tools_by_server:
                server_tools = self.tools_by_server[server_name]
                self.all_tools = [t for t in self.all_tools if t not in server_tools]
                del self.tools_by_server[server_name]
            
            # Close and remove session
            if server_name in self.sessions:
                session = self.sessions.pop(server_name)
                if hasattr(session, 'close'):
                    await session.close()
            
            # Clean up stdio and write handlers
            self.stdios.pop(server_name, None)
            self.writes.pop(server_name, None)
            
            logger.debug("Successfully cleaned up resources for %s", server_name)
        except Exception as e:
            logger.error("Error during server cleanup for %s: %s", server_name, str(e))

    async def _handle_websocket_server(self, server_name: str, config: Dict[str, Any]):
        """Handle connection to a WebSocket-based server.
        
        Args:
            server_name: Name of the server
            config: Server configuration
            
        Raises:
            ConnectionError: If connection fails after retries
        """
        logger.info("Detected WebSocket server: %s", server_name)
        
        # Add WebSocket-specific configuration
        params = {
            "command": config["command"],
            "args": config["args"],
            "reconnect_delay": self.BASE_DELAY,
            "max_retries": self.MAX_RETRIES
        }
        
        if "env" in config:
            params["env"] = config["env"]
            
        try:
            server_params = StdioServerParameters(**params)
            await self._connect_with_retry(server_name, server_params)
        except Exception as e:
            logger.error("Failed to connect to WebSocket server %s: %s", server_name, str(e))
            # Ensure cleanup is called for WebSocket server failures
            await self._cleanup_server(server_name)
            raise

    async def mcp_connect(self, server_name: str):
        """Connect to a specific MCP server by name.
        
        Args:
            server_name: Name of the server as defined in the configuration
            
        Raises:
            ValueError: If server_name is invalid or configuration is incomplete
            TypeError: If configuration values are of incorrect type
        """
        logger.info("Connecting to server: %s", server_name)
        
        if not isinstance(server_name, str):
            logger.error("Invalid server_name type: %s", type(server_name))
            raise TypeError(f"server_name must be a string, got {type(server_name)}")
            
        if not server_name:
            logger.error("Empty server_name provided")
            raise ValueError("server_name cannot be empty")
            
        if server_name not in self.available_servers:
            logger.error("Unknown server: %s. Available: %s", server_name, self.list_available_servers())
            raise ValueError(f"Unknown server: {server_name}. Available servers: {self.list_available_servers()}")
            
        config = self.available_servers[server_name]
        logger.debug("Server configuration: %s", config)
        
        # Validate required configuration fields
        if not isinstance(config, dict):
            logger.error("Invalid configuration type for %s: %s", server_name, type(config))
            raise TypeError(f"Configuration for {server_name} must be a dictionary")
            
        if "command" not in config:
            logger.error("Missing 'command' in configuration for %s", server_name)
            raise ValueError(f"Configuration for {server_name} missing required 'command' field")
            
        if not isinstance(config["command"], str):
            logger.error("Invalid command type for %s: %s", server_name, type(config["command"]))
            raise TypeError(f"'command' for {server_name} must be a string")
            
        if "args" not in config:
            logger.error("Missing 'args' in configuration for %s", server_name)
            raise ValueError(f"Configuration for {server_name} missing required 'args' field")
            
        if not isinstance(config["args"], list):
            logger.error("Invalid args type for %s: %s", server_name, type(config["args"]))
            raise TypeError(f"'args' for {server_name} must be a list")
        
        try:
            # Check if this is a WebSocket server
            if any("ws" in arg for arg in config["args"]) or server_name == "server-sequential-thinking":
                await self._handle_websocket_server(server_name, config)
            else:
                # Handle standard stdio server
                params = {
                    "command": config["command"],
                    "args": config["args"]
                }
                if "env" in config:
                    if not isinstance(config["env"], dict):
                        logger.error("Invalid env type for %s: %s", server_name, type(config["env"]))
                        raise TypeError(f"'env' for {server_name} must be a dictionary")
                    params["env"] = config["env"]
                
                server_params = StdioServerParameters(**params)
                await self._connect_with_retry(server_name, server_params)
                
        except Exception as e:
            logger.error("Failed to connect to server %s: %s", server_name, str(e))
            await self.cleanup(server_name)
            raise ConnectionError(f"Failed to connect to server '{server_name}': {str(e)}")

    async def mcp_connect_all(self) -> List[Tuple[str, Optional[Exception]]]:
        """Connect to all available MCP servers concurrently.
        
        Returns:
            List of tuples containing server names and any exceptions that occurred during connection.
            If connection was successful, the exception will be None.
            
        Example:
            results = await provider.mcp_connect_all()
            for server_name, error in results:
                if error:
                    print(f"Failed to connect to {server_name}: {error}")
                else:
                    print(f"Successfully connected to {server_name}")
        """
        # Get list of available servers
        servers = self.list_available_servers()
        logger.info("Connecting to all servers: %s", servers)
        if not servers:
            logger.warning("No servers available to connect to")
            return []

        results = []
        # Connect to each server sequentially to avoid task/context issues
        for server_name in servers:
            try:
                await self.mcp_connect(server_name)
                results.append((server_name, None))
                logger.info("Successfully connected to %s", server_name)
            except Exception as e:
                results.append((server_name, e))
                logger.error("Failed to connect to %s: %s", server_name, str(e))

        logger.info("Completed connecting to all servers. Successful: %d, Failed: %d", 
                   sum(1 for _, e in results if e is None),
                   sum(1 for _, e in results if e is not None))
        return results

    async def process_query(self, query: str) -> str:
        """Process a user query using the configured LLM backend.
        
        Args:
            query: The user's input query
            
        Returns:
            The response generated by the LLM
        """
        logger.info("Processing query: %s", query)
        if not self.sessions:
            logger.error("No active sessions found")
            raise ValueError("Not connected to any MCP server. Please select and connect to a server first.")

        # Execute tool directly with MCP types
        async def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> CallToolResult:
            logger.debug("Executing tool %s with args: %s", tool_name, tool_args)
            # Find which server has this tool
            for server_name, tools in self.tools_by_server.items():
                if any(tool.name == tool_name for tool in tools):
                    logger.debug("Found tool %s in server %s", tool_name, server_name)
                    try:
                        result = await self.sessions[server_name].call_tool(tool_name, tool_args)
                        logger.debug("Tool execution successful: %s", result)
                        return result
                    except Exception as e:
                        logger.error("Tool execution failed: %s", str(e))
                        raise
            
            logger.error("Tool %s not found in any server", tool_name)
            raise ValueError(f"Tool {tool_name} not found in any connected server")

        try:
            # Process the query using all available tools
            logger.debug("Sending query to LLM backend with %d available tools", len(self.all_tools))
            response = await self.llm_backend.process_query(
                query=query,
                tools=self.all_tools,
                execute_tool=execute_tool
            )
            logger.debug("Received response from LLM backend: %s", response)
            return response
        except Exception as e:
            logger.error("Error processing query: %s", str(e))
            raise

    async def cleanup(self, server_name: str) -> None:
        """Implement ServerCleanupHandler protocol."""
        await self._cleanup_server(server_name)

    async def cleanup_all(self):
        """Clean up all resources."""
        if self.exit_stack:
            logger.info("Starting cleanup")
            try:
                # Stop health monitoring
                self.health_monitor.stop_monitoring()
                
                # First cleanup individual servers
                server_names = list(self.sessions.keys())
                for server_name in server_names:
                    await self._cleanup_server(server_name)
                
                # Then close the exit stack which will handle remaining async context cleanup
                await self.exit_stack.aclose()
                logger.debug("Exit stack closed successfully")
            except Exception as e:
                logger.error("Error during cleanup: %s", str(e))
            finally:
                # Clear all stored references
                self.sessions.clear()
                self.stdios.clear()
                self.writes.clear()
                self.tools_by_server.clear()
                self.all_tools.clear()
                logger.debug("All resources cleared") 