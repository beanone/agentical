"""Prompt Registry for MCP.

This module provides a centralized registry for managing MCP prompts across different
servers. It handles prompt registration, lookup, and cleanup operations while
maintaining the relationship between prompts and their hosting servers.

Example:
    ```python
    registry = PromptRegistry()

    # Register prompts for a server
    registry.register_server_prompts("server1", prompts)

    # Find which server hosts a prompt
    server = registry.find_prompt_server("prompt_name")

    # Remove server prompts
    num_removed = registry.remove_server_prompts("server1")
    ```
"""

import logging

from mcp.types import Prompt as MCPPrompt

logger = logging.getLogger(__name__)


class PromptRegistry:
    """Manages the registration and lookup of MCP prompts.

    This class handles the storage and retrieval of prompts across different servers,
    providing a centralized registry for prompt management.

    Attributes:
        prompts_by_server (Dict[str, List[MCPPrompt]]): Prompts indexed by server
        all_prompts (List[MCPPrompt]): Combined list of all available prompts
    """

    def __init__(self):
        """Initialize an empty prompt registry."""
        self.prompts_by_server: dict[str, list[MCPPrompt]] = {}
        self.all_prompts: list[MCPPrompt] = []

    def register_server_prompts(self, server_name: str, prompts: list[MCPPrompt]) -> None:
        """Register prompts for a specific server.

        Args:
            server_name: Name of the server
            prompts: List of prompts to register

        Note:
            If the server already has registered prompts, they will be replaced.
            The all_prompts list is updated to include the new prompts.
        """
        logger.debug(
            "Registering prompts for server",
            extra={"server_name": server_name, "num_prompts": len(prompts)},
        )

        # If server already exists, remove its prompts first
        if server_name in self.prompts_by_server:
            self.remove_server_prompts(server_name)

        self.prompts_by_server[server_name] = prompts
        self.all_prompts.extend(prompts)

        logger.debug(
            "Prompts registered successfully",
            extra={"server_name": server_name, "total_prompts": len(self.all_prompts)},
        )

    def remove_server_prompts(self, server_name: str) -> int:
        """Remove all prompts for a specific server.

        Args:
            server_name: Name of the server

        Returns:
            Number of prompts removed

        Note:
            This operation updates both prompts_by_server and all_prompts.
            If the server doesn't exist, returns 0.
        """
        if server_name not in self.prompts_by_server:
            return 0

        num_removed = len(self.prompts_by_server[server_name])
        del self.prompts_by_server[server_name]

        # Rebuild all_prompts list
        self.all_prompts = [
            prompt
            for prompts in self.prompts_by_server.values()
            for prompt in prompts
        ]

        logger.debug(
            "Server prompts removed",
            extra={
                "server_name": server_name,
                "num_removed": num_removed,
                "remaining_prompts": len(self.all_prompts),
            },
        )
        return num_removed

    def find_prompt_server(self, prompt_name: str) -> str | None:
        """Find which server hosts a specific prompt.

        Args:
            prompt_name: Name of the prompt to find

        Returns:
            Server name if found, None otherwise

        Note:
            This is an O(n) operation where n is the total number of prompts
            across all servers. For better performance with large numbers of
            prompts, consider adding an index.
        """
        for server_name, prompts in self.prompts_by_server.items():
            if any(prompt.name == prompt_name for prompt in prompts):
                return server_name
        return None

    def clear(self) -> tuple[int, int]:
        """Clear all registered prompts.

        Returns:
            Tuple of (number of prompts cleared, number of servers cleared)

        Note:
            This operation completely resets the registry state.
            Both prompts_by_server and all_prompts collections are cleared.
        """
        num_prompts = len(self.all_prompts)
        num_servers = len(self.prompts_by_server)

        logger.debug(
            "Clearing prompt registry",
            extra={"num_prompts": num_prompts, "num_servers": num_servers},
        )

        self.prompts_by_server.clear()
        self.all_prompts.clear()
        return num_prompts, num_servers

    def get_server_prompts(self, server_name: str) -> list[MCPPrompt]:
        """Get all prompts registered for a specific server.

        Args:
            server_name: Name of the server

        Returns:
            List of prompts registered for the server

        Note:
            Returns an empty list if the server is not found.
        """
        return self.prompts_by_server.get(server_name, [])