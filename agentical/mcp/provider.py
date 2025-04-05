"""MCPToolProvider implementation using the new LLM Layer abstraction.

This module implements the main integration layer between LLM backends and MCP tools.
It provides a robust facade that manages server connections, tool discovery, and
query processing while maintaining connection health and proper resource cleanup.

Key Features:
- Automatic server connection management
- Health monitoring with automatic reconnection
- Tool discovery and management
- Query processing with LLM integration
- Proper resource cleanup

Example:
    ```python
    from agentical.api import LLMBackend
    from agentical.mcp import MCPToolProvider
    
    async def process_queries():
        # Initialize provider
        provider = MCPToolProvider(LLMBackend())
        
        # Load and verify configuration
        config = provider.load_mcp_config("mcp_config.json")
        
        try:
            # Connect to servers
            await provider.mcp_connect_all()
            
            # Process queries
            response = await provider.process_query(
                "What files are in the current directory?"
            )
            print(response)
        finally:
            # Clean up resources
            await provider.cleanup_all()
    ```

Implementation Notes:
    - Uses connection manager for robust server connections
    - Implements health monitoring with automatic recovery
    - Maintains tool registry for efficient dispatch
    - Provides comprehensive error handling
    - Ensures proper resource cleanup
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple
import time
import asyncio

from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.types import Tool as MCPTool
from mcp.types import CallToolResult
from pydantic import ValidationError

from agentical.api import LLMBackend
from agentical.mcp.health import HealthMonitor, ServerReconnector, ServerCleanupHandler
from agentical.mcp.schemas import MCPConfig, ServerConfig
from agentical.mcp.connection import MCPConnectionManager

logger = logging.getLogger(__name__)

class MCPToolProvider(ServerReconnector, ServerCleanupHandler):
    """Main facade for integrating LLMs with MCP tools.
    
    This class follows the architecture diagram's Integration Layer, coordinating
    between the LLM Layer and MCP Layer. It manages server connections, tool
    discovery, and query processing while ensuring robust operation through
    health monitoring and automatic recovery.
    
    Attributes:
        HEARTBEAT_INTERVAL (int): Time in seconds between health checks
        MAX_HEARTBEAT_MISS (int): Maximum missed heartbeats before reconnection
        connection_manager (MCPConnectionManager): Manages server connections
        available_servers (Dict[str, ServerConfig]): Available server configurations
        tools_by_server (Dict[str, List[MCPTool]]): Tools indexed by server
        all_tools (List[MCPTool]): Combined list of all available tools
        
    Implementation Notes:
        - Implements ServerReconnector and ServerCleanupHandler protocols
        - Uses AsyncExitStack for proper resource management
        - Maintains tool registry for efficient dispatch
        - Provides automatic server health monitoring
        - Ensures proper cleanup of all resources
        
    Example:
        ```python
        provider = MCPToolProvider(llm_backend)
        provider.available_servers = provider.load_mcp_config("config.json")
        
        try:
            await provider.mcp_connect("main_server")
            response = await provider.process_query("List files")
            print(response)
        finally:
            await provider.cleanup_all()
        ```
    """
    
    # Health monitoring settings
    HEARTBEAT_INTERVAL = 30  # seconds
    MAX_HEARTBEAT_MISS = 2
    
    def __init__(self, llm_backend: LLMBackend):
        """Initialize the MCP Tool Provider.
        
        Sets up the provider with the specified LLM backend and initializes
        all necessary components including connection management and health
        monitoring.
        
        Args:
            llm_backend: LLMBackend instance to use for processing queries.
                        Must be a valid instance implementing the LLMBackend
                        interface.
            
        Raises:
            TypeError: If llm_backend is None or not an instance of LLMBackend.
            
        Note:
            The provider must be properly initialized with server configurations
            before attempting to connect to any servers.
        """
        logger.debug("Initializing MCPToolProvider")
        if not isinstance(llm_backend, LLMBackend):
            logger.error("Invalid llm_backend type: %s", type(llm_backend))
            raise TypeError("llm_backend must be an instance of LLMBackend")
            
        self.exit_stack = AsyncExitStack()
        self.connection_manager = MCPConnectionManager(self.exit_stack)
        self.available_servers: Dict[str, ServerConfig] = {}
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
    def load_mcp_config(config_path: str | Path) -> Dict[str, ServerConfig]:
        """Load MCP configurations from a JSON file.
        
        Loads and validates server configurations from a JSON file. The file
        should contain a mapping of server names to their configurations.
        
        Args:
            config_path: Path to the MCP configuration file. Can be either a
                       string path or Path object.
            
        Returns:
            Dict mapping server names to their validated configurations.
            
        Raises:
            ValidationError: If configuration format is invalid
            JSONDecodeError: If JSON parsing fails
            FileNotFoundError: If config file doesn't exist
            
        Example config format:
            ```json
            {
                "main_server": {
                    "command": "server_binary",
                    "args": ["--port", "8080"],
                    "is_websocket": false,
                    "env": {"DEBUG": "1"}
                }
            }
            ```
        """
        logger.info("Loading MCP configuration from: %s", config_path)
        try:
            with open(config_path) as f:
                raw_config = json.load(f)
            
            # Parse and validate configuration using Pydantic schema
            config = MCPConfig(servers=raw_config)
            logger.info("Successfully loaded configuration with %d servers", len(config.servers))
            return config.servers
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse configuration file: %s", str(e))
            raise
        except ValidationError as e:
            logger.error("Invalid configuration format: %s", str(e))
            raise
        except Exception as e:
            logger.error("Error loading configuration: %s", str(e))
            raise

    def list_available_servers(self) -> List[str]:
        """List all available MCP servers from the loaded configuration.
        
        Returns:
            List of server names that are available for connection.
            
        Note:
            This only lists servers that have been configured, not necessarily
            ones that are currently connected.
        """
        servers = list(self.available_servers.keys())
        logger.debug("Available servers: %s", servers)
        return servers

    async def reconnect(self, server_name: str) -> bool:
        """Implement ServerReconnector protocol.
        
        Attempts to reconnect to a server that has been disconnected or is
        experiencing connection issues. This is typically called by the
        health monitor when connection problems are detected.
        
        Args:
            server_name: Name of the server to reconnect to
            
        Returns:
            bool: True if reconnection was successful, False otherwise
            
        Note:
            - Updates tool registry after successful reconnection
            - Updates health monitor state
            - Handles cleanup on failed reconnection attempts
        """
        try:
            if server_name in self.available_servers:
                config = self.available_servers[server_name]
                session = await self.connection_manager.connect(server_name, config)
                
                # Initialize and get tools
                response = await session.list_tools()
                
                # Update health monitor
                self.health_monitor.update_heartbeat(server_name)
                
                # Store MCP tools for this server
                self.tools_by_server[server_name] = response.tools
                self.all_tools.extend(response.tools)
                
                tool_names = [tool.name for tool in response.tools]
                logger.info("Connected to server '%s' with tools: %s", server_name, tool_names)
                
                # Start health monitoring
                self.health_monitor.start_monitoring()
                return True
        except Exception as e:
            logger.error("Reconnection failed for %s: %s", server_name, str(e))
            return False
        return False

    async def cleanup(self, server_name: str = None) -> None:
        """Clean up server resources.
        
        This method serves two purposes:
        1. When called with server_name, it implements the ServerCleanupHandler protocol
           by cleaning up resources for a specific server.
        2. When called without server_name, it acts as a convenience method to
           clean up all provider resources.
        
        Args:
            server_name: Optional name of the server to clean up. If not provided,
                        cleans up all resources.
            
        Note:
            - Implements ServerCleanupHandler protocol when server_name is provided
            - Calls cleanup_all() when server_name is None
            - Safe to call multiple times
            - Handles cleanup errors gracefully
        """
        if server_name is not None:
            await self.cleanup_server(server_name)
        else:
            await self.cleanup_all()

    async def cleanup_server(self, server_name: str) -> None:
        """Clean up a specific server's resources.
        
        Implements the actual server cleanup logic, removing server tools
        and cleaning up connection resources.
        
        Args:
            server_name: Name of the server to clean up
            
        Note:
            - Removes server tools from the registry
            - Cleans up connection resources
            - Safe to call multiple times
            - Handles cleanup errors gracefully
        """
        try:
            # Remove server-specific tools
            if server_name in self.tools_by_server:
                server_tools = self.tools_by_server[server_name]
                self.all_tools = [t for t in self.all_tools if t not in server_tools]
                del self.tools_by_server[server_name]
            
            # Clean up connection
            await self.connection_manager.cleanup(server_name)
            
        except Exception as e:
            logger.error("Error during server cleanup for %s: %s", server_name, str(e))

    async def cleanup_all(self) -> None:
        """Clean up all provider resources.
        
        This is the main cleanup method for the provider, cleaning up all
        resources including servers, connections, and internal state.
        
        Note:
            - Calls cleanup_all() internally
            - Safe to call multiple times
            - Handles cleanup errors gracefully
            - Ensures proper task cancellation
        """
        logger.info("Starting provider cleanup")
        
        try:
            # First stop health monitoring to prevent reconnection attempts
            if hasattr(self, 'health_monitor'):
                try:
                    self.health_monitor.stop_monitoring()
                    logger.debug("Health monitoring stopped")
                except Exception as e:
                    logger.error("Error stopping health monitor: %s", str(e))
            
            # Clean up all connections
            if hasattr(self, 'connection_manager'):
                try:
                    await self.connection_manager.cleanup_all()
                    logger.debug("All connections cleaned up")
                except Exception as e:
                    logger.error("Error during connection cleanup: %s", str(e))
            
            # Close the exit stack last
            if hasattr(self, 'exit_stack'):
                try:
                    # Create a task group for cleanup
                    async with asyncio.TaskGroup() as tg:
                        # Cancel any pending tasks
                        tasks = [task for task in asyncio.all_tasks() 
                                if task is not asyncio.current_task()]
                        for task in tasks:
                            task.cancel()
                        
                        # Create a task for closing the exit stack
                        tg.create_task(self.exit_stack.aclose())
                    logger.debug("Exit stack closed successfully")
                except* asyncio.CancelledError:
                    logger.info("Task cancelled during cleanup")
                except* Exception as e:
                    logger.error("Error closing exit stack: %s", str(e))
                
        except Exception as e:
            logger.error("Error during provider cleanup: %s", str(e))
            
        finally:
            # Clear all stored references
            if hasattr(self, 'tools_by_server'):
                self.tools_by_server.clear()
            if hasattr(self, 'all_tools'):
                self.all_tools.clear()
            logger.debug("All provider resources cleared")

    async def mcp_connect(self, server_name: str):
        """Connect to a specific MCP server by name.
        
        Establishes a connection to a server and initializes its tools.
        This is the main method for connecting to individual servers.
        
        Args:
            server_name: Name of the server as defined in the configuration.
                       Must be a non-empty string matching a configured server.
            
        Raises:
            ValueError: If server_name is invalid or not found in configuration
            ConnectionError: If connection fails after retries
            
        Note:
            - Registers server with health monitor
            - Updates tool registry on successful connection
            - Handles cleanup on failed connection attempts
            - Starts health monitoring if not already started
        """
        logger.info("Connecting to server: %s", server_name)
        
        if not isinstance(server_name, str) or not server_name.strip():
            logger.error("Invalid server_name: %s", server_name)
            raise ValueError("server_name must be a non-empty string")
            
        if server_name not in self.available_servers:
            logger.error("Unknown server: %s. Available: %s", server_name, self.list_available_servers())
            raise ValueError(f"Unknown server: {server_name}. Available servers: {self.list_available_servers()}")
            
        # Register with health monitor
        self.health_monitor.register_server(server_name)
        
        try:
            # Connect using connection manager
            session = await self.connection_manager.connect(server_name, self.available_servers[server_name])
            
            # Initialize and get tools
            response = await session.list_tools()
            
            # Update health monitor
            self.health_monitor.update_heartbeat(server_name)
            
            # Store MCP tools for this server
            self.tools_by_server[server_name] = response.tools
            self.all_tools.extend(response.tools)
            
            tool_names = [tool.name for tool in response.tools]
            logger.info("Connected to server '%s' with tools: %s", server_name, tool_names)
            
            # Start health monitoring
            self.health_monitor.start_monitoring()
            
        except Exception as e:
            logger.error("Failed to connect to server %s: %s", server_name, str(e))
            await self.cleanup_server(server_name)
            raise ConnectionError(f"Failed to connect to server '{server_name}': {str(e)}")

    async def mcp_connect_all(self) -> List[Tuple[str, Optional[Exception]]]:
        """Connect to all available MCP servers concurrently.
        
        Attempts to connect to all configured servers, collecting results
        and errors for each connection attempt.
        
        Returns:
            List of tuples containing:
                - str: Server name
                - Optional[Exception]: None if successful, Exception if failed
            
        Note:
            - Connects to servers sequentially to avoid context issues
            - Returns partial success if some connections fail
            - Does not raise exceptions for individual failures
            
        Example:
            ```python
            results = await provider.mcp_connect_all()
            for server_name, error in results:
                if error:
                    print(f"Failed to connect to {server_name}: {error}")
                else:
                    print(f"Successfully connected to {server_name}")
            ```
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
        
        Routes the query through the LLM backend, providing access to all
        available tools across connected servers. The LLM can choose which
        tools to use and how to combine them to answer the query.
        
        Args:
            query: The user's input query to process
            
        Returns:
            The response generated by the LLM
            
        Raises:
            ValueError: If no servers are connected
            Exception: If query processing fails
            
        Note:
            - Automatically routes tool calls to appropriate servers
            - Handles tool execution errors
            - Updates health monitoring on successful tool execution
        """
        logger.info("Processing query: %s", query)
        if not self.tools_by_server:
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
                        session = self.connection_manager.sessions[server_name]
                        result = await session.call_tool(tool_name, tool_args)
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