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
from typing import Dict, List, Set, Tuple

from mcp.types import Prompt as MCPPrompt

logger = logging.getLogger(__name__)


class PromptRegistry:
    """Manages the registration and lookup of MCP prompts.

    This class handles the storage and retrieval of prompts across different servers,
    providing a centralized registry for prompt management.

    Attributes:
        prompts_by_server (Dict[str, List[MCPPrompt]]): Prompts indexed by server
        all_prompts (List[MCPPrompt]): Combined list of all available prompts
        _prompt_names (Dict[str, Set[str]]): Prompt names by server for tracking
    """

    def __init__(self):
        """Initialize an empty prompt registry."""
        self.prompts_by_server: Dict[str, List[MCPPrompt]] = {}
        self.all_prompts: List[MCPPrompt] = []
        self._prompt_names: Dict[str, Set[str]] = {}

    def _validate_prompt(self, prompt: MCPPrompt) -> None:
        """Validate a single prompt.

        Args:
            prompt: Prompt to validate

        Raises:
            TypeError: If prompt is not an MCPPrompt
            ValueError: If prompt name is empty or invalid
        """
        if not isinstance(prompt, MCPPrompt):
            raise TypeError(f"Prompt must be an MCPPrompt, got {type(prompt)}")

        if not prompt.name:
            raise ValueError("Prompt name cannot be empty")

        if not isinstance(prompt.name, str):
            raise ValueError(f"Prompt name must be a string, got {type(prompt.name)}")

    def _validate_prompts(self, prompts: List[MCPPrompt], server_name: str) -> None:
        """Validate a list of prompts.

        Args:
            prompts: List of prompts to validate
            server_name: Name of the server registering these prompts

        Raises:
            TypeError: If prompts is not a list or contains invalid types
            ValueError: If prompt names are duplicated within the same server
        """
        if not isinstance(prompts, list):
            raise TypeError(f"Prompts must be a list, got {type(prompts)}")

        # Validate each prompt
        for prompt in prompts:
            self._validate_prompt(prompt)

        # Check for duplicates within the new prompts
        new_names = {p.name for p in prompts}
        if len(new_names) != len(prompts):
            raise ValueError("Duplicate prompt names found in the prompts list")

    def register_server_prompts(
        self, server_name: str, prompts: List[MCPPrompt]
    ) -> None:
        """Register prompts for a specific server.

        Args:
            server_name: Name of the server
            prompts: List of prompts to register

        Raises:
            TypeError: If prompts is not a list or contains invalid types
            ValueError: If prompt names are duplicated within the same server

        Note:
            If the server already has registered prompts, they will be replaced.
            The all_prompts list is updated to include the new prompts.
            Prompts with the same name can exist on different servers.
        """
        logger.debug(
            "Registering prompts for server",
            extra={"server_name": server_name, "num_prompts": len(prompts)},
        )

        try:
            # Validate prompts before making any changes
            self._validate_prompts(prompts, server_name)

            # If server already exists, remove its prompts first
            if server_name in self.prompts_by_server:
                self.remove_server_prompts(server_name)

            # Update registries
            self.prompts_by_server[server_name] = prompts
            self.all_prompts.extend(prompts)
            self._prompt_names[server_name] = {p.name for p in prompts}

            logger.debug(
                "Prompts registered successfully",
                extra={
                    "server_name": server_name,
                    "total_prompts": len(self.all_prompts),
                },
            )
        except (TypeError, ValueError) as e:
            logger.error(
                "Failed to register prompts",
                extra={
                    "server_name": server_name,
                    "error": str(e),
                },
            )
            raise

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

        try:
            # Get prompts to remove
            removed_prompts = self.prompts_by_server[server_name]
            num_removed = len(removed_prompts)

            # Remove from server mapping
            del self.prompts_by_server[server_name]
            self._prompt_names.pop(server_name, None)

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
        except Exception as e:
            logger.error(
                "Error removing server prompts",
                extra={
                    "server_name": server_name,
                    "error": str(e),
                },
            )
            raise

    def find_prompt_server(self, prompt_name: str) -> str | None:
        """Find which server hosts a specific prompt.

        Args:
            prompt_name: Name of the prompt to find

        Returns:
            Server name if found, None otherwise

        Note:
            If multiple servers have a prompt with the same name,
            returns the first server found.
        """
        if not prompt_name or not isinstance(prompt_name, str):
            logger.warning("Invalid prompt name", extra={"prompt_name": prompt_name})
            return None

        # Find the server
        for server_name, names in self._prompt_names.items():
            if prompt_name in names:
                return server_name
        return None

    def clear(self) -> Tuple[int, int]:
        """Clear all registered prompts.

        Returns:
            Tuple of (number of prompts cleared, number of servers cleared)

        Note:
            This operation completely resets the registry state.
            Both prompts_by_server and all_prompts collections are cleared.
        """
        try:
            num_prompts = len(self.all_prompts)
            num_servers = len(self.prompts_by_server)

            logger.debug(
                "Clearing prompt registry",
                extra={"num_prompts": num_prompts, "num_servers": num_servers},
            )

            self.prompts_by_server.clear()
            self.all_prompts.clear()
            self._prompt_names.clear()

            return num_prompts, num_servers
        except Exception as e:
            logger.error("Error clearing prompt registry", extra={"error": str(e)})
            raise

    def get_server_prompts(self, server_name: str) -> List[MCPPrompt]:
        """Get all prompts registered for a specific server.

        Args:
            server_name: Name of the server

        Returns:
            List of prompts registered for the server

        Note:
            Returns an empty list if the server is not found.
        """
        return self.prompts_by_server.get(server_name, [])
