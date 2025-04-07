"""Configuration providers for MCP.

This module defines the configuration loading abstraction and implementations
for the MCP tool provider. It follows the dependency inversion principle to
decouple configuration sources from the provider implementation.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Protocol
from pydantic import ValidationError

from agentical.mcp.schemas import MCPConfig, ServerConfig

logger = logging.getLogger(__name__)

class MCPConfigProvider(Protocol):
    """Protocol defining how MCP configurations should be loaded.
    
    This protocol allows for different configuration sources to be used
    with the MCPToolProvider, following the dependency inversion principle.
    
    Implementation Notes:
        - Must be async-compatible
        - Should handle validation
        - Should provide proper error handling
        - Should use appropriate logging
    """
    async def load_config(self) -> Dict[str, ServerConfig]:
        """Load and return server configurations.
        
        Returns:
            Dict mapping server names to their validated configurations.
            
        Raises:
            ConfigurationError: If configuration loading or validation fails
        """
        ...

class ConfigurationError(Exception):
    """Base exception for configuration-related errors."""
    pass

class FileBasedMCPConfigProvider:
    """Loads MCP configuration from a JSON file.
    
    This provider implements the MCPConfigProvider protocol for loading
    configurations from local JSON files.
    
    Attributes:
        config_path: Path to the configuration file
    """
    
    def __init__(self, config_path: str | Path):
        """Initialize the file-based configuration provider.
        
        Args:
            config_path: Path to the configuration file. Can be string or Path.
        """
        self.config_path = Path(config_path)
    
    async def load_config(self) -> Dict[str, ServerConfig]:
        """Load and validate configuration from the JSON file.
        
        Returns:
            Dict mapping server names to their validated configurations.
            
        Raises:
            ConfigurationError: If file reading or validation fails
            FileNotFoundError: If config file doesn't exist
        """
        logger.info("Loading MCP configuration from: %s", self.config_path)
        try:
            with open(self.config_path) as f:
                raw_config = json.load(f)
            
            # Parse and validate configuration using Pydantic schema
            config = MCPConfig(servers=raw_config)
            logger.info("Successfully loaded configuration with %d servers", 
                       len(config.servers))
            return config.servers
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse configuration file: %s", str(e))
            raise ConfigurationError(f"Invalid JSON in config file: {str(e)}")
        except ValidationError as e:
            logger.error("Invalid configuration format: %s", str(e))
            raise ConfigurationError(f"Configuration validation failed: {str(e)}")
        except Exception as e:
            logger.error("Error loading configuration: %s", str(e))
            raise ConfigurationError(f"Failed to load configuration: {str(e)}")

class DictBasedMCPConfigProvider(MCPConfigProvider):
    """Configuration provider that loads from a dictionary."""

    def __init__(self, config: Dict[str, ServerConfig]):
        """Initialize with a dictionary configuration.

        Args:
            config: Dictionary mapping server names to their configurations
        """
        # Create a deep copy of the config to ensure immutability
        self._config = {
            name: ServerConfig(**server_config.model_dump())
            for name, server_config in config.items()
        }

    async def load_config(self) -> Dict[str, ServerConfig]:
        """Load configuration from the stored dictionary.

        Returns:
            Dict mapping server names to their configurations
        """
        # Return a deep copy to prevent modifications
        return {
            name: ServerConfig(**server_config.model_dump())
            for name, server_config in self._config.items()
        } 