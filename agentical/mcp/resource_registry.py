"""Resource Registry for MCP.

This module provides a centralized registry for managing MCP resources across different
servers. It handles resource registration, lookup, and cleanup operations while
maintaining the relationship between resources and their hosting servers.

Example:
    ```python
    registry = ResourceRegistry()

    # Register resources for a server
    registry.register_server_resources("server1", resources)

    # Find which server hosts a resource
    server = registry.find_resource_server("resource_name")

    # Remove server resources
    num_removed = registry.remove_server_resources("server1")
    ```
"""

import logging

from mcp.types import Resource as MCPResource

logger = logging.getLogger(__name__)


class ResourceRegistry:
    """Manages the registration and lookup of MCP resources.

    This class handles the storage and retrieval of resources across different servers,
    providing a centralized registry for resource management.

    Attributes:
        resources_by_server (Dict[str, List[MCPResource]]): Resources indexed by server
        all_resources (List[MCPResource]): Combined list of all available resources
    """

    def __init__(self):
        """Initialize an empty resource registry."""
        self.resources_by_server: dict[str, list[MCPResource]] = {}
        self.all_resources: list[MCPResource] = []

    def register_server_resources(self, server_name: str, resources: list[MCPResource]) -> None:
        """Register resources for a specific server.

        Args:
            server_name: Name of the server
            resources: List of resources to register

        Note:
            If the server already has registered resources, they will be replaced.
            The all_resources list is updated to include the new resources.
        """
        logger.debug(
            "Registering resources for server",
            extra={"server_name": server_name, "num_resources": len(resources)},
        )

        # If server already exists, remove its resources first
        if server_name in self.resources_by_server:
            self.remove_server_resources(server_name)

        self.resources_by_server[server_name] = resources
        self.all_resources.extend(resources)

        logger.debug(
            "Resources registered successfully",
            extra={"server_name": server_name, "total_resources": len(self.all_resources)},
        )

    def remove_server_resources(self, server_name: str) -> int:
        """Remove all resources for a specific server.

        Args:
            server_name: Name of the server

        Returns:
            Number of resources removed

        Note:
            This operation updates both resources_by_server and all_resources.
            If the server doesn't exist, returns 0.
        """
        if server_name not in self.resources_by_server:
            return 0

        num_removed = len(self.resources_by_server[server_name])
        del self.resources_by_server[server_name]

        # Rebuild all_resources list
        self.all_resources = [
            resource
            for resources in self.resources_by_server.values()
            for resource in resources
        ]

        logger.debug(
            "Server resources removed",
            extra={
                "server_name": server_name,
                "num_removed": num_removed,
                "remaining_resources": len(self.all_resources),
            },
        )
        return num_removed

    def find_resource_server(self, resource_name: str) -> str | None:
        """Find which server hosts a specific resource.

        Args:
            resource_name: Name of the resource to find

        Returns:
            Server name if found, None otherwise

        Note:
            This is an O(n) operation where n is the total number of resources
            across all servers. For better performance with large numbers of
            resources, consider adding an index.
        """
        for server_name, resources in self.resources_by_server.items():
            if any(resource.name == resource_name for resource in resources):
                return server_name
        return None

    def clear(self) -> tuple[int, int]:
        """Clear all registered resources.

        Returns:
            Tuple of (number of resources cleared, number of servers cleared)

        Note:
            This operation completely resets the registry state.
            Both resources_by_server and all_resources collections are cleared.
        """
        num_resources = len(self.all_resources)
        num_servers = len(self.resources_by_server)

        logger.debug(
            "Clearing resource registry",
            extra={"num_resources": num_resources, "num_servers": num_servers},
        )

        self.resources_by_server.clear()
        self.all_resources.clear()
        return num_resources, num_servers

    def get_server_resources(self, server_name: str) -> list[MCPResource]:
        """Get all resources registered for a specific server.

        Args:
            server_name: Name of the server

        Returns:
            List of resources registered for the server

        Note:
            Returns an empty list if the server is not found.
        """
        return self.resources_by_server.get(server_name, [])