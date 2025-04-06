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
    from agentical.mcp import MCPToolProvider, FileBasedMCPConfigProvider
    
    async def process_queries():
        # Initialize provider with config
        config_provider = FileBasedMCPConfigProvider("config.json")
        provider = MCPToolProvider(LLMBackend(), config_provider=config_provider)
        
        try:
            # Initialize and connect
            await provider.initialize()
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

import logging
import time
from typing import Dict, Optional, List, Any, Tuple
import asyncio

from contextlib import AsyncExitStack
from mcp import ClientSession
from mcp.types import Tool as MCPTool
from mcp.types import CallToolResult

from agentical.api import LLMBackend
from agentical.mcp.health import HealthMonitor, ServerReconnector, ServerCleanupHandler
from agentical.mcp.schemas import ServerConfig
from agentical.mcp.connection import MCPConnectionManager
from agentical.mcp.config import MCPConfigProvider, DictBasedMCPConfigProvider
from agentical.utils.log_utils import redact_sensitive_data, sanitize_log_message

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
    """
    
    # Health monitoring settings
    HEARTBEAT_INTERVAL = 30  # seconds
    MAX_HEARTBEAT_MISS = 2
    
    def __init__(
        self, 
        llm_backend: LLMBackend,
        config_provider: Optional[MCPConfigProvider] = None,
        server_configs: Optional[Dict[str, ServerConfig]] = None
    ):
        """Initialize the MCP Tool Provider.
        
        Args:
            llm_backend: LLMBackend instance for processing queries
            config_provider: Optional provider for loading configurations
            server_configs: Optional direct server configurations
            
        Raises:
            TypeError: If llm_backend is None or invalid type
            ValueError: If neither config_provider nor server_configs is provided
        """
        start_time = time.time()
        logger.info("Initializing MCPToolProvider", extra={
            "llm_backend_type": type(llm_backend).__name__,
            "has_config_provider": config_provider is not None,
            "has_server_configs": server_configs is not None
        })
        
        if not isinstance(llm_backend, LLMBackend):
            logger.error("Invalid llm_backend type", extra={
                "expected": "LLMBackend",
                "received": type(llm_backend).__name__
            })
            raise TypeError("llm_backend must be an instance of LLMBackend")
            
        if not config_provider and not server_configs:
            logger.error("Missing configuration source")
            raise ValueError("Either config_provider or server_configs must be provided")
            
        self.exit_stack = AsyncExitStack()
        self.connection_manager = MCPConnectionManager(self.exit_stack)
        self.available_servers: Dict[str, ServerConfig] = {}
        self.llm_backend = llm_backend
        self.tools_by_server: Dict[str, List[MCPTool]] = {}
        self.all_tools: List[MCPTool] = []
        
        # Store configuration source
        self.config_provider = config_provider
        if server_configs:
            self.config_provider = DictBasedMCPConfigProvider(server_configs)
        
        # Initialize health monitor
        self.health_monitor = HealthMonitor(
            heartbeat_interval=self.HEARTBEAT_INTERVAL,
            max_heartbeat_miss=self.MAX_HEARTBEAT_MISS,
            reconnector=self,
            cleanup_handler=self
        )
        
        duration = time.time() - start_time
        logger.info("MCPToolProvider initialized", extra={
            "duration_ms": int(duration * 1000),
            "heartbeat_interval": self.HEARTBEAT_INTERVAL,
            "max_heartbeat_miss": self.MAX_HEARTBEAT_MISS
        })
    
    async def initialize(self) -> None:
        """Initialize the provider with configurations.
        
        This method must be called before attempting to connect to any servers
        or process queries.
        
        Raises:
            ConfigurationError: If configuration loading fails
        """
        start_time = time.time()
        logger.info("Loading provider configurations")
        
        try:
            self.available_servers = await self.config_provider.load_config()
            duration = time.time() - start_time
            logger.info("Provider configurations loaded", extra={
                "num_servers": len(self.available_servers),
                "server_names": list(self.available_servers.keys()),
                "duration_ms": int(duration * 1000)
            })
        except Exception as e:
            duration = time.time() - start_time
            logger.error("Failed to load configurations", extra={
                "error": sanitize_log_message(str(e)),
                "duration_ms": int(duration * 1000)
            })
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
        logger.debug("Listing available servers", extra={
            "num_servers": len(servers),
            "servers": servers
        })
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
        start_time = time.time()
        logger.info("Attempting server reconnection", extra={
            "server_name": server_name
        })
        
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
                duration = time.time() - start_time
                logger.info("Server reconnection successful", extra={
                    "server_name": server_name,
                    "num_tools": len(tool_names),
                    "tool_names": tool_names,
                    "duration_ms": int(duration * 1000)
                })
                
                # Start health monitoring
                self.health_monitor.start_monitoring()
                return True
        except Exception as e:
            duration = time.time() - start_time
            logger.error("Server reconnection failed", extra={
                "server_name": server_name,
                "error": sanitize_log_message(str(e)),
                "duration_ms": int(duration * 1000)
            })
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
        start_time = time.time()
        if server_name is not None:
            await self.cleanup_server(server_name)
        else:
            await self.cleanup_all()
        
        duration = time.time() - start_time
        logger.info("Cleanup completed", extra={
            "server_name": server_name if server_name else "all",
            "duration_ms": int(duration * 1000)
        })

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
        start_time = time.time()
        logger.info("Starting server cleanup", extra={
            "server_name": server_name
        })
        
        try:
            # Remove server-specific tools
            num_tools_removed = 0
            if server_name in self.tools_by_server:
                server_tools = self.tools_by_server[server_name]
                num_tools_removed = len(server_tools)
                
                # Get tools from other servers to maintain in all_tools
                other_servers_tools = []
                for other_server, tools in self.tools_by_server.items():
                    if other_server != server_name:
                        other_servers_tools.extend(tools)
                
                # Update all_tools to only include tools from other servers
                self.all_tools = other_servers_tools
                
                # Remove server from tools_by_server
                del self.tools_by_server[server_name]
            
            # Clean up connection
            await self.connection_manager.cleanup(server_name)
            
            duration = time.time() - start_time
            logger.info("Server cleanup completed", extra={
                "server_name": server_name,
                "num_tools_removed": num_tools_removed,
                "remaining_tools": len(self.all_tools),
                "duration_ms": int(duration * 1000)
            })
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error("Server cleanup failed", extra={
                "server_name": server_name,
                "error": sanitize_log_message(str(e)),
                "duration_ms": int(duration * 1000)
            })

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
        start_time = time.time()
        logger.info("Starting provider cleanup")
        
        try:
            # First stop health monitoring to prevent reconnection attempts
            if hasattr(self, 'health_monitor'):
                try:
                    self.health_monitor.stop_monitoring()
                    logger.debug("Health monitoring stopped")
                except Exception as e:
                    logger.error("Failed to stop health monitor", extra={
                        "error": sanitize_log_message(str(e))
                    })
            
            # Clean up all connections
            if hasattr(self, 'connection_manager'):
                try:
                    await self.connection_manager.cleanup_all()
                    logger.debug("All connections cleaned up")
                except Exception as e:
                    logger.error("Failed to cleanup connections", extra={
                        "error": sanitize_log_message(str(e))
                    })
            
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
                    logger.debug("Exit stack closed")
                except* asyncio.CancelledError:
                    logger.info("Tasks cancelled during cleanup")
                except* Exception as e:
                    logger.error("Failed to close exit stack", extra={
                        "error": sanitize_log_message(str(e))
                    })
                
        except Exception as e:
            logger.error("Provider cleanup failed", extra={
                "error": sanitize_log_message(str(e))
            })
            
        finally:
            # Clear all stored references
            num_tools = len(self.all_tools) if hasattr(self, 'all_tools') else 0
            num_servers = len(self.tools_by_server) if hasattr(self, 'tools_by_server') else 0
            
            if hasattr(self, 'tools_by_server'):
                self.tools_by_server.clear()
            if hasattr(self, 'all_tools'):
                self.all_tools.clear()
                
            duration = time.time() - start_time
            logger.info("Provider cleanup completed", extra={
                "num_tools_cleared": num_tools,
                "num_servers_cleared": num_servers,
                "duration_ms": int(duration * 1000)
            })

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
        start_time = time.time()
        logger.info("Connecting to server", extra={
            "server_name": server_name
        })
        
        if not isinstance(server_name, str) or not server_name.strip():
            logger.error("Invalid server name", extra={
                "server_name": server_name
            })
            raise ValueError("server_name must be a non-empty string")
            
        if server_name not in self.available_servers:
            logger.error("Unknown server", extra={
                "server_name": server_name,
                "available_servers": self.list_available_servers()
            })
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
            duration = time.time() - start_time
            logger.info("Server connection successful", extra={
                "server_name": server_name,
                "num_tools": len(tool_names),
                "tool_names": tool_names,
                "duration_ms": int(duration * 1000)
            })
            
            # Start health monitoring
            self.health_monitor.start_monitoring()
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error("Server connection failed", extra={
                "server_name": server_name,
                "error": sanitize_log_message(str(e)),
                "duration_ms": int(duration * 1000)
            })
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
        start_time = time.time()
        servers = self.list_available_servers()
        logger.info("Connecting to all servers", extra={
            "num_servers": len(servers),
            "servers": servers
        })
        
        if not servers:
            logger.warning("No servers available")
            return []

        results = []
        # Connect to each server sequentially to avoid task/context issues
        for server_name in servers:
            try:
                await self.mcp_connect(server_name)
                results.append((server_name, None))
                logger.info("Server connection successful", extra={
                    "server_name": server_name
                })
            except Exception as e:
                results.append((server_name, e))
                logger.error("Server connection failed", extra={
                    "server_name": server_name,
                    "error": sanitize_log_message(str(e))
                })

        duration = time.time() - start_time
        successful = sum(1 for _, e in results if e is None)
        failed = sum(1 for _, e in results if e is not None)
        logger.info("All server connections completed", extra={
            "successful_connections": successful,
            "failed_connections": failed,
            "duration_ms": int(duration * 1000)
        })
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
        start_time = time.time()
        logger.info("Processing query", extra=redact_sensitive_data({
            "query": query,
            "num_tools_available": len(self.all_tools),
            "num_servers": len(self.tools_by_server)
        }))
        
        if not self.tools_by_server:
            logger.error("No active sessions")
            raise ValueError("Not connected to any MCP server. Please select and connect to a server first.")

        # Execute tool directly with MCP types
        async def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> CallToolResult:
            tool_start = time.time()
            logger.debug("Executing tool", extra=redact_sensitive_data({
                "tool_name": tool_name,
                "tool_args": tool_args
            }))
            
            # Find which server has this tool
            for server_name, tools in self.tools_by_server.items():
                if any(tool.name == tool_name for tool in tools):
                    logger.debug("Found tool in server", extra={
                        "tool_name": tool_name,
                        "server_name": server_name
                    })
                    try:
                        session = self.connection_manager.sessions[server_name]
                        result = await session.call_tool(tool_name, tool_args)
                        tool_duration = time.time() - tool_start
                        logger.debug("Tool execution successful", extra={
                            "tool_name": tool_name,
                            "server_name": server_name,
                            "duration_ms": int(tool_duration * 1000)
                        })
                        return result
                    except Exception as e:
                        tool_duration = time.time() - tool_start
                        logger.error("Tool execution failed", extra={
                            "tool_name": tool_name,
                            "server_name": server_name,
                            "error": sanitize_log_message(str(e)),
                            "duration_ms": int(tool_duration * 1000)
                        })
                        raise
            
            tool_duration = time.time() - tool_start
            logger.error("Tool not found", extra={
                "tool_name": tool_name,
                "duration_ms": int(tool_duration * 1000)
            })
            raise ValueError(f"Tool {tool_name} not found in any connected server")

        try:
            # Process the query using all available tools
            logger.debug("Sending query to LLM backend", extra={
                "num_tools": len(self.all_tools)
            })
            response = await self.llm_backend.process_query(
                query=query,
                tools=self.all_tools,
                execute_tool=execute_tool
            )
            duration = time.time() - start_time
            logger.info("Query processing completed", extra={
                "duration_ms": int(duration * 1000)
            })
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error("Query processing failed", extra={
                "error": sanitize_log_message(str(e)),
                "duration_ms": int(duration * 1000)
            })
            raise 