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
from contextlib import AsyncExitStack
from typing import Any

from mcp.types import CallToolResult

from agentical.api import LLMBackend
from agentical.mcp.config import DictBasedMCPConfigProvider, MCPConfigProvider
from agentical.mcp.connection import MCPConnectionService
from agentical.mcp.schemas import ServerConfig
from agentical.mcp.tool_registry import ToolRegistry
from agentical.utils.log_utils import sanitize_log_message

logger = logging.getLogger(__name__)


class MCPToolProvider:
    """Main facade for integrating LLMs with MCP tools."""

    def __init__(
        self,
        llm_backend: LLMBackend,
        config_provider: MCPConfigProvider | None = None,
        server_configs: dict[str, ServerConfig] | None = None,
    ):
        """Initialize the MCP Tool Provider."""
        start_time = time.time()
        logger.info(
            "Initializing MCPToolProvider",
            extra={
                "llm_backend_type": type(llm_backend).__name__,
                "has_config_provider": config_provider is not None,
                "has_server_configs": server_configs is not None,
            },
        )

        if not isinstance(llm_backend, LLMBackend):
            logger.error(
                "Invalid llm_backend type",
                extra={
                    "expected": "LLMBackend",
                    "received": type(llm_backend).__name__,
                },
            )
            raise TypeError("llm_backend must be an instance of LLMBackend")

        if not config_provider and not server_configs:
            logger.error("Missing configuration source")
            raise ValueError(
                "Either config_provider or server_configs must be provided"
            )

        self.exit_stack = AsyncExitStack()
        self.connection_service = MCPConnectionService(self.exit_stack)
        self.available_servers: dict[str, ServerConfig] = {}
        self.llm_backend = llm_backend
        self.tool_registry = ToolRegistry()

        # Store configuration source
        self.config_provider = config_provider
        if server_configs:
            self.config_provider = DictBasedMCPConfigProvider(server_configs)

        duration = time.time() - start_time
        logger.info(
            "MCPToolProvider initialized", extra={"duration_ms": int(duration * 1000)}
        )

    async def initialize(self) -> None:
        """Initialize the provider with configurations."""
        start_time = time.time()
        logger.info("Loading provider configurations")

        try:
            self.available_servers = await self.config_provider.load_config()
            duration = time.time() - start_time
            logger.info(
                "Provider configurations loaded",
                extra={
                    "num_servers": len(self.available_servers),
                    "server_names": list(self.available_servers.keys()),
                    "duration_ms": int(duration * 1000),
                },
            )
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Failed to load configurations",
                extra={
                    "error": sanitize_log_message(str(e)),
                    "duration_ms": int(duration * 1000),
                },
            )
            raise

    def list_available_servers(self) -> list[str]:
        """List all available MCP servers from the loaded configuration."""
        servers = list(self.available_servers.keys())
        logger.debug(
            "Listing available servers",
            extra={"num_servers": len(servers), "servers": servers},
        )
        return servers

    async def mcp_connect(self, server_name: str) -> None:
        """Connect to a specific MCP server by name."""
        start_time = time.time()
        logger.info("Connecting to server", extra={"server_name": server_name})

        if not isinstance(server_name, str) or not server_name.strip():
            logger.error("Invalid server name", extra={"server_name": server_name})
            raise ValueError("server_name must be a non-empty string")

        if server_name not in self.available_servers:
            logger.error(
                "Unknown server",
                extra={
                    "server_name": server_name,
                    "available_servers": self.list_available_servers(),
                },
            )
            raise ValueError(
                f"Unknown server: {server_name}. Available servers: {self.list_available_servers()}"
            )

        try:
            # Connect using connection service
            session = await self.connection_service.connect(
                server_name, self.available_servers[server_name]
            )

            # Initialize and get tools
            response = await session.list_tools()

            # Register tools
            self.tool_registry.register_server_tools(server_name, response.tools)

            tool_names = [tool.name for tool in response.tools]
            duration = time.time() - start_time
            logger.info(
                "Server connection successful",
                extra={
                    "server_name": server_name,
                    "num_tools": len(tool_names),
                    "tool_names": tool_names,
                    "duration_ms": int(duration * 1000),
                },
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Server connection failed",
                extra={
                    "server_name": server_name,
                    "error": sanitize_log_message(str(e)),
                    "duration_ms": int(duration * 1000),
                },
            )
            await self.cleanup_server(server_name)
            raise ConnectionError(f"Failed to connect to server '{server_name}': {e!s}")

    async def mcp_connect_all(self) -> list[tuple[str, Exception | None]]:
        """Connect to all available MCP servers concurrently."""
        start_time = time.time()
        servers = self.list_available_servers()
        logger.info(
            "Connecting to all servers",
            extra={"num_servers": len(servers), "servers": servers},
        )

        if not servers:
            logger.warning("No servers available")
            return []

        results = []
        # Connect to each server sequentially to avoid task/context issues
        for server_name in servers:
            try:
                await self.mcp_connect(server_name)
                results.append((server_name, None))
                logger.info(
                    "Server connection successful", extra={"server_name": server_name}
                )
            except Exception as e:
                results.append((server_name, e))
                logger.error(
                    "Server connection failed",
                    extra={
                        "server_name": server_name,
                        "error": sanitize_log_message(str(e)),
                    },
                )

        duration = time.time() - start_time
        successful = sum(1 for _, e in results if e is None)
        failed = sum(1 for _, e in results if e is not None)
        logger.info(
            "All server connections completed",
            extra={
                "successful_connections": successful,
                "failed_connections": failed,
                "duration_ms": int(duration * 1000),
            },
        )
        return results

    async def cleanup_server(self, server_name: str) -> None:
        """Clean up a specific server's resources."""
        start_time = time.time()
        logger.info("Starting server cleanup", extra={"server_name": server_name})

        try:
            # Remove server tools
            num_tools_removed = self.tool_registry.remove_server_tools(server_name)

            # Clean up connection
            await self.connection_service.disconnect(server_name)

            duration = time.time() - start_time
            logger.info(
                "Server cleanup completed",
                extra={
                    "server_name": server_name,
                    "num_tools_removed": num_tools_removed,
                    "remaining_tools": len(self.tool_registry.all_tools),
                    "duration_ms": int(duration * 1000),
                },
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Server cleanup failed",
                extra={
                    "server_name": server_name,
                    "error": sanitize_log_message(str(e)),
                    "duration_ms": int(duration * 1000),
                },
            )

    async def reconnect(self, server_name: str) -> bool:
        """Reconnect to a server and re-register its tools.

        Args:
            server_name: Name of the server to reconnect to

        Returns:
            bool: True if reconnection was successful, False otherwise
        """
        try:
            if server_name not in self.available_servers:
                logger.warning(f"Cannot reconnect to unknown server: {server_name}")
                return False

            # First clean up any existing tools for this server
            await self.cleanup_server(server_name)

            # Get the server config
            config = self.available_servers[server_name]

            # Attempt to connect using the connection service
            session = await self.connection_service.connect(server_name, config)

            # Get and register tools
            response = await session.list_tools()
            self.tool_registry.register_server_tools(server_name, response.tools)

            return True
        except Exception as e:
            logger.error(f"Failed to reconnect to server {server_name}: {e!s}")
            await self.cleanup_server(server_name)
            return False

    async def cleanup_all(self) -> None:
        """Clean up all provider resources.

        This is the main cleanup method for the provider, cleaning up all
        resources including servers, connections, and internal state.

        Note:
            - Safe to call multiple times
            - Handles cleanup errors gracefully
            - Ensures proper task cancellation
            - Closes all resources in correct order
        """
        start_time = time.time()
        logger.info("Starting provider cleanup")

        try:
            # Clear tool registry first
            if hasattr(self, "tool_registry"):
                num_tools = len(self.tool_registry.all_tools)
                num_servers = len(self.tool_registry.tools_by_server)
                num_tools_cleared, num_servers_cleared = self.tool_registry.clear()
                logger.info(
                    f"Tool registry cleared - {num_tools} tools from {num_servers} servers"
                )

            # Clean up all connections through the service
            # This will handle both connection cleanup and health monitoring
            if hasattr(self, "connection_service"):
                await self.connection_service.cleanup_all()
                logger.info("Connection service cleaned up")

            # Close the exit stack last
            if hasattr(self, "exit_stack"):
                try:
                    await self.exit_stack.aclose()
                    logger.info("Exit stack closed")
                except Exception as e:
                    logger.error(
                        "Failed to close exit stack",
                        extra={"error": sanitize_log_message(str(e))},
                    )

            duration = time.time() - start_time
            logger.info(
                "Provider cleanup completed",
                extra={"duration_ms": int(duration * 1000)},
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Provider cleanup failed",
                extra={
                    "error": sanitize_log_message(str(e)),
                    "duration_ms": int(duration * 1000),
                },
            )
            raise

    async def cleanup(self, server_name: str = None) -> None:
        """Clean up server resources.

        This method serves two purposes:
        1. When called with server_name, it cleans up resources for a specific server
        2. When called without server_name, it cleans up all provider resources

        Args:
            server_name: Optional name of the server to clean up. If not provided,
                        cleans up all resources.

        Note:
            - Safe to call multiple times
            - Handles cleanup errors gracefully
        """
        if server_name is not None:
            await self.cleanup_server(server_name)
        else:
            await self.cleanup_all()

    async def process_query(self, query: str) -> str:
        """Process a user query using the configured LLM backend."""
        start_time = time.time()
        logger.info(
            "Processing query",
            extra={
                "query": query,
                "num_tools_available": len(self.tool_registry.all_tools),
                "num_servers": len(self.tool_registry.tools_by_server),
            },
        )

        if not self.tool_registry.tools_by_server:
            logger.error("No active sessions")
            raise ValueError(
                "Not connected to any MCP server. "
                "Please select and connect to a server first."
            )

        # Execute tool directly with MCP types
        async def execute_tool(
            tool_name: str, tool_args: dict[str, Any]
        ) -> CallToolResult:
            tool_start = time.time()
            logger.debug(
                "Executing tool", extra={"tool_name": tool_name, "tool_args": tool_args}
            )

            # Find which server has this tool
            server_name = self.tool_registry.find_tool_server(tool_name)
            if server_name:
                logger.debug(
                    "Found tool in server",
                    extra={"tool_name": tool_name, "server_name": server_name},
                )
                try:
                    session = self.connection_service.get_session(server_name)
                    if not session:
                        raise ValueError(f"No active session for server {server_name}")

                    result = await session.call_tool(tool_name, tool_args)
                    tool_duration = time.time() - tool_start
                    logger.debug(
                        "Tool execution successful",
                        extra={
                            "tool_name": tool_name,
                            "server_name": server_name,
                            "duration_ms": int(tool_duration * 1000),
                        },
                    )
                    return result
                except Exception as e:
                    tool_duration = time.time() - tool_start
                    logger.error(
                        "Tool execution failed",
                        extra={
                            "tool_name": tool_name,
                            "server_name": server_name,
                            "error": sanitize_log_message(str(e)),
                            "duration_ms": int(tool_duration * 1000),
                        },
                    )
                    raise

            tool_duration = time.time() - tool_start
            logger.error(
                "Tool not found",
                extra={
                    "tool_name": tool_name,
                    "duration_ms": int(tool_duration * 1000),
                },
            )
            raise ValueError(f"Tool {tool_name} not found in any connected server")

        try:
            # Process the query using all available tools
            logger.debug(
                "Sending query to LLM backend",
                extra={"num_tools": len(self.tool_registry.all_tools)},
            )
            response = await self.llm_backend.process_query(
                query=query,
                tools=self.tool_registry.all_tools,
                execute_tool=execute_tool,
            )
            duration = time.time() - start_time
            logger.info(
                "Query processing completed",
                extra={"duration_ms": int(duration * 1000)},
            )
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Query processing failed",
                extra={
                    "error": sanitize_log_message(str(e)),
                    "duration_ms": int(duration * 1000),
                },
            )
            raise
