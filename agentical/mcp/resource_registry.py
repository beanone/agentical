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
from typing import Dict, List, Set, Tuple

from mcp.types import Resource as MCPResource

logger = logging.getLogger(__name__)


class ResourceRegistry:
    """Manages the registration and lookup of MCP resources.

    This class handles the storage and retrieval of resources across different servers,
    providing a centralized registry for resource management.

    Attributes:
        resources_by_server (Dict[str, List[MCPResource]]): Resources indexed by server
        all_resources (List[MCPResource]): Combined list of all available resources
        _resource_names (Dict[str, Set[str]]): Resource names by server for tracking
    """

    def __init__(self):
        """Initialize an empty resource registry."""
        self.resources_by_server: Dict[str, List[MCPResource]] = {}
        self.all_resources: List[MCPResource] = []
        self._resource_names: Dict[str, Set[str]] = {}

    def _validate_resource(self, resource: MCPResource) -> None:
        """Validate a single resource.

        Args:
            resource: Resource to validate

        Raises:
            TypeError: If resource is not an MCPResource
            ValueError: If resource name is empty or invalid
        """
        if not isinstance(resource, MCPResource):
            raise TypeError(f"Resource must be an MCPResource, got {type(resource)}")

        if not resource.name:
            raise ValueError("Resource name cannot be empty")

        if not isinstance(resource.name, str):
            raise ValueError(f"Resource name must be a string, got {type(resource.name)}")

    def _validate_resources(self, resources: List[MCPResource], server_name: str) -> None:
        """Validate a list of resources.

        Args:
            resources: List of resources to validate
            server_name: Name of the server registering these resources

        Raises:
            TypeError: If resources is not a list or contains invalid types
            ValueError: If resource names are duplicated within the same server
        """
        if not isinstance(resources, list):
            raise TypeError(f"Resources must be a list, got {type(resources)}")

        # Validate each resource
        for resource in resources:
            self._validate_resource(resource)

        # Check for duplicates within the new resources
        new_names = {r.name for r in resources}
        if len(new_names) != len(resources):
            raise ValueError("Duplicate resource names found in the resources list")

    def register_server_resources(self, server_name: str, resources: List[MCPResource]) -> None:
        """Register resources for a specific server.

        Args:
            server_name: Name of the server
            resources: List of resources to register

        Raises:
            TypeError: If resources is not a list or contains invalid types
            ValueError: If resource names are duplicated within the same server

        Note:
            If the server already has registered resources, they will be replaced.
            The all_resources list is updated to include the new resources.
            Resources with the same name can exist on different servers.
        """
        logger.debug(
            "Registering resources for server",
            extra={"server_name": server_name, "num_resources": len(resources)},
        )

        try:
            # Validate resources before making any changes
            self._validate_resources(resources, server_name)

            # If server already exists, remove its resources first
            if server_name in self.resources_by_server:
                self.remove_server_resources(server_name)

            # Update registries
            self.resources_by_server[server_name] = resources
            self.all_resources.extend(resources)
            self._resource_names[server_name] = {r.name for r in resources}

            logger.debug(
                "Resources registered successfully",
                extra={"server_name": server_name, "total_resources": len(self.all_resources)},
            )
        except (TypeError, ValueError) as e:
            logger.error(
                "Failed to register resources",
                extra={
                    "server_name": server_name,
                    "error": str(e),
                },
            )
            raise

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

        try:
            # Get resources to remove
            removed_resources = self.resources_by_server[server_name]
            num_removed = len(removed_resources)

            # Remove from server mapping
            del self.resources_by_server[server_name]
            self._resource_names.pop(server_name, None)

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
        except Exception as e:
            logger.error(
                "Error removing server resources",
                extra={
                    "server_name": server_name,
                    "error": str(e),
                },
            )
            raise

    def find_resource_server(self, resource_name: str) -> str | None:
        """Find which server hosts a specific resource.

        Args:
            resource_name: Name of the resource to find

        Returns:
            Server name if found, None otherwise

        Note:
            If multiple servers have a resource with the same name,
            returns the first server found.
        """
        if not resource_name or not isinstance(resource_name, str):
            logger.warning("Invalid resource name", extra={"resource_name": resource_name})
            return None

        # Find the server
        for server_name, names in self._resource_names.items():
            if resource_name in names:
                return server_name
        return None

    def clear(self) -> Tuple[int, int]:
        """Clear all registered resources.

        Returns:
            Tuple of (number of resources cleared, number of servers cleared)

        Note:
            This operation completely resets the registry state.
            Both resources_by_server and all_resources collections are cleared.
        """
        try:
            num_resources = len(self.all_resources)
            num_servers = len(self.resources_by_server)

            logger.debug(
                "Clearing resource registry",
                extra={"num_resources": num_resources, "num_servers": num_servers},
            )

            self.resources_by_server.clear()
            self.all_resources.clear()
            self._resource_names.clear()

            return num_resources, num_servers
        except Exception as e:
            logger.error("Error clearing resource registry", extra={"error": str(e)})
            raise

    def get_server_resources(self, server_name: str) -> List[MCPResource]:
        """Get all resources registered for a specific server.

        Args:
            server_name: Name of the server

        Returns:
            List of resources registered for the server

        Note:
            Returns an empty list if the server is not found.
        """
        return self.resources_by_server.get(server_name, [])