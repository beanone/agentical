"""File-based configuration provider for MCP server configurations.

This module implements a file-based configuration provider that loads and validates
MCP server configurations from JSON files.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, Field, field_validator
from agentical.api.configurer import ConfigurationProvider


# Configure module logger
logger = logging.getLogger(__name__)

class ServerConfig(BaseModel):
    """Pydantic model for server configuration validation.
    
    Attributes:
        command: The command to run the server
        args: List of command line arguments
    """
    command: str = Field(..., description="Command to run the server")
    args: List[str] = Field(..., description="Command line arguments")
    
    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Validate that command is not empty."""
        if not v.strip():
            raise ValueError("Command cannot be empty")
        return v
    
    @field_validator("args")
    @classmethod
    def validate_args(cls, v: List[str]) -> List[str]:
        """Validate that all arguments are non-empty strings."""
        if not all(isinstance(arg, str) and arg.strip() for arg in v):
            raise ValueError("All arguments must be non-empty strings")
        return v


class MCPConfig(BaseModel):
    """Pydantic model for the complete MCP configuration.
    
    Attributes:
        servers: Dictionary mapping server names to their configurations
    """
    servers: Dict[str, ServerConfig]


class FileConfigProvider(ConfigurationProvider):
    """File-based implementation of the ConfigurationProvider interface.
    
    This class implements configuration loading and validation from JSON files.
    It supports caching of configurations to avoid repeated file reads.
    
    Attributes:
        config_path: Path to the configuration file
        _config_cache: Internal cache of loaded configurations
    """
    
    def __init__(self, config_path: str | Path) -> None:
        """Initialize the file configuration provider.
        
        Args:
            config_path: Path to the JSON configuration file
            
        Raises:
            ValueError: If the config_path is empty or None
        """
        if not config_path:
            logger.error("Attempted to initialize with empty config_path")
            raise ValueError("Configuration path cannot be empty")
            
        self.config_path = Path(config_path)
        self._config_cache: Dict[str, dict] = {}
        logger.info("Initialized FileConfigProvider with config path: %s", self.config_path)
        
    async def load_config(self) -> Dict[str, dict]:
        """Load and validate server configurations from the JSON file.
        
        Returns:
            Dict[str, dict]: A dictionary mapping server names to their configurations
            
        Raises:
            FileNotFoundError: If the configuration file does not exist
            ValueError: If the configuration is invalid
            json.JSONDecodeError: If the file contains invalid JSON
        """
        logger.debug("Attempting to load configuration from: %s", self.config_path)
        
        if not self.config_path.exists():
            logger.error("Configuration file not found: %s", self.config_path)
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
            
        try:
            with open(self.config_path) as f:
                raw_config = json.load(f)
                
            # Validate using Pydantic model
            config = MCPConfig.model_validate(raw_config).model_dump()["servers"]
            self._config_cache = config
            logger.info("Successfully loaded and validated configuration with %d servers", len(config))
            return config
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON configuration: %s", e)
            raise
        except ValueError as e:
            logger.error("Invalid configuration format: %s", e)
            raise
        
    async def get_server_config(self, name: str) -> dict:
        """Get configuration for a specific server.
        
        Args:
            name: The name of the server to get configuration for
            
        Returns:
            dict: The server configuration
            
        Raises:
            KeyError: If the server name is not found
            ValueError: If the configuration is invalid or not loaded
        """
        logger.debug("Retrieving configuration for server: %s", name)
        
        if not self._config_cache:
            logger.info("Configuration not loaded, loading now")
            await self.load_config()
            
        if name not in self._config_cache:
            logger.warning("Server '%s' not found in configuration", name)
            raise KeyError(f"Server '{name}' not found in configuration")
            
        logger.debug("Successfully retrieved configuration for server: %s", name)
        return self._config_cache[name]
        
    async def list_available_servers(self) -> List[str]:
        """List all available MCP servers from the loaded configuration.
        
        Returns:
            List[str]: A list of server names that are available
            
        Raises:
            IOError: If the configuration cannot be accessed
        """
        logger.debug("Listing available servers")
        
        if not self._config_cache:
            logger.info("Configuration not loaded, loading now")
            await self.load_config()
            
        server_list = list(self._config_cache.keys())
        logger.debug("Found %d available servers", len(server_list))
        return server_list 