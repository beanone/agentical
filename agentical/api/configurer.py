"""Configuration provider interface for MCP server configurations.

This module defines the interface for loading and managing MCP server configurations.
Different implementations can support various configuration sources (files, remote, etc.).
"""

from abc import ABC, abstractmethod
from typing import Dict, List


class ConfigurationProvider(ABC):
    """Abstract base class for loading and managing MCP server configurations.
    
    This interface defines the contract for configuration providers that handle
    MCP server configurations. Implementations can support different configuration
    sources such as files, environment variables, remote servers, etc.
    
    Attributes:
        None
    """
    
    @abstractmethod
    async def load_config(self) -> Dict[str, dict]:
        """Load and validate server configurations from the source.
        
        Returns:
            Dict[str, dict]: A dictionary mapping server names to their configurations.
            Each configuration must contain at least:
                - command: str - The command to start the server
                - args: List[str] - Command line arguments for the server
                
        Raises:
            ValueError: If the configuration is invalid
            IOError: If the configuration cannot be loaded
        """
        pass
        
    @abstractmethod
    async def get_server_config(self, name: str) -> dict:
        """Get configuration for a specific server.
        
        Args:
            name: The name of the server to get configuration for.
            
        Returns:
            dict: The server configuration containing at least:
                - command: str - The command to start the server
                - args: List[str] - Command line arguments for the server
                
        Raises:
            KeyError: If the server name is not found
            ValueError: If the configuration is invalid
        """
        pass
        
    @abstractmethod
    async def list_available_servers(self) -> List[str]:
        """List all available MCP servers from the loaded configuration.
        
        Returns:
            List[str]: A list of server names that are available in the configuration.
            
        Raises:
            IOError: If the configuration cannot be accessed
        """
        pass 