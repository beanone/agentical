"""Tool Registry for MCP.

This module provides a centralized registry for managing MCP tools across different servers.
It handles tool registration, lookup, and cleanup operations while maintaining the relationship
between tools and their hosting servers.

Example:
    ```python
    registry = ToolRegistry()

    # Register tools for a server
    registry.register_server_tools("server1", tools)

    # Find which server hosts a tool
    server = registry.find_tool_server("tool_name")

    # Remove server tools
    num_removed = registry.remove_server_tools("server1")
    ```
"""

import logging

from mcp.types import Tool as MCPTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Manages the registration and lookup of MCP tools.

    This class handles the storage and retrieval of tools across different servers,
    providing a centralized registry for tool management.

    Attributes:
        tools_by_server (Dict[str, List[MCPTool]]): Tools indexed by server
        all_tools (List[MCPTool]): Combined list of all available tools
    """

    def __init__(self):
        """Initialize an empty tool registry."""
        self.tools_by_server: dict[str, list[MCPTool]] = {}
        self.all_tools: list[MCPTool] = []

    def register_server_tools(self, server_name: str, tools: list[MCPTool]) -> None:
        """Register tools for a specific server.

        Args:
            server_name: Name of the server
            tools: List of tools to register

        Note:
            If the server already has registered tools, they will be replaced.
            The all_tools list is updated to include the new tools.
        """
        logger.debug(
            "Registering tools for server",
            extra={"server_name": server_name, "num_tools": len(tools)},
        )

        # If server already exists, remove its tools first
        if server_name in self.tools_by_server:
            self.remove_server_tools(server_name)

        self.tools_by_server[server_name] = tools
        self.all_tools.extend(tools)

        logger.debug(
            "Tools registered successfully",
            extra={"server_name": server_name, "total_tools": len(self.all_tools)},
        )

    def remove_server_tools(self, server_name: str) -> int:
        """Remove all tools for a specific server.

        Args:
            server_name: Name of the server

        Returns:
            Number of tools removed

        Note:
            This operation updates both tools_by_server and all_tools collections.
            Tools from other servers are preserved.
        """
        logger.debug("Removing tools for server", extra={"server_name": server_name})

        num_tools_removed = 0
        if server_name in self.tools_by_server:
            server_tools = self.tools_by_server[server_name]
            num_tools_removed = len(server_tools)

            # Get tools from other servers
            other_servers_tools = []
            for other_server, tools in self.tools_by_server.items():
                if other_server != server_name:
                    other_servers_tools.extend(tools)

            # Update all_tools
            self.all_tools = other_servers_tools
            del self.tools_by_server[server_name]

            logger.debug(
                "Server tools removed",
                extra={
                    "server_name": server_name,
                    "num_tools_removed": num_tools_removed,
                    "remaining_tools": len(self.all_tools),
                },
            )

        return num_tools_removed

    def find_tool_server(self, tool_name: str) -> str | None:
        """Find which server hosts a specific tool.

        Args:
            tool_name: Name of the tool to find

        Returns:
            Server name if found, None otherwise

        Note:
            This is an O(n) operation where n is the total number of tools
            across all servers. For better performance with large numbers of
            tools, consider adding an index.
        """
        for server_name, tools in self.tools_by_server.items():
            if any(tool.name == tool_name for tool in tools):
                return server_name
        return None

    def clear(self) -> tuple[int, int]:
        """Clear all registered tools.

        Returns:
            Tuple of (number of tools cleared, number of servers cleared)

        Note:
            This operation completely resets the registry state.
            Both tools_by_server and all_tools collections are cleared.
        """
        num_tools = len(self.all_tools)
        num_servers = len(self.tools_by_server)

        logger.debug(
            "Clearing tool registry",
            extra={"num_tools": num_tools, "num_servers": num_servers},
        )

        self.tools_by_server.clear()
        self.all_tools.clear()
        return num_tools, num_servers

    def get_server_tools(self, server_name: str) -> list[MCPTool]:
        """Get all tools registered for a specific server.

        Args:
            server_name: Name of the server

        Returns:
            List of tools registered for the server

        Note:
            Returns an empty list if the server is not found.
        """
        return self.tools_by_server.get(server_name, [])
