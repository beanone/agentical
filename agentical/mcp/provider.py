"""MCPToolProvider implementation using the new LLM Layer abstraction.

This module implements the main integration layer between LLM backends and MCP tools.
It provides a robust facade that manages server connections, tool discovery, and
query processing while maintaining connection health and proper resource cleanup.

Key Features:
- Automatic server connection management
- Health monitoring with automatic reconnection
- Tool discovery and management
- Resource discovery and management
- Prompt discovery and management
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
    - Maintains resource registry for resource management
    - Maintains prompt registry for prompt management
    - Provides comprehensive error handling
    - Ensures proper resource cleanup
"""

import logging
import time
from contextlib import AsyncExitStack
from typing import Any, Dict

from mcp.types import CallToolResult, Resource as MCPResource, Prompt as MCPPrompt

from agentical.api import LLMBackend
from agentical.mcp.config import DictBasedMCPConfigProvider, MCPConfigProvider
from agentical.mcp.connection import MCPConnectionService
from agentical.mcp.schemas import ServerConfig
from agentical.mcp.tool_registry import ToolRegistry
from agentical.mcp.resource_registry import ResourceRegistry
from agentical.mcp.prompt_registry import PromptRegistry
from agentical.utils.log_utils import sanitize_log_message

logger = logging.getLogger(__name__)


class MCPToolProvider:
    """Main facade for integrating LLMs with MCP tools, resources, and prompts."""

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
        self.resource_registry = ResourceRegistry()
        self.prompt_registry = PromptRegistry()
        self._connected_servers: Dict[str, bool] = {}

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
                f"Unknown server: {server_name}. "
                f"Available servers: {self.list_available_servers()}"
            )

        try:
            # Connect using connection service with config
            session = await self.connection_service.connect(
                server_name, self.available_servers[server_name]
            )

            # Initialize and get tools
            response = await session.list_tools()
            self.tool_registry.register_server_tools(server_name, response.tools)

            # Get and register resources if available
            try:
                resources = await session.list_resources()
                if resources and resources.resources:
                    self.resource_registry.register_server_resources(
                        server_name, resources.resources
                    )
                    # Verify resources were registered
                    registered_resources = self.resource_registry.get_server_resources(
                        server_name
                    )
                    logger.debug(
                        "Server resources registered",
                        extra={
                            "server_name": server_name,
                            "num_resources": len(registered_resources),
                            "resource_names": [r.name for r in registered_resources],
                        },
                    )
            except Exception as e:
                logger.debug(f"Server does not support resources: {e}")

            # Get and register prompts if available
            try:
                prompts = await session.list_prompts()
                if prompts and prompts.prompts:
                    self.prompt_registry.register_server_prompts(
                        server_name, prompts.prompts
                    )
                    # Verify prompts were registered
                    registered_prompts = self.prompt_registry.get_server_prompts(
                        server_name
                    )
                    logger.debug(
                        "Server prompts registered",
                        extra={
                            "server_name": server_name,
                            "num_prompts": len(registered_prompts),
                            "prompt_names": [p.name for p in registered_prompts],
                        },
                    )
            except Exception as e:
                logger.debug(f"Server does not support prompts: {e}")

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
        """Clean up resources for a specific server."""
        start_time = time.time()
        logger.info("Cleaning up server", extra={"server_name": server_name})

        try:
            # Clean up connection
            await self.connection_service.cleanup(server_name)

            # Remove tools
            self.tool_registry.remove_server_tools(server_name)

            # Remove resources
            self.resource_registry.remove_server_resources(server_name)

            # Remove prompts
            self.prompt_registry.remove_server_prompts(server_name)

            duration = time.time() - start_time
            logger.info(
                "Server cleanup successful",
                extra={"server_name": server_name, "duration_ms": int(duration * 1000)},
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
            raise  # Re-raise the exception after logging

    async def reconnect(self, server_name: str) -> bool:
        """Attempt to reconnect to a server."""
        start_time = time.time()
        logger.info("Reconnecting to server", extra={"server_name": server_name})

        try:
            # Clean up existing connection
            await self.cleanup_server(server_name)

            # Try to reconnect
            await self.mcp_connect(server_name)

            duration = time.time() - start_time
            logger.info(
                "Server reconnection successful",
                extra={"server_name": server_name, "duration_ms": int(duration * 1000)},
            )
            return True
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Server reconnection failed",
                extra={
                    "server_name": server_name,
                    "error": sanitize_log_message(str(e)),
                    "duration_ms": int(duration * 1000),
                },
            )
            return False

    async def get_resource(self, resource_name: str) -> MCPResource:
        """Get a resource by name."""
        start_time = time.time()
        logger.info("Getting resource", extra={"resource_name": resource_name})

        try:
            # Find the server that has this resource
            server_name = self.resource_registry.find_resource_server(resource_name)
            if not server_name:
                raise ValueError(f"Resource not found: {resource_name}")

            # Get the resource from the registry
            resource = self.resource_registry.get_resource(resource_name)
            if not resource:
                raise ValueError(f"Resource not found: {resource_name}")

            duration = time.time() - start_time
            logger.info(
                "Resource retrieved successfully",
                extra={
                    "resource_name": resource_name,
                    "server_name": server_name,
                    "duration_ms": int(duration * 1000),
                },
            )
            return resource
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Failed to get resource",
                extra={
                    "resource_name": resource_name,
                    "error": sanitize_log_message(str(e)),
                    "duration_ms": int(duration * 1000),
                },
            )
            raise

    async def get_prompt(self, prompt_name: str) -> MCPPrompt:
        """Get a prompt by name."""
        start_time = time.time()
        logger.info("Getting prompt", extra={"prompt_name": prompt_name})

        try:
            # Find the server that has this prompt
            server_name = self.prompt_registry.find_prompt_server(prompt_name)
            if not server_name:
                raise ValueError(f"Prompt not found: {prompt_name}")

            # Get the prompt from the registry
            prompt = self.prompt_registry.get_prompt(prompt_name)
            if not prompt:
                raise ValueError(f"Prompt not found: {prompt_name}")

            duration = time.time() - start_time
            logger.info(
                "Prompt retrieved successfully",
                extra={
                    "prompt_name": prompt_name,
                    "server_name": server_name,
                    "duration_ms": int(duration * 1000),
                },
            )
            return prompt
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                "Failed to get prompt",
                extra={
                    "prompt_name": prompt_name,
                    "error": sanitize_log_message(str(e)),
                    "duration_ms": int(duration * 1000),
                },
            )
            raise

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
            # Clear registries first
            if hasattr(self, "tool_registry"):
                num_tools = len(self.tool_registry.all_tools)
                num_servers = len(self.tool_registry.tools_by_server)
                self.tool_registry.clear()
                logger.info(
                    "Tool registry cleared",
                    extra={
                        "num_tools": num_tools,
                        "num_servers": num_servers,
                    },
                )

            if hasattr(self, "resource_registry"):
                num_resources = len(self.resource_registry.all_resources)
                num_servers = len(self.resource_registry.resources_by_server)
                self.resource_registry.clear()
                logger.info(
                    "Resource registry cleared",
                    extra={
                        "num_resources": num_resources,
                        "num_servers": num_servers,
                    },
                )

            if hasattr(self, "prompt_registry"):
                num_prompts = len(self.prompt_registry.all_prompts)
                num_servers = len(self.prompt_registry.prompts_by_server)
                self.prompt_registry.clear()
                logger.info(
                    "Prompt registry cleared",
                    extra={
                        "num_prompts": num_prompts,
                        "num_servers": num_servers,
                    },
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

            # Clear connection tracking
            self._connected_servers.clear()

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

    async def execute_tool(
        self, tool_name: str, tool_args: dict[str, Any]
    ) -> CallToolResult:
        """Execute a tool by name with the given arguments.

        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments to pass to the tool

        Returns:
            CallToolResult: Result from the tool execution

        Raises:
            ValueError: If tool is not found or server is not connected
            Exception: If tool execution fails
        """
        tool_start = time.time()
        logger.debug(
            "Executing tool", extra={"tool_name": tool_name, "tool_args": tool_args}
        )

        # Find which server has this tool
        server_name = self.tool_registry.find_tool_server(tool_name)
        if not server_name:
            tool_duration = time.time() - tool_start
            logger.error(
                "Tool not found",
                extra={
                    "tool_name": tool_name,
                    "duration_ms": int(tool_duration * 1000),
                },
            )
            raise ValueError(f"Tool {tool_name} not found in any connected server")

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

    async def process_query(self, query: str) -> str:
        """Process a query using the LLM backend and available tools.

        Args:
            query: The query to process

        Returns:
            str: Response from the LLM backend

        Raises:
            Exception: If query processing fails
        """
        start_time = time.time()
        logger.info("Processing query", extra={"query": query})

        try:
            # Process the query using all available tools, resources, and prompts
            logger.debug(
                "Sending query to LLM backend",
                extra={
                    "num_tools": len(self.tool_registry.all_tools),
                    "num_resources": len(self.resource_registry.all_resources),
                    "num_prompts": len(self.prompt_registry.all_prompts),
                },
            )
            response = await self.llm_backend.process_query(
                query=query,
                tools=self.tool_registry.all_tools,
                resources=self.resource_registry.all_resources,
                prompts=self.prompt_registry.all_prompts,
                execute_tool=self.execute_tool,
                context=None,
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

    async def reconnect_server(self, server_name: str) -> bool:
        """Reconnect to an MCP server and re-discover its capabilities.

        Args:
            server_name: Name of the server to reconnect to

        Returns:
            bool: True if reconnection was successful

        Note:
            This method first cleans up existing registrations for the server
            then rediscovers its tools, resources, and prompts.
        """
        logger.info("Reconnecting to MCP server", extra={"server_name": server_name})

        try:
            # Clean up existing registrations
            await self.cleanup_server(server_name)

            # Reconnect and rediscover capabilities
            await self.mcp_connect(server_name)

            # Verify reconnection by checking tools, resources, and prompts
            tools = self.tool_registry.get_server_tools(server_name)
            resources = self.resource_registry.get_server_resources(server_name)
            prompts = self.prompt_registry.get_server_prompts(server_name)

            logger.info(
                "Successfully reconnected to server",
                extra={
                    "server_name": server_name,
                    "num_tools": len(tools),
                    "num_resources": len(resources),
                    "num_prompts": len(prompts),
                },
            )
            return True

        except Exception as e:
            logger.error(
                "Failed to reconnect to server",
                extra={
                    "server_name": server_name,
                    "error": sanitize_log_message(str(e)),
                },
            )
            return False

    def _process_query_impl(
        self,
        query: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Implementation of query processing.

        This method should be overridden by subclasses to implement
        the actual query processing logic using the LLM backend.
        """
        raise NotImplementedError("Subclasses must implement _process_query_impl")
